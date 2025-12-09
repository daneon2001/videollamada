from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "videollamada-python"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    ALLOWED_ORIGINS: List[str] = ["http://localhost:5500", "http://127.0.0.1:5500"]

    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "videocalls"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    SQL_ECHO: bool = False

    STUN_URLS: List[str] = ["stun:stun.l.google.com:19302"]
    TURN_URLS: List[str] = []
    TURN_USERNAME: Optional[str] = None
    TURN_CREDENTIAL: Optional[str] = None

    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    TLS_ENABLE_DIRECT: bool = False
    TLS_CERT_FILE: Optional[str] = None
    TLS_KEY_FILE: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
