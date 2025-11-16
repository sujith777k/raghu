# config.py
import os

# MongoDB Configuration
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DATABASE_NAME = "alumni_database"

# Collections
PROFILES_COLLECTION = "profiles"
JOBS_COLLECTION = "jobs"
NOTIFICATIONS_COLLECTION = "notifications"