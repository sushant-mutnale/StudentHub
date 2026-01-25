"""
Interview Flow Integration Service
Connects Resume → JD → Company Knowledge → Interview in one unified flow.
Features: One-click interview start, profile updates, activity logging, matching integration.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from bson import ObjectId

from ..database import get_database
from .resume_parser import resume_parser
from .jd_parser import jd_parser
from .company_research import company_researcher
from .interview_orchestrator import interview_orchestrator, SessionStatus


class InterviewFlowService:
    """
    Unified service that orchestrates the complete interview flow.
    Connects all Module 3 components and integrates with Module 1/2.
    """
    
    def __init__(self):
        pass
    
    def _users_collection(self):
        return get_database()["users"]
    
    def _sessions_collection(self):
        return get_database()["interview_sessions"]
    
    def _activities_collection(self):
        return get_database()["user_activities"]
    
    def _resumes_collection(self):
        return get_database()["resume_uploads"]
    
    # ============ Full Flow: Start Interview ============
    
    async def start_full_interview(
        self,
        student_id: str,
        company: str,
        role: str,
        resume_id: Optional[str] = None,
        jd_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a complete interview flow.
        
        Flow:
        1. Get parsed resume (if resume_id provided)
        2. Parse JD (if jd_text provided)
        3. Fetch company interview pattern
        4. Create interview session
        5. Start session and get first question
        6. Return everything needed to begin
        """
        flow_status = {
            "resume_parsed": False,
            "jd_parsed": False,
            "company_knowledge_fetched": False,
            "session_created": False,
            "interview_started": False
        }
        
        parsed_resume = None
        parsed_jd = None
        company_pattern = None
        
        # Step 1: Get/parse resume
        if resume_id:
            try:
                resume_doc = await self._resumes_collection().find_one(
                    {"_id": ObjectId(resume_id)}
                )
                if resume_doc:
                    parsed_resume = resume_doc.get("parsed_data", {})
                    flow_status["resume_parsed"] = True
            except Exception as e:
                parsed_resume = {"error": str(e)}
        
        # Step 2: Parse JD
        if jd_text:
            try:
                jd_result = await jd_parser.parse_jd(jd_text)
                if jd_result.get("success"):
                    parsed_jd = jd_result
                    flow_status["jd_parsed"] = True
                    
                    # Extract company from JD if not provided
                    if not company and jd_result.get("company"):
                        company = jd_result["company"]
            except Exception as e:
                parsed_jd = {"error": str(e)}
        
        # Default company if none found
        if not company:
            company = "General"
        
        # Step 3: Fetch company knowledge
        try:
            company_pattern = await company_researcher.get_interview_summary(company, role)
            flow_status["company_knowledge_fetched"] = True
        except Exception as e:
            company_pattern = {"error": str(e)}
        
        # Step 4: Create session
        try:
            session_result = await interview_orchestrator.create_session(
                student_id=student_id,
                company=company,
                role=role,
                resume_id=resume_id,
                jd_text=jd_text,
                parsed_jd=parsed_jd,
                parsed_resume=parsed_resume
            )
            session_id = session_result["session_id"]
            flow_status["session_created"] = True
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create session: {str(e)}",
                "flow_status": flow_status
            }
        
        # Step 5: Start session and get first question
        try:
            start_result = await interview_orchestrator.start_session(session_id)
            flow_status["interview_started"] = True
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to start session: {str(e)}",
                "session_id": session_id,
                "flow_status": flow_status
            }
        
        # Log activity
        await self._log_activity(
            student_id=student_id,
            activity_type="INTERVIEW_STARTED",
            details={
                "company": company,
                "role": role,
                "session_id": session_id
            }
        )
        
        return {
            "success": True,
            "session_id": session_id,
            "company": company,
            "role": role,
            "total_rounds": session_result.get("total_rounds", 3),
            "estimated_duration_minutes": session_result.get("estimated_duration_minutes", 120),
            "first_question": start_result.get("first_question", {}),
            "company_tips": company_pattern.get("tips", [])[:3] if company_pattern else [],
            "flow_status": flow_status,
            "message": f"Interview for {company} {role} started. Good luck!"
        }
    
    # ============ Complete Interview & Update Profile ============
    
    async def complete_interview_and_update_profile(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Complete an interview and update the student's profile.
        
        Steps:
        1. Generate interview report
        2. Update ai_profile.interview_score
        3. Update ai_profile.overall_score
        4. Log completion activity
        5. Return report with profile update status
        """
        # Get session
        session = await interview_orchestrator.get_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        student_id = session["student_id"]
        
        # Generate report
        report = await interview_orchestrator.generate_report(session_id)
        if "error" in report:
            return {"success": False, "error": report["error"]}
        
        interview_score = report.get("overall_score", 0)
        company = session.get("company", "Unknown")
        role = session.get("role", "Unknown")
        
        # Update student's AI profile
        profile_updated = await self._update_ai_profile(
            student_id=student_id,
            interview_score=interview_score,
            company=company,
            report=report
        )
        
        # Log completion activity
        await self._log_activity(
            student_id=student_id,
            activity_type="INTERVIEW_COMPLETED",
            details={
                "company": company,
                "role": role,
                "session_id": session_id,
                "score": interview_score,
                "total_questions": report.get("total_questions", 0),
                "duration_minutes": report.get("total_time_minutes", 0)
            }
        )
        
        # Update matching score for Module 2 integration
        await self._update_matching_score(student_id, interview_score)
        
        return {
            "success": True,
            "report": report,
            "profile_updated": profile_updated,
            "message": f"Interview completed! Your score: {interview_score}%"
        }
    
    async def _update_ai_profile(
        self,
        student_id: str,
        interview_score: float,
        company: str,
        report: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update student's AI profile with interview results."""
        try:
            # Get current user
            user = await self._users_collection().find_one({"_id": ObjectId(student_id)})
            if not user:
                return {"updated": False, "error": "User not found"}
            
            ai_profile = user.get("ai_profile", {})
            
            # Get previous interview scores or initialize
            interview_history = ai_profile.get("interview_history", [])
            interview_history.append({
                "company": company,
                "score": interview_score,
                "date": datetime.utcnow(),
                "session_id": report.get("session_id")
            })
            
            # Keep only last 10 interviews
            interview_history = interview_history[-10:]
            
            # Calculate average interview score
            avg_interview_score = sum(h["score"] for h in interview_history) / len(interview_history)
            
            # Update skill assessments based on strengths/weaknesses
            skill_scores = ai_profile.get("skill_scores", {})
            
            # Round breakdown analysis
            for rb in report.get("round_breakdown", []):
                round_type = rb.get("round_type", "")
                round_score = rb.get("score", 0)
                
                if "dsa" in round_type.lower():
                    skill_scores["coding"] = (skill_scores.get("coding", 50) + round_score) / 2
                elif "behavioral" in round_type.lower():
                    skill_scores["behavioral"] = (skill_scores.get("behavioral", 50) + round_score) / 2
                elif "design" in round_type.lower():
                    skill_scores["system_design"] = (skill_scores.get("system_design", 50) + round_score) / 2
            
            # Calculate overall score (weighted)
            resume_score = ai_profile.get("resume_score", 50)
            gap_score = ai_profile.get("gap_analysis_score", 50)
            
            overall_score = (
                avg_interview_score * 0.5 +  # Interview practice matters most
                resume_score * 0.3 +
                gap_score * 0.2
            )
            
            # Update profile
            update_data = {
                "ai_profile.interview_score": round(avg_interview_score, 1),
                "ai_profile.interview_history": interview_history,
                "ai_profile.skill_scores": skill_scores,
                "ai_profile.overall_score": round(overall_score, 1),
                "ai_profile.last_interview_date": datetime.utcnow(),
                "ai_profile.interviews_completed": len(interview_history),
                "ai_profile.strengths": report.get("strengths", []),
                "ai_profile.areas_to_improve": report.get("areas_to_improve", []),
                "updated_at": datetime.utcnow()
            }
            
            await self._users_collection().update_one(
                {"_id": ObjectId(student_id)},
                {"$set": update_data}
            )
            
            return {
                "updated": True,
                "new_interview_score": round(avg_interview_score, 1),
                "new_overall_score": round(overall_score, 1),
                "skill_scores": skill_scores
            }
            
        except Exception as e:
            return {"updated": False, "error": str(e)}
    
    async def _update_matching_score(
        self,
        student_id: str,
        interview_score: float
    ):
        """Update matching score for Module 2 integration."""
        try:
            # Boost student's visibility in job matching based on interview practice
            # Students who practice interviews get a boost in matching algorithms
            
            interview_boost = min(20, interview_score * 0.2)  # Up to 20 point boost
            
            await self._users_collection().update_one(
                {"_id": ObjectId(student_id)},
                {
                    "$set": {
                        "matching_profile.interview_boost": interview_boost,
                        "matching_profile.active_interviewer": True,
                        "matching_profile.last_practice": datetime.utcnow()
                    }
                }
            )
        except Exception:
            pass
    
    async def _log_activity(
        self,
        student_id: str,
        activity_type: str,
        details: Dict[str, Any]
    ):
        """Log user activity for tracking and analytics."""
        try:
            await self._activities_collection().insert_one({
                "user_id": ObjectId(student_id),
                "type": activity_type,
                "details": details,
                "timestamp": datetime.utcnow()
            })
        except Exception:
            pass
    
    # ============ Get Interview Statistics ============
    
    async def get_student_interview_stats(
        self,
        student_id: str
    ) -> Dict[str, Any]:
        """Get comprehensive interview statistics for a student."""
        
        # Get all completed sessions
        sessions = await self._sessions_collection().find({
            "student_id": ObjectId(student_id),
            "status": SessionStatus.COMPLETED
        }).to_list(100)
        
        if not sessions:
            return {
                "total_interviews": 0,
                "average_score": 0,
                "companies_practiced": [],
                "strongest_area": None,
                "weakest_area": None,
                "improvement_trend": "no_data"
            }
        
        # Calculate statistics
        total = len(sessions)
        scores = [s.get("overall_score", 0) for s in sessions]
        avg_score = sum(scores) / total
        
        # Companies practiced
        companies = list(set(s.get("company", "Unknown") for s in sessions))
        
        # Trend analysis (last 5 vs first 5)
        if len(scores) >= 5:
            first_half = sum(scores[:len(scores)//2]) / (len(scores)//2)
            second_half = sum(scores[len(scores)//2:]) / (len(scores) - len(scores)//2)
            
            if second_half > first_half + 5:
                trend = "improving"
            elif second_half < first_half - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        # Skill breakdown
        skill_totals = {"dsa": [], "behavioral": [], "system_design": []}
        
        for session in sessions:
            for round_data in session.get("rounds", []):
                round_type = round_data.get("type", "").lower()
                score = round_data.get("score", 0)
                
                if "dsa" in round_type:
                    skill_totals["dsa"].append(score)
                elif "behavioral" in round_type:
                    skill_totals["behavioral"].append(score)
                elif "design" in round_type:
                    skill_totals["system_design"].append(score)
        
        skill_avgs = {}
        for skill, scores_list in skill_totals.items():
            if scores_list:
                skill_avgs[skill] = sum(scores_list) / len(scores_list)
        
        strongest = max(skill_avgs, key=skill_avgs.get) if skill_avgs else None
        weakest = min(skill_avgs, key=skill_avgs.get) if skill_avgs else None
        
        return {
            "total_interviews": total,
            "average_score": round(avg_score, 1),
            "companies_practiced": companies,
            "skill_averages": skill_avgs,
            "strongest_area": strongest,
            "weakest_area": weakest,
            "improvement_trend": trend,
            "recent_sessions": [
                {
                    "session_id": str(s["_id"]),
                    "company": s.get("company"),
                    "score": s.get("overall_score", 0),
                    "date": s.get("completed_at")
                }
                for s in sessions[-5:]
            ]
        }
    
    # ============ Quick Interview (Demo Mode) ============
    
    async def quick_start_demo(
        self,
        student_id: str,
        company: str = "Amazon",
        difficulty: str = "medium"
    ) -> Dict[str, Any]:
        """
        Quick start a demo interview without resume/JD.
        Good for testing or quick practice.
        """
        return await self.start_full_interview(
            student_id=student_id,
            company=company,
            role="Software Engineer",
            resume_id=None,
            jd_text=None
        )
    
    # ============ Validation & Diagnostics ============
    
    async def validate_flow(
        self,
        student_id: str
    ) -> Dict[str, Any]:
        """
        Validate that all components of the interview flow are working.
        Useful for testing and debugging.
        """
        diagnostics = {
            "resume_service": False,
            "jd_service": False,
            "company_service": False,
            "orchestrator_service": False,
            "database_connection": False
        }
        
        # Test database
        try:
            await self._users_collection().find_one({})
            diagnostics["database_connection"] = True
        except Exception as e:
            diagnostics["database_error"] = str(e)
        
        # Test resume parser
        try:
            # Just check if service exists
            if resume_parser:
                diagnostics["resume_service"] = True
        except Exception as e:
            diagnostics["resume_error"] = str(e)
        
        # Test JD parser
        try:
            test_jd = "Software Engineer at TestCo. Requirements: Python, AWS"
            result = await jd_parser.parse_jd(test_jd)
            if result.get("success"):
                diagnostics["jd_service"] = True
        except Exception as e:
            diagnostics["jd_error"] = str(e)
        
        # Test company service
        try:
            result = await company_researcher.get_company_interview_pattern("Amazon")
            if result:
                diagnostics["company_service"] = True
        except Exception as e:
            diagnostics["company_error"] = str(e)
        
        # Test orchestrator
        try:
            if interview_orchestrator:
                diagnostics["orchestrator_service"] = True
        except Exception as e:
            diagnostics["orchestrator_error"] = str(e)
        
        all_ok = all(diagnostics[k] for k in [
            "resume_service", "jd_service", "company_service", 
            "orchestrator_service", "database_connection"
        ])
        
        return {
            "status": "healthy" if all_ok else "degraded",
            "diagnostics": diagnostics,
            "message": "All systems operational" if all_ok else "Some services have issues"
        }


# Singleton instance
interview_flow = InterviewFlowService()
