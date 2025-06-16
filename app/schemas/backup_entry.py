from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.models import BackupEntryStatus

class BackupEntryInDB(BaseModel):
    """Schéma pour la représentation d'un BackupEntry tel qu'il est stocké en DB."""
    id: int
    expected_job_id: int
    status: BackupEntryStatus
    agent_report_timestamp_utc: Optional[datetime] = None
    agent_reported_hash_sha256: Optional[str] = None
    agent_reported_size_bytes: Optional[int] = None
    agent_compress_size_pre_compress: Optional[int] = None
    agent_compress_size_post_compress: Optional[int] = None
    agent_transfer_process_status: Optional[bool] = None
    agent_transfer_process_start_time: Optional[datetime] = None
    agent_transfer_process_timestamp: Optional[datetime] = None
    agent_transfer_error_message: Optional[str] = None
    agent_staged_file_name: Optional[str] = None
    agent_logs_summary: Optional[str] = None
    server_calculated_staged_hash: Optional[str] = None
    server_calculated_staged_size: Optional[int] = None
    hash_comparison_result: Optional[bool] = None
    previous_successful_hash_global: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, use_enum_values=True) 