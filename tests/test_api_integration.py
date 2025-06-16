import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import logging

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job

logger = logging.getLogger(__name__)

def create_test_backup_entry(db, job_id: int, status: BackupEntryStatus, timestamp: datetime):
    """
    Helper pour créer une entrée de sauvegarde de test.
    Note : ici, on utilise 'agent_report_timestamp_utc' plutôt que 'timestamp'
    et on stocke des valeurs de test pour le hash et la taille.
    """
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

def test_job_creation_and_entries_flow(client: TestClient, sample_job_data, test_db):
    """
    Teste le flux complet de création d'un job et de ses entrées.
    1. Crée un job via l'API.
    2. Vérifie que le job est bien enregistré (GET).
    3. Crée des entrées associées à ce job directement via la session.
    4. Vérifie via l'API que ces entrées sont associées au job.
    """
    logger.info("Test: Flux complet job et entrées")
    
    # 1. Créer un job via l'API
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Vérifier la création du job
    get_job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_response.status_code == 200, get_job_response.text
    assert get_job_response.json()["database_name"] == sample_job_data["database_name"]
    
    # 3. Créer deux entrées pour ce job
    create_test_backup_entry(test_db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(test_db, job_id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    
    # 4. Vérifier via l'API que 2 entrées sont associées au job
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 2, f"Attendu 2, obtenu {len(entries)}"
    assert all(e["expected_job_id"] == job_id for e in entries)

def test_job_update_affects_entries(client: TestClient, sample_job_data, test_db):
    """
    Teste que la mise à jour d'un job n'affecte pas ses entrées existantes.
    """
    logger.info("Test: Mise à jour job et entrées existantes")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Créer une entrée pour ce job
    create_test_backup_entry(test_db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    
    # 3. Mettre à jour le job
    update_data = {
        "expected_hour_utc": 15,
        "expected_frequency": "weekly"
    }
    update_response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
    assert update_response.status_code == 200, update_response.text
    
    # 4. Vérifier que l'entrée existe toujours
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 1, f"Attendu 1, obtenu {len(entries)}"
    assert entries[0]["expected_job_id"] == job_id

def test_job_deletion_cascade(client: TestClient, sample_job_data, test_db):
    """
    Teste que la suppression d'un job supprime aussi ses entrées.
    """
    logger.info("Test: Suppression job et cascade sur entrées")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Créer une entrée pour ce job
    create_test_backup_entry(test_db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    
    # 3. Supprimer le job
    delete_response = client.delete(f"/api/v1/jobs/{job_id}")
    assert delete_response.status_code == 204, delete_response.text
    
    # 4. Vérifier que les entrées ont également été supprimées
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 0, f"Attendu 0, obtenu {len(entries)}"

def test_multiple_jobs_and_entries(client: TestClient, sample_job_data, test_db):
    """
    Teste la gestion de plusieurs jobs et de leurs entrées.
    """
    logger.info("Test: Gestion de plusieurs jobs et entrées")
    
    jobs = []
    # 1. Créer 3 jobs uniques
    for i in range(3):
        job_data = {**sample_job_data, "database_name": f"test_db_{i}"}
        job_response = client.post("/api/v1/jobs/", json=job_data)
        assert job_response.status_code == 201, job_response.text
        jobs.append(job_response.json())
    
    # 2. Créer une entrée pour chaque job
    for job in jobs:
        create_test_backup_entry(test_db, job["id"], BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    
    # 3. Vérifier que chaque job a 1 entrée
    for job in jobs:
        entries_response = client.get(f"/api/v1/entries/by_job/{job['id']}")
        assert entries_response.status_code == 200, entries_response.text
        entries = entries_response.json()
        assert len(entries) == 1, f"Pour le job {job['id']}, attendu 1 entrée, obtenu {len(entries)}"
        assert entries[0]["expected_job_id"] == job["id"]

def test_error_handling(client: TestClient):
    """
    Teste la gestion des erreurs dans l'API.
    Note : Si votre API est censée valider que l'ID de chemin est un entier,
    alors "/api/v1/jobs/invalid" devrait retourner une erreur de validation (422).
    Sinon, adaptez ce test aux comportements réels de l'API.
    """
    logger.info("Test: Gestion des erreurs")
    
    # Test pour un ID invalide, on s'attend à 422 si le paramètre est typé en int dans la route.
    response = client.get("/api/v1/jobs/invalid")
    assert response.status_code == 422, f"Statut attendu 422, obtenu {response.status_code}"
    
    invalid_data = {
        "database_name": "test_db_invalid"
        # Omettant des champs obligatoires, on s'attend à un 422.
    }
    response = client.post("/api/v1/jobs/", json=invalid_data)
    assert response.status_code == 422, f"Statut attendu 422, obtenu {response.status_code}"
    
    response = client.get("/api/v1/entries/?limit=-1")
    assert response.status_code == 422, f"Statut attendu 422, obtenu {response.status_code}"
    
    response = client.get("/api/v1/entries/by_job/invalid")
    assert response.status_code == 422, f"Statut attendu 422, obtenu {response.status_code}"
