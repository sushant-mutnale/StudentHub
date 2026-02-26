"""
Module 1 Test Script - Tests AI Profile & Skill Assessment services
"""
import requests
import os
import sys

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv("D:\\python\\project\\StudentHub\\backend\\.env")

# Add backend to path
sys.path.insert(0, "D:\\python\\project\\StudentHub")

BASE_URL = "http://127.0.0.1:8000"
RESUME_PATH = "D:\\python\\project\\StudentHub\\Sushant_Mutnale.pdf"

def test_health():
    """Test health endpoint"""
    print("=" * 50)
    print("Testing Health Endpoint...")
    r = requests.get(f"{BASE_URL}/health")
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
    return r.status_code == 200

def test_signup_and_login():
    """Create test user and login"""
    print("=" * 50)
    print("Testing User Signup and Login...")
    
    import asyncio
    from datetime import datetime
    from motor.motor_asyncio import AsyncIOMotorClient
    from passlib.context import CryptContext
    
    # Use same hashing as server
    pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        deprecated="auto",
        pbkdf2_sha256__default_rounds=390000,
    )
    
    # Create user directly in database (bypassing OTP)
    async def create_test_user():
        client = AsyncIOMotorClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
        db = client["student_hub"]
        
        password_hash = pwd_context.hash("Test@123456")
        
        user_data = {
            "email": "test_module1@example.com",
            "username": "test_module1",
            "password_hash": password_hash,
            "full_name": "Test Student",
            "role": "student",
            "prn": "PRN123456",
            "college": "Test University",
            "branch": "Computer Science",
            "year": "2024",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "ai_profile": {
                "overall_score": 0.0,
                "skill_score": 0.0,
                "learning_score": 0.0,
                "interview_score": 0.0,
                "activity_score": 0.0,
                "profile_completeness": 0.0,
                "last_computed_at": datetime.utcnow()
            }
        }
        
        # Delete existing and recreate
        await db.users.delete_one({"username": "test_module1"})
        result = await db.users.insert_one(user_data)
        print(f"Created user: {result.inserted_id}")
        
        client.close()
    
    # Run async code
    loop = asyncio.new_event_loop()
    loop.run_until_complete(create_test_user())
    loop.close()
    
    # Login
    login_data = {
        "username": "test_module1",
        "password": "Test@123456",
        "role": "student"
    }
    r = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    print(f"Login Status: {r.status_code}")
    if r.status_code == 200:
        token = r.json().get("access_token")
        print(f"Token obtained: {token[:20]}...")
        return token
    else:
        print(f"Login Error: {r.text[:200]}")
        return None

def test_resume_parser(token):
    """Test resume upload and parsing"""
    print("=" * 50)
    print("Testing Resume Parser...")
    
    if not os.path.exists(RESUME_PATH):
        print(f"Resume file not found: {RESUME_PATH}")
        return False
    
    headers = {"Authorization": f"Bearer {token}"}
    with open(RESUME_PATH, "rb") as f:
        files = {"file": ("Sushant_Mutnale.pdf", f, "application/pdf")}
        r = requests.post(
            f"{BASE_URL}/resume/upload",
            files=files,
            params={"use_ai_enhancement": True},
            headers=headers
        )
    
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Skills extracted: {data.get('skills', [])[:5]}...")
        print(f"Confidence: {data.get('confidence_score', 'N/A')}")
        return True
    else:
        print(f"Error: {r.text[:300]}")
        return False

def test_gap_analysis(token):
    """Test skill gap analysis"""
    print("=" * 50)
    print("Testing Gap Analysis...")
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "job_required_skills": ["python", "react", "mongodb", "docker", "kubernetes"],
        "job_nice_to_have_skills": ["redis", "graphql"],
        "use_ai_recommendations": True
    }
    r = requests.post(f"{BASE_URL}/learning/analyze-gap", json=payload, headers=headers)
    
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Match %: {data.get('match_percentage', 'N/A')}")
        print(f"Gaps: {data.get('gaps', [])[:3]}...")
        return True
    else:
        print(f"Error: {r.text[:300]}")
        return False

def test_user_profile(token):
    """Test getting and updating user profile"""
    print("=" * 50)
    print("Testing User Profile & AI Scoring...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get profile
    r = requests.get(f"{BASE_URL}/users/me", headers=headers)
    print(f"Get Profile Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Username: {data.get('username')}")
        print(f"AI Profile: {data.get('ai_profile')}")
    
    # Update with skills
    update_data = {
        "skills": [
            {"name": "python", "level": 85},
            {"name": "react", "level": 70},
            {"name": "mongodb", "level": 60}
        ],
        "bio": "Computer Science student passionate about full-stack development"
    }
    r = requests.put(f"{BASE_URL}/users/me", json=update_data, headers=headers)
    print(f"Update Profile Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Updated AI Profile: {data.get('ai_profile')}")
        return True
    else:
        print(f"Error: {r.text[:200]}")
        return False

def main():
    print("\n" + "=" * 60)
    print("MODULE 1: AI PROFILE & SKILL ASSESSMENT - TEST SUITE")
    print("=" * 60 + "\n")
    
    results = {}
    
    # Test 1: Health
    results["Health"] = test_health()
    
    # Test 2: Auth
    token = test_signup_and_login()
    results["Auth"] = token is not None
    
    if token:
        # Test 3: User Profile
        results["Profile"] = test_user_profile(token)
        
        # Test 4: Resume Parser
        results["Resume"] = test_resume_parser(token)
        
        # Test 5: Gap Analysis
        results["Gap Analysis"] = test_gap_analysis(token)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test}: {status}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

if __name__ == "__main__":
    main()
