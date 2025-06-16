from typing import List
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl

class Settings(BaseSettings):
    # Configuration de l'API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "API de Surveillance des Sauvegardes"
    
    # Configuration CORS
    CORS_ORIGINS: List[AnyHttpUrl] = [
        "http://localhost:3000",  # Frontend React
        "http://localhost:8000",  # API en développement
    ]
    
    # Configuration de la base de données
    DATABASE_URL: str = "sqlite:///./backup_monitoring.db"
    
    # Configuration des notifications
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    NOTIFICATION_EMAIL_FROM: str = ""
    NOTIFICATION_EMAIL_TO: List[str] = []
    
    # Configuration du système
    APP_TIMEZONE: str = "UTC"
    BACKUP_STORAGE_ROOT: str = "/mnt/backups"
    SCANNER_INTERVAL_MINUTES: int = 5
    SCANNER_REPORT_COLLECTION_WINDOW_MINUTES: int = 60
    MAX_STATUS_FILE_AGE_DAYS: int = 1
    EXPECTED_BACKUP_DAYS_OF_WEEK: List[str] = ["MO", "TU", "WE", "TH", "FR", "SA"]
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "allow"

settings = Settings() 