import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
import os
import json
from sqlalchemy.orm import Session

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.services.scanner import BackupScanner, ScannerError
from app.services.validation_service import StatusFileValidationError
from app.utils.crypto import CryptoUtilityError
from app.utils.file_operations import FileOperationError
from app.utils.datetime_utils import DateTimeUtilityError
from config.settings import settings

@pytest.fixture
def mock_db_session():
    """Fixture pour créer une session de base de données mock."""
    session = Mock(spec=Session)
    return session

@pytest.fixture
def mock_job():
    """Fixture pour créer un job de sauvegarde mock."""
    return ExpectedBackupJob(
        id=1,
        database_name="test_db",
        company_name="test_company",
        city="test_city",
        neighborhood="test_neighborhood",
        expected_hour_utc=12,
        expected_minute_utc=0,
        is_active=True,
        current_status=JobStatus.OK
    )

@pytest.fixture
def mock_status_file_data():
    """Fixture pour créer des données de fichier STATUS.json mock."""
    return {
        "operation_timestamp": datetime.now(timezone.utc).isoformat(),
        "databases": {
            "test_db": {
                "status": "success",
                "staged_file_path": "/path/to/staged/file.bak",
                "staged_file_hash": "abc123",
                "staged_file_size": 1000
            }
        }
    }

def test_scanner_initialization(mock_db_session):
    """Test l'initialisation du scanner."""
    scanner = BackupScanner(mock_db_session)
    assert scanner.db == mock_db_session
    assert isinstance(scanner.processed_status_reports_in_this_run, set)

@patch('app.services.scanner.os.path.exists')
@patch('app.services.scanner.os.listdir')
def test_scan_all_jobs_no_agent_data(mock_listdir, mock_exists, mock_db_session, mock_job):
    """Test le scan quand il n'y a pas de données d'agent."""
    mock_exists.return_value = False
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_job]
    
    scanner = BackupScanner(mock_db_session)
    scanner._create_missing_entry_for_job_if_needed = Mock()
    scanner.scan_all_jobs()
    
    scanner._create_missing_entry_for_job_if_needed.assert_called_once_with(
        mock_job,
        "Le chemin de dépôt des agents est vide ou inaccessible. Sauvegarde manquante."
    )

@patch('app.services.scanner.os.path.exists')
@patch('app.services.scanner.os.listdir')
@patch('app.services.scanner.validate_status_file')
def test_scan_all_jobs_with_valid_status_file(
    mock_validate_status_file,
    mock_listdir,
    mock_exists,
    mock_db_session,
    mock_job,
    mock_status_file_data
):
    """Test le scan avec un fichier STATUS.json valide."""
    mock_exists.return_value = True
    mock_listdir.return_value = ["test_company_test_city_test_neighborhood"]
    mock_validate_status_file.return_value = mock_status_file_data
    
    mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_job]
    
    scanner = BackupScanner(mock_db_session)
    scanner._process_single_db_from_status_data = Mock()
    scanner._archive_status_file = Mock()
    
    scanner.scan_all_jobs()
    
    scanner._process_single_db_from_status_data.assert_called_once()
    scanner._archive_status_file.assert_called_once()

def test_create_missing_entry(mock_db_session, mock_job):
    """Test la création d'une entrée manquante."""
    scanner = BackupScanner(mock_db_session)
    scanner._save_backup_entry_and_update_job = Mock()
    
    scanner._create_missing_entry(mock_job, "Test message")
    
    scanner._save_backup_entry_and_update_job.assert_called_once()
    call_args = scanner._save_backup_entry_and_update_job.call_args[1]
    assert call_args["entry_status"] == BackupEntryStatus.MISSING
    assert call_args["entry_message"] == "Test message"

@patch('app.services.scanner.get_utc_now')
def test_create_missing_entry_for_job_if_needed(
    mock_get_utc_now,
    mock_db_session,
    mock_job
):
    """Test la création conditionnelle d'une entrée manquante."""
    now = datetime.now(timezone.utc)
    mock_get_utc_now.return_value = now
    
    scanner = BackupScanner(mock_db_session)
    scanner._create_missing_entry = Mock()
    
    # Test avec un job qui n'a pas été vérifié récemment
    mock_job.last_checked_timestamp = now - timedelta(days=2)
    scanner._create_missing_entry_for_job_if_needed(mock_job)
    
    scanner._create_missing_entry.assert_called_once()

def test_perform_post_scan_actions(mock_db_session, mock_job):
    """Test les actions post-scan."""
    scanner = BackupScanner(mock_db_session)
    
    with patch('app.services.scanner.promote_backup') as mock_promote:
        mock_promote.return_value = "/path/to/promoted/file.bak"
        scanner._perform_post_scan_actions(
            mock_job,
            BackupEntryStatus.SUCCESS,
            "/path/to/staged/file.bak"
        )
        mock_promote.assert_called_once_with(
            "/path/to/staged/file.bak",
            mock_job
        )

def test_archive_status_file(mock_db_session):
    """Test l'archivage d'un fichier STATUS.json."""
    scanner = BackupScanner(mock_db_session)
    
    with patch('app.services.scanner.move_file') as mock_move:
        scanner._archive_status_file(
            "/path/to/status.json",
            "/path/to/archive"
        )
        mock_move.assert_called_once()
