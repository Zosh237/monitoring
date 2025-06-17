import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app.main import app
from app.core.config import settings

# Construire les URL à partir des settings.
EXPECTED_JOBS_URL = f"{settings.API_V1_STR}/expected-backup-jobs"
BACKUP_ENTRIES_URL = f"{settings.API_V1_STR}/backup-entries"

client = TestClient(app)

# ---------------------------
# Tests pour ExpectedBackupJob endpoints
# ---------------------------
@pytest.fixture
def new_job_payload():
    return {
        "year": 2025,
        "company_name": "Test Company",
        "city": "Test City",
        "neighborhood": "Test Zone",
        "database_name": "test_db",
        "agent_id_responsible": "agent_1",
        "agent_deposit_path_template": "/deposits/{agent_id}/db/",
        "agent_log_deposit_path_template": "/logs/{agent_id}/",
        "final_storage_path_template": "/storage/final/",
        "current_status": "UNKNOWN",  # Même si on forcera le statut dans le CRUD, il faut respecter le schéma d'entrée.
        "last_checked_timestamp": None,
        "last_successful_backup_timestamp": None,
        "notification_recipients": "test@test.com",
        "is_active": True
    }

@pytest.fixture
def created_job(new_job_payload):
    response = client.post(f"{EXPECTED_JOBS_URL}/", json=new_job_payload)
    assert response.status_code == 201
    return response.json()

def test_create_expected_backup_job(new_job_payload):
    response = client.post(f"{EXPECTED_JOBS_URL}/", json=new_job_payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["company_name"] == new_job_payload["company_name"]
    assert "created_at" in data
    assert "updated_at" in data  # Vous devriez voir une valeur non nulle ou None selon la logique

def test_read_expected_backup_job(created_job):
    job_id = created_job["id"]
    response = client.get(f"{EXPECTED_JOBS_URL}/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == job_id
    assert data["company_name"] == created_job["company_name"]

def test_list_expected_backup_jobs(created_job):
    response = client.get(f"{EXPECTED_JOBS_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(job["id"] == created_job["id"] for job in data)

def test_update_expected_backup_job(created_job):
    job_id = created_job["id"]
    update_payload = {
        "city": "Updated City",
        "is_active": False
    }
    response = client.put(f"{EXPECTED_JOBS_URL}/{job_id}", json=update_payload)
    assert response.status_code == 200
    updated_data = response.json()
    assert updated_data["city"] == "Updated City"
    assert updated_data["is_active"] is False

def test_delete_expected_backup_job(created_job):
    job_id = created_job["id"]
    response = client.delete(f"{EXPECTED_JOBS_URL}/{job_id}")
    assert response.status_code == 204
    response = client.get(f"{EXPECTED_JOBS_URL}/{job_id}")
    assert response.status_code == 404

# ---------------------------
# Tests pour BackupEntry endpoints
# ---------------------------
@pytest.fixture
def new_backup_entry_payload(created_job):
    return {
        "expected_job_id": created_job["id"],
        "timestamp": datetime.now().isoformat(),
        "status": "SUCCESS",
        "message": "Backup successful",
        "operation_log_file_name": "status.json",
        "agent_id": "agent_1",
        "agent_overall_status": "OK",
        "server_calculated_staged_hash": "abcdef123456",
        "server_calculated_staged_size": 2048,
        "previous_successful_hash_global": "oldhashvalue",
        "hash_comparison_result": True
    }

@pytest.fixture
def created_backup_entry(new_backup_entry_payload):
    response = client.post(f"{BACKUP_ENTRIES_URL}/", json=new_backup_entry_payload)
    assert response.status_code == 201
    return response.json()

def test_create_backup_entry(new_backup_entry_payload):
    response = client.post(f"{BACKUP_ENTRIES_URL}/", json=new_backup_entry_payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == new_backup_entry_payload["status"]
    assert data["expected_job_id"] == new_backup_entry_payload["expected_job_id"]

def test_read_backup_entry(created_backup_entry):
    entry_id = created_backup_entry["id"]
    response = client.get(f"{BACKUP_ENTRIES_URL}/{entry_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == entry_id

def test_list_backup_entries(created_backup_entry):
    response = client.get(f"{BACKUP_ENTRIES_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(entry["id"] == created_backup_entry["id"] for entry in data)

def test_list_backup_entries_by_job(created_job, created_backup_entry):
    job_id = created_job["id"]
    response = client.get(f"{BACKUP_ENTRIES_URL}/by_job/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for entry in data:
        assert entry["expected_job_id"] == job_id
