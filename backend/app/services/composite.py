from typing import List, Dict, Any

class CompositeScoringService:
    def get_weights(self, db, tenant_id: str) -> Dict[str, float]:
        return {"proximity": 0.4, "skill": 0.4, "workload": 0.2}
        
    def composite_score(self, prox: float, skill: float, work: float, weights: dict) -> Dict[str, float]:
        score = (prox * weights["proximity"]) + (skill * weights["skill"]) + (work * weights["workload"])
        return {"composite_score": round(score, 1)}
        
    def rank_technicians(self, qualified: List[dict]) -> List[dict]:
        return sorted(qualified, key=lambda x: (
            -x.get("composite_score", 0.0),
            x.get("distance_km") or 9999.0,
            x.get("active_jobs", 9999),
            str(x.get("tech_id", ""))
        ))
