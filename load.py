"""
Script to load JSON data into MongoDB.
--------------------------------------
Run this once to populate your database with initial jobs and profiles data.
"""

import os
import json
import pymongo
from config import (
    MONGO_URI,
    DATABASE_NAME,
    PROFILES_COLLECTION,
    JOBS_COLLECTION,
    NOTIFICATIONS_COLLECTION,
)


def load_data_to_mongodb():
    """Load jobs and profiles data from JSON files to MongoDB"""
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DATABASE_NAME]

    try:
        confirm = input("⚠️  This will erase existing data. Continue? (y/n): ").strip().lower()
        if confirm != "y":
            print("❌ Operation cancelled.")
            return

        # Get base directory for relative file paths
        base_path = os.path.dirname(__file__)

        # ---------- LOAD JOBS ----------
        print("📦 Loading jobs data...")
        #data/jobs.json exists and is valid JSON.
        with open(os.path.join(base_path, "data", "jobs.json"), "r", encoding="utf-8") as f:
            jobs_data = json.load(f)

        db[JOBS_COLLECTION].delete_many({})
        db[JOBS_COLLECTION].insert_many(jobs_data)
        print(f"✅ Loaded {len(jobs_data)} jobs")
        #oading profiles
        print("👤 Loading profiles data...")
        #data/profiles.json exists and is valid JSON.
        with open(os.path.join(base_path, "data", "profiles.json"), "r", encoding="utf-8") as f:
            profiles_data = json.load(f)

        db[PROFILES_COLLECTION].delete_many({})
        db[PROFILES_COLLECTION].insert_many(profiles_data)
        print(f"✅ Loaded {len(profiles_data)} profiles")

    #creating index
        print("⚙️ Creating indexes for faster queries...")
        db[JOBS_COLLECTION].create_index([("location", 1)])
        db[JOBS_COLLECTION].create_index([("experience_required", 1)])
        db[PROFILES_COLLECTION].create_index([("location", 1)])
        db[PROFILES_COLLECTION].create_index([("experience", 1)])
        db[NOTIFICATIONS_COLLECTION].create_index([("user_name", 1), ("status", 1)])
        print("✅ Indexes created successfully")

        print("\n🎉 Data loading completed successfully!")

    except FileNotFoundError as e:
        print("❌ Error: Could not find data files in the 'data' folder.")
        print(f"Details: {e}")
    except Exception as e:
        import traceback
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    load_data_to_mongodb()
