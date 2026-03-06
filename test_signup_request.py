import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
EMAIL = "sush512mutnale+v2@gmail.com"
USERNAME = "sush512_v2"
PASSWORD = "Student@123"

def signup():
    print(f"\n[STEP 1] Signing up {EMAIL}...")
    payload = {
        "role": "student",
        "username": USERNAME,
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Test User",
        "prn": "TEST001",
        "college": "Test College",
        "branch": "CS",
        "year": "4th Year",
        "skills": []
    }
    try:
        res = requests.post(f"{BASE_URL}/auth/signup/student", json=payload)
        if res.status_code == 200:
            print("[SUCCESS] Signup Successful!")
            return True
        elif res.status_code == 400 and "already exists" in res.text:
            print("[INFO] User already exists, proceeding to login.")
            return True
        else:
            print(f"[FAILED] Signup Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Signup Exception: {e}")
        return False

def login():
    print(f"\n[STEP 2] Logging in as {USERNAME}...")
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "role": "student"
    }
    try:
        res = requests.post(f"{BASE_URL}/auth/login", json=payload)
        if res.status_code == 200:
            print("[SUCCESS] Login Successful!")
            return True
        else:
            print(f"[FAILED] Login Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Login Exception: {e}")
        return False

def request_forgot_password():
    print(f"\n[STEP 3] Requesting Password Reset OTP for {EMAIL}...")
    payload = {
        "email": EMAIL,
        "purpose": "password_reset"
    }
    try:
        res = requests.post(f"{BASE_URL}/auth/forgot-password", json=payload)
        if res.status_code == 200:
            print("[SUCCESS] OTP Request Sent! Please check your email.")
            return True
        else:
            print(f"[FAILED] OTP Request Failed: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        print(f"[ERROR] OTP Request Exception: {e}")
        return False

if __name__ == "__main__":
    if signup():
        if login():
            request_forgot_password()
