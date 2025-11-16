"""
AI Job Recommendation System
---------------------------------
This script uses TF-IDF + Naive Bayes to recommend jobs to new candidates.
It reads job and candidate data from MongoDB, calculates match scores, and stores recommendations.
"""

import pymongo
import numpy as np
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import LabelEncoder
from config import (
    MONGO_URI,
    DATABASE_NAME,
    PROFILES_COLLECTION,
    JOBS_COLLECTION,
    NOTIFICATIONS_COLLECTION,
)


class NewCandidateJobRecommender:
    def __init__(self):
        """Initialize MongoDB connection and ML models"""
        self.client = pymongo.MongoClient(MONGO_URI)
        self.db = self.client[DATABASE_NAME]
        self.vectorizer = TfidfVectorizer(stop_words="english", min_df=1, max_features=500)
        self.model = MultinomialNB()
        self.label_encoder = LabelEncoder()
        #for training modellls
    def train_model(self):
        """Train the ML model using job listings from MongoDB"""
        print("🤖 Training ML model...")

        jobs = list(self.db[JOBS_COLLECTION].find({}))
        if not jobs:
            raise ValueError("❌ No jobs available in database!")

        job_texts, job_labels = [], []
        for job in jobs:
            skills = job.get("required_skills", "")
            experience = str(job.get("experience_required", "0"))
            description = job.get("description", "")

            text = f"{skills} {experience} {description}".strip()
            if text:
                job_texts.append(text)
                job_labels.append(job.get("title", "Unknown"))

        X_train = self.vectorizer.fit_transform(job_texts)
        y_train = self.label_encoder.fit_transform(job_labels)
        self.model.fit(X_train, y_train)

        print(f"✅ Model trained on {len(jobs)} jobs")
        return jobs
#for matching scores
    def calculate_match_score(self, candidate, job):
        """Calculate compatibility score between candidate and job"""
        score = 0.0

        candidate_skills = set(s.strip().lower() for s in candidate.get("skills", "").split(",") if s)
        job_skills = set(s.strip().lower() for s in job.get("required_skills", "").split(",") if s)

        #ifSkills match 50%
        if candidate_skills and job_skills:
            common_skills = candidate_skills.intersection(job_skills)
            skill_match = len(common_skills) / len(job_skills)
            score += skill_match * 50

        #the experience match 30%
        candidate_exp = float(candidate.get("experience", 0))
        job_exp = float(job.get("experience_required", 0))
        if candidate_exp >= job_exp:
            score += 30
        else:
            score += (candidate_exp / max(job_exp, 1)) * 15

        # Location match 20
        if candidate.get("location", "").strip().lower() == job.get("location", "").strip().lower():
            score += 20

        return round(score, 2)
    def recommend_jobs_for_new_candidate(self, candidate, jobs, top_n=5):
        """Generate top N job recommendations for a new candidate"""
        candidate_skills = candidate.get("skills", "")
        candidate_bio = candidate.get("bio", "").strip()

        if not candidate_skills and not candidate_bio:
            return []

        if not jobs:
            return []

        recommendations = []
        candidate_experience = float(candidate.get("experience", 0))

        # Try ML-based recommendation first
        try:
            candidate_text = f"{candidate_skills} {candidate_bio}"
            X_test = self.vectorizer.transform([candidate_text])

            # Predict job title probabilities
            proba = self.model.predict_proba(X_test)[0]
            top_categories_idx = np.argsort(proba)[-top_n * 3:][::-1]  # Get more categories
            top_categories = self.label_encoder.inverse_transform(top_categories_idx)
            
            # First pass: Use ML predictions
            for job in jobs:
                job_exp = float(job.get("experience_required", 0) or 0)
                
                # Relaxed experience filter (allow 3 years difference)
                if candidate_experience + 3 < job_exp:
                    continue

                if job.get("title") in top_categories:
                    match_score = self.calculate_match_score(candidate, job)
                    if match_score > 10:  # Lower threshold
                        recommendations.append({"job": job, "match_score": match_score})
        except Exception as e:
            print(f"⚠️ ML prediction failed, using fallback: {e}")

        # Fallback: If ML didn't find enough matches, use skill-based matching for all jobs
        if len(recommendations) < top_n:
            for job in jobs:
                job_exp = float(job.get("experience_required", 0) or 0)
                
                # Relaxed experience filter
                if candidate_experience + 3 < job_exp:
                    continue

                # Skip if already in recommendations
                if any(rec["job"].get("title") == job.get("title") and 
                       rec["job"].get("company") == job.get("company") 
                       for rec in recommendations):
                    continue

                match_score = self.calculate_match_score(candidate, job)
                if match_score > 5:  # Very low threshold for fallback
                    recommendations.append({"job": job, "match_score": match_score})

        # Sort by match score and return top N
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return recommendations[:top_n]
    def create_notification(self, candidate, recommendations):
        """Store job recommendations as notifications in MongoDB"""
        if not recommendations:
            return 0

        notifications = []
        for rec in recommendations:
            job = rec["job"]
            notifications.append({
                "user_name": candidate.get("name"),
                "user_email": candidate.get("email", ""),
                "job_title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "required_skills": job.get("required_skills", ""),
                "experience_required": job.get("experience_required", 0),
                "match_score": rec["match_score"],
                "status": "unread",
                "notification_type": "new_candidate",
                "created_at": datetime.utcnow(),
            })

        self.db[NOTIFICATIONS_COLLECTION].insert_many(notifications)
        return len(notifications)
    def recommend_for_single_candidate(self, candidate_email):
        """Recommend jobs for one specific candidate by email (creates new users if needed)"""
        try:
            jobs = self.train_model()
            candidate = self.db[PROFILES_COLLECTION].find_one({"email": candidate_email})
        # if user not found creating nwe profir for user
            if not candidate:
                print(f"⚠️ Candidate with email '{candidate_email}' not found in database.")
                print("Let's create a new candidate profile.\n")

                name = input("Enter candidate name: ").strip()
                skills = input("Enter skills (comma-separated): ").strip()
                experience = input("Enter experience in years (number): ").strip()
                location = input("Enter location (city): ").strip()
                bio = input("Enter a short bio or background: ").strip()

                try:
                    experience = int(experience)
                except ValueError:
                    experience = 0  

                candidate = {
                    "name": name or "Unknown Candidate",
                    "email": candidate_email,
                    "skills": skills,
                    "experience": experience,
                    "location": location,
                    "bio": bio
                }

                #save new candidate to MongoDB
                self.db[PROFILES_COLLECTION].insert_one(candidate)
                print(f"✅ New candidate '{name}' added to database!\n")

            print(f"\n🎯 Generating recommendations for {candidate['name']} ({candidate_email})")
            recommendations = self.recommend_jobs_for_new_candidate(candidate, jobs, top_n=5)

            if not recommendations:
                print("❌ No suitable jobs found.")
                return

            count = self.create_notification(candidate, recommendations)
            print(f"✅ {count} job(s) recommended:\n")

            for i, rec in enumerate(recommendations, 1):
                job = rec["job"]
                print(f"{i}. {job['title']} at {job['company']}")
                print(f"   📍 {job['location']} | 💼 {job.get('experience_required', 0)} yrs")
                print(f"   🎯 Match: {rec['match_score']}%")
                print(f"   🔧 Skills: {job.get('required_skills', '')}")
                print(f"   📝 {job.get('description', '')}\n")

            print("🎉 Recommendations saved to notifications.")

        except Exception as e:
            import traceback
            print(f"❌ Error: {e}")
            traceback.print_exc()
        finally:
            self.client.close()
    def recommend_for_all_new_candidates(self):
        """Recommend jobs for all candidates who don’t have notifications yet"""
        try:
            jobs = self.train_model()
            all_candidates = list(self.db[PROFILES_COLLECTION].find({}))

            if not all_candidates:
                print("❌ No candidates found.")
                return

            notified_emails = set()
            existing_notifs = self.db[NOTIFICATIONS_COLLECTION].find(
                {"notification_type": "new_candidate"},
                {"user_email": 1}
            )
            for n in existing_notifs:
                notified_emails.add(n.get("user_email"))

            new_candidates = [c for c in all_candidates if c.get("email") not in notified_emails]
            if not new_candidates:
                print("✅ All candidates already have recommendations.")
                return

            print(f"📊 Found {len(new_candidates)} new candidate(s).")
            total_notifs = 0

            for candidate in new_candidates:
                print(f"🎯 Processing {candidate.get('name')} ({candidate.get('email', 'N/A')})")
                recs = self.recommend_jobs_for_new_candidate(candidate, jobs)
                if recs:
                    count = self.create_notification(candidate, recs)
                    total_notifs += count
                    print(f"   ✅ {count} job(s) recommended.")
                else:
                    print("   ❌ No suitable jobs found.")

            print(f"\n🎉 Done! Total notifications created: {total_notifs}")

        except Exception as e:
            import traceback
            print(f"❌ Error: {e}")
            traceback.print_exc()
        finally:
            self.client.close()

def main():
    import sys

    recommender = NewCandidateJobRecommender()
    print("=" * 60)
    print("   🤖 AI JOB RECOMMENDATION SYSTEM")
    print("=" * 60)

    print("\nOptions:")
    print("1. Recommend jobs for a specific candidate (by email)")
    print("2. Recommend jobs for all new candidates\n")

    if len(sys.argv) > 1:
        email = sys.argv[1]
        recommender.recommend_for_single_candidate(email)
    else:
        choice = input("Enter choice (1 or 2): ").strip()
        if choice == "1":
            email = input("Enter candidate email: ").strip()
            recommender.recommend_for_single_candidate(email)
        elif choice == "2":
            recommender.recommend_for_all_new_candidates()
        else:
            print("❌ Invalid choice.")


if __name__ == "__main__":
    main()


