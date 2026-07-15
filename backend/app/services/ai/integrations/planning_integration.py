"""
planning_integration.py

Integration layer between the existing
FieldOps planning workflow and the AI Planning Agent.

Responsibilities
----------------
- Receive candidate technicians from the backend.
- Invoke the PlanningAgent.
- Return a validated PlanningDecision.

No database operations occur here.
"""

from typing import Dict, List

from app.services.ai.FieldOpsAI.agents.planning_agent import PlanningAgent
from app.services.ai.FieldOpsAI.schemas.planning import PlanningDecision


class PlanningIntegration:
    """
    Adapter between backend planning
    services and the AI Planning Agent.
    """

    def __init__(self):
        self.agent = PlanningAgent()

    def recommend(
        self,
        customer_request: Dict,
        candidate_technicians: List[Dict],
    ) -> PlanningDecision:
        """
        Ask the AI to recommend the best technician
        from the candidate list.

        Parameters
        ----------
        customer_request
            Structured customer/job request.

        candidate_technicians
            Candidate technicians already ranked by
            the existing planning engine.

        Returns
        -------
        PlanningDecision
            Validated AI recommendation.
        """

        return self.agent.assign_technician(
            customer_request=customer_request,
            technicians=candidate_technicians,
        )