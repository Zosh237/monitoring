from fastapi import APIRouter
from app.api.endpoints import expected_backup_jobs, backup_entries

api_router = APIRouter()

# Intégration des endpoints pour les jobs de sauvegarde
api_router.include_router(
    expected_backup_jobs.router,
    prefix="/jobs",
    tags=["Expected Backup Jobs"]
)

# Intégration des endpoints pour les entrées de sauvegarde
api_router.include_router(
    backup_entries.router,
    prefix="/entries",
    tags=["Backup Entries"]
) 