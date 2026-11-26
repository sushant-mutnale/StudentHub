# =====================================================
# StudentHub - Complete Setup & Deployment Guide
# =====================================================

## What YOU Need to Do Manually (I Can't Do These)

### 1. Install Software on Your Computer
```bash
# Python 3.11+ (if not installed)
# Download from: https://www.python.org/downloads/

# Node.js 18+ (if not installed)
# Download from: https://nodejs.org/

# MongoDB (local development only)
# Download from: https://www.mongodb.com/try/download/community
```

### 2. Create Free Accounts & Get API Keys

| Service | Purpose | Where to Get |
|---------|---------|--------------|
| **MongoDB Atlas** | Database | https://cloud.mongodb.com |
| **Google AI (Gemini)** | AI Features | https://makersuite.google.com/app/apikey |
| **SendGrid** | Email | https://signup.sendgrid.com |
| **Upstash** (Optional) | Redis Cache | https://upstash.com |

---

## API Keys You Need to Provide

After creating accounts, give me these values:

```
MONGODB_URI = mongodb+srv://username:password@cluster.mongodb.net/
GOOGLE_API_KEY = AIza...your_key
SENDGRID_API_KEY = SG.your_key
OPENAI_API_KEY = sk-...your_key (optional)
REDIS_URL = redis://...your_url (optional)
```

---

## Step-by-Step Setup

### Step 1: Backend Virtual Environment

Open PowerShell in project folder and run:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Download NLP Models

After pip install, run:
```powershell
python -m spacy download en_core_web_sm
python -m nltk.downloader punkt stopwords wordnet
```

### Step 3: Update .env File

Copy `.env.example` to `.env` and fill in your values:
```powershell
copy .env.example .env
# Then edit .env with your API keys
```

### Step 4: Start MongoDB (Local)

If using local MongoDB:
```powershell
# Start MongoDB service (varies by installation)
# Or use MongoDB Compass to connect
```

### Step 5: Run Backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn backend.main:app --reload --port 8000
```

### Step 6: Frontend Setup

Open new terminal:
```powershell
cd frontend
npm install
npm run dev
```

---

## Deployment to Production

### Deploy Database (MongoDB Atlas)
1. Create free cluster at https://cloud.mongodb.com
2. Create database user
3. Get connection string
4. Allow connections from your backend host

### Deploy Backend and Frontend
1. Deploy the backend behind HTTPS with non-local MongoDB and Redis services.
2. Set these backend environment variables in your hosting environment:
   - `APP_ENV=production`
   - `JWT_SECRET=<strong random secret>`
   - `MONGODB_URI=<non-local MongoDB connection string>`
   - `REDIS_HOST=<non-local Redis host>`
   - `FRONTEND_ORIGIN=https://app.example.com`
3. Build the frontend with `npm run build` and serve `dist/` over HTTPS.
4. Set the frontend environment variable:
   - `VITE_API_URL=https://api.example.com`

Backend startup fails fast when production values use defaults or localhost services.

---

## After You Provide Keys

Once you give me the API keys, I will:
1. ✅ Update your .env file
2. ✅ Test all backend imports work
3. ✅ Verify API endpoints respond
4. ✅ Check frontend connects to backend
5. ✅ Run the test suite
6. ✅ Build production bundle

---

## Quick Checklist

| Item | Status |
|------|--------|
| Python 3.11+ installed | ⬜ |
| Node.js 18+ installed | ⬜ |
| MongoDB installed/running | ⬜ |
| MongoDB Atlas account | ⬜ |
| Google AI API key | ⬜ |
| SendGrid API key | ⬜ |
