import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)

def test_job_creation_and_entries_flow(client: TestClient, sample_job_data):
    """Teste le flux complet de création d'un job et de ses entrées."""
    logger.info("Test: Flux complet job et entrées")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201
    job_id = job_response.json()["id"]
    
    # 2. Vérifier que le job est bien créé
    get_job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_response.status_code == 200
    assert get_job_response.json()["database_name"] == sample_job_data["database_name"]
    
    # 3. Créer des entrées pour ce job
    db = SessionLocal()
    create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job_id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    db.close()
    
    # 4. Vérifier que les entrées sont bien associées au job
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200
    entries = entries_response.json()
    assert len(entries) == 2
    assert all(e["expected_job_id"] == job_id for e in entries)

def test_job_update_affects_entries(client: TestClient, sample_job_data):
    """Teste que la mise à jour d'un job n'affecte pas ses entrées existantes."""
    logger.info("Test: Mise à jour job et entrées existantes")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    job_id = job_response.json()["id"]
    
    # 2. Créer des entrées
    db = SessionLocal()
    entry = create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    db.close()
    
    # 3. Mettre à jour le job
    update_data = {
        "expected_hour_utc": 15,
        "backup_frequency": "weekly"
    }
    update_response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
    assert update_response.status_code == 200
    
    # 4. Vérifier que l'entrée existe toujours et n'a pas été modifiée
    entry_response = client.get(f"/api/v1/entries/{entry.id}")
    assert entry_response.status_code == 200
    assert entry_response.json()["expected_job_id"] == job_id

def test_job_deletion_cascade(client: TestClient, sample_job_data):
    """Teste que la suppression d'un job supprime aussi ses entrées."""
    logger.info("Test: Suppression job et cascade sur entrées")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    job_id = job_response.json()["id"]
    
    # 2. Créer des entrées
    db = SessionLocal()
    entry = create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    db.close()
    
    # 3. Supprimer le job
    delete_response = client.delete(f"/api/v1/jobs/{job_id}")
    assert delete_response.status_code == 204
    
    # 4. Vérifier que le job n'existe plus
    get_job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_response.status_code == 404
    
    # 5. Vérifier que l'entrée n'existe plus
    get_entry_response = client.get(f"/api/v1/entries/{entry.id}")
    assert get_entry_response.status_code == 404

def test_multiple_jobs_and_entries(client: TestClient, sample_job_data):
    """Teste la gestion de plusieurs jobs et leurs entrées."""
    logger.info("Test: Gestion de plusieurs jobs et entrées")
    
    # 1. Créer plusieurs jobs
    jobs = []
    for i in range(3):
        job_data = {**sample_job_data, "database_name": f"test_db_{i}"}
        job_response = client.post("/api/v1/jobs/", json=job_data)
        assert job_response.status_code == 201
        jobs.append(job_response.json()["id"])
    
    # 2. Créer des entrées pour chaque job
    db = SessionLocal()
    for job_id in jobs:
        create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
        create_test_backup_entry(db, job_id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    db.close()
    
    # 3. Vérifier que chaque job a ses entrées
    for job_id in jobs:
        entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
        assert entries_response.status_code == 200
        entries = entries_response.json()
        assert len(entries) == 2
        assert all(e["expected_job_id"] == job_id for e in entries)
    
    # 4. Vérifier que toutes les entrées sont listées
    all_entries_response = client.get("/api/v1/entries/")
    assert all_entries_response.status_code == 200
    all_entries = all_entries_response.json()
    assert len(all_entries) == 6  # 3 jobs * 2 entrées

def test_error_handling(client: TestClient):
    """Teste la gestion des erreurs dans l'API."""
    logger.info("Test: Gestion des erreurs")
    
    # 1. Test avec un ID invalide
    response = client.get("/api/v1/jobs/invalid_id")
    assert response.status_code == 422
    
    # 2. Test avec des données invalides pour la création
    invalid_data = {
        "database_name": "test_db",
        # Manque des champs requis
    }
    response = client.post("/api/v1/jobs/", json=invalid_data)
    assert response.status_code == 422
    
    # 3. Test avec des paramètres de pagination invalides
    response = client.get("/api/v1/entries/?limit=-1")
    assert response.status_code == 422
    
    # 4. Test avec un job_id invalide pour les entrées
    response = client.get("/api/v1/entries/by_job/invalid_id")
    assert response.status_code == 422 