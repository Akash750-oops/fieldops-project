from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Union

from ..database import get_db
from .. import models, schemas
import uuid

router = APIRouter(
    prefix="/technicians",
    tags=["Technicians"]
)

@router.post("/", response_model=Union[schemas.TechnicianResponse, List[schemas.TechnicianResponse]], status_code=status.HTTP_200_OK)
def create_technician(technician: Union[schemas.TechnicianCreate, List[schemas.TechnicianCreate]], db: Session = Depends(get_db)):
    """
    Register one or more new technicians.
    Prevents duplicate entries based on name and skill.
    """
    try:
        # Normalize to list for uniform processing
        tech_list = technician if isinstance(technician, list) else [technician]
        created_techs = []

        for tech_data in tech_list:
            # Check for duplicate
            existing = db.query(models.Technician).filter(
                models.Technician.technician_name == tech_data.technician_name,
                models.Technician.technician_skill == tech_data.technician_skill
            ).first()
            
            if existing:
                if not isinstance(technician, list):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Technician with name '{tech_data.technician_name}' and skill '{tech_data.technician_skill}' already exists"
                    )
                # For bulk, we skip duplicates to avoid failing the whole batch
                continue

            new_tech = models.Technician(
                tech_id=tech_data.tech_id or f"tech-{uuid.uuid4().hex[:8]}", # Use provided or auto-generate
                technician_name=tech_data.technician_name,
                technician_skill=tech_data.technician_skill,
                technician_location=tech_data.technician_location,
                technician_status=tech_data.technician_status
            )
            db.add(new_tech)
            created_techs.append(new_tech)

        db.commit()
        
        # Refresh and return
        for t in created_techs:
            db.refresh(t)
            
        if isinstance(technician, list):
            return created_techs
        else:
            if not created_techs: # Should not happen given logic above but for safety
                 raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Technician already exists")
            return created_techs[0]

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while creating technician: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/", response_model=List[schemas.TechnicianResponse])
def get_all_technicians(db: Session = Depends(get_db)):
    """
    Retrieve all registered technicians.
    """
    try:
        return db.query(models.Technician).all()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error while fetching technicians"
        )

@router.get("/workload", response_model=schemas.WorkloadResponse)
def get_technician_workload(technician_id: int, db: Session = Depends(get_db)):
    """
    Retrieve workload details of a specific technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    return {
        "technician": tech.technician_name,
        "current_jobs": tech.current_jobs,
        "status": tech.technician_status
    }


@router.put("/update-workload", response_model=schemas.WorkloadResponse)
def update_technician_workload(update: schemas.WorkloadUpdate, db: Session = Depends(get_db)):
    """
    Manually update technician workload and synchronize status.
    """
    from ..workload_utils import sync_technician_status
    
    tech = db.query(models.Technician).filter(models.Technician.technician_id == update.technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    if update.current_jobs < 0:
        raise HTTPException(status_code=400, detail="Workload count cannot be negative")
        
    tech.current_jobs = update.current_jobs
    sync_technician_status(tech)
    
    db.commit()
    db.refresh(tech)
    
    return {
        "technician": tech.technician_name,
        "current_jobs": tech.current_jobs,
        "status": tech.technician_status
    }


@router.put("/update-status", response_model=schemas.TechnicianResponse)
def update_technician_status(update: schemas.TechnicianStatusUpdate, db: Session = Depends(get_db)):
    """
    Manually update technician availability status.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == update.technician_id).first()
    if not tech:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Technician not found")
        
    tech.technician_status = update.status
    
    try:
        db.commit()
        db.refresh(tech)
        return tech
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")


@router.get("/validate-workload", response_model=schemas.WorkloadValidationResponse)
def validate_technician_workload_api(technician_id: int, db: Session = Depends(get_db)):
    """
    Validate technician workload conditions and return detailed status.
    """
    from ..validation import get_workload_validation_status
    
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    return get_workload_validation_status(tech)


@router.get("/available", response_model=List[schemas.AvailableTechnicianResponse])
def get_available_technicians(db: Session = Depends(get_db)):
    """
    Retrieve only available technicians with their workload details.
    Excludes BUSY and OFFLINE technicians from the result entirely.
    """
    # Fetch technicians with AVAILABLE or ASSIGNED status (case-insensitive)
    techs = db.query(models.Technician).filter(
        models.Technician.technician_status.in_(["AVAILABLE", "ASSIGNED", "Available", "Assigned"])
    ).all()
    
    result = []
    
    for tech in techs:
        # Eligible if under workload limit
        is_eligible = tech.current_jobs < tech.max_jobs
        
        result.append({
            "technician_id": tech.technician_id,
            "technician": tech.technician_name,
            "skill": tech.technician_skill,
            "location": tech.technician_location,
            "status": tech.technician_status,
            "current_jobs": tech.current_jobs,
            "max_jobs": tech.max_jobs,
            "eligible_for_assignment": is_eligible
        })
        
    return result


@router.get("/{technician_id}", response_model=schemas.TechnicianResponse)
def get_technician_by_id(technician_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech


@router.put("/{technician_id}/availability")
def update_technician_availability(
    technician_id: int,
    update_data: schemas.TechnicianAvailabilityUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the availability status of a technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    # Validation is handled by Pydantic Literal
    tech.technician_status = update_data.technician_status
    db.commit()
    db.refresh(tech)
    
    return {
        "message": "Technician availability updated successfully",
        "technician": {
            "id": tech.technician_id,
            "name": tech.technician_name,
            "technician_status": tech.technician_status
        }
    }

from ..schemas import NotificationPreferencesInput, PreferencesUpdateResponse
from ..services.preferences import get_technician_preferences, update_technician_preferences, DEFAULT_PREFS
from .dispatch import verify_jwt_token
from datetime import datetime, timezone

@router.get("/{id}/preferences")
async def get_preferences(
    id: str,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    prefs = get_technician_preferences(db, id)
    return {
        "tech_id": id,
        "preferences": prefs,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "self"
    }

@router.patch("/{id}/preferences", response_model=PreferencesUpdateResponse)
async def update_preferences(
    id: str,
    payload: NotificationPreferencesInput,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    try:
        updated_prefs = update_technician_preferences(
            db=db,
            tech_id=id,
            new_prefs=payload.model_dump(),
            updated_by="self"
        )
        if not updated_prefs:
            raise HTTPException(status_code=404, detail="Technician not found")
            
        return {
            "tech_id": id,
            "preferences": updated_prefs,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "self"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": "VALIDATION_FAILED", "message": str(e)})

@router.post("/{id}/preferences/reset", response_model=PreferencesUpdateResponse)
async def reset_preferences(
    id: str,
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_jwt_token)
):
    updated_prefs = update_technician_preferences(
        db=db,
        tech_id=id,
        new_prefs=DEFAULT_PREFS,
        updated_by="admin_reset"
    )
    if not updated_prefs:
        raise HTTPException(status_code=404, detail="Technician not found")
        
    return {
        "tech_id": id,
        "preferences": updated_prefs,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": "admin_reset"
    }

@router.put("/{technician_id}", response_model=schemas.TechnicianResponse)
def update_technician(technician_id: int, technician: schemas.TechnicianCreate, db: Session = Depends(get_db)):
    """
    Update a technician's details.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    tech.technician_name = technician.technician_name
    tech.technician_skill = technician.technician_skill
    tech.technician_location = technician.technician_location
    tech.technician_status = technician.technician_status
    
    try:
        db.commit()
        db.refresh(tech)
        return tech
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/{technician_id}", status_code=status.HTTP_200_OK)
def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    """
    Delete a technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    try:
        db.delete(tech)
        db.commit()
        return {"message": "Technician deleted successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.put("/{technician_id}/status")
def update_technician_status_by_id(
    technician_id: int,
    update_data: schemas.TechnicianAvailabilityUpdate,
    db: Session = Depends(get_db)
):
    """
    Update the status of a technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    
    tech.technician_status = update_data.technician_status
    
    try:
        db.commit()
        db.refresh(tech)
        return {
            "message": "Technician status updated successfully",
            "technician": {
                "id": tech.technician_id,
                "name": tech.technician_name,
                "technician_status": tech.technician_status
            }
        }
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")


