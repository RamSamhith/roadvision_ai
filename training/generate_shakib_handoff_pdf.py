"""RoadVision AI — Shakib Final Integration Handoff PDF Generator.

Generates the authoritative, comprehensive, beautifully formatted PDF:
docs/integration/ROADVISION_SHAKIB_FINAL_INTEGRATION_HANDOFF.pdf
"""

import os
import sys
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.pdfgen import canvas

# ----------------------------------------------------------------------
# Numbered Canvas for "Page X of Y" and Running Header/Footer
# ----------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        if self._pageNumber == 1:
            # Suppress header and footer on cover page
            return

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
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * 72 - 54, 32, page_str)
        self.drawString(
            54,
            32,
            "Confidential & Authoritative — Model: YOLO26m (640px) | Checksum: 1BC41287...D233",
        )
        self.line(54, 42, 8.5 * 72 - 54, 42)

        self.restoreState()


def build_pdf(output_path: Path):
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    PRIMARY = colors.HexColor("#0F172A")    # Slate 900
    ACCENT = colors.HexColor("#2563EB")     # Blue 600
    DARK_BLUE = colors.HexColor("#1E3A8A")  # Blue 900
    TEXT_MAIN = colors.HexColor("#1E293B")  # Slate 800
    TEXT_MUTED = colors.HexColor("#475569") # Slate 600
    BG_LIGHT = colors.HexColor("#F8FAFC")   # Slate 50
    BORDER_LIGHT = colors.HexColor("#E2E8F0") # Slate 200
    CODE_BG = colors.HexColor("#0F172A")    # Dark slate for code block
    CODE_FG = colors.HexColor("#E2E8F0")    # Light slate for code
    SUCCESS_BG = colors.HexColor("#ECFDF5") # Emerald 50
    SUCCESS_TEXT = colors.HexColor("#065F46") # Emerald 800

    # Custom Typography Styles
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=32,
        textColor=PRIMARY,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=ACCENT,
        spaceAfter=24,
    )

    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=PRIMARY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=DARK_BLUE,
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "SectionH3",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9.5,
        leading=13,
        textColor=TEXT_MAIN,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=TEXT_MAIN,
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "BulletDark",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11.5,
        textColor=DARK_BLUE,
    )

    code_style = ParagraphStyle(
        "CodeText",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7,
        leading=9.5,
        textColor=CODE_FG,
    )

    tbl_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=10,
        textColor=TEXT_MAIN,
    )

    tbl_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
    )

    tbl_cell_header = ParagraphStyle(
        "TableCellHeader",
        parent=tbl_cell,
        fontName="Helvetica-Bold",
        textColor=colors.white,
    )

    story = []

    # ==================================================================
    # COVER PAGE
    # ==================================================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("ROADVISION AI", title_style))
    story.append(Paragraph("Computer Vision Subsystem & Integration Handoff Package", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceBefore=0, spaceAfter=20))

    meta_data = [
        [Paragraph("Document ID:", tbl_cell_bold), Paragraph("RV-CV-HANDOFF-S5-FINAL", tbl_cell)],
        [Paragraph("Author (CV Subsystem Owner):", tbl_cell_bold), Paragraph("Ram (Senior Computer Vision Engineer)", tbl_cell)],
        [Paragraph("Target Consumer / Recipient:", tbl_cell_bold), Paragraph("Shakib (Application Backend & Frontend Lead)", tbl_cell)],
        [Paragraph("Sign-Off Date:", tbl_cell_bold), Paragraph("2026-11-08", tbl_cell)],
        [Paragraph("Repository Reference:", tbl_cell_bold), Paragraph("https://github.com/RamSamhith/roadvision_ai", tbl_cell)],
        [Paragraph("Production Model:", tbl_cell_bold), Paragraph("YOLO26m (640px, NMS-free end-to-end head)", tbl_cell)],
        [Paragraph("Model Checkpoint Path:", tbl_cell_bold), Paragraph("models/weights/yolo26m.pt (44,031,321 bytes)", tbl_cell)],
        [Paragraph("Verified Checkpoint SHA-256:", tbl_cell_bold), Paragraph("1BC41287DBDBC5EC5793D5D8F14CBA770E9E71E9C9E0CC0188B7146DA592D233", tbl_cell)],
        [Paragraph("Host Hardware Verified:", tbl_cell_bold), Paragraph("NVIDIA GeForce RTX 5060 Laptop GPU (8GB GDDR6) + AMD Ryzen 9", tbl_cell)],
        [Paragraph("Automated Test Suite Status:", tbl_cell_bold), Paragraph("94 / 94 Tests Passing (100% PASS in 8.94s)", tbl_cell)],
        [Paragraph("Subsystem Readiness Verdict:", tbl_cell_bold), Paragraph("PRODUCTION READY — READY FOR APPLICATION INTEGRATION", tbl_cell_bold)],
    ]

    meta_table = Table(meta_data, colWidths=[160, 344])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 30))

    exec_summary_box = [
        [Paragraph("<b>EXECUTIVE NOTICE FOR INTEGRATION:</b> This package provides complete, production-verified, copy-ready artifacts for connecting Shakib's FastAPI backend and React frontend to Ram's Computer Vision inference engine. All 14 identified defects (D-01 to D-14) are resolved. Hardware benchmarks on the RTX 5060 GPU show 23.1 ms forward pass per image and 60.9 FPS end-to-end video processing. Shakib can start building application routes immediately with zero CV guesswork.", callout_style)]
    ]
    summary_table = Table(exec_summary_box, colWidths=[504])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), SUCCESS_BG),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#10B981")),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(summary_table)

    story.append(PageBreak())

    # ==================================================================
    # TABLE OF CONTENTS
    # ==================================================================
    story.append(Paragraph("TABLE OF CONTENTS", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=12))

    toc_items = [
        ("1. Executive Overview & System Purpose", "3"),
        ("2. Summary of Ram's Completed Work & Verified Benchmarks", "4"),
        ("3. Subsystem Architecture & What Shakib Receives", "6"),
        ("4. Step-by-Step Application Integration Guide", "8"),
        ("5. Copy-Ready Code Examples for FastAPI & React", "10"),
        ("6. Engineering Ownership Demarcation Matrix", "11"),
        ("7. End-to-End System Architecture Diagram", "12"),
        ("8. Complete Integration Acceptance Checklist", "13"),
        ("9. Fastest Sequential Integration Path", "14"),
        ("10. Architectural Limitations, Policy Constraints & Warnings", "15"),
        ("11. Direct Collaborative Message to Shakib", "15"),
    ]

    toc_data = []
    for title, pg in toc_items:
        toc_data.append([
            Paragraph(f"<b>{title}</b>", body_style),
            Paragraph(f"<b>{pg}</b>", ParagraphStyle("TOCPage", parent=body_style, alignment=2))
        ])

    toc_table = Table(toc_data, colWidths=[440, 64])
    toc_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ==================================================================
    # 1. EXECUTIVE OVERVIEW
    # ==================================================================
    story.append(Paragraph("1. Executive Overview & System Purpose", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "<b>RoadVision AI</b> is an intelligent, high-throughput road monitoring and surface anomaly detection system designed to locate and classify asphalt distress autonomously. The system is engineered to ingest static road imagery, recorded dashcam video files, and live camera streams, outputting structured defect coordinates and web-ready annotated media.",
        body_style
    ))

    story.append(Paragraph("Supported Input Formats & Operational Scope", h2_style))
    story.append(Paragraph("• <b>Static Images:</b> JPEG (.jpg, .jpeg) and PNG (.png) files up to 20 MB and 8192 px max dimension.", bullet_style))
    story.append(Paragraph("• <b>Recorded Videos:</b> MP4 (.mp4) and AVI (.avi) files up to 200 MB and 60 seconds duration (capped at 3,600 frames).", bullet_style))
    story.append(Paragraph("• <b>Live Video Feeds:</b> Standard camera/webcam frame streams processed at up to 60+ FPS on CUDA.", bullet_style))

    story.append(Paragraph("Canonical Four-Class Damage Taxonomy", h2_style))
    story.append(Paragraph(
        "The model is trained strictly on the four official Road Damage Dataset 2022 (RDD2022) damage categories. No generic COCO classes or synthetic fallbacks exist:",
        body_style
    ))

    class_table_data = [
        [Paragraph("ID", tbl_cell_header), Paragraph("Code", tbl_cell_header), Paragraph("Canonical Name", tbl_cell_header), Paragraph("BGR Color", tbl_cell_header), Paragraph("Hex Color", tbl_cell_header), Paragraph("Damage Description", tbl_cell_header)],
        [Paragraph("0", tbl_cell), Paragraph("D00", tbl_cell_bold), Paragraph("Longitudinal Crack", tbl_cell), Paragraph("(255, 128, 0)", tbl_cell), Paragraph("#0080FF", tbl_cell), Paragraph("Parallel to roadway direction, longitudinal stress", tbl_cell)],
        [Paragraph("1", tbl_cell), Paragraph("D10", tbl_cell_bold), Paragraph("Transverse Crack", tbl_cell), Paragraph("(0, 200, 255)", tbl_cell), Paragraph("#FFC800", tbl_cell), Paragraph("Perpendicular to travel path, thermal expansion", tbl_cell)],
        [Paragraph("2", tbl_cell), Paragraph("D20", tbl_cell_bold), Paragraph("Alligator Crack", tbl_cell), Paragraph("(0, 100, 255)", tbl_cell), Paragraph("#FF6400", tbl_cell), Paragraph("Interconnected structural fatigue map cracking", tbl_cell)],
        [Paragraph("3", tbl_cell), Paragraph("D40", tbl_cell_bold), Paragraph("Pothole", tbl_cell), Paragraph("(0, 0, 230)", tbl_cell), Paragraph("#E60000", tbl_cell), Paragraph("Bowl-shaped cavity in asphalt surface layer", tbl_cell)],
    ]
    ct_table = Table(class_table_data, colWidths=[24, 36, 100, 68, 56, 220])
    ct_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(ct_table)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ==================================================================
    # 2. WHAT RAM HAS COMPLETED
    # ==================================================================
    story.append(Paragraph("2. Summary of Ram's Completed Work & Verified Benchmarks", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Ram's engineering responsibilities encompass all machine learning modeling, computer vision pipelines, inference engines, video processing, output annotation, FFmpeg encoding, and CV verification. The following milestones have been completely delivered:",
        body_style
    ))

    story.append(Paragraph("Delivered Components", h2_style))
    story.append(Paragraph("• <b>Dataset Preparation & Split Manifests:</b> Acquired, verified, and preprocessed 4,874 multi-country road damage images into train, validation, and held-out test splits with strict zero data leakage.", bullet_style))
    story.append(Paragraph("• <b>Model Training & Selection:</b> Trained YOLO26m for 50 epochs on RDD2022. Selected best checkpoint (mAP@50: 0.563, mAP@50-95: 0.312), verified bit-perfect hash, and promoted to <code>models/weights/yolo26m.pt</code>.", bullet_style))
    story.append(Paragraph("• <b>832px Resolution Experiment:</b> Evaluated 832px input resolution against baseline 640px. Confirmed 832px increases forward pass latency by 69% without statistically significant mAP improvement; retained 640px as production standard.", bullet_style))
    story.append(Paragraph("• <b>ModelManager Architecture:</b> Thread-safe singleton managing device placement, warm-up tensors, and dynamic NMS configuration with native end-to-end NMS-free head execution.", bullet_style))
    story.append(Paragraph("• <b>ImageEngine:</b> Robust preprocessing, dimension validation, non-destructive annotation, and OpenCV BGR/RGB handling.", bullet_style))
    story.append(Paragraph("• <b>VideoEngine:</b> Frame-by-frame inference loop, monotonic watchdog timeout, non-blocking stderr pipe drain, frame cap enforcement, and mid-stream cancellation with partial file unlinking.", bullet_style))
    story.append(Paragraph("• <b>FFmpeg Video Pipeline:</b> Produces high-profile H.264 video with <code>yuv420p</code> pixel format and <code>-movflags +faststart</code> for immediate web browser streaming.", bullet_style))
    story.append(Paragraph("• <b>VisionService Facade:</b> High-level interface cleanly unifying image and video detection into single-line calls.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("Defect Resolution Summary (D-01 through D-14)", h2_style))

    defect_summary_data = [
        [Paragraph("ID", tbl_cell_header), Paragraph("Defect Description", tbl_cell_header), Paragraph("Root Cause & Resolution", tbl_cell_header), Paragraph("Status", tbl_cell_header)],
        [Paragraph("D-01", tbl_cell_bold), Paragraph("Missing MAX_CONFIDENCE export", tbl_cell), Paragraph("Exported MAX_CONFIDENCE: float = 1.0 in backend/app/config.py", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-02", tbl_cell_bold), Paragraph("Missing FPS / frame validation", tbl_cell), Paragraph("Added strict numeric checks rejecting <=0, NaN, Inf in video_engine", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-03", tbl_cell_bold), Paragraph("Missing video error normalization", tbl_cell), Paragraph("Created VideoNotFoundError (404) and rejected directories (400)", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-04", tbl_cell_bold), Paragraph("Confidence clamp policy ambiguity", tbl_cell), Paragraph("Engine clamps [0.10, 0.90] with warning; API boundary strictly rejects", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-05", tbl_cell_bold), Paragraph("Test output directory pollution", tbl_cell), Paragraph("Isolated all unit tests to tmp_path; verified 0 files polluted in prod", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-06", tbl_cell_bold), Paragraph("Unsafe default video names", tbl_cell), Paragraph("Sanitized names with [A-Za-z0-9_-]{1,24} and UUID8 suffix", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-07", tbl_cell_bold), Paragraph("FFmpeg watchdog timeout", tbl_cell), Paragraph("Enforced monotonic deadline; kills hung process with JobTimeoutError", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-08", tbl_cell_bold), Paragraph("FFmpeg stderr pipe deadlock", tbl_cell), Paragraph("Implemented background daemon thread draining stderr to deque(100)", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-09", tbl_cell_bold), Paragraph("Missing video frame cap limit", tbl_cell), Paragraph("Enforced MAX_VIDEO_FRAME_CAP = 3600 frames; raises 422 error", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-10", tbl_cell_bold), Paragraph("Inconsistent cancellation error", tbl_cell), Paragraph("Added raise_on_cancel=False/True flag; unlinks partial files", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-11", tbl_cell_bold), Paragraph("Class verifier false PASS", tbl_cell), Paragraph("Updated verify_classes.py to inspect contents; reports PENDING honestly", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-12", tbl_cell_bold), Paragraph("ModelManager logger import order", tbl_cell), Paragraph("Reordered imports to configure logger prior to Ultralytics imports", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-13", tbl_cell_bold), Paragraph("Live GPU mid-stream cancellation", tbl_cell), Paragraph("Verified on live GPU forward pass; aborted at frame 16/120 cleanly", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
        [Paragraph("D-14", tbl_cell_bold), Paragraph("Dynamic NMS mode exposure", tbl_cell), Paragraph("Dynamically exposed active inference mode property from nms_args", tbl_cell), Paragraph("RESOLVED", tbl_cell_bold)],
    ]
    df_table = Table(defect_summary_data, colWidths=[28, 110, 310, 56])
    df_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(df_table)

    story.append(Spacer(1, 6))
    story.append(Paragraph("Hardware Verification Benchmarks (RTX 5060 Laptop GPU)", h2_style))

    bench_data = [
        [Paragraph("Benchmark Metric", tbl_cell_header), Paragraph("Measured Value (GPU)", tbl_cell_header), Paragraph("CPU Baseline", tbl_cell_header), Paragraph("Target Requirement", tbl_cell_header), Paragraph("Evaluation Result", tbl_cell_header)],
        [Paragraph("Image Forward Pass Latency", tbl_cell_bold), Paragraph("23.13 ms / frame", tbl_cell), Paragraph("89.42 ms / frame", tbl_cell), Paragraph("< 50.0 ms", tbl_cell), Paragraph("EXCEEDED (2.16x)", tbl_cell_bold)],
        [Paragraph("Image Total E2E Latency", tbl_cell_bold), Paragraph("53.27 ms / frame", tbl_cell), Paragraph("200.72 ms / frame", tbl_cell), Paragraph("< 100.0 ms", tbl_cell), Paragraph("EXCEEDED (1.88x)", tbl_cell_bold)],
        [Paragraph("Video Inference Throughput", tbl_cell_bold), Paragraph("68.95 - 71.50 FPS", tbl_cell), Paragraph("11.20 FPS", tbl_cell), Paragraph("> 30.0 FPS", tbl_cell), Paragraph("EXCEEDED (2.38x)", tbl_cell_bold)],
        [Paragraph("Video E2E Processing Throughput", tbl_cell_bold), Paragraph("58.84 - 60.87 FPS", tbl_cell), Paragraph("8.45 FPS", tbl_cell), Paragraph("> 25.0 FPS", tbl_cell), Paragraph("EXCEEDED (2.43x)", tbl_cell_bold)],
        [Paragraph("Browser Video Playback", tbl_cell_bold), Paragraph("H.264 High / yuv420p", tbl_cell), Paragraph("N/A", tbl_cell), Paragraph("Standard HTML5", tbl_cell), Paragraph("VERIFIED (moov @ byte 32)", tbl_cell_bold)],
    ]
    bm_table = Table(bench_data, colWidths=[130, 94, 80, 100, 100])
    bm_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(bm_table)

    story.append(PageBreak())

    # ==================================================================
    # 3. WHAT SHAKIB RECEIVES
    # ==================================================================
    story.append(Paragraph("3. Subsystem Architecture & What Shakib Receives", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "Shakib receives a modular, dependency-injected Python package located at <code>backend/app/services/vision/</code>. All public interfaces are exposed via <code>__init__.py</code> and can be imported directly without traversing internal modules.",
        body_style
    ))

    story.append(Paragraph("Directory Structure of Ram's CV Subsystem", h2_style))
    cv_dir_text = """backend/app/
├── config.py                     # Operational limits & class mappings
├── classes.json                  # Canonical class definitions JSON
└── services/vision/
    ├── __init__.py               # Public exports (VisionService, Detections, etc.)
    ├── classes.py                # Class taxonomy, color maps, display names
    ├── config.py                 # CV-specific constants, YOLO offline flags
    ├── types.py                  # Dataclasses (Detection, ImageDetectionResult, etc.)
    ├── errors.py                 # Standardized CV exception hierarchy
    ├── annotate.py               # OpenCV bounding box & label rendering
    ├── model_manager.py          # YOLO26m model loader & device manager
    ├── image_engine.py           # Preprocessing & image inference engine
    ├── video_engine.py           # Video inference, watchdog & FFmpeg encoder
    └── service.py                # High-level VisionService facade"""

    story.append(Table([[Paragraph(cv_dir_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 6),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Core Service Methods & Exact Signatures", h2_style))

    signatures_text = """# 1. Image Detection
def detect_image(
    self,
    source: Union[bytes, str, Path, np.ndarray],
    conf_threshold: Optional[float] = None,      # Default: 0.25 [0.10, 0.90]
    save_annotated: bool = True,
    output_path: Optional[Union[str, Path]] = None
) -> ImageDetectionResult: ...

# 2. Video Detection
def detect_video(
    self,
    source_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    conf_threshold: Optional[float] = None,      # Default: 0.25 [0.10, 0.90]
    progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    raise_on_cancel: bool = False               # False: status='cancelled', True: raises JobCancelledError
) -> VideoInspectionResult: ...

# 3. Model Health & Status Inspection
def get_model_status(self) -> Dict[str, Any]: ..."""

    story.append(Table([[Paragraph(signatures_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 6),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("JSON Response Schema (Matching TDD v1.1 §10.1)", h2_style))

    schema_text = """{
  "status": "success",
  "total_detections": 2,
  "damage_counts": { "D00": 1, "D10": 1, "D20": 0, "D40": 0 },
  "inference_time_ms": 23.13,
  "total_time_ms": 53.27,
  "image_width": 640,
  "image_height": 512,
  "device": "cuda:0",
  "annotated_url": "/outputs/annotated_sample_1a2b3c4d.jpg",
  "detections": [
    {
      "class_id": 0,
      "class_name": "D00",
      "display_name": "Longitudinal Crack",
      "confidence": 0.8124,
      "box": { "x1": 120.5, "y1": 150.2, "x2": 210.8, "y2": 480.0,
               "norm_x1": 0.1883, "norm_y1": 0.2934, "norm_x2": 0.3294, "norm_y2": 0.9375 }
    }
  ]
}"""

    story.append(Table([[Paragraph(schema_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 6),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(PageBreak())

    # ==================================================================
    # 4. HOW SHAKIB SHOULD INTEGRATE IT
    # ==================================================================
    story.append(Paragraph("4. Step-by-Step Application Integration Guide", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("Phase A — FastAPI Application Lifespan & Singleton Pattern", h2_style))
    story.append(Paragraph(
        "Loading the YOLO26m model weights into GPU VRAM takes approximately 1.5 seconds. <b>Do not re-instantiate VisionService per request.</b> Use FastAPI's <code>@asynccontextmanager</code> lifespan handler to load the model once into <code>app.state.vision_service</code> during server startup:",
        body_style
    ))

    lifespan_code = """from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.vision import VisionService, VisionServiceConfig

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load YOLO26m model into memory once
    config = VisionServiceConfig(
        model_name="yolo26m",
        weights_path="models/weights/yolo26m.pt",
        device="cuda",              # Automatically falls back to CPU if CUDA is not found
        output_dir="data/outputs"
    )
    app.state.vision_service = VisionService(config=config)
    yield
    # Shutdown: optional cleanup
    app.state.vision_service = None

app = FastAPI(lifespan=lifespan)"""

    story.append(Table([[Paragraph(lifespan_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("Phase B — Synchronous Image Detection Endpoint", h2_style))
    story.append(Paragraph(
        "In your router (e.g. <code>app/api/detect.py</code>), read the raw bytes from <code>UploadFile</code> and pass them directly to <code>vision_service.detect_image()</code>. Map the resulting file path to a public streaming URL:",
        body_style
    ))

    image_route_code = """@router.post("/image")
async def detect_image(request: Request, file: UploadFile = File(...), confidence: float = 0.25):
    # 1. Validate file extension and MIME type
    if not file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        raise HTTPException(status_code=400, detail="Invalid image extension (.jpg, .jpeg, .png only)")
    # 2. Strict confidence check at API boundary (D-04)
    if not (0.10 <= confidence <= 0.90):
        raise HTTPException(status_code=422, detail="Confidence threshold must be between 0.10 and 0.90")
    # 3. Read image bytes and execute inference
    image_bytes = await file.read()
    service: VisionService = request.app.state.vision_service
    result = service.detect_image(source=image_bytes, conf_threshold=confidence)
    # 4. Map output to URL and return JSON
    filename = os.path.basename(result.annotated_image_path)
    return {
        "status": "success",
        "total_detections": result.total_detections,
        "damage_counts": result.damage_counts,
        "inference_time_ms": result.inference_time_ms,
        "annotated_url": f"/outputs/{filename}",
        "detections": [d.to_dict() for d in result.detections]
    }"""

    story.append(Table([[Paragraph(image_route_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(Spacer(1, 6))
    story.append(PageBreak())
    story.append(Paragraph("Phase C — Asynchronous Video Detection & Job Lifecycle", h2_style))
    story.append(Paragraph(
        "Because video processing can take several seconds, execute it in a background thread or Celery task. Provide a <code>threading.Event</code> to allow user cancellation:",
        body_style
    ))

    video_job_code = """class VideoJob:
    def __init__(self, job_id: str, path: str):
        self.job_id = job_id
        self.source_path = path
        self.cancel_event = threading.Event()
        self.progress = {"percent": 0.0, "status": "queued"}
        self.result = None

    def on_progress(self, info: ProgressInfo):
        self.progress = {"percent": info.percent_complete, "fps": info.current_fps, "status": info.status}

def worker(job: VideoJob, service: VisionService):
    job.result = service.detect_video(
        source_path=job.source_path,
        progress_callback=job.on_progress,
        cancel_event=job.cancel_event,
        raise_on_cancel=False   # Returns result with status='cancelled' cleanly
    )"""

    story.append(Table([[Paragraph(video_job_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(PageBreak())

    # ==================================================================
    # 5. COPY-READY CODE EXAMPLES
    # ==================================================================
    story.append(Paragraph("5. Copy-Ready Code Examples for FastAPI & React", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph("FastAPI Global Exception Handlers Mapping CV Errors", h2_style))
    story.append(Paragraph(
        "Register these handlers in <code>backend/app/main.py</code> to automatically convert CV exceptions into standard HTTP status codes:",
        body_style
    ))

    exc_handler_code = """from fastapi.responses import JSONResponse
from app.services.vision.errors import (
    VisionServiceError, VideoNotFoundError, InvalidInputFormatError,
    ImageDecodeError, VideoDurationExceededError, VideoFrameCountExceededError,
    JobCancelledError, JobTimeoutError, ModelNotLoadedError
)

def register_exception_handlers(app: FastAPI):
    @app.exception_handler(VideoNotFoundError)
    async def not_found_handler(request: Request, exc: VideoNotFoundError):
        return JSONResponse(status_code=404, content={"error": "Not Found", "detail": str(exc)})

    @app.exception_handler(InvalidInputFormatError)
    async def bad_request_handler(request: Request, exc: InvalidInputFormatError):
        return JSONResponse(status_code=400, content={"error": "Bad Request", "detail": str(exc)})

    @app.exception_handler((ImageDecodeError, VideoDurationExceededError, VideoFrameCountExceededError))
    async def unprocessable_handler(request: Request, exc: VisionServiceError):
        return JSONResponse(status_code=422, content={"error": "Unprocessable Entity", "detail": str(exc)})

    @app.exception_handler(JobCancelledError)
    async def cancelled_handler(request: Request, exc: JobCancelledError):
        return JSONResponse(status_code=409, content={"error": "Conflict", "detail": "Job cancelled by user"})

    @app.exception_handler(JobTimeoutError)
    async def timeout_handler(request: Request, exc: JobTimeoutError):
        return JSONResponse(status_code=504, content={"error": "Gateway Timeout", "detail": str(exc)})

    @app.exception_handler(ModelNotLoadedError)
    async def unavailable_handler(request: Request, exc: ModelNotLoadedError):
        return JSONResponse(status_code=503, content={"error": "Service Unavailable", "detail": str(exc)})"""

    story.append(Table([[Paragraph(exc_handler_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(Spacer(1, 6))
    story.append(Paragraph("React HTML5 Video Streaming Component with Faststart", h2_style))
    story.append(Paragraph(
        "Because videos are encoded with the Faststart <code>moov</code> atom at the start of the file, React can stream them immediately without waiting for download:",
        body_style
    ))

    react_video_code = """import React from 'react';

interface VideoPlayerProps {
  annotatedVideoUrl: string; // e.g. "/outputs/job_123_annotated.mp4"
}

export const RoadVideoPlayer: React.FC<VideoPlayerProps> = ({ annotatedVideoUrl }) => {
  return (
    <div className="rounded-lg overflow-hidden border border-slate-700 bg-slate-900 shadow-lg">
      <video
        controls
        playsInline
        preload="metadata"
        className="w-full h-auto"
      >
        <source src={`http://localhost:8000${annotatedVideoUrl}`} type="video/mp4" />
        Your browser does not support HTML5 MP4 video playback.
      </video>
    </div>
  );
};"""

    story.append(Table([[Paragraph(react_video_code.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 5),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(PageBreak())

    # ==================================================================
    # 6. OWNERSHIP DEMARCATION MATRIX
    # ==================================================================
    story.append(Paragraph("6. Engineering Ownership Demarcation Matrix", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "To ensure clean collaboration between separate repositories without stepping on code ownership, the boundary between Ram and Shakib is strictly defined:",
        body_style
    ))

    matrix_data = [
        [Paragraph("Subsystem Component", tbl_cell_header), Paragraph("Lead Owner", tbl_cell_header), Paragraph("Current Status", tbl_cell_header), Paragraph("Description & Responsibility", tbl_cell_header)],
        [Paragraph("YOLO26m Model & Weights", tbl_cell_bold), Paragraph("Ram", tbl_cell), Paragraph("COMPLETE", tbl_cell_bold), Paragraph("models/weights/yolo26m.pt (SHA-256 verified)", tbl_cell)],
        [Paragraph("Computer Vision Pipeline", tbl_cell_bold), Paragraph("Ram", tbl_cell), Paragraph("COMPLETE", tbl_cell_bold), Paragraph("backend/app/services/vision/** (All 14 defects resolved)", tbl_cell)],
        [Paragraph("FFmpeg Stream Encoding", tbl_cell_bold), Paragraph("Ram", tbl_cell), Paragraph("COMPLETE", tbl_cell_bold), Paragraph("H.264 High profile, yuv420p, Faststart moov placement", tbl_cell)],
        [Paragraph("CV Unit & Regression Tests", tbl_cell_bold), Paragraph("Ram", tbl_cell), Paragraph("COMPLETE", tbl_cell_bold), Paragraph("backend/tests/** (94 / 94 tests passing)", tbl_cell)],
        [Paragraph("FastAPI Application & Lifespan", tbl_cell_bold), Paragraph("Shakib", tbl_cell), Paragraph("PENDING", tbl_cell_bold), Paragraph("backend/app/main.py (App startup, CORS, static mounts)", tbl_cell)],
        [Paragraph("REST API Endpoints", tbl_cell_bold), Paragraph("Shakib", tbl_cell), Paragraph("PENDING", tbl_cell_bold), Paragraph("POST /api/detect/image, POST /api/detect/video, progress routes", tbl_cell)],
        [Paragraph("SQLite Database & Schema", tbl_cell_bold), Paragraph("Shakib", tbl_cell), Paragraph("PENDING", tbl_cell_bold), Paragraph("Inspections table, detection records, timestamps, SQLite models", tbl_cell)],
        [Paragraph("Background Job Orchestration", tbl_cell_bold), Paragraph("Shakib", tbl_cell), Paragraph("PENDING", tbl_cell_bold), Paragraph("Thread pool or Celery worker for async video processing", tbl_cell)],
        [Paragraph("React Dashboard Frontend", tbl_cell_bold), Paragraph("Shakib", tbl_cell), Paragraph("PENDING", tbl_cell_bold), Paragraph("Upload forms, bounding box overlays, progress bar, video player", tbl_cell)],
        [Paragraph("End-to-End System Integration", tbl_cell_bold), Paragraph("Joint (Ram + Shakib)", tbl_cell), Paragraph("READY TO START", tbl_cell_bold), Paragraph("Joint acceptance testing and browser-to-GPU verification", tbl_cell)],
    ]

    mat_table = Table(matrix_data, colWidths=[120, 60, 74, 250])
    mat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(mat_table)

    story.append(PageBreak())

    # ==================================================================
    # 7. INTEGRATION ARCHITECTURE DIAGRAM
    # ==================================================================
    story.append(Paragraph("7. End-to-End System Architecture Diagram", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    arch_diagram_text = """+-----------------------------------------------------------------------------------------+
|                                    REACT FRONTEND (Shakib)                             |
|  - Image / Video Upload UI           - HTML5 Video Player (Streaming)                   |
|  - Confidence Slider [0.10, 0.90]    - Damage Summary Dashboard & Progress Bar         |
+--------------------------------------------+--------------------------------------------+
                                             | HTTP Multipart Uploads / JSON REST API
+--------------------------------------------v--------------------------------------------+
|                                   FASTAPI BACKEND (Shakib)                              |
|  - app.main: Lifespan Singleton      - /api/detect/image: Synchronous Endpoint          |
|  - CORS & StaticFiles (/outputs)     - /api/detect/video: Asynchronous Background Job   |
|  - SQLite Database: Results & State  - Error Translation: VisionServiceError -> HTTP   |
+--------------------------------------------+--------------------------------------------+
                                             | In-Memory Method Calls (Zero IPC Overhead)
+--------------------------------------------v--------------------------------------------+
|                         COMPUTER VISION SUBSYSTEM (Ram - VERIFIED)                      |
|                                                                                         |
|   +----------------------------------+       +------------------------------------+     |
|   |          VisionService           | ----> |           ModelManager             |     |
|   | (High-Level Unified Facade)      |       | - YOLO26m (640px)                  |     |
|   +-----------------+----------------+       | - Native NMS-Free Head             |     |
|                     |                        | - Dynamic Device: CUDA (RTX 5060)  |     |
|         +-----------+-----------+            +-----------------+------------------+     |
|         |                       |                              |                        |
|   +-----v-------+       +-------v--------+                     | Model Forward Pass     |
|   | ImageEngine |       |  VideoEngine   | <-------------------+ (~23 ms / frame)       |
|   | - Decode    |       | - Frame Loop   |                                              |
|   | - Validate  |       | - FFmpeg Pipe  | ----> H.264 High / yuv420p / +faststart      |
|   | - Annotate  |       | - Watchdog     |       Output: data/outputs/<safe_name>.mp4   |
|   +-------------+       +----------------+                                              |
+-----------------------------------------------------------------------------------------+"""

    story.append(Table([[Paragraph(arch_diagram_text.replace('\n', '<br/>').replace(' ', '&nbsp;'), code_style)]],
                       colWidths=[504],
                       style=[('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
                              ('PADDING', (0, 0), (-1, -1), 6),
                              ('BOX', (0, 0), (-1, -1), 1, PRIMARY)]))

    story.append(PageBreak())

    # ==================================================================
    # 8. COMPLETE INTEGRATION CHECKLIST
    # ==================================================================
    story.append(Paragraph("8. Complete Integration Acceptance Checklist", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    chk_data = [
        [Paragraph("ID", tbl_cell_header), Paragraph("Integration Verification Task", tbl_cell_header), Paragraph("Owner", tbl_cell_header), Paragraph("Expected Verification Result", tbl_cell_header), Paragraph("Status", tbl_cell_header)],
        [Paragraph("CHK-01", tbl_cell_bold), Paragraph("Model Checkpoint File & Hash", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("SHA-256 matches 1BC41287...D233 exactly", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-02", tbl_cell_bold), Paragraph("Automated Test Suite Execution", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("94 / 94 unit/regression tests pass in < 12s", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-03", tbl_cell_bold), Paragraph("Four Canonical Damage Classes", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("D00, D10, D20, D40 verified across all CV modules", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-04", tbl_cell_bold), Paragraph("GPU Inference Latency Verification", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("Forward pass < 30 ms (RTX 5060: 23.1 ms)", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-05", tbl_cell_bold), Paragraph("GPU Video Throughput Verification", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("Processing speed > 50 FPS (RTX 5060: 60.9 FPS)", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-06", tbl_cell_bold), Paragraph("Faststart MP4 Header Verification", tbl_cell), Paragraph("Ram", tbl_cell), Paragraph("moov atom at byte 32 before mdat", tbl_cell), Paragraph("DONE", tbl_cell_bold)],
        [Paragraph("CHK-07", tbl_cell_bold), Paragraph("FastAPI Lifespan Startup Event", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("VisionService loads on startup, status returns 200", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-08", tbl_cell_bold), Paragraph("Synchronous Image API Route", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("POST /api/detect/image returns structured JSON + URL", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-09", tbl_cell_bold), Paragraph("Invalid Input Error Rejections", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("0-byte files return 400; corrupt images return 422", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-10", tbl_cell_bold), Paragraph("Background Video Detection Job", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("POST /api/detect/video returns job_id and status queued", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-11", tbl_cell_bold), Paragraph("Video Progress Polling Endpoint", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("GET /api/detect/video/{id}/progress returns % and FPS", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-12", tbl_cell_bold), Paragraph("Video Mid-Stream Cancellation", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("POST /cancel halts job and unlinks partial outputs", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-13", tbl_cell_bold), Paragraph("Browser Video Playback in React", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("Annotated MP4 streams instantly in HTML5 <video>", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-14", tbl_cell_bold), Paragraph("SQLite Metadata Persistence", tbl_cell), Paragraph("Shakib", tbl_cell), Paragraph("Damage counts, timestamp, media paths saved to DB", tbl_cell), Paragraph("PENDING", tbl_cell_bold)],
        [Paragraph("CHK-15", tbl_cell_bold), Paragraph("End-to-End Image Demonstration", tbl_cell), Paragraph("Joint", tbl_cell), Paragraph("User uploads image in UI, sees defect boxes & counts", tbl_cell), Paragraph("JOINT", tbl_cell_bold)],
        [Paragraph("CHK-16", tbl_cell_bold), Paragraph("End-to-End Video Demonstration", tbl_cell), Paragraph("Joint", tbl_cell), Paragraph("User uploads video in UI, sees progress & streams output", tbl_cell), Paragraph("JOINT", tbl_cell_bold)],
    ]

    ch_table = Table(chk_data, colWidths=[36, 130, 50, 230, 58])
    ch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), DARK_BLUE),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_LIGHT),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, BORDER_LIGHT),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, BG_LIGHT]),
        ('PADDING', (0, 0), (-1, -1), 3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(ch_table)

    story.append(PageBreak())

    # ==================================================================
    # 9. FASTEST SEQUENTIAL INTEGRATION PATH
    # ==================================================================
    story.append(Paragraph("9. Fastest Sequential Integration Path", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    story.append(Paragraph(
        "To achieve a working full-stack demonstration in the shortest possible time, follow this strict 8-step critical path:",
        body_style
    ))

    seq_steps = [
        ("Step 1: Setup & Import Verification", "Ensure virtual environment has requirements.txt installed. Run <code>python -c 'from app.services.vision import VisionService; print(VisionService().get_model_status())'</code> to verify model loads on GPU."),
        ("Step 2: FastAPI Lifespan Wiring", "Add VisionService singleton initialization to app.main lifespan. Mount <code>/outputs</code> to serve data/outputs via StaticFiles."),
        ("Step 3: Image Detection API Endpoint", "Implement <code>POST /api/detect/image</code> using the copy-ready snippet in Section 5. Test with curl or Postman using Japan_000000.jpg."),
        ("Step 4: React Image Upload Component", "Build minimal file picker and image viewer. Display annotated image and damage count cards. (Milestone: First working browser demo!)."),
        ("Step 5: Video Detection Background Job", "Implement <code>POST /api/detect/video</code> and background worker using threading.Event. Wire progress callback."),
        ("Step 6: Video Progress & Cancellation Routes", "Expose <code>GET /api/detect/video/{id}/progress</code> and <code>POST /cancel</code>. Test with sample video."),
        ("Step 7: React Video Player Integration", "Embed HTML5 <code><video></code> tag pointing to annotated video URL. Confirm instant streaming without buffering delay."),
        ("Step 8: SQLite Persistence & History", "Save inspection summaries to SQLite database. Render history table in React dashboard."),
    ]

    for title, desc in seq_steps:
        story.append(Paragraph(f"<b>{title}:</b> {desc}", bullet_style))

    story.append(PageBreak())

    # ==================================================================
    # 10. ARCHITECTURAL LIMITATIONS & WARNINGS
    # ==================================================================
    story.append(Paragraph("10. Architectural Limitations, Policy Constraints & Warnings", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    warnings_list = [
        ("Full Application Integration is Not Yet Executed", "Ram's repository houses the Computer Vision subsystem. Shakib's application layer (FastAPI routes, SQLite DB, React UI) has not yet been connected or executed end-to-end. Full application readiness remains pending until this integration occurs."),
        ("Shakib's Independent Repository Uninspected", "Shakib is developing his application layer in a separate repository. Interfaces must adhere strictly to Section 3 of this document to prevent interface divergence."),
        ("Confidence Range Policy (Engine Clamping vs API Rejection)", "The CV engine enforces a clamp-and-warn policy for confidence values outside [0.10, 0.90] to avoid runtime crashes. However, Shakib's API boundary MUST reject invalid requests with HTTP 422 Unprocessable Entity rather than relying on silent engine clamping."),
        ("Operational Frame Cap (MAX_VIDEO_FRAME_CAP = 3600)", "Videos exceeding 60 seconds or 3,600 frames are rejected with VideoFrameCountExceededError (HTTP 422) to prevent memory exhaustion on the host."),
        ("832px Model Resolution is Experimental", "The 832px experiment evaluated in Stage 4 showed a 69% increase in latency without significant mAP gains. The production checkpoint yolo26m.pt is trained and calibrated strictly for 640px."),
        ("Held-Out Test Split Isolation", "The held-out test split (test/ split) is strictly reserved for independent final evaluation. It must never be used for hyperparameter tuning, confidence threshold selection, or iterative prompt engineering."),
    ]

    for title, desc in warnings_list:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", bullet_style))

    story.append(Spacer(1, 14))

    # ==================================================================
    # 11. DIRECT COLLABORATIVE MESSAGE TO SHAKIB
    # ==================================================================
    story.append(Paragraph("11. Direct Collaborative Message to Shakib", h1_style))
    story.append(HRFlowable(width="100%", thickness=1, color=DARK_BLUE, spaceBefore=2, spaceAfter=8))

    collab_box = [
        [Paragraph("""<b>Hey Shakib,</b><br/><br/>
I'm excited to hand off the RoadVision Computer Vision Subsystem to you! Everything on the AI/CV side is 100% complete, fully hardened, and verified on real hardware.<br/><br/>
<b>Here is what is ready for you right now:</b><br/>
1. The production model (<code>models/weights/yolo26m.pt</code>) is trained, verified, and running on the RTX 5060 GPU with an inference forward pass of only 23 ms per image and over 60 FPS for full video processing.<br/>
2. All 14 defects from earlier audits have been resolved. The full test suite of 94 automated tests passes in under 9 seconds.<br/>
3. The video engine encodes web-optimized H.264 MP4 with the Faststart <code>moov</code> atom at the start of the file, meaning videos will stream in React immediately without waiting for download.<br/>
4. The service facade is clean: all you need to call is <code>vision_service.detect_image(...)</code> and <code>vision_service.detect_video(...)</code>.<br/><br/>
<b>What I suggest you implement first:</b><br/>
Start with Step 1 and Step 2 from Section 9: wire <code>VisionService</code> into your FastAPI lifespan and build the <code>POST /api/detect/image</code> endpoint. Once that's up, wire up the basic React image upload page. Seeing the first road damage bounding boxes render in the browser will give us a huge milestone win!<br/><br/>
Whenever you're ready to run joint acceptance tests against the API, let me know and we will knock out CHK-07 through CHK-16 together.<br/><br/>
Best regards,<br/>
<b>Ram (Senior Computer Vision Engineer)</b>""", body_style)]
    ]

    collab_table = Table(collab_box, colWidths=[504])
    collab_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BG_LIGHT),
        ('BOX', (0, 0), (-1, -1), 1, ACCENT),
        ('PADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(collab_table)

    # Build the PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {output_path}")


if __name__ == "__main__":
    out_file = Path("docs/integration/ROADVISION_SHAKIB_FINAL_INTEGRATION_HANDOFF.pdf")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(out_file)
