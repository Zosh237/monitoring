# app/services/scanner.py
# Ce module implémente le scanner principal qui surveille l'état des sauvegardes.

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

# Importe la configuration de l'application
from config.settings import settings

logger = logging.getLogger(__name__)

class ScannerError(Exception):
    """Exception personnalisée pour les erreurs du scanner."""
    pass

class BackupScanner:
    """
    Scanner principal responsable de la surveillance des sauvegardes selon une logique en 3 phases :
    1. Collecte et validation de tous les rapports STATUS.json
    2. Évaluation et mise à jour de chaque job de sauvegarde attendu  
    3. Archivage des rapports traités
    """
    
    def __init__(self, session: Session):
        """Initialise le scanner avec une session de base de données."""
        self.session = session
        self.settings = settings
        self.logger = logger
        # Stockage des rapports pertinents par (agent_id, database_name)
        self.all_relevant_reports_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
        # File d'attente pour l'archivage des STATUS.json
        self.status_files_to_archive: Set[str] = set()
        logger.debug("BackupScanner initialisé.")

    def scan_all_jobs(self) -> None:

        """
        Point d'entrée principal du scanner. Exécute les 3 phases séquentielles :
        Phase 1 : Collecte et traitement initial de tous les rapports d'agents
        Phase 2 : Évaluation et mise à jour de chaque job de sauvegarde attendu
        Phase 3 : Archivage des rapports STATUS.json traités
        """
        self.logger.info("Début du scan de tous les jobs de sauvegarde.")
        self.logger.info(f"📂 Racine BACKUP = {self.settings.BACKUP_STORAGE_ROOT}")
        self.logger.info(f"🕓 Fenêtre de collecte = ±{self.settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES} minutes")

        
        # Réinitialisation des structures pour cette exécution
        self.all_relevant_reports_map.clear()
        self.status_files_to_archive.clear()
        
        # Phase 1 : Collecte et validation des rapports
        self._phase1_collect_and_validate_reports()
        
        # Phase 2 : Évaluation des jobs
        self._phase2_evaluate_jobs()
        
        # Phase 3 : Archivage des rapports
        self._phase3_archive_reports()
        
        self.logger.info("Scan des jobs de sauvegarde terminé.")

    def _phase1_collect_and_validate_reports(self) -> None:
        """
        Phase 1 : Parcours des répertoires d'agents pour collecter et valider
        tous les rapports STATUS.json disponibles.
        """
        self.logger.info("Phase 1 : Collecte et validation des rapports STATUS.json")
        
        if not os.path.exists(self.settings.BACKUP_STORAGE_ROOT):
            self.logger.warning(f"Répertoire racine de stockage non trouvé : {self.settings.BACKUP_STORAGE_ROOT}")
            return
            
        for agent_folder_name in os.listdir(self.settings.BACKUP_STORAGE_ROOT):
            agent_folder_path = os.path.join(self.settings.BACKUP_STORAGE_ROOT, agent_folder_name)
            
            if not os.path.isdir(agent_folder_path):
                continue
                
            # Validation du nom du dossier d'agent
            if not self._is_valid_agent_folder_name(agent_folder_name):
                self.logger.warning(f"Nom de dossier d'agent invalide : {agent_folder_name}")
                self._archive_invalid_agent_reports(agent_folder_path)
                continue
                
            # Traitement des rapports de cet agent
            self._process_agent_reports(agent_folder_name, agent_folder_path)

    def _phase2_evaluate_jobs(self) -> None:
        """
        Phase 2 : Évaluation de chaque job de sauvegarde attendu
        en recherchant les rapports pertinents et en déterminant les statuts.
        """
        self.logger.info("Phase 2 : Évaluation des jobs de sauvegarde")
        
        all_active_jobs = self.session.query(ExpectedBackupJob).filter(
            ExpectedBackupJob.is_active == True
        ).all()
        
        for job in all_active_jobs:
            self._evaluate_single_job(job)

    def _phase3_archive_reports(self) -> None:
        """
        Phase 3 : Archivage de tous les rapports STATUS.json traités.
        """
        self.logger.info("Phase 3 : Archivage des rapports STATUS.json")
        
        for status_file_path in self.status_files_to_archive:
            if os.path.exists(status_file_path):
                self._archive_single_status_file(status_file_path)

    def _process_agent_reports(self, agent_folder_name: str, agent_folder_path: str) -> None:
        """
        Traite tous les rapports STATUS.json d'un agent spécifique.
        """
        parts = agent_folder_name.split("_")
        company_name, city, neighborhood = parts[0], parts[1], parts[2]
        
        agent_log_dir = os.path.join(agent_folder_path, "log")
        if not os.path.exists(agent_log_dir):
            self.logger.warning(f"Dossier log non trouvé pour l'agent : {agent_folder_name}")
            return
            
        # Recherche des fichiers STATUS.json pertinents
        status_files = self._find_status_files_for_agent(
            agent_log_dir, company_name, city, neighborhood
        )
        
        # Traitement de chaque fichier STATUS.json trouvé
        for status_file_path in status_files:
            self.status_files_to_archive.add(status_file_path)
            
            try:
                status_data = validate_status_file(status_file_path)
                self._process_valid_status_file(agent_folder_name, status_file_path, status_data)
                
            except (StatusFileValidationError, DateTimeUtilityError, json.JSONDecodeError) as e:
                self.logger.warning(f"Fichier STATUS.json invalide '{status_file_path}': {e}")
            except Exception as e:
                self.logger.error(f"Erreur lors du traitement de '{status_file_path}': {e}", exc_info=True)

    def _process_valid_status_file(self, agent_folder_name: str, status_file_path: str, status_data: Dict[str, Any]) -> None:
        """
        Traite un fichier STATUS.json valide et met à jour la carte des rapports pertinents.
        """
        # Vérification de la fraîcheur du rapport
        op_timestamp_str = status_data.get("operation_end_time")
        if not op_timestamp_str:
            self.logger.warning(f"Champ 'operation_end_time' manquant dans {status_file_path}")
            return
            
        op_timestamp = parse_iso_datetime(op_timestamp_str)
        now_utc = get_utc_now()
        
        if now_utc - op_timestamp > timedelta(days=self.settings.MAX_STATUS_FILE_AGE_DAYS):
            self.logger.warning(f"Rapport trop ancien dans {status_file_path} : {op_timestamp}")
            return
            
        # Vérification de la cohérence de l'agent_id
        reported_agent_id = status_data.get("agent_id")
        if reported_agent_id != agent_folder_name:
            self.logger.warning(f"Incohérence agent_id dans {status_file_path}: attendu '{agent_folder_name}', trouvé '{reported_agent_id}'")
            return
            
        # Traitement des bases de données rapportées
        databases = status_data.get("databases", {})
        for db_name, db_data in databases.items():
            report_key = (agent_folder_name, db_name)
            
            # Conserver seulement le rapport le plus récent pour chaque combinaison (agent, db)
            if report_key not in self.all_relevant_reports_map or \
               op_timestamp > self.all_relevant_reports_map[report_key]['operation_timestamp']:
                
                self.all_relevant_reports_map[report_key] = {
                    'status_file_path': status_file_path,
                    'operation_timestamp': op_timestamp,
                    'overall_status_data': status_data,
                    'db_data': db_data
                }

    def _evaluate_single_job(self, job: ExpectedBackupJob) -> None:
        """
        Évalue un job spécifique en recherchant un rapport pertinent.
        """
        report_key = (job.agent_id_responsible, job.database_name)
        
        if report_key in self.all_relevant_reports_map:
            report_info = self.all_relevant_reports_map[report_key]
            
            # Vérification de la pertinence temporelle pour le cycle du job
            if self._is_report_relevant_for_job_cycle(
                report_info['operation_timestamp'], job
            ):
                self.logger.info(f"Traitement du rapport pour le job {job.database_name} (ID: {job.id})")
                self._process_job_with_report(job, report_info)
            else:
                self.logger.debug(f"Rapport trouvé mais non pertinent pour le cycle du job {job.database_name}")
                self._handle_missing_or_unknown_job(job)
        else:
            self.logger.debug(f"Aucun rapport trouvé pour le job {job.database_name}")
            self._handle_missing_or_unknown_job(job)

    def _process_job_with_report(self, job: ExpectedBackupJob, report_info: Dict[str, Any]) -> None:
        """
        Traite un job ayant un rapport pertinent.
        """
        overall_status_data = report_info['overall_status_data']
        db_data = report_info['db_data']
        status_file_path = report_info['status_file_path']
        
        # Détermination du chemin du fichier stagé
        staged_file_name = db_data.get("staged_file_name", "")
        if not staged_file_name:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Nom du fichier stagé manquant pour {job.database_name}"
            self.logger.error(entry_message)
            
            self._save_backup_entry_and_update_job(
                job, entry_status, entry_message, get_utc_now(),
                overall_status_data, db_data, None, None, None, status_file_path
            )
            return
            
        staged_db_file_path = os.path.join(
            self.settings.BACKUP_STORAGE_ROOT,
            job.agent_id_responsible,
            "database",
            staged_file_name
        )
        
        # Analyse de l'intégrité et détermination du statut
        try:
            (server_hash, server_size, entry_status, 
             entry_message, hash_comparison_result) = self._determine_status_and_integrity(
                job, staged_db_file_path, db_data, get_utc_now()
            )
            
            # Si la sauvegarde est valide, on la promeut
            if entry_status == BackupEntryStatus.SUCCESS:
                try:
                    final_path = promote_backup(staged_db_file_path, job)
                    self.logger.info(f"Sauvegarde promue avec succès vers : {final_path}")
                except BackupManagerError as e:
                    self.logger.error(f"Échec de la promotion de la sauvegarde : {e}")
                    entry_status = BackupEntryStatus.FAILED
                    entry_message = f"Échec de la promotion : {e}"
            
        except ScannerError as e:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Échec de traitement pour {job.database_name} : {e}"
            server_hash = server_size = hash_comparison_result = None
            self.logger.error(entry_message)
        except Exception as e:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Erreur inattendue pour {job.database_name} : {e}"
            server_hash = server_size = hash_comparison_result = None
            self.logger.critical(entry_message, exc_info=True)
        
        # Sauvegarde des résultats
        self._save_backup_entry_and_update_job(
            job, entry_status, entry_message, get_utc_now(),
            overall_status_data, db_data, server_hash, server_size,
            hash_comparison_result, status_file_path
        )

    def _handle_missing_or_unknown_job(self, job: ExpectedBackupJob) -> None:
        """
        Gère les jobs sans rapport pertinent en vérifiant si la deadline est dépassée.
        """
        now_utc = get_utc_now()
        
        # Détermination de la date du cycle le plus récent
        target_date = now_utc.date()
        if (now_utc.hour < job.expected_hour_utc or 
            (now_utc.hour == job.expected_hour_utc and now_utc.minute < job.expected_minute_utc)):
            target_date = now_utc.date() - timedelta(days=1)
        
        # Calcul de la deadline du cycle
        expected_datetime = datetime(
            target_date.year, target_date.month, target_date.day,
            job.expected_hour_utc, job.expected_minute_utc, 0, 0, 
            tzinfo=timezone.utc
        )
        deadline = expected_datetime + timedelta(
            minutes=self.settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES
        )
        
        if now_utc <= deadline:
            self.logger.debug(f"Job {job.database_name} : Deadline non atteinte ({deadline})")
            return
            
        # Vérification si le job n'a pas déjà été traité pour ce cycle
        recent_entry = self.session.query(BackupEntry).filter(
            BackupEntry.expected_job_id == job.id,
            BackupEntry.timestamp >= expected_datetime - timedelta(
                minutes=self.settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES * 2
            )
        ).order_by(BackupEntry.timestamp.desc()).first()
        
        if recent_entry and recent_entry.status in [
            BackupEntryStatus.SUCCESS, BackupEntryStatus.FAILED,
            BackupEntryStatus.HASH_MISMATCH, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
        ]:
            self.logger.debug(f"Job {job.database_name} : Entrée récente existante ({recent_entry.status.value})")
            return
            
        # Création de l'entrée MISSING
        self._create_missing_entry(job, target_date, now_utc)

    def _determine_status_and_integrity(
        self, job: ExpectedBackupJob, staged_file_path: str, 
        agent_data: dict, now_utc: datetime
    ) -> Tuple[Optional[str], Optional[int], BackupEntryStatus, str, Optional[bool]]:
        """
        Détermine le statut et vérifie l'intégrité d'une sauvegarde.
        """
        # Extraction des statuts rapportés par l'agent
        backup_status = agent_data.get("BACKUP", {}).get("status", False)
        compress_status = agent_data.get("COMPRESS", {}).get("status", False)
        transfer_status = agent_data.get("TRANSFER", {}).get("status", False)
        
        agent_hash = agent_data.get("COMPRESS", {}).get("sha256_checksum")
        agent_size = agent_data.get("COMPRESS", {}).get("size")
        
        # Vérification des échecs rapportés par l'agent
        if not all([backup_status, compress_status, transfer_status]):
            failed_processes = []
            if not backup_status: failed_processes.append("backup")
            if not compress_status: failed_processes.append("compression") 
            if not transfer_status: failed_processes.append("transfert")
            
            message = f"Échec agent pour {job.database_name} : {', '.join(failed_processes)}"
            logs_summary = agent_data.get('logs_summary')
            if logs_summary:
                message += f". Détails : {logs_summary}"
                
            return None, None, BackupEntryStatus.FAILED, message, None
            
        # Vérification de l'existence du fichier
        if not os.path.exists(staged_file_path):
            return (None, None, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED,
                   f"Fichier stagé introuvable pour {job.database_name} : {staged_file_path}", None)
        
        # Calcul des valeurs côté serveur
        try:
            server_hash = calculate_file_sha256(staged_file_path)
            server_size = os.path.getsize(staged_file_path)
            
            # Conversion et validation de la taille agent
            try:
                agent_size = int(agent_size) if agent_size is not None else -1
            except (ValueError, TypeError):
                agent_size = -1
                
        except (CryptoUtilityError, FileOperationError, OSError) as e:
            return (None, None, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED,
                   f"Erreur de vérification fichier pour {job.database_name} : {e}", None)
        
        # Vérification de l'intégrité du transfert
        if server_hash != agent_hash or server_size != agent_size:
            message = (f"Échec intégrité transfert pour {job.database_name}. "
                      f"Agent (hash/size): {agent_hash}/{agent_size}, "
                      f"Serveur (hash/size): {server_hash}/{server_size}")
            return server_hash, server_size, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED, message, None
        
        # Comparaison avec le hash précédent pour détecter les changements  
        hash_comparison_result = True
        status = BackupEntryStatus.SUCCESS
        message = "Sauvegarde transférée avec intégrité"
        
        if job.previous_successful_hash_global and server_hash == job.previous_successful_hash_global:
            status = BackupEntryStatus.HASH_MISMATCH
            message = f"Hash identique au précédent succès pour {job.database_name} - contenu potentiellement inchangé"
            hash_comparison_result = False
            
        return server_hash, server_size, status, message, hash_comparison_result

    def _save_backup_entry_and_update_job(
        self, job: ExpectedBackupJob, entry_status: BackupEntryStatus,
        entry_message: str, now_utc: datetime, overall_status_data: Dict[str, Any],
        agent_report_data: Dict[str, Any], server_hash: Optional[str],
        server_size: Optional[int], hash_comparison_result: Optional[bool],
        status_file_path: str
    ):
        """Crée une nouvelle entrée de sauvegarde et met à jour le job."""
        
        status_file_name = os.path.basename(status_file_path) if status_file_path else None
        agent_id = overall_status_data.get("agent_id", job.agent_id_responsible)
        
        # Création de l'entrée BackupEntry
        new_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=now_utc,
            status=entry_status,
            message=entry_message,
            operation_log_file_name=status_file_name,
            agent_id=agent_id,
            agent_overall_status=overall_status_data.get("overall_status"),
            
            # Détails des processus agent
            agent_backup_process_status=agent_report_data.get("BACKUP", {}).get("status"),
            agent_backup_process_start_time=self._parse_datetime_safe(agent_report_data.get("BACKUP", {}).get("start_time")),
            agent_backup_process_timestamp=self._parse_datetime_safe(agent_report_data.get("BACKUP", {}).get("end_time")),
            agent_backup_hash_pre_compress=agent_report_data.get("BACKUP", {}).get("sha256_checksum"),
            agent_backup_size_pre_compress=agent_report_data.get("BACKUP", {}).get("size"),
            
            agent_compress_process_status=agent_report_data.get("COMPRESS", {}).get("status"),
            agent_compress_process_start_time=self._parse_datetime_safe(agent_report_data.get("COMPRESS", {}).get("start_time")),
            agent_compress_process_timestamp=self._parse_datetime_safe(agent_report_data.get("COMPRESS", {}).get("end_time")),
            agent_compress_hash_post_compress=agent_report_data.get("COMPRESS", {}).get("sha256_checksum"),
            agent_compress_size_post_compress=agent_report_data.get("COMPRESS", {}).get("size"),
            
            agent_transfer_process_status=agent_report_data.get("TRANSFER", {}).get("status"),
            agent_transfer_process_start_time=self._parse_datetime_safe(agent_report_data.get("TRANSFER", {}).get("start_time")),
            agent_transfer_process_timestamp=self._parse_datetime_safe(agent_report_data.get("TRANSFER", {}).get("end_time")),
            agent_transfer_error_message=agent_report_data.get("TRANSFER", {}).get("error_message"),
            agent_staged_file_name=agent_report_data.get("staged_file_name"),
            agent_logs_summary=agent_report_data.get("logs_summary"),
            
            # Détails calculés par le serveur
            server_calculated_staged_hash=server_hash,
            server_calculated_staged_size=server_size,
            previous_successful_hash_global=job.previous_successful_hash_global,
            hash_comparison_result=hash_comparison_result
        )
        
        self.session.add(new_entry)
        
        # Mise à jour du job
        status_map = {
            BackupEntryStatus.SUCCESS: JobStatus.OK,
            BackupEntryStatus.FAILED: JobStatus.FAILED,
            BackupEntryStatus.MISSING: JobStatus.MISSING,
            BackupEntryStatus.HASH_MISMATCH: JobStatus.HASH_MISMATCH,
            BackupEntryStatus.TRANSFER_INTEGRITY_FAILED: JobStatus.TRANSFER_INTEGRITY_FAILED,
        }
        
        job.current_status = status_map.get(entry_status, JobStatus.UNKNOWN)
        job.last_checked_timestamp = now_utc
        
        # Mise à jour du hash de succès pour les vrais succès
        if entry_status == BackupEntryStatus.SUCCESS:
            job.last_successful_backup_timestamp = now_utc
            job.previous_successful_hash_global = server_hash
            
        self.session.commit()
        self.session.refresh(job)
        
        self.logger.info(f"Job {job.database_name} mis à jour : {job.current_status.value}")

    def _create_missing_entry(self, job: ExpectedBackupJob, target_date, now_utc: datetime) -> None:
        """Crée une entrée MISSING pour un job."""
        new_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=now_utc,
            status=BackupEntryStatus.MISSING,
            message=f"Sauvegarde manquante pour le cycle du {target_date} à {job.expected_hour_utc:02d}:{job.expected_minute_utc:02d} UTC"
        )
        
        self.session.add(new_entry)
        job.current_status = JobStatus.MISSING
        job.last_checked_timestamp = now_utc
        self.session.commit()
        
        self.logger.info(f"Job {job.database_name} marqué MISSING pour le cycle du {target_date}")

    #def _find_status_files_for_agent(
    #    self, agent_log_dir: str, company_name: str, city: str, neighborhood: str
    #) -> list:
    #    """Recherche tous les fichiers STATUS.json pertinents pour un agent."""
    #    status_files = []
    #    expected_pattern = rf"^\d{{8}}_\d{{6}}_{re.escape(company_name)}_{re.escape(city)}_{re.escape(neighborhood)}\.json$"
        
    #    for filename in os.listdir(agent_log_dir):
    #        if re.match(expected_pattern, filename, re.IGNORECASE):
    #            status_files.append(os.path.join(agent_log_dir, filename))
                
    #    return status_files

    def _find_status_files_for_agent(
        self, agent_log_dir: str, company_name: str, city: str, neighborhood: str
    ) -> list:
        """Recherche tous les fichiers STATUS.json pertinents pour un agent."""
        status_files = []
        
        # Format 1 : timestampé (production)
        pattern_1 = rf"^\d{{8}}_\d{{6}}_{re.escape(company_name)}_{re.escape(city)}_{re.escape(neighborhood)}\.json$"
        
        # Format 2 : préfixé HORODATAGE (test manuel)
        pattern_2 = rf"^HORODATAGE_{re.escape(company_name)}_{re.escape(city)}_{re.escape(neighborhood)}\.json$"

        for filename in os.listdir(agent_log_dir):
            if re.match(pattern_1, filename, re.IGNORECASE) or re.match(pattern_2, filename, re.IGNORECASE):
                full_path = os.path.join(agent_log_dir, filename)
                status_files.append(full_path)

        if not status_files:
            self.logger.warning(
                f"🚫 Aucun STATUS.json trouvé pour {company_name}_{city}_{neighborhood} dans {agent_log_dir}"
            )

        return status_files


    def _archive_invalid_agent_reports(self, agent_folder_path: str) -> None:
        """Archive tous les STATUS.json d'un agent invalide."""
        log_dir = os.path.join(agent_folder_path, "log")
        if not os.path.exists(log_dir):
            return
            
        archive_dir = os.path.join(log_dir, "_archive")
        ensure_directory_exists(archive_dir)
        
        for filename in os.listdir(log_dir):
            if filename.lower().endswith('.json'):
                source_path = os.path.join(log_dir, filename)
                self.logger.info(f"➡️ Scanner explore : {self.settings.agent_reports_root}")
                self.status_files_to_archive.add(source_path)

    def _archive_single_status_file(self, status_file_path: str) -> None:
        """Archive un seul fichier STATUS.json."""
        try:
            # Détermination du répertoire d'archive
            log_dir = os.path.dirname(status_file_path)
            archive_dir = os.path.join(log_dir, "_archive")
            ensure_directory_exists(archive_dir)
            
            # Déplacement du fichier
            dest_path = os.path.join(archive_dir, os.path.basename(status_file_path))
            move_file(status_file_path, dest_path)
            
            self.logger.info(f"STATUS.json archivé : {os.path.basename(status_file_path)}")
            
        except FileOperationError as e:
            self.logger.error(f"Échec archivage de {os.path.basename(status_file_path)} : {e}")
        except Exception as e:
            self.logger.error(f"Erreur archivage de {os.path.basename(status_file_path)} : {e}", exc_info=True)

    def _is_report_relevant_for_job_cycle(self, report_timestamp: datetime, job: ExpectedBackupJob) -> bool:
        """Vérifie si un rapport est pertinent pour le cycle d'un job."""
        report_date = report_timestamp.date()
        
        expected_datetime = datetime(
            report_date.year, report_date.month, report_date.day,
            job.expected_hour_utc, job.expected_minute_utc, 0, 0,
            tzinfo=timezone.utc
        )
        
        window_minutes = self.settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES
        window_start = expected_datetime - timedelta(minutes=window_minutes)
        window_end = expected_datetime + timedelta(minutes=window_minutes)
        
        is_relevant = window_start <= report_timestamp <= window_end
        
        self.logger.debug(
            f"Pertinence rapport : {report_timestamp.time()} vs job {job.expected_hour_utc:02d}:{job.expected_minute_utc:02d} "
            f"fenêtre [{window_start.time()}-{window_end.time()}] -> {is_relevant}"
        )
        
        return is_relevant

    def _is_valid_agent_folder_name(self, folder_name: str) -> bool:
        """Vérifie si le nom de dossier d'agent est valide (ENTREPRISE_VILLE_QUARTIER)."""
        return len(folder_name.split("_")) == 3

    def _parse_datetime_safe(self, datetime_str: str) -> Optional[datetime]:
        """Parse une chaîne datetime de manière sécurisée."""
        if not datetime_str:
            return None
        try:
            return parse_iso_datetime(datetime_str)
        except (DateTimeUtilityError, ValueError):
            return None

def run_scanner(session: Session):
    """
    Fonction wrapper pour exécuter le scanner, destinée à être appelée par APScheduler.
    """
    scanner = BackupScanner(session)
    scanner.scan_all_jobs()