from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import Bin
from backend.app.schemas.pydantic_models import BinCreate, BinUpdate, BinResponse

router = APIRouter(prefix="/bins", tags=["Smart Bins"])

@router.get("", response_model=List[BinResponse])
def get_bins(
    waste_type: Optional[str] = None,
    operational_status: Optional[str] = None,
    sensor_status: Optional[str] = None,
    min_fill: Optional[float] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Bin)
    if waste_type:
        query = query.filter(Bin.waste_type == waste_type)
    if operational_status:
        query = query.filter(Bin.operational_status == operational_status)
    if sensor_status:
        query = query.filter(Bin.sensor_status == sensor_status)
    if min_fill is not None:
        query = query.filter(Bin.current_fill_percent >= min_fill)
    query = query.order_by(Bin.bin_id)
    if limit:
        query = query.limit(limit)
    return query.all()

@router.post("", response_model=BinResponse, status_code=201)
def create_bin(bin_in: BinCreate, db: Session = Depends(get_db)):
    existing = db.query(Bin).filter(Bin.bin_id == bin_in.bin_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Bin with ID '{bin_in.bin_id}' already exists.")
    
    bin_obj = Bin(**bin_in.dict())
    db.add(bin_obj)
    db.commit()
    db.refresh(bin_obj)
    return bin_obj

@router.get("/{id_or_bin_id}", response_model=BinResponse)
def get_bin(id_or_bin_id: str, db: Session = Depends(get_db)):
    if id_or_bin_id.isdigit():
        bin_obj = db.query(Bin).filter(Bin.id == int(id_or_bin_id)).first()
    else:
        bin_obj = db.query(Bin).filter(Bin.bin_id == id_or_bin_id).first()

    if not bin_obj:
        raise HTTPException(status_code=404, detail="Bin not found")
    return bin_obj

@router.put("/{id_or_bin_id}", response_model=BinResponse)
def update_bin(id_or_bin_id: str, bin_update: BinUpdate, db: Session = Depends(get_db)):
    if id_or_bin_id.isdigit():
        bin_obj = db.query(Bin).filter(Bin.id == int(id_or_bin_id)).first()
    else:
        bin_obj = db.query(Bin).filter(Bin.bin_id == id_or_bin_id).first()

    if not bin_obj:
        raise HTTPException(status_code=404, detail="Bin not found")

    update_data = bin_update.dict(exclude_unset=True)
    for field, val in update_data.items():
        setattr(bin_obj, field, val)

    bin_obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(bin_obj)
    return bin_obj

@router.delete("/{id_or_bin_id}")
def delete_bin(id_or_bin_id: str, db: Session = Depends(get_db)):
    if id_or_bin_id.isdigit():
        bin_obj = db.query(Bin).filter(Bin.id == int(id_or_bin_id)).first()
    else:
        bin_obj = db.query(Bin).filter(Bin.bin_id == id_or_bin_id).first()

    if not bin_obj:
        raise HTTPException(status_code=404, detail="Bin not found")

    db.delete(bin_obj)
    db.commit()
    return {"success": True, "message": f"Bin {id_or_bin_id} deleted."}
