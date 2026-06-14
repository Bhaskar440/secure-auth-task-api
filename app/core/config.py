from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = Field("Secure Auth Task API", env="APP_NAME") # <-- ADD THIS LINE

    # Infrastructure URLs
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # Third-Party Integrations
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")

    class Config:
        extra = "ignore"

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()