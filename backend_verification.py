import requests
import json
import random
import string

import sys

# Redirect stdout to file
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("verification_report.txt", "w", encoding='utf-8')
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger()

BASE_URL = "http://127.0.0.1:8000"

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent, default=str)[:500])  # Limit to 500 chars

def run_verification():
    print("🚀 Starting ENHANCED Backend Verification...")
    print("=" * 70)
    
    # 1. Login (using existing user)
    username = "sushantmutnale512@gmail.com"
    password = "Sushant@512"
    
    print(f"\n[1] AUTHENTICATION - Login")
    print("-" * 70)
    token = None
    try:
        response = requests.post(f"{BASE_URL}/auth/login", json={
            "username": username,
            "password": password,
            "role": "student"
        })
        if response.status_code == 200:
            data = response.json()
            token = data["access_token"]
            print("✅ Status: SUCCESS")
            print(f"📊 Response Data:")
            print(f"   - Token: {token[:20]}...")
            print(f"   - User ID: {data.get('user', {}).get('id')}")
            print(f"   - Username: {data.get('user', {}).get('username')}")
            print(f"   - Email: {data.get('user', {}).get('email')}")
            print(f"   - Role: {data.get('user', {}).get('role')}")
            
            # Validation
            if not token or len(token) < 20:
                print("❌ VALIDATION FAILED: Invalid token")
            if not data.get('user'):
                print("❌ VALIDATION FAILED: No user data in response")
        else:
            print(f"❌ Status: FAILED ({response.status_code})")
            print(f"   Error: {response.text}")
            return
    except Exception as e:
        print(f"❌ Exception: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # 2. User Profile
    print(f"\n[2] USER PROFILE - Fetch & Update")
    print("-" * 70)
    try:
        response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        if response.status_code == 200:
            profile = response.json()
            print("✅ Status: SUCCESS")
            print(f"📊 Profile Data:")
            print(f"   - ID: {profile.get('id')}")
            print(f"   - Full Name: {profile.get('full_name')}")
            print(f"   - College: {profile.get('college')}")
            print(f"   - Branch: {profile.get('branch')}")
            print(f"   - Skills: {profile.get('skills', [])[:5]}")  # First 5 skills
            print(f"   - Bio: {profile.get('bio', 'N/A')[:50]}...")
            
            # Validation
            if not profile.get('id'):
                print("❌ VALIDATION FAILED: No user ID")
            if not profile.get('email'):
                print("❌ VALIDATION FAILED: No email")
                
            # Update Profile
            print(f"\n   Testing Profile Update...")
            new_skill_name = f"Backend_{generate_random_string(3)}"
            current_skills = profile.get("skills", [])
            
            # Format skills as list of dicts (SkillSchema)
            new_skills_list = []
            for s in current_skills:
                 if isinstance(s, dict):
                     new_skills_list.append(s) # Keep existing
            
            # Add new skill
            new_skills_list.append({
                "name": new_skill_name,
                "level": 1,
                "proficiency": "Beginner",
                "confidence": 50
            })
            
            update_payload = {"skills": new_skills_list}
                
            update_response = requests.put(f"{BASE_URL}/users/me", headers=headers, json=update_payload)
            if update_response.status_code == 200:
                updated = update_response.json()
                print(f"   ✅ Profile Update Success")
                print(f"   - Added Skill: {new_skill_name}")
                print(f"   - Total Skills: {len(updated.get('skills', []))}")
            else:
                print(f"   ❌ Update Failed: {update_response.status_code}")
                print(f"   Error: {update_response.text}")
        else:
            print(f"❌ Status: FAILED ({response.status_code})")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # 3. Jobs
    print(f"\n[3] JOBS - List & Apply")
    print("-" * 70)
    job_id = None
    try:
        response = requests.get(f"{BASE_URL}/jobs?limit=3", headers=headers)
        if response.status_code == 200:
            jobs = response.json()
            print(f"✅ Status: SUCCESS")
            print(f"📊 Jobs Data ({len(jobs)} jobs found):")
            for i, job in enumerate(jobs[:3], 1):
                print(f"\n   Job {i}:")
                print(f"   - ID: {job.get('id')}")
                print(f"   - Title: {job.get('title')}")
                print(f"   - Company: {job.get('company_name')}")
                print(f"   - Location: {job.get('location')}")
                print(f"   - Skills: {job.get('skills_required', [])[:3]}")
                
                # Validation
                if not job.get('id') or not job.get('title'):
                    print(f"   ❌ VALIDATION FAILED: Missing critical job data")
            
            if jobs:
                job_id = jobs[0]["id"]
                # Check if already applied? 
                # We can't check explicitly without another endpoint, 
                # but applied status code handles it.
                
                print(f"\n   Testing Job Application (Job: {jobs[0].get('title')})...")
                app_response = requests.post(
                    f"{BASE_URL}/jobs/{job_id}/apply",
                    headers=headers,
                    json={"message": "I am interested in this role."}
                )
                if app_response.status_code in [200, 201]:
                    app_data = app_response.json()
                    print(f"   ✅ Application Success")
                    print(f"   - Application ID: {app_data.get('id')}")
                    print(f"   - Student ID: {app_data.get('student_id')}")
                elif "already" in app_response.text.lower():
                    print(f"   ℹ️ Already Applied")
                else:
                    print(f"   ❌ Application Failed: {app_response.status_code}")
        else:
            print(f"❌ Status: FAILED ({response.status_code})")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # 4. Voice Interview (AI)
    print(f"\n[4] VOICE INTERVIEW (AI) - Create Session")
    print("-" * 70)
    try:
        response = requests.post(f"{BASE_URL}/api/voice/session/create", headers=headers, json={
            "company": "TechCorp",
            "role": "Backend Developer",
            "interview_type": "session"
        })
        if response.status_code == 200:
            data = response.json()
            print("✅ Status: SUCCESS")
            print(f"📊 Voice Session Data:")
            print(f"   - Session ID: {data.get('session_id')}")
            print(f"   - Status: {data.get('status')}")
            print(f"   - Question: {data.get('question', 'N/A')[:100]}...")
            print(f"   - Audio URL: {data.get('audio_url', 'N/A')[:50]}...")
            print(f"   - Interview State: {data.get('interview_state', {})}")
            
            # Validation
            if not data.get('session_id'):
                print("❌ VALIDATION FAILED: No session ID")
            if not data.get('question') and not data.get('audio_url'):
                print("❌ VALIDATION FAILED: No question or audio provided")
        else:
            print(f"❌ Status: FAILED ({response.status_code})")
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # 5. Learning Path (AI)
    print(f"\n[5] LEARNING PATH (AI) - Generate Path")
    print("-" * 70)
    try:
        # Get student ID from profile data or token
        student_id = data.get('user', {}).get('id')
        if not student_id:
             # Try to decode token or just use the one we got from login response
             # We should have stored it. 
             # Let's use the one from login response 'data' which is in scope? 
             # No, 'data' variable is reused.
             # We need to save user_id from login.
             pass
        
        # Actually, let's just grab it from login 'data' variable if we can or fetch me `profile['id']`
        # profile variable is from [2].
        if 'profile' in locals() and profile.get('id'):
            student_id = profile.get('id')
        else:
            print("⚠️ Warning: Could not find student_id for learning path request")
            student_id = "unknown"

        response = requests.post(f"{BASE_URL}/learning/generate-path", headers=headers, json={
            "student_id": student_id,
            "gaps": [
                {"skill": "FastAPI", "current_level": 1, "target_level": 3, "priority": "high", "reason": "Job requirement"},
                {"skill": "Docker", "current_level": 1, "target_level": 2, "priority": "medium", "reason": "Infrastructure skill"}
            ]
        })
        if response.status_code == 200:
            data = response.json()
            print("✅ Status: SUCCESS")
            print(f"📊 Learning Path Data:")
            print(f"   - Total Paths: {len(data.get('learning_paths', []))}")
            print(f"   - Estimated Weeks: {data.get('total_estimated_weeks')}")
            print(f"   - AI Powered Paths: {data.get('ai_powered_paths')}")
            
            for i, path in enumerate(data.get('learning_paths', [])[:2], 1):
                print(f"\n   Path {i} ({path.get('skill')}):")
                print(f"   - ID: {path.get('id')}")
                print(f"   - Current → Target: Level {path.get('current_level')} → {path.get('target_level')}")
                print(f"   - Priority: {path.get('gap_priority')}")
                print(f"   - Stages: {len(path.get('stages', []))}")
                print(f"   - Completion: {path.get('progress', {}).get('completion_percentage', 0)}%")
                print(f"   - AI Powered: {path.get('ai_powered')}")
                if path.get('ai_advice'):
                    print(f"   - AI Advice: {path.get('ai_advice')[:80]}...")
                
                # Show first stage
                stages = path.get('stages', [])
                if stages:
                    stage1 = stages[0]
                    print(f"   - Stage 1: {stage1.get('title', 'N/A')}")
                    print(f"     Resources: {len(stage1.get('resources', []))} items")
            
            # Validation
            if not data.get('learning_paths'):
                print("❌ VALIDATION FAILED: No learning paths generated")
            for path in data.get('learning_paths', []):
                if not path.get('stages') or len(path.get('stages', [])) == 0:
                    print(f"❌ VALIDATION FAILED: Path '{path.get('skill')}' has no stages")
        else:
            print(f"❌ Status: FAILED ({response.status_code})")
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        
    print("\n" + "=" * 70)
    print("🏁 ENHANCED VERIFICATION COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    run_verification()
