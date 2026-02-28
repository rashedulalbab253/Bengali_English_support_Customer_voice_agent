import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    """Application settings and configuration."""
    APP_NAME: str = "OmniServe AI"
    APP_ID: str = "omniserve-voice-platform"
    
    # Provider Selection: "gemini" or "groq"
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "groq")
    
    # Groq Configuration
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # Gemini Configuration
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = "gemini-2.0-flash"
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
