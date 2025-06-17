from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

# Importation des schémas mis à jour pour BackupEntry
from app.schemas.backup_entry import BackupEntry, BackupEntryCreate
# Importation des opérations CRUD pour BackupEntry (à adapter selon votre logique)
from app.crud import backup_entry as crud_entry
from app.core.database import get_db

router = APIRouter(
    prefix="",
    tags=["Backup Entries"],
    responses={404: {"description": "Non trouvé"}},
)

@router.post("/", response_model=BackupEntry, status_code=status.HTTP_201_CREATED)
def create_backup_entry(
    entry: BackupEntryCreate, db: Session = Depends(get_db)
):
    """
    Crée une nouvelle BackupEntry pour le ExpectedBackupJob spécifié par expected_job_id.
    Vérifie que le job existe avant la création.
    """
    # Vérification de l'existence du ExpectedBackupJob
    job = crud_entry.get_expected_backup_job_for_entry(db=db, job_id=entry.expected_job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="ExpectedBackupJob non trouvé pour le expected_job_id donné")
    new_entry = crud_entry.create_backup_entry(db=db, entry=entry)
    return new_entry

@router.get("/by_job/{job_id}", response_model=List[BackupEntry])
def read_backup_entries_by_job(
    job_id: int = Path(..., title="ID du job", gt=0),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0),
    db: Session = Depends(get_db)
):
    """
    Récupère la liste des BackupEntry associées au ExpectedBackupJob spécifié par son ID.
    """
    entries = crud_entry.get_backup_entries_by_job_id(db=db, job_id=job_id, skip=skip, limit=limit)
    return entries

@router.get("/{entry_id}", response_model=BackupEntry)
def read_backup_entry(
    entry_id: int = Path(..., title="ID de l'entrée", gt=0),
    db: Session = Depends(get_db)
):
    """
    Récupère une BackupEntry par son identifiant.
    """
    entry = crud_entry.get_backup_entry(db=db, entry_id=entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée de sauvegarde non trouvée")
    return entry

@router.get("/", response_model=List[BackupEntry])
def read_backup_entries(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0),
    db: Session = Depends(get_db)
):
    """
    Retourne la liste de toutes les BackupEntry.
    - `skip` indique le nombre d'enregistrements à ignorer.
    - `limit` fixe le nombre maximal de résultats.
    """
    entries = crud_entry.get_backup_entries(db=db, skip=skip, limit=limit)
    return entries
