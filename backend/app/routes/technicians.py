from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from ..database import get_db
from .. import models, schemas

router = APIRouter(
    prefix="/technicians",
    tags=["Technicians"]
)

@router.post("/", response_model=schemas.TechnicianResponse, status_code=status.HTTP_200_OK)
def create_technician(technician: schemas.TechnicianCreate, db: Session = Depends(get_db)):
    """
    Register a new technician.
    Prevents duplicate entries based on name and skill.
    """
    try:
        # Check for duplicate
        existing = db.query(models.Technician).filter(
            models.Technician.technician_name == technician.technician_name,
            models.Technician.technician_skill == technician.technician_skill
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Technician with this name and skill already exists"
            )

        new_tech = models.Technician(
            technician_name=technician.technician_name,
            technician_skill=technician.technician_skill,
            technician_location=technician.technician_location,
            technician_status=technician.technician_status
        )

        db.add(new_tech)
        db.commit()
        db.refresh(new_tech)
        return new_tech

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
    Retrieve all technicians currently eligible for assignment.
    """
    techs = db.query(models.Technician).all()
    available_techs = []
    
    for tech in techs:
        # Eligible if AVAILABLE and under workload limit
        is_eligible = (
            tech.technician_status == "AVAILABLE" and 
            tech.current_jobs < tech.max_jobs
        )
        
        available_techs.append({
            "technician": tech.technician_name,
            "status": tech.technician_status,
            "eligible_for_assignment": is_eligible
        })
        
    return available_techs


@router.get("/{technician_id}", response_model=schemas.TechnicianResponse)
def get_technician_by_id(technician_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech
