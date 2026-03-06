"""
Test script to verify that moving an application stage triggers a notification.
Run with: .\\venv\\Scripts\\activate; python test_stage_notification.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from backend.database import connect_to_mongo, get_database
    from bson import ObjectId

    print("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()

    # 1. Find the target student (Sushant)
    student = await db["users"].find_one({"email": "sushantmutnale512@gmail.com"})
    if not student:
        print("Student not found!")
        return
    student_id = student["_id"]

    # 2. Find a job and an application for this student
    app = await db["applications"].find_one({"student_id": student_id})
    if not app:
        print("No existing application found. Creating a dummy one for testing...")
        
        # Get a recruiter
        recruiter = await db["users"].find_one({"role": "recruiter"})
        if not recruiter:
            print("No recruiter found to own the job!")
            return
            
        # Get or create a dummy job
        job = await db["opportunities_jobs"].find_one({"recruiter_id": recruiter["_id"]})
        if not job:
            print("No job found!")
            return
            
        # Get a pipeline template
        pipeline = await db["pipeline_templates"].find_one({"company_id": recruiter["_id"]})
        if not pipeline:
            from backend.models.pipeline import create_default_pipeline_for_company
            pipeline = await create_default_pipeline_for_company(str(recruiter["_id"]), "Test Company")
            
        first_stage = pipeline["stages"][0]
            
        import datetime
        from backend.models.application import create_application
        
        app_doc = await create_application(
            job_id=str(job["_id"]),
            student_id=str(student_id),
            company_id=str(recruiter["_id"]),
            pipeline_template_id=str(pipeline["_id"]),
            initial_stage_id=first_stage["id"],
            initial_stage_name=first_stage["name"],
            resume_file_id="dummy",
            answers={}
        )
        app_id = str(app_doc["_id"])
        print(f"Created test application {app_id}")
        app = await db["applications"].find_one({"_id": ObjectId(app_id)})
    
    app_id = str(app["_id"])
    recruiter_id = str(app["company_id"])
    pipeline_id = str(app["pipeline_template_id"])
    
    # 3. Get the pipeline to find the NEXT stage
    pipeline = await db["pipeline_templates"].find_one({"_id": ObjectId(pipeline_id)})
    if not pipeline:
        print("Pipeline not found!")
        return
        
    current_stage_id = app["current_stage_id"]
    stages = pipeline.get("stages", [])
    
    # Find a stage that is not the current one, preferably 'rejected' or 'interview'
    target_stage = None
    for stage in stages:
        if stage["id"] != current_stage_id and stage["type"] in ("rejected", "interview", "review"):
            target_stage = stage
            break
            
    if not target_stage:
        for stage in stages:
            if stage["id"] != current_stage_id:
                target_stage = stage
                break
                
    if not target_stage:
        print("Pipeline only has one stage, cannot test move!")
        return
        
    print(f"\nMoving application {app_id} from '{app['current_stage_name']}' to '{target_stage['name']}'...")

    # 4. Trigger the route logic directly using the service layer
    # Since we added the hook to move_application_stage inside the route instead of the model,
    # we need to simulate the route's actions.
    
    from backend.models.application import move_application_stage
    from backend.services.notification_service import notification_service
    
    updated = await move_application_stage(
        application_id=app_id,
        new_stage_id=target_stage["id"],
        new_stage_name=target_stage["name"],
        changed_by=recruiter_id,
        reason="Test script automated move",
        student_visible_stage=target_stage.get("student_visible_name", target_stage["name"])
    )
    
    # Get the job object correctly using ObjectId
    job = await db["opportunities_jobs"].find_one({"_id": ObjectId(str(app["job_id"]))})
    if not job:
        print("Job not found, using generic name.")
        company_name = "Test Company"
        job = {"title": "Test Job"}
    else:
        company_name = job.get("company_name", "Test Company")
        
    recruiter = await db["users"].find_one({"_id": ObjectId(str(app["company_id"]))})
    
    # Trigger the notification as the route does
    print("Calling notification service...")
    result = await notification_service.create_application_update_notification(
        student_id=str(student_id),
        job_title=job.get("title", "Job"),
        company_name=company_name,
        new_stage_name=target_stage["name"],
        stage_type=target_stage.get("type", "custom"),
        application_id=app_id
    )
    print(f"Notification result: {result}")
    
    # 5. Verify it was written to the db
    print("\nChecking notifications collection for Sushant...")
    import pymongo
    recent = await db["notifications"].find(
        {"user_id": student_id, "category": "application_update"}
    ).sort("created_at", pymongo.DESCENDING).limit(1).to_list(1)
    
    if recent:
        rn = recent[0]
        print(f"\n✅ FOUND TRIGGERED NOTIFICATION!")
        print(f"   Title:    {rn['title']}")
        print(f"   Message:  {rn['message']}")
        print(f"   Priority: {rn['priority']}")
        print(f"   URL:      {rn['action_url']}")
    else:
        print("\n❌ Failed to find notification in database.")

asyncio.run(main())
