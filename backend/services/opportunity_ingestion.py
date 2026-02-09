"""
Opportunity Ingestion Service
Pulls external opportunities from multiple sources for the recommendation engine.
Sources: Internshala (Apify), Devpost (hackathons), Google News RSS (content)
"""

import os
import asyncio
import hashlib
import logging
import feedparser
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import xml.etree.ElementTree as ET
import re

logger = logging.getLogger(__name__)

from ..database import get_database


# ============ Data Schemas ============

@dataclass
class JobOpportunity:
    """Normalized job/internship opportunity."""
    source: str
    source_id: str
    source_url: str
    title: str
    company: str
    location: str
    work_mode: str  # remote, onsite, hybrid
    stipend: Optional[str]
    skills_required: List[str]
    description_snippet: str
    posted_at: Optional[datetime]
    apply_by: Optional[datetime]
    is_active: bool = True


@dataclass
class HackathonOpportunity:
    """Normalized hackathon opportunity."""
    source: str
    source_id: str
    event_url: str
    event_name: str
    organizer: str
    theme_tags: List[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    status: str  # open, closed, upcoming
    eligibility: str  # students, all, professionals
    prize_info: Optional[str]


@dataclass
class ContentOpportunity:
    """Normalized content/news item."""
    source: str
    title: str
    url: str
    publisher: str
    published_at: Optional[datetime]
    topic: str
    query_used: str


# ============ Collections ============

def opportunities_jobs_collection():
    return get_database()["opportunities_jobs"]


def opportunities_hackathons_collection():
    return get_database()["opportunities_hackathons"]


def opportunities_content_collection():
    return get_database()["opportunities_content"]


def ingestion_log_collection():
    return get_database()["ingestion_logs"]


# ============ Internshala/Jobs Ingestion ============

class JobsIngestionService:
    """
    Ingests job/internship listings from external sources.
    Primary: Apify Internshala Actor
    Fallback: Mock data for demo
    """
    
    def __init__(self):
        self.apify_key = os.getenv("APIFY_API_KEY")
        self.apify_actor_id = "salman_bareesh/internshala-scrapper"  # User provided actor
        # Initialize client if key is present
        self.client = None
        if self.apify_key:
            from apify_client import ApifyClient
            self.client = ApifyClient(self.apify_key)
    
    async def ingest_from_apify(self, filters: Dict = None) -> List[Dict]:
        """
        Call Apify actor to get Internshala listings.
        Returns raw data from Apify using ApifyClient.
        """
        if not self.client:
            logger.warning("Apify Client not initialized. Missing API Key.")
            return []
        
        # User requested specific input format in their snippet, but for this actor
        # we typically just need startUrls or specific search queries.
        # The user's snippet was for google-places, so we adapt for internshala.
        # The actor "salman_bareesh/internshala-scrapper" usually takes startUrls.
        
        run_input = {
            "startUrls": [
                {"url": "https://internshala.com/internships/"}
            ],
            "maxItems": 50
        }
        if filters:
            run_input.update(filters)
            
        try:
            # Run the actor and wait for it to finish
            logger.info(f"Starting Apify Actor: {self.apify_actor_id}")
            
            # Run synchronously in a thread pool since ApifyClient is synchronous (or use async client if available? 
            # actually ApifyClient is sync, ApifyClientAsync is async. Let's use run_in_executor for safety or just sync if fast sufficient.
            # But wait, python's apify-client has an AsyncApifyClient? 
            # The user snippet used `ApifyClient` (sync). We should use `ApifyClientAsync` if we are in async context, 
            # OR wrap the sync client in a thread. 
            # To match user snippet simplicity, we'll assume sync is fine if we wrap it or if it's quick, 
            # but web scraping takes time. Let's use ApifyClientAsync for best practice in this async service.
            
            from apify_client import ApifyClientAsync
            async_client = ApifyClientAsync(self.apify_key)
            
            run = await async_client.actor(self.apify_actor_id).call(run_input=run_input)
            
            logger.info(f"Apify run completed: {run.get('id')}")
            
            # Fetch results from the dataset
            dataset_items = await async_client.dataset(run["defaultDatasetId"]).list_items()
            return dataset_items.items
            
        except Exception as e:
            logger.error(f"Apify ingestion failed: {e}", exc_info=True)
        
        return []
    
    def get_mock_jobs(self) -> List[Dict]:
        """Demo job listings for testing."""
        return [
            {
                "source": "mock_internshala",
                "source_id": "mock_001",
                "source_url": "https://internshala.com/internship/detail/software-development-internship-1",
                "title": "Software Development Intern",
                "company": "TechStartup Inc.",
                "location": "Bangalore",
                "work_mode": "remote",
                "stipend": "₹15,000/month",
                "skills_required": ["python", "django", "postgresql"],
                "description_snippet": "Looking for passionate developers to join our team...",
                "posted_at": datetime.utcnow() - timedelta(days=2),
                "apply_by": datetime.utcnow() + timedelta(days=14),
                "is_active": True
            },
            {
                "source": "mock_internshala",
                "source_id": "mock_002",
                "source_url": "https://internshala.com/internship/detail/data-science-internship-2",
                "title": "Data Science Intern",
                "company": "Analytics Corp",
                "location": "Mumbai",
                "work_mode": "hybrid",
                "stipend": "₹20,000/month",
                "skills_required": ["python", "machine learning", "pandas", "sql"],
                "description_snippet": "Join our data science team and work on real ML projects...",
                "posted_at": datetime.utcnow() - timedelta(days=1),
                "apply_by": datetime.utcnow() + timedelta(days=10),
                "is_active": True
            },
            {
                "source": "mock_internshala",
                "source_id": "mock_003",
                "source_url": "https://internshala.com/internship/detail/frontend-dev-3",
                "title": "Frontend Developer Intern",
                "company": "WebDesign Studios",
                "location": "Delhi",
                "work_mode": "onsite",
                "stipend": "₹12,000/month",
                "skills_required": ["react", "javascript", "css", "html"],
                "description_snippet": "Build beautiful user interfaces with React...",
                "posted_at": datetime.utcnow() - timedelta(days=3),
                "apply_by": datetime.utcnow() + timedelta(days=7),
                "is_active": True
            },
            {
                "source": "mock_internshala",
                "source_id": "mock_004",
                "source_url": "https://internshala.com/internship/detail/backend-dev-4",
                "title": "Backend Developer Intern",
                "company": "CloudServices Ltd",
                "location": "Pune",
                "work_mode": "remote",
                "stipend": "₹18,000/month",
                "skills_required": ["nodejs", "mongodb", "express", "aws"],
                "description_snippet": "Build scalable backend services for our cloud platform...",
                "posted_at": datetime.utcnow() - timedelta(days=1),
                "apply_by": datetime.utcnow() + timedelta(days=20),
                "is_active": True
            },
            {
                "source": "mock_internshala",
                "source_id": "mock_005",
                "source_url": "https://internshala.com/internship/detail/devops-5",
                "title": "DevOps Engineering Intern",
                "company": "InfraTech Solutions",
                "location": "Hyderabad",
                "work_mode": "hybrid",
                "stipend": "₹22,000/month",
                "skills_required": ["docker", "kubernetes", "jenkins", "linux"],
                "description_snippet": "Help us build and maintain our CI/CD pipelines...",
                "posted_at": datetime.utcnow(),
                "apply_by": datetime.utcnow() + timedelta(days=15),
                "is_active": True
            },
            {
                "source": "mock_internshala",
                "source_id": "mock_006",
                "source_url": "https://internshala.com/internship/detail/mobile-dev-6",
                "title": "Mobile App Developer Intern",
                "company": "AppMakers",
                "location": "Chennai",
                "work_mode": "remote",
                "stipend": "₹16,000/month",
                "skills_required": ["react native", "javascript", "mobile development"],
                "description_snippet": "Build cross-platform mobile apps using React Native...",
                "posted_at": datetime.utcnow() - timedelta(days=4),
                "apply_by": datetime.utcnow() + timedelta(days=12),
                "is_active": True
            }
        ]
    
    async def ingest_jobs(self, use_mock: bool = True) -> Dict[str, Any]:
        """
        Main ingestion method. Fetches jobs and stores in MongoDB.
        """
        collection = opportunities_jobs_collection()
        
        # Get jobs (Apify or mock)
        if use_mock or not self.apify_key:
            jobs = self.get_mock_jobs()
        else:
            raw_jobs = await self.ingest_from_apify()
            jobs = self._normalize_apify_jobs(raw_jobs)
        
        # Upsert jobs
        inserted = 0
        updated = 0
        
        for job in jobs:
            source_id = job.get("source_id") or hashlib.md5(
                f"{job['source']}_{job['title']}_{job['company']}".encode()
            ).hexdigest()[:12]
            
            job["source_id"] = source_id
            job["scraped_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"source": job["source"], "source_id": source_id},
                {"$set": job},
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1
        
        # Log ingestion
        await self._log_ingestion("jobs", len(jobs), inserted, updated)
        
        # [NEW] Fire RAG Vectorization Events for NEW jobs
        # We only want to vectorize new or updated jobs to save resources
        if inserted > 0 or updated > 0:
            try:
                from ..events.event_bus import event_bus, Events
                logger.info(f"Publishing RAG events for {len(jobs)} scraped jobs...")
                for job in jobs:
                    # optimization: only publish if we think it's new/updated or just fire all (idempotent)
                    # For now, fire all to ensure consistency
                    await event_bus.publish(Events.JOB_POSTED, {
                        "id": job["source_id"], # logic might need mapping to internal DB _id if we used upsert
                        "title": job.get("title", ""),
                        "description": job.get("description", "") or job.get("description_snippet", ""),
                        "company_name": job.get("company", ""),
                        "location": job.get("location", "")
                    })
            except Exception as e:
                logger.error(f"Failed to publish RAG events for scraped jobs: {e}")

        return {
            "source": "internshala",
            "total_fetched": len(jobs),
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _normalize_apify_jobs(self, raw_jobs: List[Dict]) -> List[Dict]:
        """Normalize Apify output to our schema."""
        normalized = []
        for job in raw_jobs:
            normalized.append({
                "source": "internshala_apify",
                "source_id": job.get("id", ""),
                "source_url": job.get("url", ""),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "location": job.get("location", ""),
                "work_mode": self._detect_work_mode(job.get("location", "")),
                "stipend": job.get("stipend", ""),
                "skills_required": job.get("skills", []),
                "description_snippet": (job.get("description", "")[:200] + "...") if job.get("description") else "",
                "posted_at": self._parse_date(job.get("posted")),
                "apply_by": self._parse_date(job.get("deadline")),
                "is_active": True
            })
        return normalized
    
    def _detect_work_mode(self, location: str) -> str:
        """Detect work mode from location string."""
        location_lower = location.lower()
        if "remote" in location_lower or "wfh" in location_lower:
            return "remote"
        elif "hybrid" in location_lower:
            return "hybrid"
        return "onsite"
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    async def _log_ingestion(self, source_type: str, total: int, inserted: int, updated: int):
        """Log ingestion run."""
        await ingestion_log_collection().insert_one({
            "source_type": source_type,
            "total_fetched": total,
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow()
        })


# ============ Hackathons Ingestion ============

class HackathonsIngestionService:
    """
    Ingests hackathon listings from external sources.
    Primary: Devpost RSS/web
    Fallback: Mock data for demo
    """
    
    DEVPOST_RSS_URL = "https://devpost.com/hackathons.rss"
    
    async def ingest_from_devpost(self) -> List[Dict]:
        """Fetch hackathons from Devpost RSS."""
        hackathons = []
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.DEVPOST_RSS_URL) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        hackathons = self._parse_devpost_rss(content)
        except aiohttp.ClientError as e:
            logger.error(f"Devpost network error: {e}")
        except Exception as e:
            logger.error(f"Devpost ingestion unexpected error: {e}")
        
        return hackathons
    
    def _parse_devpost_rss(self, xml_content: str) -> List[Dict]:
        """Parse Devpost RSS feed."""
        hackathons = []
        
        try:
            feed = feedparser.parse(xml_content)
            
            for entry in feed.entries[:30]:  # Limit to 30
                hackathon = {
                    "source": "devpost",
                    "source_id": hashlib.md5(entry.get("link", "").encode()).hexdigest()[:12],
                    "event_url": entry.get("link", ""),
                    "event_name": entry.get("title", ""),
                    "organizer": self._extract_organizer(entry),
                    "theme_tags": self._extract_tags(entry),
                    "start_date": self._parse_entry_date(entry.get("published")),
                    "end_date": None,  # RSS doesn't always have this
                    "status": "open",
                    "eligibility": "all",
                    "prize_info": self._extract_prize(entry)
                }
                hackathons.append(hackathon)
        except Exception as e:
            logger.error(f"RSS parsing error: {e}")
        
        return hackathons
    
    def _extract_organizer(self, entry) -> str:
        """Extract organizer from entry."""
        return entry.get("author", "Unknown Organizer")
    
    def _extract_tags(self, entry) -> List[str]:
        """Extract theme tags from entry."""
        tags = []
        if hasattr(entry, 'tags'):
            tags = [t.get('term', '') for t in entry.tags if t.get('term')]
        
        # Also extract from title/summary
        title = entry.get("title", "").lower()
        summary = entry.get("summary", "").lower()
        combined = f"{title} {summary}"
        
        common_tags = ["ai", "ml", "blockchain", "web3", "healthcare", "fintech", 
                       "sustainability", "education", "gaming", "iot", "cloud"]
        for tag in common_tags:
            if tag in combined:
                tags.append(tag.upper())
        
        return list(set(tags))[:5]  # Max 5 tags
    
    def _extract_prize(self, entry) -> Optional[str]:
        """Extract prize info if available."""
        summary = entry.get("summary", "")
        # Look for prize patterns like "$10,000" or "₹50,000"
        prize_match = re.search(r'[\$₹€]\s?\d{1,3}(?:,\d{3})*(?:\.\d{2})?', summary)
        return prize_match.group() if prize_match else None
    
    def _parse_entry_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date string."""
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
    
    def get_mock_hackathons(self) -> List[Dict]:
        """Demo hackathon listings."""
        return [
            {
                "source": "mock_devpost",
                "source_id": "hack_001",
                "event_url": "https://devpost.com/hackathons/ai-summit-2026",
                "event_name": "AI Innovation Summit 2026",
                "organizer": "Google Developer Groups",
                "theme_tags": ["AI", "ML", "Healthcare"],
                "start_date": datetime.utcnow() + timedelta(days=30),
                "end_date": datetime.utcnow() + timedelta(days=32),
                "status": "open",
                "eligibility": "students",
                "prize_info": "$50,000"
            },
            {
                "source": "mock_devpost",
                "source_id": "hack_002",
                "event_url": "https://devpost.com/hackathons/web3-build",
                "event_name": "Web3 Build Challenge",
                "organizer": "Ethereum Foundation",
                "theme_tags": ["Web3", "Blockchain", "DeFi"],
                "start_date": datetime.utcnow() + timedelta(days=15),
                "end_date": datetime.utcnow() + timedelta(days=17),
                "status": "open",
                "eligibility": "all",
                "prize_info": "$25,000"
            },
            {
                "source": "mock_devpost",
                "source_id": "hack_003",
                "event_url": "https://devpost.com/hackathons/climate-hack",
                "event_name": "Climate Tech Hackathon",
                "organizer": "UN Climate Initiative",
                "theme_tags": ["Sustainability", "CleanTech", "IoT"],
                "start_date": datetime.utcnow() + timedelta(days=45),
                "end_date": datetime.utcnow() + timedelta(days=47),
                "status": "upcoming",
                "eligibility": "students",
                "prize_info": "$30,000"
            },
            {
                "source": "mock_devpost",
                "source_id": "hack_004",
                "event_url": "https://devpost.com/hackathons/fintech-2026",
                "event_name": "FinTech Innovation Challenge",
                "organizer": "Goldman Sachs",
                "theme_tags": ["FinTech", "AI", "Banking"],
                "start_date": datetime.utcnow() + timedelta(days=20),
                "end_date": datetime.utcnow() + timedelta(days=22),
                "status": "open",
                "eligibility": "students",
                "prize_info": "$40,000"
            },
            {
                "source": "mock_devpost",
                "source_id": "hack_005",
                "event_url": "https://devpost.com/hackathons/gaming-jam",
                "event_name": "Global Game Jam 2026",
                "organizer": "Game Developers Association",
                "theme_tags": ["Gaming", "Unity", "VR"],
                "start_date": datetime.utcnow() + timedelta(days=60),
                "end_date": datetime.utcnow() + timedelta(days=61),
                "status": "upcoming",
                "eligibility": "all",
                "prize_info": "$15,000"
            }
        ]
    
    async def ingest_hackathons(self, use_mock: bool = True) -> Dict[str, Any]:
        """Main ingestion method for hackathons."""
        collection = opportunities_hackathons_collection()
        
        # Get hackathons
        if use_mock:
            hackathons = self.get_mock_hackathons()
        else:
            hackathons = await self.ingest_from_devpost()
            if not hackathons:  # Fallback to mock
                hackathons = self.get_mock_hackathons()
        
        inserted = 0
        updated = 0
        
        for hackathon in hackathons:
            hackathon["scraped_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"source": hackathon["source"], "source_id": hackathon["source_id"]},
                {"$set": hackathon},
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1
        
        await self._log_ingestion("hackathons", len(hackathons), inserted, updated)
        
        return {
            "source": "devpost",
            "total_fetched": len(hackathons),
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _log_ingestion(self, source_type: str, total: int, inserted: int, updated: int):
        await ingestion_log_collection().insert_one({
            "source_type": source_type,
            "total_fetched": total,
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow()
        })


# ============ Content/News Ingestion ============

class ContentIngestionService:
    """
    Ingests trending tech content from news sources.
    Primary: Google News RSS
    Fallback: Mock data for demo
    """
    
    # Google News RSS base URL
    NEWS_RSS_BASE = "https://news.google.com/rss/search"
    
    # Topics to track (relevant to tech careers)
    TOPICS = [
        {"query": "tech hiring trends 2026", "topic": "Hiring"},
        {"query": "software developer jobs", "topic": "Jobs"},
        {"query": "AI machine learning career", "topic": "AI/ML"},
        {"query": "data science hiring", "topic": "Data Science"},
        {"query": "web development trends", "topic": "Web Dev"},
        {"query": "startup funding tech", "topic": "Startups"},
        {"query": "tech layoffs 2026", "topic": "Industry"},
        {"query": "programming skills demand", "topic": "Skills"}
    ]
    
    async def ingest_from_google_news(self, query: str, topic: str) -> List[Dict]:
        """Fetch news from Google News RSS for a query."""
        articles = []
        
        url = f"{self.NEWS_RSS_BASE}?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        articles = self._parse_news_rss(content, query, topic)
        except aiohttp.ClientError as e:
            logger.error(f"Google News network error: {e}")
        except Exception as e:
            logger.error(f"Google News ingestion unexpected error: {e}")
        
        return articles
    
    def _parse_news_rss(self, xml_content: str, query: str, topic: str) -> List[Dict]:
        """Parse Google News RSS feed."""
        articles = []
        
        try:
            feed = feedparser.parse(xml_content)
            
            for entry in feed.entries[:10]:  # Limit per topic
                article = {
                    "source": "google_news_rss",
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "publisher": self._extract_publisher(entry),
                    "published_at": self._parse_entry_date(entry.get("published")),
                    "topic": topic,
                    "query_used": query
                }
                articles.append(article)
        except Exception as e:
            logger.error(f"News RSS parsing error: {e}")
        
        return articles
    
    def _extract_publisher(self, entry) -> str:
        """Extract publisher from entry."""
        source = entry.get("source", {})
        if isinstance(source, dict):
            return source.get("title", "Unknown")
        return str(source) if source else "Unknown"
    
    def _parse_entry_date(self, date_str: str) -> Optional[datetime]:
        """Parse RSS date string."""
        if not date_str:
            return None
        try:
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception:
            return None
    
    def get_mock_content(self) -> List[Dict]:
        """Demo content articles."""
        return [
            {
                "source": "mock_news",
                "title": "Top 10 Programming Skills in Demand for 2026",
                "url": "https://techblog.com/programming-skills-2026",
                "publisher": "TechBlog",
                "published_at": datetime.utcnow() - timedelta(hours=2),
                "topic": "Skills",
                "query_used": "programming skills demand"
            },
            {
                "source": "mock_news",
                "title": "AI/ML Engineer Salaries Continue to Rise",
                "url": "https://careernews.com/ai-ml-salaries-2026",
                "publisher": "CareerNews",
                "published_at": datetime.utcnow() - timedelta(hours=5),
                "topic": "AI/ML",
                "query_used": "AI machine learning career"
            },
            {
                "source": "mock_news",
                "title": "Tech Giants Announce Major Hiring Plans for Q2",
                "url": "https://businesstoday.com/tech-hiring-q2-2026",
                "publisher": "Business Today",
                "published_at": datetime.utcnow() - timedelta(hours=8),
                "topic": "Hiring",
                "query_used": "tech hiring trends 2026"
            },
            {
                "source": "mock_news",
                "title": "Remote Work: The New Normal for Developers",
                "url": "https://devnews.com/remote-work-developers",
                "publisher": "DevNews",
                "published_at": datetime.utcnow() - timedelta(hours=12),
                "topic": "Industry",
                "query_used": "software developer jobs"
            },
            {
                "source": "mock_news",
                "title": "Data Science Bootcamps See Record Enrollments",
                "url": "https://edutech.com/data-science-bootcamps",
                "publisher": "EduTech",
                "published_at": datetime.utcnow() - timedelta(hours=15),
                "topic": "Data Science",
                "query_used": "data science hiring"
            },
            {
                "source": "mock_news",
                "title": "Startup Funding Hits New High in Tech Sector",
                "url": "https://startupnews.com/funding-2026",
                "publisher": "StartupNews",
                "published_at": datetime.utcnow() - timedelta(hours=20),
                "topic": "Startups",
                "query_used": "startup funding tech"
            },
            {
                "source": "mock_news",
                "title": "React vs Vue: Which Framework to Learn in 2026?",
                "url": "https://webdevweekly.com/react-vs-vue",
                "publisher": "WebDev Weekly",
                "published_at": datetime.utcnow() - timedelta(hours=24),
                "topic": "Web Dev",
                "query_used": "web development trends"
            },
            {
                "source": "mock_news",
                "title": "Cloud Computing Certifications Worth Getting",
                "url": "https://cloudacademy.com/certifications-2026",
                "publisher": "Cloud Academy",
                "published_at": datetime.utcnow() - timedelta(hours=30),
                "topic": "Skills",
                "query_used": "programming skills demand"
            }
        ]
    
    async def ingest_content(self, use_mock: bool = True) -> Dict[str, Any]:
        """Main ingestion method for content."""
        collection = opportunities_content_collection()
        
        all_articles = []
        
        if use_mock:
            all_articles = self.get_mock_content()
        else:
            # Fetch from each topic
            for topic_config in self.TOPICS:
                articles = await self.ingest_from_google_news(
                    topic_config["query"],
                    topic_config["topic"]
                )
                all_articles.extend(articles)
                await asyncio.sleep(1)  # Rate limiting
            
            if not all_articles:  # Fallback
                all_articles = self.get_mock_content()
        
        inserted = 0
        updated = 0
        
        for article in all_articles:
            # Generate unique ID from URL
            source_id = hashlib.md5(article["url"].encode()).hexdigest()[:12]
            article["source_id"] = source_id
            article["scraped_at"] = datetime.utcnow()
            
            result = await collection.update_one(
                {"source_id": source_id},
                {"$set": article},
                upsert=True
            )
            
            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1
        
        await self._log_ingestion("content", len(all_articles), inserted, updated)
        
        return {
            "source": "google_news_rss",
            "topics_fetched": len(self.TOPICS),
            "total_articles": len(all_articles),
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _log_ingestion(self, source_type: str, total: int, inserted: int, updated: int):
        await ingestion_log_collection().insert_one({
            "source_type": source_type,
            "total_fetched": total,
            "inserted": inserted,
            "updated": updated,
            "timestamp": datetime.utcnow()
        })


# ============ Main Ingestion Orchestrator ============

class OpportunityIngestionService:
    """
    Orchestrates all opportunity ingestion services.
    """
    
    def __init__(self):
        self.jobs_service = JobsIngestionService()
        self.hackathons_service = HackathonsIngestionService()
        self.content_service = ContentIngestionService()
    
    async def ingest_all(self, use_mock: bool = True) -> Dict[str, Any]:
        """Run all ingestion services."""
        results = {}
        
        # Jobs
        results["jobs"] = await self.jobs_service.ingest_jobs(use_mock)
        
        # Hackathons
        results["hackathons"] = await self.hackathons_service.ingest_hackathons(use_mock)
        
        # Content
        results["content"] = await self.content_service.ingest_content(use_mock)
        
        return {
            "status": "completed",
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_jobs(
        self,
        skills: List[str] = None,
        location: str = None,
        work_mode: str = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict]:
        """Get job opportunities with filters."""
        collection = opportunities_jobs_collection()
        
        query = {"is_active": True}
        
        if skills:
            # Match any of the skills
            query["skills_required"] = {"$in": [s.lower() for s in skills]}
        
        if location:
            query["location"] = {"$regex": location, "$options": "i"}
        
        if work_mode:
            query["work_mode"] = work_mode
        
        cursor = collection.find(query).sort("scraped_at", -1).skip(skip).limit(limit)
        jobs = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for job in jobs:
            job["_id"] = str(job["_id"])
        
        return jobs
    
    async def get_hackathons(
        self,
        theme_tags: List[str] = None,
        status: str = None,
        eligibility: str = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict]:
        """Get hackathon opportunities with filters."""
        collection = opportunities_hackathons_collection()
        
        query = {}
        
        if theme_tags:
            query["theme_tags"] = {"$in": [t.upper() for t in theme_tags]}
        
        if status:
            query["status"] = status
        
        if eligibility:
            query["eligibility"] = eligibility
        
        cursor = collection.find(query).sort("scraped_at", -1).skip(skip).limit(limit)
        hackathons = await cursor.to_list(length=limit)
        
        for h in hackathons:
            h["_id"] = str(h["_id"])
        
        return hackathons
    
    async def get_content(
        self,
        topic: str = None,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict]:
        """Get content articles with filters."""
        collection = opportunities_content_collection()
        
        query = {}
        if topic:
            query["topic"] = topic
        
        cursor = collection.find(query).sort("published_at", -1).skip(skip).limit(limit)
        articles = await cursor.to_list(length=limit)
        
        for a in articles:
            a["_id"] = str(a["_id"])
        
        return articles
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics."""
        jobs_count = await opportunities_jobs_collection().count_documents({})
        hackathons_count = await opportunities_hackathons_collection().count_documents({})
        content_count = await opportunities_content_collection().count_documents({})
        
        # Get last ingestion times
        logs = ingestion_log_collection()
        last_jobs = await logs.find_one(
            {"source_type": "jobs"},
            sort=[("timestamp", -1)]
        )
        last_hackathons = await logs.find_one(
            {"source_type": "hackathons"},
            sort=[("timestamp", -1)]
        )
        last_content = await logs.find_one(
            {"source_type": "content"},
            sort=[("timestamp", -1)]
        )
        
        return {
            "totals": {
                "jobs": jobs_count,
                "hackathons": hackathons_count,
                "content": content_count
            },
            "last_ingestion": {
                "jobs": last_jobs["timestamp"].isoformat() if last_jobs else None,
                "hackathons": last_hackathons["timestamp"].isoformat() if last_hackathons else None,
                "content": last_content["timestamp"].isoformat() if last_content else None
            }
        }


# Singleton instance
opportunity_ingestion = OpportunityIngestionService()
