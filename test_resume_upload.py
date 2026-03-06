import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"
EMAIL = "test_ai_resume@example.com"
PASSWORD = "password123"

def get_token():
    # Try login first
    print("Logging in...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
    if resp.status_code == 200:
        return resp.json()["access_token"]
        
    print("Login failed, trying to register...")
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": EMAIL,
        "password": PASSWORD,
        "full_name": "Test User",
        "role": "student"
    })
    
    if resp.status_code in [200, 201]:
        print("Registration successful, logging in...")
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": EMAIL, "password": PASSWORD})
        return resp.json()["access_token"]
    
    print(f"Failed to get token: {resp.text}")
    sys.exit(1)

def main():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    pdf_path = "D:/python/project/StudentHub/Sushant_Mutnale.pdf"
    
    print(f"Uploading {pdf_path}...")
    with open(pdf_path, 'rb') as f:
        files = {'file': (pdf_path.split('/')[-1], f, 'application/pdf')}
        data = {'use_ai_enhancement': 'true'}
        resp = requests.post(f"{BASE_URL}/resume/upload", headers=headers, files=files, data=data)
        
    if resp.status_code == 200:
        print("\nUpload Successful!")
        result = resp.json()
        feedback = result.get("feedback")
        
        if feedback:
            print("\n--- AI Feedback Received ---")
            print(f"Summary: {feedback.get('summary')}")
            print(f"Overall Score: {feedback.get('rating', {}).get('overall')}")
            print("\nStrengths:")
            for s in feedback.get("strengths", []):
                print(f" - {s.get('title')}: {s.get('description')}")
            print("\nImprovements:")
            for i in feedback.get("issues", []):
                print(f" - {i.get('title')}: {i.get('description')}")
            print("\nAction Plan:")
            for a in feedback.get("action_plan", []):
                print(f" - {a}")
            print("----------------------------\n")
        else:
            print("SUCCESS: But no feedback field found in response.")
            print(json.dumps(result, indent=2)[:500] + "...")
    else:
        print(f"Upload Failed ({resp.status_code}): {resp.text}")

if __name__ == "__main__":
    main()
