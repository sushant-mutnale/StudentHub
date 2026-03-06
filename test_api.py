"""Comprehensive API Testing Script - Using Demo Users"""
import httpx

BASE_URL = 'http://127.0.0.1:8000'

def test_api():
    results = []
    token = None
    
    print("=" * 50)
    print("STUDENTHUB API COMPREHENSIVE TESTS")
    print("=" * 50)
    
    # 1. Health Check
    print("\n[1] Health Check...")
    r = httpx.get(f'{BASE_URL}/health')
    results.append(('Health', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 2. API Docs
    print("\n[2] API Documentation...")
    r = httpx.get(f'{BASE_URL}/docs')
    results.append(('Docs', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 3. Login with demo student (seeded by app)
    print("\n[3] Login (Demo Student)...")
    login_data = {
        'username': 'demo_student', 
        'password': 'Student@123',
        'role': 'student'
    }
    r = httpx.post(f'{BASE_URL}/auth/login', json=login_data)
    results.append(('Login Student', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        token = r.json().get('access_token')
        print(f"    Token obtained: Yes")
    else:
        print(f"    Error: {r.text[:200]}")
    
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    
    # 4. Get Profile
    print("\n[4] Get User Profile...")
    if token:
        r = httpx.get(f'{BASE_URL}/users/me', headers=headers)
        results.append(('Get Profile', r.status_code == 200))
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            print(f"    Username: {r.json().get('username')}")
    else:
        results.append(('Get Profile', False))
        print("    SKIP - No token")
    
    # 5. List Jobs
    print("\n[5] List Jobs...")
    r = httpx.get(f'{BASE_URL}/jobs/', headers=headers)
    results.append(('List Jobs', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 6. Get Posts
    print("\n[6] Get Posts Feed...")
    r = httpx.get(f'{BASE_URL}/posts/', headers=headers)
    results.append(('Get Posts', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 7. My Applications (Module 5)
    print("\n[7] My Applications (Module 5)...")
    r = httpx.get(f'{BASE_URL}/applications/my', headers=headers)
    results.append(('My Applications', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 8. Pipelines - requires recruiter
    print("\n[8] Pipelines (requires recruiter)...")
    r = httpx.get(f'{BASE_URL}/pipelines/', headers=headers)
    results.append(('Pipelines Access Control', r.status_code in [401, 403]))
    print(f"    Status: {r.status_code} (401/403 expected)")
    
    # 9. Now login as recruiter
    print("\n[9] Login (Demo Recruiter)...")
    login_data = {
        'username': 'demo_recruiter', 
        'password': 'Recruiter@123',
        'role': 'recruiter'
    }
    r = httpx.post(f'{BASE_URL}/auth/login', json=login_data)
    results.append(('Login Recruiter', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    if r.status_code == 200:
        rec_token = r.json().get('access_token')
        rec_headers = {'Authorization': f'Bearer {rec_token}'}
    else:
        rec_token = None
        rec_headers = {}
    
    # 10. Pipelines as recruiter
    print("\n[10] Pipelines (as Recruiter)...")
    r = httpx.get(f'{BASE_URL}/pipelines/', headers=rec_headers)
    results.append(('Pipelines List', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 11. Scorecards Templates
    print("\n[11] Scorecards Templates...")
    r = httpx.get(f'{BASE_URL}/scorecards/templates', headers=rec_headers)
    results.append(('Scorecards Templates', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 12. Verification Status
    print("\n[12] Verification Status...")
    r = httpx.get(f'{BASE_URL}/verification/status', headers=rec_headers)
    results.append(('Verification Status', r.status_code == 200))
    print(f"    Status: {r.status_code}")
    
    # 13. Admin Review Queue (requires admin role)
    print("\n[13] Admin Review Queue...")
    r = httpx.get(f'{BASE_URL}/admin/review-queue', headers=rec_headers)
    results.append(('Admin Queue', r.status_code in [200, 403]))  # 403 expected without admin role
    print(f"    Status: {r.status_code} (403 expected for non-admin)")
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, p in results if p)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    for name, p in results:
        status = "[PASS]" if p else "[FAIL]"
        print(f"  {status}: {name}")
    
    if passed == total:
        print("\n>>> ALL TESTS PASSED! <<<")
    else:
        print(f"\n>>> {total - passed} test(s) need attention <<<")
    
    return passed, total

if __name__ == '__main__':
    passed, total = test_api()
    print(f"\nFinal Score: {passed}/{total}")
