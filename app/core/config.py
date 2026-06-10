"""Application configuration management."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    app_name: str = "Support Ticket AI System"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # LLM Settings
    groq_api_key: str
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.0
    groq_max_tokens: int = 1024
    
    # Data Settings
    data_path: str = "data/support_tickets.csv"
    
    # Anomaly Detection Settings
    anomaly_z_threshold: float = 3.0
    critical_ticket_hours_threshold: int = 24
    high_priority_hours_threshold: int = 48
    min_agent_rating: float = 2.5
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
