from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import sys
import time

# Ensure the 'src' directory can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.agent import CustomerSupportAgent
from src.config import settings
from src.utils import logger
from src.analytics import analytics

app = FastAPI(title="OmniServe AI - Context-Aware Voice Support")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Agent
agent = None
current_api_key = None

def get_agent(api_key: Optional[str] = None, provider: Optional[str] = None):
    global agent, current_api_key
    
    needs_new_agent = (
        agent is None or 
        (api_key and api_key != current_api_key) or 
        (provider and agent.provider != provider)
    )
    
    if needs_new_agent:
        try:
            agent = CustomerSupportAgent(api_key=api_key, provider=provider)
            current_api_key = api_key
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    return agent

class ChatQuery(BaseModel):
    query: str
    user_id: str
    api_key: Optional[str] = None
    provider: Optional[str] = None

class ProfileRequest(BaseModel):
    user_id: str
    api_key: Optional[str] = None
    provider: Optional[str] = None

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat(data: ChatQuery):
    try:
        start_time = time.time()
        current_agent = get_agent(data.api_key, data.provider)
        response = current_agent.handle_query(data.query, user_id=data.user_id)
        response_time = time.time() - start_time
        
        # Log analytics
        analytics.log_interaction(
            user_id=data.user_id,
            query=data.query,
            response=response,
            response_time=response_time
        )
        
        return {"response": response}
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Chat error: {e}\n{error_detail}")
        # Return the error message to the frontend for debugging
        return {"error": str(e), "response": f"I encountered an error: {str(e)}"}

@app.post("/generate-profile")
async def generate_profile(data: ProfileRequest):
    try:
        current_agent = get_agent(data.api_key, data.provider)
        profile = current_agent.generate_synthetic_profile(data.user_id)
        if profile:
            return profile
        else:
            raise HTTPException(status_code=500, detail="Failed to generate profile")
    except Exception as e:
        logger.error(f"Profile generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/{user_id}")
async def get_memories(user_id: str):
    try:
        current_agent = get_agent()
        memories = current_agent.get_user_memories(user_id)
        return {"memories": memories}
    except Exception as e:
        logger.error(f"Memory retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics Endpoints
@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get overall analytics summary."""
    try:
        return analytics.get_summary_stats()
    except Exception as e:
        logger.error(f"Analytics summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/user/{user_id}")
async def get_user_analytics(user_id: str):
    """Get analytics for a specific user."""
    try:
        return analytics.get_user_stats(user_id)
    except Exception as e:
        logger.error(f"User analytics error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/recent")
async def get_recent_interactions(limit: int = 10):
    """Get recent interactions."""
    try:
        return {"interactions": analytics.get_recent_interactions(limit)}
    except Exception as e:
        logger.error(f"Recent interactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/top-users")
async def get_top_users(limit: int = 5):
    """Get most active users."""
    try:
        return {"top_users": analytics.get_top_users(limit)}
    except Exception as e:
        logger.error(f"Top users error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
