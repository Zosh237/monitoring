# tests/test_api_integration.py
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
import logging

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job

logger = logging.getLogger(__name__)

def create_test_backup_entry(db, job_id: int, status: BackupEntryStatus, timestamp: datetime) -> BackupEntry:
    """
    Helper pour créer une entrée de sauvegarde de test.
    Utilise 'timestamp', 'agent_backup_hash_pre_compress' et 'agent_backup_size_pre_compress'
    conformément à la définition du modèle BackupEntry.
    """
    entry = BackupEntry(
        expected_job_id=job_id,
        status=status,
        timestamp=timestamp,
        agent_backup_hash_pre_compress="test_hash_sha256",
        agent_backup_size_pre_compress=1024,
        created_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def test_job_creation_and_entries_flow(client: TestClient, sample_job_data, test_db):
    """
    Teste le flux complet :
    1. Création d'un job via l'API.
    2. Vérification de la création du job (GET).
    3. Création d'entrées associées au job via la session 'test_db'.
    4. Vérification via l'API que ces entrées sont correctement associées au job.
    """
    logger.info("Test: Flux complet job et entrées")
    
    # 1. Créer un job via l'API
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Vérifier que le job est bien créé
    get_job_response = client.get(f"/api/v1/jobs/{job_id}")
    assert get_job_response.status_code == 200, get_job_response.text
    assert get_job_response.json()["database_name"] == sample_job_data["database_name"]
    
    # 3. Créer deux entrées pour ce job
    db = test_db  # La fixture 'test_db' fournit une session ouverte et commitée.
    create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job_id, BackupEntryStatus.FAILED, datetime.now(timezone.utc) - timedelta(days=1))
    
    # 4. Vérifier via l'API que 2 entrées sont associées au job
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 2, f"Attendu 2, obtenu {len(entries)}"
    assert all(e["expected_job_id"] == job_id for e in entries)

def test_job_update_affects_entries(client: TestClient, sample_job_data, test_db):
    """
    Teste que la mise à jour d'un job conserve intacte les entrées déjà créées.
    """
    logger.info("Test: Mise à jour d'un job et conservation des entrées")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Créer une entrée pour ce job
    db = test_db
    create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    
    # 3. Mettre à jour le job via l'API
    update_data = {
        "expected_hour_utc": 15,
        "expected_frequency": "weekly"
    }
    update_response = client.put(f"/api/v1/jobs/{job_id}", json=update_data)
    assert update_response.status_code == 200, update_response.text
    
    # 4. Vérifier que l'entrée est toujours présente
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 1, f"Attendu 1, obtenu {len(entries)}"
    assert entries[0]["expected_job_id"] == job_id

def test_job_deletion_cascade(client: TestClient, sample_job_data, test_db):
    """
    Teste que la suppression d'un job entraîne la suppression de ses entrées associées.
    """
    logger.info("Test: Suppression d'un job avec cascade sur les entrées")
    
    # 1. Créer un job
    job_response = client.post("/api/v1/jobs/", json=sample_job_data)
    assert job_response.status_code == 201, job_response.text
    job_id = job_response.json()["id"]
    
    # 2. Créer une entrée pour ce job
    db = test_db
    create_test_backup_entry(db, job_id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    
    # 3. Supprimer le job via l'API
    delete_response = client.delete(f"/api/v1/jobs/{job_id}")
    assert delete_response.status_code == 204, delete_response.text
    
    # 4. Vérifier via l'API que les entrées ont été supprimées
    entries_response = client.get(f"/api/v1/entries/by_job/{job_id}")
    assert entries_response.status_code == 200, entries_response.text
    entries = entries_response.json()
    assert len(entries) == 0, f"Attendu 0, obtenu {len(entries)}"

def test_multiple_jobs_and_entries(client: TestClient, sample_job_data, test_db):
    """
    Teste la création de plusieurs jobs et la gestion de leurs entrées.
    """
    logger.info("Test: Gestion de plusieurs jobs et leurs entrées")
    
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
    
    # 3. Vérifier que chaque job possède exactement 1 entrée
    for job in jobs:
        entries_response = client.get(f"/api/v1/entries/by_job/{job['id']}")
        assert entries_response.status_code == 200, entries_response.text
        entries = entries_response.json()
        assert len(entries) == 1, f"Pour le job {job['id']}, attendu 1 entrée, obtenu {len(entries)}"
        assert entries[0]["expected_job_id"] == job["id"]

def test_error_handling(client: TestClient):
    """
    Teste la gestion des erreurs dans l'API en vérifiant :
      - La création d'un job avec des données incomplètes renvoie 422.
      - Une requête GET pour un job avec un job_id <= 0 (ici 0) renvoie 422.
      - Des paramètres de pagination invalides (limit négatif) renvoient 422.
    """
    # 1. Tester la création avec des données invalides
    invalid_data = {
        "database_name": "test_db_invalid"
        # Les autres champs obligatoires sont absents
    }
    response = client.post("/api/v1/jobs/", json=invalid_data)
    assert response.status_code == 422, f"Attendu 422, obtenu {response.status_code}"

    # 2. Tester une requête GET avec un job_id incohérent (0, ce qui ne respecte pas gt=0)
    response = client.get("/api/v1/jobs/0")
    assert response.status_code == 422, f"Attendu 422 pour job_id<=0, obtenu {response.status_code}"

    # 3. Tester une requête GET sur les entrées avec un paramètre de pagination invalide
    response = client.get("/api/v1/entries/?limit=-1")
    assert response.status_code == 422, f"Attendu 422 pour limit négatif, obtenu {response.status_code}"
