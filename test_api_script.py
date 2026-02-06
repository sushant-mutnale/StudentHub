import requests
import time
import sys

BASE_URL = "http://127.0.0.1:8000"

def test_login():
    print(f"\n[TEST] Testing Login at {BASE_URL}/auth/login...")
    try:
        # Use credentials from seed_default_users in main.py
        payload = {
            "username": "demo_student",
            "password": "Student@123", # Password used in seed
            "role": "student"
        }
        res = requests.post(f"{BASE_URL}/auth/login", json=payload)
        
        if res.status_code == 200:
            print(f"[SUCCESS] Login Success! Status: {res.status_code}")
            return res.json()["access_token"]
        else:
            print(f"[FAILED] Login Failed! Status: {res.status_code}")
            print(f"Response: {res.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Login Error: {e}")
        return None

def test_forgot_password():
    print(f"\n[TEST] Testing Forgot Password at {BASE_URL}/auth/forgot-password...")
    try:
        # Use email corresponding to demo_student
        payload = {
            "email": "student@example.com",
            "purpose": "password_reset"
        }
        
        start_time = time.time()
        res = requests.post(f"{BASE_URL}/auth/forgot-password", json=payload)
        duration = time.time() - start_time
        
        if res.status_code == 200:
            print(f"[SUCCESS] Forgot Password Success! (Took {duration:.2f}s)")
            print(f"Response: {res.json()}")
        else:
            print(f"[FAILED] Forgot Password Failed! Status: {res.status_code}")
            print(f"Response: {res.text}")
            
    except Exception as e:
        print(f"[ERROR] Forgot Password Exception: {e}")

if __name__ == "__main__":
    # Wait for server to be ready
    print("Waiting for server to start...")
    for i in range(10):
        try:
            requests.get(f"{BASE_URL}/health")
            print("Server is up!")
            break
        except:
            time.sleep(1)
    else:
        print("Server failed to start in time.")
        sys.exit(1)

    token = test_login()
    if token:
        test_forgot_password()
