import logging.config
import os
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import Base, engine
from app.core.config import settings
from app.core.scheduler import start_scheduler, shutdown_scheduler
from app.api.endpoints import expected_backup_jobs, backup_entries

# --- Configuration du Logging ---
LOGGING_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "logging.yaml")

if os.path.exists(LOGGING_CONFIG_PATH):
    try:
        with open(LOGGING_CONFIG_PATH, "r") as f:
            logging_config = yaml.safe_load(f)
        logging.config.dictConfig(logging_config)
    except Exception as e:
        raise RuntimeError(f"{LOGGING_CONFIG_PATH} is invalid: {e}")
else:
    import logging
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - [%(name)s] - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# --- Initialisation de l'Application FastAPI ---
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

@app.on_event("startup")
async def startup_event():
    logger.info("Démarrage de l'application FastAPI...")
    start_scheduler()
    logger.info("Application prête.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Arrêt de l'application FastAPI...")
    shutdown_scheduler()
    logger.info("Application arrêtée.")

@app.get("/")
async def root():
    return {"message": "API de Surveillance des Sauvegardes est en ligne"}

# Inclusion des routeurs avec des préfixes de route explicites :
# Les endpoints Expected Backup Jobs seront accessibles sous "/api/v1/expected-backup-jobs"
app.include_router(
    expected_backup_jobs.router,
    prefix=f"{settings.API_V1_STR}/expected-backup-jobs",
    tags=["Expected Backup Jobs"]
)
app.include_router(
    backup_entries.router,
    prefix=f"{settings.API_V1_STR}/backup-entries",
    tags=["Backup Entries"]
)
