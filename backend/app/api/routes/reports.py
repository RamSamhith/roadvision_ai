"""Inspection report generation and export endpoints (PDF & CSV)."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Query, Request, Response
from fastapi.responses import Response

from app.database.inspections import get_inspection, list_inspections
from app.errors import ApiError
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])
log = logging.getLogger("roadvision.api.reports")


@router.get("/inspection/{inspection_id}/pdf")
def download_inspection_pdf(inspection_id: int, request: Request) -> Response:
    """Generate and return a professional PDF report for an inspection session."""
    settings = request.app.state.settings
    service = ReportService(settings)
    pdf_bytes = service.generate_inspection_pdf(inspection_id)
    filename = f"roadvision_report_inspection_{inspection_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/csv")
def export_inspections_csv(
    request: Request,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
) -> Response:
    """Export tabular history records in CSV format."""
    settings = request.app.state.settings
    service = ReportService(settings)
    inspections = list_inspections(settings, limit=limit, offset=offset)
    csv_text = service.export_history_csv(inspections)
    filename = "roadvision_inspections_export.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

