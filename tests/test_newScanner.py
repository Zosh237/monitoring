import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, test_engine, TestSessionLocal
from app.services.new_scanner import NewBackupScanner
from app.models.models import ExpectedBackupJob, BackupEntry
from config.settings import settings  # Assurez-vous que c'est bien écrit ainsi

# === Configuration des tests ===

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Crée toutes les tables nécessaires pour les tests et les détruit à la fin."""
    Base.metadata.create_all(bind=test_engine)
    yield
    #Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def test_session():
    """Fixture pour une session de test avec une base isolée."""
    db = TestSessionLocal()
    yield db
    db.close()

@pytest.fixture
def temp_backup_dirs(tmp_path, monkeypatch):
    """Crée des dossiers temporaires pour les tests et met à jour les settings."""
    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    validated_path = tmp_path / "validated"
    validated_path.mkdir()

    # Utilisez directement l'objet settings (et non "config.settings.BACKUP_STORAGE_ROOT")
    monkeypatch.setattr(settings, "BACKUP_STORAGE_ROOT", str(backup_root))
    monkeypatch.setattr(settings, "VALIDATED_BACKUPS_BASE_PATH", str(validated_path))
    return backup_root, validated_path

def compute_hash(content: bytes) -> str:
    """Calcule le hash SHA-256 d'un contenu donné."""
    return hashlib.sha256(content).hexdigest()

def create_valid_agent_folder(backup_root: Path, agent_id: str, db_filename: str, db_content: bytes):
    """Crée l'arborescence d'un agent avec dossier 'log' et 'database'."""
    agent_dir = backup_root / agent_id
    agent_dir.mkdir()
    
    log_dir = agent_dir / "log"
    db_dir = agent_dir / "database"
    log_dir.mkdir()
    db_dir.mkdir()
    
    backup_file_path = db_dir / db_filename
    backup_file_path.write_bytes(db_content)
    
    file_hash = compute_hash(db_content)
    
    report = {
        "databases": {
            "test_db": {
                "staged_file_name": db_filename,
                "sha256_checksum": file_hash
            }
        }
    }
    json_report_path = log_dir / "report.json"
    json_report_path.write_text(json.dumps(report), encoding="utf-8")
    
    return agent_dir, backup_file_path, json_report_path

# === Tests ===

def test_new_scanner_success(temp_backup_dirs, test_session):
    """Test: Scanner détecte un backup valide et le classe en SUCCESS."""
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent1"
    db_filename = "backup.txt"
    content = b"Backup valid content"

    agent_dir, backup_file_path, json_report_path = create_valid_agent_folder(
        backup_root, agent_id, db_filename, content
    )

    job = ExpectedBackupJob(
        year=2025,
        company_name="Test Company",
        city="Test City",
        neighborhood="Test Zone",
        database_name="test_db",
        agent_id_responsible=agent_id,
        agent_deposit_path_template=f"/deposits/{agent_id}/db/",
        agent_log_deposit_path_template=f"/logs/{agent_id}/",
        final_storage_path_template=f"/storage/final/{db_filename}",
        current_status="UNKNOWN",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    test_session.add(job)
    test_session.commit()

    scanner = NewBackupScanner(test_session)
    scanner.scan()

    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "SUCCESS"

    promoted_file = validated_path / db_filename
    assert promoted_file.exists()

    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()

def test_new_scanner_missing_backup(temp_backup_dirs, test_session):
    """Test: Scanner classe un job en MISSING quand le backup est absent."""
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent2"
    db_filename = "backup.txt"

    agent_dir = backup_root / agent_id
    agent_dir.mkdir()
    log_dir = agent_dir / "log"
    db_dir = agent_dir / "database"
    log_dir.mkdir()
    db_dir.mkdir()

    report = {
        "databases": {
            "test_db": {
                "staged_file_name": db_filename,
                "sha256_checksum": "dummy_hash"
            }
        }
    }
    json_report_path = log_dir / "report.json"
    json_report_path.write_text(json.dumps(report), encoding="utf-8")

    job = ExpectedBackupJob(
        year=2025,
        company_name="Test Company",
        city="Test City",
        neighborhood="Test Zone",
        database_name="test_db",
        agent_id_responsible=agent_id,
        agent_deposit_path_template=f"/deposits/{agent_id}/db/",
        agent_log_deposit_path_template=f"/logs/{agent_id}/",
        final_storage_path_template=f"/storage/final/{db_filename}",
        current_status="UNKNOWN",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    test_session.add(job)
    test_session.commit()

    scanner = NewBackupScanner(test_session)
    scanner.scan()

    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "MISSING"

    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()

def test_new_scanner_hash_mismatch(temp_backup_dirs, test_session):
    """Test: Scanner classe un job en HASH_MISMATCH si le hash est incorrect."""
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent3"
    db_filename = "backup.txt"
    content = b"Original content"

    agent_dir, backup_file_path, json_report_path = create_valid_agent_folder(
        backup_root, agent_id, db_filename, content
    )

    report = {
        "databases": {
            "test_db": {
                "staged_file_name": db_filename,
                "sha256_checksum": "wronghash"
            }
        }
    }
    json_report_path.write_text(json.dumps(report), encoding="utf-8")

    job = ExpectedBackupJob(
        year=2025,
        company_name="Test Company",
        city="Test City",
        neighborhood="Test Zone",
        database_name="test_db",
        agent_id_responsible=agent_id,
        agent_deposit_path_template=f"/deposits/{agent_id}/db/",
        agent_log_deposit_path_template=f"/logs/{agent_id}/",
        final_storage_path_template=f"/storage/final/{db_filename}",
        current_status="UNKNOWN",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    test_session.add(job)
    test_session.commit()

    scanner = NewBackupScanner(test_session)
    scanner.scan()

    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "HASH_MISMATCH"

    promoted_file = validated_path / db_filename
    assert not promoted_file.exists()

    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()
