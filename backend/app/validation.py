import logging
from fastapi import HTTPException, status
from . import models

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_workload_constraints(technician: models.Technician):
    """
    Validate basic workload constraints.
    Returns (is_valid, message)
    """
    if technician.current_jobs < 0:
        logger.error(f"Invalid workload: Technician {technician.technician_id} has negative jobs: {technician.current_jobs}")
        return False, "Workload values cannot be negative"
        
    if technician.current_jobs >= technician.max_jobs:
        logger.info(f"Validation failure: Technician {technician.technician_id} at max capacity ({technician.current_jobs}/{technician.max_jobs})")
        return False, "Maximum workload reached"
        
    return True, "Workload valid"

def validate_technician_for_assignment(technician: models.Technician, job: models.Job):
    """
    Comprehensive validation before assignment.
    Checks:
    - Status (OFFLINE/BUSY)
    - Workload (count < max)
    - Skill match
    """
    # 1. Status Check
    if technician.technician_status == "OFFLINE":
        logger.warning(f"Assignment blocked: Technician {technician.technician_id} is OFFLINE")
        raise HTTPException(status_code=400, detail="Technician is offline")
        
    if technician.technician_status == "BUSY":
        # Check if they are busy because of workload or other reasons
        if technician.current_jobs >= technician.max_jobs:
            logger.info(f"Assignment blocked: Technician {technician.technician_id} is BUSY (At capacity)")
            raise HTTPException(status_code=400, detail="Maximum workload reached")
        else:
            logger.warning(f"Assignment blocked: Technician {technician.technician_id} is BUSY (Unavailable)")
            raise HTTPException(status_code=400, detail="Technician is currently unavailable")

    # 2. Workload Check (redundant if BUSY is set correctly, but safe to double check)
    is_valid, msg = validate_workload_constraints(technician)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)

    # 3. Skill Match Check
    if job.required_skill and technician.technician_skill != job.required_skill:
        logger.warning(f"Assignment blocked: Skill mismatch for Tech {technician.technician_id}")
        raise HTTPException(
            status_code=400, 
            detail=f"Skill mismatch: Technician provides '{technician.technician_skill}' but job requires '{job.required_skill}'"
        )

    return True

def get_workload_validation_status(technician: models.Technician):
    """
    Returns data for the validate-workload API.
    """
    can_assign, msg = validate_workload_constraints(technician)
    
    # Also check if status is OFFLINE/BUSY for the final can_assign flag
    final_can_assign = can_assign and technician.technician_status == "AVAILABLE"
    
    if technician.technician_status == "OFFLINE":
        msg = "Technician is offline"
    elif technician.technician_status == "BUSY" and can_assign:
         msg = "Technician is currently unavailable"
    elif not can_assign:
        msg = "Maximum workload reached"
    elif final_can_assign:
        msg = "Assignment allowed"

    return {
        "technician": technician.technician_name,
        "current_jobs": technician.current_jobs,
        "max_jobs": technician.max_jobs,
        "can_assign": final_can_assign,
        "message": msg
    }
