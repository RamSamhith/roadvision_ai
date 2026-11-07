"""RoadVision AI — Targeted PDF Page-Level Correction Tool.

Performs precise, targeted page-level replacement on:
docs/integration/ROADVISION_SHAKIB_FINAL_INTEGRATION_HANDOFF.pdf

Preserves:
- Visual identity, typography, colors, running headers, running footers ("Page X of 15").
- Untouched pages: Page 1 (Cover), Page 2 (TOC), Page 3 (Executive Overview),
  Page 5 (Defect Register), Page 11 (Demarcation Matrix), Page 12 (Architecture Diagram),
  Page 13 (Checklist).

Corrects:
- Page 4: Dataset acquisition vs prepared pairs vs split counts; Validation vs Test mAP metrics.
- Page 6: Exact method signatures and types matching backend/app/services/vision/service.py.
- Page 7: JSON response schema matching actual VisionInspectionResult / DetectionResult mapping.
- Page 8: FastAPI lifespan (no VisionServiceConfig), non-blocking run_in_threadpool image endpoint.
- Page 9: Comprehensive VideoJob worker explaining all states, cancellation, cleanup, and metadata.
- Page 10: Valid FastAPI exception handlers (no tuple decorator) and complete compilable React Video component.
- Page 14: Step 1 command with service.get_status().
- Page 15: Exact confidence policy ([0.10, 0.90] in config and clamp range; Shakib API 422 boundary).
"""

import os
import sys
from pathlib import Path
import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------
# Page-Specific Numbered Canvas to enforce exact target page numbering
# ----------------------------------------------------------------------
class SpecificPageCanvas(canvas.Canvas):
    target_page_number = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def showPage(self):
        self.draw_page_decorations()
        super().showPage()

    def draw_page_decorations(self):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header
        self.drawString(
            54,
            11 * 72 - 36,
            "RoadVision AI — Final Computer Vision Subsystem & Shakib Integration Handoff",
        )
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 11 * 72 - 40, 8.5 * 72 - 54, 11 * 72 - 40)

        # Running Footer
        page_str = f"Page {self.target_page_number} of 15"
        self.drawRightString(8.5 * 72 - 54, 32, page_str)
        self.drawString(
            54,
            32,
            "Confidential & Authoritative — Model: YOLO26m (640px) | Checksum: 1BC41287...D233",
        )
        self.line(54, 42, 8.5 * 72 - 54, 42)

        self.restoreState()


def get_styles():
    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    ACCENT = colors.HexColor("#2563EB")     # Blue 600
    DARK_BLUE = colors.HexColor("#1E3A8A")  # Blue 900
    TEXT_MAIN = colors.HexColor("#1E293B")  # Slate 800
    CODE_BG = colors.HexColor("#0F172A")    # Dark slate
    CODE_FG = colors.HexColor("#E2E8F0")    # Light slate

    h1_style = ParagraphStyle(
        "CorrH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=0,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "CorrH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=DARK_BLUE,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "CorrBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.2,
        leading=11.5,
        textColor=TEXT_MAIN,
        spaceAfter=4,
    )

    bullet_style = ParagraphStyle(
        "CorrBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "CorrCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.2,
        leading=8.0,
        textColor=CODE_FG,
    )

    tbl_cell = ParagraphStyle(
        "CorrTblCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=9.5,
        textColor=TEXT_MAIN,
    )

    tbl_cell_bold = ParagraphStyle(
        "CorrTblCellBold",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
    )

    tbl_cell_header = ParagraphStyle(
        "CorrTblCellHdr",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    return {
        "h1": h1_style, "h2": h2_style, "body": body_style,
        "bullet": bullet_style, "code": code_style, "cell": tbl_cell,
        "cell_bold": tbl_cell_bold, "cell_hdr": tbl_cell_header,
        "DARK_BLUE": DARK_BLUE, "PRIMARY": PRIMARY, "CODE_BG": CODE_BG,
        "BORDER_LIGHT": colors.HexColor("#E2E8F0"), "BG_LIGHT": colors.HexColor("#F8FAFC"),
    }


def escape_code(text: str) -> str:
    """Escape XML entities for ReportLab Paragraph code blocks."""
    # Escape & first, then < and >
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    # Preserve newlines and leading whitespace
    return text.replace("\n", "<br/>").replace(" ", "&nbsp;")


def generate_single_page_pdf(story, output_path: Path, page_num: int):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    class CustomCanvas(SpecificPageCanvas):
        target_page_number = page_num

    doc.build(story, canvasmaker=CustomCanvas)


def create_page_4_story(s):
    story = []
    story.append(Paragraph("2. Summary of Ram's Completed Work & Verified Benchmarks", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Ram's engineering responsibilities encompass all machine learning modeling, computer vision pipelines, inference engines, video processing, output annotation, FFmpeg encoding, and CV verification. The following milestones have been completely delivered:",
        s["body"]
    ))

    story.append(Paragraph("Delivered Components & Verified Dataset Numbers", s["h2"]))
    story.append(Paragraph(
        "• <b>Dataset Acquisition vs. Prepared Splits:</b> Acquired <b>47,420</b> raw images across 6 country subsets; <b>38,385</b> carry XML annotations (65,712 raw bounding boxes). Under Policy A ({D00, D10, D20, D40} in-scope classes with ≥1 valid box), exactly <b>23,767</b> eligible image/label pairs were prepared with <b>55,006</b> target annotations. Partitioned into stratified splits: <b>Train:</b> 19,017 images (80.01%), <b>Val:</b> 2,401 images (10.10%), <b>Held-out Test:</b> 2,349 images (9.88%). Manifest verified: <code>split_manifest.csv</code> (SHA-256: <code>7cf34087b2efee5ff5988d600f79ece891cc66acf0e7589a02b6dc2dab1b569e</code>).",
        s["bullet"]
    ))
    story.append(Paragraph(
        "• <b>Model Training & Dual Metric Verification (Val vs. Test):</b> Trained YOLO26m (20.35M params, 68.1 GFLOPs fused) for 50 epochs on RDD2022. <b>Validation Metrics (S4-T5, Best Epoch 45/49):</b> mAP@50 = <b>0.630</b> (63.0%), mAP@50-95 = <b>0.324</b> (32.4%), Precision = 0.682, Recall = 0.574. <b>Held-Out Test Metrics (S4-T6 Independent Evaluation on 2,349 unseen images):</b> mAP@50 = <b>0.619</b> (61.9%), mAP@50-95 = <b>0.320</b> (32.0%), Precision = 0.670, Recall = 0.564. The test vs. val drop is only <b>-1.1 pp</b> on mAP@50, proving strong generalization without data leakage. Promoted to <code>models/weights/yolo26m.pt</code> (SHA-256: <code>1BC41287...D233</code>).",
        s["bullet"]
    ))
    story.append(Paragraph(
        "• <b>832px Resolution Experiment:</b> Evaluated 832px input resolution against baseline 640px. Confirmed 832px increases forward pass latency by 69% without statistically significant mAP improvement; retained 640px as production standard.",
        s["bullet"]
    ))
    story.append(Paragraph(
        "• <b>CV Subsystem Architecture:</b> Delivered thread-safe ModelManager, ImageEngine, VideoEngine with monotonic watchdog timeout, stderr pipe drain, and mid-stream cancellation with partial file unlinking.",
        s["bullet"]
    ))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Hardware Verification Benchmarks (NVIDIA RTX 5060 Laptop GPU)", s["h2"]))

    bench_data = [
        [Paragraph("Benchmark Metric", s["cell_hdr"]), Paragraph("Measured Value (GPU)", s["cell_hdr"]), Paragraph("CPU Baseline", s["cell_hdr"]), Paragraph("Target Requirement", s["cell_hdr"]), Paragraph("Evaluation Result", s["cell_hdr"])],
        [Paragraph("Image Forward Pass Latency", s["cell_bold"]), Paragraph("23.13 - 23.57 ms / frame", s["cell"]), Paragraph("89.42 ms / frame", s["cell"]), Paragraph("< 50.0 ms", s["cell"]), Paragraph("EXCEEDED (2.16x)", s["cell_bold"])],
        [Paragraph("Image Total E2E Latency", s["cell_bold"]), Paragraph("52.09 - 53.27 ms / frame", s["cell"]), Paragraph("190.28 ms / frame", s["cell"]), Paragraph("< 100.0 ms", s["cell"]), Paragraph("EXCEEDED (1.88x)", s["cell_bold"])],
        [Paragraph("Video Inference Throughput", s["cell_bold"]), Paragraph("68.95 - 71.50 FPS", s["cell"]), Paragraph("11.20 FPS", s["cell"]), Paragraph("> 30.0 FPS", s["cell"]), Paragraph("EXCEEDED (2.38x)", s["cell_bold"])],
        [Paragraph("Video E2E Processing Throughput", s["cell_bold"]), Paragraph("58.84 - 60.87 FPS", s["cell"]), Paragraph("8.45 FPS", s["cell"]), Paragraph("> 25.0 FPS", s["cell"]), Paragraph("EXCEEDED (2.43x)", s["cell_bold"])],
        [Paragraph("Browser Video Playback", s["cell_bold"]), Paragraph("H.264 High / yuv420p", s["cell"]), Paragraph("N/A", s["cell"]), Paragraph("Standard HTML5", s["cell"]), Paragraph("VERIFIED (moov @ byte 32)", s["cell_bold"])],
    ]
    bm_table = Table(bench_data, colWidths=[130, 94, 80, 100, 100])
    bm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), s["DARK_BLUE"]),
        ('BOX', (0, 0), (-1, -1), 1, s["BORDER_LIGHT"]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, s["BORDER_LIGHT"]),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, s["BG_LIGHT"]]),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(bm_table)
    return story


def create_page_6_story(s):
    story = []
    story.append(Paragraph("3. Subsystem Architecture & What Shakib Receives", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Shakib receives a modular, dependency-injected Python package located at <code>backend/app/services/vision/</code>. All public symbols are exported cleanly via <code>__init__.py</code> without traversing internal submodules.",
        s["body"]
    ))

    story.append(Paragraph("Directory Structure of Ram's CV Subsystem", s["h2"]))
    cv_dir_text = """backend/app/
├── config.py                     # Operational limits & class mappings
├── classes.json                  # Canonical class definitions JSON
└── services/vision/
    ├── __init__.py               # Public exports (VisionService, Detections, etc.)
    ├── classes.py                # Class taxonomy, color maps, display names
    ├── config.py                 # CV constants, YOLO offline flags, clamp limits
    ├── types.py                  # Dataclasses (VisionInspectionResult, ModelStatus, etc.)
    ├── errors.py                 # Standardized CV exception hierarchy
    ├── annotate.py               # OpenCV bounding box & label rendering
    ├── model_manager.py          # YOLO26m model loader & device manager
    ├── image_engine.py           # Preprocessing & image inference engine
    ├── video_engine.py           # Video inference, watchdog & FFmpeg encoder
    └── service.py                # High-level VisionService facade"""

    story.append(Table([[Paragraph(escape_code(cv_dir_text), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Core Service Methods & Exact Verified Signatures", s["h2"]))

    signatures_text = """# 1. VisionService Instantiation & Lifecycle (service.py)
class VisionService:
    def __init__(self, primary_device: Optional[str] = None): ...
    def initialize(self, device: Optional[str] = None) -> bool: ...
    def get_status(self) -> ModelStatus: ...

# 2. Image Detection (service.py)
def detect_image(
    self,
    image_input: Union[bytes, Path, str, np.ndarray],
    conf: float = 0.25,                            # Default: 0.25 [clamped 0.10, 0.90]
    filename: Optional[str] = None,
    annotate: bool = True,
    output_path: Optional[Union[str, Path]] = None
) -> VisionInspectionResult: ...

# 3. Video Detection (service.py)
def detect_video(
    self,
    video_input: Union[Path, str],
    conf: float = 0.25,                            # Default: 0.25 [clamped 0.10, 0.90]
    output_path: Optional[Union[str, Path]] = None,
    cancel_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[int, int, int, Dict[str, int]], None]] = None,
    timeout_s: float = 600.0,
    raise_on_cancel: bool = False                  # False: status='cancelled', True: raises JobCancelledError
) -> VideoInspectionResult: ..."""

    story.append(Table([[Paragraph(escape_code(signatures_text), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))
    return story


def create_page_7_story(s):
    story = []
    story.append(Paragraph("JSON Response Schema (Matching TDD v1.1 §10.1)", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Shakib's API endpoint maps <code>VisionInspectionResult</code> and nested <code>DetectionResult</code> into the JSON schema defined in TDD v1.1 §10.1:",
        s["body"]
    ))

    schema_text = """{
  "status": "success",
  "total_detections": 2,
  "damage_counts": { "D00": 1, "D10": 1, "D20": 0, "D40": 0 },
  "inference_time_ms": 23.57,
  "total_time_ms": 52.09,
  "image_width": 640,
  "image_height": 512,
  "device": "cuda:0",
  "annotated_url": "/outputs/annotated_sample_1a2b3c4d.jpg",
  "detections": [
    {
      "class_id": 0,
      "class_name": "D00",
      "display_name": "Longitudinal crack",
      "confidence": 0.8124,
      "box": { "x1": 120.5, "y1": 150.2, "x2": 210.8, "y2": 480.0,
               "norm_x1": 0.1883, "norm_y1": 0.2934, "norm_x2": 0.3294, "norm_y2": 0.9375 }
    }
  ]
}"""

    story.append(Table([[Paragraph(escape_code(schema_text), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Object Mapping Reference", s["h2"]))
    story.append(Paragraph("• <code>res = vision_service.detect_image(...)</code> returns <code>VisionInspectionResult</code>.", s["bullet"]))
    story.append(Paragraph("• <code>det = res.result</code> contains <code>total_detections</code>, <code>class_counts</code>, <code>detections</code>, <code>inference_time_ms</code>.", s["bullet"]))
    story.append(Paragraph("• <code>res.annotated_output_path</code> yields destination Path; map to URL via <code>f'/outputs/{res.annotated_output_path.name}'</code>.", s["bullet"]))
    story.append(Paragraph("• Each item in <code>det.detections</code> is a <code>Detection</code> object with <code>class_id</code>, <code>class_name</code>, <code>confidence</code>, <code>box</code>.", s["bullet"]))
    return story


def create_page_8_story(s):
    story = []
    story.append(Paragraph("4. Step-by-Step Application Integration Guide", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph("Phase A — FastAPI Application Lifespan & Singleton Pattern", s["h2"]))
    story.append(Paragraph(
        "Loading YOLO26m weights into GPU VRAM takes ~1.5s. <b>Do not re-instantiate VisionService per request.</b> Use FastAPI's <code>@asynccontextmanager</code> lifespan handler to load the model once into <code>app.state.vision_service</code> during startup:",
        s["body"]
    ))

    lifespan_code = """from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.vision import VisionService, get_vision_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Instantiate VisionService and initialize weights onto GPU
    service = VisionService(primary_device="cuda")
    success = service.initialize(device="cuda") # Dynamic CPU fallback if CUDA unavailable
    app.state.vision_service = service
    yield
    # Shutdown cleanup
    app.state.vision_service = None

app = FastAPI(title="RoadVision AI API", lifespan=lifespan)"""

    story.append(Table([[Paragraph(escape_code(lifespan_code), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 4),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Phase B — Synchronous Image Endpoint with Non-Blocking Threadpool", s["h2"]))
    story.append(Paragraph(
        "To prevent blocking the FastAPI async event loop during CPU/GPU inference, offload the call using <code>starlette.concurrency.run_in_threadpool</code> (or <code>asyncio.to_thread</code>):",
        s["body"]
    ))

    image_route_code = """from pathlib import Path
from fastapi import APIRouter, File, UploadFile, Query, Request, HTTPException
from starlette.concurrency import run_in_threadpool # Non-blocking threadpool offload
from app.services.vision import VisionService
from app.services.vision.config import MAX_IMAGE_BYTES

router = APIRouter(prefix="/api/detect", tags=["Detection"])

@router.post("/image")
async def detect_image(request: Request, file: UploadFile = File(...), confidence: float = Query(0.25, ge=0.10, le=0.90)):
    # 1. Validate file extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {'.jpg', '.jpeg', '.png'}:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{ext}'. Allowed: .jpg, .jpeg, .png")
    # 2. Strict confidence check at API boundary (D-04)
    if not (0.10 <= confidence <= 0.90):
        raise HTTPException(status_code=422, detail="Confidence threshold must be between 0.10 and 0.90")
    # 3. Read image bytes and validate payload size
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=422, detail=f"Image exceeds size limit of {MAX_IMAGE_BYTES // (1024*1024)} MB")
    # 4. Offload blocking inference to threadpool without blocking event loop
    service: VisionService = request.app.state.vision_service
    res = await run_in_threadpool(service.detect_image, image_input=image_bytes, conf=confidence, filename=file.filename)
    det = res.result
    annotated_url = f"/outputs/{res.annotated_output_path.name}" if res.annotated_output_path else None
    return {
        "status": "success", "total_detections": det.total_detections, "damage_counts": det.class_counts,
        "inference_time_ms": det.inference_time_ms, "annotated_url": annotated_url,
        "detections": [d.to_dict() if hasattr(d, 'to_dict') else d.__dict__ for d in det.detections]
    }"""

    story.append(Table([[Paragraph(escape_code(image_route_code), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 4),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))
    return story


def create_page_9_story(s):
    story = []
    story.append(Paragraph("Phase C — Asynchronous Video Detection & Job Lifecycle", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "Video processing takes multiple seconds. Execute jobs asynchronously in a background thread worker. Use <code>threading.Event</code> for cancellation and map all lifecycle states cleanly. Note: Ram's CV engine handles frame-by-frame inference, progress callbacks, and partial file cleanup; Shakib owns job persistence, state tracking, and REST endpoints:",
        s["body"]
    ))

    video_job_code = """import os, threading
from typing import Dict, Any, Optional
from app.services.vision import VisionService, VideoInspectionResult

class VideoJob:
    def __init__(self, job_id: str, source_path: str):
        self.job_id = job_id
        self.source_path = source_path
        self.cancel_event = threading.Event()
        self.status = "queued"          # States: queued, processing, completed, cancelled, failed
        self.progress: Dict[str, Any] = {"percent": 0.0, "processed": 0, "total": 0, "fps": 0.0}
        self.result: Optional[VideoInspectionResult] = None
        self.error: Optional[str] = None

    def on_progress(self, processed: int, total: int, hits: int, class_counts: dict) -> None:
        pct = round((processed / total) * 100.0, 1) if total > 0 else 0.0
        self.progress = {"percent": pct, "processed": processed, "total": total, "detections": hits}

    def cancel(self) -> None:
        self.cancel_event.set()

def run_video_job_worker(job: VideoJob, service: VisionService) -> None:
    job.status = "processing"
    try:
        # raise_on_cancel=False returns VideoInspectionResult(status='cancelled') and unlinks partial outputs
        res = service.detect_video(
            video_input=job.source_path,
            progress_callback=job.on_progress,
            cancel_event=job.cancel_event,
            raise_on_cancel=False
        )
        job.result = res
        job.status = res.status  # 'completed' or 'cancelled'
    except Exception as e:
        job.status = "failed"
        job.error = str(e)
    finally:
        # Clean up temporary raw upload if needed
        if os.path.exists(job.source_path) and job.status in ("completed", "cancelled"):
            pass # Keep or purge raw upload per Shakib's database retention policy"""

    story.append(Table([[Paragraph(escape_code(video_job_code), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Job Lifecycle & API Routes to Expose", s["h2"]))
    story.append(Paragraph("• <code>POST /api/detect/video</code>: Accepts MP4/AVI, assigns UUID4 <code>job_id</code>, starts thread, returns HTTP 200 with status <code>queued</code>.", s["bullet"]))
    story.append(Paragraph("• <code>GET /api/detect/video/{id}/progress</code>: Returns current percentage, processed frames, and status for UI progress bar.", s["bullet"]))
    story.append(Paragraph("• <code>POST /api/detect/video/{id}/cancel</code>: Triggers <code>job.cancel()</code>; halts inference loop immediately and unlinks partial video.", s["bullet"]))
    story.append(Paragraph("• <code>GET /api/detect/video/{id}/result</code>: Returns final damage breakdown, FPS, and streaming URL <code>/outputs/<name>.mp4</code>.", s["bullet"]))
    return story


def create_page_10_story(s):
    story = []
    story.append(Paragraph("5. Copy-Ready Code Examples for FastAPI & React", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=4))

    story.append(Paragraph("FastAPI Global Exception Handlers (Mapping CV Errors to HTTP)", s["h2"]))
    story.append(Paragraph(
        "Register these handlers in <code>backend/app/main.py</code> (each handler registers a distinct class or base hierarchy; tuples are not accepted by FastAPI):",
        s["body"]
    ))

    exc_handler_code = """from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.services.vision.errors import (
    VisionServiceError, VideoNotFoundError, UnsupportedImageFormatError,
    UnsupportedVideoFormatError, ImageValidationError, VideoValidationError,
    JobCancelledError, JobTimeoutError, ModelLoadError, ModelUnavailableError
)

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(VideoNotFoundError)
    async def not_found(req: Request, exc: VideoNotFoundError):
        return JSONResponse(status_code=404, content={"error": "Not Found", "detail": str(exc)})

    @app.exception_handler(JobCancelledError)
    async def cancelled(req: Request, exc: JobCancelledError):
        return JSONResponse(status_code=409, content={"error": "Conflict", "detail": "Job was cancelled."})

    @app.exception_handler(JobTimeoutError)
    async def timeout(req: Request, exc: JobTimeoutError):
        return JSONResponse(status_code=504, content={"error": "Gateway Timeout", "detail": str(exc)})

    @app.exception_handler(ImageValidationError)
    async def img_err(req: Request, exc: ImageValidationError):
        status = 400 if isinstance(exc, UnsupportedImageFormatError) else 422
        return JSONResponse(status_code=status, content={"error": "Image Validation Error", "detail": str(exc)})

    @app.exception_handler(VideoValidationError)
    async def vid_err(req: Request, exc: VideoValidationError):
        status = 400 if isinstance(exc, UnsupportedVideoFormatError) else 422
        return JSONResponse(status_code=status, content={"error": "Video Validation Error", "detail": str(exc)})

    @app.exception_handler(VisionServiceError)
    async def cv_err(req: Request, exc: VisionServiceError):
        status = 503 if isinstance(exc, (ModelLoadError, ModelUnavailableError)) else 500
        return JSONResponse(status_code=status, content={"error": "Vision Subsystem Error", "detail": str(exc)})"""

    story.append(Table([[Paragraph(escape_code(exc_handler_code), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 3),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))

    story.append(Spacer(1, 3))
    story.append(Paragraph("Complete Compilable React HTML5 Video Player Component", s["h2"]))
    story.append(Paragraph(
        "Type-safe React component with responsive styling and Faststart MP4 stream support:",
        s["body"]
    ))

    react_video_code = """import React from 'react';

interface RoadVideoPlayerProps {
  annotatedVideoUrl: string; // e.g. "/outputs/Japan_000000_annotated_a1b2c3d4.mp4"
  className?: string;
}

export const RoadVideoPlayer: React.FC<RoadVideoPlayerProps> = ({
  annotatedVideoUrl,
  className = "w-full rounded-lg shadow border border-slate-700",
}) => (
  <div className="relative overflow-hidden bg-slate-950 rounded-lg p-2">
    <video controls playsInline preload="metadata" className={className} src={annotatedVideoUrl}>
      <source src={annotatedVideoUrl} type="video/mp4" />
      <p className="text-slate-400 p-4 text-sm">Your browser does not support HTML5 MP4 video playback.</p>
    </video>
  </div>
);"""

    story.append(Table([[Paragraph(escape_code(react_video_code), s["code"])]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), s["CODE_BG"]),
                              ('PADDING', (0, 0), (-1, -1), 3),
                              ('BOX', (0, 0), (-1, -1), 1, s["PRIMARY"])]))
    return story


def create_page_14_story(s):
    story = []
    story.append(Paragraph("9. Fastest Sequential Integration Path", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    story.append(Paragraph(
        "To achieve a working full-stack demonstration in the shortest possible time, follow this strict 8-step critical path:",
        s["body"]
    ))

    seq_steps = [
        ("Step 1: Setup & Import Verification", "Ensure virtual environment has requirements.txt installed. Run <code>python -c \"from app.services.vision import VisionService; s = VisionService(); s.initialize(); print(s.get_status())\"</code> to verify model loads on GPU."),
        ("Step 2: FastAPI Lifespan Wiring", "Add VisionService singleton initialization to app.main lifespan. Mount <code>/outputs</code> to serve data/outputs via StaticFiles."),
        ("Step 3: Image Detection API Endpoint", "Implement <code>POST /api/detect/image</code> using the copy-ready snippet in Section 5 with run_in_threadpool. Test with curl using Japan_000000.jpg."),
        ("Step 4: React Image Upload Component", "Build minimal file picker and image viewer. Display annotated image and damage count cards. (Milestone: First working browser demo!)."),
        ("Step 5: Video Detection Background Job", "Implement <code>POST /api/detect/video</code> and background worker using threading.Event. Wire progress callback."),
        ("Step 6: Video Progress & Cancellation Routes", "Expose <code>GET /api/detect/video/{id}/progress</code> and <code>POST /cancel</code>. Test with sample video."),
        ("Step 7: React Video Player Integration", "Embed RoadVideoPlayer component pointing to annotated video URL. Confirm instant streaming without buffering delay."),
        ("Step 8: SQLite Persistence & History", "Save inspection summaries to SQLite database. Render history table in React dashboard."),
    ]

    for title, desc in seq_steps:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", s["bullet"]))
    return story


def create_page_15_story(s):
    story = []
    story.append(Paragraph("10. Architectural Limitations, Policy Constraints & Warnings", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    warnings_list = [
        ("Full Application Integration is Not Yet Executed", "Ram's repository houses the Computer Vision subsystem. Shakib's application layer (FastAPI routes, SQLite DB, React UI) has not yet been connected or executed end-to-end. Full application readiness remains pending until this integration occurs."),
        ("Shakib's Independent Repository Uninspected", "Shakib is developing his application layer in a separate repository. Interfaces must adhere strictly to Section 3 of this document to prevent interface divergence."),
        ("Confidence Policy & Range Clarification", "Both backend/app/config.py and vision config define DEFAULT_CONFIDENCE = 0.25, MIN_CONFIDENCE = 0.10, MAX_CONFIDENCE = 0.90. The CV engine enforces clamp-and-warn on [0.10, 0.90] to prevent runtime crashes. However, Shakib's API layer MUST reject requests outside [0.10, 0.90] with HTTP 422 Unprocessable Entity rather than relying on silent engine clamping. Ram's library code does not implement HTTP 422 boundaries."),
        ("Operational Frame Cap (MAX_VIDEO_FRAME_CAP = 3600)", "Videos exceeding 60 seconds or 3,600 frames are rejected with VideoFrameCountExceededError (HTTP 422) to prevent memory exhaustion on the host."),
        ("832px Model Resolution is Experimental", "The 832px experiment evaluated in Stage 4 showed a 69% increase in latency without significant mAP gains. The production checkpoint yolo26m.pt is trained and calibrated strictly for 640px."),
        ("Held-Out Test Split Isolation", "The held-out test split (test/ split) is strictly reserved for independent final evaluation. It must never be used for hyperparameter tuning, confidence threshold selection, or iterative prompt engineering."),
    ]

    for title, desc in warnings_list:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", s["bullet"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("11. Direct Collaborative Message to Shakib", s["h1"]))
    story.append(HRFlowable(width="100%", thickness=1, color=s["DARK_BLUE"], spaceBefore=2, spaceAfter=6))

    collab_box = [
        [Paragraph("""<b>Hey Shakib,</b><br/><br/>
I'm excited to hand off the RoadVision Computer Vision Subsystem to you! Everything on the AI/CV side is 100% complete, fully hardened, and verified on real hardware.<br/><br/>
<b>Here is what is ready for you right now:</b><br/>
1. The production model (<code>models/weights/yolo26m.pt</code>) is trained, verified, and running on the RTX 5060 GPU with an inference forward pass of ~23 ms per image and over 60 FPS for full video processing.<br/>
2. All 14 defects from earlier audits have been resolved. The full test suite of 94 automated tests passes in under 9 seconds.<br/>
3. The video engine encodes web-optimized H.264 MP4 with the Faststart <code>moov</code> atom at the start of the file, meaning videos will stream in React immediately without waiting for download.<br/>
4. The service facade is clean: call <code>vision_service.detect_image(...)</code> and <code>vision_service.detect_video(...)</code> directly.<br/><br/>
<b>What I suggest you implement first:</b><br/>
Start with Step 1 and Step 2 from Section 9: wire <code>VisionService</code> into your FastAPI lifespan and build <code>POST /api/detect/image</code> using <code>run_in_threadpool</code>. Once that's up, wire up the basic React image upload page. Seeing the first road damage bounding boxes render in the browser will give us a huge milestone win!<br/><br/>
Whenever you're ready to run joint acceptance tests against the API, let me know and we will knock out CHK-07 through CHK-16 together.<br/><br/>
Best regards,<br/>
<b>Ram (Senior Computer Vision Engineer)</b>""", s["body"])]
    ]

    collab_table = Table(collab_box, colWidths=[504])
    collab_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), s["BG_LIGHT"]),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#2563EB")),
        ('PADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(collab_table)
    return story


def execute_pdf_corrections():
    src_pdf_path = Path("docs/integration/ROADVISION_SHAKIB_FINAL_INTEGRATION_HANDOFF.pdf")
    temp_dir = Path("runs/pdf_corrections")
    temp_dir.mkdir(parents=True, exist_ok=True)

    styles = get_styles()

    pages_to_replace = {
        4: create_page_4_story(styles),
        6: create_page_6_story(styles),
        7: create_page_7_story(styles),
        8: create_page_8_story(styles),
        9: create_page_9_story(styles),
        10: create_page_10_story(styles),
        14: create_page_14_story(styles),
        15: create_page_15_story(styles),
    }

    # Generate single replacement pages
    replacement_pdf_paths = {}
    for page_num, story in pages_to_replace.items():
        out_page_pdf = temp_dir / f"page_{page_num}_corrected.pdf"
        generate_single_page_pdf(story, out_page_pdf, page_num)
        replacement_pdf_paths[page_num] = out_page_pdf
        print(f"Generated corrected replacement for Page {page_num}: {out_page_pdf}")

    # Open the existing source PDF
    doc = fitz.open(str(src_pdf_path))
    original_page_count = len(doc)
    print(f"Opened original PDF: {src_pdf_path} (Total pages: {original_page_count})")
    assert original_page_count == 15, f"Expected 15 pages in source PDF, found {original_page_count}"

    # Perform targeted page-level replacement
    for page_num, repl_path in replacement_pdf_paths.items():
        page_idx = page_num - 1  # 0-indexed
        repl_doc = fitz.open(str(repl_path))
        assert len(repl_doc) == 1, f"Replacement for page {page_num} must have exactly 1 page, found {len(repl_doc)}"

        # Delete the existing page at page_idx and insert the replacement
        doc.delete_page(page_idx)
        doc.insert_pdf(repl_doc, from_page=0, to_page=0, start_at=page_idx)
        print(f"Replaced Page {page_num} (index {page_idx}) with corrected page.")

    # Save to a temporary output first
    temp_final_pdf = temp_dir / "final_corrected_handoff.pdf"
    doc.save(str(temp_final_pdf))
    doc.close()

    # Verify the temporary final PDF before overwriting deliverable
    verify_doc = fitz.open(str(temp_final_pdf))
    print(f"Verified corrected PDF total pages: {len(verify_doc)}")
    assert len(verify_doc) == 15, f"Expected 15 pages in final PDF, got {len(verify_doc)}"

    # Check that corrections are present
    p4_text = verify_doc[3].get_text()
    assert "47,420" in p4_text, "Page 4 missing '47,420' raw images!"
    assert "23,767" in p4_text, "Page 4 missing '23,767' prepared pairs!"
    assert "0.630" in p4_text, "Page 4 missing val mAP '0.630'!"
    assert "0.619" in p4_text, "Page 4 missing test mAP '0.619'!"

    p8_text = verify_doc[7].get_text()
    assert "run_in_threadpool" in p8_text, "Page 8 missing 'run_in_threadpool'!"

    p10_text = verify_doc[9].get_text()
    assert "@app.exception_handler(VideoNotFoundError)" in p10_text, "Page 10 missing individual exception handler!"
    assert "RoadVideoPlayer" in p10_text, "Page 10 missing 'RoadVideoPlayer'!"
    assert "src={annotatedVideoUrl}" in p10_text, "Page 10 missing 'src={annotatedVideoUrl}'!"

    p15_text = verify_doc[14].get_text()
    assert "0.10" in p15_text and "0.90" in p15_text, "Page 15 missing confidence range clarification!"

    verify_doc.close()
    print("All content assertions passed on corrected PDF!")

    # Overwrite the deliverable
    import shutil
    shutil.copy2(temp_final_pdf, src_pdf_path)
    print(f"Successfully updated deliverable in place: {src_pdf_path} ({os.path.getsize(src_pdf_path)} bytes)")


if __name__ == "__main__":
    execute_pdf_corrections()
