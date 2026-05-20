from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Job
from app.schemas import JobCreate, JobResponse

router = APIRouter(
    prefix="/jobs",
    tags=["Jobs"]
)


@router.post("/", response_model=JobResponse, status_code=201)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    try:
        new_job = Job(
            customer_name=job.customer_name,
            location=job.location,
            issue_description=job.issue_description,
            priority=job.priority,
            service_type=job.service_type,
            contact_number=job.contact_number,
            preferred_service_date=job.preferred_service_date,
        )

        db.add(new_job)
        db.commit()
        db.refresh(new_job)

        return new_job

    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(error)}"
        )


@router.get("/", response_model=list[JobResponse])
def get_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.id.desc()).all()

@router.put("/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job: JobCreate, db: Session = Depends(get_db)):
    existing_job = db.query(Job).filter(Job.id == job_id).first()

    if not existing_job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_job.customer_name = job.customer_name
    existing_job.location = job.location
    existing_job.issue_description = job.issue_description
    existing_job.priority = job.priority
    existing_job.service_type = job.service_type
    existing_job.contact_number = job.contact_number
    existing_job.preferred_service_date = job.preferred_service_date

    db.commit()
    db.refresh(existing_job)

    return existing_job