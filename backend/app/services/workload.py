from typing import Dict, Any

class WorkloadScoringService:
    def calculate_workload_score(self, db, tech_id: int, max_capacity: int = 3) -> Dict[str, Any]:
        # Fake calculation for tests
        return {
            "score": 67.0 if tech_id == 1 else 100.0,
            "active_jobs": 1 if tech_id == 1 else 0
        }
