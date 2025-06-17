from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.models.models import ExpectedBackupJob, JobStatus
from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate

def create_expected_backup_job(db: Session, job: ExpectedBackupJobCreate) -> ExpectedBackupJob:
    """
    Crée un nouveau job de sauvegarde attendu dans la base de données.
    """
    # Gestion flexible : dict ou objet Pydantic
    if isinstance(job, dict):
        job_data = job
    else:
        # Objet Pydantic - utilise dict() pour v1 ou model_dump() pour v2
        job_data = job.dict() if hasattr(job, 'dict') else job.model_dump()
    
    db_job = ExpectedBackupJob(
        **job_data,
        current_status=JobStatus.UNKNOWN,
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Récupère un job de sauvegarde attendu par son ID.
    """
    return db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()

def get_expected_backup_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[ExpectedBackupJob]:
    """
    Récupère une liste de jobs de sauvegarde attendus avec pagination.
    """
    return db.query(ExpectedBackupJob).offset(skip).limit(limit).all()

def update_expected_backup_job(db: Session, job_id: int, job_update: ExpectedBackupJobUpdate) -> Optional[ExpectedBackupJob]:
    """
    Met à jour un job de sauvegarde attendu existant.
    """
    db_job = db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()
    if db_job:
        # Gestion flexible : dict ou objet Pydantic
        if isinstance(job_update, dict):
            update_data = job_update
        else:
            # Objet Pydantic - utilise dict() pour v1 ou model_dump() pour v2
            update_data = job_update.dict(exclude_unset=True) if hasattr(job_update, 'dict') else job_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            setattr(db_job, key, value)
        db.commit()
        db.refresh(db_job)
    return db_job

def delete_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Supprime un job de sauvegarde attendu par son ID.
    """
    db_job = db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first() #db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()
    if db_job:
        db.delete(db_job)
        db.commit()
    return db_job