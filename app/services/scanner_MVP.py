import os
import json
import sys

from app.services.notifier import notify_backup_status_change, NotificationError

# Ajoute le dossier racine 'monitoring' au PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


import shutil
from datetime import datetime, timezone

# Importations de l'application
from app.utils.crypto import calculate_file_sha256
from app.utils.is_valid_backup_report import is_valid_backup_report
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
    print(f"fonction archive ok")

    return archived_path

# ------------------------------------------------------------------------------
# Traitement d'un ExpectedBackupJob individuel
# ------------------------------------------------------------------------------
def process_expected_job(job, databases_data, agent_databases_folder, agent_id, operation_log_file_name, agent_status, db_session):
    now = datetime.now(timezone.utc)
    computed_hash = None
    staged_file_name = None
    backup_file_path = None
    message = ""

    if job.database_name in databases_data:
        data = databases_data[job.database_name]
        staged_file_name = data.get("staged_file_name")
        compress_section = data.get("COMPRESS", {})
        expected_hash = compress_section.get("sha256_checksum")

        backup_file_path = os.path.join(agent_databases_folder, staged_file_name)
        if os.path.exists(backup_file_path):
            try:
                computed_hash = calculate_file_sha256(backup_file_path)
                print(f"++++++computed_hash:{computed_hash} expected_hash:{expected_hash}+++++++++")
                if computed_hash != expected_hash:
                    job.current_status = "FAILED"
                    message = "Hash calculé différent du hash déclaré dans le rapport."
                else:
                    job.last_successful_backup_timestamp=now
                    # Hash validé par l'agent — on entre en zone promotion
                    if job.previous_successful_hash_global:
                        if computed_hash == job.previous_successful_hash_global:
                            job.current_status = "UNCHANGED"
                            message = "Backup identique à la dernière version validée."
                        else:
                            job.current_status = "SUCCESS"
                            
                            job.previous_successful_hash_global = computed_hash
                            message = "Nouveau backup validé avec contenu mis à jour."
                            try:
                                validated_path = os.path.join(settings.VALIDATED_BACKUPS_BASE_PATH, job.company_name,job.city, str(job.year))
                                job.file_storage_path_template = os.path.join(validated_path, staged_file_name)
                                os.makedirs(validated_path, exist_ok=True)
                                shutil.copy2(backup_file_path, os.path.join(validated_path, staged_file_name))
                            except Exception as copy_err:
                                job.current_status = "FAILED"
                                message += f" / Copie échouée : {copy_err}"
                    else:
                        job.current_status = "SUCCESS"
                        job.previous_successful_hash_global = computed_hash
                        message = "Premier succès validé."
                        try:
                            validated_path = os.path.join(settings.VALIDATED_BACKUPS_BASE_PATH, job.company_name,job.city, str(job.year))
                            job.file_storage_path_template = os.path.join(validated_path, staged_file_name)
                            os.makedirs(validated_path, exist_ok=True)
                            shutil.copy2(backup_file_path, os.path.join(validated_path, staged_file_name))
                        except Exception as copy_err:
                            job.current_status = "FAILED"
                            message += f" / Copie échouée : {copy_err}"
            except Exception as hash_error:
                job.current_status = "FAILED"
                message = f"Erreur lors du calcul du hash : {hash_error}"
        else:
            message = f"Fichier backup introuvable : {staged_file_name}"
    else:
        job.current_status = "MISSING"
        message = "Aucune entrée dans le rapport pour ce job."

    # Mise à jour du job
    job.last_checked_timestamp = now
        
    
        
    # Création de l'entrée BackupEntry enrichie
    backup_entry = BackupEntry(
        expected_job_id=job.id,
        timestamp=now,
        status=job.current_status,
        message=message,
        expected_hash = expected_hash,#job.previous_successful_hash_global or "",
        operation_log_file_name=operation_log_file_name,
        agent_id=agent_id,
        agent_overall_status=agent_status,
        server_calculated_staged_hash=computed_hash or "",
        server_calculated_staged_size=os.path.getsize(backup_file_path) if backup_file_path and os.path.exists(backup_file_path) else None,
        
        previous_successful_hash_global=job.previous_successful_hash_global,
        hash_comparison_result= True if ((computed_hash == expected_hash) and (computed_hash and expected_hash)) else False,
        
        created_at=now
    )

    db_session.add(job)
    db_session.add(backup_entry)
    ##db_session.flush() #force l'insertion SQL sans commit pour récupérer l'ID
    
    if job.current_status in ["MISSING", "UNCHANGED", "FAILED" ]:
        try:
            print(f"************ DEBUT NOTIFICATION *************")
            notify_backup_status_change(job, backup_entry, expected_hash)
        except NotificationError as e:
            print(f"Echec de l'envoi de la notification {e}")
        except Exception as e:
            print(f"Une erreur inattendue est survenue {e}")
            send_notification(job, message)

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
    print(f"📄 Traitement du JSON************ : {agent_log_json_path}")

    report = load_json_report(agent_log_json_path)

    if not isinstance(report, dict):
        print(f"⚠️ Rapport JSON vide ou corrompu : {agent_log_json_path}")
        archive_report(agent_log_json_path)
        return

    if not is_valid_backup_report(report):
        print(f"❌ Rapport invalide — ignoré : {agent_log_json_path}")
        archive_report(agent_log_json_path)
        return

    databases_data = report.get("databases", {})

    active_jobs = db_session.query(ExpectedBackupJob).filter_by(is_active=True).all()

    agent_id = report.get("agent_id")
    operation_log_file_name = os.path.basename(agent_log_json_path)
    agent_status = report.get("overall_status")

    for job in active_jobs:
        process_expected_job(
            job,
            databases_data,
            agent_databases_folder, 
            agent_id,
            operation_log_file_name,
            agent_status,
            db_session
        )
    db_session.commit()
    print(f"fonction process_agent ok")

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
    print("🗂 Chemin racine utilisé***** :", root_folder)
    print("🧪 Contenu racine******* :", os.listdir(root_folder))


    for agent_name in os.listdir(root_folder):
        print(f"*********2X  { os.listdir(root_folder) }  2X***********")
        agent_path = os.path.join(root_folder, agent_name)
        print(f"*********3X  { os.listdir(agent_path) }  3X***********")
        if not os.path.isdir(agent_path):
            continue
        log_folder = os.path.join(agent_path, "log")
        databases_folder = os.path.join(agent_path, "databases")
        if not os.path.isdir(log_folder) or not os.path.isdir(databases_folder):
            continue
        for file_name in os.listdir(log_folder):
            print(f"*********4X  { os.listdir(log_folder) }  4X***********")
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
