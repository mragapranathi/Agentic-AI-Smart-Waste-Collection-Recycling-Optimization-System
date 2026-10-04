from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.pydantic_models import PriorityItem, PriorityCalculateRequest
from backend.app.services.priority_engine import PriorityEngine

router = APIRouter(prefix="/priorities", tags=["Collection Priorities"])

@router.get("", response_model=List[PriorityItem])
def get_priorities(db: Session = Depends(get_db)):
    return PriorityEngine.calculate_all_priorities(db)

@router.post("/calculate", response_model=List[PriorityItem])
def calculate_priorities(payload: Optional[PriorityCalculateRequest] = None, db: Session = Depends(get_db)):
    return PriorityEngine.calculate_all_priorities(db)
