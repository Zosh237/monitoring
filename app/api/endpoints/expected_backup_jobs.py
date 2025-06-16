from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate, ExpectedBackupJobInDB
from app.crud import expected_backup_job as crud_job
from app.core.database import get_db

router = APIRouter(
    prefix="/jobs",
    tags=["Expected Backup Jobs"],
    responses={404: {"description": "Non trouvé"}},
)

@router.post("/", response_model=ExpectedBackupJobInDB, status_code=status.HTTP_201_CREATED)
def create_job(job: ExpectedBackupJobCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau job de sauvegarde attendu.
    """
    db_job = crud_job.create_expected_backup_job(db=db, job=job)
    return db_job

@router.get("/{job_id}", response_model=ExpectedBackupJobInDB)
def read_job(job_id: int, db: Session = Depends(get_db)):
    """
    Récupère un job de sauvegarde attendu par son ID.
    """
    db_job = crud_job.get_expected_backup_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.get("/", response_model=List[ExpectedBackupJobInDB])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de tous les jobs de sauvegarde attendus.
    """
    jobs = crud_job.get_expected_backup_jobs(db=db, skip=skip, limit=limit)
    return jobs

@router.put("/{job_id}", response_model=ExpectedBackupJobInDB)
def update_job(job_id: int, job_update: ExpectedBackupJobUpdate, db: Session = Depends(get_db)):
    """
    Met à jour un job de sauvegarde attendu existant.
    """
    db_job = crud_job.update_expected_backup_job(db=db, job_id=job_id, job_update=job_update)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Supprime un job de sauvegarde attendu.
    """
    db_job = crud_job.delete_expected_backup_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return None 