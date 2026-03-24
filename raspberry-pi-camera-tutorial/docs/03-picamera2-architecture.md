# 03 — Picamera2 Architecture

Understanding the architecture of Picamera2 isn't strictly necessary to take photos — but it's the kind of knowledge that prevents you from being confused when something doesn't work as expected, and that opens up advanced capabilities once you're ready for them. This document walks through every layer of the system, from your Python code at the top all the way down to the physical camera sensor at the bottom.

---

## The Big Picture — A Layered System

The camera system on a Raspberry Pi is built in distinct layers, each with a clear responsibility. Think of it like an onion: your code sits on the outside, and every layer beneath it handles something more specific and lower-level. When you call `picam2.capture_file()`, that call travels down through all of these layers before any actual hardware is touched, and the resulting image data travels all the way back up.

```
┌─────────────────────────────────────────────┐
│           YOUR PYTHON APPLICATION            │
│  (The code you write)                        │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           PICAMERA2 LIBRARY                  │
│  (Configuration, Encoders, Previews,         │
│   Buffer management)                         │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           LIBCAMERA FRAMEWORK                │
│  (Camera Manager, Pipeline Handler,          │
│   Auto Exposure / AWB / Autofocus)           │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│              HARDWARE                        │
│  (Image Sensor → ISP → DMA / Memory)         │
└─────────────────────────────────────────────┘
```

Let's look at each layer in detail.

---

## Layer 1: Your Application Code

At the top is your Python program. You interact with everything through a single entry point: the `Picamera2` class. This class is designed as a **facade** — a software pattern that provides one simple interface to a complex system. From the outside, you call `start()`, `capture_file()`, and `stop()`. What those three calls trigger internally, across multiple threads and hardware subsystems, is substantial. The facade hides that complexity from you so you can focus on what you're building.

---

## Layer 2: The Picamera2 Library

The Picamera2 library layer is where the Python-friendly interface is translated into lower-level camera operations. It contains four major subsystems that you'll interact with, either directly or indirectly.

### The Configuration System

Configuration is how you tell the camera what mode to operate in before you start it. Think of it as choosing the right tool for the job — you configure for stills when you want maximum quality, for video when you need frame rate, for preview when you need low latency.

When you call `create_still_configuration()`, Picamera2 builds a `CameraConfiguration` object that describes the full pipeline setup: what resolution to use, what format the image data should be in, how many memory buffers to allocate, and which sensor mode to request from libcamera. Here's a simplified look at what that configuration object contains:

```python
# What create_still_configuration() returns (simplified)
{
    "main": {          # The primary output stream
        "size": (4608, 2592),      # Full sensor resolution
        "format": "XBGR8888"       # Pixel format
    },
    "lores": None,     # Optional low-resolution stream (disabled by default)
    "raw": None,       # Optional raw Bayer data stream (disabled by default)
    "transform": Transform(hflip=False, vflip=False),
    "colour_space": ColorSpace.Sycc(),
    "buffer_count": 1
}
```

You can modify any of these values before calling `configure()`. For example, if you want to capture a thumbnail alongside your full-resolution image in a single request:

```python
config = picam2.create_still_configuration(
    main={"size": (4608, 2592)},
    lores={"size": (640, 480)}   # Enable the low-res stream
)
picam2.configure(config)
```

The three configuration types optimise for different things: `create_still_configuration()` maximises quality by choosing the highest-resolution sensor mode and applying strong noise reduction; `create_video_configuration()` maximises throughput by choosing a sensor mode that delivers high frame rates with lower overhead; and `create_preview_configuration()` minimises latency for real-time display.

### The Control System

If configuration is choosing the right tool, controls are adjusting that tool while you're using it. Controls affect the image signal processor's behaviour in real time and can be changed at any moment while the camera is running. The full list of available controls on your specific camera can be queried with `picam2.camera_controls`, but the most commonly used ones are shown in this table:

| Control | Type | Range | What it does |
|---------|------|-------|--------------|
| `Brightness` | float | -1.0 → 1.0 | Post-processing brightness offset |
| `Contrast` | float | 0.0 → 32.0 | Shadow/highlight spread |
| `Saturation` | float | 0.0 → 32.0 | Color vividness |
| `ExposureTime` | int (µs) | varies | Sensor integration time (overrides AE) |
| `AnalogueGain` | float | varies | Sensor amplification (like ISO) |
| `AwbMode` | int | enum | Auto white balance mode |
| `AfMode` | int | enum | Autofocus mode (Module 3 only) |
| `Sharpness` | float | 0.0 → 16.0 | Edge sharpening strength |
| `NoiseReductionMode` | int | enum | How aggressively noise is reduced |
| `ColourGains` | tuple | varies | Manual red/blue gains (overrides AWB) |

### The Capture Methods

The capture methods are your bridge between the live camera stream and your application. Understanding the difference between them will save you a lot of confusion.

`capture_file(filename)` is the simplest: it grabs a frame, encodes it based on the file extension you provide (`.jpg`, `.png`, etc.), and writes it to disk. It's one line and it just works.

`capture_array()` returns the current frame as a numpy array in memory. This is what you use for any kind of image analysis, computer vision, or real-time processing — anything where you want to *look at* the image in Python rather than just *save* it.

`capture_buffer()` returns the raw memory buffer in its native format, before any conversion to a numpy array. This is useful for maximum-performance pipelines where even the numpy conversion overhead matters, though most users will use `capture_array()` instead.

`capture_metadata()` returns information *about* the last frame without returning the image itself. This metadata includes the actual exposure time used, the analogue gain, the colour gains applied by auto white balance, the focus position, and more. It's very useful for debugging (why does my image look wrong?) and for logging (what settings did the camera actually use?).

`capture_request()` is the lowest-level method, giving you direct access to a `CompletedRequest` object that contains all active streams simultaneously. This is the method to use when you need to grab a high-res main image and a low-res thumbnail in the same instant, or when you need raw Bayer data alongside the processed image.

### Streams, Encoders, and Previews

When the camera is running, it continuously produces frames — typically at somewhere between 15 and 120 frames per second depending on the mode. Picamera2 manages where those frames go through a stream-based architecture. You can have multiple streams active simultaneously:

The **main stream** is the primary output at your configured resolution. The **lores stream** is an optional low-resolution copy of the same frames, useful when you want to run fast image analysis on small frames while also recording high-resolution stills. The **raw stream** gives you the unprocessed Bayer sensor data, useful for custom ISP pipelines or scientific applications.

**Encoders** consume a stream and compress it into a video format. `H264Encoder` produces efficient H.264 video, which is what you'll use for most recording applications. `MJPEGEncoder` produces Motion JPEG, essentially a sequence of JPEG frames in a single file — simpler but less efficient. When you call `start_encoder(encoder, output)`, the encoder runs in its own thread, continuously pulling frames from the specified stream and writing compressed data to the output.

**Previews** are live display windows that show the camera feed in real time. `QtPreview` creates a window using the Qt framework, which works well on systems with a desktop environment. `DrmPreview` renders directly to the display hardware, bypassing the window system entirely — this is the option for headless embedded systems. `NullPreview` does nothing at all and is used when you want Picamera2's preview infrastructure to exist (because some code paths require it) but you don't actually want a window.

---

## Layer 3: The libcamera Framework

Below Picamera2 sits libcamera, the modern Linux camera stack that replaced the older MMAL/V4L2 system. You don't interact with libcamera directly in most applications — Picamera2 handles that translation — but understanding what libcamera does explains why some things work the way they do.

The **Camera Manager** is responsible for discovering all cameras connected to the system at boot time. It enumerates devices, reads their capability information, and enforces exclusive access — only one application can have a camera open at a time. When you create a `Picamera2()` object, it requests a camera from the Camera Manager, which grants access if no other application is currently using it.

The **Pipeline Handler** is the component that actually configures the complete image processing chain for a specific hardware platform. On a Raspberry Pi, the pipeline involves the camera sensor, the ISP (which lives in the GPU), DMA controllers for moving image data efficiently between hardware components, and output buffers that your application can read. The pipeline handler knows the specific capabilities and quirks of the Raspberry Pi hardware and sets everything up according to your configuration requirements.

The **image processing algorithms** run continuously in the background as long as the camera is streaming. Auto-Exposure (AE) analyses each frame's brightness and adjusts the exposure time and gain to keep the image properly exposed. Auto White Balance (AWB) samples the color distribution of the scene and applies color corrections so that white objects appear neutral under any lighting. Auto Focus (AF), if your camera module supports it, analyses the sharpness of the image at different focus positions and continuously adjusts the lens to maximise sharpness. These algorithms are the reason you need that two-second warm-up period — they're running iteratively and need several frames of data before they converge on accurate settings.

---

## Layer 4: The Hardware

At the bottom of the stack is the physical hardware.

The **image sensor** is the component that actually converts light into electrical signals. On the Camera Module 3, this is the IMX708 sensor from Sony. Light enters through the lens, hits the sensor surface, and the photoelectric cells in the sensor generate electrical charges proportional to the amount of light they received. These charges are read out as raw digital values in what's called the **Bayer pattern** — a grid where each position records only red, green, or blue light (not all three). The human eye is more sensitive to green, so the Bayer pattern has twice as many green pixels as red or blue.

The **ISP (Image Signal Processor)** takes that raw Bayer data from the sensor and transforms it into the finished colour image you actually see. This is a sophisticated multi-stage process: **demosaicing** (reconstructing full colour at every pixel by interpolating from the surrounding Bayer cells), **colour space conversion** (transforming from camera-native colour coordinates to standard RGB), **scaling** (resizing to your requested output resolution), **noise reduction** (smoothing out graininess from sensor noise), and **sharpening** (enhancing edges). All of this happens in dedicated hardware rather than in software, which is why it can process 12-megapixel frames at 14 frames per second without overloading the CPU.

The **DMA (Direct Memory Access) controllers** handle moving image data between hardware components without involving the CPU. Once the ISP has finished processing a frame, the DMA controller moves the finished image into a memory buffer that your application can read. This is efficient because the CPU never has to copy those large image buffers — the DMA hardware handles the transfer while the CPU is free to run your Python code.

---

## The Four Major Usage Patterns

Now that you understand the architecture, here are the four patterns you'll encounter most in real applications, shown with their internal data flow:

**Pattern 1: Simple Still Capture** — The most common pattern. Start the camera, wait for auto-exposure to settle, grab a frame, save it, stop. The frame travels from the sensor through the ISP into the main stream buffer, then `capture_file()` reads that buffer and encodes it to JPEG.

**Pattern 2: Video Recording** — Create a video configuration, start an encoder alongside the camera, let it run for as long as needed, then stop the encoder and the camera. The encoder runs in a background thread, continuously reading frames from the encode stream and writing compressed data to a file.

**Pattern 3: Computer Vision with Preview** — Create a preview configuration with a main stream for processing and a display stream for showing the live feed. Your code reads from the main stream with `capture_array()` in a loop, while the preview window updates from the display stream in parallel. These happen simultaneously in different threads.

**Pattern 4: Multi-Stream Capture** — Use `capture_request()` to grab a single `CompletedRequest` object that contains all active streams at the same instant. Pull a high-resolution array from the main stream and a low-resolution array from the lores stream simultaneously, ensuring they represent exactly the same moment in time.

---

## The Class Inheritance Tree

For those who want to understand the object-oriented structure, here is the class hierarchy showing what inherits from what:

```
object (Python base class)
│
├── Picamera2                    ← The main class you use directly
│
├── Preview (Abstract Base)
│   ├── QtPreview
│   │   └── QtGlPreview          ← Qt with OpenGL acceleration
│   ├── DrmPreview               ← Headless / embedded systems
│   └── NullPreview              ← No display (testing / CI)
│
├── Encoder (Abstract Base)
│   ├── H264Encoder              ← Efficient video recording
│   ├── MJPEGEncoder             ← Motion JPEG recording
│   └── JpegEncoder              ← Still image encoding
│
├── Output (Abstract Base)
│   ├── FileOutput               ← Write to disk
│   ├── FfmpegOutput             ← Pipe through FFmpeg
│   └── CircularOutput           ← Ring-buffer (e.g. dashcam style)
│
├── CameraConfiguration          ← Dictionary-like config object
├── StreamConfiguration          ← Per-stream settings (libcamera binding)
├── Transform                    ← Flip/rotation data class
├── CompletedRequest             ← Wrapper around a captured libcamera request
└── Metadata                     ← Dictionary subclass for capture metadata
```

Abstract base classes (Preview, Encoder, Output) define a common interface that all subclasses must implement. This is what allows Picamera2 to treat `H264Encoder` and `MJPEGEncoder` interchangeably — they both implement the same encoder interface, just with different compression algorithms underneath.

---

## Key Design Insight: Everything Is a Stream

The single most important concept in the Picamera2 architecture is that **the camera is always streaming frames**, and different parts of your application consume those frames in different ways. When you understand this, a lot of the API design choices make immediate sense.

`capture_file()` consumes one frame from the main stream and saves it. `capture_array()` consumes one frame from the main stream and gives it to your Python code. An encoder continuously consumes every frame from the encode stream and compresses them. A preview continuously consumes every frame from the display stream and renders them on screen. Multiple consumers can be active simultaneously, each getting a copy of the same frames from their respective stream.

This stream-centric design is why the camera can be recording video, showing a live preview, and allowing you to grab numpy arrays for analysis — all at exactly the same time.

**Next: [04 — Practical Projects](04-projects.md)**
