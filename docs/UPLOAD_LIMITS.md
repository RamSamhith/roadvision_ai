# RoadVision — Upload System & Size Limits

This document details upload limits, file validation, storage lifecycle, and error behavior.

---

## 1. Configured Limits Summary

| Category | Limit Value | Enforcement Layer | Failure Status |
|---|---|---|---|
| **Max Image File Size** | 20 MB (20,971,520 bytes) | Streaming chunk counter | 413 Payload Too Large |
| **Max Image Dimensions** | 8192 × 8192 pixels | Pillow image header inspection | 422 Unprocessable Entity |
| **Supported Image Formats** | JPEG (`.jpg`, `.jpeg`), PNG (`.png`) | Extension & MIME header verify | 415 Unsupported Media Type |
| **Max Video File Size** | 200 MB (209,715,200 bytes) | Streaming chunk counter | 413 Payload Too Large |
| **Max Video Duration** | 60 seconds | OpenCV container header check | 422 Unprocessable Entity |
| **Max Video Resolution** | 1920 × 1080 (1080p) | OpenCV stream frame inspection | 422 Unprocessable Entity |
| **Supported Video Formats** | MP4 (`.mp4`), AVI (`.avi`) | Extension & container probe | 415 Unsupported Media Type |
| **Max Live Camera Session** | 10 minutes (600 seconds) | Background watchdog timer | Auto-finalizes session |
| **Concurrent Active Jobs** | 1 active job (exclusive lock) | In-process `JobSlot` | 409 Conflict |

---

## 2. Multi-Layer Validation Architecture

1. **Extension Screening**:
   - The file extension is parsed and converted to lowercase.
   - Non-compliant extensions fail immediately with HTTP 415.

2. **Streamed Content Storage**:
   - Files are saved in 1 MB chunks to `data/uploads_tmp/<uuid>.<ext>`.
   - If total written bytes exceed the limit, streaming halts immediately, the file is unlinked, and HTTP 413 is raised without buffering excess payload in RAM.

3. **Content & Format Deep Inspection**:
   - **Images**: Verified using Pillow `Image.open().verify()` and decoded via OpenCV `cv2.imread()`. Corrupt or spoofed files fail with HTTP 400.
   - **Videos**: Validated using OpenCV `cv2.VideoCapture()`. Container validity, stream decodability, frame count, FPS, and duration are inspected before queuing.

4. **Sanitized Output Storage**:
   - Annotated artifacts are saved to `data/outputs/` using timestamped UUID names (e.g. `20261108_125528_d583eef28d414026.jpg`).
   - Retrieval endpoints validate output names against strict regex `^[A-Za-z0-9_-]{8,64}\.(jpg|mp4)$`, completely blocking directory traversal attacks (`../`).

