# tests/test_api_expected_backup_jobs.py
import pytest
import logging

logger = logging.getLogger(__name__)

def test_create_expected_backup_job(client, unique_sample_job_data):
    """
    Teste la création d'un job de sauvegarde.
    """
    logger.info("Test: Création d'un job de sauvegarde")
    response = client.post("/api/v1/jobs/", json=unique_sample_job_data)
    assert response.status_code == 201, response.text
    created_job = response.json()
    
    assert created_job["database_name"] == unique_sample_job_data["database_name"]
    assert created_job["agent_id_responsible"] == unique_sample_job_data["agent_id_responsible"]
    # On attend que current_status soit défini par défaut, par exemple "UNKNOWN"
    assert created_job["current_status"] == "UNKNOWN"
    assert "id" in created_job
    assert "created_at" in created_job

def test_create_expected_backup_job_invalid_data(client):
    """
    Teste la création d'un job avec des données invalides.
    """
    logger.info("Test: Création d'un job avec données invalides")
    invalid_data = {
        "database_name": "test_db_invalid"
        # Plusieurs champs obligatoires sont manquants
    }
    response = client.post("/api/v1/jobs/", json=invalid_data)
    assert response.status_code == 422

def test_get_expected_backup_job(client, unique_sample_job_data):
    """
    Teste la récupération d'un job par ID.
    """
    logger.info("Test: Récupération d'un job par ID")
    create_response = client.post("/api/v1/jobs/", json=unique_sample_job_data)
    assert create_response.status_code == 201, create_response.text
    job = create_response.json()
    job_id = job["id"]
    
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200, response.text
    fetched_job = response.json()
    assert fetched_job["id"] == job_id
    assert fetched_job["database_name"] == unique_sample_job_data["database_name"]

def test_get_expected_backup_job_not_found(client):
    """
    Teste la récupération d'un job inexistant.
    """
    logger.info("Test: Récupération d'un job inexistant")
    response = client.get("/api/v1/jobs/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json().get("detail", "")

def test_get_all_expected_backup_jobs(client, unique_sample_job_data):
    """
    Teste la récupération de tous les jobs.
    """
    logger.info("Test: Récupération de tous les jobs")
    client.post("/api/v1/jobs/", json=unique_sample_job_data)
    second_job = unique_sample_job_data.copy()
    second_job["database_name"] = unique_sample_job_data["database_name"] + "_2"
    client.post("/api/v1/jobs/", json=second_job)
    
    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200, response.text
    jobs = response.json()
    assert len(jobs) >= 2

def test_update_expected_backup_job(client, unique_sample_job_data):
    """
    Teste la mise à jour d'un job.
    """
    logger.info("Test: Mise à jour d'un job")
    create_response = client.post("/api/v1/jobs/", json=unique_sample_job_data)
    assert create_response.status_code == 201, create_response.text
    job = create_response.json()
    job_id = job["id"]
    
    update_data = {
        "expected_hour_utc": 15,
        "expected_frequency": "weekly"
    }
    response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
    assert response.status_code == 200, response.text
    updated_job = response.json()
    assert updated_job["expected_hour_utc"] == update_data["expected_hour_utc"]
    assert updated_job["expected_frequency"] == update_data["expected_frequency"]

def test_update_expected_backup_job_not_found(client):
    """
    Teste la mise à jour d'un job inexistant.
    """
    logger.info("Test: Mise à jour d'un job inexistant")
    update_data = {"expected_hour_utc": 15, "expected_frequency": "weekly"}
    response = client.put("/api/v1/jobs/99999", json=update_data)
    assert response.status_code == 404
    assert "Job non trouvé" in response.json().get("detail", "")

def test_delete_expected_backup_job(client, unique_sample_job_data):
    """
    Teste la suppression d'un job.
    """
    logger.info("Test: Suppression d'un job")
    create_response = client.post("/api/v1/jobs/", json=unique_sample_job_data)
    assert create_response.status_code == 201, create_response.text
    job_id = create_response.json()["id"]
    
    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 204
    
    get_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_response.status_code == 404

def test_delete_expected_backup_job_not_found(client):
    """
    Teste la suppression d'un job inexistant.
    """
    logger.info("Test: Suppression d'un job inexistant")
    response = client.delete("/api/v1/jobs/99999")
    assert response.status_code == 404
    assert "Job non trouvé" in response.json().get("detail", "")

def test_pagination_expected_backup_jobs(client, unique_sample_job_data):
    """
    Teste la pagination des jobs.
    """
    logger.info("Test: Pagination des jobs")
    # Créer 15 jobs avec un database_name différent
    for i in range(15):
        job_data = unique_sample_job_data.copy()
        job_data["database_name"] = f"{unique_sample_job_data['database_name']}_{i}"
        client.post("/api/v1/jobs/", json=job_data)
    
    # Test avec limit=10 : doit retourner 10 jobs
    response = client.get("/api/v1/jobs/?limit=10")
    assert response.status_code == 200, response.text
    jobs = response.json()
    assert len(jobs) == 10, f"Attendu 10 jobs, obtenu {len(jobs)}"
    
    # Test avec skip=10, limit=10 : sur 15 jobs, doit retourner 5 jobs
    response = client.get("/api/v1/jobs/?skip=10&limit=10")
    assert response.status_code == 200, response.text
    jobs = response.json()
    assert len(jobs) == 5, f"Attendu 5 jobs, obtenu {len(jobs)}"
