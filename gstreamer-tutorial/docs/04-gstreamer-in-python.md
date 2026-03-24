# 04 — GStreamer in Python

Everything you did with `gst-launch-1.0` in the previous document can be done
from Python. The two approaches are not fundamentally different — Python just
gives you variables, logic, and loops around the same underlying GStreamer
machinery. This document explains how the Python bindings work and how they
map to the concepts you already know.

---

## PyGObject: The Bridge Between Python and GStreamer

GStreamer is written in C. Python accesses it through a library called
**PyGObject**, which is a general-purpose bridge between Python and C libraries
that follow the GLib/GObject convention (a convention used by GStreamer, GTK,
and many other Linux libraries). When you installed `python3-gst-1.0`, you
installed PyGObject together with the GStreamer-specific bindings on top of it.

You will always begin a GStreamer Python script with the same three lines:

```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst
```

The `gi` module is PyGObject itself. `gi.require_version("Gst", "1.0")` tells
it which version of GStreamer to bind to — this must be called before importing
from `gi.repository`, otherwise you might accidentally bind to an older version
if one is present on the system. `from gi.repository import Gst` imports the
GStreamer namespace, giving you access to everything GStreamer exposes.

One more line must appear before you use any GStreamer functionality:

```python
Gst.init(None)
```

This initialises the GStreamer library — loading plugins, setting up internal
data structures, and parsing any GStreamer-specific command-line arguments if
you pass `sys.argv` instead of `None`. Without this call, every GStreamer
function call after it will fail in confusing ways.

---

## Method 1: parse_launch — The Direct Translation

The fastest way to move from a working `gst-launch-1.0` command to Python is
`Gst.parse_launch()`. It takes the exact same pipeline string you used on the
command line and returns a pipeline object ready to run:

```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)

# This is exactly the same string you tested in gst-launch-1.0,
# just moved into Python as a multi-line string for readability.
pipeline = Gst.parse_launch("""
    v4l2src device=/dev/video0
    ! image/jpeg,width=1280,height=720,framerate=30/1
    ! jpegdec
    ! videoconvert
    ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=2000
    ! h264parse config-interval=1
    ! mp4mux
    ! filesink location=output.mp4
""")

# Tell the pipeline to start flowing data.
# This is equivalent to pressing Enter in gst-launch-1.0.
pipeline.set_state(Gst.State.PLAYING)
```

`parse_launch` is convenient and readable, but it has one limitation: you
cannot easily get a reference to individual elements inside the pipeline to
change their properties after the pipeline has been built. For simple, fixed
pipelines this does not matter — but for anything more dynamic, Method 2 is
better.

---

## Method 2: Building Element by Element

The more explicit approach creates each element individually, sets its
properties directly in Python, adds them all to a pipeline object, and then
links them together. This is more verbose but gives you full control:

```python
import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

Gst.init(None)

# Create the pipeline container. Think of this as an empty conveyor belt.
pipeline = Gst.Pipeline.new("my-pipeline")

# Create each element individually.
# Gst.ElementFactory.make(element_name, instance_name)
# The instance_name is just a label you can use to look up the element later.
source    = Gst.ElementFactory.make("v4l2src",    "camera")
decoder   = Gst.ElementFactory.make("jpegdec",    "decoder")
converter = Gst.ElementFactory.make("videoconvert", "converter")
encoder   = Gst.ElementFactory.make("x264enc",    "encoder")
parser    = Gst.ElementFactory.make("h264parse",  "parser")
muxer     = Gst.ElementFactory.make("mp4mux",     "muxer")
sink      = Gst.ElementFactory.make("filesink",   "sink")

# Set properties directly on each element using Python.
# This is cleaner than embedding them in a string.
source.set_property("device", "/dev/video0")
encoder.set_property("tune", "zerolatency")
encoder.set_property("speed-preset", "ultrafast")
encoder.set_property("bitrate", 2000)
parser.set_property("config-interval", 1)
sink.set_property("location", "output.mp4")

# Every element must be added to the pipeline before it can be linked.
# This attaches the element to the pipeline's internal clock and
# memory management system.
for elem in [source, decoder, converter, encoder, parser, muxer, sink]:
    pipeline.add(elem)

# Create a caps filter as a Gst.Caps object and use link_filtered
# to link two elements with that constraint between them.
mjpeg_caps = Gst.Caps.from_string(
    "image/jpeg,width=1280,height=720,framerate=30/1"
)

# link_filtered links two elements AND inserts a caps filter between them.
source.link_filtered(decoder, mjpeg_caps)

# For elements without caps constraints, plain link() is enough.
decoder.link(converter)
converter.link(encoder)
encoder.link(parser)
parser.link(muxer)
muxer.link(sink)

pipeline.set_state(Gst.State.PLAYING)
```

Notice that caps filters in the element-by-element approach are handled
differently from the pipeline string approach. Instead of inserting them as
literal strings between `!` characters, you create a `Gst.Caps` object and pass
it to `link_filtered()`. The result is identical — a caps constraint between
two elements — but expressed in Python objects rather than a string.

---

## Pipeline States

A GStreamer pipeline moves through several states during its lifecycle. When you
call `set_state(Gst.State.PLAYING)`, GStreamer does not jump straight to
playing — it transitions through intermediate states, each performing different
setup work. Understanding these states explains why errors sometimes happen
before any data has flowed.

`Gst.State.NULL` is the initial state when a pipeline is created. Elements
exist but no resources are allocated. `Gst.State.READY` means elements have
opened their resources (the camera driver has been initialised, the output file
has been created) but data is not yet flowing. `Gst.State.PAUSED` means the
pipeline has been fully negotiated and pre-rolled — all elements have agreed on
formats and the first frame has been buffered — but playback is paused.
`Gst.State.PLAYING` means data is actively flowing through the pipeline.

When you call `set_state(Gst.State.PLAYING)`, GStreamer transitions from NULL
through READY and PAUSED to PLAYING in sequence. Caps negotiation happens
during the PAUSED transition. This is why negotiation errors appear even though
you have not actually played any video yet — the format negotiation is resolved
during setup, not during playback.

When you are done, always transition back to NULL to release resources cleanly:

```python
pipeline.set_state(Gst.State.NULL)
```

---

## Keeping the Pipeline Running

`set_state(Gst.State.PLAYING)` returns immediately. Without anything after it,
your Python script will reach the end of the file, the pipeline object will be
garbage-collected, and everything will shut down instantly before any video is
captured. You need to keep the script alive while the pipeline is running.

The simplest approach for a script you stop manually is a loop that waits for
a keyboard interrupt:

```python
import time
import signal
import sys

# Start the pipeline
pipeline.set_state(Gst.State.PLAYING)

def stop(sig, frame):
    print("Stopping pipeline...")
    pipeline.set_state(Gst.State.NULL)
    sys.exit(0)

# When the user presses Ctrl+C, stop cleanly
signal.signal(signal.SIGINT, stop)

print("Recording... press Ctrl+C to stop.")
while True:
    time.sleep(1)
```

The complete example scripts in `examples/webcam-to-file/` use exactly this
pattern so you can see it working in a full, runnable context.

---

## Checking for Errors

GStreamer communicates events — including errors — through a **bus**: a message
queue that elements post messages to as they run. Polling the bus gives you
access to error messages, warnings, end-of-stream notifications, and state
changes.

For a simple capture script, the most important thing to check for is errors.
This pattern polls the bus on each loop iteration:

```python
bus = pipeline.get_bus()

while True:
    # Try to get a message without blocking.
    # timeout=0 means return immediately even if no messages are waiting.
    msg = bus.timed_pop_filtered(
        0,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    if msg:
        if msg.type == Gst.MessageType.ERROR:
            err, debug = msg.parse_error()
            print(f"Error: {err.message}")
            print(f"Debug: {debug}")
            break
        elif msg.type == Gst.MessageType.EOS:
            print("End of stream reached.")
            break

    time.sleep(0.1)

pipeline.set_state(Gst.State.NULL)
```

`Gst.MessageType.EOS` is an "end of stream" message — it is sent when a source
element has run out of data. For a file source, this is expected and normal.
For a live camera, you will never get EOS unless the camera is disconnected.

The complete example scripts combine error checking with the signal handler
pattern shown above. After reading this document, the code in those scripts
should feel self-explanatory rather than mysterious.

**Next: [05 — Software Encoding](05-software-encoding.md)**
