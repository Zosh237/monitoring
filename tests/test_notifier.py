import pytest
import logging
from unittest.mock import MagicMock, patch
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from datetime import datetime, timezone

# Ajustez le répertoire racine du projet au PYTHONPATH.
import sys
import os
sys.path.append(os.path.abspath('.'))

# Importe les modules à tester
from app.services.notifier import send_email_notification, notify_backup_status_change, NotificationError
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from config.settings import settings as app_settings # Renomme pour éviter le conflit avec la fixture

# Configuration du logging pour les tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Couleurs pour les logs de test
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'

@pytest.fixture
def mock_smtp_server():
    """
    Fixture pour mocker l'objet smtplib.SMTP.
    """
    with patch('smtplib.SMTP') as mock_smtp:
        mock_instance = MagicMock()
        mock_smtp.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def setup_email_settings():
    """
    Fixture pour configurer temporairement les paramètres d'e-mail dans les settings.
    """
    original_host = app_settings.EMAIL_HOST
    original_port = app_settings.EMAIL_PORT
    original_username = app_settings.EMAIL_USERNAME
    original_password = app_settings.EMAIL_PASSWORD
    original_sender = app_settings.EMAIL_SENDER
    original_recipient = app_settings.ADMIN_EMAIL_RECIPIENT

    app_settings.EMAIL_HOST = "smtp.test.com"
    app_settings.EMAIL_PORT = 587
    app_settings.EMAIL_USERNAME = "test_user"
    app_settings.EMAIL_PASSWORD = "test_password"
    app_settings.EMAIL_SENDER = "sender@test.com"
    app_settings.ADMIN_EMAIL_RECIPIENT = "admin@example.com"

    yield

    # Restaure les paramètres originaux après le test
    app_settings.EMAIL_HOST = original_host
    app_settings.EMAIL_PORT = original_port
    app_settings.EMAIL_USERNAME = original_username
    app_settings.EMAIL_PASSWORD = original_password
    app_settings.EMAIL_SENDER = original_sender
    app_settings.ADMIN_EMAIL_RECIPIENT = original_recipient

@pytest.fixture
def mock_job_entry():
    """
    Fixture pour un ExpectedBackupJob et un BackupEntry mockés.
    """
    job = MagicMock(spec=ExpectedBackupJob)
    job.id = 1
    job.database_name = "test_db"
    job.agent_id_responsible = "AGENT_XYZ_ABC"
    job.company_name = "TestCorp"
    job.city = "TestCity"
    job.current_status = JobStatus.FAILED

    entry = MagicMock(spec=BackupEntry)
    entry.id = 101
    entry.status = BackupEntryStatus.FAILED
    entry.agent_report_timestamp_utc = datetime(2025, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
    entry.agent_transfer_error_message = "Simulated transfer error."
    entry.agent_reported_hash_sha256 = "hash_agent"
    entry.server_calculated_staged_hash = "hash_server"
    entry.agent_reported_size_bytes = 12345
    entry.server_calculated_staged_size = 54321
    entry.hash_comparison_result = True # True indique une non-concordance
    entry.agent_logs_summary = "Some logs summary."

    return job, entry

# --- Tests pour send_email_notification ---

def test_send_email_notification_success(mock_smtp_server, setup_email_settings, caplog):
    """
    Teste l'envoi réussi d'un e-mail.
    """
    logger.info(f"{COLOR_BLUE}--- Test: send_email_notification succès ---{COLOR_RESET}")
    recipient = "test@example.com"
    subject = "Test Subject"
    body = "Test Body"

    with caplog.at_level(logging.INFO):
        send_email_notification(recipient, subject, body)

        mock_smtp_server.starttls.assert_called_once()
        mock_smtp_server.login.assert_called_once_with(app_settings.EMAIL_USERNAME, app_settings.EMAIL_PASSWORD)
        mock_smtp_server.sendmail.assert_called_once()
        mock_smtp_server.quit.assert_called_once()

        assert f"E-mail de notification envoyé à '{recipient}' avec le sujet : '{subject}'" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ E-mail envoyé avec succès.{COLOR_RESET}")

def test_send_email_notification_smtp_failure(mock_smtp_server, setup_email_settings, caplog):
    """
    Teste la gestion des erreurs SMTP lors de l'envoi d'un e-mail.
    """
    logger.info(f"{COLOR_BLUE}--- Test: send_email_notification échec SMTP ---{COLOR_RESET}")
    mock_smtp_server.login.side_effect = smtplib.SMTPAuthenticationError(535, "Auth failed")

    recipient = "test@example.com"
    subject = "Test Subject"
    body = "Test Body"

    with caplog.at_level(logging.ERROR):
        with pytest.raises(NotificationError) as excinfo:
            try:
                send_email_notification(recipient, subject, body)
            finally:
                mock_smtp_server.quit.assert_called_once() # Vérifie que quit est appelé même en cas d'erreur

        assert "Échec de l'envoi de l'e-mail (SMTP)" in str(excinfo.value)
        assert f"Erreur SMTP lors de l'envoi de l'e-mail à '{recipient}'" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ L'erreur SMTP a été capturée et loguée.{COLOR_RESET}")

def test_send_email_notification_missing_settings(mock_smtp_server, caplog):
    """
    Teste qu'aucun e-mail n'est envoyé si les paramètres sont manquants.
    """
    logger.info(f"{COLOR_BLUE}--- Test: send_email_notification paramètres manquants ---{COLOR_RESET}")
    # Vide les paramètres d'e-mail pour ce test
    original_host = app_settings.EMAIL_HOST
    app_settings.EMAIL_HOST = None

    recipient = "test@example.com"
    subject = "Test Subject"
    body = "Test Body"

    with caplog.at_level(logging.WARNING):
        send_email_notification(recipient, subject, body)

        mock_smtp_server.assert_not_called() # Aucune interaction avec smtplib
        assert "Paramètres d'e-mail SMTP non configurés. La notification par e-mail est désactivée." in caplog.text
        logger.info(f"{COLOR_GREEN}✓ Aucune tentative d'envoi si les paramètres sont manquants.{COLOR_RESET}")
    
    app_settings.EMAIL_HOST = original_host # Restaure le paramètre

# --- Tests pour notify_backup_status_change ---

@patch('app.services.notifier.send_email_notification')
def test_notify_backup_status_change_failed(mock_send_email, mock_job_entry, caplog, setup_email_settings):
    """
    Teste que notify_backup_status_change envoie un e-mail pour un statut FAILED.
    """
    logger.info(f"{COLOR_BLUE}--- Test: notify_backup_status_change - FAILED ---{COLOR_RESET}")
    job, entry = mock_job_entry
    entry.status = BackupEntryStatus.FAILED
    job.current_status = JobStatus.FAILED

    with caplog.at_level(logging.INFO):
        notify_backup_status_change(job, entry)

        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        
        assert args[0] == app_settings.ADMIN_EMAIL_RECIPIENT
        assert "ALERTE SAUVEGARDE - test_db - FAILED" in args[1] # Sujet
        assert "Une anomalie a été détectée" in args[2] # Corps
        assert "Statut de l'entrée     : FAILED" in args[2]
        assert "Simulated transfer error." in args[2]
        assert "Statut global du Job   : FAILED" in args[2]
        assert "Hachage Attendu (Agent): hash_agent" in args[2]
        assert "Hachage Calculé (Serveur): hash_server" in args[2]
        assert "Taille Agent (octets)  : 12345" in args[2]
        assert "Taille Calculée (Serveur): 54321" in args[2]
        assert "Comparaison Hachage    : Non conforme" in args[2] # True -> non conforme

        # Vérifie que le message de log est présent
        assert any("Déclenchement de la notification" in record.message for record in caplog.records)
        logger.info(f"{COLOR_GREEN}✓ Notification envoyée pour statut FAILED.{COLOR_RESET}")

@patch('app.services.notifier.send_email_notification')
def test_notify_backup_status_change_hash_mismatch(mock_send_email, mock_job_entry, caplog, setup_email_settings):
    """
    Teste que notify_backup_status_change envoie un e-mail pour un statut HASH_MISMATCH.
    """
    logger.info(f"{COLOR_BLUE}--- Test: notify_backup_status_change - HASH_MISMATCH ---{COLOR_RESET}")
    job, entry = mock_job_entry
    entry.status = BackupEntryStatus.HASH_MISMATCH
    job.current_status = JobStatus.HASH_MISMATCH

    with caplog.at_level(logging.INFO):
        notify_backup_status_change(job, entry)

        mock_send_email.assert_called_once()
        args, kwargs = mock_send_email.call_args
        
        assert args[0] == app_settings.ADMIN_EMAIL_RECIPIENT
        assert "ALERTE SAUVEGARDE - test_db - HASH MISMATCH" in args[1]
        assert "Statut de l'entrée     : HASH_MISMATCH" in args[2]
        assert "Statut global du Job   : HASH_MISMATCH" in args[2]
        logger.info(f"{COLOR_GREEN}✓ Notification envoyée pour statut HASH_MISMATCH.{COLOR_RESET}")

@patch('app.services.notifier.send_email_notification')
def test_notify_backup_status_change_success(mock_send_email, mock_job_entry, caplog, setup_email_settings):
    """
    Teste que notify_backup_status_change N'ENVOIE PAS d'e-mail pour un statut SUCCESS.
    """
    logger.info(f"{COLOR_BLUE}--- Test: notify_backup_status_change - SUCCESS ---{COLOR_RESET}")
    job, entry = mock_job_entry
    entry.status = BackupEntryStatus.SUCCESS
    job.current_status = JobStatus.OK

    with caplog.at_level(logging.DEBUG):
        notify_backup_status_change(job, entry)

        mock_send_email.assert_not_called() # Ne doit pas être appelé
        assert any("Aucune notification requise pour le statut SUCCÈS" in record.message for record in caplog.records)
        logger.info(f"{COLOR_GREEN}✓ Aucune notification envoyée pour statut SUCCESS.{COLOR_RESET}")

@patch('app.services.notifier.send_email_notification', side_effect=NotificationError("Test notification error"))
def test_notify_backup_status_change_notification_error_handling(mock_send_email, mock_job_entry, caplog, setup_email_settings):
    """
    Teste que notify_backup_status_change gère les erreurs de NotificationError.
    """
    logger.info(f"{COLOR_BLUE}--- Test: notify_backup_status_change - gestion d'erreur de notification ---{COLOR_RESET}")
    job, entry = mock_job_entry
    entry.status = BackupEntryStatus.MISSING
    job.current_status = JobStatus.MISSING

    with caplog.at_level(logging.ERROR):
        notify_backup_status_change(job, entry)
        
        mock_send_email.assert_called_once() # La tentative d'envoi a eu lieu
        assert any(f"Échec de l'envoi de la notification pour le job '{job.database_name}'" in record.message for record in caplog.records)
        logger.info(f"{COLOR_GREEN}✓ L'erreur de notification a été loguée sans crasher.{COLOR_RESET}") 