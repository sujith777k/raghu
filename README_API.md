# Job Recommendation System - API Setup Guide

This guide will help you connect the HTML frontend (`ai.html`) with the Python backend recommendation system.

## Prerequisites

1. **Python 3.8+** installed
2. **MongoDB** running on `localhost:27017`
3. All required Python packages installed

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- FastAPI (web framework)
- uvicorn (ASGI server)
- pymongo (MongoDB driver)
- scikit-learn (ML library)
- And other dependencies

### 2. Load Data into MongoDB

Before running the API, you need to populate MongoDB with jobs and profiles data:

```bash
cd ML
python load.py
```

This will load data from `data/jobs.json` and `data/profiles.json` into MongoDB.

### 3. Start the API Server

You can start the server in two ways:

**Option A: Using the startup script**
```bash
cd ML
python start_server.py
```

**Option B: Using uvicorn directly**
```bash
cd ML
uvicorn api:app --reload --host 0.0.0.0 --port 5501
```

The server will start on `http://localhost:5501` (accessible from any device on your network)

### 4. Open the Frontend

Open `ML/ai.html` in your web browser. The frontend automatically detects the current host and connects to port 5501, so it will work on any device.

## API Endpoints

- **GET /** - Health check endpoint
- **POST /recommend** - Get job recommendations for a candidate profile
- **GET /docs** - Interactive API documentation (Swagger UI)

**Note:** The API runs on port 5501 and is accessible from any device on your network. The frontend automatically detects the current host.

## API Request Format

The `/recommend` endpoint expects a POST request with JSON body:

```json
{
  "full_name": "John Doe",
  "email": "john.doe@example.com",
  "skills": "JavaScript, Python, React, Node.js",
  "years_of_experience": 5,
  "location": "New York, NY",
  "bio": "Experienced software developer..."
}
```

## API Response Format

The API returns job recommendations:

```json
{
  "recommendations": [
    {
      "job_title": "Software Engineer",
      "company_name": "Tech Corp",
      "job_location": "New York, NY",
      "required_skills": ["JavaScript", "Python", "React"],
      "match_score": 0.85,
      "description": "Job description...",
      "experience_required": 3
    }
  ]
}
```

## Troubleshooting

### MongoDB Connection Error
- Make sure MongoDB is running: `mongod` or start MongoDB service
- Check if MongoDB is on `localhost:27017`

### No Jobs Found
- Run `python load.py` to populate the database
- Check if `data/jobs.json` exists and has valid data

### CORS Errors
- The API is configured to allow all origins for development
- In production, update `allow_origins` in `api.py`

### Port Already in Use
- Change the port in `start_server.py` and update the `apiPort` variable in `ai.html` (line 435)

## Testing the API

You can test the API using:

1. **Swagger UI**: Visit `http://localhost:5501/docs` (or use your device's IP address)
2. **Frontend**: Fill out the form in `ai.html` and submit (works on any device)
3. **curl**:
```bash
curl -X POST "http://localhost:5501/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Test User",
    "email": "test@example.com",
    "skills": "Python, JavaScript",
    "years_of_experience": 3,
    "location": "New York",
    "bio": "Software developer"
  }'
```

## Architecture

```
Frontend (ai.html)
    ↓ HTTP POST
API Server (api.py)
    ↓ Uses
ML Engine (ai.py)
    ↓ Queries
MongoDB Database
```

The system uses TF-IDF + Naive Bayes to match candidate profiles with job listings based on skills, experience, and location.

