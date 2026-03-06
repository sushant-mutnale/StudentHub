"""
Company Interview Research Service
Provides interview patterns, DSA topics, and behavioral themes for companies.
Features: MongoDB lookup with seed data fallback, AI-generated tips.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio

from ..database import get_database
from ..data.company_interview_data import COMPANY_INTERVIEW_DATA, DEFAULT_COMPANY_PATTERN


class CompanyInterviewResearcher:
    """
    Service to lookup and provide company interview knowledge.
    Uses MongoDB with fallback to seed data and AI enhancements.
    """
    
    def __init__(self):
        self._llm_service = None
        self._seed_data_indexed = None
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def _get_seed_data_indexed(self) -> Dict[str, Dict]:
        """Index seed data by company name and aliases for fast lookup."""
        if self._seed_data_indexed is None:
            self._seed_data_indexed = {}
            for company_data in COMPANY_INTERVIEW_DATA:
                # Index by main name
                key = company_data["company"].lower()
                self._seed_data_indexed[key] = company_data
                # Index by aliases
                for alias in company_data.get("company_aliases", []):
                    self._seed_data_indexed[alias.lower()] = company_data
        return self._seed_data_indexed
    
    def _collection(self):
        """Get MongoDB collection."""
        return get_database()["company_interview_knowledge"]
    
    def _research_queue_collection(self):
        """Get research queue collection for unknown companies."""
        return get_database()["company_research_queue"]
    
    async def get_company_interview_pattern(
        self,
        company: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get interview pattern for a company.
        
        Lookup order:
        1. MongoDB (for user-added or updated data)
        2. Seed data (pre-populated knowledge)
        3. Default pattern + add to research queue
        """
        company_lower = company.lower().strip()
        
        # 1. Try MongoDB first
        db_result = await self._collection().find_one({
            "$or": [
                {"company": {"$regex": f"^{company}$", "$options": "i"}},
                {"company_aliases": {"$regex": f"^{company}$", "$options": "i"}}
            ]
        })
        
        if db_result:
            db_result["_id"] = str(db_result["_id"])
            db_result["source"] = "database"
            return db_result
        
        # 2. Try seed data
        indexed = self._get_seed_data_indexed()
        if company_lower in indexed:
            result = indexed[company_lower].copy()
            result["source"] = "seed_data"
            return result
        
        # 3. Return default and queue for research
        await self._add_to_research_queue(company, role)
        
        result = DEFAULT_COMPANY_PATTERN.copy()
        result["company"] = company
        result["source"] = "default"
        result["note"] = "Company not in knowledge base. Using default pattern."
        return result
    
    async def _add_to_research_queue(
        self,
        company: str,
        role: Optional[str] = None
    ):
        """Add unknown company to research queue for admin to update."""
        try:
            await self._research_queue_collection().update_one(
                {"company": company.lower()},
                {
                    "$set": {
                        "company": company,
                        "role": role,
                        "status": "pending",
                        "updated_at": datetime.utcnow()
                    },
                    "$inc": {"request_count": 1},
                    "$setOnInsert": {"created_at": datetime.utcnow()}
                },
                upsert=True
            )
        except Exception:
            pass  # Non-critical, don't fail if queue update fails
    
    async def get_dsa_topics(self, company: str) -> List[str]:
        """Get DSA topics commonly asked at a company."""
        pattern = await self.get_company_interview_pattern(company)
        return pattern.get("dsa_topics", [])
    
    async def get_behavioral_themes(self, company: str) -> List[str]:
        """Get behavioral themes/values for a company."""
        pattern = await self.get_company_interview_pattern(company)
        return pattern.get("behavioral_themes", [])
    
    async def get_system_design_topics(self, company: str) -> List[str]:
        """Get system design topics for a company."""
        pattern = await self.get_company_interview_pattern(company)
        return pattern.get("system_design_topics", [])
    
    async def estimate_difficulty(self, company: str) -> str:
        """Estimate interview difficulty for a company."""
        pattern = await self.get_company_interview_pattern(company)
        return pattern.get("difficulty", "medium")
    
    async def get_preparation_tips(
        self,
        company: str,
        role: Optional[str] = None,
        student_skills: Optional[List[str]] = None
    ) -> List[str]:
        """
        Get preparation tips for a company.
        Uses AI to generate personalized tips if available.
        """
        pattern = await self.get_company_interview_pattern(company, role)
        base_tips = pattern.get("tips", [])
        
        # If AI available and student skills provided, generate personalized tips
        llm = self._get_llm_service()
        if llm and student_skills:
            try:
                personalized = await self._generate_ai_tips(
                    company, role, student_skills, pattern
                )
                if personalized:
                    return personalized + base_tips[:3]
            except Exception:
                pass
        
        return base_tips
    
    async def _generate_ai_tips(
        self,
        company: str,
        role: Optional[str],
        student_skills: List[str],
        pattern: Dict[str, Any]
    ) -> List[str]:
        """Generate personalized tips using AI."""
        llm = self._get_llm_service()
        if not llm:
            return []
        
        prompt = f"""Generate 3 personalized interview preparation tips for a student.

Company: {company}
Role: {role or 'Software Engineer'}
Student's Skills: {', '.join(student_skills[:10])}

Company's Interview Focus:
- DSA Topics: {', '.join(pattern.get('dsa_topics', [])[:5])}
- Behavioral Themes: {', '.join(pattern.get('behavioral_themes', [])[:3])}
- Difficulty: {pattern.get('difficulty', 'medium')}

Generate 3 SHORT, ACTIONABLE tips (1 sentence each) that are specific to:
1. What DSA topics to focus on given their skills
2. How to prepare for behavioral based on company values
3. One unique insight about this company's interview

Format: One tip per line, no numbering."""

        try:
            response = await llm.generate(prompt)
            if response and not response.startswith("Error"):
                tips = [t.strip() for t in response.split("\n") if t.strip()]
                return tips[:3]
        except Exception:
            pass
        
        return []
    
    async def get_interview_summary(
        self,
        company: str,
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a complete interview summary for a company.
        Combines all information into a student-friendly format.
        """
        pattern = await self.get_company_interview_pattern(company, role)
        
        # Calculate total interview time
        total_time = sum(r.get("duration", 60) for r in pattern.get("rounds", []))
        
        # Generate summary text
        difficulty = pattern.get("difficulty", "medium")
        prep_weeks = pattern.get("preparation_time_weeks", 4)
        
        summary = {
            "company": pattern.get("company", company),
            "role": role or "Software Engineer",
            "difficulty": difficulty,
            "difficulty_score": {"easy": 1, "medium": 2, "medium-hard": 3, "hard": 4, "very hard": 5}.get(difficulty, 3),
            "total_rounds": pattern.get("total_rounds", len(pattern.get("rounds", []))),
            "total_interview_time_minutes": total_time,
            "rounds": pattern.get("rounds", []),
            "dsa_topics": pattern.get("dsa_topics", []),
            "behavioral_themes": pattern.get("behavioral_themes", []),
            "system_design_topics": pattern.get("system_design_topics", []),
            "tips": pattern.get("tips", []),
            "example_questions": pattern.get("example_questions", []),
            "recommended_prep_weeks": prep_weeks,
            "sources": pattern.get("sources", []),
            "data_source": pattern.get("source", "unknown"),
        }
        
        return summary
    
    async def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for companies in the knowledge base."""
        query_lower = query.lower()
        results = []
        
        # Search in seed data
        indexed = self._get_seed_data_indexed()
        seen = set()
        
        for key, data in indexed.items():
            if query_lower in key and data["company"] not in seen:
                seen.add(data["company"])
                results.append({
                    "company": data["company"],
                    "difficulty": data.get("difficulty", "medium"),
                    "total_rounds": data.get("total_rounds", 3),
                    "source": "seed_data"
                })
        
        # Also search MongoDB
        try:
            cursor = self._collection().find({
                "$or": [
                    {"company": {"$regex": query, "$options": "i"}},
                    {"company_aliases": {"$regex": query, "$options": "i"}}
                ]
            }).limit(limit)
            
            async for doc in cursor:
                if doc["company"] not in seen:
                    seen.add(doc["company"])
                    results.append({
                        "company": doc["company"],
                        "difficulty": doc.get("difficulty", "medium"),
                        "total_rounds": doc.get("total_rounds", 3),
                        "source": "database"
                    })
        except Exception:
            pass
        
        return results[:limit]
    
    async def list_all_companies(self) -> List[str]:
        """List all companies in the knowledge base."""
        companies = set()
        
        # From seed data
        for data in COMPANY_INTERVIEW_DATA:
            companies.add(data["company"])
        
        # From MongoDB
        try:
            cursor = self._collection().distinct("company")
            for company in await cursor.to_list(length=100):
                companies.add(company)
        except Exception:
            pass
        
        return sorted(companies)
    
    async def add_company_knowledge(
        self,
        company_data: Dict[str, Any]
    ) -> str:
        """Add or update company interview knowledge in MongoDB."""
        company_data["updated_at"] = datetime.utcnow()
        
        result = await self._collection().update_one(
            {"company": {"$regex": f"^{company_data['company']}$", "$options": "i"}},
            {"$set": company_data},
            upsert=True
        )
        
        return str(result.upserted_id) if result.upserted_id else "updated"


# Singleton instance
company_researcher = CompanyInterviewResearcher()
