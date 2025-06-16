import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def create_test_backup_entry(db: Session, job_id: int, status: BackupEntryStatus, timestamp: datetime) -> BackupEntry:
    """Helper pour créer une entrée de sauvegarde de test."""
    entry = BackupEntry(
        expected_job_id=job_id,
        status=status,
        agent_report_timestamp_utc=timestamp,
        agent_reported_hash_sha256="test_hash",
        agent_reported_size_bytes=1024,
        created_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def test_get_backup_entry(client: TestClient, sample_job_data):
    """Teste la récupération d'une entrée de sauvegarde par ID."""
    logger.info("Test: Récupération d'une entrée de sauvegarde par ID")
    # Créer un job et une entrée
    db = SessionLocal()
    job = create_expected_backup_job(db, sample_job_data)
    entry = create_test_backup_entry(db, job.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    db.close()
    
    response = client.get(f"/api/v1/entries/{entry.id}")
    assert response.status_code == 200
    fetched_entry = response.json()
    assert fetched_entry["id"] == entry.id
    assert fetched_entry["expected_job_id"] == job.id
    assert fetched_entry["status"] == BackupEntryStatus.SUCCESS.value

def test_get_backup_entry_not_found(client: TestClient):
    """Teste la récupération d'une entrée de sauvegarde inexistante."""
    logger.info("Test: Récupération d'une entrée de sauvegarde inexistante")
    response = client.get("/api/v1/entries/99999")
    assert response.status_code == 404
    assert "Entrée de sauvegarde non trouvée" in response.json()["detail"]

def test_get_all_backup_entries(client: TestClient, sample_job_data):
    """Teste la récupération de toutes les entrées de sauvegarde."""
    logger.info("Test: Récupération de toutes les entrées de sauvegarde")
    db = SessionLocal()
    job = create_expected_backup_job(db, sample_job_data)
    create_test_backup_entry(db, job.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job.id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    db.close()
    
    response = client.get("/api/v1/entries/")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 2

def test_get_backup_entries_by_job_id(client: TestClient, sample_job_data):
    """Teste la récupération des entrées de sauvegarde pour un job spécifique."""
    logger.info("Test: Récupération des entrées par Job ID")
    db = SessionLocal()
    job1 = create_expected_backup_job(db, sample_job_data)
    job2_data = {**sample_job_data, "database_name": "another_db"}
    job2 = create_expected_backup_job(db, job2_data)
    
    create_test_backup_entry(db, job1.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job1.id, BackupEntryStatus.HASH_MISMATCH, datetime.now(timezone.utc) - timedelta(hours=1))
    create_test_backup_entry(db, job2.id, BackupEntryStatus.FAILED, datetime.now(timezone.utc))
    db.close()
    
    response = client.get(f"/api/v1/entries/by_job/{job1.id}")
    assert response.status_code == 200
    entries_for_job1 = response.json()
    assert len(entries_for_job1) == 2
    assert all(e["expected_job_id"] == job1.id for e in entries_for_job1)

def test_get_backup_entries_by_job_id_not_found(client: TestClient):
    """Teste la récupération des entrées pour un job inexistant."""
    logger.info("Test: Récupération des entrées par Job ID inexistant")
    response = client.get("/api/v1/entries/by_job/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json()["detail"]

def test_pagination_backup_entries(client: TestClient, sample_job_data):
    """Teste la pagination des entrées de sauvegarde."""
    logger.info("Test: Pagination des entrées de sauvegarde")
    db = SessionLocal()
    job = create_expected_backup_job(db, sample_job_data)
    
    # Créer 15 entrées
    for i in range(15):
        create_test_backup_entry(
            db, 
            job.id, 
            BackupEntryStatus.SUCCESS, 
            datetime.now(timezone.utc) - timedelta(hours=i)
        )
    db.close()
    
    # Test avec limite de 10
    response = client.get("/api/v1/entries/?limit=10")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 10
    
    # Test avec skip
    response = client.get("/api/v1/entries/?skip=10&limit=10")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 5  # Il ne reste que 5 entrées après avoir sauté les 10 premiers

def test_backup_entries_ordering(client: TestClient, sample_job_data):
    """Teste l'ordre des entrées de sauvegarde (plus récentes en premier)."""
    logger.info("Test: Ordre des entrées de sauvegarde")
    db = SessionLocal()
    job = create_expected_backup_job(db, sample_job_data)
    
    # Créer des entrées avec des timestamps différents
    old_entry = create_test_backup_entry(
        db, 
        job.id, 
        BackupEntryStatus.SUCCESS, 
        datetime.now(timezone.utc) - timedelta(days=2)
    )
    new_entry = create_test_backup_entry(
        db, 
        job.id, 
        BackupEntryStatus.SUCCESS, 
        datetime.now(timezone.utc)
    )
    db.close()
    
    response = client.get(f"/api/v1/entries/by_job/{job.id}")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 2
    assert entries[0]["id"] == new_entry.id  # La plus récente en premier
    assert entries[1]["id"] == old_entry.id  # La plus ancienne en second 