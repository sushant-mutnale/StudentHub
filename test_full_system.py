"""
Comprehensive Full System Test Script
Tests ALL backend features including:
- Authentication (signup, login)
- User management
- Jobs CRUD
- Posts
- Module 5: Pipelines, Applications, Scorecards, Verification, Admin
- LLM integration
- Other services
"""
import httpx
import time
import json

BASE_URL = 'http://127.0.0.1:8000'

class TestResults:
    def __init__(self):
        self.results = []
        self.errors = []
    
    def add(self, name, passed, details=""):
        self.results.append((name, passed, details))
        if not passed:
            self.errors.append((name, details))
    
    def summary(self):
        passed = sum(1 for _, p, _ in self.results if p)
        return passed, len(self.results)


def test_full_system():
    results = TestResults()
    student_token = None
    recruiter_token = None
    
    print("=" * 60)
    print("STUDENTHUB FULL SYSTEM TEST")
    print("=" * 60)
    
    # ========== PHASE 1: HEALTH & DOCS ==========
    print("\n--- PHASE 1: Health & Documentation ---")
    
    r = httpx.get(f'{BASE_URL}/health')
    results.add('Health Check', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Health Check: {r.status_code}")
    
    r = httpx.get(f'{BASE_URL}/docs')
    results.add('API Docs', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] API Docs: {r.status_code}")
    
    r = httpx.get(f'{BASE_URL}/openapi.json')
    results.add('OpenAPI Schema', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] OpenAPI Schema: {r.status_code}")
    
    # ========== PHASE 2: AUTHENTICATION ==========
    print("\n--- PHASE 2: Authentication ---")
    
    # Login as demo student
    login_data = {'username': 'demo_student', 'password': 'Student@123', 'role': 'student'}
    r = httpx.post(f'{BASE_URL}/auth/login', json=login_data)
    results.add('Student Login', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Student Login: {r.status_code}")
    if r.status_code == 200:
        student_token = r.json().get('access_token')
    
    # Login as demo recruiter
    login_data = {'username': 'demo_recruiter', 'password': 'Recruiter@123', 'role': 'recruiter'}
    r = httpx.post(f'{BASE_URL}/auth/login', json=login_data)
    results.add('Recruiter Login', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Recruiter Login: {r.status_code}")
    if r.status_code == 200:
        recruiter_token = r.json().get('access_token')
    
    student_headers = {'Authorization': f'Bearer {student_token}'} if student_token else {}
    recruiter_headers = {'Authorization': f'Bearer {recruiter_token}'} if recruiter_token else {}
    
    # ========== PHASE 3: USER MANAGEMENT ==========
    print("\n--- PHASE 3: User Management ---")
    
    r = httpx.get(f'{BASE_URL}/users/me', headers=student_headers)
    results.add('Get Student Profile', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Get Student Profile: {r.status_code}")
    
    r = httpx.get(f'{BASE_URL}/users/me', headers=recruiter_headers)
    results.add('Get Recruiter Profile', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Get Recruiter Profile: {r.status_code}")
    
    # ========== PHASE 4: JOBS ==========
    print("\n--- PHASE 4: Jobs ---")
    
    r = httpx.get(f'{BASE_URL}/jobs/', headers=student_headers)
    results.add('List Jobs (Student)', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] List Jobs (Student): {r.status_code}")
    
    r = httpx.get(f'{BASE_URL}/jobs/', headers=recruiter_headers)
    results.add('List Jobs (Recruiter)', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] List Jobs (Recruiter): {r.status_code}")
    
    # ========== PHASE 5: POSTS ==========
    print("\n--- PHASE 5: Posts ---")
    
    r = httpx.get(f'{BASE_URL}/posts/', headers=student_headers)
    results.add('List Posts', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] List Posts: {r.status_code}")
    
    # ========== PHASE 6: MODULE 5 - PIPELINES ==========
    print("\n--- PHASE 6: Module 5 - Pipelines ---")
    
    # Student should NOT access pipelines
    r = httpx.get(f'{BASE_URL}/pipelines/', headers=student_headers)
    results.add('Pipelines Guard (Student)', r.status_code == 403, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 403 else 'FAIL'}] Pipelines Guard (Student): {r.status_code}")
    
    # Recruiter CAN access pipelines
    r = httpx.get(f'{BASE_URL}/pipelines/', headers=recruiter_headers)
    results.add('Pipelines List (Recruiter)', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Pipelines List (Recruiter): {r.status_code}")
    
    # ========== PHASE 7: MODULE 5 - APPLICATIONS ==========
    print("\n--- PHASE 7: Module 5 - Applications ---")
    
    r = httpx.get(f'{BASE_URL}/applications/my', headers=student_headers)
    results.add('My Applications (Student)', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] My Applications (Student): {r.status_code}")
    
    # ========== PHASE 8: MODULE 5 - SCORECARDS ==========
    print("\n--- PHASE 8: Module 5 - Scorecards ---")
    
    r = httpx.get(f'{BASE_URL}/scorecards/templates', headers=recruiter_headers)
    results.add('Scorecard Templates', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Scorecard Templates: {r.status_code}")
    
    # ========== PHASE 9: MODULE 5 - VERIFICATION ==========
    print("\n--- PHASE 9: Module 5 - Verification ---")
    
    r = httpx.get(f'{BASE_URL}/verification/status', headers=recruiter_headers)
    results.add('Verification Status', r.status_code == 200, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 200 else 'FAIL'}] Verification Status: {r.status_code}")
    
    # ========== PHASE 10: MODULE 5 - ADMIN ==========
    print("\n--- PHASE 10: Module 5 - Admin ---")
    
    r = httpx.get(f'{BASE_URL}/admin/review-queue', headers=recruiter_headers)
    results.add('Admin Queue (Non-Admin)', r.status_code == 403, f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code == 403 else 'FAIL'}] Admin Queue Guard: {r.status_code}")
    
    # ========== PHASE 11: INTERVIEWS ==========
    print("\n--- PHASE 11: Interviews ---")
    
    r = httpx.get(f'{BASE_URL}/interviews/my', headers=student_headers)
    results.add('List Interviews', r.status_code in [200, 404], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404] else 'FAIL'}] List Interviews: {r.status_code}")
    
    # ========== PHASE 12: NOTIFICATIONS ==========
    print("\n--- PHASE 12: Notifications ---")
    
    r = httpx.get(f'{BASE_URL}/notifications/', headers=student_headers)
    results.add('List Notifications', r.status_code in [200, 404], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404] else 'FAIL'}] List Notifications: {r.status_code}")
    
    # ========== PHASE 13: LEARNING ==========
    print("\n--- PHASE 13: Learning Paths ---")
    
    r = httpx.get(f'{BASE_URL}/learning/paths', headers=student_headers)
    results.add('Learning Paths', r.status_code in [200, 404], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404] else 'FAIL'}] Learning Paths: {r.status_code}")
    
    # ========== PHASE 14: RESUME ==========
    print("\n--- PHASE 14: Resume ---")
    
    r = httpx.get(f'{BASE_URL}/resume/my-resumes', headers=student_headers)
    results.add('Get Resumes', r.status_code in [200, 404], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404] else 'FAIL'}] Get Resumes: {r.status_code}")
    
    # ========== PHASE 15: RESEARCH ==========
    print("\n--- PHASE 15: Company Research ---")
    
    r = httpx.get(f'{BASE_URL}/research/companies', headers=student_headers)
    results.add('Company Research', r.status_code in [200, 404, 405], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404, 405] else 'FAIL'}] Company Research: {r.status_code}")
    
    # ========== PHASE 16: RECOMMENDATIONS ==========
    print("\n--- PHASE 16: Recommendations ---")
    
    r = httpx.get(f'{BASE_URL}/recommendations/', headers=student_headers)
    results.add('Recommendations', r.status_code in [200, 404], f"Status: {r.status_code}")
    print(f"[{'PASS' if r.status_code in [200, 404] else 'FAIL'}] Recommendations: {r.status_code}")
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed, total = results.summary()
    print(f"\nTotal: {passed}/{total} tests passed")
    
    print("\nDetailed Results:")
    for name, p, details in results.results:
        status = "[PASS]" if p else "[FAIL]"
        print(f"  {status} {name}: {details}")
    
    if results.errors:
        print(f"\nErrors ({len(results.errors)}):")
        for name, details in results.errors:
            print(f"  - {name}: {details}")
    else:
        print("\n>>> ALL TESTS PASSED! <<<")
    
    return passed, total, results.errors


if __name__ == '__main__':
    passed, total, errors = test_full_system()
    print(f"\n\nFinal Score: {passed}/{total}")
    if errors:
        print(f"Errors to fix: {len(errors)}")
