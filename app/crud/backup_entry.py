from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.models import BackupEntry

def get_backup_entry(db: Session, entry_id: int) -> Optional[BackupEntry]:
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    return db.query(BackupEntry).filter(BackupEntry.id == entry_id).first()

def get_backup_entries(db: Session, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste d'entrées de sauvegarde avec pagination.
    """
    return db.query(BackupEntry).order_by(BackupEntry.created_at.desc()).offset(skip).limit(limit).all()

def get_backup_entries_by_job_id(db: Session, job_id: int, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste d'entrées de sauvegarde pour un job spécifique, avec pagination.
    """
    return db.query(BackupEntry).filter(BackupEntry.expected_job_id == job_id).order_by(BackupEntry.created_at.desc()).offset(skip).limit(limit).all() 