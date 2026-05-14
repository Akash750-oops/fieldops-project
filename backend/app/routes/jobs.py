from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import case
from ..database import get_db
from ..models import Job
from ..schemas import JobCreate, JobResponse
from ..workload_utils import update_workload_count
from typing import List, Union
from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post("/", response_model=Union[dict, JobResponse], status_code=201)
def create_job(jobs: Union[JobCreate, List[JobCreate]], db: Session = Depends(get_db)):
    try:
        # Normalize input to a list of jobs
        is_bulk = isinstance(jobs, list)
        job_data_list = jobs if is_bulk else [jobs]

        job_objects = [
            Job(
                customer_name=j.customer_name,
                location=j.location,
                issue_description=j.issue_description,
                priority=j.priority,
                service_type=j.service_type,
                contact_number=j.contact_number,
                preferred_service_date=j.preferred_service_date,
                required_skill=j.required_skill,
                status=j.status
            ) for j in job_data_list
        ]

        db.add_all(job_objects)
        db.commit()

        if is_bulk:
            for job in job_objects:
                db.refresh(job)
            return {
                "message": f"{len(job_objects)} jobs created successfully",
                "jobs": [JobResponse.model_validate(job) for job in job_objects]
            }

        # Single job response
        new_job = job_objects[0]
        db.refresh(new_job)
        return JobResponse.model_validate(new_job)

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(error)}"
        )


@router.get("/", response_model=Union[dict, list[JobResponse]])
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()
    return jobs


@router.get("/sorted", response_model=list[JobResponse])
def get_jobs_sorted(db: Session = Depends(get_db)):
    """
    Fetch all jobs ordered by priority.
    Supports both P1-P5 and LOW-CRITICAL if mixed.
    """
    priority_map = {
        "CRITICAL": 1, "P1": 1,
        "HIGH": 2, "P2": 2,
        "MEDIUM": 3, "P3": 3,
        "LOW": 4, "P4": 4,
        "P5": 5
    }
    
    priority_order = case(
        priority_map,
        value=Job.priority,
        else_=99
    )

    return db.query(Job).order_by(priority_order, Job.id.desc()).all()


@router.get("/{job_id}", response_model=JobResponse)
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job_data: JobCreate, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Workload reduction logic
    old_status = job.status.lower()
    new_status = job_data.status.lower()
    
    # If job is transitioning from active/in-progress to completed/cancelled
    active_statuses = ["active", "in progress"]
    finished_statuses = ["completed", "cancelled", "done"]
    
    if old_status in active_statuses and new_status in finished_statuses:
        if job.assigned_technician_id:
            update_workload_count(db, job.assigned_technician_id, -1)
            
    job.customer_name = job_data.customer_name
    job.location = job_data.location
    job.issue_description = job_data.issue_description
    job.priority = job_data.priority
    job.service_type = job_data.service_type
    job.contact_number = job_data.contact_number
    job.preferred_service_date = job_data.preferred_service_date
    job.required_skill = job_data.required_skill
    job.status = job_data.status

    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # If job was active and assigned, reduce workload
    if job.status.lower() in ["active", "in progress"] and job.assigned_technician_id:
        update_workload_count(db, job.assigned_technician_id, -1)
        
    db.delete(job)
    db.commit()
    return {"message": "Job deleted successfully", "job_id": job_id}