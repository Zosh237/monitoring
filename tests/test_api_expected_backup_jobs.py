import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from app.models.models import ExpectedBackupJob, JobStatus, BackupFrequency
from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate

logger = logging.getLogger(__name__)

def test_create_expected_backup_job(client: TestClient, sample_job_data):
    """Teste la création d'un job de sauvegarde."""
    logger.info("Test: Création d'un job de sauvegarde")
    response = client.post("/api/v1/jobs/", json=sample_job_data)
    
    assert response.status_code == 201
    created_job = response.json()
    
    assert created_job["database_name"] == sample_job_data["database_name"]
    assert created_job["agent_id_responsible"] == sample_job_data["agent_id_responsible"]
    assert created_job["current_status"] == JobStatus.UNKNOWN.value
    assert "id" in created_job
    assert "created_at" in created_job

def test_create_expected_backup_job_invalid_data(client: TestClient):
    """Teste la création d'un job avec des données invalides."""
    logger.info("Test: Création d'un job avec données invalides")
    invalid_data = {
        "database_name": "test_db",
        # Manque des champs requis
    }
    response = client.post("/api/v1/jobs/", json=invalid_data)
    assert response.status_code == 422

def test_get_expected_backup_job(client: TestClient, sample_job_data):
    """Teste la récupération d'un job par ID."""
    logger.info("Test: Récupération d'un job par ID")
    # Créer d'abord un job
    create_response = client.post("/api/v1/jobs/", json=sample_job_data)
    job_id = create_response.json()["id"]
    
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    job = response.json()
    assert job["id"] == job_id
    assert job["database_name"] == sample_job_data["database_name"]

def test_get_expected_backup_job_not_found(client: TestClient):
    """Teste la récupération d'un job inexistant."""
    logger.info("Test: Récupération d'un job inexistant")
    response = client.get("/api/v1/jobs/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json()["detail"]

def test_get_all_expected_backup_jobs(client: TestClient, sample_job_data):
    """Teste la récupération de tous les jobs."""
    logger.info("Test: Récupération de tous les jobs")
    # Créer plusieurs jobs
    client.post("/api/v1/jobs/", json=sample_job_data)
    client.post("/api/v1/jobs/", json={**sample_job_data, "database_name": "test_db_2"})
    
    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 2

def test_update_expected_backup_job(client: TestClient, sample_job_data):
    """Teste la mise à jour d'un job."""
    logger.info("Test: Mise à jour d'un job")
    # Créer d'abord un job
    create_response = client.post("/api/v1/jobs/", json=sample_job_data)
    job_id = create_response.json()["id"]
    
    update_data = {
        "expected_hour_utc": 15,
        "backup_frequency": "weekly"
    }
    response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
    assert response.status_code == 200
    updated_job = response.json()
    assert updated_job["expected_hour_utc"] == update_data["expected_hour_utc"]
    assert updated_job["backup_frequency"] == update_data["backup_frequency"]

def test_update_expected_backup_job_not_found(client: TestClient):
    """Teste la mise à jour d'un job inexistant."""
    logger.info("Test: Mise à jour d'un job inexistant")
    update_data = {"expected_hour_utc": 15}
    response = client.put("/api/v1/jobs/99999", json=update_data)
    assert response.status_code == 404
    assert "Job non trouvé" in response.json()["detail"]

def test_delete_expected_backup_job(client: TestClient, sample_job_data):
    """Teste la suppression d'un job."""
    logger.info("Test: Suppression d'un job")
    # Créer d'abord un job
    create_response = client.post("/api/v1/jobs/", json=sample_job_data)
    job_id = create_response.json()["id"]
    
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 204
    
    # Vérifier que le job n'existe plus
    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 404

def test_delete_expected_backup_job_not_found(client: TestClient):
    """Teste la suppression d'un job inexistant."""
    logger.info("Test: Suppression d'un job inexistant")
    response = client.delete("/api/v1/jobs/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json()["detail"]

def test_pagination_expected_backup_jobs(client: TestClient, sample_job_data):
    """Teste la pagination des jobs."""
    logger.info("Test: Pagination des jobs")
    # Créer plusieurs jobs
    for i in range(15):
        client.post("/api/v1/jobs/", json={**sample_job_data, "database_name": f"test_db_{i}"})
    
    # Test avec limite de 10
    response = client.get("/api/v1/jobs/?limit=10")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 10
    
    # Test avec skip
    response = client.get("/api/v1/jobs/?skip=10&limit=10")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) == 5  # Il ne reste que 5 jobs après avoir sauté les 10 premiers 