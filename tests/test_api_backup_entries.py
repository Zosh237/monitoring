import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job
from app.core.database import SessionLocal, engine, Base

logger = logging.getLogger(__name__)


# --- Helper pour créer une entrée de sauvegarde ---
def create_test_backup_entry(
    db: Session,
    job_id: int = 10,
    status: BackupEntryStatus = BackupEntryStatus.UNKNOWN,
    timestamp: datetime = None
) -> BackupEntry:
    """Helper pour créer une entrée de sauvegarde de test."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    
    entry = BackupEntry(
        expected_job_id=job_id,
        status=status,
        timestamp=timestamp,
        agent_backup_hash_pre_compress="test_hash_sha256",
        agent_backup_size_pre_compress=1024,
        created_at=datetime.now(timezone.utc)
    )
    logger.info(f"Insertion d'une BackupEntry pour job_id={job_id} avec status={status} à {timestamp}")
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(f"BackupEntry créée avec l'ID {entry.id}")
    return entry



# --- Tests des endpoints des backup entries ---

def test_get_backup_entry(client: TestClient, unique_sample_job_data):
    """Teste la récupération d'une entrée de sauvegarde par ID."""
    logger.info("Test: Récupération d'une entrée de sauvegarde par ID")
    db = SessionLocal()
    
    # Correction du dictionnaire si besoin
    corrected_job_data = unique_sample_job_data.copy()
    if 'backup_frequency' in corrected_job_data:
        corrected_job_data['expected_frequency'] = corrected_job_data.pop('backup_frequency')
    
    job = create_expected_backup_job(db, corrected_job_data)
    # Récupérer l'ID avant de fermer la session
    job_id = job.id  
    entry = create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    entry_id = entry.id
    db.close()
    
    response = client.get(f"/api/v1/entries/{entry_id}")
    assert response.status_code == 200, response.text
    fetched_entry = response.json()
    assert fetched_entry["id"] == entry_id
    assert fetched_entry["expected_job_id"] == job_id
    assert fetched_entry["status"] == BackupEntryStatus.SUCCESS.value

def test_get_backup_entry_not_found(client: TestClient):
    """Teste la récupération d'une entrée de sauvegarde inexistante."""
    logger.info("Test: Récupération d'une entrée de sauvegarde inexistante")
    response = client.get("/api/v1/entries/99999")
    assert response.status_code == 404
    assert "Entrée de sauvegarde non trouvée" in response.json().get("detail", "")

def test_get_all_backup_entries(client: TestClient, unique_sample_job_data):
    """Teste la récupération de toutes les entrées de sauvegarde."""
    logger.info("Test: Récupération de toutes les entrées de sauvegarde")
    db = SessionLocal()

    corrected_job_data = unique_sample_job_data.copy()
    if 'backup_frequency' in corrected_job_data:
        corrected_job_data['expected_frequency'] = corrected_job_data.pop('backup_frequency')

    job = create_expected_backup_job(db, corrected_job_data)
    job_id = job.id
    create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job_id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    db.close()
    
    response = client.get("/api/v1/entries/")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) >= 2

def test_get_backup_entries_by_job_id(client: TestClient, unique_sample_job_data):
    """Teste la récupération des entrées de sauvegarde pour un job spécifique."""
    logger.info("Test: Récupération des entrées par Job ID")
    db = SessionLocal()
    
    corrected_job_data = unique_sample_job_data.copy()
    if 'backup_frequency' in corrected_job_data:
        corrected_job_data['expected_frequency'] = corrected_job_data.pop('backup_frequency')
    
    job1 = create_expected_backup_job(db, corrected_job_data)
    job1_id = job1.id
    job2_data = {**corrected_job_data, "database_name": corrected_job_data["database_name"] + "_2"}
    job2 = create_expected_backup_job(db, job2_data)
    
    create_test_backup_entry(db, job1_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job1_id, BackupEntryStatus.HASH_MISMATCH, datetime.now(timezone.utc) - timedelta(hours=1))
    create_test_backup_entry(db, job2.id, BackupEntryStatus.FAILED, datetime.now(timezone.utc))
    db.close()
    
    response = client.get(f"/api/v1/entries/by_job/{job1_id}")
    assert response.status_code == 200
    entries_for_job1 = response.json()
    assert len(entries_for_job1) == 2
    assert all(e["expected_job_id"] == job1_id for e in entries_for_job1)

def test_get_backup_entries_by_job_id_not_found(client: TestClient):
    """Teste la récupération des entrées pour un job inexistant."""
    logger.info("Test: Récupération des entrées par Job ID inexistant")
    response = client.get("/api/v1/entries/by_job/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json().get("detail", "")

def test_pagination_backup_entries(client: TestClient, unique_sample_job_data):
    """Teste la pagination des entrées de sauvegarde."""
    logger.info("Test: Pagination des entrées de sauvegarde")
    db = SessionLocal()
    
    corrected_job_data = unique_sample_job_data.copy()
    if 'backup_frequency' in corrected_job_data:
        corrected_job_data['expected_frequency'] = corrected_job_data.pop('backup_frequency')
    
    job = create_expected_backup_job(db, corrected_job_data)
    job_id = job.id
    
    # Créer 15 entrées
    for i in range(15):
        create_test_backup_entry(
            db, 
            job_id, 
            BackupEntryStatus.SUCCESS, 
            datetime.now(timezone.utc) - timedelta(hours=i)
        )
    db.close()
    
    # Premier appel : limit=10
    response = client.get("/api/v1/entries/?limit=10")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 10
    
    # Deuxième appel : skip=10 & limit=10
    response = client.get("/api/v1/entries/?skip=10&limit=10")
    assert response.status_code == 200
    entries = response.json()
    # Ici, on s'attend à récupérer 15 - 10 = 5 entrées.
    assert len(entries) == 5, f"Attendu 5 entrées, obtenu {len(entries)}"

def test_backup_entries_ordering(client: TestClient, unique_sample_job_data):
    """Teste l'ordre des entrées de sauvegarde (les plus récentes en premier)."""
    logger.info("Test: Ordre des entrées de sauvegarde")
    db = SessionLocal()
    
    corrected_job_data = unique_sample_job_data.copy()
    if 'backup_frequency' in corrected_job_data:
        corrected_job_data['expected_frequency'] = corrected_job_data.pop('backup_frequency')
    
    job = create_expected_backup_job(db, corrected_job_data)
    job_id = job.id
    
    # Créer deux entrées avec des timestamps différents
    old_entry = create_test_backup_entry(
        db, 
        job_id, 
        BackupEntryStatus.SUCCESS, 
        datetime.now(timezone.utc) - timedelta(days=2)
    )
    new_entry = create_test_backup_entry(
        db, 
        job_id, 
        BackupEntryStatus.SUCCESS, 
        datetime.now(timezone.utc)
    )
    # Sauvegarde les ID avant de fermer la session pour éviter le DetachedInstanceError
    new_entry_id = new_entry.id
    old_entry_id = old_entry.id
    db.close()
    
    response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 2
    # Le plus récent doit être en premier
    assert entries[0]["id"] == new_entry_id
    assert entries[1]["id"] == old_entry_id
