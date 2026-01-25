MODULE 3,  WEEK 2: STEP-BY-STEP 
: Resume Parsing Setup
Step 1: Understand PDF Resume Structure
What you need to know:

Resumes are PDFs with structured sections: Name, Contact, Skills, Experience, Education, Projects

You need to extract text from PDF → parse structured data

Skills appear as bullet points or comma-separated lists

Education/Experience have dates, companies, descriptions

What to do:

Download 5 sample resumes (ask your friends or use online templates)

Open them in a PDF viewer and manually note:

Where is the name? (usually top)

Where are skills? (usually middle, bullet points)

Where is experience? (companies, job titles, dates)

Where are projects? (if they exist)

This gives you the pattern you're looking for

Why this matters:
Every resume layout is different. You need to know the PATTERNS before coding.

Step 2: Choose PDF Parsing Library
Your options:

pdfplumber - Best for extracting structured text + tables. Easy to use.

PyPDF2 - Good for basic PDF handling

PyMuPDF (fitz) - Fast, handles complex PDFs

What to do:

Pick pdfplumber (it's the easiest for resume extraction)

Install it: pip install pdfplumber

Create a test script that:

Opens a sample resume PDF

Extracts all text

Prints the extracted text

Run it and see what you get

Why this matters:
You need to see the raw PDF output before you parse it. Text extraction is the foundation.

Step 3: Plan Resume Parsing Logic
What information to extract:

Name (usually top line)

Email (pattern: xxx@xxx.xxx)

Phone (pattern: xxx-xxx-xxxx or +91-xxxx)

Skills (bullet points with technical keywords)

Education (Degree, University, Year)

Experience (Company, Job Title, Dates, Description)

Projects (Project Name, Technologies, Description)

What to do:

Write down the extraction logic in plain English (no code):

"Split PDF text by sections (Skills, Experience, Education)"

"For Skills section, find lines with comma or bullet, split them"

"For Experience, look for date patterns (YYYY-YYYY)"

Draw a simple flowchart:

text
PDF → Extract Text → Split into Sections → Find each field → Store as JSON
Why this matters:
Before coding, understand the LOGIC. This prevents bugs later.

Step 4: Create Resume Parser Service (MongoDB + API)
What you're building:

A service that takes a PDF file path

Returns structured JSON with: name, skills, experience, education, projects

What to do:

Create a new file: backend/services/resume_parser.py

Inside this file, create a class ResumeParsingService with methods:

parse_resume_pdf() - Main method

extract_skills_section() - Find and parse skills

extract_experience_section() - Find and parse experience

extract_education_section() - Find and parse education

normalize_skills() - Clean up skill names (lowercase, trim spaces)

Don't use external resume parsing libraries yet — do it manually first so you understand what's happening

Why this matters:
You learn the parsing logic before relying on libraries.

Step 5: Create Resume Upload API Endpoint
What you're building:

An endpoint where students can upload resume PDF

Backend receives it, parses it, stores it in MongoDB

What to do:

Create a new route file: backend/routes/interview.py

Add an endpoint: POST /api/interview/upload-resume

This endpoint should:

Receive uploaded PDF file

Save it temporarily to disk

Call ResumeParsingService.parse_resume_pdf()

Store parsed data in MongoDB collection resume_uploads

Return the parsed data as JSON response

Delete the temporary file

MongoDB collection structure:

text
resume_uploads {
  student_id: "ObjectId",
  file_name: "resume.pdf",
  parsed_data: {
    name: "John Doe",
    email: "john@example.com",
    skills: ["Python", "React", "MongoDB"],
    experience: [...],
    education: [...],
    projects: [...]
  },
  uploaded_at: "2026-01-24T..."
}
Why this matters:
Now students can upload resumes → backend parses → stored in DB. Foundation ready.

Step 6: Test Resume Parsing (Manual Testing)
What to do:

Use Postman or curl to test the API:

text
POST /api/interview/upload-resume
File: your_resume.pdf
Check the response — did it extract:

✅ Your name?

✅ Your email?

✅ Your skills?

✅ Your experience?

If any field is missing or wrong, debug the parser

Why this matters:
Catch errors early. Fix before moving forward.