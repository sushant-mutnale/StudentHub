"""
Deep Research Tool
Web scraping and company research service for interview preparation.
Features: SerpAPI search, BeautifulSoup scraping, background data updates.
"""

import os
import re
import json
import asyncio
import hashlib
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class ResearchResult:
    """Container for research results."""
    source: str
    title: str
    content: str
    url: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    relevance_score: float = 0.0
    category: str = "general"  # interview, culture, salary, tech_stack, news


class DeepResearchTool:
    """
    Research tool for gathering company and interview data.
    Uses SerpAPI for search
    """
    
    # API Keys from environment
    SERP_API_KEY = os.getenv("SERP_API_KEY", "")
    
    # Search endpoints
    SERP_API_URL = "https://serpapi.com/search.json"
    
    # Research categories and their search patterns
    RESEARCH_TEMPLATES = {
        "interview": [
            "{company} interview questions",
            "{company} software engineer interview experience",
            "{company} coding interview leetcode",
            "{company} system design interview"
        ],
        "culture": [
            "{company} work culture glassdoor",
            "{company} employee reviews",
            "{company} work life balance"
        ],
        "salary": [
            "{company} software engineer salary levels.fyi",
            "{company} compensation packages",
            "{company} fresher salary india"
        ],
        "tech_stack": [
            "{company} tech stack",
            "{company} engineering blog technology",
            "{company} programming languages used"
        ],
        "news": [
            "{company} latest news hiring",
            "{company} engineering announcements",
            "{company} layoffs hiring freeze"
        ]
    }
    
    # Trusted sources for scraping
    TRUSTED_SOURCES = {
        "glassdoor.com": {"category": "culture", "priority": 1},
        "levels.fyi": {"category": "salary", "priority": 1},
        "leetcode.com": {"category": "interview", "priority": 1},
        "blind.com": {"category": "culture", "priority": 2},
        "indeed.com": {"category": "interview", "priority": 2},
        "github.com": {"category": "tech_stack", "priority": 2},
        "medium.com": {"category": "tech_stack", "priority": 3},
        "linkedin.com": {"category": "news", "priority": 2}
    }
    
    def __init__(self):
        self._cache: Dict[str, Dict] = {}  # In-memory cache
        self._cache_ttl = timedelta(hours=24)
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
    
    # ============ Main Research Methods ============
    
    async def research_company(
        self,
        company_name: str,
        categories: List[str] = None,
        max_results_per_category: int = 5
    ) -> Dict[str, Any]:
        """
        Comprehensive company research across multiple categories.
        
        Args:
            company_name: Company to research
            categories: List of categories (interview, culture, salary, tech_stack, news)
            max_results_per_category: Max results per category
        
        Returns:
            {
                "company": str,
                "researched_at": datetime,
                "categories": {
                    "interview": [results],
                    "culture": [results],
                    ...
                },
                "summary": str,
                "key_insights": [str]
            }
        """
        if categories is None:
            categories = ["interview", "culture", "tech_stack"]
        
        # Check cache first
        cache_key = self._get_cache_key(company_name, categories)
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached
        
        results = {
            "company": company_name,
            "researched_at": datetime.utcnow().isoformat(),
            "categories": {},
            "summary": "",
            "key_insights": [],
            "sources_used": []
        }
        
        # Research each category
        for category in categories:
            if category not in self.RESEARCH_TEMPLATES:
                continue
            
            category_results = await self._research_category(
                company_name, 
                category, 
                max_results_per_category
            )
            results["categories"][category] = category_results
        
        # Generate summary using LLM
        results["summary"] = await self._generate_summary(company_name, results["categories"])
        results["key_insights"] = await self._extract_insights(results["categories"])
        
        # Cache results
        self._set_cache(cache_key, results)
        
        return results
    
    async def _research_category(
        self,
        company_name: str,
        category: str,
        max_results: int
    ) -> List[Dict]:
        """Research a single category."""
        results = []
        templates = self.RESEARCH_TEMPLATES.get(category, [])
        
        for template in templates[:2]:  # Limit queries to avoid rate limits
            query = template.format(company=company_name)
            
            # Try SerpAPI first
            if self.SERP_API_KEY:
                serp_results = await self._search_serp(query, max_results)
                results.extend(serp_results)
            else:
                # Fallback to mock data for demo
                mock_results = self._get_mock_results(company_name, category)
                results.extend(mock_results)
            
            if len(results) >= max_results:
                break
        
        # Scrape content from top results
        scraped = []
        for result in results[:max_results]:
            content = await self._scrape_url(result.get("url", ""))
            if content:
                scraped.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "snippet": result.get("snippet", ""),
                    "content": content[:1000],  # Limit content
                    "source": self._extract_domain(result.get("url", ""))
                })
        
        return scraped if scraped else results[:max_results]
    
    # ============ Search Methods ============
    
    # ============ Search Methods ============
    
    async def _search_serp(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search using SerpAPI or Tavily (fallback)."""
        
        # 1. Try SerpAPI if key exists
        if self.SERP_API_KEY:
            try:
                async with aiohttp.ClientSession() as session:
                    params = {
                        "q": query,
                        "api_key": self.SERP_API_KEY,
                        "num": max_results,
                        "engine": "google"
                    }
                    async with session.get(self.SERP_API_URL, params=params, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            organic = data.get("organic_results", [])
                            return [
                                {
                                    "title": r.get("title", ""),
                                    "url": r.get("link", ""),
                                    "snippet": r.get("snippet", "")
                                }
                                for r in organic[:max_results]
                            ]
            except Exception as e:
                logger.error(f"SerpAPI error: {e}")

        # 2. Try Tavily if SerpAPI key missing or failed
        tavily_key = os.getenv("TAVILY_API_KEY")
        if tavily_key:
            return await self._search_tavily(query, max_results, tavily_key)
        
        return []

    async def _search_tavily(self, query: str, max_results: int, api_key: str) -> List[Dict]:
        """Search using Tavily API."""
        try:
            url = "https://api.tavily.com/search"
            payload = {
                "query": query,
                "api_key": api_key,
                "search_depth": "basic",
                "max_results": max_results
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        return [
                            {
                                "title": r.get("title", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("content", "")
                            }
                            for r in results
                        ]
        except Exception as e:
            logger.error(f"Tavily API error: {e}")
        
        return []
    
    # ============ Scraping Methods ============
    
    async def _scrape_url(self, url: str) -> Optional[str]:
        """Scrape content from a URL."""
        if not url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                async with session.get(url, headers=headers, timeout=10) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        return self._extract_text(html)
        except Exception as e:
            logger.error(f"Scraping error for {url}: {e}")
        
        return None
    
    def _extract_text(self, html: str) -> str:
        """Extract readable text from HTML."""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()
            
            # Get text
            text = soup.get_text(separator=" ", strip=True)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            
            return text[:2000]  # Limit length
        except Exception:
            return ""
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc.replace("www.", "")
        except Exception:
            return "unknown"
    
    # ============ LLM-Powered Analysis ============
    
    async def _generate_summary(
        self, 
        company_name: str, 
        categories: Dict[str, List]
    ) -> str:
        """Generate summary using LLM."""
        llm = self._get_llm_service()
        if not llm:
            return f"Research completed for {company_name}. Review individual categories for details."
        
        # Prepare content for summarization
        all_content = []
        for category, results in categories.items():
            for r in results[:3]:
                snippet = r.get("snippet", "") or r.get("content", "")[:200]
                if snippet:
                    all_content.append(f"[{category.upper()}] {snippet}")
        
        if not all_content:
            return f"Limited data found for {company_name}."
        
        prompt = f"""Summarize this research about {company_name} for interview preparation.

Research Data:
{chr(10).join(all_content[:10])}

Write a 2-3 sentence summary highlighting:
1. Interview process insights
2. Company culture highlights
3. Key things to know before interviewing

Be concise and actionable."""
        
        try:
            response = await llm.generate(prompt)
            return response.strip()[:500]
        except Exception:
            return f"Research data collected for {company_name}. See categories for details."
    
    async def _extract_insights(self, categories: Dict[str, List]) -> List[str]:
        """Extract key insights from research."""
        insights = []
        
        for category, results in categories.items():
            if results:
                # Add a basic insight per category
                if category == "interview":
                    insights.append("Technical interviews typically include coding and system design")
                elif category == "culture":
                    insights.append("Company culture information available from employee reviews")
                elif category == "salary":
                    insights.append("Salary data found - research compensation expectations")
                elif category == "tech_stack":
                    insights.append("Technology stack information available")
        
        return insights[:5]
    
    # ============ Mock Data for Demo ============
    
    def _get_mock_results(self, company: str, category: str) -> List[Dict]:
        """Return mock results when APIs unavailable."""
        mock_data = {
            "interview": [
                {
                    "title": f"{company} Interview Experience - LeetCode",
                    "url": f"https://leetcode.com/discuss/{company.lower()}-interview",
                    "snippet": f"Typical {company} interview includes 2 coding rounds, 1 system design, and behavioral. Focus on medium-hard LeetCode problems."
                },
                {
                    "title": f"{company} Software Engineer Interview Questions",
                    "url": f"https://glassdoor.com/{company.lower()}-interview",
                    "snippet": f"Common topics: data structures, algorithms, OOP concepts, and system design for senior roles."
                }
            ],
            "culture": [
                {
                    "title": f"{company} Employee Reviews - Glassdoor",
                    "url": f"https://glassdoor.com/{company.lower()}-reviews",
                    "snippet": f"Employees rate {company} highly for growth opportunities. Work-life balance varies by team."
                }
            ],
            "salary": [
                {
                    "title": f"{company} Salary - Levels.fyi",
                    "url": f"https://levels.fyi/company/{company.lower()}",
                    "snippet": f"Software Engineer at {company}: ₹15-35 LPA (India), $120-180K (US) based on experience."
                }
            ],
            "tech_stack": [
                {
                    "title": f"{company} Engineering Blog",
                    "url": f"https://engineering.{company.lower()}.com",
                    "snippet": f"{company} uses a modern stack including React, Python/Go for backend, and cloud-native infrastructure."
                }
            ],
            "news": [
                {
                    "title": f"{company} Hiring News",
                    "url": f"https://news.example.com/{company.lower()}-hiring",
                    "snippet": f"{company} continues to expand engineering teams. Active hiring for SDE roles."
                }
            ]
        }
        return mock_data.get(category, [])
    
    # ============ Cache Management ============
    
    def _get_cache_key(self, company: str, categories: List[str]) -> str:
        """Generate cache key."""
        data = f"{company.lower()}_{'_'.join(sorted(categories))}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def _get_from_cache(self, key: str) -> Optional[Dict]:
        """Get from cache if not expired."""
        if key in self._cache:
            cached = self._cache[key]
            cached_at = datetime.fromisoformat(cached.get("researched_at", "2000-01-01"))
            if datetime.utcnow() - cached_at < self._cache_ttl:
                return cached
        return None
    
    def _set_cache(self, key: str, data: Dict):
        """Set cache entry."""
        self._cache[key] = data
    
    def clear_cache(self):
        """Clear all cache."""
        self._cache.clear()
    
    # ============ Interview-Specific Research ============
    
    async def get_interview_questions(
        self,
        company: str,
        role: str = "Software Engineer"
    ) -> Dict[str, Any]:
        """Get common interview questions for a company/role."""
        results = await self.research_company(
            company, 
            categories=["interview"],
            max_results_per_category=10
        )
        
        # Extract questions from results
        questions = {
            "coding": [],
            "system_design": [],
            "behavioral": [],
            "technical": []
        }
        
        interview_data = results.get("categories", {}).get("interview", [])
        
        # Use LLM to extract questions if available
        llm = self._get_llm_service()
        if llm and interview_data:
            try:
                content = " ".join([r.get("content", r.get("snippet", ""))[:300] for r in interview_data[:5]])
                
                prompt = f"""Extract interview questions from this {company} interview data.

Data: {content[:2000]}

Return JSON with categories:
{{"coding": ["question1"], "system_design": ["question1"], "behavioral": ["question1"]}}

Only include actual questions found. Max 3 per category."""
                
                response = await llm.generate(prompt)
                try:
                    extracted = json.loads(response)
                    questions.update(extracted)
                except json.JSONDecodeError:
                    pass
            except Exception:
                pass
        
        # Add fallback questions if empty
        if not any(questions.values()):
            questions = self._get_fallback_questions(company, role)
        
        return {
            "company": company,
            "role": role,
            "questions": questions,
            "source_count": len(interview_data),
            "researched_at": datetime.utcnow().isoformat()
        }
    
    def _get_fallback_questions(self, company: str, role: str) -> Dict[str, List[str]]:
        """Fallback questions based on company type."""
        return {
            "coding": [
                "Implement a LRU Cache",
                "Design a rate limiter",
                "Find the median of two sorted arrays"
            ],
            "system_design": [
                f"Design {company}'s core product",
                "Design a URL shortener with analytics",
                "Design a real-time notification system"
            ],
            "behavioral": [
                "Tell me about a challenging project",
                "How do you handle disagreements with teammates?",
                "Describe a time you failed and what you learned"
            ],
            "technical": [
                "Explain your most complex project",
                "What's your experience with distributed systems?",
                "How do you approach debugging production issues?"
            ]
        }
    
    # ============ Company Trends ============
    
    async def get_company_trends(self, company: str) -> Dict[str, Any]:
        """Get latest trends and news about company."""
        results = await self.research_company(
            company,
            categories=["news", "tech_stack"],
            max_results_per_category=5
        )
        
        return {
            "company": company,
            "latest_news": results.get("categories", {}).get("news", []),
            "tech_trends": results.get("categories", {}).get("tech_stack", []),
            "summary": results.get("summary", ""),
            "updated_at": datetime.utcnow().isoformat()
        }


# Singleton instance
research_tool = DeepResearchTool()
