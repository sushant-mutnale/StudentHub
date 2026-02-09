from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
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
)
from .utils.auth import hash_password
from .events.handlers import register_all_handlers
from .workers import worker_manager, OutboxWorker, OutboxCleanupWorker, RecommendationWorker, RetentionWorker, IngestionWorker
from .middleware import RateLimitMiddleware, CorrelationIdMiddleware, IdempotencyMiddleware

app = FastAPI(title="Student Hub API")

# Middlewares (Order matters: executed bottom-to-top for request, top-to-bottom for response)
if settings.app_env != "testing":
    app.add_middleware(RateLimitMiddleware)  # 3. Check rate limits
    app.add_middleware(IdempotencyMiddleware)  # 2. Check for duplicate requests
    app.add_middleware(CorrelationIdMiddleware)  # 1. Tag request with ID

app.add_middleware(
    CORSMiddleware,
    # allow_origins=settings.frontend_origins,  # Strictly limited origins
    allow_origin_regex="https?://.*",  # Allow ALL origins (http/https) to support Vercel/Render/Localhost
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for Render and monitoring."""
    return {"status": "healthy", "version": "1.0.0"}


@app.on_event("startup")
async def startup_event():
    await connect_to_mongo()
    await ensure_database_indexes()
    
    # Initialize Event-Driven System
    register_all_handlers()
    
    # Start Background Workers (skip during testing to avoid loop conflicts)
    if settings.app_env != "testing":
        worker_manager.register(OutboxWorker(poll_interval=2.0))
        worker_manager.register(OutboxCleanupWorker(poll_interval=3600))
        worker_manager.register(RecommendationWorker(poll_interval=300))
        worker_manager.register(RetentionWorker(poll_interval=86400))
        worker_manager.register(IngestionWorker(poll_interval=43200)) # 12 hours
        await worker_manager.start_all()
    
    if settings.app_env.lower() != "production":
        await seed_default_users()


@app.on_event("shutdown")
async def shutdown_event():
    if settings.app_env != "testing":
        await worker_manager.stop_all()
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


async def seed_default_users():
    db = get_database()
    if await db["users"].count_documents({}) > 0:
        return
    now = datetime.utcnow()
    await db["users"].insert_many(
        [
            {
                "role": "student",
                "username": "demo_student",
                "email": "student@example.com",
                "password_hash": hash_password("Student@123"),
                "full_name": "Demo Student",
                "prn": "PRN00123",
                "college": "Sample University",
                "branch": "Computer Science",
                "year": "3rd Year",
                "skills": ["React", "Python", "MongoDB"],
                "created_at": now,
                "updated_at": now,
            },
            {
                "role": "recruiter",
                "username": "demo_recruiter",
                "email": "recruiter@example.com",
                "password_hash": hash_password("Recruiter@123"),
                "company_name": "Talent Seekers",
                "contact_number": "+1-555-0101",
                "website": "https://talentseekers.example.com",
                "company_description": "Connecting graduates with dream jobs.",
                "skills": [],
                "created_at": now,
                "updated_at": now,
            },
        ]
    )


# Vercel Serverless Handler
# This allows FastAPI to work with Vercel's serverless Python functions
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Mangum not installed (local dev), ignore
    handler = None
