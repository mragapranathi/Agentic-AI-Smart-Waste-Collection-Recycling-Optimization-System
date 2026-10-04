import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.pydantic_models import ReportGenerateRequest, ReportResponse
from backend.app.services.report_generator import PDFReportGenerator
from backend.app.services.kpi_service import KPIService

router = APIRouter(prefix="/reports", tags=["Reports & Audits"])

# Use absolute path so PDF download works regardless of CWD (incl. pytest)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # repo root
REPORTS_DIR = str(_BACKEND_ROOT / "data" / "reports")

@router.post("/generate", response_model=ReportResponse)
def generate_report(payload: Optional[ReportGenerateRequest] = None, db: Session = Depends(get_db)):
    period = payload.period_days if payload else 7
    title = payload.title if payload else "Municipal Waste Collection & Recycling Optimization Audit Report"

    os.makedirs(REPORTS_DIR, exist_ok=True)
    report_id = f"RPT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:4]}"
    filename = f"{report_id}.pdf"
    file_path = os.path.join(REPORTS_DIR, filename)

    try:
        PDFReportGenerator.generate_operations_report(
            db=db,
            output_path=file_path,
            period_days=period,
            title=title
        )
        kpis = KPIService.get_dashboard_kpis(db)
        return ReportResponse(
            report_id=report_id,
            generated_at=datetime.utcnow(),
            download_url=f"/api/reports/download/{filename}",
            summary=kpis
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

@router.get("/download/{filename}")
def download_report(filename: str):
    file_path = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Requested report PDF file does not exist.")
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=filename
    )

@router.get("")
def list_reports():
    os.makedirs(REPORTS_DIR, exist_ok=True)
    files = [f for f in os.listdir(REPORTS_DIR) if f.endswith(".pdf")]
    return [
        {
            "filename": f,
            "report_id": f.replace(".pdf", ""),
            "download_url": f"/api/reports/download/{f}"
        }
        for f in sorted(files, reverse=True)
    ]
