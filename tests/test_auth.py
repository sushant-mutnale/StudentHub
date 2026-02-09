import pytest
from fastapi.testclient import TestClient
from faker import Faker

fake = Faker()

def test_signup_student(client: TestClient):
    """Test successful student registration."""
    payload = {
        "email": fake.email(),
        "username": fake.user_name(), 
        "password": "StrongPassword123!",
        "role": "student",
        "full_name": fake.name(),
        "prn": "PRN12345",
        "college": "Test College",
        "branch": "CS",
        "year": "2024",
        "otp": "123456"
    }
    response = client.post("/auth/signup/student", json=payload)
    if response.status_code != 200:
        pytest.fail(f"Signup failed: {response.text}")
    assert response.status_code == 200 # Returns UserPublic on success, check status code definition (usually 200 or 201)
    data = response.json()
    assert "id" in data
    assert data["email"] == payload["email"]
    assert data["role"] == "student"

def test_signup_duplicate_email(client: TestClient):
    """Test signup with existing email fails."""
    email = fake.email()
    payload = {
        "email": email,
        "username": fake.user_name(),
        "password": "pass",
        "role": "student",
        "full_name": "Test User",
        "prn": "PRN999",
        "college": "Test U",
        "branch": "IT",
        "year": "2025",
        "otp": "123456"
    }
    # First signup
    client.post("/auth/signup/student", json=payload)
    
    # Second signup
    response = client.post("/auth/signup/student", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_success(client: TestClient):
    """Test login gets valid token."""
    # Register
    email = fake.email()
    password = "MyPassword123"
    username = fake.user_name()
    client.post("/auth/signup/student", json={
        "email": email, 
        "username": username,
        "password": password,
        "role": "student",
        "full_name": "Login Test",
        "prn": "PRN555",
        "college": "Login U",
        "branch": "Login Branch",
        "year": "2026",
        "otp": "123456"
    })
    
    # Login
    response = client.post("/auth/login", json={
        "username": username,
        "password": password,
        "role": "student"
    }) 
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    """Test login with wrong password fails."""
    response = client.post("/auth/login", json={
        "username": "wronguser",
        "password": "wrongpassword",
        "role": "student"
    })
    assert response.status_code == 401

def test_access_protected_route_without_token(client: TestClient):
    """Test accessing protected route returns 401."""
    response = client.get("/users/me")
    assert response.status_code == 401
