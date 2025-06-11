from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey, BigInteger, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

# --- Définition des Enums ---
class JobStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"
    UNKNOWN = "unknown"

class BackupFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    HOURLY = "hourly"
    ONCE = 'once'

class BackupEntryStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"

# --- TABLE 1: ExpectedBackupJob ---
class ExpectedBackupJob(Base):
    __tablename__ = "expected_backup_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False)
    company_name = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    database_name = Column(String, nullable=False, index=True)
    expected_hour_utc = Column(Integer, nullable=False)
    expected_minute_utc = Column(Integer, nullable=False)
    
    __table_args__ = (
        UniqueConstraint('year', 'company_name', 'city', 'database_name',
                       'expected_hour_utc', 'expected_minute_utc',
                       name='_unique_job_config'),
    )

    expected_storage_base_path = Column(String, nullable=False)
    expected_frequency = Column(SQLEnum(*[f.value for f in BackupFrequency]), nullable=False)  # Correction ici
    days_of_week = Column(String, nullable=False)
    current_status = Column(SQLEnum(*[s.value for s in JobStatus]), default=JobStatus.UNKNOWN.value, nullable=False)
    last_checked_timestamp = Column(DateTime, nullable=True)
    last_successful_backup_timestamp = Column(DateTime, nullable=True)
    notification_recipients = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    backup_entries = relationship("BackupEntry", back_populates="expected_job", order_by="desc(BackupEntry.timestamp)")

    def __repr__(self):
        return (f"<ExpectedBackupJob(company='{self.company_name}', city='{self.city}', "
                f"db='{self.database_name}', year={self.year}, "
                f"expected_time={self.expected_hour_utc:02d}:{self.expected_minute_utc:02d} UTC, "
                f"status='{self.current_status}')>")

# --- TABLE 2: BackupEntry ---
class BackupEntry(Base):
    __tablename__ = "backup_entries"

    id = Column(Integer, primary_key=True, index=True)
    expected_job_id = Column(Integer, ForeignKey("expected_backup_jobs.id"), nullable=False, index=True)
    expected_job = relationship("ExpectedBackupJob", back_populates="backup_entries")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(SQLEnum(*[s.value for s in BackupEntryStatus]), nullable=False, index=True)  # Correction ici
    message = Column(Text, nullable=True)
    log_file_name = Column(String, nullable=True)
    backup_file_name = Column(String, nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum_sha256 = Column(String(64), nullable=True, index=True)
    previous_checksum_sha256 = Column(String(64), nullable=True)
    hash_comparison_result = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (f"<BackupEntry(job_id={self.expected_job_id}, status='{self.status}', "
                f"timestamp='{self.timestamp}', hash_ok={self.hash_comparison_result})>")