import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import Optional

from config.settings import settings
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

    server = None
    try:
        # Établit une connexion SMTP sécurisée
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls() # Active le chiffrement TLS
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD) # S'authentifie
        text = msg.as_string() # Convertit le message en chaîne
        server.sendmail(settings.EMAIL_SENDER, recipient_email, text) # Envoie l'e-mail
        logger.info(f"E-mail de notification envoyé à '{recipient_email}' avec le sujet : '{subject}'")
    except smtplib.SMTPException as e:
        logger.error(f"Erreur SMTP lors de l'envoi de l'e-mail à '{recipient_email}': {e}", exc_info=True)
        raise NotificationError(f"Échec de l'envoi de l'e-mail (SMTP) : {e}")
    except Exception as e:
        logger.critical(f"Erreur inattendue lors de l'envoi de l'e-mail à '{recipient_email}': {e}", exc_info=True)
        raise NotificationError(f"Échec inattendu de l'envoi de l'e-mail : {e}")
    finally:
        if server:
            server.quit() # Ferme la connexion SMTP même en cas d'erreur

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
    status_label = backup_entry.status.upper().replace('_', ' ')
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
        f"  Statut global du Job   : {job.current_status.upper()}\n\n"
        f"--- Détails de l'Entrée de Sauvegarde Détectée ---\n"
        f"  ID Entrée              : {backup_entry.id}\n"
        f"  Statut de l'entrée     : {backup_entry.status.upper()}\n"
        #f"  Horodatage Agent       : {backup_entry.agent_report_timestamp_utc.isoformat() if backup_entry.agent_report_timestamp_utc else 'N/A'}\n"
        #f"  Message d'erreur Agent : {backup_entry.agent_transfer_error_message or 'Aucun message spécifique de l\'agent.'}\n"
        f"  Hachage Attendu (Agent): {backup_entry.calculated_hash or 'N/A'}\n"
        f"  Hachage Calculé (Serveur): {backup_entry.server_calculated_staged_hash or 'N/A'}\n"
        #f"  Taille Agent (octets)  : {backup_entry.agent_reported_size_bytes or 'N/A'}\n"
        #f"  Taille Calculée (Serveur): {backup_entry.server_calculated_staged_size or 'N/A'}\n"
        f"  Comparaison Hachage    : {'Non conforme' if backup_entry.hash_comparison_result else 'Conforme' if backup_entry.hash_comparison_result is False else 'N/A'}\n"
        #f"  Résumé des logs Agent  : {backup_entry.agent_logs_summary or 'Aucun résumé.'}\n\n"
        f"Veuillez prendre les mesures nécessaires pour investiguer et résoudre ce problème.\n\n"
        f"Cordialement,\n"
        f"Votre Système de Surveillance des Sauvegardes Automatisé"
    )

    # Envoie la notification si une adresse d'administrateur est configurée
    if settings.ADMIN_EMAIL_RECIPIENT:
        try:
            logger.info(f"Déclenchement de la notification pour le job '{job.database_name}' avec le statut '{backup_entry.status}'.")
            send_email_notification(settings.ADMIN_EMAIL_RECIPIENT, subject, body)
        except NotificationError as e:
            # L'erreur a déjà été loguée dans send_email_notification
            logger.error(f"Échec de l'envoi de la notification pour le job '{job.database_name}' : {e}")
            pass # Continuer l'exécution du scanner malgré l'échec de la notification
    else:
        logger.warning("Aucun destinataire d'e-mail administrateur configuré (ADMIN_EMAIL_RECIPIENT). Notification non envoyée.")
