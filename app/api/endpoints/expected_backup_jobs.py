from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.orm import Session
from typing import List

# Importation des schémas mis à jour pour ExpectedBackupJob
from app.schemas.expected_backup_job import (
    ExpectedBackupJob, 
    ExpectedBackupJobCreate, 
    ExpectedBackupJobUpdate
)
# Importation des opérations CRUD pour ExpectedBackupJob (à adapter selon votre logique)
from app.crud import expected_backup_job as crud_job
from app.core.database import get_db

router = APIRouter(
    prefix="",
    tags=["Expected Backup Jobs"],
    responses={404: {"description": "Non trouvé"}},
)

@router.post("/", response_model=ExpectedBackupJob, status_code=status.HTTP_201_CREATED)
def create_expected_backup_job(
    job: ExpectedBackupJobCreate, db: Session = Depends(get_db)
):
    """
    Crée un nouveau ExpectedBackupJob avec les données fournies.
    """
    created_job = crud_job.create_expected_backup_job(db=db, job=job)
    return created_job

@router.get("/{job_id}", response_model=ExpectedBackupJob)
def read_expected_backup_job(
    job_id: int = Path(..., title="ID du job", gt=0),
    db: Session = Depends(get_db)
):
    """
    Récupère un ExpectedBackupJob par son identifiant.
    """
    db_job = crud_job.get_expected_backup_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.get("/", response_model=List[ExpectedBackupJob])
def list_expected_backup_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, gt=0),
    db: Session = Depends(get_db)
):
    """
    Retourne la liste de tous les ExpectedBackupJob.
    - `skip` indique le nombre d'enregistrements à ignorer.
    - `limit` fixe le nombre maximal de résultats retournés.
    """
    jobs = crud_job.get_expected_backup_jobs(db=db, skip=skip, limit=limit)
    return jobs

@router.put("/{job_id}", response_model=ExpectedBackupJob)
def update_expected_backup_job(
    job_id: int = Path(..., title="ID du job", gt=0),
    job_update: ExpectedBackupJobUpdate = None,
    db: Session = Depends(get_db)
):
    """
    Met à jour les données d'un ExpectedBackupJob existant.
    """
    updated_job = crud_job.update_expected_backup_job(db=db, job_id=job_id, job_update=job_update)
    if updated_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return updated_job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expected_backup_job(
    job_id: int = Path(..., title="ID du job", gt=0),
    db: Session = Depends(get_db)
):
    """
    Supprime l'ExpectedBackupJob dont l'ID est fourni.
    """
    deleted_job = crud_job.delete_expected_backup_job(db=db, job_id=job_id)
    if deleted_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
