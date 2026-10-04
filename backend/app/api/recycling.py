from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.pydantic_models import RecyclingAnalyticsResponse, RecyclingRecordCreate, RecyclingRecordResponse
from backend.app.services.recycling_service import RecyclingService
from backend.app.models.entities import RecyclingRecord

router = APIRouter(prefix="/recycling", tags=["Recycling & Segregation"])

@router.get("/analytics", response_model=RecyclingAnalyticsResponse)
def get_recycling_analytics(days: int = 30, db: Session = Depends(get_db)):
    return RecyclingService.get_recycling_analytics(db, days=days)

@router.get("/records", response_model=list[RecyclingRecordResponse])
def get_recycling_records(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(RecyclingRecord).order_by(RecyclingRecord.created_at.desc()).limit(limit).all()

@router.post("/records", response_model=RecyclingRecordResponse, status_code=201)
def add_recycling_record(payload: RecyclingRecordCreate, db: Session = Depends(get_db)):
    rr = RecyclingRecord(**payload.dict())
    db.add(rr)
    db.commit()
    db.refresh(rr)
    return rr

