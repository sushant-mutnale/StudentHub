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

## Notes

- All API routes require authentication (JWT token)
- AI features fallback to rule-based if API keys not set
- Course search falls back to local resources if external APIs fail
