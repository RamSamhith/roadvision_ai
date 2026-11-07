"""Application Startup and Lifespan Lifecycle Tests (S5-M2).

Tests the backend application startup and shutdown lifecycle per TDD v1.1 §13.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.services.vision import VisionService, get_vision_service
from app.services.vision.types import ModelStatus


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """Lifespan context manager as specified in TDD v1.1 §13."""
    # Startup: initialize vision service
    service = get_vision_service()
    service.initialize()
    yield
    # Shutdown: cleanup


def test_app_startup_success():
    """Verify application startup initializes VisionService and exposes health."""
    app = FastAPI(lifespan=app_lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/model/status")
    def model_status():
        return get_vision_service().get_status().to_dict()

    mock_mgr = MagicMock()
    mock_mgr.active = "YOLO26m"
    mock_mgr.model = MagicMock()
    mock_mgr.device = "cuda:0"
    mock_mgr.models_used = ["YOLO26m"]
    mock_mgr.switched = False
    mock_mgr.errors = {}
    mock_mgr.startup.return_value = True
    mock_mgr.get_status.return_value = ModelStatus(
        active_model="YOLO26m",
        is_available=True,
        device="cuda:0",
        nms_mode="end-to-end (nms=False)",
        classes=["D00", "D10", "D20", "D40"],
        fallback_active=False,
        models_used=["YOLO26m"],
        errors={},
    )

    with patch.object(get_vision_service(), "model_manager", mock_mgr):
        with TestClient(app) as client:
            resp_health = client.get("/api/health")
            assert resp_health.status_code == 200
            assert resp_health.json() == {"status": "ok"}

            resp_status = client.get("/api/model/status")
            assert resp_status.status_code == 200
            data = resp_status.json()
            assert data["active_model"] == "YOLO26m"
            assert data["is_available"] is True


def test_app_startup_model_failure_handling():
    """Verify application startup records error honestly if model cannot be loaded."""
    app = FastAPI(lifespan=app_lifespan)

    mock_mgr = MagicMock()
    mock_mgr.active = None
    mock_mgr.model = None
    mock_mgr.device = "cpu"
    mock_mgr.models_used = []
    mock_mgr.switched = False
    mock_mgr.errors = {"YOLO26m": "FileNotFoundError: checkpoint missing"}
    mock_mgr.startup.return_value = False
    mock_mgr.get_status.return_value = ModelStatus(
        active_model=None,
        is_available=False,
        device="cpu",
        nms_mode="end-to-end (nms=False)",
        classes=["D00", "D10", "D20", "D40"],
        fallback_active=False,
        models_used=[],
        errors={"YOLO26m": "FileNotFoundError: checkpoint missing"},
    )

    with patch.object(get_vision_service(), "model_manager", mock_mgr):
        with TestClient(app) as client:
            status = get_vision_service().get_status()
            assert status.is_available is False
            assert "YOLO26m" in status.errors
