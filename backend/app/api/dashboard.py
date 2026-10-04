from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.pydantic_models import DashboardKPIsResponse
from backend.app.services.kpi_service import KPIService

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Operations Center"])

@router.get("/kpis", response_model=DashboardKPIsResponse)
def get_dashboard_kpis(db: Session = Depends(get_db)):
    return KPIService.get_dashboard_kpis(db)
