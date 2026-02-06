from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from backend.middleware import RateLimitMiddleware
from backend.config import settings

def test_auth_rate_limit():
    """Test rate limiting logic using a dedicated app instance."""
    
    # 1. Create app with middleware explicitly added
    # We set rate limit settings temporarily if needed, but they are read from settings object
    # which is global. Ideally mock settings, but defaults are 5/minute for auth.
    
    # Force settings values just in case
    # stored_limit = settings.rate_limit_auth
    # settings.rate_limit_auth = "5/minute" 
    
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    
    @app.post("/auth/login")
    async def login():
        return {"msg": "ok"}
        
    with TestClient(app) as client:
        # Hit 10 times (limit is 5)
        for i in range(10):
            response = client.post("/auth/login", json={"u": "p"})
            
            if response.status_code == 429:
                break
        
        # We should have hit 429 by now
        assert response.status_code == 429
        assert "Too Many Requests" in response.text
        assert "X-RateLimit-Limit" in response.headers
