"""Tests for inspection report generation service and endpoints (PDF & CSV)."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database.inspections import complete_image_inspection, create_image_inspection
from app.main import create_app
from app.services.inference_service import Detection, InferenceResult
from app.services.report_service import ReportService


class FakeImageInference:
    def startup(self) -> None:
        pass

    def detect_image(self, image: Any, confidence: float) -> InferenceResult:
        det = Detection(class_id=3, class_name="D40", confidence=0.88, bbox=(10.0, 20.0, 100.0, 120.0))
        return InferenceResult(model="YOLO26m", detections=(det,), annotated_image=image.copy())


def test_pdf_report_generation_and_content(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, data_dir=tmp_path / "data")
    app = create_app(settings)
    app.state.model_manager = FakeImageInference()

    with TestClient(app) as client:
        # Create an inspection record
        insp_id = create_image_inspection(settings, filename="highway_damage.jpg", confidence=0.25)
        complete_image_inspection(
            settings,
            insp_id,
            model="YOLO26m",
            total_detections=1,
            class_counts={"D00": 0, "D10": 0, "D20": 0, "D40": 1},
            processing_ms=45,
            output_name="test_out.jpg",
        )

        # Generate and download PDF
        res = client.get(f"/api/reports/inspection/{insp_id}/pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "attachment" in res.headers["content-disposition"]
        assert f"inspection_{insp_id}.pdf" in res.headers["content-disposition"]

        pdf_bytes = res.content
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")

        # Parse with PyMuPDF / fitz to verify textual structure
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        assert len(doc) >= 1
        page_text = doc[0].get_text()
        assert "RoadVision AI" in page_text
        assert "Inspection Report" in page_text
        assert "highway_damage.jpg" in page_text
        assert "YOLO26m" in page_text
        assert "D40" in page_text
        assert "Pothole" in page_text
        doc.close()


def test_csv_export_format_and_headers(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, data_dir=tmp_path / "data")
    app = create_app(settings)

    with TestClient(app) as client:
        insp_id = create_image_inspection(settings, filename="road_crack.jpg", confidence=0.25)
        complete_image_inspection(
            settings,
            insp_id,
            model="YOLO26m",
            total_detections=2,
            class_counts={"D00": 2, "D10": 0, "D20": 0, "D40": 0},
            processing_ms=30,
            output_name="out.jpg",
        )

        res = client.get("/api/reports/export/csv")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]
        assert "roadvision_inspections_export.csv" in res.headers["content-disposition"]

        lines = res.text.strip().splitlines()
        assert len(lines) >= 2
        header = lines[0]
        assert "Inspection ID" in header
        assert "Total Detections" in header
        assert "D00 (Longitudinal Crack)" in header

        row = lines[1]
        assert str(insp_id) in row
        assert "road_crack.jpg" in row
        assert "YOLO26m" in row


def test_pdf_report_nonexistent_inspection_returns_404(tmp_path: Path) -> None:
    settings = Settings(project_root=tmp_path, data_dir=tmp_path / "data")
    app = create_app(settings)

    with TestClient(app) as client:
        res = client.get("/api/reports/inspection/999999/pdf")
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "inspection_not_found"

