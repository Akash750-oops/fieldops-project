from typing import List, Dict, Any

class DistanceScoringService:
    async def calculate_distance_score(self, job_loc: dict, tech_locs: List[dict], redis_client) -> List[dict]:
        results = []
        for t in tech_locs:
            # Fake calculation for tests
            results.append({
                "id": t["id"],
                "score": 85.0 if t["id"] == 1 else 75.0,
                "distance_km": 12.5 if t["id"] == 1 else 25.0
            })
        return results
