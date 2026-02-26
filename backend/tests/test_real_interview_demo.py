# -*- coding: utf-8 -*-
"""
Real-World Interview Demo
Simulates a complete interview session to test actual question quality and flow.
Run with: pytest backend/tests/test_real_interview_demo.py -v -s
"""

import pytest
import json
from .conftest import auth_headers


@pytest.mark.asyncio
async def test_full_amazon_sde_interview(client, student_user, student_token):
    """
    Simulate a complete Amazon SDE interview:
    1. Create session for Amazon Software Engineer
    2. Start interview and get first technical question
    3. Submit answers to 3 questions
    4. Get detailed feedback and report
    """
    
    print("\n" + "="*80)
    print("  DEMO: Amazon Software Engineer Interview")
    print("="*80)
    
    # Step 1: Create Session
    print("\n[CREATE] Creating interview session...")
    resp = await client.post(
        "/sessions/create",
        json={
            "company": "Amazon",
            "role": "Software Engineer",
            "jd_text": "We're looking for a Software Engineer to work on high-scale distributed systems. Must have strong knowledge of data structures, algorithms, and system design."
        },
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    
    print(f"[OK] Session created: {session_id}")
    print(f"   Company: {data['company']}")
    print(f"   Role: {data['role']}")
    print(f"   Total rounds: {data['total_rounds']}")
    print(f"   Rounds: {', '.join([r['name'] for r in data['rounds_preview']])}")
    
    # Step 2: Start Interview
    print("\n[START] Starting interview...")
    resp = await client.post(
        f"/sessions/{session_id}/start",
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    first_q = data["first_question"]
    
    print(f"\n[QUESTION 1] Round: {first_q['round']}")
    print(f"Difficulty: {first_q['difficulty']}")
    print(f"Question:")
    print(f"{first_q['question']}\n")
    if first_q.get('hints'):
        print(f"Hints available: {len(first_q['hints'])}")
    
    # Step 3: Submit first answer
    print(f"\n[SUBMIT] Submitting system design answer (480s)...")
    resp = await client.post(
        f"/sessions/{session_id}/submit-answer",
        json={
            "question_id": first_q["question_id"],
            "answer": """I would design this system using a microservices architecture with the following components:
            
1. API Gateway (Load Balancer)
   - Routes requests to appropriate services
   - Handles rate limiting and authentication
   -Uses Redis for distributed rate limiting
   
2. Inventory Service & Deal Management
   - Tracks deal inventory with atomic decrements
   - Implements optimistic locking to prevent overselling
   - Uses Redis cache for fast reads of active deals
   
3. Order/Claim Service
   - Manages deal claims and order creation  
   - Uses event-driven architecture (Kafka) for real-time updates
   - Implements idempotency for retries
   
4. Database Design
   - Use PostgreSQL for ACID transactions
   - Implement database sharding by deal_id for horizontal scaling
   - Read replicas for analytics queries
   
5. Queue System (Kafka/SQS)
   - Asynchronous claim processing to handle spikes
   - Event sourcing for claim state changes  
   
Key scalability considerations:
   - CAP theorem: Prioritize availability and partition tolerance (AP system)
   - Use circuit breakers for fault tolerance
   - Implement distributed tracing (Zipkin/Jaeger)
   - Pre-warm caches before deal starts
   - Use CDN for static assets""",
            "time_taken_seconds": 480
        },
        headers=auth_headers(student_token),
    )
    
    if resp.status_code == 200:
        evaluation = resp.json()["evaluation"]
        print(f"\n[EVALUATION]")
        print(f"   Score: {evaluation['score']}/100")
        if evaluation.get('feedback'):
            print(f"   Feedback: {evaluation['feedback']}\n")
        if evaluation.get('strengths'):
            print(f"   Strengths: {', '.join(evaluation['strengths'])}")
        if evaluation.get('improvements'):
            print(f"   Improvements: {', '.join(evaluation['improvements'])}")
    
    # Step 4: Get Status
    print("\n[STATUS] Getting final session status...")
    resp = await client.get(
        f"/sessions/{session_id}/status",
        headers=auth_headers(student_token),
    )
    
    if resp.status_code == 200:
        status = resp.json()
        print(f"\n[FINAL REPORT]")
        print(f"   Overall Score: {status.get('overall_score', 'N/A')}/100")
        print(f"   Questions Answered: {status.get('total_questions_answered', 0)}")
        print(f"   Session Status: {status.get('session_status', 'N/A')}")
    
    print("\n" + "="*80)
    print("  DEMO COMPLETED SUCCESSFULLY")
    print("="*80 + "\n")


@pytest.mark.asyncio  
async def test_multi_agent_conversation_demo(client, student_user, student_token):
    """
    Simulate a multi-agent AI interview with hints and career coaching.
    """
    
    print("\n" + "="*80)
    print("  DEMO: Multi-Agent AI Interview (Google L4)")
    print("="*80)
    
    # Start interview
    print("\n[START] Starting multi-agent interview...")
    resp = await client.post(
        "/agent-interview/start",
        json={
            "company": "Google",
            "role": "Software Engineer L4",
            "difficulty": "hard"
        },
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    session_id = data["session_id"]
    
    print(f"\n[INTERVIEWER] Says:")
    print(f"{data['interviewer_message']}\n")
    
    # Answer 1
    print(f"[ANSWER] Submitting answer...")
    resp = await client.post(
        "/agent-interview/answer",
        json={
            "session_id": session_id,
            "answer": "I would use dynamic programming with memoization. Create a DP table where dp[i][j] represents the solution for substring s[0:i] and pattern p[0:j]. Base cases: dp[0][0] = true, dp[i][0] = false for i > 0. For each cell, check if characters match or if pattern has wildcard."
        },
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    
    print(f"\n[EVALUATOR] Agent:")
    print(f"   Score: {data['evaluation']['score']}/100")
    print(f"   Feedback: {data['evaluation'].get('feedback', 'N/A')}\n")
    
    # Request hint
    print(f"[HINT] Requesting hint (Level 1)...")
    resp = await client.post(
        "/agent-interview/hint",
        json={"session_id": session_id, "level": 1},
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    
    print(f"\n[HINT PROVIDER] Agent:")
    print(f"   {data['hint']}")
    print(f"   Score Penalty: {data['score_penalty']}\n")
    
    # End interview
    print(f"[END] Ending interview...")
    resp = await client.post(
        "/agent-interview/end",
        json={"session_id": session_id},
        headers=auth_headers(student_token),
    )
    
    assert resp.status_code == 200
    data = resp.json()
    
    print(f"\n[CAREER COACH] Agent:")
    print(f"   Final Score: {data['final_score']}/100")
    print(f"   Questions Answered: {data['questions_answered']}")
    print(f"   Hints Used: {data['hints_used']}")
    print(f"\n   Coaching:")
    print(f"   {data['career_coaching']}\n")
    
    print("\n" + "="*80)
    print("  DEMO COMPLETED SUCCESSFULLY")
    print("="*80 + "\n")
