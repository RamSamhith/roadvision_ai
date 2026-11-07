"""End-to-End Image Detection API Integration Tests (S5-M2).

Tests the full image detection workflow according to TDD v1.1 §10 and PRD v1.1:
Image Upload -> Validation -> VisionService -> Structured Detections ->
Annotated Image -> API Response -> Output File Retrieval.
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
import pytest
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.testclient import TestClient
from PIL import Image

from app.services.vision import (
    ALLOWED_IMAGE_EXTENSIONS,
    CLASS_CODES,
    DEFAULT_CONFIDENCE,
    MAX_CONFIDENCE,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MIN_CONFIDENCE,
    VisionInspectionResult,
    get_vision_service,
)
from app.services.vision.errors import (
    ImageDecodeError,
    ImageDimensionExceededError,
    ImageSizeExceededError,
    ModelUnavailableError,
    UnsupportedImageFormatError,
    VisionServiceError,
)
from app.services.vision.types import Detection, DetectionResult

# Safe name pattern from TDD v1.1 §10.2
SAFE_NAME = re.compile(r"^[A-Za-z0-9_-]{8,64}\.(jpg|png|mp4)$")


def create_integration_app(output_dir: Path) -> FastAPI:
    """Build a reference FastAPI app implementing TDD v1.1 §10 contracts."""
    app = FastAPI(title="RoadVision AI Image Integration", version="1.0.0")

    # Install TDD v1.1 §10.3 error handlers
    @app.exception_handler(VisionServiceError)
    async def vision_err_handler(request: Request, exc: VisionServiceError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def val_err_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "invalid_parameters",
                    "message": "Invalid request parameters.",
                }
            },
        )

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/model/status")
    def model_status():
        service = get_vision_service()
        return service.get_status().to_dict()

    @app.post("/api/detect/image")
    def detect_image(
        file: UploadFile = File(...),
        conf: float = Form(DEFAULT_CONFIDENCE),
    ):
        # 1. Parameter range validation (PRD v1.1 FR-06: 0.10 to 0.90)
        if conf < MIN_CONFIDENCE or conf > MAX_CONFIDENCE:
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "invalid_parameters",
                        "message": f"Confidence threshold must be between {MIN_CONFIDENCE} and {MAX_CONFIDENCE}.",
                    }
                },
            )

        # 2. Extension check
        filename = file.filename or "upload.jpg"
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise UnsupportedImageFormatError(ext, ALLOWED_IMAGE_EXTENSIONS)

        # 3. Streamed payload size check (TDD v1.1 §10.2)
        raw_bytes = file.file.read()
        if len(raw_bytes) > MAX_IMAGE_BYTES:
            raise ImageSizeExceededError(len(raw_bytes), MAX_IMAGE_BYTES)

        # 4. Generate unique managed output name
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_token = uuid.uuid4().hex[:8]
        out_name = f"{timestamp_str}_{unique_token}.jpg"
        out_path = output_dir / out_name

        # 5. Call VisionService
        service = get_vision_service()
        insp: VisionInspectionResult = service.detect_image(
            image_input=raw_bytes,
            conf=conf,
            filename=filename,
            annotate=True,
            output_path=out_path,
        )

        # 6. Build response matching TDD v1.1 §10.3 ImageResult
        res = insp.result
        return {
            "id": 1,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "input_type": "image",
            "filename": filename,
            "models_used": ",".join(insp.models_used),
            "conf_threshold": conf,
            "nms_mode": "end2end",
            "total_detections": res.total_detections,
            "class_summary": res.class_counts,
            "frames_total": 1,
            "frames_processed": 1,
            "frames_with_detections": 1 if res.total_detections > 0 else 0,
            "processing_ms": int(round(res.inference_time_ms)),
            "output_url": f"/api/results/{out_name}",
            "status": "completed",
            "error_message": None,
            "detections": [d.to_dict() for d in res.detections],
        }

    @app.get("/api/results/{name}")
    def get_result(name: str):
        if not SAFE_NAME.fullmatch(name):
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "invalid_name", "message": "Invalid file name."}},
            )
        target = (output_dir / name).resolve()
        if target.parent != output_dir.resolve() or not target.is_file():
            return JSONResponse(
                status_code=404,
                content={"error": {"code": "not_found", "message": "Output no longer available."}},
            )
        return FileResponse(str(target), media_type="image/jpeg")

    return app


def make_test_image(format_name: str = "JPEG", width: int = 120, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(180, 180, 180))
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    return buf.getvalue()


@pytest.fixture
def client_and_output(tmp_path):
    out_dir = tmp_path / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    app = create_integration_app(out_dir)
    client = TestClient(app)
    return client, out_dir


# -----------------------------------------------------------------------------
# Test Cases
# -----------------------------------------------------------------------------

def test_api_health(client_and_output):
    client, _ = client_and_output
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_api_model_status(client_and_output):
    client, _ = client_and_output
    resp = client.get("/api/model/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "active_model" in data
    assert "classes" in data
    assert data["classes"] == ["D00", "D10", "D20", "D40"]
    assert "nms_mode" in data


def test_api_detect_image_valid_jpg(client_and_output):
    client, out_dir = client_and_output
    raw = make_test_image("JPEG", 200, 200)

    # Mock VisionService to return controlled detection
    mock_res = DetectionResult(
        model="YOLO26m",
        total_detections=1,
        class_counts={"D00": 1, "D10": 0, "D20": 0, "D40": 0},
        detections=[Detection(0, "D00", 0.89, [20.0, 30.0, 80.0, 90.0], "Longitudinal crack")],
        inference_time_ms=25.0,
        image_dimensions=(200, 200),
    )
    mock_insp = VisionInspectionResult(
        result=mock_res,
        annotated_image_bytes=raw,
        annotated_output_path=str(out_dir / "sample.jpg"),
        models_used=["YOLO26m"],
        device="cuda:0",
        success=True,
    )

    with patch.object(get_vision_service(), "detect_image", return_value=mock_insp):
        resp = client.post(
            "/api/detect/image",
            files={"file": ("road.jpg", raw, "image/jpeg")},
            data={"conf": 0.35},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["filename"] == "road.jpg"
        assert data["conf_threshold"] == 0.35
        assert data["total_detections"] == 1
        assert data["class_summary"]["D00"] == 1
        assert data["models_used"] == "YOLO26m"
        assert len(data["detections"]) == 1
        assert data["detections"][0]["class_name"] == "D00"
        assert data["detections"][0]["box"] == [20.0, 30.0, 80.0, 90.0]
        assert data["output_url"].startswith("/api/results/")


def test_api_detect_image_valid_png(client_and_output):
    client, out_dir = client_and_output
    raw = make_test_image("PNG", 150, 150)

    mock_res = DetectionResult(
        model="YOLO26m",
        total_detections=0,
        class_counts={"D00": 0, "D10": 0, "D20": 0, "D40": 0},
        detections=[],
        inference_time_ms=18.0,
        image_dimensions=(150, 150),
    )
    mock_insp = VisionInspectionResult(
        result=mock_res,
        annotated_image_bytes=raw,
        annotated_output_path=str(out_dir / "sample_png.jpg"),
        models_used=["YOLO26m"],
        device="cuda:0",
        success=True,
    )

    with patch.object(get_vision_service(), "detect_image", return_value=mock_insp):
        resp = client.post(
            "/api/detect/image",
            files={"file": ("road_surface.png", raw, "image/png")},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_detections"] == 0
        assert data["frames_with_detections"] == 0
        assert data["class_summary"] == {"D00": 0, "D10": 0, "D20": 0, "D40": 0}


def test_api_detect_image_unsupported_format(client_and_output):
    client, _ = client_and_output
    raw = make_test_image("GIF", 50, 50)
    resp = client.post(
        "/api/detect/image",
        files={"file": ("animation.gif", raw, "image/gif")},
    )
    assert resp.status_code == 415
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "unsupported_image_format"


def test_api_detect_image_corrupt_payload(client_and_output):
    client, _ = client_and_output
    corrupt_bytes = b"NOT_A_VALID_JPEG_STREAM"
    resp = client.post(
        "/api/detect/image",
        files={"file": ("broken.jpg", corrupt_bytes, "image/jpeg")},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "image_decode_failed"


def test_api_detect_image_size_limit(client_and_output):
    client, _ = client_and_output
    oversized = b"0" * (MAX_IMAGE_BYTES + 1024)
    resp = client.post(
        "/api/detect/image",
        files={"file": ("massive.jpg", oversized, "image/jpeg")},
    )
    assert resp.status_code == 413
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "image_size_exceeded"


def test_api_detect_image_dimension_limit(client_and_output):
    client, _ = client_and_output
    # Create valid JPEG header reporting dimensions exceeding limit
    with patch("app.services.vision.image_engine.validate_image_payload", side_effect=ImageDimensionExceededError(9000, 9000, 8192)):
        raw = make_test_image("JPEG", 100, 100)
        resp = client.post(
            "/api/detect/image",
            files={"file": ("too_wide.jpg", raw, "image/jpeg")},
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "image_dimension_exceeded"


def test_api_detect_image_invalid_confidence(client_and_output):
    client, _ = client_and_output
    raw = make_test_image("JPEG", 100, 100)
    # Range is 0.10 to 0.90
    resp_low = client.post(
        "/api/detect/image",
        files={"file": ("road.jpg", raw, "image/jpeg")},
        data={"conf": 0.05},
    )
    assert resp_low.status_code == 422
    assert resp_low.json()["error"]["code"] == "invalid_parameters"

    resp_high = client.post(
        "/api/detect/image",
        files={"file": ("road.jpg", raw, "image/jpeg")},
        data={"conf": 0.95},
    )
    assert resp_high.status_code == 422
    assert resp_high.json()["error"]["code"] == "invalid_parameters"


def test_api_detect_image_model_unavailable(client_and_output):
    client, _ = client_and_output
    raw = make_test_image("JPEG", 100, 100)
    with patch.object(get_vision_service(), "detect_image", side_effect=ModelUnavailableError("Model not loaded")):
        resp = client.post(
            "/api/detect/image",
            files={"file": ("road.jpg", raw, "image/jpeg")},
        )
        assert resp.status_code == 503
        data = resp.json()
        assert data["error"]["code"] == "model_unavailable"


def test_api_results_retrieval_and_safety(client_and_output):
    client, out_dir = client_and_output
    sample_file = out_dir / "20261107_120000_12345678.jpg"
    sample_file.write_bytes(make_test_image("JPEG", 50, 50))

    # Valid name retrieval
    resp = client.get(f"/api/results/{sample_file.name}")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"

    # Missing file
    resp_missing = client.get("/api/results/20261107_120000_99999999.jpg")
    assert resp_missing.status_code == 404
    assert resp_missing.json()["error"]["code"] == "not_found"

    # Directory traversal attack rejection (URL-encoded traversal and invalid extension)
    resp_traversal = client.get("/api/results/..%2F..%2Fetc%2Fpasswd")
    assert resp_traversal.status_code in (400, 404)
    if resp_traversal.status_code == 400:
        assert resp_traversal.json()["error"]["code"] == "invalid_name"

    resp_invalid_ext = client.get("/api/results/malicious_payload.exe")
    assert resp_invalid_ext.status_code == 400
    assert resp_invalid_ext.json()["error"]["code"] == "invalid_name"
