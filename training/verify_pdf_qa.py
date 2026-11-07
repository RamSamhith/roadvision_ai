import fitz

doc = fitz.open("docs/integration/ROADVISION_SHAKIB_FINAL_INTEGRATION_HANDOFF.pdf")
print(f"Total pages in deliverable: {len(doc)}")

# 1. Check for old incorrect text
old_terms = [
    "4,874",
    "0.563",
    "@app.exception_handler((ImageDecodeError",
]

for term in old_terms:
    found = False
    for i, p in enumerate(doc):
        if term in p.get_text():
            print(f"WARNING: Old term '{term}' still found on page {i+1}!")
            found = True
    if not found:
        print(f"CONFIRMED: Old term '{term}' is completely removed.")

# 2. Check for required new accurate content
required_checks = [
    (4, "47,420", "Raw acquired images"),
    (4, "23,767", "Prepared eligible pairs"),
    (4, "0.630", "Validation mAP50"),
    (4, "0.619", "Held-out test mAP50"),
    (6, "def detect_image", "detect_image signature"),
    (6, "def detect_video", "detect_video signature"),
    (6, "def get_status", "get_status signature"),
    (8, "run_in_threadpool", "Non-blocking threadpool in image endpoint"),
    (8, 'VisionService(primary_device="cuda")', "Actual service constructor"),
    (9, "run_video_job_worker", "Video job worker"),
    (10, "@app.exception_handler(VideoNotFoundError)", "Individual exception handler"),
    (10, "RoadVideoPlayer", "React Video Player component"),
    (10, "src={annotatedVideoUrl}", "Real video src binding"),
    (10, "<source src={annotatedVideoUrl}", "Real source tag"),
    (14, "s.get_status()", "Step 1 get_status call"),
    (15, "0.10", "Min confidence"),
    (15, "0.90", "Max confidence"),
]

for pg, term, desc in required_checks:
    p_text = doc[pg - 1].get_text()
    if term in p_text:
        print(f"CONFIRMED on Page {pg}: {desc} (found '{term}')")
    else:
        print(f"FAILED on Page {pg}: {desc} (missing '{term}')")

# 3. Check every page line count and headers/footers
print("\n=== PAGE SUMMARY ===")
for i, page in enumerate(doc):
    lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
    hdr = lines[0] if lines else "EMPTY"
    ftr = [l for l in lines if "Page " in l]
    footer_text = ftr[-1] if ftr else "N/A"
    print(f"Page {i+1:02d}: {len(page.get_text()):4d} chars, {len(lines):3d} lines | Header: {hdr[:50]} | Footer: {footer_text}")

