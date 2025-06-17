from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import BackupEntry, ExpectedBackupJob
from app.schemas.backup_entry import BackupEntryCreate

def create_backup_entry(db: Session, entry: BackupEntryCreate) -> BackupEntry:
    """
    Crée une nouvelle entrée de sauvegarde dans la base de données à partir des données fournies.
    """
    db_entry = BackupEntry(**entry.dict())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_backup_entry(db: Session, entry_id: int) -> Optional[BackupEntry]:
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    return db.query(BackupEntry).filter(BackupEntry.id == entry_id).first()

def get_backup_entries(db: Session, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste paginée d'entrées de sauvegarde, triées par date de création décroissante.
    """
    return db.query(BackupEntry).order_by(BackupEntry.created_at.desc()).offset(skip).limit(limit).all()

def get_backup_entries_by_job_id(db: Session, job_id: int, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste paginée d'entrées de sauvegarde associées à un job spécifique.
    """
    return (
        db.query(BackupEntry)
        .filter(BackupEntry.expected_job_id == job_id)
        .order_by(BackupEntry.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_expected_backup_job_for_entry(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Vérifie l'existence d'un ExpectedBackupJob pour l'ID donné.
    Sert à valider le champ expected_job_id avant la création d'une BackupEntry.
    """
    return db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()
