import asyncio
import os
import sys

# Add backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from services.resume_parser import resume_parser
from services.ai_resume_evaluator import ai_resume_evaluator
import json

async def main():
    pdf_path = "D:/python/project/StudentHub/Sushant_Mutnale.pdf"
    print(f"1. Parsing {pdf_path}...")
    
    # Parse the resume using existing functionality
    parsed_data = await resume_parser.parse_resume(pdf_path, use_ai_enhancement=False)
    
    if not parsed_data.get('success'):
        print(f"Parsing failed: {parsed_data.get('error')}")
        return
        
    print("Parsing successful. Extracted basic data.")
    print(f"Name: {parsed_data.get('contact', {}).get('name')}")
    print(f"Skills: {len(parsed_data.get('skills', []))} found")
    
    print("\n2. Running AI Profile Evaluator...")
    # Prepare data exactly as the endpoint does
    eval_data = {
        "contact": parsed_data.get("contact", {}),
        "skills": parsed_data.get("skills", []),
        "experience": parsed_data.get("experience", []),
        "education": parsed_data.get("education", []),
        "projects": parsed_data.get("projects", [])
    }
    
    feedback = await ai_resume_evaluator.evaluate_resume(eval_data, target_role="Software Engineer")
    
    if feedback:
        print("\n=== AI Feedback Successfully Generated ===")
        print(f"Summary: {feedback.get('summary')}\n")
        print(f"Overall Score: {feedback.get('rating', {}).get('overall')}")
        print("Breakdown:")
        for b in feedback.get("rating", {}).get("breakdown", []):
            print(f"  - {b.get('aspect')}: {b.get('score')}/{b.get('max')}")
            
        print("\nStrengths:")
        for s in feedback.get("strengths", []):
            print(f"  + {s.get('title')}: {s.get('description')}")
            
        print("\nIssues:")
        for i in feedback.get("issues", []):
            print(f"  - {i.get('title')}: {i.get('description')}")
            
        print("\nAction Plan:")
        for a in feedback.get("action_plan", []):
            print(f"  * {a}")
        print("==========================================")
    else:
        print("Failed to generate AI feedback.")

if __name__ == "__main__":
    asyncio.run(main())
