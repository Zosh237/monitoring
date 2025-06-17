# config/settings.py
# Ce fichier définit les paramètres de configuration de l'application en utilisant Pydantic.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import os




class Settings(BaseSettings):
    """
    Classe de configuration de l'application.
    Les paramètres sont chargés à partir des variables d'environnement ou d'un fichier .env.
    """
    BACKUP_STORAGE_ROOT: str = "/mnt/backups"  # ✅ Remplace temporairement
    VALIDATED_BACKUPS_BASE_PATH: str = "/mnt/backups/validated"
    
    # Configuration de la base de données
    DATABASE_URL: str = Field(
        "sqlite:///./data/db/sql_app.db",
        env="DATABASE_URL"
    )

    API_V1_STR: str = Field("/api/v1",
         env="API_V1_STR"
    )


    # Chemin pour le stockage final des sauvegardes validées
    # C'est là que backup_manager déplacera les fichiers.
    # Intervalle de planification du scanner de sauvegardes en minutes
    SCANNER_INTERVAL_MINUTES: int = int(os.getenv("SCANNER_INTERVAL_MINUTES", 15))
    
    # Nouvelle variable : Fenêtre de temps en minutes pendant laquelle un rapport STATUS.json
    # est considéré comme pertinent après l'heure attendue du job.
    # Ex: Si job attendu à 13h, et fenêtre de 60 min, un rapport entre 13h00 et 14h00 sera considéré.
    SCANNER_REPORT_COLLECTION_WINDOW_MINUTES: int = Field(
        60, # 60 minutes de marge de retard pour les rapports
        env="SCANNER_REPORT_COLLECTION_WINDOW_MINUTES"
    )

    # Nouvelle variable : Âge maximum (en jours) d'un fichier STATUS.json
    # pour qu'il soit considéré comme pertinent par le scanner.
    MAX_STATUS_FILE_AGE_DAYS: int = Field(
        1, # Un rapport de plus d'un jour est ignoré (sauf si c'est la seule preuve d'un job ancien)
        env="MAX_STATUS_FILE_AGE_DAYS"
    )

    # Jours de la semaine où les sauvegardes sont attendues (ex: MO, TU, WE, TH, FR, SA, SU)
    EXPECTED_BACKUP_DAYS_OF_WEEK: List[str] = Field(
        ["MO", "TU", "WE", "TH", "FR", "SA"],
        env="EXPECTED_BACKUP_DAYS_OF_WEEK"
    )

    # Fuseau horaire par défaut de l'application pour les opérations temporelles si non spécifié en UTC
    APP_TIMEZONE: str = Field(
        "UTC",
        env="APP_TIMEZONE"
    )

    # Paramètres pour les notifications par e-mail
    EMAIL_HOST: Optional[str] = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))  # Port par défaut pour TLS
    EMAIL_USERNAME: Optional[str] = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
    EMAIL_SENDER: Optional[str] = os.getenv("EMAIL_SENDER")
    ADMIN_EMAIL_RECIPIENT: Optional[str] = os.getenv("ADMIN_EMAIL_RECIPIENT")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    

settings = Settings()
