from fastapi import APIRouter, Depends, HTTPException, Path, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.schemas.backup_entry import BackupEntryInDB
from app.crud import backup_entry as crud_entry
from app.core.database import get_db

router = APIRouter(
    prefix="/entries",
    tags=["Backup Entries"],
    responses={404: {"description": "Non trouvé"}},
)

from sqlalchemy.orm import Session
from app.models.models import BackupEntry



# Ajoutez ici vos autres fonctions CRUD (get_backup_entry, get_backup_entries, etc.)

# La route plus spécifique "by_job" doit être déclarée EN PREMIER
@router.get("/by_job/{job_id}", response_model=List[BackupEntryInDB])
def read_entries_by_job(
    job_id: int = Path(..., title="ID du job", gt=0),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Récupère une liste d'entrées de sauvegarde pour un job spécifique par son ID.
    On ne vérifie pas l'existence du job, ce qui permet aux appels de retourner
    tout simplement une liste vide en cas de cascade.
    """
    entries = crud_entry.get_backup_entries_by_job_id(db=db, job_id=job_id, skip=skip, limit=limit)
    return entries

@router.get("/{entry_id}", response_model=BackupEntryInDB)
def read_entry(
    entry_id: int = Path(..., title="ID de l'entrée", gt=0),
    db: Session = Depends(get_db)
):
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    db_entry = crud_entry.get_backup_entry(db=db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée de sauvegarde non trouvée")
    return db_entry

@router.get("/", response_model=List[BackupEntryInDB])
def read_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0),
    db: Session = Depends(get_db)
):
    """
    Récupère une liste de toutes les entrées de sauvegarde.
    - `skip` doit être supérieur ou égal à 0.
    - `limit` doit être strictement positif.
    """
    entries = crud_entry.get_backup_entries(db=db, skip=skip, limit=limit)
    return entries