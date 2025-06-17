# app/services/new_scanner.py
"""
Ce scanner MVP (basé sur #MVPSCAN#) réalise les actions suivantes :
  - Parcourt la racine des agents définie par settings.BACKUP_STORAGE_ROOT.
  - Pour chaque dossier agent, il recherche dans 'log/' un fichier JSON (rapport) et dans 'database/' les backups.
  - Pour chaque job attendu (ExpectedBackupJob) lié à l'agent, il lit le rapport et vérifie si un backup est déposé.
  - S'il existe, il calcule le hash du fichier backup et le compare à la valeur attendue (sha256_checksum).
      → Si le hash correspond, on considère le backup comme VALIDÉ (SUCCESS).
      → Sinon, il est marqué HASH_MISMATCH.
  - S'il manque le backup ou la clé "staged_file_name" dans le JSON, le job est marqué MISSING.
  - Après traitement, le rapport JSON est archivé via un déplacement dans un sous-dossier "_archive".
  - En cas de backup valide, le backup est copié (et non déplacé) dans le dossier de validation défini par settings.VALIDATED_BACKUPS_BASE_PATH.
  - Enfin, le scanner met à jour la table BackupEntry et le job (ExpectedBackupJob) avec le statut constaté.
Ce scanner est censé être lancé à intervalle régulier via un scheduler ou un endpoint manuel.
"""

import os
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session

# Importation des modèles simplifiés
from app.models.models import ExpectedBackupJob, BackupEntry
# Importation des utilitaires
from app.utils.file_operations import ensure_directory_exists, move_file, copy_file
from app.utils.crypto import calculate_file_sha256
# Import de la configuration
from config.settings import settings

logger = logging.getLogger(__name__)

class NewBackupScanner:
    def __init__(self, session: Session):
        self.session = session
        self.settings = settings
        self.logger = logger

    def scan(self) -> None:
        self.logger.info("Démarrage d'un nouveau cycle de scan (MVP)")
        backup_root = self.settings.BACKUP_STORAGE_ROOT

        if not os.path.exists(backup_root):
            self.logger.error(f"Répertoire racine des backups introuvable: {backup_root}")
            return

        # Parcours de tous les dossiers d'agents
        agent_folders = [
            os.path.join(backup_root, d)
            for d in os.listdir(backup_root)
            if os.path.isdir(os.path.join(backup_root, d))
        ]

        for agent_folder in agent_folders:
            agent_id = os.path.basename(agent_folder)
            self.logger.info(f"Analyse de l'agent: {agent_id}")

            # Traitement du dossier log de l'agent
            log_dir = os.path.join(agent_folder, "log")
            if not os.path.exists(log_dir):
                self.logger.warning(f"Dossier 'log' absent pour l'agent {agent_id}")
                continue

            json_files = [
                f for f in os.listdir(log_dir)
                if f.lower().endswith(".json") and not f.startswith("_archive")
            ]
            if not json_files:
                self.logger.info(f"Aucun fichier JSON trouvé pour l'agent {agent_id}")
                continue

            # On traite le premier rapport trouvé (dans ce MVP, on considère un rapport utile par cycle)
            json_file = sorted(json_files)[0]
            json_path = os.path.join(log_dir, json_file)
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    report_data = json.load(f)
                self.logger.info(f"Lecture du rapport {json_file} de l'agent {agent_id}")
            except Exception as e:
                self.logger.error(f"Erreur de lecture du fichier {json_path} : {e}")
                continue

            # Parcours des jobs attendus pour cet agent
            expected_jobs = self.session.query(ExpectedBackupJob).filter_by(
                agent_id_responsible=agent_id
            ).all()

            # Emplacement du dossier backup dans l'arborescence de l'agent
            db_folder = os.path.join(agent_folder, "database")
            for job in expected_jobs:
                # Extraction des informations backup pour ce job depuis le rapport JSON
                db_report = report_data.get("databases", {}).get(job.database_name, {})
                backup_filename = db_report.get("staged_file_name")
                if not backup_filename:
                    self.logger.warning(
                        f"Info backup manquante pour le job {job.database_name} de l'agent {agent_id}"
                    )
                    self._mark_job_as_missing(job)
                    continue

                backup_file_path = os.path.join(db_folder, backup_filename)
                if os.path.exists(backup_file_path):
                    try:
                        calculated_hash = calculate_file_sha256(backup_file_path)
                    except Exception as e:
                        self.logger.error(f"Erreur lors du calcul du hash pour {backup_file_path} : {e}")
                        calculated_hash = None

                    expected_hash = db_report.get("sha256_checksum")
                    # Pour le MVP, le backup est validé si le hash correspond
                    status = "SUCCESS" if calculated_hash == expected_hash else "HASH_MISMATCH"
                    self._update_backup_entry(job, backup_file_path, status, calculated_hash)
                    if status == "SUCCESS":
                        self._promote_backup(backup_file_path, job)
                else:
                    self.logger.warning(
                        f"Fichier de backup introuvable : {backup_file_path} pour le job {job.database_name}"
                    )
                    self._mark_job_as_missing(job)

            # Archivage du rapport JSON traité
            self._archive_file(json_path)

        self.session.commit()
        self.logger.info("Cycle de scan terminé.")

    def _update_backup_entry(self, job: ExpectedBackupJob, backup_file_path: str, status: str, file_hash: str) -> None:
        new_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=datetime.now(timezone.utc),
            status=status,
            message=f"Backup traité avec le statut {status}",
            ##source_file_path=backup_file_path,
            calculated_hash=file_hash
        )
        self.session.add(new_entry)
        job.current_status = status
        job.last_checked_timestamp = datetime.now(timezone.utc)
        self.logger.info(f"Job {job.database_name} de l'agent {job.agent_id_responsible} mis à jour: {status}")

    def _mark_job_as_missing(self, job: ExpectedBackupJob) -> None:
        new_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=datetime.now(timezone.utc),
            status="MISSING",
            message="Backup manquant"
        )
        self.session.add(new_entry)
        job.current_status = "MISSING"
        job.last_checked_timestamp = datetime.now(timezone.utc)
        self.logger.info(f"Job {job.database_name} de l'agent {job.agent_id_responsible} marqué MISSING")

    def _promote_backup(self, backup_file_path: str, job: ExpectedBackupJob) -> None:
        """
        Copie le backup validé vers le dossier de validation.
        Le fichier original n'est pas déplacé de l'arborescence de l'agent.
        """
        validated_path = self.settings.VALIDATED_BACKUPS_BASE_PATH
        ensure_directory_exists(validated_path)
        destination_path = os.path.join(validated_path, os.path.basename(backup_file_path))
        try:
            copy_file(backup_file_path, destination_path)
            self.logger.info(f"Backup {backup_file_path} copié vers {destination_path}")
        except Exception as e:
            self.logger.error(f"Erreur lors de la promotion (copie) du backup {backup_file_path}: {e}")

    def _archive_file(self, file_path: str) -> None:
        folder = os.path.dirname(file_path)
        archive_dir = os.path.join(folder, "_archive")
        ensure_directory_exists(archive_dir)
        destination_path = os.path.join(archive_dir, os.path.basename(file_path))
        try:
            move_file(file_path, destination_path)
            self.logger.info(f"Fichier {file_path} archivé dans {destination_path}")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'archivage du fichier {file_path}: {e}")

def run_new_scanner(session: Session) -> None:
    scanner = NewBackupScanner(session)
    scanner.scan()
