import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

async def test_tavily():
    tavily_key = os.getenv("TAVILY_API_KEY")
    query = "google company culture"
    url = "https://api.tavily.com/search"
    payload = {
        "query": query,
        "api_key": tavily_key,
        "search_depth": "basic",
        "max_results": 5
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            print(f"Status: {resp.status}")
            print(await resp.text())

asyncio.run(test_tavily())
