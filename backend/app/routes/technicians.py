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

@router.get("/{technician_id}", response_model=schemas.TechnicianResponse)
def get_technician_by_id(technician_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details of a specific technician.
    """
    tech = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()
    if not tech:
        raise HTTPException(status_code=404, detail="Technician not found")
    return tech
