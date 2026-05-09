from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Union
from sqlalchemy import case
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_db
from app import models, schemas


router = APIRouter(
    tags=["Jobs"]
)


@router.post("/jobs", status_code=status.HTTP_200_OK)
def create_job(jobs: Union[schemas.JobCreate, List[schemas.JobCreate]], db: Session = Depends(get_db)):
    """
    Create one or more new jobs.

    PostgreSQL automatically generates a unique job ID
    because id is SERIAL / primary key in the jobs table.
    """

    try:
        # Normalize input to a list of jobs
        is_bulk = isinstance(jobs, list)
        job_data_list = jobs if is_bulk else [jobs]

        job_objects = [
            models.Job(
                customer_name=j.customer_name,
                location=j.location,
                issue=j.issue,
                priority=j.priority,
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
                "jobs": job_objects
            }

        # Single job response (preserving existing format for frontend compatibility)
        new_job = job_objects[0]
        db.refresh(new_job)

        return {
            "message": "Job created successfully",
            "job_id": new_job.id,
            "job": {
                "id": new_job.id,
                "customer_name": new_job.customer_name,
                "location": new_job.location,
                "issue": new_job.issue,
                "priority": new_job.priority,
                "status": new_job.status,
                "created_at": new_job.created_at,
                "updated_at": new_job.updated_at,
            },
        }

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating job"
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred"
        )


@router.get("/jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    try:
        jobs = db.query(models.Job).order_by(models.Job.id.desc()).all()

        return {
            "message": "Jobs fetched successfully",
            "count": len(jobs),
            "jobs": jobs,
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching jobs"
        )


@router.get("/jobs/sorted")
def get_jobs_sorted(db: Session = Depends(get_db)):
    """
    Fetch all jobs ordered by priority:
    CRITICAL > HIGH > MEDIUM > LOW
    """
    try:
        priority_order = case(
            {
                "CRITICAL": 1,
                "HIGH": 2,
                "MEDIUM": 3,
                "LOW": 4
            },
            value=models.Job.priority
        )

        jobs = db.query(models.Job).order_by(priority_order, models.Job.id.desc()).all()

        return {
            "message": "Jobs fetched and sorted by priority successfully",
            "count": len(jobs),
            "jobs": jobs,
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching sorted jobs"
        )


@router.get("/jobs/{job_id}")
def get_job_by_id(job_id: int, db: Session = Depends(get_db)):
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        return {
            "message": "Job fetched successfully",
            "job": job,
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching job"
        )


@router.put("/jobs/{job_id}")
def update_job(job_id: int, job_data: schemas.JobCreate, db: Session = Depends(get_db)):
    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        job.customer_name = job_data.customer_name
        job.location = job_data.location
        job.issue = job_data.issue
        job.priority = job_data.priority
        job.status = job_data.status

        db.commit()
        db.refresh(job)

        return {
            "message": "Job updated successfully",
            "job": {
                "id": job.id,
                "customer_name": job.customer_name,
                "location": job.location,
                "issue": job.issue,
                "priority": job.priority,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating job"
        )


@router.patch("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """
    Cancel an existing active job.

    This does not delete the job from database.
    It only changes status from active to cancelled.
    """

    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        if job.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job is already cancelled"
            )

        job.status = "cancelled"

        db.commit()
        db.refresh(job)

        return {
            "message": "Job cancelled successfully",
            "job_id": job.id,
            "job": {
                "id": job.id,
                "customer_name": job.customer_name,
                "location": job.location,
                "issue": job.issue,
                "priority": job.priority,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            },
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while cancelling job"
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while cancelling job"
        )


@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Delete an existing job permanently from database.
    """

    try:
        job = db.query(models.Job).filter(models.Job.id == job_id).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        deleted_job_id = job.id

        db.delete(job)
        db.commit()

        return {
            "message": "Job deleted successfully",
            "deleted_job_id": deleted_job_id,
        }

    except HTTPException:
        raise

    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting job"
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error occurred while deleting job"
        )