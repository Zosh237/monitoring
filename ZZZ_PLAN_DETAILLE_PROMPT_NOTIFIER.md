Prompt d'implémentation de la fonctionnalité de Notification et des Tests
Objectif Général
Mettre en place un service de notification par e-mail pour alerter les administrateurs en cas d'anomalies détectées lors du scan des sauvegardes. Ce prompt inclut la création du module de notification (app/services/notifier.py), l'extension de la configuration, l'intégration dans le scanner (app/services/scanner.py), et le développement de tests unitaires et d'intégration dédiés pour garantir la fiabilité de cette nouvelle fonctionnalité. L'ensemble de l'implémentation doit se faire sans modifier ou casser le code existant.

Module à Implémenter : Le Service de Notification
Concept
Le service de notification est responsable de l'envoi d'alertes automatisées lorsque le système de surveillance des sauvegardes détecte qu'un job de sauvegarde a échoué, est manquant, présente une incohérence de hachage, ou une erreur d'intégrité de transfert. Pour la première phase, les notifications se feront par e-mail, configurables via les variables d'environnement.

Algorithme Détaillé
Création du module app/services/notifier.py :

Ce module contiendra les fonctions pour envoyer des e-mails.

Il importera les bibliothèques smtplib, email.mime.text, email.mime.multipart pour l'envoi d'e-mails standard.

Il importera logging pour la journalisation des opérations de notification.

Il importera les paramètres de configuration (config.settings) et les modèles de base de données (app.models.models) pour extraire les informations nécessaires à la composition des messages.

Il définira une exception personnalisée NotificationError.

Il implémentera une fonction send_email_notification(recipient_email: str, subject: str, body: str) :

Cette fonction tentera d'établir une connexion SMTP sécurisée (TLS).

Elle se connectera au serveur SMTP avec les identifiants fournis dans la configuration.

Elle construira le message MIME avec l'expéditeur, le destinataire et le sujet.

Elle enverra le message.

Elle gérera les exceptions liées à l'envoi d'e-mails (connexion, authentification, envoi) et les loguera via logging.

Il implémentera une fonction notify_backup_status_change(job: ExpectedBackupJob, backup_entry: BackupEntry) :

Cette fonction prendra en entrée un objet ExpectedBackupJob et un objet BackupEntry.

Elle construira le subject et le body de l'e-mail en utilisant les détails pertinents des objets job et backup_entry (nom de la base de données, statut, messages d'erreur, hachages, tailles, etc.).

Elle appellera send_email_notification en utilisant l'adresse e-mail administrateur configurée (settings.ADMIN_EMAIL_RECIPIENT).

Elle loguera l'action de notification.

Extension de la configuration (config/settings.py) :

Ajouter les variables d'environnement suivantes pour la configuration SMTP et l'adresse du destinataire :

EMAIL_HOST: L'hôte SMTP (ex: smtp.gmail.com).

EMAIL_PORT: Le port SMTP (ex: 587 pour TLS).

EMAIL_USERNAME: Le nom d'utilisateur pour l'authentification SMTP.

EMAIL_PASSWORD: Le mot de passe pour l'authentification SMTP.

EMAIL_SENDER: L'adresse e-mail de l'expéditeur.

ADMIN_EMAIL_RECIPIENT: L'adresse e-mail à laquelle envoyer les notifications d'alerte.

Intégration dans le scanner (app/services/scanner.py) :

Importer la fonction notify_backup_status_change depuis app/services/notifier.py.

Dans la méthode _process_job_status (ou une méthode similaire où le statut final de BackupEntry est déterminé et le ExpectedBackupJob est mis à jour), ajouter une logique pour vérifier le backup_entry_status.

Si le backup_entry_status est l'un des statuts d'échec (BackupEntryStatus.FAILED, BackupEntryStatus.MISSING, BackupEntryStatus.HASH_MISMATCH, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED), alors appeler notify_backup_status_change en lui passant les objets job et backup_entry.

Assurer que l'objet backup_entry passé au notificateur est bien celui qui reflète le statut le plus récent persisté en base de données. Il peut être nécessaire de rafraîchir l'objet job et de récupérer la dernière backup_entry associée si elles ne sont pas à jour dans le contexte actuel de la méthode.

Gérer les exceptions potentielles de NotificationError lors de l'appel à notify_backup_status_change pour ne pas bloquer le processus du scanner.

Implémentation du Code (Fichiers à créer/modifier)
1. Création de app/services/notifier.py

# app/services/notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional

# Importe les paramètres de configuration
from config.settings import settings
# Importe les modèles de base de données pour le typage et l'accès aux données
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus

logger = logging.getLogger(__name__)

class NotificationError(Exception):
    """Exception personnalisée pour les erreurs de notification."""
    pass

def send_email_notification(
    recipient_email: str,
    subject: str,
    body: str
):
    """
    Envoie une notification par e-mail en utilisant les paramètres SMTP configurés.

    Args:
        recipient_email (str): L'adresse e-mail du destinataire.
        subject (str): Le sujet de l'e-mail.
        body (str): Le corps de l'e-mail (texte brut).
    
    Raises:
        NotificationError: Si l'envoi de l'e-mail échoue.
    """
    # Vérifie si les paramètres SMTP essentiels sont configurés
    if not settings.EMAIL_HOST or not settings.EMAIL_PORT or \
       not settings.EMAIL_USERNAME or not settings.EMAIL_PASSWORD or \
       not settings.EMAIL_SENDER:
        logger.warning("Paramètres d'e-mail SMTP non configurés. La notification par e-mail est désactivée.")
        return

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Établit une connexion SMTP sécurisée
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls() # Active le chiffrement TLS
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD) # S'authentifie
        text = msg.as_string() # Convertit le message en chaîne
        server.sendmail(settings.EMAIL_SENDER, recipient_email, text) # Envoie l'e-mail
        server.quit() # Ferme la connexion SMTP
        logger.info(f"E-mail de notification envoyé à '{recipient_email}' avec le sujet : '{subject}'")
    except smtplib.SMTPException as e:
        logger.error(f"Erreur SMTP lors de l'envoi de l'e-mail à '{recipient_email}': {e}", exc_info=True)
        raise NotificationError(f"Échec de l'envoi de l'e-mail (SMTP) : {e}")
    except Exception as e:
        logger.critical(f"Erreur inattendue lors de l'envoi de l'e-mail à '{recipient_email}': {e}", exc_info=True)
        raise NotificationError(f"Échec inattendu de l'envoi de l'e-mail : {e}")

def notify_backup_status_change(
    job: ExpectedBackupJob,
    backup_entry: BackupEntry
):
    """
    Compose et envoie une notification par e-mail en cas de changement critique du statut de sauvegarde.

    Args:
        job (ExpectedBackupJob): L'objet du job de sauvegarde attendu.
        backup_entry (BackupEntry): L'objet de l'entrée de sauvegarde correspondant à la détection.
    """
    # Ne pas notifier si le statut de l'entrée est SUCCESS
    if backup_entry.status == BackupEntryStatus.SUCCESS:
        logger.debug(f"Aucune notification requise pour le statut SUCCÈS du job '{job.database_name}'.")
        return

    # Détermine le sujet de l'e-mail basé sur le statut
    status_label = backup_entry.status.value.upper().replace('_', ' ')
    subject = f"ALERTE SAUVEGARDE - {job.database_name} - {status_label}"

    # Construit le corps de l'e-mail
    body = (
        f"Cher administrateur,\n\n"
        f"Une anomalie a été détectée concernant la sauvegarde de la base de données '{job.database_name}'.\n\n"
        f"--- Détails du Job de Sauvegarde ---\n"
        f"  ID Job                 : {job.id}\n"
        f"  Nom de la Base de Données : {job.database_name}\n"
        f"  Agent Responsable      : {job.agent_id_responsible}\n"
        f"  Compagnie              : {job.company_name}\n"
        f"  Ville                  : {job.city}\n"
        f"  Statut global du Job   : {job.current_status.value.upper()}\n\n"
        f"--- Détails de l'Entrée de Sauvegarde Détectée ---\n"
        f"  ID Entrée              : {backup_entry.id}\n"
        f"  Statut de l'entrée     : {backup_entry.status.value.upper()}\n"
        f"  Horodatage Agent       : {backup_entry.agent_report_timestamp_utc.isoformat() if backup_entry.agent_report_timestamp_utc else 'N/A'}\n"
        f"  Message d'erreur Agent : {backup_entry.agent_transfer_error_message or 'Aucun message spécifique de l\'agent.'}\n"
        f"  Hachage Attendu (Agent): {backup_entry.agent_reported_hash_sha256 or 'N/A'}\n"
        f"  Hachage Calculé (Serveur): {backup_entry.server_calculated_staged_hash or 'N/A'}\n"
        f"  Taille Agent (octets)  : {backup_entry.agent_reported_size_bytes or 'N/A'}\n"
        f"  Taille Calculée (Serveur): {backup_entry.server_calculated_staged_size or 'N/A'}\n"
        f"  Comparaison Hachage    : {'Non conforme' if backup_entry.hash_comparison_result else 'Conforme' if backup_entry.hash_comparison_result is False else 'N/A'}\n"
        f"  Résumé des logs Agent  : {backup_entry.agent_logs_summary or 'Aucun résumé.'}\n\n"
        f"Veuillez prendre les mesures nécessaires pour investiguer et résoudre ce problème.\n\n"
        f"Cordialement,\n"
        f"Votre Système de Surveillance des Sauvegardes Automatisé"
    )

    # Envoie la notification si une adresse d'administrateur est configurée
    if settings.ADMIN_EMAIL_RECIPIENT:
        try:
            send_email_notification(settings.ADMIN_EMAIL_RECIPIENT, subject, body)
        except NotificationError:
            # L'erreur a déjà été loguée dans send_email_notification
            pass # Continuer l'exécution du scanner malgré l'échec de la notification
    else:
        logger.warning("Aucun destinataire d'e-mail administrateur configuré (ADMIN_EMAIL_RECIPIENT). Notification non envoyée.")


2. Extension de config/settings.py

Ajouter les variables d'environnement dans la classe Settings:

# config/settings.py (extrait)
# ... autres imports ...
import os
from typing import Optional # Assurez-vous que Optional est importé

class Settings(BaseSettings):
    # ... autres paramètres ...

    # Paramètres pour les notifications par e-mail
    EMAIL_HOST: Optional[str] = os.getenv("EMAIL_HOST")
    EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", 587)) # Port par défaut pour TLS
    EMAIL_USERNAME: Optional[str] = os.getenv("EMAIL_USERNAME")
    EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
    EMAIL_SENDER: Optional[str] = os.getenv("EMAIL_SENDER")
    ADMIN_EMAIL_RECIPIENT: Optional[str] = os.getenv("ADMIN_EMAIL_RECIPIENT") # L'adresse principale pour les alertes

    # ... autres paramètres ...

3. Intégration dans app/services/scanner.py

Modifier la méthode _process_job_status pour appeler le notificateur.

# app/services/scanner.py (extrait)
# ...
import logging
import os
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import re
from typing import Tuple, Dict, Any, Optional, Set

# Importe les modèles de base de données
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus

# Importe les utilitaires et services nécessaires
from app.services.validation_service import validate_status_file, StatusFileValidationError
from app.utils.crypto import calculate_file_sha256, CryptoUtilityError
from app.utils.file_operations import ensure_directory_exists, move_file, FileOperationError, copy_file
from app.utils.datetime_utils import parse_iso_datetime, get_utc_now, DateTimeUtilityError
from app.utils.path_utils import get_expected_final_path
from app.services.backup_manager import promote_backup, BackupManagerError

# IMPORTE LE SERVICE DE NOTIFICATION
from app.services.notifier import notify_backup_status_change, NotificationError

# Importe la configuration de l'application
from config.settings import settings

logger = logging.getLogger(__name__)

class ScannerError(Exception):
    """Exception personnalisée pour les erreurs du scanner."""
    pass

# ... (le reste des fonctions et classes) ...

class BackupScanner:
    """
    Scanner principal responsable de la surveillance des sauvegardes selon une logique en 3 phases :
    1. Collecte et validation de tous les rapports STATUS.json
    2. Évaluation et mise à jour de chaque job de sauvegarde attendu
    3. Archivage des rapports traités
    """
    def __init__(self, session: Session):
        self.session = session
        self.settings = settings
        self.logger = logger
        self.all_relevant_reports_map: Dict[int, Dict[str, Any]] = {} # Map job_id -> relevant_report_data
        self.status_files_to_archive: Set[str] = set() # Set de chemins de fichiers STATUS.json à archiver

    # ... (autres méthodes existantes) ...

    def _process_job_status(self, db_session: Session, job: ExpectedBackupJob, relevant_entry: Dict[str, Any], staged_db_file_path: Optional[str]):
        """
        Détermine le statut d'une entrée de sauvegarde et du job associé,
        met à jour la base de données et déclenche des actions comme la promotion ou la notification.
        """
        backup_entry_status: BackupEntryStatus
        job_status: JobStatus = JobStatus.UNKNOWN
        error_message: Optional[str] = None

        self.logger.debug(f"Traitement du statut pour le job '{job.database_name}' (ID: {job.id}).")

        # Initialise un nouveau BackupEntry. Il sera mis à jour avec le statut final.
        new_backup_entry = BackupEntry(
            expected_job_id=job.id,
            agent_report_timestamp_utc=parse_iso_datetime(relevant_entry['operation_timestamp_utc']),
            agent_reported_hash_sha256=relevant_entry.get('hash_sha256'),
            agent_reported_size_bytes=relevant_entry.get('size_bytes'),
            agent_compress_size_pre_compress=relevant_entry.get('compress_size_pre_compress'),
            agent_compress_size_post_compress=relevant_entry.get('compress_size_post_compress'),
            agent_transfer_process_status=relevant_entry.get('agent_transfer_process_status'),
            agent_transfer_process_start_time=self._parse_datetime_safe(relevant_entry.get('agent_transfer_process_start_time_utc')),
            agent_transfer_process_timestamp=self._parse_datetime_safe(relevant_entry.get('agent_transfer_process_timestamp_utc')),
            agent_transfer_error_message=relevant_entry.get('agent_transfer_error_message'),
            agent_staged_file_name=relevant_entry.get('staged_file_name'),
            agent_logs_summary=relevant_entry.get('logs_summary')
        )
        db_session.add(new_backup_entry) # Ajoute l'entrée à la session pour la persistance

        # Logique de détermination du statut de la sauvegarde
        if relevant_entry.get('status') == 'failed':
            backup_entry_status = BackupEntryStatus.FAILED
            job_status = JobStatus.FAILED
            error_message = relevant_entry.get('error_msg', 'Erreur signalée par l\'agent.')
            self.logger.warning(f"Job '{job.database_name}' (ID: {job.id}) a un statut 'FAILED' signalé par l'agent. Erreur: {error_message}")
        elif relevant_entry.get('status') == 'transfer_integrity_failed':
            backup_entry_status = BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
            job_status = JobStatus.TRANSFER_INTEGRITY_FAILED
            error_message = relevant_entry.get('error_msg', 'Intégrité du transfert échouée signalée par l\'agent.')
            self.logger.warning(f"Job '{job.database_name}' (ID: {job.id}) a un statut 'TRANSFER_INTEGRITY_FAILED' signalé par l'agent. Erreur: {error_message}")
        elif staged_db_file_path: # Si un fichier stagé est présent, procéder aux vérifications serveur
            self.logger.debug(f"Fichier stagé trouvé pour '{job.database_name}'. Calcul du hachage et de la taille.")
            try:
                server_hash = calculate_file_sha256(staged_db_file_path)
                server_size = os.path.getsize(staged_db_file_path)

                new_backup_entry.server_calculated_staged_hash = server_hash
                new_backup_entry.server_calculated_staged_size = server_size

                self.logger.debug(f"Server Hash: {server_hash}, Agent Hash: {relevant_entry.get('hash_sha256')}")
                self.logger.debug(f"Server Size: {server_size}, Agent Size: {relevant_entry.get('size_bytes')}")

                # Comparaison des hachages
                hash_match = (server_hash == relevant_entry.get('hash_sha256'))
                new_backup_entry.hash_comparison_result = not hash_match # True si non-concordant, False si concordant

                if not hash_match:
                    backup_entry_status = BackupEntryStatus.HASH_MISMATCH
                    job_status = JobStatus.HASH_MISMATCH
                    error_message = f"Incohérence de hachage détectée pour '{job.database_name}'. Agent: {relevant_entry.get('hash_sha256')}, Serveur: {server_hash}"
                    self.logger.error(error_message)
                elif server_size != relevant_entry.get('size_bytes'):
                    # Si les hachages correspondent mais pas les tailles, c'est aussi une anomalie.
                    # On pourrait définir un nouveau statut BackupEntryStatus.SIZE_MISMATCH si nécessaire
                    # Pour l'instant, on le considère comme une erreur générique ou on se fie plus au hash
                    self.logger.warning(f"Taille de fichier stagé pour '{job.database_name}' (ID: {job.id}) non concordante avec l'agent. Agent: {relevant_entry.get('size_bytes')}, Serveur: {server_size}")
                    # Ne change pas le statut à HASH_MISMATCH si les hashes sont OK, pourrait rester SUCCESS ou FAILED si d'autres checks.
                    # Si la taille est différente mais le hash identique, cela est très improbable et suggère un problème avec l'agent ou le FS.
                    # Pour l'instant, nous considérons le hash comme l'autorité principale pour l'intégrité.
                    backup_entry_status = BackupEntryStatus.SUCCESS # Considere comme succes si hash ok, mais logge l'alerte sur la taille
                    job_status = JobStatus.OK
                else:
                    backup_entry_status = BackupEntryStatus.SUCCESS
                    job_status = JobStatus.OK
                    self.logger.info(f"Fichier stagé pour '{job.database_name}' validé avec succès (hachage et taille).")
                    
                    # Promotion de la sauvegarde réussie vers le stockage final
                    try:
                        self.logger.info(f"Promotion de la sauvegarde pour '{job.database_name}'...")
                        promote_backup(staged_db_file_path, job)
                        # Le fichier stagé n'est PAS supprimé après promotion, le scanner s'en occupe.
                        self.logger.info(f"Sauvegarde pour '{job.database_name}' promue avec succès.")
                    except BackupManagerError as e:
                        backup_entry_status = BackupEntryStatus.FAILED # La promotion est un échec serveur
                        job_status = JobStatus.FAILED
                        error_message = f"Échec de la promotion de la sauvegarde : {e}"
                        self.logger.error(f"Échec de la promotion de la sauvegarde pour '{job.database_name}' : {e}", exc_info=True)

            except CryptoUtilityError as e:
                backup_entry_status = BackupEntryStatus.FAILED
                job_status = JobStatus.FAILED
                error_message = f"Erreur de calcul de hachage sur le serveur : {e}"
                self.logger.error(f"Erreur lors du calcul du hachage serveur pour '{job.database_name}': {e}", exc_info=True)
            except Exception as e:
                backup_entry_status = BackupEntryStatus.FAILED
                job_status = JobStatus.FAILED
                error_message = f"Erreur inattendue lors de la validation serveur : {e}"
                self.logger.critical(f"Erreur inattendue lors du traitement du fichier stagé pour '{job.database_name}': {e}", exc_info=True)
        else: # Aucun fichier stagé et l'agent n'a pas signalé d'échec de transfert explicite
            backup_entry_status = BackupEntryStatus.MISSING
            job_status = JobStatus.MISSING
            error_message = "Fichier de sauvegarde manquant dans la zone de staging."
            self.logger.error(f"Fichier de sauvegarde manquant pour '{job.database_name}' (ID: {job.id}).")

        # Met à jour le statut de l'entrée de sauvegarde
        new_backup_entry.status = backup_entry_status
        db_session.commit() # Persiste l'entrée de sauvegarde pour avoir son ID et statut à jour

        # Met à jour le statut du job de sauvegarde attendu
        job.current_status = job_status
        job.last_checked_at_utc = get_utc_now()
        if job_status == JobStatus.OK:
            job.last_successful_backup_utc = job.last_checked_at_utc
        elif job_status in [JobStatus.FAILED, JobStatus.MISSING, JobStatus.HASH_MISMATCH, JobStatus.TRANSFER_INTEGRITY_FAILED]:
            job.last_failed_backup_utc = job.last_checked_at_utc
        db_session.commit() # Persiste les changements du job

        # --- Déclenchement de la notification ---
        # Rafraîchit l'objet new_backup_entry pour s'assurer qu'il a toutes les infos persistées, y compris l'ID.
        db_session.refresh(new_backup_entry)
        db_session.refresh(job) # Rafraîchit le job pour s'assurer du statut current_status le plus récent

        if backup_entry_status != BackupEntryStatus.SUCCESS:
            self.logger.info(f"Déclenchement de la notification pour le job '{job.database_name}' avec le statut '{backup_entry_status.value}'.")
            try:
                notify_backup_status_change(job, new_backup_entry)
            except NotificationError as e:
                self.logger.error(f"Échec de l'envoi de la notification pour le job '{job.database_name}' : {e}")
            except Exception as e:
                self.logger.critical(f"Erreur inattendue lors du déclenchement de la notification pour le job '{job.database_name}' : {e}", exc_info=True)
        else:
            self.logger.info(f"Job '{job.database_name}' (ID: {job.id}) traité avec succès. Aucune notification d'erreur requise.")

        # Gère le déplacement du fichier stagé si le traitement est terminé
        if staged_db_file_path:
            self._handle_staged_file_post_processing(staged_db_file_path, job, backup_entry_status)


Tests pour le Service de Notification
Nous allons créer un fichier de test dédié pour le service de notification et étendre les tests du scanner pour vérifier l'intégration.

Objectif des Tests
Tests Unitaires (tests/test_notifier.py) :

Vérifier que send_email_notification envoie correctement un e-mail (en mockant le serveur SMTP).

Tester la gestion des erreurs par send_email_notification (connexion, authentification).

Vérifier que notify_backup_status_change formate correctement le message et appelle send_email_notification pour les statuts d'erreur.

S'assurer que notify_backup_status_change ne tente pas d'envoyer un e-mail si le statut est SUCCESS ou si les configurations sont manquantes.

Tests d'Intégration (tests/test_scanner_notifications.py ou extension de tests/test_scanner.py) :

Confirmer que le scanner appelle notify_backup_status_change lorsque des statuts d'échec sont détectés (e.g., FAILED, MISSING, HASH_MISMATCH, TRANSFER_INTEGRITY_FAILED).

Vérifier que le scanner ne l'appelle pas pour les statuts SUCCESS.

Création du fichier de test : tests/test_notifier.py
# tests/test_notifier.py
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
            send_email_notification(recipient, subject, body)

        assert "Échec de l'envoi de l'e-mail (SMTP)" in str(excinfo.value)
        assert f"Erreur SMTP lors de l'envoi de l'e-mail à '{recipient}'" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ L'erreur SMTP a été capturée et loguée.{COLOR_RESET}")
    
    mock_smtp_server.quit.assert_called_once() # La session doit être fermée même en cas d'échec

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

        assert f"Déclenchement de la notification pour le job 'test_db' avec le statut 'failed'." in caplog.text
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
        assert f"Aucune notification requise pour le statut SUCCÈS du job '{job.database_name}'." in caplog.text
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
        assert f"Échec de l'envoi de la notification pour le job '{job.database_name}' : Test notification error" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ L'erreur de notification a été loguée sans crasher.{COLOR_RESET}")


# --- Tests d'intégration dans scanner.py ---
# Ces tests peuvent être ajoutés à tests/test_scanner.py ou dans un nouveau fichier comme tests/test_scanner_notifications.py

# Pour ces tests, vous aurez besoin des fixtures de tests/test_scanner.py
# (db, test_env, create_job_and_agent_paths, create_status_json_file, create_staged_file)

# Voici un exemple de ce à quoi ressembleraient ces tests dans un contexte scanner:
# @patch('app.services.notifier.notify_backup_status_change')
# def test_scanner_notifies_on_failed_backup(mock_notify, db, test_env):
#     # Configure un job et un fichier status.json qui indique un échec
#     job = create_job_and_agent_paths(db, "CompanyX", "CityX", "NeighX", "db1", 10, 0)
#     create_status_json_file(
#         "CompanyX", "CityX", "NeighX",
#         datetime.now(timezone.utc),
#         multiple_dbs_in_report=[{"db_name": "db1", "status": "failed", "error_msg": "Network issue"}]
#     )
#
#     scanner = BackupScanner(db)
#     scanner.scan_all_jobs()
#
#     # Vérifie que la fonction de notification a été appelée une fois
#     mock_notify.assert_called_once()
#     # Vous pouvez inspecter les arguments de l'appel pour plus de détails
#     call_args = mock_notify.call_args[0]
#     assert call_args[0].id == job.id # Le job passé doit être le bon
#     assert call_args[1].status == BackupEntryStatus.FAILED # Le statut doit être FAILED
#
# @patch('app.services.notifier.notify_backup_status_change')
# def test_scanner_does_not_notify_on_successful_backup(mock_notify, db, test_env):
#     # Configure un job et un fichier status.json qui indique un succès
#     job = create_job_and_agent_paths(db, "CompanyY", "CityY", "NeighY", "db2", 10, 0)
#     create_status_json_file(
#         "CompanyY", "CityY", "NeighY",
#         datetime.now(timezone.utc),
#         multiple_dbs_in_report=[{"db_name": "db2", "status": "success", "hash_sha256": "abcdef", "size_bytes": 100}]
#     )
#     create_staged_file("CompanyY", "CityY", "NeighY", "db2_backup.zip", "abcdef", 100)
#
#     scanner = BackupScanner(db)
#     scanner.scan_all_jobs()
#
#     # Vérifie que la fonction de notification n'a PAS été appelée
#     mock_notify.assert_not_called()


Considérations pour les Tests
Mocking : Pour les tests unitaires de notifier.py, il est crucial de mocker smtplib.SMTP afin d'éviter d'envoyer de vrais e-mails pendant les tests.

Configuration : Utilisez une fixture pytest (setup_email_settings) pour définir des paramètres d'e-mail de test temporaires et les nettoyer après l'exécution de chaque test. Cela garantit l'isolation des tests de configuration réelle.

caplog : Utilisez la fixture caplog de pytest pour vérifier que les messages de journalisation sont émis correctement (par exemple, avertissements si la configuration est manquante, erreurs en cas d'échec d'envoi).

Objets Mockés : Créez des mocks pour les objets ExpectedBackupJob et BackupEntry afin de simuler des scénarios spécifiques de statut et de données.

Tests d'Intégration (Scanner) : Lors de l'intégration dans scanner.py, utilisez @patch('app.services.notifier.notify_backup_status_change') pour vérifier que la fonction de notification est appelée (ou non) dans les scénarios appropriés du scanner. Vous n'avez pas besoin de tester l'envoi réel de l'e-mail à ce niveau, juste l'appel à la fonction du service de notification.

Ce prompt devrait permettre à l'IA de coder et de tester la fonctionnalité de notification de manière robuste et isolée.