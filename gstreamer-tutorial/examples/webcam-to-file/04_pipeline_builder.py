"""
04_pipeline_builder.py
----------------------
The same hardware encoding pipeline as 03_hardware_encode.py, but built
element-by-element using Python objects rather than a pipeline string.

This style is more verbose than parse_launch, but it gives you:
  - Direct Python references to each element for runtime property changes
  - Clearer separation between pipeline structure and element configuration
  - Type-checked property setting (typos fail at set_property, not at runtime)
  - A natural place to add conditional logic (different settings per camera, etc.)

Reading this script alongside 03_hardware_encode.py shows that both approaches
produce an identical pipeline. Use parse_launch for simple fixed pipelines;
use element-by-element building for anything that needs runtime flexibility.

Run:    python3 04_pipeline_builder.py
Stop:   Ctrl+C
Output: output_pipeline_builder.mp4
"""

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import signal
import subprocess
import sys

Gst.init(None)


def set_encoder_bitrate(bitrate_bps: int) -> None:
    """Set hardware encoder bitrate via v4l2-ctl before the pipeline starts."""
    result = subprocess.run(
        ["v4l2-ctl", "--list-devices"],
        capture_output=True, text=True
    )
    encoder_device = None
    lines = result.stdout.splitlines()
    in_codec_section = False
    for line in lines:
        if "bcm2835-codec" in line:
            in_codec_section = True
            continue
        if in_codec_section and "/dev/video" in line:
            encoder_device = line.strip()
            break
        if in_codec_section and line.strip() == "":
            break
    if encoder_device:
        subprocess.run(
            ["v4l2-ctl", "-d", encoder_device,
             "--set-ctrl", f"video_bitrate={bitrate_bps}"],
            check=False
        )
        print(f"Hardware encoder bitrate set to {bitrate_bps // 1000} kbps on {encoder_device}")
    else:
        print("WARNING: Hardware encoder device not found. Using default bitrate.")


def create_pipeline(
    camera_device:  str = "/dev/video0",
    width:          int = 1280,
    height:         int = 720,
    framerate:      int = 30,
    output_path:    str = "output_pipeline_builder.mp4",
) -> Gst.Pipeline:
    """
    Create and return a fully configured hardware encoding pipeline.

    Accepting configuration as parameters rather than hardcoding it
    is good practice: it makes the function reusable and testable,
    and it documents exactly what can vary about the pipeline.

    Returns a Gst.Pipeline in NULL state, ready to be started with
    set_state(Gst.State.PLAYING).
    """

    # ----------------------------------------------------------------
    # Create the pipeline container
    # ----------------------------------------------------------------
    # Gst.Pipeline is a special bin (container) that also manages a
    # shared clock for all elements inside it. Every element you create
    # must be added to this pipeline before it can be linked to others.
    pipeline = Gst.Pipeline.new("hardware-encode-pipeline")

    # ----------------------------------------------------------------
    # Create each element
    # ----------------------------------------------------------------
    # Gst.ElementFactory.make(element_name, instance_name)
    # The instance_name is a label you can use to retrieve the element
    # later with pipeline.get_by_name("label"). Choose descriptive names.

    source      = Gst.ElementFactory.make("v4l2src",      "camera-source")
    decoder     = Gst.ElementFactory.make("jpegdec",       "mjpeg-decoder")
    converter   = Gst.ElementFactory.make("v4l2convert",   "v4l2-converter")
    encoder     = Gst.ElementFactory.make("v4l2h264enc",   "hw-encoder")
    parser      = Gst.ElementFactory.make("h264parse",     "h264-parser")
    muxer       = Gst.ElementFactory.make("mp4mux",        "mp4-muxer")
    sink        = Gst.ElementFactory.make("filesink",      "file-sink")

    # Verify all elements were created successfully.
    # ElementFactory.make returns None if the element plugin is not installed.
    all_elements = [source, decoder, converter, encoder, parser, muxer, sink]
    for elem in all_elements:
        if elem is None:
            # The element name is not directly available here, but we can
            # check which one is None by looking at the list position.
            idx = all_elements.index(elem)
            names = ["v4l2src", "jpegdec", "v4l2convert", "v4l2h264enc",
                     "h264parse", "mp4mux", "filesink"]
            print(f"ERROR: Could not create element '{names[idx]}'.")
            print("       Is the required GStreamer plugin package installed?")
            print("       Run: sudo apt install gstreamer1.0-plugins-bad gstreamer1.0-v4l2")
            sys.exit(1)

    # ----------------------------------------------------------------
    # Configure element properties
    # ----------------------------------------------------------------
    # set_property(property_name, value) is the Python equivalent of
    # writing key=value in a gst-launch-1.0 pipeline string.
    # Property names use hyphens (not underscores) as GStreamer convention.

    # Camera: which device to open, and whether to generate timestamps.
    # do-timestamp=True ensures each frame gets a presentation timestamp,
    # which mp4mux needs to write correct timing information.
    source.set_property("device", camera_device)
    source.set_property("do-timestamp", True)

    # Hardware encoder: the extra-controls string passes V4L2 kernel controls.
    #   repeat_sequence_header=1   → embed SPS/PPS headers regularly (not just at start)
    #   h264_i_frame_period=30     → keyframe every 30 frames (= every 1 second at 30fps)
    encoder.set_property(
        "extra-controls",
        "controls,repeat_sequence_header=1,h264_i_frame_period=30"
    )

    # H264parse: config-interval=1 re-inserts the stream headers before
    # every keyframe, making the output file seek-friendly.
    parser.set_property("config-interval", 1)

    # Filesink: where to write the output file.
    # sync=False means write as fast as possible without throttling to
    # real-time — this prevents dropped frames on slow storage.
    sink.set_property("location", output_path)
    sink.set_property("sync", False)

    # ----------------------------------------------------------------
    # Add all elements to the pipeline
    # ----------------------------------------------------------------
    # Elements must be added to the pipeline BEFORE linking. Adding
    # attaches them to the pipeline's clock, memory pool, and message bus.
    for elem in all_elements:
        pipeline.add(elem)

    # ----------------------------------------------------------------
    # Link elements together
    # ----------------------------------------------------------------
    # Plain link() lets GStreamer negotiate the format automatically.
    # link_filtered() inserts an explicit caps constraint between two elements,
    # preventing GStreamer from picking an unexpected or incompatible format.

    # Camera → decoder: request MJPEG at exactly our target resolution/framerate.
    # Without this constraint, the camera might choose a different mode.
    mjpeg_caps = Gst.Caps.from_string(
        f"image/jpeg,width={width},height={height},framerate={framerate}/1"
    )
    source.link_filtered(decoder, mjpeg_caps)

    # Decoder → converter: no constraint needed; videoconvert/v4l2convert accept
    # whatever pixel format jpegdec produces.
    decoder.link(converter)

    # Converter → encoder: force I420 pixel format.
    # This is the most important caps constraint in the hardware pipeline.
    # I420 (planar YUV 4:2:0) is the format the VideoCore encoder expects.
    # Without this, GStreamer might negotiate a format the hardware rejects.
    yuv_caps = Gst.Caps.from_string("video/x-raw,format=I420")
    converter.link_filtered(encoder, yuv_caps)

    # Encoder → parser: declare the H.264 level.
    # level=(string)4 means H.264 level 4, which supports up to 1080p30.
    # The (string) type annotation is required because GStreamer represents
    # levels as strings (to support half-levels like 4.1, 4.2).
    h264_caps = Gst.Caps.from_string("video/x-h264,level=(string)4")
    encoder.link_filtered(parser, h264_caps)

    # Parser → muxer → sink: no constraints needed for these final steps.
    parser.link(muxer)
    muxer.link(sink)

    return pipeline


# -----------------------------------------------------------------
# Main
# -----------------------------------------------------------------
set_encoder_bitrate(2_000_000)   # 2 Mbps

pipeline = create_pipeline(
    camera_device = "/dev/video0",
    width         = 1280,
    height        = 720,
    framerate     = 30,
    output_path   = "output_pipeline_builder.mp4",
)


def on_sigint(sig, frame):
    """Send EOS on Ctrl+C to ensure mp4mux writes the file index correctly."""
    print("\nStopping... sending EOS to finalise the MP4 file.")
    pipeline.send_event(Gst.Event.new_eos())


signal.signal(signal.SIGINT, on_sigint)

pipeline.set_state(Gst.State.PLAYING)
print("Recording with HARDWARE encoder (element-by-element pipeline).")
print("Output: output_pipeline_builder.mp4")
print("Press Ctrl+C to stop.\n")

bus = pipeline.get_bus()

while True:
    msg = bus.timed_pop_filtered(
        Gst.MSECOND * 200,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    if msg is not None:
        if msg.type == Gst.MessageType.ERROR:
            err, debug_info = msg.parse_error()
            print(f"\nGStreamer error: {err.message}")
            print(f"Debug info:      {debug_info}")
            break
        elif msg.type == Gst.MessageType.EOS:
            print("File finalised successfully.")
            break

pipeline.set_state(Gst.State.NULL)
print("Pipeline stopped. Output saved to: output_pipeline_builder.mp4")
