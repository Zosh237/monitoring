from fastapi import APIRouter, Depends, HTTPException, status, Path
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
    db_job = crud_job.create_expected_backup_job(db=db, job=job)
    return db_job

@router.get("/{job_id}", response_model=ExpectedBackupJobInDB)
def read_job(
    job_id: str = Path(..., title="ID du job"),
    db: Session = Depends(get_db)
):
    # Tenter de convertir le job_id en entier, sinon renvoyer 422
    try:
        job_id_int = int(job_id)
        if job_id_int <= 0:
            raise HTTPException(status_code=422, detail="job_id must be greater than 0")
    except ValueError:
        raise HTTPException(status_code=422, detail="job_id must be an integer")
    
    db_job = crud_job.get_expected_backup_job(db=db, job_id=job_id_int)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.get("/", response_model=List[ExpectedBackupJobInDB])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = crud_job.get_expected_backup_jobs(db=db, skip=skip, limit=limit)
    return jobs

@router.put("/{job_id}", response_model=ExpectedBackupJobInDB)
def update_job(
    job_id: str = Path(..., title="ID du job"),
    job_update: ExpectedBackupJobUpdate = None,
    db: Session = Depends(get_db)
):
    try:
        job_id_int = int(job_id)
        if job_id_int <= 0:
            raise HTTPException(status_code=422, detail="job_id must be greater than 0")
    except ValueError:
        raise HTTPException(status_code=422, detail="job_id must be an integer")
        
    db_job = crud_job.update_expected_backup_job(db=db, job_id=job_id_int, job_update=job_update)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: str = Path(..., title="ID du job"),
    db: Session = Depends(get_db)
):
    try:
        job_id_int = int(job_id)
        if job_id_int <= 0:
            raise HTTPException(status_code=422, detail="job_id must be greater than 0")
    except ValueError:
        raise HTTPException(status_code=422, detail="job_id must be an integer")
        
    db_job = crud_job.delete_expected_backup_job(db=db, job_id=job_id_int)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return None

