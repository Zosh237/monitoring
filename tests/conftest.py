import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from datetime import datetime, timezone

# Patch du logging pour éviter l'erreur de config lors des tests
import logging.config
def fake_file_config(*args, **kwargs):
    pass
logging.config.fileConfig = fake_file_config

from app.main import app
from app.core.database import Base, get_db

# Configuration du logging pour les tests
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fixture pour la base de données SQLite en mémoire
@pytest.fixture(scope="module")
def test_db():
    """
    Crée une base de données SQLite en mémoire pour les tests.
    Chaque test module obtient sa propre base de données.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client(test_db):
    """
    Crée un client de test FastAPI pour interagir avec l'API.
    """
    with TestClient(app) as c:
        yield c

# Fixture pour les données de test communes
@pytest.fixture
def sample_job_data():
    """
    Fournit des données de test pour un job de sauvegarde.
    """
    return {
        "database_name": "test_db",
        "agent_id_responsible": "AGENT_TEST_001",
        "company_name": "TestCompany",
        "city": "TestCity",
        "expected_hour_utc": 12,
        "expected_minute_utc": 0,
        "backup_frequency": "daily",
        "final_storage_path_template": "/backups/{year}/{company}/{city}/{db}_backup.zip"
    }

@pytest.fixture
def sample_backup_entry_data():
    """
    Fournit des données de test pour une entrée de sauvegarde.
    """
    return {
        "status": "success",
        "agent_report_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "agent_reported_hash_sha256": "test_hash_123",
        "agent_reported_size_bytes": 1024,
        "agent_compress_size_pre_compress": 2048,
        "agent_compress_size_post_compress": 1024,
        "agent_transfer_process_status": True,
        "agent_transfer_process_start_time": datetime.now(timezone.utc).isoformat(),
        "agent_transfer_process_timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_staged_file_name": "test_backup.zip",
        "agent_logs_summary": "Test backup completed successfully",
        "server_calculated_staged_hash": "test_hash_123",
        "server_calculated_staged_size": 1024,
        "hash_comparison_result": True,
        "previous_successful_hash_global": "previous_hash_123"
    }
