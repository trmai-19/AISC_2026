import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "DCI - Digital Cultural Interpreter Backend"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgrespassword@localhost:5432/aisc_db"
    
    @field_validator("DATABASE_URL", mode="before")
    def format_database_url(cls, v):
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg2://", 1)
        return v

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            return json.loads(v)
        return v
    
    # AI / LLM Configuration
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "bge-m3"
    CONFIDENCE_THRESHOLD: float = 0.70
    
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
