from typing import List, Dict, Any

class SkillScoringService:
    def get_taxonomy(self, db) -> Dict[str, Any]:
        return {}
        
    def expand_equivalents(self, skills: set, taxonomy: dict) -> set:
        return skills
        
    def get_all_prerequisites(self, skill: str, taxonomy: dict) -> List[str]:
        return []
        
    def calculate_skill_score(self, req_str: str, tech_str: str, db) -> float:
        return 90.0
