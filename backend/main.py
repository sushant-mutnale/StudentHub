from datetime import datetime, timedelta

from fastapi import FastAPI, Request
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
    voice_routes,
    demo_routes,
    sidebar_routes,
)
from .utils.auth import hash_password
from .events.handlers import register_all_handlers
from .workers import worker_manager, OutboxWorker, OutboxCleanupWorker, RecommendationWorker, RetentionWorker, IngestionWorker
from .middleware import RateLimitMiddleware, CorrelationIdMiddleware, IdempotencyMiddleware

app = FastAPI(title="Student Hub API")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    print(f"Incoming Request: {request.method} {request.url.path}")
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        print(f"Request Completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        print(f"Request Failed: {request.method} {request.url.path} - Error: {str(e)}")
        raise e

# Middlewares (Order matters: executed bottom-to-top for request, top-to-bottom for response)
if settings.app_env != "testing":
    app.add_middleware(RateLimitMiddleware)  # 3. Check rate limits
    app.add_middleware(IdempotencyMiddleware)  # 2. Check for duplicate requests
    app.add_middleware(CorrelationIdMiddleware)  # 1. Tag request with ID

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_origin_regex="https?://.*",
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
        
        # Check if we need immediate ingestion (startup check)
        from .services.opportunity_ingestion import ingestion_log_collection, opportunity_ingestion
        from datetime import timedelta
        
        try:
            latest_log = await ingestion_log_collection().find_one(sort=[("timestamp", -1)])
            
            needs_ingestion = False
            if not latest_log:
                # No logs exist, run first time
                needs_ingestion = True
            else:
                last_run = latest_log.get("timestamp")
                if last_run and (datetime.utcnow() - last_run) > timedelta(hours=24):
                    # More than 24h since last run
                    needs_ingestion = True
                    
            if needs_ingestion:
                import sys
                print("Running initial opportunity ingestion check on startup...", file=sys.stderr)
                # Fire and forget
                import asyncio
                asyncio.create_task(opportunity_ingestion.ingest_all(use_mock=False))
        except Exception as e:
            import sys
            print(f"Failed to check ingestion status on startup: {e}", file=sys.stderr)
    
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
app.include_router(voice_routes.router, prefix="/api", tags=["voice"])
app.include_router(demo_routes.router, tags=["demo"])
app.include_router(sidebar_routes.router)

async def seed_default_users():
    db = get_database()
    if await db["users"].count_documents({}) > 3:
        return
    now = datetime.utcnow()
    
    # 1. Seed Diverse Users for Suggestions
    demo_users = [
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
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "alice_coder",
            "email": "alice@example.com",
            "password_hash": hash_password("Alice@123"),
            "full_name": "Alice Johnson",
            "prn": "PRN00456",
            "college": "Sample University",
            "branch": "Computer Science",
            "year": "3rd Year",
            "skills": ["React", "JavaScript", "UI Design"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "bob_data",
            "email": "bob@example.com",
            "password_hash": hash_password("Bob@123"),
            "full_name": "Bob Smith",
            "prn": "PRN00789",
            "college": "Tech Institute",
            "branch": "IT",
            "year": "2nd Year",
            "skills": ["Python", "SQL", "Data Science"],
            "connections": [],
            "created_at": now,
            "updated_at": now,
        },
        {
            "role": "student",
            "username": "charlie_dev",
            "email": "charlie@example.com",
            "password_hash": hash_password("Charlie@123"),
            "full_name": "Charlie Brown",
            "prn": "PRN00111",
            "college": "Sample University",
            "branch": "Data Science",
            "year": "4th Year",
            "skills": ["Python", "Machine Learning", "FastAPI"],
            "connections": [],
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
            "connections": [],
            "created_at": now,
            "updated_at": now,
        }
    ]
    
    for u in demo_users:
        if not await db["users"].find_one({"username": u["username"]}):
            await db["users"].insert_one(u)

    # 2. Seed Opportunities if empty
    if await db["opportunities_hackathons"].count_documents({}) == 0:
        await db["opportunities_hackathons"].insert_many([
            {
                "source": "seed",
                "source_id": "seed_h1",
                "event_url": "https://devpost.com/hackathons",
                "event_name": "Global AI Challenge 2026",
                "organizer": "Google Cloud",
                "theme_tags": ["AI", "ML", "Cloud"],
                "start_date": now + timedelta(days=20),
                "status": "open"
            },
            {
                "source": "seed",
                "source_id": "seed_h2",
                "event_url": "https://devpost.com/hackathons",
                "event_name": "Web3 Innovation Summit",
                "organizer": "Solana Foundation",
                "theme_tags": ["Web3", "Blockchain"],
                "start_date": now + timedelta(days=15),
                "status": "upcoming"
            }
        ])

    # 3. Seed Learning Resources if empty
    if await db["opportunities_content"].count_documents({}) == 0:
        await db["opportunities_content"].insert_many([
            {
                "source_id": "seed_r1",
                "title": "Mastering React Server Components",
                "publisher": "React Blog",
                "topic": "Frontend",
                "url": "https://react.dev/blog",
                "published_at": now - timedelta(days=2)
            },
            {
                "source_id": "seed_r2",
                "title": "System Design: The Complete Guide",
                "publisher": "Medium",
                "topic": "Architecture",
                "url": "https://medium.com",
                "published_at": now - timedelta(days=5)
            }
        ])


# Vercel Serverless Handler
# This allows FastAPI to work with Vercel's serverless Python functions
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Mangum not installed (local dev), ignore
    handler = None

