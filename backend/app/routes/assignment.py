from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List

from ..database import get_db
from .. import models, schemas, utils

router = APIRouter(
    tags=["Assignment"]
)

@router.get("/technicians/nearest", response_model=schemas.NearestTechnicianResponse)
def get_nearest_technician(job_id: int, db: Session = Depends(get_db)):
    """
    Identify the nearest available technician based on skill and location.
    """
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Filter technicians by skill, availability, and workload
    technicians = db.query(models.Technician).filter(
        models.Technician.technician_skill == job.required_skill,
        models.Technician.technician_status == "AVAILABLE",
        models.Technician.current_jobs < models.Technician.max_jobs
    ).all()

    if not technicians:
        raise HTTPException(
            status_code=404, 
            detail=f"No available technicians found with skill: {job.required_skill}"
        )

    # Calculate distances
    tech_distances = []
    for tech in technicians:
        dist = utils.calculate_distance(job.location, tech.technician_location)
        tech_distances.append((tech, dist))

    # Sort by distance
    tech_distances.sort(key=lambda x: x[1])
    
    nearest_tech, min_dist = tech_distances[0]
    
    return {
        "technician": nearest_tech,
        "distance": min_dist
    }

@router.post("/assign-job")
def assign_job(assignment: schemas.TechnicianAssignment, db: Session = Depends(get_db)):
    """
    Assign a technician to a job with full validation.
    Checks:
    - Job existence
    - Technician existence
    - Technician availability (BUSY/OFFLINE)
    - Skill match
    - Duplicate assignment prevention
    """
    try:
        # 1. Fetch Job
        job = db.query(models.Job).filter(models.Job.id == assignment.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        # 2. Fetch Technician
        technician = db.query(models.Technician).filter(
            models.Technician.technician_id == assignment.technician_id
        ).first()
        
        if not technician:
            raise HTTPException(status_code=404, detail="Technician not found")

        # 3. Check for Duplicate Assignment
        if job.assigned_technician_id:
            raise HTTPException(
                status_code=400, 
                detail=f"Job #{job.id} is already assigned to technician #{job.assigned_technician_id}"
            )

        # 4. Comprehensive Validation (Workload, Status, Skill)
        from ..validation import validate_technician_for_assignment
        validate_technician_for_assignment(technician, job)


        # 7. Perform Assignment
        job.assigned_technician_id = technician.technician_id
        job.status = "in progress"
        
        # Use workload utility for increment and status sync
        from ..workload_utils import update_workload_count
        update_workload_count(db, technician.technician_id, 1)

        db.commit()
        db.refresh(job)
        db.refresh(technician)

        return {
            "message": "Technician assigned successfully",
            "job_id": job.id,
            "assigned_technician": {
                "id": technician.technician_id,
                "name": technician.technician_name,
                "skill": technician.technician_skill
            },
            "job_status": job.status
        }

    except HTTPException:
        # Re-raise HTTP exceptions to be handled by the global handler
        raise
    except SQLAlchemyError as e:
        db.rollback()
        # Log database error here if logging is configured
        print(f"Database error during job assignment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error occurred"
        )
    except Exception as e:
        db.rollback()
        print(f"Unexpected error during job assignment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
