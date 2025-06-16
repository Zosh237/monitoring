from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.models import JobStatus, BackupFrequency

class ExpectedBackupJobBase(BaseModel):
    """Schéma de base pour les données d'un ExpectedBackupJob."""
    database_name: str
    agent_id_responsible: str
    company_name: str
    city: str
    expected_hour_utc: int
    expected_minute_utc: int
    backup_frequency: BackupFrequency
    final_storage_path_template: str

class ExpectedBackupJobCreate(ExpectedBackupJobBase):
    """Schéma pour la création d'un ExpectedBackupJob."""
    pass

class ExpectedBackupJobUpdate(ExpectedBackupJobBase):
    """Schéma pour la mise à jour d'un ExpectedBackupJob (tous les champs sont optionnels)."""
    database_name: Optional[str] = None
    agent_id_responsible: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    expected_hour_utc: Optional[int] = None
    expected_minute_utc: Optional[int] = None
    backup_frequency: Optional[BackupFrequency] = None
    final_storage_path_template: Optional[str] = None

class ExpectedBackupJobInDB(ExpectedBackupJobBase):
    """Schéma pour la représentation d'un ExpectedBackupJob tel qu'il est stocké en DB."""
    id: int
    current_status: JobStatus
    last_checked_at_utc: Optional[datetime] = None
    last_successful_backup_utc: Optional[datetime] = None
    last_failed_backup_utc: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True) 