"""
FastAPI Backend for Job Recommendation System
----------------------------------------------
This API server connects the HTML frontend with the ML recommendation engine.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from ai import NewCandidateJobRecommender
import uvicorn

app = FastAPI(title="Job Recommendation API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the recommender (will be initialized on startup)
recommender = None


class CandidateProfile(BaseModel):
    full_name: str
    email: EmailStr
    skills: str  # Comma-separated string
    years_of_experience: int
    location: str
    bio: str


class JobRecommendation(BaseModel):
    job_title: str
    company_name: str
    job_location: str
    required_skills: List[str]
    match_score: float
    description: Optional[str] = None
    experience_required: Optional[int] = None


class RecommendationResponse(BaseModel):
    recommendations: List[JobRecommendation]


@app.on_event("startup")
async def startup_event():
    """Initialize the recommender on startup"""
    global recommender
    try:
        recommender = NewCandidateJobRecommender()
        # Pre-train the model
        recommender.train_model()
        print("✅ Recommender initialized and model trained")
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize recommender: {e}")
        print("The model will be trained on first request.")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Job Recommendation API is running", "status": "ok"}


@app.get("/debug/jobs")
async def debug_jobs():
    """Debug endpoint to check if jobs are loaded"""
    try:
        if recommender is None:
            global recommender
            recommender = NewCandidateJobRecommender()
        
        # Get jobs from the jobs collection
        from config import JOBS_COLLECTION
        jobs = list(recommender.db[JOBS_COLLECTION].find({}))
        
        return {
            "total_jobs": len(jobs),
            "sample_jobs": jobs[:3] if jobs else [],
            "collections": recommender.db.list_collection_names(),
            "status": "ok"
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "message": "Could not access database"
        }


@app.post("/recommend", response_model=RecommendationResponse)
async def get_recommendations(profile: CandidateProfile):
    """
    Get job recommendations for a candidate profile
    """
    try:
        # Ensure recommender is initialized
        if recommender is None:
            global recommender
            recommender = NewCandidateJobRecommender()
        
        # Train model if needed (or retrain to get fresh jobs)
        jobs = recommender.train_model()
        
        # Convert frontend format to backend format
        candidate = {
            "name": profile.full_name,
            "email": profile.email,
            "skills": profile.skills,  # Already comma-separated string
            "experience": profile.years_of_experience,
            "location": profile.location,
            "bio": profile.bio
        }
        
        # Get recommendations
        print(f"🔍 Searching for jobs for: {candidate['name']}")
        print(f"   Skills: {candidate['skills']}")
        print(f"   Experience: {candidate['experience']} years")
        print(f"   Location: {candidate['location']}")
        print(f"   Total jobs in database: {len(jobs)}")
        
        recommendations = recommender.recommend_jobs_for_new_candidate(
            candidate, jobs, top_n=10
        )
        
        print(f"✅ Found {len(recommendations)} recommendations")
        
        # Convert backend format to frontend format
        formatted_recommendations = []
        for rec in recommendations:
            try:
                job = rec["job"]






                
                match_score = rec["match_score"] / 100.0  # Convert percentage to decimal (0-1)
                
                # Parse required_skills from string to list
                required_skills_str = job.get("required_skills", "")
                required_skills = [
                    skill.strip() 
                    for skill in required_skills_str.split(",") 
                    if skill.strip()
                ] if required_skills_str else []
                
                formatted_recommendations.append(JobRecommendation(
                    job_title=job.get("title", "Job Title Not Available"),
                    company_name=job.get("company", "Company Name Not Available"),
                    job_location=job.get("location", "Location Not Specified"),
                    required_skills=required_skills,
                    match_score=match_score,
                    description=job.get("description", ""),
                    experience_required=job.get("experience_required", 0)
                ))
            except Exception as e:
                print(f"⚠️ Error formatting job recommendation: {e}")
                continue
        
        if not formatted_recommendations:
            print("⚠️ No recommendations found. Possible reasons:")
            print("   - No jobs in database (run load.py)")
            print("   - Candidate skills don't match any jobs")
            print("   - Experience requirements too strict")
            print("   - Location mismatch")
        
        return RecommendationResponse(recommendations=formatted_recommendations)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error in recommendation: {e}")
        print(error_details)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate recommendations: {str(e)}"
        )


if __name__ == "__main__":
    print("🚀 Starting Job Recommendation API Server...")
    print("📝 API Documentation available at: http://localhost:5501/docs")
    uvicorn.run(app, host="0.0.0.0", port=5501, reload=True)

