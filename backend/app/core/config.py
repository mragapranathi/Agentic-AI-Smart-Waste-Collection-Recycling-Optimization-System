import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    PROJECT_NAME: str = "Agentic AI Smart Waste Collection & Recycling Optimization System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment & Demo mode
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./smart_waste.db")
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # gemini, openai, anthropic, fallback
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Thresholds & Municipal Defaults
    DEFAULT_COLLECTION_THRESHOLD: float = 85.0  # %
    STALE_SENSOR_HOURS: float = 6.0
    SUDDEN_CHANGE_THRESHOLD: float = 35.0  # % change within 10 minutes
    
    # Depot coordinates (Municipal Operations Hub)
    # Default: Bangalore Municipal Operations Center / Configurable Demo City
    DEPOT_LAT: float = float(os.getenv("DEPOT_LAT", "12.9716"))
    DEPOT_LNG: float = float(os.getenv("DEPOT_LNG", "77.5946"))
    DEPOT_NAME: str = os.getenv("DEPOT_NAME", "Central Waste Management Depot")

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]

settings = Settings()
