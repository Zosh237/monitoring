from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.models import JobStatus, BackupFrequency

class ExpectedBackupJobBase(BaseModel):
    """Schéma de base pour les données d'un ExpectedBackupJob."""
    year: int
    database_name: str
    agent_id_responsible: str
    company_name: str
    city: str
    neighborhood: str
    expected_hour_utc: int
    expected_minute_utc: int
    expected_frequency: BackupFrequency
    days_of_week: str
    agent_deposit_path_template: str
    agent_log_deposit_path_template: str
    final_storage_path_template: str

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class ExpectedBackupJobCreate(ExpectedBackupJobBase):
    """Schéma pour la création d'un ExpectedBackupJob."""
    pass

class ExpectedBackupJobUpdate(BaseModel):
    """Schéma pour la mise à jour d'un ExpectedBackupJob (tous les champs sont optionnels)."""
    year: Optional[int] = None
    database_name: Optional[str] = None
    agent_id_responsible: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None
    expected_hour_utc: Optional[int] = None
    expected_minute_utc: Optional[int] = None
    expected_frequency: Optional[BackupFrequency] = None
    days_of_week: Optional[str] = None
    agent_deposit_path_template: Optional[str] = None
    agent_log_deposit_path_template: Optional[str] = None
    final_storage_path_template: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

class ExpectedBackupJobInDB(ExpectedBackupJobBase):
    """Schéma pour la représentation d'un ExpectedBackupJob tel qu'il est stocké en DB."""
    id: int
    current_status: JobStatus
    last_checked_at_utc: Optional[datetime] = None
    last_successful_backup_utc: Optional[datetime] = None
    last_failed_backup_utc: Optional[datetime] = None
    created_at: datetime
