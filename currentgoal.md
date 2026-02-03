Module 4: Complete 3-Week Plan (Detailed, Structured)
WEEK 1: Data Sources + Ingestion Pipeline
Goal
Set up reliable external data sources and build automated ingestion jobs that pull opportunities into MongoDB.

Day 1-2: Source Selection & API Setup
Step 1: Create Source Registry Document
What to do:

Create file: backend/docs/external_sources.md

Document each source with:

Source name

What data it provides

Access method (API/RSS/scraper)

Cost (if any)

Rate limits

Reliability score (how stable is it?)

Fallback option

Example structure:

text
Source: Apify Internshala Scrapper
Type: Jobs/Internships
Access: REST API (Apify Actor)
Cost: $5 per 1,000 results (free tier available)
Rate Limit: Based on Apify account plan
Fields Available: title, company, location, stipend, skills, deadline
Reliability: Medium (community actor, may change)
Fallback: Manual RSS from Internshala + another Apify actor
Update Frequency: Daily (recommended)
Step 2: Set Up API Keys & Test Access
What to do:

Create accounts on:

Apify (for Internshala scraper)
​

NewsAPI or use Google News RSS (no key needed)
​

Store credentials in .env:

text
APIFY_API_KEY=your_key
NEWS_API_KEY=optional
Test each source manually:

Run test API call to Apify Internshala actor

Fetch sample RSS feed from Google News

Verify Devpost structure (manual check first)

Deliverable: Confirmed access to all 3 source types with sample data retrieved.

Day 3-4: Design Unified Data Schema
Step 1: Design MongoDB Collections
What to do:

Create 3 collections (or 1 with type field):

Collection: opportunities_jobs

json
{
  "_id": "ObjectId",
  "source": "internshala_apify",
  "source_id": "unique_id_from_source",
  "source_url": "https://internshala.com/...",
  
  "title": "Backend Developer Intern",
  "company": "TechCorp",
  "location": "Mumbai / Remote",
  "work_mode": "hybrid",
  
  "stipend": {
    "amount": 15000,
    "currency": "INR",
    "period": "month"
  },
  
  "skills_required": ["python", "fastapi", "mongodb"],
  "experience_required": "0-1 years",
  "duration": "3 months",
  
  "description_snippet": "First 200 chars...",
  "posted_at": "2026-02-01T...",
  "apply_by": "2026-03-01T...",
  
  "scraped_at": "2026-02-03T...",
  "last_verified": "2026-02-03T...",
  "status": "active",
  
  "metadata": {
    "applicants_count": 50,
    "views": 200
  }
}
Collection: opportunities_hackathons

json
{
  "_id": "ObjectId",
  "source": "devpost",
  "source_url": "https://devpost.com/hackathons/...",
  
  "event_name": "AI for Good Hackathon 2026",
  "organizer": "Microsoft",
  "theme_tags": ["AI", "Healthcare", "Social Impact"],
  
  "start_date": "2026-03-15T...",
  "end_date": "2026-03-17T...",
  "registration_deadline": "2026-03-10T...",
  
  "eligibility": "students",
  "participation_mode": "online",
  "prize_pool": "$10,000",
  
  "tech_stack_tags": ["python", "tensorflow", "react"],
  "difficulty_level": "intermediate",
  
  "scraped_at": "2026-02-03T...",
  "status": "open"
}
Collection: opportunities_content

json
{
  "_id": "ObjectId",
  "source": "google_news_rss",
  "source_url": "https://news.google.com/...",
  
  "title": "AI Job Market Trends in 2026",
  "publisher": "TechCrunch",
  "published_at": "2026-02-03T08:00:00Z",
  
  "topic": "AI",
  "category": "career_insights",
  "language": "en",
  "country": "IN",
  
  "query_used": "intitle:AI+jobs when:7d",
  "relevance_keywords": ["hiring", "AI engineer", "machine learning"],
  
  "scraped_at": "2026-02-03T12:00:00Z",
  "engagement_score": 0
}
Step 2: Create Data Validation Models
What to do:

Create file: backend/models/opportunity.py

Define Pydantic models for each opportunity type:

JobOpportunity

HackathonOpportunity

ContentOpportunity

Why this matters:
Validation ensures bad/incomplete data from external sources doesn't break your system.

Day 5-7: Build Ingestion Services
Step 1: Create Ingestion Service Architecture
What to do:

Create folder: backend/services/ingestion/

Create base class: base_ingestor.py

Base Ingestor Interface (concept, no code):

text
Class BaseIngestor:
    Methods:
    - fetch_raw_data() → get data from source
    - normalize_data(raw) → convert to unified schema
    - validate_data(normalized) → check quality
    - store_data(validated) → save to MongoDB
    - handle_duplicates() → skip if already exists
    - log_ingestion_stats() → track success/failures
Step 2: Build Job Ingestion Service
What to do:

Create file: backend/services/ingestion/job_ingestor.py

Logic flow (pseudocode):

text
FUNCTION ingest_jobs():
    # Fetch from Apify
    raw_data = call_apify_internshala_actor(
        category="technology",
        location="India",
        max_results=100
    )
    
    normalized_jobs = []
    FOR each raw_job in raw_data:
        # Normalize
        job = {
            source: "internshala_apify",
            source_id: raw_job.id,
            title: raw_job.profile,
            company: raw_job.company_name,
            location: parse_location(raw_job.location),
            work_mode: detect_work_mode(raw_job.location),
            stipend: parse_stipend(raw_job.stipend),
            skills_required: normalize_skills(raw_job.skills),
            posted_at: parse_date(raw_job.start_date),
            apply_by: parse_date(raw_job.last_date),
            source_url: raw_job.url,
            scraped_at: now()
        }
        
        # Validate
        IF validate_job(job):
            normalized_jobs.append(job)
    
    # Store (skip duplicates)
    FOR each job in normalized_jobs:
        IF NOT exists_in_db(job.source_id):
            db.opportunities_jobs.insert(job)
        ELSE:
            db.opportunities_jobs.update(job.source_id, job)
    
    log_stats(total=len(raw_data), stored=len(normalized_jobs))
Key helper functions to build:

normalize_skills(skills_string): "Python, React" → ["python", "react"]

parse_stipend(stipend_text): "₹15,000/month" → {amount: 15000, currency: "INR"}

detect_work_mode(location): "Work From Home" → "remote"

exists_in_db(source_id): check if job already stored

Step 3: Build Hackathon Ingestion Service
What to do:

Create file: backend/services/ingestion/hackathon_ingestor.py

Logic flow (pseudocode):

text
FUNCTION ingest_hackathons():
    # Option 1: Scrape Devpost (use BeautifulSoup)
    # Option 2: Use existing community scraper
    # Option 3: Manual RSS if available
    
    raw_data = fetch_devpost_listings(
        status="open",
        themes=["AI", "Web3", "Healthcare"]
    )
    
    normalized_hackathons = []
    FOR each raw_event in raw_data:
        hackathon = {
            source: "devpost",
            event_name: raw_event.title,
            source_url: raw_event.url,
            organizer: extract_organizer(raw_event),
            theme_tags: extract_themes(raw_event.tags),
            start_date: parse_date(raw_event.start),
            end_date: parse_date(raw_event.end),
            registration_deadline: parse_date(raw_event.deadline),
            eligibility: detect_eligibility(raw_event.description),
            tech_stack_tags: extract_tech_stack(raw_event),
            scraped_at: now()
        }
        
        IF validate_hackathon(hackathon):
            normalized_hackathons.append(hackathon)
    
    FOR each hackathon in normalized_hackathons:
        IF NOT exists_in_db(hackathon.source_url):
            db.opportunities_hackathons.insert(hackathon)
Important considerations:

Devpost might not have a clean API, so you may need BeautifulSoup or RSS fallback

Store only public metadata (event name, dates, link)

Don't store full descriptions (copyright)

Step 4: Build Content Ingestion Service
What to do:

Create file: backend/services/ingestion/content_ingestor.py

Logic flow (pseudocode):

text
FUNCTION ingest_content():
    # Define topic queries
    topics = {
        "AI": "intitle:AI OR intitle:artificial+intelligence when:7d",
        "Data Science": "intitle:data+science OR intitle:analytics when:7d",
        "Full Stack": "intitle:full+stack OR intitle:MERN when:7d",
        "DevOps": "intitle:DevOps OR intitle:Docker when:7d"
    }
    
    all_content = []
    FOR each topic, query in topics:
        # Fetch Google News RSS
        rss_url = build_google_news_rss_url(
            query=query,
            language="en",
            country="IN"
        )
        
        raw_feed = fetch_rss(rss_url)
        
        FOR each item in raw_feed.items:
            content = {
                source: "google_news_rss",
                source_url: item.link,
                title: item.title,
                publisher: extract_publisher(item.source),
                published_at: parse_date(item.pubDate),
                topic: topic,
                category: "career_insights",
                language: "en",
                country: "IN",
                query_used: query,
                scraped_at: now()
            }
            
            IF validate_content(content):
                all_content.append(content)
    
    FOR each content in all_content:
        IF NOT exists_in_db(content.source_url):
            db.opportunities_content.insert(content)
Google News RSS URL builder (concept):

text
FUNCTION build_google_news_rss_url(query, language, country):
    base = "https://news.google.com/rss/search"
    params = {
        "q": query,
        "hl": language,
        "gl": country,
        "ceid": f"{country}:{language}"
    }
    RETURN base + "?" + urlencode(params)
Step 5: Create Scheduling System
What to do:

Create file: backend/jobs/scheduler.py

Use APScheduler or similar library

Schedule design:

text
Jobs Schedule:
- ingest_jobs: Every 24 hours at 2 AM IST
- ingest_hackathons: Every 24 hours at 3 AM IST
- ingest_content: Every 6 hours
- cleanup_expired: Every 24 hours at 4 AM
Cleanup logic (important):

text
FUNCTION cleanup_expired_opportunities():
    # Jobs
    db.opportunities_jobs.update_many(
        {apply_by: {$lt: now()}},
        {$set: {status: "expired"}}
    )
    
    # Hackathons
    db.opportunities_hackathons.update_many(
        {end_date: {$lt: now()}},
        {$set: {status: "closed"}}
    )
    
    # Content (archive after 30 days)
    db.opportunities_content.delete_many(
        {scraped_at: {$lt: now() - 30 days}}
    )
Week 1 Deliverables Summary
Component	Status	What's Built
Source Registry	✅	Documented 3 data sources with access methods
Data Schema	✅	3 MongoDB collections with validation
Job Ingestor	✅	Apify Internshala integration
Hackathon Ingestor	✅	Devpost scraping/metadata extraction
Content Ingestor	✅	Google News RSS multi-topic fetcher
Scheduler	✅	Automated daily/hourly runs
Cleanup Job	✅	Auto-expire old opportunities
WEEK 2: Recommendation Engine
Goal
Build an intelligent ranking system that matches opportunities to students based on their AI profile, skills, and learning gaps.

Day 1-2: Design Recommendation Algorithm
Step 1: Define Recommendation Inputs
What to consider:
From student profile:

skills (current proficiency levels)

ai_profile.skill_score

ai_profile.learning_score

ai_profile.interview_score

learning_gaps (from Module 3)

location / preferred_locations

graduation_year

interests / career_goals

From opportunity:

skills_required

experience_required

location / work_mode

posted_at (freshness)

stipend / prize_pool

difficulty_level (if available)

Step 2: Design Scoring Formulas
Job Recommendation Score:

text
Job Score = 
    (Skill Match × 40%) +
    (Proficiency Fit × 20%) +
    (Freshness × 15%) +
    (Location Match × 10%) +
    (Career Alignment × 10%) +
    (AI Profile Readiness × 5%)
Component calculations (pseudocode):

1. Skill Match Score (0-100):

text
FUNCTION calculate_skill_match(student_skills, job_required_skills):
    matched_skills = intersection(student_skills, job_required_skills)
    match_percentage = len(matched_skills) / len(job_required_skills) * 100
    
    # Bonus for proficiency level match
    FOR each matched_skill:
        IF student_skill_level >= 70:
            match_percentage += 5  # bonus for high proficiency
    
    RETURN min(match_percentage, 100)
2. Proficiency Fit Score (0-100):

text
FUNCTION calculate_proficiency_fit(student_skills, job_skills):
    # Check if student is under/over/perfect qualified
    avg_student_proficiency = average(student_skills.levels)
    
    IF experience_required == "0-1 years" AND avg_student_proficiency < 50:
        RETURN 100  # perfect fit - entry level
    ELSE IF experience_required == "1-3 years" AND avg_student_proficiency 50-80:
        RETURN 100  # perfect fit - intermediate
    ELSE IF student overqualified:
        RETURN 60  # might get bored
    ELSE IF student underqualified:
        RETURN 40  # might struggle
3. Freshness Score (0-100):

text
FUNCTION calculate_freshness(posted_at):
    days_old = (now() - posted_at).days
    
    IF days_old <= 3:
        RETURN 100
    ELSE IF days_old <= 7:
        RETURN 80
    ELSE IF days_old <= 14:
        RETURN 60
    ELSE IF days_old <= 30:
        RETURN 40
    ELSE:
        RETURN 20
4. Location Match Score (0-100):

text
FUNCTION calculate_location_match(student_location, job_location, job_work_mode):
    IF job_work_mode == "remote":
        RETURN 100  # always matches
    ELSE IF student_location in job_location:
        RETURN 100  # exact match
    ELSE IF student_location.state == job_location.state:
        RETURN 70  # same state
    ELSE IF job_work_mode == "hybrid":
        RETURN 50  # hybrid might work
    ELSE:
        RETURN 20  # relocation needed
5. Career Alignment Score (0-100):

text
FUNCTION calculate_career_alignment(student_interests, job_title, job_skills):
    alignment_score = 0
    
    # Check if job matches stated interests
    FOR each interest in student_interests:
        IF interest in job_title OR interest in job_skills:
            alignment_score += 30
    
    # Check if it fills learning gaps (high value!)
    FOR each gap in student_learning_gaps:
        IF gap in job_skills:
            alignment_score += 20  # job helps fill gap
    
    RETURN min(alignment_score, 100)
6. AI Profile Readiness Score (0-100):

text
FUNCTION calculate_readiness(ai_profile):
    # Higher overall score = more competitive
    # But also consider if student is improving
    
    readiness = ai_profile.overall_score
    
    # Bonus for recent improvement
    IF ai_profile.learning_score increased in last 30 days:
        readiness += 10
    
    IF ai_profile.interview_score > 70:
        readiness += 10
    
    RETURN min(readiness, 100)
Day 3-4: Build Recommendation Service
Step 1: Create Recommendation Engine
What to do:

Create file: backend/services/recommendation_engine.py

Main class structure:

text
Class RecommendationEngine:
    
    Method: recommend_jobs(student_id, limit=20, filters={}):
        # Fetch student profile
        student = get_student_profile(student_id)
        
        # Fetch active jobs
        jobs = db.opportunities_jobs.find({status: "active"})
        
        # Score each job
        scored_jobs = []
        FOR each job in jobs:
            score = calculate_job_score(student, job)
            scored_jobs.append({
                job: job,
                score: score,
                match_details: explain_score(student, job)
            })
        
        # Sort by score descending
        scored_jobs.sort(key=score, reverse=True)
        
        # Apply filters if provided
        IF filters.location:
            scored_jobs = filter_by_location(scored_jobs, filters.location)
        
        IF filters.min_stipend:
            scored_jobs = filter_by_stipend(scored_jobs, filters.min_stipend)
        
        # Return top N
        RETURN scored_jobs[:limit]
    
    Method: recommend_hackathons(student_id, limit=10):
        student = get_student_profile(student_id)
        hackathons = db.opportunities_hackathons.find({status: "open"})
        
        scored_hackathons = []
        FOR each hackathon in hackathons:
            score = calculate_hackathon_score(student, hackathon)
            scored_hackathons.append({
                hackathon: hackathon,
                score: score
            })
        
        scored_hackathons.sort(key=score, reverse=True)
        RETURN scored_hackathons[:limit]
    
    Method: recommend_content(student_id, limit=15):
        student = get_student_profile(student_id)
        content = db.opportunities_content.find()
        
        scored_content = []
        FOR each article in content:
            score = calculate_content_score(student, article)
            scored_content.append({
                article: article,
                score: score
            })
        
        scored_content.sort(key=score, reverse=True)
        RETURN scored_content[:limit]
Step 2: Add Match Explanation Feature
What to do:
Users should understand why something was recommended.

text
FUNCTION explain_score(student, job):
    explanation = {
        "total_score": score,
        "breakdown": {
            "skill_match": {
                "score": 85,
                "reason": "You have 4 out of 5 required skills",
                "matched_skills": ["python", "fastapi", "mongodb"],
                "missing_skills": ["docker"]
            },
            "proficiency_fit": {
                "score": 90,
                "reason": "Your skill level matches entry-level requirement"
            },
            "freshness": {
                "score": 100,
                "reason": "Posted 2 days ago"
            }
        },
        "recommendation": "Great fit! Consider learning Docker to be 100% match."
    }
    RETURN explanation
Day 5-6: Build Recommendation API Endpoints
Step 1: Create Recommendation Routes
What to do:

Create file: backend/routes/recommendation.py

Endpoints to create:

1. GET /recommendations/jobs

text
Query params:
- student_id (from JWT token)
- limit (default 20)
- location (optional filter)
- min_stipend (optional filter)
- work_mode (optional: remote/onsite/hybrid)

Response:
{
    "status": "success",
    "recommendations": [
        {
            "job": {job object},
            "score": 87.5,
            "rank": 1,
            "match_details": {explanation object},
            "action_url": "source URL or /jobs/{id}/apply"
        }
    ],
    "filters_applied": {...},
    "total_available": 150
}
2. GET /recommendations/hackathons

text
Query params:
- student_id
- limit (default 10)
- theme (optional: AI, Web3, etc.)
- start_date_after (optional)

Response:
{
    "status": "success",
    "recommendations": [
        {
            "hackathon": {hackathon object},
            "score": 92.0,
            "rank": 1,
            "why_recommended": "Matches your AI skills and learning goals"
        }
    ]
}
3. GET /recommendations/content

text
Query params:
- student_id
- limit (default 15)
- topic (optional: AI, Data Science, etc.)
- recency (optional: today/week/month)

Response:
{
    "status": "success",
    "recommendations": [
        {
            "article": {content object},
            "score": 88.0,
            "relevance_reason": "Trending in AI, your top interest"
        }
    ]
}
4. POST /recommendations/feedback

text
Purpose: Track user interactions to improve recommendations

Body:
{
    "opportunity_id": "ObjectId",
    "opportunity_type": "job/hackathon/content",
    "action": "clicked/saved/ignored/applied",
    "student_id": "ObjectId"
}

Logic:
- Store interaction in `recommendation_feedback` collection
- Use this data to adjust future scores
Day 7: Personalization & Feedback Loop
Step 1: Add Interaction Tracking
What to do:

Create collection: recommendation_feedback

Schema:

json
{
  "_id": "ObjectId",
  "student_id": "ObjectId",
  "opportunity_id": "ObjectId",
  "opportunity_type": "job",
  "action": "clicked",
  "timestamp": "2026-02-03T...",
  "recommendation_score": 87.5,
  "recommendation_rank": 3,
  "context": {
    "source_page": "feed",
    "device": "mobile"
  }
}
Step 2: Use Feedback to Adjust Scores
What to do:
Refine recommendation logic over time:

text
FUNCTION adjust_score_based_on_feedback(base_score, student_id, opportunity):
    # Check if student interacted with similar opportunities before
    
    similar_interactions = db.recommendation_feedback.find({
        student_id: student_id,
        opportunity_type: opportunity.type,
        action: {$in: ["clicked", "applied", "saved"]}
    })
    
    # If student consistently ignores certain types
    IF student ignored similar opportunities 3+ times:
        base_score *= 0.7  # reduce score
    
    # If student consistently engages with certain types
    IF student engaged with similar opportunities 3+ times:
        base_score *= 1.3  # boost score
    
    RETURN base_score
Week 2 Deliverables Summary
Component	Status	What's Built
Scoring Algorithms	✅	6 scoring components with formulas
Recommendation Engine	✅	Service class with 3 recommendation types
Match Explanation	✅	Why each opportunity was recommended
API Endpoints	✅	4 endpoints (jobs/hackathons/content/feedback)
Feedback Loop	✅	Interaction tracking + score adjustment
Filters	✅	Location, stipend, theme, date filters
WEEK 3: Notification System
Goal
Build a smart notification system that alerts students about relevant opportunities and tracks their engagement.

Day 1-2: Design Notification Rules Engine
Step 1: Define Notification Triggers
What to consider:
When should students receive notifications?

Trigger categories:

1. New Opportunity Matches:

New job matches skills with score > 75%

New hackathon in preferred theme

Trending article in learning gap area

2. Time-Sensitive Alerts:

Application deadline approaching (3 days before)

Hackathon registration closing soon (1 day before)

Saved job about to expire

3. Learning Reminders:

Skill gap remains high for 30+ days

Learning path inactive for 7+ days

Recommended course still not started

4. Recruiter Activity:

Recruiter viewed profile

Interview scheduled

New message received

Offer extended

5. Achievement/Progress:

AI profile score increased by 10+ points

Completed learning stage

Mock interview score improved

Step 2: Design Notification Data Model
What to do:

Create collection: notifications

Schema:

json
{
  "_id": "ObjectId",
  "user_id": "ObjectId",
  "user_type": "student",
  
  "type": "opportunity_match",
  "category": "job",
  "priority": "high",
  
  "title": "New Backend Intern match!",
  "message": "TechCorp Backend Intern - 85% match for your skills",
  
  "action_url": "/jobs/ObjectId",
  "action_text": "View Job",
  
  "related_entity": {
    "entity_type": "job",
    "entity_id": "ObjectId",
    "entity_preview": {
      "title": "Backend Developer Intern",
      "company": "TechCorp"
    }
  },
  
  "trigger": {
    "rule": "new_high_match_job",
    "score": 85,
    "threshold": 75
  },
  
  "created_at": "2026-02-03T...",
  "read_at": null,
  "clicked_at": null,
  "dismissed_at": null,
  
  "delivery_status": {
    "in_app": true,
    "email": false,
    "push": false
  },
  
  "metadata": {
    "batch_id": "daily_digest_20260203",
    "experiment_group": "A"
  }
}
Day 3-4: Build Notification Service
Step 1: Create Notification Manager
What to do:

Create file: backend/services/notification_service.py

Service structure:

text
Class NotificationService:
    
    Method: check_and_create_notifications():
        # Run all notification rules
        check_opportunity_matches()
        check_deadlines()
        check_learning_reminders()
        check_recruiter_activity()
        check_achievements()
    
    Method: check_opportunity_matches():
        # Get all students
        students = db.users.find({role: "student", notifications_enabled: true})
        
        FOR each student:
            # Get recommendations
            top_jobs = RecommendationEngine.recommend_jobs(student.id, limit=5)
            
            FOR each job in top_jobs:
                # Only notify if score is very high
                IF job.score >= 75 AND NOT already_notified(student, job):
                    create_notification(
                        user_id=student.id,
                        type="opportunity_match",
                        category="job",
                        priority="high",
                        title=f"New {job.title} match!",
                        message=f"{job.company} - {job.score}% match",
                        action_url=f"/jobs/{job.id}",
                        related_entity=job
                    )
    
    Method: check_deadlines():
        # Find jobs/hackathons expiring soon
        expiring_jobs = db.opportunities_jobs.find({
            apply_by: {$gte: now(), $lte: now() + 3 days},
            status: "active"
        })
        
        FOR each job in expiring_jobs:
            # Find students who saved/viewed this job
            interested_students = db.recommendation_feedback.find({
                opportunity_id: job.id,
                action: {$in: ["saved", "clicked"]}
            })
            
            FOR each student in interested_students:
                IF NOT already_applied(student, job):
                    create_notification(
                        user_id=student.id,
                        type="deadline_reminder",
                        priority="urgent",
                        title="Application deadline approaching",
                        message=f"{job.title} at {job.company} closes in 3 days"
                    )
    
    Method: check_learning_reminders():
        # Find students with inactive learning paths
        inactive_students = db.learning_paths.find({
            "progress.updated_at": {$lt: now() - 7 days},
            "progress.completion_percentage": {$lt: 100}
        })
        
        FOR each path in inactive_students:
            create_notification(
                user_id=path.student_id,
                type="learning_reminder",
                priority="medium",
                title="Continue your learning path",
                message=f"Your {path.skill} learning has been inactive for 7 days"
            )
    
    Method: check_achievements():
        # Check for recent profile improvements
        students = db.users.find({role: "student"})
        
        FOR each student:
            previous_score = get_score_from_7_days_ago(student)
            current_score = student.ai_profile.overall_score
            
            IF current_score - previous_score >= 10:
                create_notification(
                    user_id=student.id,
                    type="achievement",
                    priority="low",
                    title="🎉 Profile score improved!",
                    message=f"Your AI profile score increased by {current_score - previous_score} points"
                )
    
    Method: create_notification(user_id, type, priority, title, message, ...):
        notification = {
            user_id: user_id,
            type: type,
            priority: priority,
            title: title,
            message: message,
            created_at: now(),
            read_at: null
        }
        
        db.notifications.insert(notification)
        
        # Update user's unread count
        db.users.update(
            {_id: user_id},
            {$inc: {"notification_count": 1}}
        )
Day 5-6: Build Notification API & Delivery
Step 1: Create Notification Endpoints
What to do:

Create file: backend/routes/notifications.py

Endpoints:

1. GET /notifications/my

text
Purpose: Get user's notifications

Query params:
- unread_only (boolean)
- limit (default 20)
- type (optional filter)
- priority (optional filter)

Response:
{
    "status": "success",
    "notifications": [
        {notification object}
    ],
    "unread_count": 5,
    "total_count": 47
}
2. POST /notifications/{id}/mark-read

text
Purpose: Mark notification as read

Logic:
- Update read_at timestamp
- Decrement user's unread count
3. POST /notifications/mark-all-read

text
Purpose: Mark all as read

Logic:
- Update all unread notifications for user
- Reset unread count to 0
4. DELETE /notifications/{id}

text
Purpose: Dismiss/delete notification

Logic:
- Update dismissed_at timestamp
- Remove from active notifications list
5. GET /notifications/settings

text
Purpose: Get user's notification preferences

Response:
{
    "status": "success",
    "settings": {
        "opportunities": {
            "enabled": true,
            "min_score_threshold": 75,
            "frequency": "instant"
        },
        "deadlines": {
            "enabled": true,
            "advance_notice_days": 3
        },
        "learning": {
            "enabled": true,
            "reminder_frequency": "weekly"
        },
        "recruiter_activity": {
            "enabled": true
        }
    }
}
6. PUT /notifications/settings

text
Purpose: Update notification preferences

Body: {settings object}

Logic:
- Store in user profile
- Notification service respects these settings
Step 2: Add Real-time Delivery (Optional but Recommended)
What to do:

Add WebSocket support for real-time notifications

Concept:

text
When new notification created:
    IF user is online (connected via WebSocket):
        send_realtime_notification(user_id, notification)
    ELSE:
        notification will appear next time they check /notifications/my
Simple WebSocket flow (no code, just concept):

text
# Student opens app
Student → WebSocket Connect → Backend stores connection

# New notification triggered
Backend → Check if student online
IF online:
    Backend → Send notification via WebSocket → Student sees toast/badge
ELSE:
    Just store in DB
Day 7: Notification Scheduler & Polish
Step 1: Schedule Notification Jobs
What to do:
Add notification checks to scheduler:

text
Notification Schedule:
- check_opportunity_matches: Every 6 hours
- check_deadlines: Every 12 hours
- check_learning_reminders: Every 24 hours at 10 AM
- check_achievements: Every 24 hours at 8 PM
Step 2: Add Notification Batching (Prevent Spam)
What to do:
Group similar notifications to avoid overwhelming users:

text
FUNCTION batch_notifications():
    # Instead of 10 separate "new job match" notifications
    # Send 1 notification: "10 new jobs match your profile"
    
    pending_notifications = get_pending_notifications_for_user(user_id)
    
    # Group by type
    grouped = group_by_type(pending_notifications)
    
    FOR each type, notifications in grouped:
        IF len(notifications) > 3:
            # Create batch notification
            create_notification(
                type="batch",
                title=f"{len(notifications)} new {type} for you",
                message="View all in your feed",
                related_entities=notifications
            )
            
            # Mark individual ones as batched
            mark_as_batched(notifications)
        ELSE:
            # Send individually
            FOR notification in notifications:
                deliver(notification)
Step 3: Add Notification Analytics
What to do:
Track notification effectiveness:

text
Metrics to track:
- Delivery rate (created vs delivered)
- Open rate (delivered vs read)
- Click-through rate (read vs action clicked)
- Dismiss rate (read vs dismissed without action)
- Time to action (created → action taken)

Store in: `notification_analytics` collection

Use to:
- Identify which notification types work best
- Optimize timing (when do students engage most?)
- Adjust score thresholds
Week 3 Deliverables Summary
Component	Status	What's Built
Notification Rules	✅	5 trigger categories with logic
Notification Service	✅	Automated checking + creation
API Endpoints	✅	6 endpoints for full notification management
User Preferences	✅	Customizable notification settings
Batching Logic	✅	Prevent notification spam
Real-time Delivery	✅	WebSocket support (optional)
Analytics Tracking	✅	Measure notification effectiveness
Scheduler Integration	✅	Automated periodic checks
Module 4 Complete Integration (End of Week 3)
What you have built:
text
External Data (Week 1)
    ↓
Recommendation Engine (Week 2)
    ↓
Notification System (Week 3)
    ↓
Student sees personalized opportunities + timely alerts
How it connects to existing modules:
Module 1 (Profiles): Recommendations use AI profile scores

Module 2 (Matching): Jobs from Module 4 can trigger Module 2 matching

Module 3 (Learning): Learning gaps inform recommendations

Module 5 (Communication): Notifications trigger communication threads

Testing Checklist for Module 4
Week 1 Tests:
 Ingestion jobs run without errors

 Data normalized correctly (check random samples)

 Duplicates handled properly

 Expired opportunities cleaned up

Week 2 Tests:
 Recommendations return results for test student

 Scores make sense (high-match jobs rank higher)

 Filters work (location, stipend, etc.)

 Feedback tracking updates scores

Week 3 Tests:
 Notifications created for new high-match jobs

 Deadline reminders sent 3 days before

 Notifications marked read/dismissed correctly

 Batching prevents spam

 User preferences respected