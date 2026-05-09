from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app import models, schemas


router = APIRouter(
    tags=["Technicians"]
)


@router.post("/technicians", status_code=status.HTTP_200_OK)
def create_technician(technician: schemas.TechnicianCreate, db: Session = Depends(get_db)):
    """
    Create a new technician.
    """
    try:
        new_technician = models.Technician(
            technician_name=technician.technician_name,
            technician_skill=technician.technician_skill,
            technician_location=technician.technician_location,
            technician_status=technician.technician_status
        )

        db.add(new_technician)
        db.commit()
        db.refresh(new_technician)

        return {
            "message": "Technician created successfully",
            "technician_id": new_technician.technician_id,
            "technician": new_technician
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating technician"
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )


@router.get("/technicians")
def get_all_technicians(db: Session = Depends(get_db)):
    """
    Get all technicians.
    """
    try:
        technicians = db.query(models.Technician).order_by(models.Technician.technician_id.desc()).all()

        return {
            "message": "Technicians fetched successfully",
            "count": len(technicians),
            "technicians": technicians
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching technicians"
        )


@router.get("/technicians/{technician_id}")
def get_technician_by_id(technician_id: int, db: Session = Depends(get_db)):
    """
    Get one technician by ID.
    """
    try:
        technician = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()

        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Technician not found"
            )

        return {
            "message": "Technician fetched successfully",
            "technician": technician
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching technician"
        )


@router.put("/technicians/{technician_id}")
def update_technician(technician_id: int, technician_data: schemas.TechnicianCreate, db: Session = Depends(get_db)):
    """
    Update technician details.
    """
    try:
        technician = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()

        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Technician not found"
            )

        technician.technician_name = technician_data.technician_name
        technician.technician_skill = technician_data.technician_skill
        technician.technician_location = technician_data.technician_location
        technician.technician_status = technician_data.technician_status

        db.commit()
        db.refresh(technician)

        return {
            "message": "Technician updated successfully",
            "technician": technician
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating technician"
        )


@router.delete("/technicians/{technician_id}")
def delete_technician(technician_id: int, db: Session = Depends(get_db)):
    """
    Delete technician.
    """
    try:
        technician = db.query(models.Technician).filter(models.Technician.technician_id == technician_id).first()

        if not technician:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Technician not found"
            )

        deleted_id = technician.technician_id
        db.delete(technician)
        db.commit()

        return {
            "message": "Technician deleted successfully",
            "deleted_technician_id": deleted_id
        }

    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting technician"
        )
