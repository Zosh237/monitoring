import os
import json
import shutil
from datetime import datetime, timezone

# Importations de l'application
from app.utils.crypto import calculate_file_sha256
from app.models.models import ExpectedBackupJob, BackupEntry
from config.settings import settings  # Pour BACKUP_STORAGE_ROOT et VALIDATED_BACKUPS_BASE_PATH

# ------------------------------------------------------------------------------
# Partie Notification
# ------------------------------------------------------------------------------
def send_notification(job, message):
    """
    Envoie une notification pour un job dont le statut n'est pas SUCCESS.
    Cette fonction est un stub à adapter (e.g., envoi d'un e-mail, alerte Slack, etc.).
    """
    # Ici, nous utilisons simplement un print pour la démonstration.
    print(f"[NOTIFICATION] Job ID {job.id} ({job.database_name}) - Statut: {job.current_status} - Message: {message}")

# ------------------------------------------------------------------------------
# Fonctions de base pour charger et archiver les rapports JSON
# ------------------------------------------------------------------------------
def load_json_report(json_path):
    """Charge et renvoie le contenu d'un fichier JSON."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def archive_report(json_path):
    """
    Déplace le fichier JSON traité dans un sous-dossier "_archive" 
    du dossier parent (typiquement le dossier log de l'agent).
    """
    archive_folder = os.path.join(os.path.dirname(json_path), "_archive")
    os.makedirs(archive_folder, exist_ok=True)
    archived_path = os.path.join(archive_folder, os.path.basename(json_path))
    shutil.move(json_path, archived_path)
    return archived_path

# ------------------------------------------------------------------------------
# Traitement d'un ExpectedBackupJob individuel
# ------------------------------------------------------------------------------
def process_expected_job(job, databases_data, agent_databases_folder, db_session):
    """
    Traite un ExpectedBackupJob à partir des informations fournies dans databases_data (extrait du JSON).
    
    Pour le job correspondant, la logique est la suivante :
      - Si la clé job.database_name est présente dans databases_data :
          1. Extraire staged_file_name et expected_hash (issu de la section COMPRESS).
          2. Vérifier l'existence du fichier backup dans agent_databases_folder.
             a. Si présent, calculer le hash.
                • Si computed_hash != expected_hash → job = FAILED.
                • Si computed_hash == expected_hash :
                    - Si aucun hash n'est enregistré ou si computed_hash diffère du hash stocké → job = SUCCESS.
                    - Sinon, si computed_hash est identique au hash déjà enregistré → job = HASH_MISMATCH.
             b. Sinon → job = MISSING.
      - Sinon → job = MISSING.
      
    Dans tous les cas, une entrée BackupEntry appropriée est créée,
    et une notification est envoyée si le statut n'est pas SUCCESS.
    """
    now = datetime.now(timezone.utc)
    if job.database_name in databases_data:
        data = databases_data[job.database_name]
        staged_file_name = data.get("staged_file_name")
        compress_section = data.get("COMPRESS", {})
        expected_hash = compress_section.get("sha256_checksum")
        backup_file_path = os.path.join(agent_databases_folder, staged_file_name)
        if os.path.exists(backup_file_path):
            try:
                computed_hash = calculate_file_sha256(backup_file_path)
            except Exception as err:
                job.current_status = "FAILED"
                job.error_message = f"Erreur lors du calcul du hash: {err}"
                job.last_checked_timestamp = now
                backup_entry = BackupEntry(
                    expected_job_id=job.id,
                    timestamp=now,
                    status="FAILED",
                    message=job.error_message,
                    calculated_hash=""
                )
                db_session.add(job)
                db_session.add(backup_entry)
                send_notification(job, job.error_message)
                return

            if computed_hash != expected_hash:
                job.current_status = "FAILED"
                message = "Hash calculé différent du hash attendu."
            else:
                # Le hash correspond ; on vérifie s'il a changé depuis le dernier scan.
                if job.calculated_hash is None or job.calculated_hash != computed_hash:
                    job.current_status = "SUCCESS"
                    job.calculated_hash = computed_hash
                    message = "Backup validé et mis à jour."
                else:
                    job.current_status = "HASH_MISMATCH"
                    message = "Backup inchangé entre deux scans (HASH_MISMATCH)."
            job.last_checked_timestamp = now
            backup_entry = BackupEntry(
                expected_job_id=job.id,
                timestamp=now,
                status=job.current_status,
                message=message,
                calculated_hash=computed_hash
            )
            db_session.add(job)
            db_session.add(backup_entry)
            if job.current_status == "SUCCESS":
                # Copier le backup validé vers l'espace de validation.
                validated_backup_path = os.path.join(settings.VALIDATED_BACKUPS_BASE_PATH, staged_file_name)
                try:
                    shutil.copy2(backup_file_path, validated_backup_path)
                except Exception as err:
                    job.current_status = "FAILED"
                    job.error_message = f"Erreur lors de la copie: {err}"
                    backup_entry.message += " / Copie échouée."
                    db_session.add(job)
                    db_session.add(backup_entry)
                    send_notification(job, job.error_message)
                    return
            if job.current_status != "SUCCESS":
                send_notification(job, message)
        else:
            job.current_status = "MISSING"
            job.last_checked_timestamp = now
            backup_entry = BackupEntry(
                expected_job_id=job.id,
                timestamp=now,
                status="MISSING",
                message=f"Fichier backup introuvable: {staged_file_name}",
                calculated_hash=""
            )
            db_session.add(job)
            db_session.add(backup_entry)
            send_notification(job, backup_entry.message)
    else:
        job.current_status = "MISSING"
        job.last_checked_timestamp = now
        backup_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=now,
            status="MISSING",
            message="Aucune entrée dans le rapport pour ce job.",
            calculated_hash=""
        )
        db_session.add(job)
        db_session.add(backup_entry)
        send_notification(job, backup_entry.message)

# ------------------------------------------------------------------------------
# Traitement complet d'un rapport JSON pour un agent donné
# ------------------------------------------------------------------------------
def process_agent_report(agent_log_json_path, agent_databases_folder, db_session):
    """
    Traite un rapport JSON d'un agent.
      - Charge le rapport depuis le dossier log.
      - Récupère la section "databases".
      - Récupère les ExpectedBackupJob actifs (filtrage supplémentaire possible par critères).
      - Pour chaque job, appelle process_expected_job.
      - Commit les modifications et archive le rapport traité.
    """
    report = load_json_report(agent_log_json_path)
    databases_data = report.get("databases", {})
    active_jobs = db_session.query(ExpectedBackupJob).filter_by(is_active=True).all()
    for job in active_jobs:
        process_expected_job(job, databases_data, agent_databases_folder, db_session)
    db_session.commit()
    archive_report(agent_log_json_path)

# ------------------------------------------------------------------------------
# Itération sur le dossier racine des agents
# ------------------------------------------------------------------------------
def process_all_agents(db_session):
    """
    Parcourt le dossier racine (défini par settings.BACKUP_STORAGE_ROOT) et pour chaque agent :
      - Récupère les dossiers 'log' et 'databases'.
      - Pour chaque fichier JSON dans 'log', lance le traitement.
    """
    root_folder = settings.BACKUP_STORAGE_ROOT
    for agent_name in os.listdir(root_folder):
        agent_path = os.path.join(root_folder, agent_name)
        if not os.path.isdir(agent_path):
            continue
        log_folder = os.path.join(agent_path, "log")
        databases_folder = os.path.join(agent_path, "databases")
        if not os.path.isdir(log_folder) or not os.path.isdir(databases_folder):
            continue
        for file_name in os.listdir(log_folder):
            if file_name.lower().endswith(".json"):
                agent_log_json_path = os.path.join(log_folder, file_name)
                process_agent_report(agent_log_json_path, databases_folder, db_session)

# ------------------------------------------------------------------------------
# Fonction de lancement du scanner en production
# ------------------------------------------------------------------------------
def run_new_scanner():
    """
    Lance le scanner sur l'ensemble des agents en parcourant le dossier racine.
    
    Pour une exécution en production, nous utilisons SessionLocal, qui pointe sur la base de production.
    """
    # Utiliser la SessionLocal en production.
    from app.core.database import SessionLocal
    db_session = SessionLocal()
    try:
        process_all_agents(db_session)
    finally:
        db_session.close()

# ------------------------------------------------------------------------------
# Point d'entrée pour exécution en tant que script
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    run_new_scanner()
