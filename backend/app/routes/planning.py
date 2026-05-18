from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Job, Technician
from .. import schemas

router = APIRouter(
    tags=["Planning"]
)

@router.get("/planned-assignments", response_model=list[schemas.PlannedAssignmentResponse])
def get_planned_assignments(db: Session = Depends(get_db)):
    """
    Fetch all jobs that are assigned to a technician.
    """
    results = db.query(
        Job.id.label("job_id"),
        Technician.technician_name.label("technician"),
        Technician.technician_skill.label("skill"),
        Job.customer_name.label("customer"),
        Job.location,
        Job.priority,
        Job.status,
        Technician.current_jobs,
        Technician.max_jobs
    ).join(Technician, Job.assigned_technician_id == Technician.technician_id).all()
    
    return results
