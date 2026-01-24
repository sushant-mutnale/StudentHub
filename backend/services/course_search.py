"""
Course Search Service
Dynamic course/tutorial search using multiple providers:
- YouTube Data API (official)
- Udemy (via scraper APIs)
- Coursera (via scraper APIs)  
- EdX (via scraper APIs)

Falls back to local resources if APIs unavailable.
"""

import os
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class CourseSearchProvider:
    """Base class for course search providers."""
    
    def __init__(self):
        self.name = "base"
        self.enabled = False
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search for courses matching query. Override in subclasses."""
        raise NotImplementedError


class YouTubeProvider(CourseSearchProvider):
    """
    YouTube Data API v3 for video tutorials/courses.
    Get API key from: https://console.cloud.google.com/
    """
    
    def __init__(self):
        super().__init__()
        self.name = "youtube"
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.enabled = bool(self.api_key)
        self.base_url = "https://www.googleapis.com/youtube/v3/search"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        try:
            params = {
                "part": "snippet",
                "q": f"{query} course tutorial programming",
                "key": self.api_key,
                "maxResults": max_results,
                "type": "video",
                "videoDuration": "long",  # Prefer longer educational content
                "relevanceLanguage": "en",
                "safeSearch": "strict"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=10) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
            
            results = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                video_id = item.get("id", {}).get("videoId", "")
                
                results.append({
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", "")[:200],
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "source": "YouTube",
                    "type": "video",
                    "channel": snippet.get("channelTitle", ""),
                    "thumbnail": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "provider": self.name
                })
            
            return results
            
        except asyncio.TimeoutError:
            print(f"[{self.name}] Timeout during search")
            return []
        except Exception as e:
            print(f"[{self.name}] Error: {str(e)}")
            return []


class UdemyScraperProvider(CourseSearchProvider):
    """
    Udemy course search via Apify scraper API.
    Get token from: https://apify.com/
    """
    
    def __init__(self):
        super().__init__()
        self.name = "udemy"
        self.api_token = os.getenv("APIFY_TOKEN")
        self.enabled = bool(self.api_token)
        # Using a public Udemy scraper actor
        self.base_url = "https://api.apify.com/v2/acts/easyapi~udemy-course-scraper/runs"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        try:
            # Apify actors run async, so we use their sync endpoint with timeout
            run_input = {
                "searchQuery": query,
                "maxItems": max_results
            }
            
            headers = {"Content-Type": "application/json"}
            params = {"token": self.api_token, "waitForFinish": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=run_input,
                    headers=headers,
                    params=params,
                    timeout=35
                ) as resp:
                    if resp.status != 201:
                        return []
                    run_data = await resp.json()
                
                # Get results from dataset
                dataset_id = run_data.get("data", {}).get("defaultDatasetId")
                if not dataset_id:
                    return []
                
                dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                async with session.get(dataset_url, params={"token": self.api_token}) as resp:
                    if resp.status != 200:
                        return []
                    items = await resp.json()
            
            results = []
            for item in items[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("headline", "")[:200],
                    "url": item.get("url", ""),
                    "source": "Udemy",
                    "type": "course",
                    "instructor": item.get("instructorName", ""),
                    "rating": item.get("rating", 0),
                    "price": item.get("price", ""),
                    "provider": self.name
                })
            
            return results
            
        except asyncio.TimeoutError:
            print(f"[{self.name}] Timeout during search")
            return []
        except Exception as e:
            print(f"[{self.name}] Error: {str(e)}")
            return []


class CourseraScraperProvider(CourseSearchProvider):
    """
    Coursera course search via Apify scraper.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "coursera"
        self.api_token = os.getenv("APIFY_TOKEN")
        self.enabled = bool(self.api_token)
        self.base_url = "https://api.apify.com/v2/acts/epctex~coursera-scraper/runs"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        try:
            run_input = {
                "searchTerms": [query],
                "maxItems": max_results
            }
            
            headers = {"Content-Type": "application/json"}
            params = {"token": self.api_token, "waitForFinish": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=run_input,
                    headers=headers,
                    params=params,
                    timeout=35
                ) as resp:
                    if resp.status != 201:
                        return []
                    run_data = await resp.json()
                
                dataset_id = run_data.get("data", {}).get("defaultDatasetId")
                if not dataset_id:
                    return []
                
                dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                async with session.get(dataset_url, params={"token": self.api_token}) as resp:
                    if resp.status != 200:
                        return []
                    items = await resp.json()
            
            results = []
            for item in items[:max_results]:
                results.append({
                    "title": item.get("name", item.get("title", "")),
                    "description": item.get("description", "")[:200],
                    "url": item.get("url", ""),
                    "source": "Coursera",
                    "type": "course",
                    "partner": item.get("partnerName", ""),
                    "rating": item.get("rating", 0),
                    "duration": item.get("duration", ""),
                    "provider": self.name
                })
            
            return results
            
        except asyncio.TimeoutError:
            print(f"[{self.name}] Timeout during search")
            return []
        except Exception as e:
            print(f"[{self.name}] Error: {str(e)}")
            return []


class EdXScraperProvider(CourseSearchProvider):
    """
    EdX course search via Apify scraper.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "edx"
        self.api_token = os.getenv("APIFY_TOKEN")
        self.enabled = bool(self.api_token)
        self.base_url = "https://api.apify.com/v2/acts/epctex~edx-scraper/runs"
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        
        try:
            run_input = {
                "searchTerms": [query],
                "maxItems": max_results
            }
            
            headers = {"Content-Type": "application/json"}
            params = {"token": self.api_token, "waitForFinish": 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.base_url,
                    json=run_input,
                    headers=headers,
                    params=params,
                    timeout=35
                ) as resp:
                    if resp.status != 201:
                        return []
                    run_data = await resp.json()
                
                dataset_id = run_data.get("data", {}).get("defaultDatasetId")
                if not dataset_id:
                    return []
                
                dataset_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items"
                async with session.get(dataset_url, params={"token": self.api_token}) as resp:
                    if resp.status != 200:
                        return []
                    items = await resp.json()
            
            results = []
            for item in items[:max_results]:
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", "")[:200],
                    "url": item.get("url", ""),
                    "source": "EdX",
                    "type": "course",
                    "institution": item.get("school", ""),
                    "level": item.get("level", ""),
                    "provider": self.name
                })
            
            return results
            
        except asyncio.TimeoutError:
            print(f"[{self.name}] Timeout during search")
            return []
        except Exception as e:
            print(f"[{self.name}] Error: {str(e)}")
            return []


class LocalResourceProvider(CourseSearchProvider):
    """
    Fallback provider using local learning_resources.json.
    Always available, no API needed.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "local"
        self.enabled = True
        self.resources_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "learning_resources.json"
        )
        self._cache = None
    
    def _load_resources(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache
        
        try:
            with open(self.resources_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
        except FileNotFoundError:
            self._cache = {}
        
        return self._cache
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        resources = self._load_resources()
        query_lower = query.lower().replace("-", "_").replace(" ", "_")
        
        results = []
        
        # Direct skill match
        if query_lower in resources:
            skill_data = resources[query_lower]
            for level in ["beginner", "intermediate", "advanced"]:
                for res in skill_data.get(level, [])[:2]:
                    results.append({
                        "title": res.get("title", ""),
                        "description": f"{level.title()} level resource for {query}",
                        "url": res.get("url", ""),
                        "source": res.get("source", "Local Library"),
                        "type": res.get("type", "article"),
                        "level": level,
                        "provider": self.name
                    })
                    if len(results) >= max_results:
                        break
                if len(results) >= max_results:
                    break
        
        # Fuzzy match if no direct match
        if not results:
            for skill_name, skill_data in resources.items():
                if query_lower in skill_name or skill_name in query_lower:
                    for level in ["beginner", "intermediate"]:
                        for res in skill_data.get(level, [])[:1]:
                            results.append({
                                "title": res.get("title", ""),
                                "description": f"{level.title()} level resource",
                                "url": res.get("url", ""),
                                "source": res.get("source", "Local Library"),
                                "type": res.get("type", "article"),
                                "level": level,
                                "provider": self.name
                            })
                            if len(results) >= max_results:
                                break
                if len(results) >= max_results:
                    break
        
        return results[:max_results]


class CourseSearchService:
    """
    Aggregated course search across multiple providers.
    Implements proper fallback chain.
    """
    
    def __init__(self):
        # Initialize providers in priority order
        self.providers: List[CourseSearchProvider] = [
            YouTubeProvider(),
            UdemyScraperProvider(),
            CourseraScraperProvider(),
            EdXScraperProvider(),
            LocalResourceProvider(),  # Always last as fallback
        ]
        
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
    
    def get_enabled_providers(self) -> List[str]:
        """Return list of enabled provider names."""
        return [p.name for p in self.providers if p.enabled]
    
    async def search_all(
        self,
        query: str,
        max_per_provider: int = 3,
        providers: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search across all enabled providers concurrently.
        
        Args:
            query: Search query (skill name)
            max_per_provider: Max results per provider
            providers: Optional list of specific providers to use
            
        Returns:
            Dict with results by provider and aggregated list
        """
        active_providers = [
            p for p in self.providers 
            if p.enabled and (providers is None or p.name in providers)
        ]
        
        if not active_providers:
            # No providers available, use local fallback
            local = LocalResourceProvider()
            results = await local.search(query, max_per_provider * 3)
            return {
                "query": query,
                "providers_used": ["local"],
                "total_results": len(results),
                "results_by_provider": {"local": results},
                "all_results": results,
                "searched_at": datetime.utcnow().isoformat()
            }
        
        # Run all searches concurrently
        tasks = [p.search(query, max_per_provider) for p in active_providers]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        results_by_provider = {}
        all_results = []
        providers_used = []
        
        for provider, results in zip(active_providers, results_list):
            if isinstance(results, Exception):
                print(f"[{provider.name}] Search failed: {results}")
                continue
            
            if results:
                results_by_provider[provider.name] = results
                all_results.extend(results)
                providers_used.append(provider.name)
        
        # Fallback to local if no external results
        if not all_results:
            local = LocalResourceProvider()
            local_results = await local.search(query, max_per_provider * 3)
            results_by_provider["local"] = local_results
            all_results = local_results
            providers_used = ["local"]
        
        return {
            "query": query,
            "providers_used": providers_used,
            "total_results": len(all_results),
            "results_by_provider": results_by_provider,
            "all_results": all_results,
            "searched_at": datetime.utcnow().isoformat()
        }
    
    async def search_with_llm_ranking(
        self,
        query: str,
        student_context: Optional[Dict[str, Any]] = None,
        max_results: int = 5
    ) -> Dict[str, Any]:
        """
        Search for courses and use LLM to rank/recommend the best ones.
        
        Args:
            query: Skill/topic to search
            student_context: Student profile info for personalization
            max_results: Number of recommendations to return
        """
        # First, search all providers
        search_results = await self.search_all(query, max_per_provider=5)
        all_courses = search_results.get("all_results", [])
        
        if not all_courses:
            return {
                "query": query,
                "recommendations": [],
                "ai_powered": False,
                "message": "No courses found for this query."
            }
        
        # Try to use LLM for intelligent ranking
        llm = self._get_llm_service()
        
        if llm is None:
            # No LLM available - return top results as-is
            return {
                "query": query,
                "recommendations": all_courses[:max_results],
                "ai_powered": False,
                "providers_used": search_results.get("providers_used", []),
                "message": "Showing top results (AI ranking unavailable)"
            }
        
        try:
            from .ai_prompts import RESOURCE_RECOMMENDATION_PROMPT
            
            # Prepare course list for LLM
            courses_text = "\n".join([
                f"- [{i+1}] {c.get('title', 'Unknown')} ({c.get('source', 'Unknown')}) - {c.get('type', 'course')}"
                for i, c in enumerate(all_courses[:15])  # Limit to avoid token overflow
            ])
            
            context_text = ""
            if student_context:
                context_text = f"""
Student Background:
- Current Skills: {', '.join(student_context.get('skills', []))}
- Experience Level: {student_context.get('experience_level', 'Unknown')}
- Learning Goal: {student_context.get('goal', 'General improvement')}
"""
            
            prompt = RESOURCE_RECOMMENDATION_PROMPT.format(
                skill=query,
                courses_list=courses_text,
                student_context=context_text or "No specific context provided",
                num_recommendations=max_results
            )
            
            response = await llm.generate(prompt)
            
            if response and not response.startswith("Error"):
                # Parse LLM response for ranked indices
                recommended_indices = self._parse_llm_rankings(response, len(all_courses))
                ranked_results = [all_courses[i] for i in recommended_indices if i < len(all_courses)]
                
                # If parsing failed, fall back to all results
                if not ranked_results:
                    ranked_results = all_courses[:max_results]
                
                return {
                    "query": query,
                    "recommendations": ranked_results[:max_results],
                    "ai_powered": True,
                    "ai_reasoning": response.strip(),
                    "providers_used": search_results.get("providers_used", []),
                    "total_found": len(all_courses)
                }
            
        except Exception as e:
            print(f"LLM ranking failed: {e}")
        
        # Fallback - return results without AI ranking
        return {
            "query": query,
            "recommendations": all_courses[:max_results],
            "ai_powered": False,
            "providers_used": search_results.get("providers_used", []),
            "message": "Showing top results (AI ranking failed)"
        }
    
    def _parse_llm_rankings(self, llm_response: str, max_index: int) -> List[int]:
        """
        Parse LLM response to extract recommended course indices.
        Expects format like: "1, 3, 5" or "[1] ... [3] ... [5]"
        """
        import re
        
        # Try to find numbers in the response
        numbers = re.findall(r'\[?(\d+)\]?', llm_response)
        
        indices = []
        for num_str in numbers:
            try:
                idx = int(num_str) - 1  # Convert to 0-indexed
                if 0 <= idx < max_index and idx not in indices:
                    indices.append(idx)
            except ValueError:
                continue
        
        return indices[:10]  # Safety limit


# Singleton instance
course_search_service = CourseSearchService()


# ============ LLM Tool Functions ============
# These are the tool functions that can be called by the LLM

async def tool_search_youtube(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tool function: Search YouTube for educational videos."""
    provider = YouTubeProvider()
    return await provider.search(query, max_results)


async def tool_search_udemy(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tool function: Search Udemy for courses."""
    provider = UdemyScraperProvider()
    return await provider.search(query, max_results)


async def tool_search_coursera(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tool function: Search Coursera for courses."""
    provider = CourseraScraperProvider()
    return await provider.search(query, max_results)


async def tool_search_edx(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """Tool function: Search EdX for courses."""
    provider = EdXScraperProvider()
    return await provider.search(query, max_results)


async def tool_search_all_courses(query: str, max_per_provider: int = 3) -> Dict[str, Any]:
    """Tool function: Search all providers for courses."""
    return await course_search_service.search_all(query, max_per_provider)


async def tool_get_course_recommendations(
    skill: str,
    current_skills: Optional[List[str]] = None,
    experience_level: str = "beginner"
) -> Dict[str, Any]:
    """
    Tool function: Get AI-ranked course recommendations.
    
    Args:
        skill: Skill to learn
        current_skills: Student's existing skills
        experience_level: beginner/intermediate/advanced
    """
    context = {
        "skills": current_skills or [],
        "experience_level": experience_level,
        "goal": f"Learn {skill}"
    }
    return await course_search_service.search_with_llm_ranking(
        query=skill,
        student_context=context,
        max_results=5
    )
