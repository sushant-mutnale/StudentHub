import asyncio

async def run_direct():
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson import ObjectId
    
    MONGODB_URI = "mongodb+srv://Sush_512:Sushant%40512@studenthub.zlkxvkr.mongodb.net/?appName=Studenthub"
    MONGODB_DB = "student_hub"
    
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[MONGODB_DB]
    
    pipeline_id = ObjectId("69906572e79b1fa699ab8ed1")
    job_id = ObjectId("69894013b3a5d71e39a98f5e")
    recruiter_id = ObjectId("698378443aad5104692a54be")
    
    pipeline = await db.pipeline_templates.find_one({"_id": pipeline_id})
    if not pipeline: return
    
    total_candidates = 0
    for stage in sorted(pipeline.get("stages", []), key=lambda s: s.get("order", 0)):
        stage_id = stage["id"]
        
        apps = await db.applications.find({
            "company_id": recruiter_id,
            "current_stage_id": stage_id,
            "job_id": job_id,
            "status": "active"
        }).to_list(length=200)
        
        print(f"Stage {stage_id} - {stage.get('name')}: {len(apps)}")
        total_candidates += len(apps)
    
    print(f"\nTotal Cands: {total_candidates}")

if __name__ == "__main__":
    asyncio.run(run_direct())
