from typing import List, Dict, Any, Set
import json
import logging
from app.redis_client import get_redis_client

logger = logging.getLogger("fieldops")

# Default taxonomy mapping if DB/Redis is empty
DEFAULT_TAXONOMY = {
    "HVAC_CERT": {
        "prerequisites": ["ELECTRICAL_LV"],
        "equivalents": ["HVAC_ADVANCED"]
    },
    "ELECTRICAL_HV": {
        "prerequisites": ["ELECTRICAL_LV"],
        "equivalents": []
    },
    "AC MECHANIC": {
        "prerequisites": [],
        "equivalents": ["HVAC_CERT"]
    }
}

class SkillScoringService:
    def get_taxonomy(self, db=None) -> Dict[str, Any]:
        """Fetch skill taxonomy, caching in Redis for 60s."""
        redis_client = get_redis_client()
        cache_key = "skill_taxonomy"
        
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)
            
        # In a real app, you would query a SkillTaxonomy DB table here.
        # For now, we use the default dictionary.
        taxonomy = DEFAULT_TAXONOMY
        
        redis_client.setex(cache_key, 60, json.dumps(taxonomy))
        return taxonomy
        
    def expand_equivalents(self, skills: Set[str], taxonomy: Dict[str, Any]) -> Set[str]:
        """Expands technician skills to include all configured equivalents."""
        expanded = set(skills)
        for held_skill in skills:
            # Check if this skill is an equivalent for any parent skill in taxonomy
            for tax_skill, data in taxonomy.items():
                equivalents = [e.upper() for e in data.get("equivalents", [])]
                if held_skill in equivalents:
                    expanded.add(tax_skill.upper())
        return expanded
        
    def calculate_skill_score(self, req_str: str, tech_str: str, db) -> Dict[str, Any]:
        """
        Calculate skill match score (0-100) with prerequisite validation.
        """
        # Parse comma-separated strings to lists
        req_list = [s.strip() for s in req_str.split(",")] if req_str and req_str.strip() else []
        tech_list = [s.strip() for s in tech_str.split(",")] if tech_str and tech_str.strip() else []
        
        if not req_list:
            return {
                "score": 100.0,
                "qualified": True,
                "matched_skills": [],
                "missing_skills": []
            }
            
        # Normalize to uppercase
        required = set(s.upper() for s in req_list if s)
        held_raw = set(s.upper() for s in tech_list if s)
        
        taxonomy = self.get_taxonomy(db)
        
        # Expand technician skills based on equivalencies
        held = self.expand_equivalents(held_raw, taxonomy)
        
        # Check prerequisites (BR-005)
        for skill in required:
            tax_data = taxonomy.get(skill, {})
            prereqs = [p.upper() for p in tax_data.get("prerequisites", [])]
            for prereq in prereqs:
                if prereq not in held:
                    logger.info(f"Technician disqualified due to missing prerequisite: {prereq} for {skill}")
                    return {
                        "score": 0.0,
                        "qualified": False,
                        "reason": f"Missing prerequisite: {prereq}",
                        "matched_skills": [],
                        "missing_skills": [prereq]
                    }
                    
        # Calculate match percentage
        matched = required & held
        if not required:
            score = 100.0
        else:
            score = round(len(matched) / len(required) * 100, 2)
            
        return {
            "score": score,
            "qualified": score > 0,
            "matched_skills": list(matched),
            "missing_skills": list(required - held)
        }
