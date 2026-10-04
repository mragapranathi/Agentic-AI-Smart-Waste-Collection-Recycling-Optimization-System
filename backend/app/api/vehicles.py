from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.entities import Vehicle
from backend.app.schemas.pydantic_models import VehicleCreate, VehicleUpdate, VehicleResponse

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])

@router.get("", response_model=List[VehicleResponse])
def get_vehicles(
    status: Optional[str] = None,
    waste_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Vehicle)
    if status:
        query = query.filter(Vehicle.status == status)
    vehicles = query.all()

    if waste_type:
        filtered = []
        for v in vehicles:
            types = v.supported_waste_types
            if isinstance(types, list) and (waste_type in types or "All" in types):
                filtered.append(v)
        return filtered

    return vehicles

@router.post("", response_model=VehicleResponse, status_code=201)
def create_vehicle(v_in: VehicleCreate, db: Session = Depends(get_db)):
    existing = db.query(Vehicle).filter(Vehicle.vehicle_id == v_in.vehicle_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Vehicle '{v_in.vehicle_id}' already exists.")

    veh = Vehicle(**v_in.dict())
    db.add(veh)
    db.commit()
    db.refresh(veh)
    return veh

@router.get("/{id_or_vid}", response_model=VehicleResponse)
def get_vehicle(id_or_vid: str, db: Session = Depends(get_db)):
    if id_or_vid.isdigit():
        veh = db.query(Vehicle).filter(Vehicle.id == int(id_or_vid)).first()
    else:
        veh = db.query(Vehicle).filter(Vehicle.vehicle_id == id_or_vid).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")
    return veh

@router.put("/{id_or_vid}", response_model=VehicleResponse)
def update_vehicle(id_or_vid: str, v_update: VehicleUpdate, db: Session = Depends(get_db)):
    if id_or_vid.isdigit():
        veh = db.query(Vehicle).filter(Vehicle.id == int(id_or_vid)).first()
    else:
        veh = db.query(Vehicle).filter(Vehicle.vehicle_id == id_or_vid).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    for k, v in v_update.dict(exclude_unset=True).items():
        setattr(veh, k, v)

    db.commit()
    db.refresh(veh)
    return veh

@router.delete("/{id_or_vid}")
def delete_vehicle(id_or_vid: str, db: Session = Depends(get_db)):
    if id_or_vid.isdigit():
        veh = db.query(Vehicle).filter(Vehicle.id == int(id_or_vid)).first()
    else:
        veh = db.query(Vehicle).filter(Vehicle.vehicle_id == id_or_vid).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehicle not found.")

    db.delete(veh)
    db.commit()
    return {"success": True, "message": f"Vehicle {id_or_vid} deleted successfully."}

