import logging.config
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.config import settings
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.api.endpoints import expected_backup_jobs, backup_entries

# --- Configuration du Logging ---
# Chemin vers le fichier de configuration YAML du logging
LOGGING_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "logging.yaml")

# Charger la configuration du logging
if os.path.exists(LOGGING_CONFIG_PATH):
    logging.config.fileConfig(LOGGING_CONFIG_PATH, disable_existing_loggers=False)
else:
    # Fallback pour le logging si le fichier de configuration n'est pas trouvé
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - [%(name)s] - %(levelname)s - %(message)s')

# Obtenir un logger pour cette application
logger = logging.getLogger(__name__)

#--- Initialisation de l'Application FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Création des tables de la base de données
Base.metadata.create_all(bind=engine)

# --- Événements au démarrage de l'application ---
@app.on_event("startup")
async def startup_event():
    logger.info("Démarrage de l'application FastAPI...")
    start_scheduler()
    logger.info("Application prête.")

@app.on_event("shutdown")
async def shutdown_event():
    """Gestionnaire d'événements d'arrêt de l'application."""
    logger.info("Arrêt de l'application FastAPI...")
    shutdown_scheduler()
    logger.info("Application arrêtée.")

# --- Endpoint de test simple ---
@app.get("/")
async def root():
    """
    Point d'entrée principal de l'API.
    """
    return {"message": "API de Surveillance des Sauvegardes est en ligne"}

# --- Exemple d'utilisation du logger ailleurs dans le code ---
# (Pour démontrer comment vous l'utiliserez dans d'autres modules)
# Créez ce fichier si vous voulez tester : app/core/exceptions.py
#try:
#    import app.core.exceptions
#    logger.debug("Le module exceptions a été importé.")
#except ImportError:
#    logger.warning("Le module exceptions n'a pas pu être importé. Il est peut-être absent.")

# Inclusion des routeurs avec le préfixe /api/v1
app.include_router(expected_backup_jobs.router, prefix=settings.API_V1_STR, tags=["Expected Backup Jobs"])
app.include_router(backup_entries.router, prefix=settings.API_V1_STR, tags=["Backup Entries"])
