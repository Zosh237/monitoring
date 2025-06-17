# app/services/test_new_scanner.py
import os
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

# Import du scanner et des modèles
from app.services.new_scanner import NewBackupScanner
from app.models.models import ExpectedBackupJob, BackupEntry
from config.settings import settings

# === Fixtures de configuration et de session pour tester le scanner ===

@pytest.fixture
def temp_backup_dirs(tmp_path, monkeypatch):
    """
    Crée des dossiers temporaires pour BACKUP_STORAGE_ROOT et VALIDATED_BACKUPS_BASE_PATH,
    ensuite met à jour les settings via monkeypatch.
    """
    backup_root = tmp_path / "backups"
    backup_root.mkdir()
    validated_path = tmp_path / "validated"
    validated_path.mkdir()

    # Surclasse la config pour les tests
    monkeypatch.setattr(settings, "BACKUP_STORAGE_ROOT", str(backup_root))
    monkeypatch.setattr(settings, "VALIDATED_BACKUPS_BASE_PATH", str(validated_path))
    return backup_root, validated_path

@pytest.fixture
def test_session():
    """
    Fixture pour fournir une session SQLAlchemy de test.
    Ici on suppose l'utilisation d'un engine de test (en mémoire ou dédié aux tests).
    """
    from app.core.database import engine  # adapte ceci selon ton implémentation de SessionLocal
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def compute_hash(content: bytes) -> str:
    """Calcule le hash SHA-256 d'un contenu donné."""
    return hashlib.sha256(content).hexdigest()

def create_valid_agent_folder(backup_root: Path, agent_id: str, db_filename: str, db_content: bytes):
    """
    Crée l'arborescence d'un agent avec dossier 'log' et 'database'.
    Écrit un backup dans 'database' et un rapport JSON dans 'log'.
    Le rapport contient les informations obligatoires : 'staged_file_name' et 'sha256_checksum'.
    """
    agent_dir = backup_root / agent_id
    agent_dir.mkdir()
    
    log_dir = agent_dir / "log"
    db_dir = agent_dir / "database"
    log_dir.mkdir()
    db_dir.mkdir()
    
    # Créer le fichier de backup dans database/
    backup_file_path = db_dir / db_filename
    backup_file_path.write_bytes(db_content)
    
    # Calculer le hash du backup
    file_hash = compute_hash(db_content)
    
    # Créer le rapport JSON dans log/
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

# === Tests du scanner ===

def test_new_scanner_success(temp_backup_dirs, test_session):
    """
    Scénario SUCCESS :
      - Le backup existe dans l'arborescence et le hash correspond.
      - Une BackupEntry avec le statut 'SUCCESS' doit être créée,
      - Le backup est copié dans le dossier VALIDATED_BACKUPS_BASE_PATH,
      - Le rapport JSON est archivé dans le sous-dossier '_archive'.
    """
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent1"
    db_filename = "backup.txt"
    content = b"Backup valid content"
    
    # Création de l'arborescence pour l'agent avec rapport valide
    agent_dir, backup_file_path, json_report_path = create_valid_agent_folder(
        backup_root, agent_id, db_filename, content
    )
    
    # Créer l'ExpectedBackupJob avec les champs obligatoires
    job = ExpectedBackupJob(agent_id_responsible=agent_id, database_name="test_db")
    test_session.add(job)
    test_session.commit()
    
    # Exécuter le scanner
    scanner = NewBackupScanner(test_session)
    scanner.scan()
    
    # Vérifier la création d'une BackupEntry avec statut SUCCESS
    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "SUCCESS"
    
    # Vérifier la copie du backup dans VALIDATED_BACKUPS_BASE_PATH
    promoted_file = validated_path / db_filename
    assert promoted_file.exists()
    
    # Vérifier l'archivage du rapport JSON
    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()

def test_new_scanner_missing_backup(temp_backup_dirs, test_session):
    """
    Scénario MISSING :
      - Le rapport mentionne un backup via 'staged_file_name', mais le fichier n'existe pas dans 'database'.
      - Une BackupEntry avec le statut 'MISSING' doit être créée,
      - Le rapport JSON doit être archivé.
    """
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent2"
    db_filename = "backup.txt"
    
    # Création de l'arborescence avec dossier log et database, mais sans backup dans database
    agent_dir = backup_root / agent_id
    agent_dir.mkdir()
    log_dir = agent_dir / "log"
    db_dir = agent_dir / "database"
    log_dir.mkdir()
    db_dir.mkdir()

    # Créer un rapport JSON indiquant la présence d'un backup non existant
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
    
    # Insertion d'un ExpectedBackupJob minimal
    job = ExpectedBackupJob(agent_id_responsible=agent_id, database_name="test_db")
    test_session.add(job)
    test_session.commit()
    
    scanner = NewBackupScanner(test_session)
    scanner.scan()
    
    # Vérifier que le job est marqué MISSING
    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "MISSING"
    
    # Vérifier l'archivage du rapport JSON
    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()

def test_new_scanner_hash_mismatch(temp_backup_dirs, test_session):
    """
    Scénario HASH_MISMATCH :
      - Le backup existe dans l'arborescence, mais le hash calculé ne correspond pas à celui attendu dans le rapport.
      - Une BackupEntry avec le statut 'HASH_MISMATCH' doit être créée,
      - Aucun fichier ne doit être copié dans VALIDATED_BACKUPS_BASE_PATH.
      - Le rapport JSON doit être archivé.
    """
    backup_root, validated_path = temp_backup_dirs
    agent_id = "agent3"
    db_filename = "backup.txt"
    content = b"Original content"

    # Création de l'arborescence avec un rapport valide
    agent_dir, backup_file_path, json_report_path = create_valid_agent_folder(
        backup_root, agent_id, db_filename, content
    )
    
    # Modifier le rapport JSON pour forcer un hash incorrect
    report = {
        "databases": {
            "test_db": {
                "staged_file_name": db_filename,
                "sha256_checksum": "wronghash"
            }
        }
    }
    json_report_path.write_text(json.dumps(report), encoding="utf-8")
    
    # Insertion de l'ExpectedBackupJob minimal
    job = ExpectedBackupJob(agent_id_responsible=agent_id, database_name="test_db")
    test_session.add(job)
    test_session.commit()
    
    scanner = NewBackupScanner(test_session)
    scanner.scan()
    
    entry = test_session.query(BackupEntry).filter_by(expected_job_id=job.id).first()
    assert entry is not None
    assert entry.status == "HASH_MISMATCH"
    
    # Vérifier qu'aucun fichier n'a été copié dans le dossier de validation
    promoted_file = validated_path / db_filename
    assert not promoted_file.exists()
    
    archive_dir = json_report_path.parent / "_archive"
    archived_file = archive_dir / json_report_path.name
    assert archived_file.exists()
