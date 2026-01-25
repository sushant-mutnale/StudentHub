"""
Resume Parser Service
Extracts structured data from PDF resumes using multiple strategies.
Features: Multi-library fallback, AI enhancement option, confidence scoring.
"""

import os
import re
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import asyncio


# Section header patterns for detection
SECTION_PATTERNS = {
    "skills": [
        r"(?i)^(technical\s+)?skills?",
        r"(?i)^core\s+competencies",
        r"(?i)^technologies",
        r"(?i)^expertise",
        r"(?i)^proficiencies",
    ],
    "experience": [
        r"(?i)^(work\s+)?experience",
        r"(?i)^employment(\s+history)?",
        r"(?i)^professional\s+experience",
        r"(?i)^work\s+history",
        r"(?i)^career\s+history",
    ],
    "education": [
        r"(?i)^education(al)?(\s+background)?",
        r"(?i)^academic(\s+background)?",
        r"(?i)^qualifications",
    ],
    "projects": [
        r"(?i)^projects?",
        r"(?i)^personal\s+projects",
        r"(?i)^key\s+projects",
        r"(?i)^notable\s+projects",
    ],
    "summary": [
        r"(?i)^(professional\s+)?summary",
        r"(?i)^(career\s+)?objective",
        r"(?i)^about\s+me",
        r"(?i)^profile",
    ],
    "certifications": [
        r"(?i)^certifications?",
        r"(?i)^licenses?(\s+and\s+certifications?)?",
        r"(?i)^credentials",
    ],
}

# Common tech skills for extraction
TECH_SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust", "ruby",
    "react", "angular", "vue", "node", "express", "django", "flask", "fastapi", "spring",
    "mongodb", "postgresql", "mysql", "redis", "elasticsearch", "cassandra",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "github actions",
    "git", "linux", "bash", "sql", "nosql", "rest", "graphql", "grpc",
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn",
    "html", "css", "sass", "tailwind", "bootstrap",
    "agile", "scrum", "jira", "confluence",
]


class ResumeParser:
    """
    Multi-strategy resume parser with AI enhancement capability.
    """
    
    def __init__(self, use_ai: bool = False):
        self.use_ai = use_ai
        self._llm_service = None
        self._gap_analyzer = None
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def _get_gap_analyzer(self):
        """Lazy load gap analyzer for skill normalization."""
        if self._gap_analyzer is None:
            try:
                from .gap_analyzer import skill_gap_analyzer
                self._gap_analyzer = skill_gap_analyzer
            except Exception:
                self._gap_analyzer = None
        return self._gap_analyzer
    
    def extract_text_pdfplumber(self, file_path: str) -> str:
        """Extract text using pdfplumber (primary method)."""
        try:
            import pdfplumber
            
            text_parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"[pdfplumber] Extraction failed: {e}")
            return ""
    
    def extract_text_pymupdf(self, file_path: str) -> str:
        """Extract text using PyMuPDF (fallback method)."""
        try:
            import fitz  # PyMuPDF
            
            text_parts = []
            doc = fitz.open(file_path)
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            
            return "\n".join(text_parts)
        except Exception as e:
            print(f"[PyMuPDF] Extraction failed: {e}")
            return ""
    
    def extract_text(self, file_path: str) -> Tuple[str, str]:
        """
        Extract text from PDF with fallback chain.
        Returns (text, method_used)
        """
        # Try pdfplumber first
        text = self.extract_text_pdfplumber(file_path)
        if text.strip():
            return text, "pdfplumber"
        
        # Fallback to PyMuPDF
        text = self.extract_text_pymupdf(file_path)
        if text.strip():
            return text, "pymupdf"
        
        return "", "none"
    
    def extract_contact_info(self, text: str) -> Dict[str, Optional[str]]:
        """Extract contact information from resume text."""
        contact = {
            "name": None,
            "email": None,
            "phone": None,
            "linkedin": None,
            "github": None,
            "location": None,
        }
        
        lines = text.split("\n")
        
        # Email pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        email_match = re.search(email_pattern, text)
        if email_match:
            contact["email"] = email_match.group(0).lower()
        
        # Phone patterns (various formats)
        phone_patterns = [
            r'(?:\+91[-\s]?)?[6-9]\d{9}',  # Indian mobile
            r'(?:\+1[-\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # US format
            r'\d{10,12}',  # Generic 10-12 digits
        ]
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                contact["phone"] = phone_match.group(0)
                break
        
        # LinkedIn
        linkedin_pattern = r'linkedin\.com/in/([a-zA-Z0-9_-]+)'
        linkedin_match = re.search(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_match:
            contact["linkedin"] = f"https://linkedin.com/in/{linkedin_match.group(1)}"
        
        # GitHub
        github_pattern = r'github\.com/([a-zA-Z0-9_-]+)'
        github_match = re.search(github_pattern, text, re.IGNORECASE)
        if github_match:
            contact["github"] = f"https://github.com/{github_match.group(1)}"
        
        # Name - usually first non-empty line that's not an email/URL
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            if "@" in line or "http" in line.lower() or line.isdigit():
                continue
            if len(line.split()) <= 4 and len(line) > 2:
                # Likely a name (2-4 words, not too short)
                contact["name"] = line.title()
                break
        
        return contact
    
    def find_section_bounds(self, text: str) -> Dict[str, Tuple[int, int]]:
        """Find start and end positions of each section."""
        lines = text.split("\n")
        sections = {}
        section_order = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            for section_name, patterns in SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, line_stripped):
                        sections[section_name] = i
                        section_order.append((section_name, i))
                        break
        
        # Calculate end positions based on next section
        bounds = {}
        for idx, (section_name, start_line) in enumerate(section_order):
            if idx + 1 < len(section_order):
                end_line = section_order[idx + 1][1]
            else:
                end_line = len(lines)
            bounds[section_name] = (start_line, end_line)
        
        return bounds
    
    def extract_section_text(self, text: str, section_name: str) -> str:
        """Extract text for a specific section."""
        bounds = self.find_section_bounds(text)
        
        if section_name not in bounds:
            return ""
        
        lines = text.split("\n")
        start, end = bounds[section_name]
        
        # Skip the header line
        section_lines = lines[start + 1:end]
        return "\n".join(section_lines).strip()
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume."""
        skills = set()
        
        # Try to find skills section
        skills_text = self.extract_section_text(text, "skills")
        
        if not skills_text:
            # Search entire document for tech skills
            skills_text = text
        
        text_lower = skills_text.lower()
        
        # Match known tech skills
        for skill in TECH_SKILLS:
            if skill.lower() in text_lower:
                skills.add(skill.title())
        
        # Extract from bullet points and comma-separated lists
        lines = skills_text.split("\n")
        for line in lines:
            # Remove bullet points
            line = re.sub(r'^[\s•\-\*▪◦]+', '', line).strip()
            
            # Split by common delimiters
            parts = re.split(r'[,|;•]', line)
            for part in parts:
                part = part.strip()
                if 2 <= len(part) <= 30 and not part.isdigit():
                    # Looks like a skill
                    skills.add(part)
        
        # Normalize skills using gap_analyzer if available
        analyzer = self._get_gap_analyzer()
        if analyzer:
            normalized = []
            for skill in skills:
                norm_skill = analyzer.normalize_skill(skill)
                normalized.append(norm_skill.title() if norm_skill else skill)
            return sorted(set(normalized))
        
        return sorted(skills)
    
    def extract_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience entries."""
        experiences = []
        exp_text = self.extract_section_text(text, "experience")
        
        if not exp_text:
            return experiences
        
        # Date patterns
        date_pattern = r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|' \
                       r'\d{1,2}/\d{4}|\d{4})\s*[-–—to]+\s*(Present|Current|' \
                       r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}|' \
                       r'\d{1,2}/\d{4}|\d{4})'
        
        lines = exp_text.split("\n")
        current_entry = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for date range (often indicates new entry)
            date_match = re.search(date_pattern, line, re.IGNORECASE)
            
            if date_match:
                # Save previous entry
                if current_entry:
                    experiences.append(current_entry)
                
                current_entry = {
                    "company": "",
                    "title": "",
                    "start_date": date_match.group(1),
                    "end_date": date_match.group(2),
                    "description": [],
                    "raw_line": line,
                }
                
                # Try to extract company/title from same line
                before_date = line[:date_match.start()].strip()
                if before_date:
                    parts = re.split(r'[–\-|,]', before_date, 1)
                    if len(parts) >= 2:
                        current_entry["title"] = parts[0].strip()
                        current_entry["company"] = parts[1].strip()
                    else:
                        current_entry["company"] = before_date
            
            elif current_entry:
                # Add to description
                if line.startswith(("•", "-", "*", "▪", "◦")):
                    line = line[1:].strip()
                current_entry["description"].append(line)
        
        # Don't forget last entry
        if current_entry:
            experiences.append(current_entry)
        
        # Clean up descriptions
        for exp in experiences:
            exp["description"] = " ".join(exp["description"])[:500]
        
        return experiences
    
    def extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education entries."""
        education = []
        edu_text = self.extract_section_text(text, "education")
        
        if not edu_text:
            return education
        
        # Common degree patterns
        degree_patterns = [
            r'(?i)(B\.?S\.?|B\.?A\.?|B\.?Tech|B\.?E\.?|Bachelor)',
            r'(?i)(M\.?S\.?|M\.?A\.?|M\.?Tech|M\.?E\.?|Master|MBA)',
            r'(?i)(Ph\.?D|Doctorate)',
            r'(?i)(Diploma|Certificate)',
        ]
        
        lines = edu_text.split("\n")
        current_entry = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains a degree
            has_degree = any(re.search(p, line) for p in degree_patterns)
            
            # Check for year (graduation year)
            year_match = re.search(r'20\d{2}|19\d{2}', line)
            
            if has_degree or (year_match and len(line) > 10):
                if current_entry:
                    education.append(current_entry)
                
                current_entry = {
                    "degree": "",
                    "institution": "",
                    "year": year_match.group(0) if year_match else "",
                    "gpa": "",
                    "raw_line": line,
                }
                
                # Try to parse degree and institution
                # Often format: "Degree in Field, University, Year"
                parts = re.split(r'[,|–\-]', line)
                if parts:
                    current_entry["degree"] = parts[0].strip()
                if len(parts) > 1:
                    current_entry["institution"] = parts[1].strip()
                
                # Look for GPA
                gpa_match = re.search(r'(?:GPA|CGPA)[:\s]*(\d+\.?\d*)', line, re.IGNORECASE)
                if gpa_match:
                    current_entry["gpa"] = gpa_match.group(1)
            
            elif current_entry and not has_degree:
                # Additional info for current entry
                if not current_entry["institution"] and len(line) > 5:
                    current_entry["institution"] = line
        
        if current_entry:
            education.append(current_entry)
        
        return education
    
    def extract_projects(self, text: str) -> List[Dict[str, Any]]:
        """Extract project entries."""
        projects = []
        proj_text = self.extract_section_text(text, "projects")
        
        if not proj_text:
            return projects
        
        lines = proj_text.split("\n")
        current_project = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Project titles are often bold/larger or on their own line
            # Heuristic: short lines that look like titles
            is_title = (
                len(line) < 60 and
                not line.startswith(("•", "-", "*")) and
                not re.match(r'^\d', line)
            )
            
            if is_title and (not current_project or line[0].isupper()):
                if current_project:
                    projects.append(current_project)
                
                current_project = {
                    "name": line,
                    "description": "",
                    "technologies": [],
                }
            elif current_project:
                # Add to description
                if line.startswith(("•", "-", "*")):
                    line = line[1:].strip()
                
                # Check for tech stack line
                tech_match = re.search(r'(?i)(?:tech(?:nologies)?|stack|built with)[:\s]*(.*)', line)
                if tech_match:
                    techs = re.split(r'[,|]', tech_match.group(1))
                    current_project["technologies"] = [t.strip() for t in techs if t.strip()]
                else:
                    current_project["description"] += " " + line
        
        if current_project:
            projects.append(current_project)
        
        # Clean up
        for proj in projects:
            proj["description"] = proj["description"].strip()[:300]
        
        return projects
    
    def calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """
        Calculate parsing confidence score (0-100).
        Based on completeness of extracted data.
        """
        score = 0
        max_score = 100
        
        contact = parsed_data.get("contact", {})
        
        # Contact info (30 points max)
        if contact.get("name"):
            score += 10
        if contact.get("email"):
            score += 10
        if contact.get("phone") or contact.get("linkedin"):
            score += 10
        
        # Skills (25 points max)
        skills = parsed_data.get("skills", [])
        if skills:
            skill_score = min(25, len(skills) * 2.5)
            score += skill_score
        
        # Experience (25 points max)
        experience = parsed_data.get("experience", [])
        if experience:
            exp_score = min(25, len(experience) * 8)
            score += exp_score
        
        # Education (15 points max)
        education = parsed_data.get("education", [])
        if education:
            edu_score = min(15, len(education) * 7)
            score += edu_score
        
        # Projects (5 points max)
        projects = parsed_data.get("projects", [])
        if projects:
            score += min(5, len(projects) * 2)
        
        return min(100, round(score, 1))
    
    async def ai_enhance_extraction(self, raw_text: str, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to enhance/fix extraction for complex layouts.
        """
        llm = self._get_llm_service()
        
        if llm is None:
            return parsed_data
        
        try:
            prompt = f"""Analyze this resume text and extract structured information.

RESUME TEXT:
{raw_text[:3000]}  # Limit to avoid token overflow

CURRENT EXTRACTION (may have errors):
- Name: {parsed_data.get('contact', {}).get('name', 'Not found')}
- Email: {parsed_data.get('contact', {}).get('email', 'Not found')}
- Skills: {', '.join(parsed_data.get('skills', [])[:10])}

Please verify and correct if needed. Respond in this EXACT format:
NAME: [extracted name]
EMAIL: [extracted email]
PHONE: [extracted phone]
SKILLS: [comma-separated list of technical skills]

Only provide corrections. If current extraction is correct, say "CORRECT" for that field."""

            response = await llm.generate(prompt)
            
            if response and not response.startswith("Error"):
                # Parse LLM response and merge corrections
                enhanced = self._parse_ai_corrections(response, parsed_data)
                enhanced["ai_enhanced"] = True
                return enhanced
        
        except Exception as e:
            print(f"AI enhancement failed: {e}")
        
        return parsed_data
    
    def _parse_ai_corrections(self, response: str, original: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI response and merge corrections."""
        enhanced = original.copy()
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("NAME:"):
                value = line[5:].strip()
                if value and value.upper() != "CORRECT":
                    enhanced.setdefault("contact", {})["name"] = value
            
            elif line.upper().startswith("EMAIL:"):
                value = line[6:].strip()
                if value and value.upper() != "CORRECT" and "@" in value:
                    enhanced.setdefault("contact", {})["email"] = value.lower()
            
            elif line.upper().startswith("PHONE:"):
                value = line[6:].strip()
                if value and value.upper() != "CORRECT":
                    enhanced.setdefault("contact", {})["phone"] = value
            
            elif line.upper().startswith("SKILLS:"):
                value = line[7:].strip()
                if value and value.upper() != "CORRECT":
                    skills = [s.strip() for s in value.split(",") if s.strip()]
                    if skills:
                        enhanced["skills"] = skills
        
        return enhanced
    
    async def parse_resume(
        self,
        file_path: str,
        use_ai_enhancement: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: Parse a resume PDF.
        
        Args:
            file_path: Path to PDF file
            use_ai_enhancement: Whether to use LLM for fixing extraction
            
        Returns:
            Parsed resume data with confidence score
        """
        # Extract text
        raw_text, extraction_method = self.extract_text(file_path)
        
        if not raw_text:
            return {
                "success": False,
                "error": "Could not extract text from PDF",
                "extraction_method": extraction_method,
            }
        
        # Extract structured data
        parsed_data = {
            "contact": self.extract_contact_info(raw_text),
            "skills": self.extract_skills(raw_text),
            "experience": self.extract_experience(raw_text),
            "education": self.extract_education(raw_text),
            "projects": self.extract_projects(raw_text),
            "raw_text": raw_text,
            "extraction_method": extraction_method,
            "ai_enhanced": False,
        }
        
        # Calculate initial confidence
        parsed_data["parsing_confidence"] = self.calculate_confidence(parsed_data)
        
        # AI enhancement if requested and confidence is low
        if use_ai_enhancement or (self.use_ai and parsed_data["parsing_confidence"] < 50):
            parsed_data = await self.ai_enhance_extraction(raw_text, parsed_data)
            # Recalculate confidence after enhancement
            parsed_data["parsing_confidence"] = self.calculate_confidence(parsed_data)
        
        parsed_data["success"] = True
        return parsed_data
    
    def get_file_hash(self, file_path: str) -> str:
        """Calculate MD5 hash of file for deduplication."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def get_file_hash_from_bytes(self, content: bytes) -> str:
        """Calculate MD5 hash from bytes for deduplication."""
        return hashlib.md5(content).hexdigest()


# Singleton instance
resume_parser = ResumeParser()
