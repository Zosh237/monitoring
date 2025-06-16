# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine, SessionLocal
from app.models.models import ExpectedBackupJob, BackupEntry
from app.main import app  # L'application FastAPI

# --- Création du schéma avant la session de test ---
@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Crée toutes les tables nécessaires pour les tests au début d'une session
    et les détruit à la fin.
    """
    # Assurez-vous que tous les modèles sont importés pour être inclus dans Base.metadata
    Base.metadata.create_all(bind=engine)
    print("Tables créées :", list(Base.metadata.tables.keys()))
    yield
    Base.metadata.drop_all(bind=engine)

# --- Nettoyage des tables avant chaque test ---
@pytest.fixture(autouse=True)
def clean_tables():
    """
    Vide les tables ExpectedBackupJob et BackupEntry avant chaque test
    afin de garantir un environnement propre.
    """
    db = SessionLocal()
    db.query(BackupEntry).delete()
    db.query(ExpectedBackupJob).delete()
    db.commit()
    db.close()
    yield

# --- Fourniture d'un client FastAPI ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

# --- Fixture pour des données de test complètes pour ExpectedBackupJob ---
@pytest.fixture
def sample_job_data():
    return {
        "database_name": "test_db",
        "agent_id_responsible": "AGENT_TEST_001",
        "company_name": "TestCompany",
        "city": "TestCity",
        "year": 2025,
        "neighborhood": "Akwa",
        "expected_hour_utc": 12,
        "expected_minute_utc": 0,
        "expected_frequency": "daily",  # Champ obligatoire désormais
        "final_storage_path_template": "/backups/{year}/{company}/{city}/{db}_backup.zip",
        "agent_deposit_path_template": "/depot/{company}/{city}/{db}/",
        "agent_log_deposit_path_template": "/logs/{agent_id}/",
        "days_of_week": "Mon,Tue,Wed,Thu,Fri"
    }

# --- Fixture pour rendre les données uniques par test ---
@pytest.fixture
def unique_sample_job_data(sample_job_data, request):
    """
    Renvoie une copie de sample_job_data avec des valeurs uniques pour
    éviter les conflits d'unicité (par exemple, dans company_name et database_name).
    """
    data = sample_job_data.copy()
    suffix = "_" + request.node.name
    data["company_name"] += suffix
    data["database_name"] += suffix
    return data

# --- Optionnel : Fixture pour des données de test pour BackupEntry ---
@pytest.fixture
def sample_backup_entry_data():
    return {
        "agent_backup_hash_pre_compress": "test_hash_sha256",
        "agent_backup_size_pre_compress": 1024,
        # D'autres champs optionnels peuvent être ajoutés ici si besoin.
    }
