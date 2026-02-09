"""
Job Description Parser Service
Extracts structured data from job descriptions with AI enhancement option.
Features: Section detection, skill extraction, experience level detection, salary parsing.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
import asyncio

logger = logging.getLogger(__name__)


# Section header patterns for JD parsing
JD_SECTION_PATTERNS = {
    "requirements": [
        r"(?i)^(requirements?|required\s+skills?|must\s+have|essential|what\s+you.*need|what\s+we.*looking)",
        r"(?i)^(technical\s+requirements?|key\s+requirements?|minimum\s+qualifications?)",
    ],
    "nice_to_have": [
        r"(?i)^(nice\s+to\s+have|preferred|bonus|plus|good\s+to\s+have|desired)",
        r"(?i)^(preferred\s+qualifications?|optional\s+skills?)",
    ],
    "responsibilities": [
        r"(?i)^(responsibilities?|what\s+you.*do|role|duties|key\s+responsibilities)",
        r"(?i)^(about\s+the\s+role|job\s+description|overview)",
    ],
    "qualifications": [
        r"(?i)^(qualifications?|education|background|experience\s+requirements?)",
        r"(?i)^(who\s+you\s+are|ideal\s+candidate)",
    ],
    "benefits": [
        r"(?i)^(benefits?|perks|what\s+we\s+offer|compensation)",
    ],
    "about_company": [
        r"(?i)^(about\s+us|about\s+the\s+company|who\s+we\s+are|company\s+overview)",
    ],
}

# Experience level keywords
EXPERIENCE_LEVELS = {
    "intern": ["intern", "internship", "trainee", "student"],
    "entry": ["entry-level", "entry level", "fresher", "graduate", "junior", "0-1 year", "0-2 year"],
    "mid": ["mid-level", "mid level", "2-4 year", "3-5 year", "2+ year", "3+ year"],
    "senior": ["senior", "lead", "5+ year", "5-8 year", "6+ year", "experienced"],
    "principal": ["principal", "staff", "architect", "8+ year", "10+ year"],
    "manager": ["manager", "head of", "director", "vp", "vice president"],
}

# Common tech skills for extraction (extended)
TECH_SKILLS_KEYWORDS = [
    # Programming Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang", "rust", "ruby",
    "php", "swift", "kotlin", "scala", "r", "matlab", "perl", "lua", "dart", "elixir",
    
    # Frontend
    "react", "reactjs", "angular", "vue", "vuejs", "svelte", "nextjs", "next.js", "nuxt",
    "html", "css", "sass", "scss", "less", "tailwind", "bootstrap", "material-ui", "chakra",
    "webpack", "vite", "babel", "jquery", "redux", "mobx", "zustand",
    
    # Backend
    "node", "nodejs", "express", "fastapi", "django", "flask", "spring", "springboot",
    "rails", "laravel", "asp.net", ".net", "nestjs", "gin", "fiber",
    
    # Databases
    "mongodb", "postgresql", "postgres", "mysql", "redis", "elasticsearch", "cassandra",
    "dynamodb", "sqlite", "oracle", "sql server", "mariadb", "neo4j", "firebase",
    
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "k8s", "terraform",
    "jenkins", "gitlab ci", "github actions", "circleci", "ansible", "puppet", "chef",
    "cloudformation", "ecs", "eks", "lambda", "s3", "ec2", "rds",
    
    # Data & ML
    "machine learning", "deep learning", "tensorflow", "pytorch", "scikit-learn", "pandas",
    "numpy", "spark", "hadoop", "kafka", "airflow", "mlflow", "data science", "nlp",
    "computer vision", "ai", "artificial intelligence", "data engineering", "etl",
    
    # Tools & Practices
    "git", "github", "gitlab", "bitbucket", "jira", "confluence", "agile", "scrum",
    "ci/cd", "devops", "microservices", "rest", "restful", "graphql", "grpc", "api",
    "linux", "unix", "bash", "shell", "powershell",
    
    # Other
    "system design", "distributed systems", "cloud architecture", "security", "oauth",
    "jwt", "authentication", "authorization", "testing", "unit testing", "tdd",
    "performance optimization", "scalability", "high availability",
]

# Skill normalization mapping
SKILL_NORMALIZATION = {
    # JavaScript ecosystem
    "reactjs": "react", "react.js": "react", "react js": "react",
    "vuejs": "vue", "vue.js": "vue", "vue js": "vue",
    "angularjs": "angular", "angular.js": "angular",
    "nodejs": "node.js", "node": "node.js", "node js": "node.js",
    "nextjs": "next.js", "next": "next.js",
    "nuxtjs": "nuxt.js", "nuxt": "nuxt.js",
    "expressjs": "express", "express.js": "express",
    "nestjs": "nest.js", "nest": "nest.js",
    "js": "javascript", "ecmascript": "javascript",
    "ts": "typescript",
    
    # Python ecosystem
    "python3": "python", "py": "python", "python2": "python",
    "fast-api": "fastapi", "fast api": "fastapi",
    "sci-kit learn": "scikit-learn", "sklearn": "scikit-learn",
    
    # Java ecosystem
    "spring-boot": "spring boot", "springboot": "spring boot",
    
    # Databases
    "postgres": "postgresql", "pg": "postgresql",
    "mongo": "mongodb", "mongo db": "mongodb",
    "mysql": "mysql", "my sql": "mysql",
    "elastic search": "elasticsearch", "elastic": "elasticsearch",
    "dynamodb": "dynamodb", "dynamo db": "dynamodb", "dynamo": "dynamodb",
    
    # Cloud
    "amazon web services": "aws", "amazon aws": "aws",
    "google cloud platform": "gcp", "google cloud": "gcp",
    "microsoft azure": "azure", "ms azure": "azure",
    "k8s": "kubernetes", "kube": "kubernetes",
    
    # DevOps
    "ci cd": "ci/cd", "cicd": "ci/cd",
    "github-actions": "github actions",
    "gitlab-ci": "gitlab ci",
    
    # General
    "golang": "go",
    "c sharp": "c#", "csharp": "c#",
    "c plus plus": "c++", "cpp": "c++",
    "restful api": "rest api", "rest": "rest api",
    "graphql api": "graphql",
    "ml": "machine learning",
    "dl": "deep learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
}


class JobDescriptionParser:
    """
    Parses job descriptions to extract structured data.
    Supports AI-enhanced extraction for better accuracy.
    """
    
    def __init__(self):
        self._llm_service = None
    
    def _get_llm_service(self):
        """Lazy load LLM service."""
        if self._llm_service is None:
            try:
                from .llm_service import llm_service
                self._llm_service = llm_service
            except Exception:
                self._llm_service = None
        return self._llm_service
    
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name to standard form."""
        # Clean the skill
        skill_clean = skill.lower().strip()
        skill_clean = re.sub(r'[^\w\s\.\+\#\-/]', '', skill_clean)
        
        # Check normalization mapping
        if skill_clean in SKILL_NORMALIZATION:
            return SKILL_NORMALIZATION[skill_clean]
        
        return skill_clean.title()
    
    def find_section_bounds(self, text: str) -> Dict[str, Tuple[int, int]]:
        """Find start and end positions of each section in JD."""
        lines = text.split("\n")
        sections = {}
        section_order = []
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            for section_name, patterns in JD_SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, line_stripped):
                        sections[section_name] = i
                        section_order.append((section_name, i))
                        break
        
        # Calculate end positions
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
    
    def extract_job_title(self, text: str) -> str:
        """Extract job title from JD text."""
        lines = text.split("\n")
        
        # Usually first non-empty line is the title
        for line in lines[:5]:
            line = line.strip()
            if not line:
                continue
            # Skip if it looks like company name or location
            if any(word in line.lower() for word in ["about", "location", "http", "www", "@"]):
                continue
            # Job titles are usually short
            if 3 < len(line) < 80:
                return line
        
        return ""
    
    def extract_company(self, text: str) -> str:
        """Extract company name from JD."""
        # Look for common patterns
        patterns = [
            r"(?i)(?:at|@|company[:\s]+|employer[:\s]+)\s*([A-Z][a-zA-Z0-9\s&\.]+)",
            r"(?i)about\s+([A-Z][a-zA-Z0-9\s&\.]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:500])
            if match:
                company = match.group(1).strip()
                if 2 < len(company) < 50:
                    return company
        
        # Try from about_company section
        about_text = self.extract_section_text(text, "about_company")
        if about_text:
            # First sentence often has company name
            first_sentence = about_text.split(".")[0]
            # Look for capitalized words
            words = re.findall(r'\b[A-Z][a-zA-Z]+\b', first_sentence)
            if words:
                return " ".join(words[:3])
        
        return ""
    
    def extract_experience_level(self, text: str) -> str:
        """Determine experience level from JD."""
        text_lower = text.lower()
        
        # Check for explicit years pattern
        years_match = re.search(r'(\d+)\+?\s*(?:to|-)\s*(\d+)?\s*years?', text_lower)
        if years_match:
            min_years = int(years_match.group(1))
            if min_years == 0:
                return "entry"
            elif min_years <= 2:
                return "mid"
            elif min_years <= 5:
                return "senior"
            else:
                return "principal"
        
        # Check keywords
        for level, keywords in EXPERIENCE_LEVELS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return level
        
        return "not_specified"
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from given text."""
        skills = set()
        text_lower = text.lower()
        
        # Match known tech skills
        for skill in TECH_SKILLS_KEYWORDS:
            # Word boundary matching
            pattern = r'\b' + re.escape(skill.lower()) + r'\b'
            if re.search(pattern, text_lower):
                normalized = self.normalize_skill(skill)
                skills.add(normalized)
        
        # Extract from bullet points
        lines = text.split("\n")
        for line in lines:
            # Remove bullet points
            line = re.sub(r'^[\s•\-\*▪◦]+', '', line).strip()
            
            # Short lines with skills often follow pattern "Skill: description" or just "Skill"
            if len(line) < 50 and not line.endswith("."):
                parts = re.split(r'[,|;/]', line)
                for part in parts:
                    part = part.strip()
                    if 2 <= len(part) <= 30:
                        # Check if it's likely a skill (title case or known)
                        for skill in TECH_SKILLS_KEYWORDS:
                            if skill.lower() in part.lower():
                                skills.add(self.normalize_skill(skill))
        
        return sorted(skills)
    
    def extract_required_skills(self, text: str) -> List[str]:
        """Extract required/must-have skills."""
        # First try dedicated section
        req_text = self.extract_section_text(text, "requirements")
        
        if req_text:
            return self.extract_skills_from_text(req_text)
        
        # Fallback: extract from entire text
        return self.extract_skills_from_text(text)
    
    def extract_nice_to_have_skills(self, text: str) -> List[str]:
        """Extract nice-to-have/preferred skills."""
        nice_text = self.extract_section_text(text, "nice_to_have")
        
        if nice_text:
            return self.extract_skills_from_text(nice_text)
        
        return []
    
    def extract_responsibilities(self, text: str) -> List[str]:
        """Extract job responsibilities."""
        resp_text = self.extract_section_text(text, "responsibilities")
        
        if not resp_text:
            return []
        
        responsibilities = []
        lines = resp_text.split("\n")
        
        for line in lines:
            line = re.sub(r'^[\s•\-\*▪◦\d\.]+', '', line).strip()
            if len(line) > 20:
                responsibilities.append(line)
        
        return responsibilities[:10]  # Limit to 10
    
    def extract_qualifications(self, text: str) -> List[str]:
        """Extract qualifications/requirements."""
        qual_text = self.extract_section_text(text, "qualifications")
        
        if not qual_text:
            # Try requirements section
            qual_text = self.extract_section_text(text, "requirements")
        
        if not qual_text:
            return []
        
        qualifications = []
        lines = qual_text.split("\n")
        
        for line in lines:
            line = re.sub(r'^[\s•\-\*▪◦\d\.]+', '', line).strip()
            if len(line) > 15:
                qualifications.append(line)
        
        return qualifications[:10]
    
    def extract_salary_range(self, text: str) -> Dict[str, Any]:
        """Extract salary range if mentioned."""
        salary = {"min": None, "max": None, "currency": "USD", "period": "yearly"}
        
        # Common salary patterns
        patterns = [
            # $100,000 - $150,000
            r'\$\s*([\d,]+)\s*[-–to]+\s*\$?\s*([\d,]+)',
            # 100k - 150k
            r'([\d]+)k\s*[-–to]+\s*([\d]+)k',
            # $100,000/year
            r'\$\s*([\d,]+)\s*(?:per\s+year|/year|annually)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_val = int(match.group(1).replace(",", ""))
                    # Handle "k" notation
                    if min_val < 1000:
                        min_val *= 1000
                    salary["min"] = min_val
                    
                    if match.lastindex >= 2:
                        max_val = int(match.group(2).replace(",", ""))
                        if max_val < 1000:
                            max_val *= 1000
                        salary["max"] = max_val
                    
                    break
                except (ValueError, IndexError):
                    continue
        
        # Detect currency
        if "₹" in text or "inr" in text.lower() or "lpa" in text.lower():
            salary["currency"] = "INR"
        elif "€" in text or "eur" in text.lower():
            salary["currency"] = "EUR"
        elif "£" in text or "gbp" in text.lower():
            salary["currency"] = "GBP"
        
        return salary if salary["min"] else {}
    
    def extract_location(self, text: str) -> Dict[str, Any]:
        """Extract job location."""
        location = {"city": None, "country": None, "remote": False, "hybrid": False}
        
        text_lower = text.lower()
        
        # Remote patterns
        if any(word in text_lower for word in ["remote", "work from home", "wfh", "fully remote"]):
            location["remote"] = True
        
        if any(word in text_lower for word in ["hybrid", "flexible location", "partially remote"]):
            location["hybrid"] = True
        
        # Common location patterns
        loc_patterns = [
            r"(?i)location[:\s]+([A-Za-z\s,]+)",
            r"(?i)based\s+in\s+([A-Za-z\s,]+)",
            r"(?i)office[:\s]+([A-Za-z\s,]+)",
        ]
        
        for pattern in loc_patterns:
            match = re.search(pattern, text)
            if match:
                loc_str = match.group(1).strip()[:50]
                parts = [p.strip() for p in loc_str.split(",")]
                if parts:
                    location["city"] = parts[0]
                if len(parts) > 1:
                    location["country"] = parts[-1]
                break
        
        return location
    
    def calculate_confidence(self, parsed_data: Dict[str, Any]) -> float:
        """Calculate parsing confidence score."""
        score = 0
        
        if parsed_data.get("job_title"):
            score += 20
        if parsed_data.get("company"):
            score += 15
        if parsed_data.get("required_skills"):
            score += min(30, len(parsed_data["required_skills"]) * 5)
        if parsed_data.get("experience_level") != "not_specified":
            score += 15
        if parsed_data.get("responsibilities"):
            score += 10
        if parsed_data.get("qualifications"):
            score += 10
        
        return min(100, score)
    
    async def ai_enhance_extraction(
        self,
        jd_text: str,
        parsed_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to enhance JD extraction."""
        llm = self._get_llm_service()
        
        if llm is None:
            return parsed_data
        
        try:
            prompt = f"""Analyze this job description and extract key information.

JOB DESCRIPTION:
{jd_text[:3000]}

CURRENT EXTRACTION (verify and correct):
- Job Title: {parsed_data.get('job_title', 'Not found')}
- Company: {parsed_data.get('company', 'Not found')}
- Required Skills: {', '.join(parsed_data.get('required_skills', [])[:8])}
- Experience Level: {parsed_data.get('experience_level', 'Not found')}

Please verify and provide corrections. Respond in EXACTLY this format:
JOB_TITLE: [extracted title]
COMPANY: [company name]
EXPERIENCE_LEVEL: [intern/entry/mid/senior/principal/manager]
REQUIRED_SKILLS: [comma-separated list of technical skills]
NICE_TO_HAVE: [comma-separated list of preferred skills]

If current extraction is correct, respond "CORRECT" for that field."""

            response = await llm.generate(prompt)
            
            if response and not response.startswith("Error"):
                enhanced = self._parse_ai_corrections(response, parsed_data)
                enhanced["ai_enhanced"] = True
                return enhanced
        
        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
        
        return parsed_data
    
    def _parse_ai_corrections(
        self,
        response: str,
        original: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse AI response and merge corrections."""
        enhanced = original.copy()
        
        lines = response.split("\n")
        for line in lines:
            line = line.strip()
            
            if line.upper().startswith("JOB_TITLE:"):
                value = line[10:].strip()
                if value and value.upper() != "CORRECT":
                    enhanced["job_title"] = value
            
            elif line.upper().startswith("COMPANY:"):
                value = line[8:].strip()
                if value and value.upper() != "CORRECT":
                    enhanced["company"] = value
            
            elif line.upper().startswith("EXPERIENCE_LEVEL:"):
                value = line[17:].strip().lower()
                if value and value != "correct":
                    enhanced["experience_level"] = value
            
            elif line.upper().startswith("REQUIRED_SKILLS:"):
                value = line[16:].strip()
                if value and value.upper() != "CORRECT":
                    skills = [self.normalize_skill(s.strip()) for s in value.split(",") if s.strip()]
                    if skills:
                        enhanced["required_skills"] = skills
            
            elif line.upper().startswith("NICE_TO_HAVE:"):
                value = line[13:].strip()
                if value and value.upper() != "CORRECT":
                    skills = [self.normalize_skill(s.strip()) for s in value.split(",") if s.strip()]
                    if skills:
                        enhanced["nice_to_have_skills"] = skills
        
        return enhanced
    
    async def parse_jd(
        self,
        jd_text: str,
        use_ai_enhancement: bool = False
    ) -> Dict[str, Any]:
        """
        Main entry point: Parse a job description.
        
        Args:
            jd_text: Raw job description text
            use_ai_enhancement: Whether to use LLM for better extraction
            
        Returns:
            Parsed JD data with all fields
        """
        if not jd_text or len(jd_text.strip()) < 50:
            return {
                "success": False,
                "error": "Job description text too short or empty",
            }
        
        # Extract all fields
        parsed_data = {
            "job_title": self.extract_job_title(jd_text),
            "company": self.extract_company(jd_text),
            "required_skills": self.extract_required_skills(jd_text),
            "nice_to_have_skills": self.extract_nice_to_have_skills(jd_text),
            "experience_level": self.extract_experience_level(jd_text),
            "responsibilities": self.extract_responsibilities(jd_text),
            "qualifications": self.extract_qualifications(jd_text),
            "salary_range": self.extract_salary_range(jd_text),
            "location": self.extract_location(jd_text),
            "ai_enhanced": False,
        }
        
        # Calculate initial confidence
        parsed_data["parsing_confidence"] = self.calculate_confidence(parsed_data)
        
        # AI enhancement if requested
        if use_ai_enhancement:
            parsed_data = await self.ai_enhance_extraction(jd_text, parsed_data)
            parsed_data["parsing_confidence"] = self.calculate_confidence(parsed_data)
        
        parsed_data["success"] = True
        return parsed_data


# Singleton instance
jd_parser = JobDescriptionParser()
