from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.backup_entry import BackupEntryInDB
from app.crud import backup_entry as crud_entry
from app.crud import expected_backup_job as crud_job
from app.core.database import get_db

router = APIRouter(
    prefix="/entries",
    tags=["Backup Entries"],
    responses={404: {"description": "Non trouvé"}},
)

@router.get("/{entry_id}", response_model=BackupEntryInDB)
def read_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    db_entry = crud_entry.get_backup_entry(db=db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée de sauvegarde non trouvée")
    return db_entry

@router.get("/", response_model=List[BackupEntryInDB])
def read_entries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de toutes les entrées de sauvegarde.
    """
    entries = crud_entry.get_backup_entries(db=db, skip=skip, limit=limit)
    return entries

@router.get("/by_job/{job_id}", response_model=List[BackupEntryInDB])
def read_entries_by_job(job_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste d'entrées de sauvegarde pour un job spécifique par son ID.
    """
    # Vérifier si le job existe avant de chercher ses entrées
    job = crud_job.get_expected_backup_job(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")

    entries = crud_entry.get_backup_entries_by_job_id(db=db, job_id=job_id, skip=skip, limit=limit)
    return entries 