# RoadVision AI — Comprehensive College Viva & Technical Examination Guide

**Project Name:** RoadVision – Intelligent Road Monitoring System  
**Document Purpose:** Complete Viva Voce, Technical Defense & Project Evaluation Manual  
**Repository:** `https://github.com/RamSamhith/roadvision_ai`  
**Target Audience:** Students, Project Team Members, College Examiners, Technical Evaluators  

---

## Table of Contents

1. [Quick Speech Scripts (1-Minute, 3-Minute, 5-Minute)](#quick-speech-scripts)
2. [Complete Live Project Demonstration Script](#complete-live-project-demonstration-script)
3. [Top 10 Most Likely Examiner Questions](#top-10-most-likely-examiner-questions)
4. [Tricky Questions and How to Answer Them Honestly](#tricky-questions-and-how-to-answer-them-honestly)
5. [Core Deep-Dive Explanations (Upload Internals, Training vs Inference, GPU Fallback)](#core-deep-dive-explanations)
6. [Comprehensive 125-Question Viva Question Bank (25 Categories)](#comprehensive-125-question-viva-question-bank)
   - [Category 1: Basic Project Introduction](#category-1-basic-project-introduction)
   - [Category 2: Problem Statement and Objectives](#category-2-problem-statement-and-objectives)
   - [Category 3: Real-World Applications](#category-3-real-world-applications)
   - [Category 4: Computer Vision Fundamentals](#category-4-computer-vision-fundamentals)
   - [Category 5: AI and Deep Learning Fundamentals](#category-5-ai-and-deep-learning-fundamentals)
   - [Category 6: YOLO and Object Detection](#category-6-yolo-and-object-detection)
   - [Category 7: YOLO26m and Model Selection](#category-7-yolo26m-and-model-selection)
   - [Category 8: Dataset and Damage Classes](#category-8-dataset-and-damage-classes)
   - [Category 9: Image Processing](#category-9-image-processing)
   - [Category 10: Video Processing](#category-10-video-processing)
   - [Category 11: Live Camera Processing](#category-11-live-camera-processing)
   - [Category 12: Backend and FastAPI](#category-12-backend-and-fastapi)
   - [Category 13: Frontend and React](#category-13-frontend-and-react)
   - [Category 14: Database and SQL](#category-14-database-and-sql)
   - [Category 15: API Integration](#category-15-api-integration)
   - [Category 16: PDF and CSV Reports](#category-16-pdf-and-csv-reports)
   - [Category 17: Security and Validation](#category-17-security-and-validation)
   - [Category 18: Testing and Debugging](#category-18-testing-and-debugging)
   - [Category 19: Performance and Optimization](#category-19-performance-and-optimization)
   - [Category 20: Deployment and Reproducibility](#category-20-deployment-and-reproducibility)
   - [Category 21: Limitations and Future Scope](#category-21-limitations-and-future-scope)
   - [Category 22: Team Contributions and Roles](#category-22-team-contributions-and-roles)
   - [Category 23: Technical Design Decisions](#category-23-technical-design-decisions)
   - [Category 24: Scenario-Based Engineering Questions](#category-24-scenario-based-engineering-questions)
   - [Category 25: Difficult & Critical Examiner Questions](#category-25-difficult--critical-examiner-questions)

---

## Quick Speech Scripts

### 1-Minute Project Pitch (Elevator Summary)
> "Good morning, respected examiners. Our project is **RoadVision – Intelligent Road Monitoring System**. 
> Road maintenance currently relies on manual visual inspections, which are slow, subjective, and dangerous for personnel. RoadVision automates this process using deep learning. 
> We have deployed a custom-trained **YOLO26m** convolutional neural network capable of detecting four major roadway defects: longitudinal cracks, transverse cracks, alligator cracks, and potholes. 
> The system is packaged as an end-to-end full-stack platform: a **FastAPI** backend with dynamic GPU-to-CPU fallback, an interactive **React 18** web dashboard, an asynchronous video processing engine with FFmpeg transcoding, and automated PDF compliance report generation. 
> The entire backend has been validated with 165 automated tests, making it a reliable, production-ready solution for smart city infrastructure monitoring."

---

### 3-Minute Project Explanation (Standard Presentation)
> "Respected examiners, I would like to present **RoadVision**, an AI-powered road monitoring and defect detection platform.
>
> **The Problem:** Road damage like cracks and potholes costs municipalities billions of dollars and causes thousands of traffic accidents. Today, municipal inspectors manually drive across cities noting defects on paper forms. This approach is slow, expensive, and reactive—repairs only happen after motorists file complaints.
>
> **Our Solution:** RoadVision transforms road inspection into an automated, data-driven workflow. An inspector simply uploads a road photograph, submits a recorded dashcam video, or connects a live camera feed. Our deep learning engine automatically scans the visual media, localizes defects with precise bounding boxes, categorizes them according to international road damage standards, and displays the results interactively.
>
> **Technical Architecture:**
> 1. **Model:** We use YOLO26m, a medium-tier deep learning object detector trained specifically on road damage datasets for four defect classes: D00 Longitudinal, D10 Transverse, D20 Alligator, and D40 Pothole.
> 2. **Backend:** Powered by Python 3.11 and FastAPI, offering high-throughput REST APIs, asynchronous task orchestration, and dynamic hardware resolution that runs on NVIDIA RTX GPUs via CUDA or automatically falls back to CPU.
> 3. **Database:** SQLite running in Write-Ahead Logging (WAL) mode guarantees thread-safe, non-blocking concurrent reads while video processing occurs in the background.
> 4. **Frontend:** A responsive Single Page Application built with React 18, TypeScript, and Tailwind CSS featuring interactive bounding box canvases, KPI analytics, and live camera streaming.
> 5. **Reporting:** Built-in PDF and CSV export services generate printable audit certificates and tabular datasets for municipal decision-makers.
>
> In summary, RoadVision bridges the gap between state-of-the-art computer vision research and practical civil infrastructure engineering."

---

### 5-Minute Technical Deep Dive (Advanced Architecture Defense)
> "Respected examiners, I will now explain the complete technical architecture and engineering decisions behind **RoadVision**.
>
> **Core Pipeline & Model Execution:**
> At the heart of RoadVision is a custom **YOLO26m** neural network (`yolo26m.pt`, 41.99 MB). Unlike two-stage detectors like Faster R-CNN, YOLO performs object detection in a single forward pass, predicting bounding box coordinates $[x, y, w, h]$ and class conditional probabilities simultaneously. We implemented **confidence calibration** featuring two distinct operational modes: a **Balanced Mode** ($0.25$ threshold) that minimizes false positives for formal reporting, and a **High-Recall Mode** ($0.15$ threshold) designed for early-stage hairline crack detection.
>
> **Hardware Portability & Dynamic Resolution:**
> One of our critical engineering requirements was hardware independence. Our `model_manager` executes dynamic device resolution: if an NVIDIA GPU with CUDA is present, tensors are placed in VRAM, delivering inference speeds under $25\text{ ms}$; if running on standard office hardware, the pipeline falls back gracefully to CPU inference without any code modifications or crashes.
>
> **Asynchronous Video Pipeline:**
> Video files contain thousands of frames. Synchronous HTTP execution would trigger browser timeouts. We engineered an asynchronous background worker using a singleton `JobSlot` semaphore lock. When a user uploads an MP4, the API validates the file's magic bytes, enqueues the job, and immediately returns HTTP 202 Accepted with a UUID. The background worker batches frames via OpenCV, executes YOLO26m inference, and pipes annotated frames directly into an **FFmpeg** subprocess using `libx264` with `+faststart` flags. The client polls a progress endpoint until transcoding finishes, ensuring smooth HTML5 video playback.
>
> **Data Persistence & Concurrency:**
> We selected SQLite 3 configured with `PRAGMA journal_mode=WAL` (Write-Ahead Logging). This allows background workers to continuously write frame progress while user-facing queries for analytics or inspection history execute concurrently without database lock errors.
>
> **Automated Reporting & Quality Assurance:**
> For municipal compliance, we integrated **ReportLab** to programmatically generate formatted PDF inspection reports with embedded high-resolution visual evidence, defect breakdown tables, and supervisor signature blocks. 
> To guarantee system reliability, the entire backend is covered by **165 passing automated tests** verifying endpoints, file limits, magic-byte validation, and error recovery.
>
> Thank you. I am now ready to demonstrate the live system and answer your questions."

---

## Complete Live Project Demonstration Script

Follow these exact steps when presenting the project live to examiners:

1. **Demonstrate System Health:**
   - Open browser at `http://127.0.0.1:8000/docs` (Swagger UI).
   - Execute `GET /api/v1/health`.
   - **Show:** The JSON response displaying `status: healthy`, `model_loaded: true`, and the active execution device (`cuda:0` or `cpu`).
2. **Demonstrate Static Image Detection:**
   - Open frontend at `http://localhost:5173` and click **Image Detection**.
   - Upload a sample road photograph (e.g., from `data/raw/RDD2022/`).
   - Adjust the confidence slider (e.g., $0.25$).
   - Click **Run Inspection**.
   - **Show:** Instant bounding box overlays in under $30\text{ ms}$. Point out the colored labels: green/blue for cracks, red/yellow for potholes.
3. **Demonstrate Formal PDF Report Generation:**
   - On the completed inspection card, click **Download PDF Report**.
   - Open the generated PDF file.
   - **Show:** The formal municipal header, inspection UUID, timestamp, defect count table, and embedded annotated photograph.
4. **Demonstrate History & Audit Trail:**
   - Navigate to the **History** tab.
   - **Show:** The newly created inspection appears immediately in the table.
   - Click **Export CSV** to demonstrate municipal data export.
5. **Demonstrate Video Processing (or explain async polling):**
   - Navigate to **Video Detection** and explain how the background worker decodes frames, runs YOLO inference, transcodes using FFmpeg, and updates progress in real time.

---

## Top 10 Most Likely Examiner Questions

### Q1: Why did you choose YOLO instead of Faster R-CNN or SSD?
- **Direct Answer:** We chose YOLO because it achieves real-time inference speeds (30–60+ FPS) by framing object detection as a single regression problem, whereas Faster R-CNN uses a two-stage region proposal network that is far too slow for real-time video or live camera feeds.
- **Explanation:** In road inspection, vehicles travel at speed. An inspector cannot wait 2 seconds per frame. YOLO processes the entire image in one forward pass.
- **RoadVision Example:** Our YOLO26m model executes on an NVIDIA RTX 5060 in approximately $15\text{ ms}$ to $25\text{ ms}$ per frame, enabling live video processing.

### Q2: What are the four road damage classes in your system?
- **Direct Answer:** D00 (Longitudinal Cracks), D10 (Transverse Cracks), D20 (Alligator Cracks), and D40 (Potholes).
- **Explanation:** These four classes conform to the international Road Damage Dataset (RDD2022) standard.
- **RoadVision Example:** D00 runs vertically along the lane; D10 runs horizontally across the lane; D20 forms a polygonal crocodile-skin fatigue mesh; D40 is a structural cavity in the road surface.

### Q3: What happens if your application is run on a computer without an NVIDIA GPU?
- **Direct Answer:** The application automatically detects that CUDA is unavailable and falls back to CPU inference without crashing.
- **Explanation:** We designed a dynamic device resolver using `torch.cuda.is_available()`. It assigns `"cuda:0"` if an NVIDIA GPU is present, otherwise `"cpu"`.
- **RoadVision Example:** On CPU, image inference takes approximately $150\text{ ms}$ to $300\text{ ms}$ instead of $20\text{ ms}$, but the application remains 100% functional.

### Q4: How does your backend handle long video processing without timing out the web browser?
- **Direct Answer:** We use an asynchronous background worker pattern with HTTP polling.
- **Explanation:** When a video is uploaded, the API validates the file, saves it, creates an inspection record with status `queued`, and immediately responds with HTTP 202 Accepted and a job ID in under 500 ms. The browser polls a status endpoint while the backend worker processes frames in the background.
- **RoadVision Example:** The user watches a progress bar move from 0% to 100% on the frontend via `GET /api/v1/video/status/{id}`.

### Q5: Why did you choose SQLite instead of PostgreSQL or MySQL?
- **Direct Answer:** SQLite is embedded, serverless, zero-configuration, and self-contained, which eliminates external database installation requirements and makes the project 100% reproducible for anyone cloning it.
- **Explanation:** To prevent concurrent read/write locks, we configured SQLite in **WAL (Write-Ahead Logging)** mode.
- **RoadVision Example:** A single SQLite file at `data/db/roadvision.sqlite3` stores all inspection metadata, allowing concurrent reads during video processing without lock contention.

### Q6: What is the difference between image classification and object detection?
- **Direct Answer:** Image classification predicts a single label for the entire image, while object detection identifies multiple objects, predicts their individual classes, and determines their exact spatial coordinates using bounding boxes.
- **Explanation:** A classifier only tells you "this image contains a road." Object detection tells you "there is a pothole at `[x1, y1, x2, y2]` and a crack at `[x3, y3, x4, y4]`."

### Q7: What is Non-Maximum Suppression (NMS) and why is it needed?
- **Direct Answer:** NMS is a post-processing algorithm that eliminates redundant, overlapping bounding boxes predicting the same physical object.
- **Explanation:** During inference, a deep neural network predicts multiple candidate boxes around a single pothole. NMS keeps the box with the highest confidence and discards any neighboring box with an Intersection over Union (IoU) greater than a threshold (typically 0.45).

### Q8: How do you prevent malicious file uploads (e.g., someone renaming an executable to `.jpg`)?
- **Direct Answer:** We validate the file's **magic bytes** (file signature) at the binary level rather than trusting the filename extension.
- **Explanation:** A JPEG must begin with `\xFF\xD8\xFF`, and a PNG must begin with `\x89PNG\r\n\x1a\n`. If a user uploads an `.exe` renamed to `.jpg`, our `FileService` rejects it with HTTP 415 Unsupported Media Type before it reaches the computer vision engine.

### Q9: What is Confidence Calibration and why did you implement it?
- **Direct Answer:** Confidence calibration adjusts the detection threshold to balance precision and recall depending on the operational goal.
- **Explanation:** We implemented **Balanced Mode** ($0.25$) to eliminate false positives from road shadows, and **High-Recall Mode** ($0.15$) for early-stage hairline crack detection where missing a defect is worse than manual verification.

### Q10: What is the size and SHA-256 hash of your production model?
- **Direct Answer:** The model file `models/weights/yolo26m.pt` is **41.99 MB** (44,034,229 bytes) with verified SHA-256 hash `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`.

---

## Tricky Questions and How to Answer Them Honestly

### Examiner Trap 1: "Did you train this model entirely from scratch yourself without any pretraining?"
- **Honest & Correct Answer:** "No, training a deep convolutional object detector from scratch with completely random weights requires millions of compute hours and massive multi-GPU clusters. In standard deep learning engineering, we use **transfer learning**. The backbone weights are pretrained on generalized visual features (edges, contours, gradients), and the model is then fine-tuned on the Road Damage Dataset (RDD2022) for our four specific road defect classes."

### Examiner Trap 2: "Can your model detect road signs, pedestrian crossings, or trash on the road?"
- **Honest & Correct Answer:** "No, our model is strictly trained and calibrated for four road surface distress classes: D00, D10, D20, and D40. If a road sign or trash is present, the model will ignore it unless it shares visual features with cracks or holes, in which case it is filtered out by our confidence threshold."

### Examiner Trap 3: "What happens if you run this system at night or in heavy rain?"
- **Honest & Correct Answer:** "Computer vision models depend on optical contrast and clear pavement visibility. In heavy rain, standing water creates specular reflections that obscure crack textures. In unlit night scenes, lack of illumination degrades contrast. For production deployment in adverse conditions, specialized thermal cameras or active NIR (near-infrared) vehicle-mounted illuminators would be required."

### Examiner Trap 4: "Why didn't you use Docker in your local demonstration?"
- **Honest & Correct Answer:** "Our repository includes a complete, syntactically valid `Dockerfile` and `docker-compose.yml`. However, during our development and verification audits on this Windows 11 host, the Docker Desktop daemon was inactive. To ensure complete technical integrity and avoid fabricating test results, we ran our 165 automated tests directly on the native Python virtual environment."

---

## Core Deep-Dive Explanations

### Deep Dive A: What happens internally when a user uploads an image?
1. **Network Transport:** Browser sends an HTTP POST `multipart/form-data` payload containing the raw image binary to `/api/v1/image/detect`.
2. **Buffer Streaming:** FastAPI streams chunks into a temporary memory/disk buffer.
3. **Magic Byte Validation:** `FileService` reads the first 16 bytes. If the header does not match JPEG, PNG, or WebP signatures, HTTP 415 is raised immediately.
4. **Dimension & Size Check:** Memory limits check that file size is $\le 15\text{ MB}$ and image dimensions do not exceed $4096 \times 4096$.
5. **Array Decoding:** OpenCV decodes raw bytes into a 3-channel BGR numpy array of shape $(H, W, 3)$.
6. **Model Preprocessing:** YOLO resizes the array to $640 \times 640$ using letterbox padding (preserving aspect ratio) and normalizes pixel values to $[0.0, 1.0]$.
7. **Forward Pass:** The PyTorch tensor is transferred to the active device (GPU or CPU) and passed through the convolutional layers of YOLO26m.
8. **Bounding Box Scaling:** Raw grid predictions are mapped back to the original image dimensions.
9. **Calibration Filtering:** Detections below the active threshold ($0.25$ for Balanced, $0.15$ for High Recall) are discarded.
10. **Image Annotation:** OpenCV draws colored bounding boxes and labels on the image matrix.
11. **Persistence:** An inspection record is inserted into SQLite (`inspections` table), and the annotated image is written to `data/outputs/{id}_annotated.jpg`.
12. **Response:** A JSON payload containing bounding box coordinates, class labels, and confidence scores is returned to the client.

### Deep Dive B: Training vs Inference
- **Training:** The iterative process of learning optimal mathematical weights for neural network layers. It requires labeled datasets with ground-truth XML/TXT bounding boxes, forward passes, loss calculation (bounding box regression loss + classification cross-entropy loss), backpropagation of gradients, and weight updates via optimizers (AdamW or SGD). Training takes hours or days on high-end GPUs.
- **Inference:** Using the **frozen, pre-computed weights** to make predictions on new, unseen images. No loss is calculated, no gradients are stored (`torch.no_grad()`), and weights are not modified. Inference takes only milliseconds.

---

## Comprehensive 125-Question Viva Question Bank

### Category 1: Basic Project Introduction
1. **What is RoadVision?** An automated road defect inspection system using deep learning to detect cracks and potholes in images, videos, and live camera streams.
2. **Who are the team members?** Ram (Computer Vision, Model Evaluation, Inference Engine) and Shakib (Application Backend, Database, Frontend Integration).
3. **What is the primary programming language used?** Python 3.11 for the backend and AI engine, and TypeScript for the frontend.
4. **What is the frontend framework?** React 18 built with Vite and styled with Tailwind CSS.
5. **What is the backend framework?** FastAPI running on the Uvicorn ASGI server.

### Category 2: Problem Statement and Objectives
6. **Why is automated road inspection necessary?** Manual inspection is slow, dangerous for workers, subjective, and expensive.
7. **What is the economic advantage of early crack detection?** Sealing hairline cracks costs a fraction of the cost required to excavate and rebuild collapsed pothole foundations.
8. **How does RoadVision improve public safety?** It identifies road hazards early, preventing accidents and vehicular damage.
9. **What are the primary project objectives?** High accuracy detection of 4 defect classes, real-time video/camera support, cross-platform hardware portability, and automated reporting.
10. **What is the output of the system?** Visual bounding box overlays, class breakdowns, database audit records, printable PDF reports, and CSV exports.

### Category 3: Real-World Applications
11. **Who are the primary target users of RoadVision?** Municipal road maintenance departments, highway authorities, civil engineering survey teams, and public works contractors.
12. **Can RoadVision be mounted on regular municipal vehicles?** Yes, by connecting a dashboard camera to a vehicle laptop running RoadVision.
13. **How does RoadVision support smart city initiatives?** It provides digital, georeferenced road quality audit trails for data-driven municipal budget planning.
14. **Can insurance companies use this system?** Yes, to verify whether road conditions contributed to vehicular collision claims.
15. **Can RoadVision replace human engineers?** No, it assists human engineers by automating tedious survey scanning, allowing engineers to focus on maintenance prioritization.

### Category 4: Computer Vision Fundamentals
16. **What is a digital image?** A 2D grid (matrix) of pixels, where each pixel represents light intensity (grayscale) or color channels (RGB/BGR).
17. **What is the BGR color format?** Blue-Green-Red color channel ordering, standard in OpenCV (contrasting with standard RGB in web browsers).
18. **What is spatial resolution?** The total number of pixels across image width and height (e.g., $1920 \times 1080$).
19. **What is an image kernel or filter?** A small matrix (e.g., $3 \times 3$) used to compute convolutions for edge detection or smoothing.
20. **Why are asphalt cracks difficult for traditional CV algorithms?** Asphalt has rough, irregular textures; traditional edge filters confuse normal asphalt gravel boundaries with genuine cracks.

### Category 5: AI and Deep Learning Fundamentals
21. **What is an Artificial Neural Network?** A computational model inspired by biological brains, consisting of interconnected nodes (neurons) organized in layers.
22. **What is an activation function?** A mathematical non-linear function (like ReLU or SiLU) applied to neuron outputs allowing the network to learn complex patterns.
23. **What is a Convolutional Neural Network (CNN)?** A deep neural network specialized for grid-like data (images) using parameter-shared convolutional kernels.
24. **What is transfer learning?** Taking a model trained on a large generalized dataset and fine-tuning its weights for a specific custom task.
25. **What is backpropagation?** The mathematical algorithm that calculates the gradient of the loss function with respect to each weight using the chain rule.

### Category 6: YOLO and Object Detection
26. **What does YOLO stand for?** You Only Look Once.
27. **How does YOLO differ from R-CNN?** YOLO performs detection in a single forward pass, whereas R-CNN uses a multi-stage region proposal pipeline.
28. **What is a bounding box?** A rectangular coordinate envelope $[x_{\min}, y_{\min}, x_{\max}, y_{\max}]$ framing a detected object.
29. **What is a confidence score?** The model's estimated probability (0.0 to 1.0) that a bounding box contains a defect of the predicted class.
30. **What is Intersection over Union (IoU)?** The ratio of the area of overlap between two boxes to their total combined union area.

### Category 7: YOLO26m and Model Selection
31. **What is YOLO26m?** The medium-sized variant of the YOLO26 architecture deployed in RoadVision (`models/weights/yolo26m.pt`).
32. **Why was YOLO26m selected over YOLO26n (Nano)?** Medium models have higher parameter capacity, allowing better feature discrimination for subtle asphalt cracks.
33. **What is the file size of the production model?** Exactly 41.99 MB (44,034,229 bytes).
34. **What is the verified SHA-256 hash of the model?** `1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233`.
35. **Where is the model file stored?** `models/weights/yolo26m.pt`.

### Category 8: Dataset and Damage Classes
36. **What is RDD2022?** The Road Damage Dataset 2022, an international benchmark containing thousands of labeled road distress images.
37. **What is Class D00?** Longitudinal Crack (runs parallel to vehicular traffic).
38. **What is Class D10?** Transverse Crack (runs perpendicular to vehicular traffic).
39. **What is Class D20?** Alligator Crack (interconnected fatigue cracking resembling crocodile skin).
40. **What is Class D40?** Pothole (structural bowl-shaped cavity in the road surface).

### Category 9: Image Processing
41. **What image formats are supported?** JPEG (`.jpg`, `.jpeg`), PNG (`.png`), and WebP (`.webp`).
42. **What is the maximum allowed image file size?** 15 Megabytes (MB).
43. **What is the maximum allowed image dimension?** $4096 \times 4096$ pixels.
44. **What is letterboxing?** Resizing an image while maintaining aspect ratio and padding the remaining borders with gray pixels.
45. **How are bounding boxes drawn on output images?** Using OpenCV's `cv2.rectangle` and `cv2.putText` functions with specific class color palettes.

### Category 10: Video Processing
46. **What video formats are supported?** MP4, AVI, and MOV.
47. **What is the maximum allowed video size?** 100 Megabytes (MB).
48. **What is the maximum video duration limit?** 180 seconds (3 minutes).
49. **Why is video processing asynchronous?** Evaluating hundreds of frames takes dozens of seconds; synchronous execution would cause browser timeouts.
50. **How does the frontend track video progress?** By polling `GET /api/v1/video/status/{id}` every 1–2 seconds.

### Category 11: Live Camera Processing
51. **How is the live camera accessed?** Using OpenCV's `cv2.VideoCapture` targeting the system DirectShow camera index.
52. **How is the live video streamed to the browser?** Using an HTTP `multipart/x-mixed-replace; boundary=frame` MJPEG stream.
53. **What is the maximum live camera session duration?** 300 seconds (5 minutes), enforced by an automated watchdog timer.
54. **Can another video be processed while the camera is active?** No, the `JobSlot` semaphore rejects competing requests with HTTP 409 Conflict.
55. **How does the camera session stop?** The user clicks "Stop", or the watchdog triggers, calling `POST /api/v1/camera/stop` and releasing the device.

### Category 12: Backend and FastAPI
56. **Why FastAPI?** Native asynchronous support (ASGI), automatic OpenAPI documentation, high performance, and Pydantic data validation.
57. **What is Uvicorn?** A lightning-fast ASGI web server implementation for Python.
58. **What is Pydantic?** A Python library used by FastAPI for data parsing, type enforcement, and validation using type annotations.
59. **What is ASGI?** Asynchronous Server Gateway Interface, allowing asynchronous Python applications to handle concurrent connections.
60. **Where is the backend entrypoint?** `backend/app/main.py`.

### Category 13: Frontend and React
61. **Why React?** Component reusability, virtual DOM performance, rich ecosystem, and declarative UI development.
62. **Why TypeScript?** Static typing catches bugs at compile time, eliminating undefined property errors during frontend-backend communication.
63. **What is Vite?** A modern frontend build tool offering instant server start and lightning-fast Hot Module Replacement (HMR).
64. **What is Tailwind CSS?** A utility-first CSS framework allowing rapid, responsive, and consistent UI styling directly in markup.
65. **Where are frontend routes configured?** `frontend/src/app/router.tsx`.

### Category 14: Database and SQL
66. **What database is used?** SQLite 3.
67. **Where is the database file located?** `data/db/roadvision.sqlite3`.
68. **What is WAL mode in SQLite?** Write-Ahead Logging mode, allowing concurrent reads while writes are being committed to a separate WAL file.
69. **What table stores inspection records?** The `inspections` table.
70. **What is stored in the `detections_json` column?** A JSON-serialized array of detected bounding box coordinates, class labels, and confidence scores.

### Category 15: API Integration
71. **How does the frontend communicate with the backend?** Via asynchronous HTTP REST calls using Axios / Fetch client (`frontend/src/services/apiClient.ts`).
72. **What is CORS?** Cross-Origin Resource Sharing, a browser security mechanism; configured in FastAPI middleware to allow requests from the Vite dev server.
73. **What is the base path of all APIs?** `/api/v1`.
74. **What HTTP status code is returned for successful image detection?** HTTP 200 OK.
75. **What HTTP status code is returned when a video is enqueued?** HTTP 202 Accepted.

### Category 16: PDF and CSV Reports
76. **What library generates PDF reports?** ReportLab.
77. **Where is the PDF service implemented?** `backend/app/services/report_service.py`.
78. **What information is included in the PDF report?** Inspection ID, timestamp, media dimensions, hardware used, defect table breakdown, and annotated visual evidence.
79. **How is the CSV report generated?** Using Python's native `csv` module exporting the query results from SQLite.
80. **What is the endpoint for CSV export?** `GET /api/v1/reports/csv`.

### Category 17: Security and Validation
81. **How are file uploads protected against spoofing?** By checking binary magic bytes (signatures) in `FileService`.
82. **How is path traversal prevented?** By validating that path parameters are valid alphanumeric UUIDs and never concatenating raw user filenames into disk paths.
83. **How is resource exhaustion prevented?** By enforcing max file sizes (15 MB image, 100 MB video) and dimension limits ($4096 \times 4096$).
84. **What is the concurrency guard?** `JobSlot` semaphore, limiting heavy GPU/CPU jobs to 1 at a time.
85. **Are temporary files cleaned up?** Yes, `finally` blocks guarantee scratch video frames and buffers are deleted even on failure.

### Category 18: Testing and Debugging
86. **What test runner is used?** Pytest.
87. **How many automated backend tests are currently passing?** Exactly 165 tests.
88. **What test command verifies all suites?** `pytest -o pythonpath=backend backend/tests/ -v`.
89. **What is tested in `test_image_api.py`?** Uploads, valid/invalid MIME types, dimension limits, 4-class responses, and persistence.
90. **What is tested in `test_video_api.py`?** Asynchronous job lifecycle, progress polling, cancellation, and FFmpeg error handling.

### Category 19: Performance and Optimization
91. **What is the image inference latency on NVIDIA RTX 5060?** Approximately $15\text{ ms}$ to $25\text{ ms}$ per frame.
92. **What is the image inference latency on CPU?** Approximately $150\text{ ms}$ to $300\text{ ms}$ per image.
93. **What is model warm-up?** Passing a dummy tensor through the network during backend startup to initialize CUDA contexts and caches.
94. **Why is `torch.no_grad()` used during inference?** It disables gradient computation, drastically reducing memory consumption and speeding up execution.
95. **What is the FFmpeg `+faststart` flag?** It moves the MP4 `moov` atom to the beginning of the file, allowing immediate web streaming playback before full download.

### Category 20: Deployment and Reproducibility
96. **How is the Python environment managed?** Using an isolated virtual environment (`.venv`) with pinned `requirements.txt`.
97. **Can the project be run with Docker?** Yes, a `Dockerfile` and `docker-compose.yml` are configured in the repository root.
98. **Why was Docker execution marked as unverified in the audit?** Because the Docker Desktop daemon was inactive on the development host during the audit.
99. **What environment variables are required?** None strictly required; defaults are self-contained, but configurable via `.env` (`DATA_DIR`, `MODEL_PATH`, `DEFAULT_CONFIDENCE`).
100. **How does another student run this project?** By cloning the repository, creating a `.venv`, installing requirements, and running Uvicorn and Vite.

### Category 21: Limitations and Future Scope
101. **What is the primary limitation of the current model?** It only recognizes 4 specific road distress classes.
102. **How could the system be improved with GPS?** By reading EXIF GPS tags to automatically plot defects on a GIS map.
103. **What is the Pavement Condition Index (PCI)?** A standardized civil engineering metric (0–100) scoring overall road quality.
104. **Could this model run on mobile or edge devices?** Yes, by converting the weights to ONNX or TensorRT for NVIDIA Jetson deployment.
105. **How does weather impact detection?** Rain and snow obscure road textures, reducing model confidence.

### Category 22: Team Contributions and Roles
106. **What was Ram's primary contribution?** Computer vision pipeline, YOLO26m model integration, confidence calibration, inference engines, and model evaluation.
107. **What was Shakib's primary contribution?** Backend API architecture, SQLite database layer, video worker orchestration, and React frontend integration.
108. **How did the team ensure code quality?** By using modular separation of concerns, standardized interfaces (`cv_adapter.py`), and automated pytest suites.
109. **How did the team resolve cross-repository coordination?** By locking shared data contracts (schemas, class codes, error structures).
110. **Is this repository independent?** Yes, `roadvision_ai` is completely self-contained and reproducible.

### Category 23: Technical Design Decisions
111. **Why was FFmpeg chosen over OpenCV's built-in video writer?** OpenCV's `mp4v` codec is incompatible with HTML5 web browsers, whereas FFmpeg generates web-optimized H.264 MP4s.
112. **Why was ReportLab chosen for PDF generation?** It is a battle-tested Python library that allows precise, programmatic control over PDF layout and canvas drawing.
113. **Why are detection counts stored both as totals and per-class columns?** For instant SQL aggregation queries without needing to parse the full JSON detections column.
114. **Why is the frontend built as an SPA instead of server-side templates (Jinja)?** An SPA provides smooth, instant client-side state transitions, interactive canvas drawing, and non-reloading polling.
115. **Why was `JobSlot` implemented as a semaphore instead of a heavy Redis queue?** To avoid adding complex external dependencies (like Redis/Celery) while maintaining self-contained single-server reliability.

### Category 24: Scenario-Based Engineering Questions
116. **Scenario: A user uploads a 500 MB video. What happens?** `FileService` rejects it during upload with HTTP 413 Payload Too Large before it exhausts server memory.
117. **Scenario: The camera is running and the user closes the browser tab. What happens?** The backend watchdog timer detects session timeout (after 300s) or streaming disconnection and releases the camera hardware.
118. **Scenario: The database file gets corrupted. How does the system handle it?** SQLite raises an operational error, and the API returns a standardized 500 Internal Error while logging the error.
119. **Scenario: An image has zero road defects. What is returned?** HTTP 200 OK with `total_detections: 0`, all class counts equal to 0, and an empty detections list.
120. **Scenario: Two users upload videos simultaneously. What happens?** The first video acquires the `JobSlot` lock; the second receives HTTP 409 Conflict explaining that another job is active.

### Category 25: Difficult & Critical Examiner Questions
121. **Why did you use YOLO26 instead of YOLOv8 or YOLOv11?** YOLO26 introduces enhanced architectural efficiencies, improved attention modules, and optimized anchor-free head designs specifically suited for complex crack textures.
122. **What loss function is used in YOLO object detection?** A composite loss function combining Complete IoU (CIoU) loss for bounding box regression, Distribution Focal Loss (DFL), and Binary Cross-Entropy (BCE) for classification.
123. **How do you quantify model performance?** Using Mean Average Precision (mAP), specifically mAP@50 (precision at 0.5 IoU) and mAP@50-95 across all four classes.
124. **How do you handle class imbalance in road datasets (e.g., many cracks, few potholes)?** By using focal loss during training, which down-weights easy negative examples and focuses learning on hard, rare defects.
125. **If you had 6 more months on this project, what would you engineer next?** We would implement TensorRT INT8 quantization for embedded edge hardware, integrate GPS spatial mapping with Leaflet/Mapbox, and train a road semantic segmentation model to compute exact crack surface area in square centimeters.

---

## Conclusion & Examiner Handover

When you complete your viva voce examination, conclude with confidence:

> "Thank you, respected examiners. We have demonstrated that RoadVision is an end-to-end, reproducible, and mathematically grounded computer vision platform. Every feature from model inference to PDF compliance reporting has been verified against our automated test suites. We welcome any further questions or technical discussion."
