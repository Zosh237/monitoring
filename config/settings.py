from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    """
        Classe de configuration de l'application.
        Les paramètres sont chargés à partir des variables d'environnement
    """

    #Config de la BD
    DATABASE_URL: str = Field(
        "sqlite:///./data/db/sql_app.db",
        env="DATABASE_URL"
    )

    # Chemin racine pour le stockage des sauvegardes
    BACKUP_STORAGE_ROOT: str = Field(
        "/mnt/backups",
        env="BACKUP_STORAGE_ROOT"
    )

    # Intervalle de planification du scanner de sauvegardes en minutes
    SCANNER_INTERVAL_MINUTES: int = Field(
        15,  # Par défaut, le scanner s'exécute toutes les 15 minutes
        env="SCANNER_INTERVAL_MINUTES"
    )

    # Jours de la semaine où les sauvegardes sont attendues (ex: Lun, Mar, Mer, Jeu, Ven, Sam)
    # Les valeurs doivent être des codes courts des jours de la semaine (MO, TU, WE, TH, FR, SA, SU)
    EXPECTED_BACKUP_DAYS_OF_WEEK: List[str] = Field(
        ["MO", "TU", "WE", "TH", "FR", "SA"], # Lundi à samedi par défaut
        env="EXPECTED_BACKUP_DAYS_OF_WEEK"
    )

    # Fuseau horaire par défaut de l'application pour les opérations temporelles si non spécifié en UTC
    # (Bien que nous privilégions UTC pour les timestamps internes)
    APP_TIMEZONE: str = Field(
        "UTC", # Par défaut, utilisez UTC pour la cohérence
        env="APP_TIMEZONE"
    )

    # Configuration du modèle de chargement des paramètres
    model_config = SettingsConfigDict(
        env_file=".env",            # Indique à Pydantic de charger les variables depuis un fichier .env
        env_file_encoding='utf-8',  # Encodage du fichier .env
        extra='ignore'              # Ignore les variables d'environnement non définies dans la classe Settings
    )

# Crée une instance unique des paramètres pour toute l'application.
# Cette instance sera chargée une seule fois au démarrage.
settings = Settings()