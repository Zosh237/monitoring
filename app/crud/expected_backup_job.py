from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.models.models import ExpectedBackupJob, JobStatus
from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate

def create_expected_backup_job(db: Session, job: ExpectedBackupJobCreate) -> ExpectedBackupJob:
    job_data = job.dict() if hasattr(job, 'dict') else job.model_dump()
    job_data.pop("current_status", None)  # Évite la redondance
    now = datetime.now(timezone.utc)

    db_job = ExpectedBackupJob(
        **job_data,
        current_status=JobStatus.UNKNOWN.value,  # ✅ Remplace "unknown" par l'énumération
        created_at=now,
        updated_at=now
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


# Les autres fonctions CRUD restent identiques...


def get_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Récupère un job de sauvegarde attendu par son ID.
    """
    return db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()

def get_expected_backup_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[ExpectedBackupJob]:
    """
    Récupère une liste paginée de jobs de sauvegarde attendus.
    """
    return db.query(ExpectedBackupJob).offset(skip).limit(limit).all()

def update_expected_backup_job(db: Session, job_id: int, job_update: ExpectedBackupJobUpdate) -> Optional[ExpectedBackupJob]:
    db_job = get_expected_backup_job(db, job_id)
    if db_job:
        update_data = job_update.dict(exclude_unset=True) if hasattr(job_update, 'dict') else job_update.model_dump(exclude_unset=True)
        if "current_status" in update_data:
            update_data["current_status"] = JobStatus(update_data["current_status"]).value  # ✅ Conversion explicite
        for key, value in update_data.items():
            setattr(db_job, key, value)
        db_job.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(db_job)
    return db_job



def delete_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Supprime un job de sauvegarde attendu par son ID.
    """
    db_job = get_expected_backup_job(db, job_id)
    if db_job:
        db.delete(db_job)
        db.commit()
    return db_job
