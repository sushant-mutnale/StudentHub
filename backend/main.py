import logging

from .config import settings
from .logging_config import configure_logging, redact_text

configure_logging(settings.app_env)
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .database import close_mongo_connection, connect_to_mongo, get_database
from .models.indexes import ensure_database_indexes
from .routes import (
    auth_routes,
    interview_routes,
    job_routes,
    match_routes,
    offer_routes,
    post_routes,
    thread_routes,
    next_action_routes,
    calendar_routes,
    saved_search_routes,
    user_routes,
    notification_routes,
    learning_routes,
    course_routes,
    resume_routes,
    jd_routes,
    company_routes,
    session_routes,
    question_routes,
    flow_routes,
    planner_routes,
    sandbox_routes,
    research_routes,
    agent_routes,
    opportunity_routes,
    recommendation_routes,
    smart_notification_routes,
    pipeline_routes,
    application_routes,
    scorecard_routes,
    verification_routes,
    admin_routes,
    hackathon_routes,
    message_routes,
    analytics_routes,
    voice_routes,
    demo_routes,
    sidebar_routes,
)
from .seed import seed_default_users
from .events.handlers import register_all_handlers
from .workers import worker_manager
from .worker_health import DEGRADED_WORKER_HEALTH, get_worker_health
from .middleware import RateLimitMiddleware, CorrelationIdMiddleware, IdempotencyMiddleware, SecurityHeadersMiddleware

app = FastAPI(title="Student Hub API")

from fastapi.responses import JSONResponse
from fastapi import Request
import traceback
from bson.errors import InvalidId

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        {
            "event": "unhandled_exception",
            "method": request.method,
            "path": request.url.path,
            "error": redact_text(str(exc)),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."}
    )

@app.exception_handler(InvalidId)
async def invalid_id_exception_handler(request: Request, exc: InvalidId):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid document ID format."}
    )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    logger.info(
        {
            "event": "request.started",
            "method": request.method,
            "path": request.url.path,
        }
    )
    start_time = time.time()
    try:
        response = await call_next(request)
        logger.info(
            {
                "event": "request.completed",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_seconds": round(time.time() - start_time, 4),
            }
        )
        return response
    except Exception as e:
        logger.error(
            {
                "event": "request.failed",
                "method": request.method,
                "path": request.url.path,
                "error": redact_text(str(e)),
            },
            exc_info=True,
        )
        raise e

from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: int = 60):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": "Request timed out"}
            )

# Security headers are applied in ALL environments including tests.
app.add_middleware(SecurityHeadersMiddleware)

# Middlewares (Order matters: executed bottom-to-top for request, top-to-bottom for response)
if settings.app_env != "testing":
    app.add_middleware(TimeoutMiddleware, timeout=60)
    app.add_middleware(RateLimitMiddleware)  # 3. Check rate limits
    app.add_middleware(IdempotencyMiddleware)  # 2. Check for duplicate requests
    app.add_middleware(CorrelationIdMiddleware)  # 1. Tag request with ID

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """Basic liveness check."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/health/ready", tags=["health"])
async def readiness_check():
    checks = {"mongodb": "ok", "redis": "ok"}
    overall = "ready"

    try:
        db = get_database()
        await db.command("ping")
    except Exception:
        checks["mongodb"] = "error"
        overall = "degraded"

    try:
        from .redis_client import RedisClient
        ok = await RedisClient.ping()
        if not ok:
            checks["redis"] = "error"
            overall = "degraded"
    except Exception:
        checks["redis"] = "error"
        overall = "degraded"

    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks, "version": "1.0.0"},
    )


@app.get("/health/worker", tags=["health"])
async def worker_health_check():
    try:
        result = await get_worker_health()
    except Exception:
        result = dict(DEGRADED_WORKER_HEALTH)
    status_code = 200 if result["status"] == "ok" else 503
    return JSONResponse(status_code=status_code, content=result)


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    register_all_handlers()


@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()


app.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
app.include_router(user_routes.router, prefix="/users", tags=["users"])
app.include_router(post_routes.router, prefix="/posts", tags=["posts"])
app.include_router(job_routes.router, prefix="/jobs", tags=["jobs"])
app.include_router(match_routes.router, prefix="/jobs", tags=["matches"])
app.include_router(thread_routes.router, tags=["threads"])
app.include_router(interview_routes.router)
app.include_router(offer_routes.router)
app.include_router(notification_routes.router)
app.include_router(message_routes.router, prefix="/messages", tags=["messages"])
app.include_router(learning_routes.router)
app.include_router(course_routes.router)
app.include_router(resume_routes.router)
app.include_router(jd_routes.router)
app.include_router(company_routes.router)
app.include_router(session_routes.router)
app.include_router(question_routes.router)
app.include_router(flow_routes.router)
app.include_router(planner_routes.router)
app.include_router(sandbox_routes.router)
app.include_router(research_routes.router)
app.include_router(agent_routes.router)
app.include_router(opportunity_routes.router)
app.include_router(recommendation_routes.router)
app.include_router(smart_notification_routes.router)
app.include_router(pipeline_routes.router)
app.include_router(application_routes.router)
app.include_router(verification_routes.router)
app.include_router(admin_routes.router)
app.include_router(hackathon_routes.router)
app.include_router(analytics_routes.router)
app.include_router(scorecard_routes.router)  # Recruiter interview scorecards
app.include_router(voice_routes.router, prefix="/api", tags=["voice"])
app.include_router(next_action_routes.router)
app.include_router(calendar_routes.router)
app.include_router(saved_search_routes.router)
app.include_router(demo_routes.router, tags=["demo"])
app.include_router(sidebar_routes.router)



# Vercel Serverless Handler
# This allows FastAPI to work with Vercel's serverless Python functions
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Mangum not installed (local dev), ignore
    handler = None

