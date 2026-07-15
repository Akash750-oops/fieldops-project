"""
planning_service.py

Planning Service for FieldOps Commander.

Responsibilities
----------------
- Retrieve job details.
- Retrieve available technicians.
- Build the PlanningContext.
- Invoke the AI Planning Agent.
- Store AI recommendations.
- Return a validated PlanningDecision.

The Planning Service NEVER:
- Ranks technicians.
- Updates the Job table.
- Assigns technicians.
- Changes technician status.

It orchestrates the planning workflow only.
"""

from typing import List

from app.services.ai.FieldOpsAI.repositories.job_repository import JobRepository
from app.services.ai.FieldOpsAI.repositories.technician_repository import TechnicianRepository
from app.services.ai.FieldOpsAI.repositories.job_assignment_repository import JobAssignmentRepository

from app.services.ai.FieldOpsAI.agents.planning_agent import PlanningAgent

from app.services.ai.FieldOpsAI.schemas.planning import PlanningContext,PlanningDecision


class PlanningService:
    """
    Service responsible for AI-assisted technician planning.
    """

    def __init__(self, db):
        self.db = db
        self.job_repository = JobRepository(db)
        self.technician_repository = TechnicianRepository(db)
        self.assignment_repository = JobAssignmentRepository(db)

        self.agent = PlanningAgent()

    # ---------------------------------------------------------

    def plan(
        self,
        job_id: int,
        rejected_technician_ids: List[int] | None = None,
    ) -> PlanningDecision:
        """
        Generate AI technician recommendations.

        Parameters
        ----------
        job_id
            Existing Job identifier.

        rejected_technician_ids
            Technicians that have already rejected or timed out.

        Returns
        -------
        PlanningDecision
        """

        if rejected_technician_ids is None:
            rejected_technician_ids = []

        # -----------------------------------------------------
        # Load Job
        # -----------------------------------------------------

        job = self.job_repository.get_by_id(job_id)

        if job is None:
            raise ValueError(
                f"Job {job_id} was not found."
            )

        # -----------------------------------------------------
        # Load Available Technicians
        # -----------------------------------------------------

        technicians = self.technician_repository.get_available(
            tenant_id=job.tenant_id
        )

        if not technicians:
            raise ValueError(
                "No available technicians found."
            )

        # -----------------------------------------------------
        # Convert Technicians into AI Format
        # -----------------------------------------------------

        available_technicians = []

        for technician in technicians:

            available_technicians.append(
                self.technician_repository.to_ai_dict(
                    technician
                )
            )

        # -----------------------------------------------------
        # Build Planning Context
        # -----------------------------------------------------

        context = PlanningContext(

            job_id=job.id,

            customer_request={
                "customer_name": job.customer_name,
                "location": job.location,
                "priority": job.priority,
                "required_skill": job.required_skill,
            },

            available_technicians=available_technicians,

            rejected_technician_ids=rejected_technician_ids,
        )

        # -----------------------------------------------------
        # Ask AI Planning Agent
        # -----------------------------------------------------

        decision: PlanningDecision = self.agent.plan(
            context
        )

        # -----------------------------------------------------
        # Store AI Recommendations
        # -----------------------------------------------------

        recommendations = []

        for technician in decision.recommended_technicians:
            recommendations.append(
                {
                    "technician_id": technician.technician_id,
                    "rank": technician.rank,
                }
            )

        self.assignment_repository.save_recommendations(
            job_id=job.id,
            recommendations=recommendations,
        )

        self.assignment_repository.save()

        # -----------------------------------------------------
        # Return AI Decision
        # -----------------------------------------------------

        return decision