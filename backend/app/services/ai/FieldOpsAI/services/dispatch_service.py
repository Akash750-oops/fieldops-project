"""
dispatch_service.py

Dispatch Service for FieldOps Commander.

Responsibilities
----------------
- Dispatch the current technician.
- Handle technician acceptance.
- Handle technician rejection.
- Handle technician timeout.
- Promote backup technicians.
- Update Job and Technician records.

The Dispatch Service NEVER:
- Ranks technicians.
- Chooses technicians.
- Calls the Planning Agent directly.
"""

from datetime import datetime, timezone

from app.services.ai.FieldOpsAI.repositories.job_repository import JobRepository
from app.services.ai.FieldOpsAI.repositories.technician_repository import TechnicianRepository
from app.services.ai.FieldOpsAI.repositories.job_assignment_repository import JobAssignmentRepository


class DispatchService:
    """
    Service responsible for technician dispatch workflow.
    """

    def __init__(self, db):
        self.db = db

        self.job_repository = JobRepository(db)
        self.technician_repository = TechnicianRepository(db)
        self.assignment_repository = JobAssignmentRepository(db)

    # ---------------------------------------------------------

    def dispatch(
        self,
        job_id: int,
    ):
        """
        Dispatch the current ranked technician.

        Returns
        -------
        JobAssignment
            Current technician assignment.
        """

        assignment = self.assignment_repository.get_current_candidate(
            job_id
        )

        if assignment is None:
            raise ValueError(
                "No technician available for dispatch."
            )

        self.assignment_repository.mark_assigned(
            assignment
        )

        self.assignment_repository.save()

        return assignment

    # ---------------------------------------------------------

    def accept(
        self,
        job_id: int,
    ):
        """
        Technician accepted the job.

        Updates:
            - JobAssignment
            - Job
            - Technician
        """

        assignment = self.assignment_repository.get_current_candidate(
            job_id
        )

        if assignment is None:
            raise ValueError(
                "No current technician."
            )

        # -------------------------------------
        # Update Assignment
        # -------------------------------------

        self.assignment_repository.mark_accepted(
            assignment
        )

        # -------------------------------------
        # Update Job
        # -------------------------------------

        job = self.job_repository.assign_technician(
            job_id,
            assignment.technician_id,
        )

        self.job_repository.update_status(
            job_id,
            "ASSIGNED",
        )

        # -------------------------------------
        # Update Technician
        # -------------------------------------

        self.technician_repository.update_status(
            assignment.technician_id,
            "BUSY",
        )

        self.technician_repository.increment_jobs(
            assignment.technician_id
        )

        # -------------------------------------

        self.assignment_repository.save()

        return job

    # ---------------------------------------------------------

    def reject(
        self,
        job_id: int,
    ):
        """
        Technician rejected the assignment.

        Promote the next technician.
        """

        assignment = self.assignment_repository.get_current_candidate(
            job_id
        )

        if assignment is None:
            raise ValueError(
                "No current technician."
            )

        self.assignment_repository.mark_rejected(
            assignment
        )

        next_candidate = (
            self.assignment_repository.promote_next_candidate(
                job_id
            )
        )

        self.assignment_repository.save()

        return next_candidate

    # ---------------------------------------------------------

    def timeout(
        self,
        job_id: int,
    ):
        """
        Technician did not respond.

        Promote the next technician.
        """

        assignment = self.assignment_repository.get_current_candidate(
            job_id
        )

        if assignment is None:
            raise ValueError(
                "No current technician."
            )

        self.assignment_repository.mark_timeout(
            assignment
        )

        next_candidate = (
            self.assignment_repository.promote_next_candidate(
                job_id
            )
        )

        self.assignment_repository.save()

        return next_candidate

    # ---------------------------------------------------------

    def get_current_dispatch(
        self,
        job_id: int,
    ):
        """
        Return the technician currently being dispatched.
        """

        return self.assignment_repository.get_current_candidate(
            job_id
        )

    # ---------------------------------------------------------

    def get_rejected_technicians(
        self,
        job_id: int,
    ):
        """
        Return technicians who already rejected
        or timed out.
        """

        return (
            self.assignment_repository.get_rejected_technician_ids(
                job_id
            )
        )