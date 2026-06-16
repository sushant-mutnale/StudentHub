import os
import pytest
import asyncio
from bson import ObjectId
from unittest.mock import patch, MagicMock

from backend.database import get_database
from backend.services.resume_parser import resume_parser
from backend.routes.resume_routes import resumes_collection, resume_cache_collection, parse_resume_background_task
from .conftest import auth_headers


# Path to a real sample PDF in the workspace
SAMPLE_PDF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Sushant_Mutnale.pdf"))


@pytest.mark.asyncio
async def test_resume_parser_hashing():
    """Verify SHA-256 hashing works for bytes and files."""
    dummy_content = b"Hello world parsed resume content"
    hash_bytes = resume_parser.get_file_hash_from_bytes(dummy_content)
    assert len(hash_bytes) == 64  # SHA-256 hash length is 64 characters hex
    
    # Check consistency
    assert hash_bytes == resume_parser.get_file_hash_from_bytes(dummy_content)


@pytest.mark.asyncio
async def test_resume_upload_and_background_parsing(client, student_user, student_token):
    """Verify file upload accepts processing state and runs background task."""
    db = get_database()
    
    # Ensure sample PDF exists
    assert os.path.exists(SAMPLE_PDF_PATH), f"Sample PDF not found at {SAMPLE_PDF_PATH}"
    
    with open(SAMPLE_PDF_PATH, "rb") as f:
        file_bytes = f.read()
        
    # Send upload request
    resp = await client.post(
        "/resume/upload",
        files={"file": ("Sushant_Mutnale.pdf", file_bytes, "application/pdf")},
        headers=auth_headers(student_token)
    )
    
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] in ("processing", "completed")
    resume_id = data["resume_id"]
    assert resume_id is not None
    
    # Check current status in DB
    doc = await resumes_collection().find_one({"_id": ObjectId(resume_id)})
    
    # If it was processing, run the background task manually to complete it
    if doc["status"] == "processing":
        # Invoke background task manually
        await parse_resume_background_task(
            resume_id=resume_id,
            file_path=doc["file_path"],
            file_hash=doc["file_hash"],
            use_ai_enhancement=False,
            student_id=str(student_user["_id"])
        )
        # Fetch updated doc
        doc = await resumes_collection().find_one({"_id": ObjectId(resume_id)})
        
    assert doc["status"] == "completed"
    
    # Query details to verify it is completed
    detail_resp = await client.get(
        f"/resume/{resume_id}",
        headers=auth_headers(student_token)
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail_data = detail_resp.json()
    assert detail_data["status"] == "completed"
    assert detail_data["id"] == resume_id
    
    # Check database cache has the hash registered
    cache_doc = await resume_cache_collection().find_one({"file_hash": doc["file_hash"]})
    assert cache_doc is not None


@pytest.mark.asyncio
async def test_resume_cache_hit(client, student_user, student_token):
    """Verify subsequent upload of identical file hits cache instantly."""
    db = get_database()
    
    with open(SAMPLE_PDF_PATH, "rb") as f:
        file_bytes = f.read()
    
    file_hash = resume_parser.get_file_hash_from_bytes(file_bytes)
    
    # Seed cache record
    cache_record = {
        "file_hash": file_hash,
        "parsed_data": {
            "contact": {"name": "Seeded Candidate", "email": "seed@candidate.com"},
            "skills": ["Python", "OCR", "FastAPI"],
            "experience": [],
            "education": [],
            "projects": []
        },
        "feedback": {
            "overall_score": 85.0,
            "category_scores": {"skills": 90.0},
            "executive_summary": "Highly skilled candidate"
        },
        "raw_text": "Sample candidate text",
        "parsing_confidence": 92.5,
        "ai_enhanced": False,
        "extraction_method": "pdfplumber",
        "created_at": None
    }
    
    # Correct datetime reference
    from datetime import datetime
    cache_record["created_at"] = datetime.utcnow()
    
    await resume_cache_collection().insert_one(cache_record)
    
    # Upload same file
    resp = await client.post(
        "/resume/upload",
        files={"file": ("Sushant_Mutnale.pdf", file_bytes, "application/pdf")},
        headers=auth_headers(student_token)
    )
    
    assert resp.status_code == 200, resp.text
    data = resp.json()
    
    # Assert cache hit completed immediately
    assert data["status"] == "completed"
    assert data["contact"]["name"] == "Seeded Candidate"
    assert data["contact"]["email"] == "seed@candidate.com"
    assert "OCR" in data["extracted_skills"]
    assert data["overall_score"] == 85.0
    
    # Check user skills merged (skill names are lowercased in user profile update)
    user = await db["users"].find_one({"_id": student_user["_id"]})
    user_skills = [s.get("name", "").lower() if isinstance(s, dict) else str(s).lower() for s in user.get("skills", [])]
    assert "ocr" in user_skills or "OCR" in user_skills


@pytest.mark.asyncio
async def test_ocr_fallback_trigger():
    """Test the validation and trigger flow of OCR fallback."""
    # Test valid vs invalid text density
    valid_text = "This is a normal resume text containing technical skills like Python, Java, and React. Work experience at Google."
    invalid_text = "123 \n 456 \n 789 \n"
    
    # is_text_valid expects a reasonable alphabetic character count and percentage
    assert resume_parser.is_text_valid(valid_text) is True
    assert resume_parser.is_text_valid(invalid_text) is False
    
    # Mock extract_text_ocr to verify it gets called when text is invalid
    with patch.object(resume_parser, "extract_text_pdfplumber", return_value=""), \
         patch.object(resume_parser, "extract_text_pymupdf", return_value=""), \
         patch.object(resume_parser, "extract_text_ocr", return_value="OCR Mock Text") as mock_ocr:
         
         text, method = resume_parser.extract_text("dummy_path.pdf")
         assert text == "OCR Mock Text"
         assert method == "tesseract_ocr"
         mock_ocr.assert_called_once_with("dummy_path.pdf")
