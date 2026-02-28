import pymongo
client = pymongo.MongoClient("mongodb://localhost:27017")
db = client["student_hub"]
user = db.users.find_one({"username": "demo_student"})
print("Skills:", user.get("skills"))
