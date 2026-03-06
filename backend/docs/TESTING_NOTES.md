# Testing Notes - Module 3

This file tracks testing requirements for features that need manual testing or special setup.

---

## Week 2: Resume Parsing

### Dependencies Required
```bash
pip install pdfplumber PyMuPDF PyPDF2
```

### How to Test Resume Upload

1. **Start the backend server**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

2. **Test via Swagger UI**
   - Open: http://localhost:8000/docs
   - Navigate to `/resume/upload`
   - Click "Try it out"
   - Upload a PDF resume file
   - Check response for extracted data

3. **Test via curl**
   ```bash
   curl -X POST "http://localhost:8000/resume/upload" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@your_resume.pdf"
   ```

4. **Test with AI Enhancement**
   ```bash
   curl -X POST "http://localhost:8000/resume/upload?use_ai_enhancement=true" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -F "file=@your_resume.pdf"
   ```

### Expected Response Fields
- `contact`: name, email, phone, linkedin, github
- `skills`: List of extracted skills
- `experience`: List of work experiences with dates
- `education`: List of degrees with institutions
- `projects`: List of projects with technologies
- `parsing_confidence`: 0-100 score
- `ai_enhanced`: true/false

### Test Cases to Verify
- [ ] Upload PDF and verify name extraction
- [ ] Verify email pattern detection
- [ ] Verify skills extraction from bullet points
- [ ] Verify experience dates parsing
- [ ] Test duplicate upload rejection
- [ ] Test file size limit (> 5MB should fail)
- [ ] Test non-PDF file rejection
- [ ] Test AI enhancement improves confidence

---

## Week 1: Learning Paths & Course Search

### Dependencies Required
```bash
pip install aiohttp langchain langchain-openai langchain-community
```

### Environment Variables Needed
```env
OPENROUTER_API_KEY=...     # For LLM features
YOUTUBE_API_KEY=...        # For YouTube course search
APIFY_TOKEN=...            # For Udemy/Coursera/EdX scrapers
```

### How to Test Gap Analysis
```bash
curl -X POST "http://localhost:8000/learning/analyze-gap" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"current_skills": ["Python", "JavaScript"], "target_role": "Full Stack Developer"}'
```

### How to Test Course Search
```bash
curl -X POST "http://localhost:8000/courses/search" \
  -H "Content-Type: application/json" \
  -d '{"skill": "React", "providers": ["youtube", "local"]}'
```

---

## Week 3: Job Description Parsing

### How to Test JD Parsing

1. **Quick parse (no auth required)**
   ```bash
   curl -X POST "http://localhost:8000/jd/quick-parse?jd_text=Backend%20Engineer%20at%20Google...&use_ai=false"
   ```

2. **Full parse with auth**
   ```bash
   curl -X POST "http://localhost:8000/jd/parse" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"jd_text": "Job description here...", "use_ai_enhancement": false}'
   ```

3. **Save a JD**
   ```bash
   curl -X POST "http://localhost:8000/jd/save" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"jd_text": "Job description...", "job_url": "https://linkedin.com/jobs/..."}'
   ```

4. **Match skills between resume and JD**
   ```bash
   curl -X POST "http://localhost:8000/jd/match-skills" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"resume_id": "...", "jd_id": "..."}'
   ```

### Expected Response Fields
- `job_title`: Extracted job title
- `company`: Company name
- `required_skills`: Must-have skills
- `nice_to_have_skills`: Preferred skills
- `experience_level`: intern/entry/mid/senior/principal/manager
- `responsibilities`: List of duties
- `qualifications`: Required qualifications
- `salary_range`: {min, max, currency, period}
- `location`: {city, country, remote, hybrid}
- `parsing_confidence`: 0-100 score

### Test Cases to Verify
- [ ] Job title extraction from various formats
- [ ] Required vs nice-to-have skill separation
- [ ] Experience level detection (years patterns)
- [ ] Salary range parsing ($100k-150k, ₹15LPA, etc.)
- [ ] Remote/hybrid detection
- [ ] Skill normalization (ReactJS → React)
- [ ] Skill matching with resume

---

## Notes

- All API routes require authentication (JWT token)
- AI features fallback to rule-based if API keys not set
- Course search falls back to local resources if external APIs fail
