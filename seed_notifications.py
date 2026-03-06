"""
Seed mock notifications for sushantmutnale512@gmail.com.
Run: .\\venv\\Scripts\\activate; python seed_notifications.py
"""
import asyncio, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datetime import datetime, timedelta

async def main():
    from backend.database import connect_to_mongo, get_database
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    db = get_database()

    user = await db["users"].find_one({"email": "sushantmutnale512@gmail.com"})
    if not user:
        print("User not found!")
        return

    uid = user["_id"]
    name = (user.get("full_name") or user.get("username") or "User").split()[0]
    print(f"Found user: {name} (id={uid})")

    now = datetime.utcnow()

    def notif(ntype, priority, title, message, action_url, read=False, clicked=False):
        offset_hours = {"urgent": 1, "high": 4, "medium": 8, "low": 24}
        age = timedelta(hours=offset_hours.get(priority, 6))
        return {
            "user_id":      uid,
            "user_type":    "student",
            "type":         ntype,
            "category":     ntype.split("_")[0],
            "priority":     priority,
            "title":        title,
            "message":      message,
            "action_url":   action_url,
            "action_text":  "View",
            "related_entity": None,
            "trigger":      {"rule": "mock_seed"},
            "created_at":   now - age,
            "read_at":      (now - age + timedelta(minutes=5)) if read else None,
            "clicked_at":   (now - age + timedelta(minutes=10)) if clicked else None,
            "dismissed_at": None,
            "delivery_status": {"in_app": True, "email": False, "push": False},
        }

    notifications = [
        notif("opportunity_match", "high",
              f"New Job Match: Backend Developer Intern",
              "TechStartup Inc. - 87% match based on your Python & Django skills",
              "/opportunities"),
        notif("deadline_reminder", "urgent",
              "Application deadline in 2 days!",
              "Frontend Developer Intern at WebDesign Studios closes on March 8th - apply now!",
              "/opportunities"),
        notif("recruiter_activity", "high",
              f"New message from a recruiter",
              "A recruiter at InfraTech Solutions messaged you about a DevOps internship",
              "/messages"),
        notif("learning_reminder", "medium",
              "Continue your Learning Path",
              "Your Docker learning path is idle for 5 days. You were 40% through!",
              "/learning"),
        notif("learning_reminder", "high",
              "Skill Gap Alert: AWS is in demand",
              "3 companies matching your profile require AWS. Start your AWS path now.",
              "/learning"),
        notif("recruiter_activity", "medium",
              "Recruiter viewed your profile",
              "Someone from Analytics Corp checked your profile - Python & ML skills caught their attention",
              "/profile"),
        notif("achievement", "low",
              f"Profile Score Improved!",
              f"Your AI readiness score increased by 12 points to 74%. Great progress, {name}!",
              "/profile", read=True),
        notif("opportunity_match", "medium",
              "New Job Match: Data Science Intern",
              "Analytics Corp - 79% match. Requires Python, ML, Pandas",
              "/opportunities", read=True, clicked=True),
    ]

    coll = db["notifications"]
    result = await coll.insert_many(notifications)
    print(f"Inserted {len(result.inserted_ids)} mock notifications successfully!")
    print("Open the Notifications page and refresh to see them.")

asyncio.run(main())
