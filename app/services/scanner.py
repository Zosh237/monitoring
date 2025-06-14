# app/services/scanner.py
# Ce module implémente le scanner principal qui surveille l'état des sauvegardes.

import logging
import os
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import re # Pour l'analyse des noms de fichiers

# Importe les modèles de base de données
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus

# Importe les utilitaires et services nécessaires
from app.services.validation_service import validate_status_file, StatusFileValidationError
from app.utils.crypto import calculate_file_sha256, CryptoUtilityError
from app.utils.file_operations import ensure_directory_exists, move_file, delete_file, FileOperationError
from app.utils.datetime_utils import parse_iso_datetime, get_utc_now, is_time_within_window, DateTimeUtilityError

# Importe la configuration de l'application
from config.settings import settings

logger = logging.getLogger(__name__)

class ScannerError(Exception):
    """Exception personnalisée pour les erreurs du scanner."""
    pass

class BackupScanner:
    """
    Classe responsable de l'exécution du processus de scan des sauvegardes.
    Elle encapsule la logique de recherche des rapports d'agents, de validation
    des fichiers, de détermination des statuts et de mise à jour de la DB.
    """
    def __init__(self, db_session: Session):
        """
        Initialise le scanner avec une session de base de données.
        """
        self.db = db_session
        # Set pour stocker les clés des rapports STATUS.json déjà traités
        # durant cette exécution de scan_all_jobs, pour éviter les doublons.
        self.processed_status_reports_in_this_run = set() 
        logger.debug("BackupScanner initialisé.")

    def scan_all_jobs(self):
        """
        Fonction principale du scanner.
        1. Parcourt les dossiers de dépôt des agents (sites).
        2. Pour chaque site, trouve et traite le STATUS.json le plus récent et pertinent.
        3. Identifie les jobs qui sont MISSING après avoir traité tous les rapports.
        """
        logger.info("Démarrage du scan des sauvegardes pour tous les sites/agents...")

        agent_deposit_base_path = settings.BACKUP_STORAGE_ROOT # Utilisez BACKUP_STORAGE_ROOT pour le chemin de base
        if not os.path.exists(agent_deposit_base_path):
            logger.warning(f"Le chemin de dépôt des agents n'existe pas : {agent_deposit_base_path}. Veuillez le créer ou vérifier la configuration.")
            self._mark_all_jobs_missing_if_no_agent_data_found()
            return

        # Lister uniquement les répertoires d'agents (qui sont nommés ENTREPRISE_VILLE_QUARTIER)
        agent_site_folders = [d for d in os.listdir(agent_deposit_base_path) if os.path.isdir(os.path.join(agent_deposit_base_path, d))]

        if not agent_site_folders:
            logger.info("Aucun dossier de site/agent trouvé dans la zone de dépôt. Aucune sauvegarde à scanner via rapports.")
            self._mark_all_jobs_missing_if_no_agent_data_found()
            return

        # Dictionnaire pour suivre les jobs traités par un rapport STATUS.json pertinent lors de ce scan
        # Clé: (company_name, city, neighborhood), Valeur: True si au moins un STATUS.json pertinent a été traité
        sites_with_relevant_status_processed = set()

        for agent_folder_name in agent_site_folders:
            try:
                # Extraire company, city, neighborhood du nom du dossier de l'agent
                parts = agent_folder_name.split('_')
                if len(parts) < 3:
                    logger.warning(f"Nom de dossier d'agent invalide (attendu ENTREPRISE_VILLE_QUARTIER) : {agent_folder_name}. Ignoré.")
                    continue
                company_name = parts[0]
                city = parts[1]
                neighborhood = '_'.join(parts[2:]) # Pour gérer les quartiers avec des underscores

                # Processus complet pour un site/agent donné
                if self._process_agent_site(agent_folder_name, company_name, city, neighborhood):
                    sites_with_relevant_status_processed.add((company_name, city, neighborhood))

            except Exception as e:
                logger.error(f"Erreur lors du traitement du dossier de l'agent '{agent_folder_name}': {e}", exc_info=True)

        # Après avoir parcouru tous les dossiers d'agents et traité leurs rapports,
        # identifier les jobs qui sont MISSING car leur site n'a pas eu de STATUS.json pertinent traité.
        all_active_jobs = self.db.query(ExpectedBackupJob).filter(ExpectedBackupJob.is_active == True).all()
        for job in all_active_jobs:
            job_site_identifier = (job.company_name, job.city, job.neighborhood)
            if job_site_identifier not in sites_with_relevant_status_processed:
                # Si aucun rapport pertinent n'a été traité pour ce site, marquer ses jobs comme MISSING si nécessaire.
                self._create_missing_entry_for_job_if_needed(job, "Aucun rapport STATUS.json pertinent trouvé pour le site de ce job.")

        logger.info("Scan des sauvegardes terminé pour tous les agents.")
    
    def _mark_all_jobs_missing_if_no_agent_data_found(self):
        """
        Marque tous les jobs actifs en DB comme MISSING s'il n'y a aucun dossier d'agent
        ou aucun fichier STATUS.json pertinent n'a été trouvé globalement.
        """
        all_active_jobs = self.db.query(ExpectedBackupJob).filter(ExpectedBackupJob.is_active == True).all()
        for job in all_active_jobs:
            self._create_missing_entry_for_job_if_needed(job, "Le chemin de dépôt des agents est vide ou inaccessible. Sauvegarde manquante.")


    def _process_agent_site(self, agent_folder_name: str, company_name: str, city: str, neighborhood: str) -> bool:
        """
        Traite le dossier d'un site/agent spécifique : trouve le dernier STATUS.json pertinent,
        le traite pour tous les jobs associés à ce site, et archive le fichier.
        Retourne True si un STATUS.json pertinent a été traité, False sinon.
        """
        logger.info(f"Traitement du site/agent : {agent_folder_name} ({company_name}/{city}/{neighborhood})")

        # Construire les chemins des répertoires de logs et d'archive pour cet agent
        agent_log_dir = os.path.join(settings.BACKUP_STORAGE_ROOT, agent_folder_name, "log")
        agent_archive_dir = os.path.join(agent_log_dir, "_archive")
        ensure_directory_exists(agent_log_dir)
        ensure_directory_exists(agent_archive_dir) # Créer le dossier d'archive

        # Étape 1: Recherche du fichier STATUS.json le plus récent et pertinent pour ce site
        latest_status_file_path, overall_status_data = self._find_latest_relevant_status_file(
            agent_log_dir, company_name, city, neighborhood
        )

        if not latest_status_file_path or not overall_status_data:
            logger.info(f"Aucun fichier STATUS.json pertinent trouvé ou valide pour le site {company_name}/{city}/{neighborhood} dans le cycle actuel.")
            return False # Indique qu'aucun rapport pertinent n'a été traité pour ce site

        # Vérification si ce rapport a déjà été traité lors de l'exécution actuelle du scanner
        # (utilise le chemin du fichier et le timestamp interne comme clé)
        report_key = (latest_status_file_path, overall_status_data.get("operation_timestamp"))
        if report_key in self.processed_status_reports_in_this_run:
            logger.info(f"Le STATUS.json '{os.path.basename(latest_status_file_path)}' (timestamp interne {overall_status_data.get('operation_timestamp')}) a déjà été traité lors de ce cycle de scan. Ignoré.")
            return False # Déjà traité

        self.processed_status_reports_in_this_run.add(report_key) # Marquer comme traité pour ce scan

        logger.info(f"Traitement du fichier STATUS.json : {os.path.basename(latest_status_file_path)} (Timestamp interne: {overall_status_data.get('operation_timestamp')})")
        
        # Étape 2: Récupérer tous les jobs associés à ce site (company, city, neighborhood)
        # Ces jobs peuvent avoir des expected_hour_utc différents (ex: 13h et 20h)
        site_jobs = self.db.query(ExpectedBackupJob).filter(
            ExpectedBackupJob.company_name == company_name,
            ExpectedBackupJob.city == city,
            ExpectedBackupJob.neighborhood == neighborhood,
            ExpectedBackupJob.is_active == True
        ).all()

        if not site_jobs:
            logger.warning(f"Aucun job attendu trouvé en DB pour le site : {company_name}/{city}/{neighborhood}. Le STATUS.json sera archivé sans traitement spécifique des BDs.")
            self._archive_status_file(latest_status_file_path, agent_archive_dir)
            return False # Aucun job à traiter pour ce rapport

        # Étape 3: Traiter chaque base de données rapportée dans le STATUS.json
        reported_db_names = overall_status_data.get("databases", {}).keys()
        processed_db_jobs_this_status_file = set() # Pour suivre les BDs traitées par ce STATUS.json

        # Récupérer le timestamp d'opération du rapport (qui définit le cycle de sauvegarde)
        report_operation_timestamp = parse_iso_datetime(overall_status_data.get("operation_timestamp"))

        for db_name, agent_report_data in overall_status_data.get("databases", {}).items():
            job_for_db = next((job for job in site_jobs if job.database_name == db_name), None)

            if job_for_db:
                # Vérifier si ce rapport est pertinent pour le cycle attendu de ce job
                if self._is_report_relevant_for_job_cycle(report_operation_timestamp, job_for_db):
                    self._process_single_db_from_status_data(job_for_db, agent_report_data, overall_status_data, latest_status_file_path)
                    processed_db_jobs_this_status_file.add(db_name)
                else:
                    logger.warning(f"Rapport pour BD '{db_name}' du job {job_for_db.id} (Site {agent_folder_name}) avec timestamp {report_operation_timestamp} est hors de la fenêtre du cycle attendu ({job_for_db.expected_hour_utc:02d}:{job_for_db.expected_minute_utc:02d} UTC). Ignoré pour ce job.")
            else:
                logger.warning(f"Base de données '{db_name}' rapportée dans le STATUS.json de {agent_folder_name} mais aucun ExpectedBackupJob correspondant trouvé en DB pour ce site. Ignoré.")
        
        # Étape 4: Gérer les jobs MISSING pour ce site qui n'ont PAS été rapportés dans ce STATUS.json
        # (Ou si le rapport était hors de la fenêtre pour eux)
        for job in site_jobs:
            if job.database_name not in processed_db_jobs_this_status_file:
                # Si le job n'a pas été traité par un rapport pertinent, il est potentiellement MISSING
                self._create_missing_entry_for_job_if_needed(job, message_override=f"BD '{job.database_name}' du site {agent_folder_name} attendue mais non rapportée ou rapport non pertinent dans le STATUS.json actuel.")

        # Étape 5: Archivage du STATUS.json après son traitement réussi pour toutes les BDs qu'il concerne
        self._archive_status_file(latest_status_file_path, agent_archive_dir)
        return True # Indique qu'un rapport pertinent a été traité pour ce site

    def _find_latest_relevant_status_file(
        self, agent_log_dir: str, company_name: str, city: str, neighborhood: str
    ) -> tuple[str, dict]:
        """
        Recherche le fichier STATUS.json le plus récent et pertinent dans le dossier de logs de l'agent.
        La nomenclature attendue est HORODATAGE_ENTREPRISE_VILLE_QUARTIER.json.
        """
        relevant_files_info = []
        # Pattern pour le nom du fichier STATUS.json: YYYYMMDD_HHMMSS_ENTREPRISE_VILLE_QUARTIER.json
        expected_suffix_pattern = rf"_{re.escape(company_name)}_{re.escape(city)}_{re.escape(neighborhood)}\.json$"
        
        for filename in os.listdir(agent_log_dir):
            # Regex pour correspondre au format YYYYMMDD_HHMMSS_ENTREPRISE_VILLE_QUARTIER.json
            match = re.match(r"^(\d{8})_(\d{6})" + expected_suffix_pattern, filename)
            if match:
                file_path = os.path.join(agent_log_dir, filename)
                try:
                    # Extraire l'horodatage complet du début du nom de fichier
                    timestamp_str_from_name = f"{match.group(1)}_{match.group(2)}"
                    # Convertir en datetime UTC conscient
                    file_timestamp = datetime.strptime(timestamp_str_from_name, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
                    
                    relevant_files_info.append((file_timestamp, file_path))
                except (ValueError, IndexError):
                    logger.warning(f"Nom de fichier STATUS.json malformé (horodatage) : {filename}. Ignoré.")
                    continue
        
        if not relevant_files_info:
            return None, None # Aucun fichier pertinent trouvé

        # Trier par horodatage (le plus récent en premier)
        relevant_files_info.sort(key=lambda x: x[0], reverse=True)
        
        # Prendre le fichier le plus récent et tenter de le valider
        latest_file_timestamp_from_name, latest_file_path = relevant_files_info[0]
        
        try:
            overall_status_data = validate_status_file(latest_file_path)
            
            # Vérification du timestamp interne du STATUS.json
            op_timestamp_str_in_json = overall_status_data.get("operation_timestamp")
            if not op_timestamp_str_in_json:
                raise StatusFileValidationError("Le champ 'operation_timestamp' est manquant dans le STATUS.json.")
            
            op_timestamp_in_json = parse_iso_datetime(op_timestamp_str_in_json)
            
            # Vérifier la fraîcheur du rapport : l'opération doit être récente (par exemple, moins de MAX_STATUS_FILE_AGE_DAYS)
            if get_utc_now() - op_timestamp_in_json > timedelta(days=settings.MAX_STATUS_FILE_AGE_DAYS):
                 logger.warning(f"Timestamp interne du STATUS.json ({op_timestamp_in_json}) est trop ancien (plus de {settings.MAX_STATUS_FILE_AGE_DAYS} jours). Fichier : {latest_file_path}.")
                 raise ScannerError("Le STATUS.json trouvé est trop ancien.")
            
            # Stocker le chemin et le timestamp du nom de fichier pour les enregistrements d'historique
            overall_status_data['status_file_path'] = latest_file_path
            overall_status_data['operation_timestamp_from_filename'] = latest_file_timestamp_from_name 

            logger.info(f"Fichier STATUS.json le plus récent et pertinent trouvé : {latest_file_path} (Timestamp interne: {op_timestamp_in_json})")
            return latest_file_path, overall_status_data

        except StatusFileValidationError as e:
            logger.warning(f"Fichier STATUS.json '{os.path.basename(latest_file_path)}' invalide (validation échouée) : {e}. Ignoré.")
        except DateTimeUtilityError as e:
            logger.warning(f"Erreur de parsing de timestamp dans STATUS.json '{os.path.basename(latest_file_path)}': {e}. Ignoré.")
        except json.JSONDecodeError as e:
            logger.warning(f"Fichier STATUS.json '{os.path.basename(latest_file_path)}' corrompu (non-JSON) : {e}. Ignoré.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la lecture/validation de '{os.path.basename(latest_file_path)}': {e}. Ignoré.", exc_info=True)
        
        return None, None # Aucun fichier valide et pertinent trouvé


    def _is_report_relevant_for_job_cycle(self, report_operation_timestamp: datetime, job: ExpectedBackupJob) -> bool:
        """
        Détermine si le timestamp d'opération d'un rapport est pertinent pour le cycle attendu de ce job.
        C'est ici que l'on différencie les rapports de 13h et de 20h pour un même job.
        """
        # Obtenir la date du rapport (qui définit le jour de l'opération)
        report_date = report_operation_timestamp.date()

        # Construire l'heure attendue du job pour cette date
        expected_job_datetime_utc = datetime(
            report_date.year, report_date.month, report_date.day,
            job.expected_hour_utc, job.expected_minute_utc, 0, 0, tzinfo=timezone.utc
        )

        # Vérifier si le timestamp du rapport se situe dans la fenêtre de collecte
        # par rapport à l'heure attendue du job.
        is_relevant = is_time_within_window(
            report_operation_timestamp,
            job.expected_hour_utc,
            job.expected_minute_utc,
            settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES # Utilise la nouvelle variable de settings
        )
        logger.debug(f"Vérification pertinence: Rapport {report_operation_timestamp.time()} vs Job {job.expected_hour_utc:02d}:{job.expected_minute_utc:02d}. Fenêtre +/- {settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES}min -> {is_relevant}")
        return is_relevant


    def _process_single_db_from_status_data(self, job: ExpectedBackupJob, agent_report_data: dict, overall_status_data: dict, status_file_original_path: str):
        """
        Traite les données d'une seule base de données extraites d'un STATUS.json.
        """
        logger.info(f"Analyse des données pour la BD '{job.database_name}' du job {job.id}.")
        
        entry_status = BackupEntryStatus.FAILED
        entry_message = "Échec non spécifié."
        server_calculated_hash = None
        server_calculated_size = None
        hash_comparison_result = None

        now_utc = get_utc_now()
        
        # Le chemin du fichier stagé est maintenant basé sur le agent_id_responsible qui est le nom du dossier du site
        staged_db_file_path = os.path.join(
            settings.BACKUP_STORAGE_ROOT,
            job.agent_id_responsible, # agent_id_responsible est maintenant {ENTREPRISE}_{VILLE}_{QUARTIER}
            "database",
            f"{job.database_name}.sql.gz"
        )

        try:
            (server_calculated_hash, server_calculated_size, 
             entry_status, entry_message, hash_comparison_result) = \
                self._determine_status_and_integrity(job, staged_db_file_path, agent_report_data, now_utc)

        except ScannerError as e:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Échec de traitement interne pour {job.database_name} : {e}"
            logger.error(entry_message)
        except Exception as e:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Erreur inattendue lors du traitement de la BD {job.database_name} : {e}"
            logger.critical(entry_message, exc_info=True)
        
        self._save_backup_entry_and_update_job(
            job=job,
            entry_status=entry_status,
            entry_message=entry_message,
            now_utc=now_utc,
            overall_status_data=overall_status_data,
            agent_report_data=agent_report_data,
            server_calculated_staged_hash=server_calculated_hash,
            server_calculated_staged_size=server_calculated_size,
            hash_comparison_result=hash_comparison_result
        )
        # La promotion est faite ici si SUCCESS, sinon le fichier reste pour investigation
        self._perform_post_scan_actions(job, entry_status, staged_db_file_path)

    def _create_missing_entry_for_job_if_needed(self, job: ExpectedBackupJob, message_override: str = None):
        """
        Crée une BackupEntry de type MISSING pour un job si toutes les conditions suivantes sont remplies:
        1. L'heure actuelle est passée la fin de la fenêtre de collecte du cycle le plus récent du job.
        2. Le job n'a pas été scanné (ou mis à jour) avec un rapport pertinent depuis ce cycle.
        3. Le statut actuel du job n'est pas déjà un échec critique (FAILED, MISSING) pour ce cycle.
        Ceci évite de créer des entrées MISSING à chaque scan si un problème persiste.
        """
        now_utc = get_utc_now()
        
        # Déterminer la date du cycle attendu le plus récent
        # Si l'heure actuelle est avant l'heure attendue du job, le cycle pertinent est celui d'hier.
        # Sinon, c'est celui d'aujourd'hui.
        target_date_for_cycle = now_utc.date()
        if now_utc.hour < job.expected_hour_utc or \
           (now_utc.hour == job.expected_hour_utc and now_utc.minute < job.expected_minute_utc):
            target_date_for_cycle = now_utc.date() - timedelta(days=1)
        
        # L'heure de fin de la fenêtre de collecte pour le cycle attendu
        expected_cycle_collection_deadline = datetime(
            target_date_for_cycle.year, target_date_for_cycle.month, target_date_for_cycle.day,
            job.expected_hour_utc, job.expected_minute_utc, 0, 0, tzinfo=timezone.utc
        ) + timedelta(minutes=settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES)

        # Correction timezone : rendre last_checked_timestamp aware si besoin
        last_checked = job.last_checked_timestamp
        if last_checked is not None and last_checked.tzinfo is None:
            last_checked = last_checked.replace(tzinfo=timezone.utc)
        # Condition 2: Le job n'a pas été mis à jour par un rapport pertinent pour ce cycle
        if last_checked is None or last_checked < expected_cycle_collection_deadline:
            # Condition 3: Le statut actuel du job n'est pas déjà un échec qui couvre ce cycle.
            # On veut éviter de recréer une entrée MISSING si un échec pertinent a déjà été enregistré.
            # On considère que si le job est FAILED ou MISSING, et que son last_checked_timestamp
            # est après la deadline du cycle précédent, il est déjà bien pris en compte.
            
            # Plus simple pour MVP: Si le statut n'est PAS OK (SUCCESS) pour ce cycle récent.
            # L'idée est de créer une entrée MISSING s'il y a un DÉFICIT de rapport.
            # Si le job est déjà MISSING ou FAILED, on ne recrée pas une entrée MISSING si c'est pour le même cycle manquant.
            # Pour l'instant, on regarde juste si le job est OK.
            if job.current_status != JobStatus.OK : # S'il n'est pas OK, il est potentiellement MISSING ou FAILED
                # Pour éviter le spam, on peut ajouter une condition: est-ce que la dernière BackupEntry
                # pour ce job est déjà MISSING ET son timestamp est très proche de la deadline ?
                # Pour l'MVP, on simplifie : si pas OK, on crée l'entrée MISSING.
                self._create_missing_entry(job, message_override)
            else:
                 logger.debug(f"Job '{job.database_name}' a déjà un statut OK pour son cycle récent. Pas de nouvelle entrée MISSING.")
        else:
            logger.debug(f"Job '{job.database_name}' a été vérifié après la deadline du cycle récent. Pas de nouvelle entrée MISSING.")


    def _create_missing_entry(self, job: ExpectedBackupJob, message_override: str = None):
        """
        Fonction interne pour créer une BackupEntry de type MISSING.
        """
        now_utc = get_utc_now()
        entry_status = BackupEntryStatus.MISSING
        entry_message = message_override if message_override else f"Sauvegarde non détectée pour '{job.database_name}'."
        
        overall_status_data = {"overall_status": "no_report_found", "status_file_path": None, "operation_timestamp": None} 
        agent_report_data = {} 

        self._save_backup_entry_and_update_job(
            job=job,
            entry_status=entry_status,
            entry_message=entry_message,
            now_utc=now_utc,
            overall_status_data=overall_status_data,
            agent_report_data=agent_report_data,
            server_calculated_staged_hash=None,
            server_calculated_staged_size=None,
            hash_comparison_result=None
        )
        logger.warning(f"Job '{job.database_name}' marqué comme MISSING. Message: {entry_message}")


    def _determine_status_and_integrity(self, job: ExpectedBackupJob, staged_db_file_path: str, agent_report_data: dict, now_utc: datetime) -> tuple[str, int, BackupEntryStatus, str, bool]:
        """
        Détermine le statut de l'entrée de sauvegarde en effectuant les vérifications d'intégrité.
        Retourne le hash/size calculé par le serveur, le statut de l'entrée, le message, et le résultat de comparaison de hash.
        """
        entry_status = BackupEntryStatus.FAILED # Statut par défaut si des problèmes sont détectés
        entry_message = "Échec non spécifié."
        server_calculated_hash = None
        server_calculated_size = None
        hash_comparison_result = None

        backup_status_agent = agent_report_data.get("backup_process", {}).get("status", False)
        compress_status_agent = agent_report_data.get("compress_process", {}).get("status", False)
        transfer_status_agent = agent_report_data.get("transfer_process", {}).get("status", False)

        # Logique des statuts par ordre de priorité inverse de détection des problèmes
        # 1. Échec rapporté par l'agent sur les processus internes (dump, compression)
        if not backup_status_agent or not compress_status_agent:
            entry_status = BackupEntryStatus.FAILED
            entry_message = (f"Agent a rapporté un échec dans le processus de backup ou de compression "
                             f"pour {job.database_name}. Détails : {agent_report_data.get('logs_summary', 'N/A')}")
            logger.warning(entry_message)
            return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result

        # 2. Échec de transfert rapporté par l'agent
        if not transfer_status_agent:
            entry_status = BackupEntryStatus.FAILED
            entry_message = f"Agent a rapporté un échec de transfert pour {job.database_name}. Message: {agent_report_data.get('transfer_process', {}).get('error_message', 'Aucun message.')}"
            logger.warning(entry_message)
            return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result

        # 3. Transfert signalé OK par agent, mais vérification d'intégrité côté serveur échoue
        # Le fichier stagé doit exister pour cette vérification.
        if not os.path.exists(staged_db_file_path):
            # C'est un MISSING spécifique ici: l'agent a dit que le transfert était OK, mais le fichier n'est pas là.
            entry_status = BackupEntryStatus.MISSING 
            entry_message = f"Fichier stagé attendu non trouvé pour {job.database_name} à {staged_db_file_path}, malgré le rapport de succès de l'agent."
            logger.error(entry_message)
            return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result

        try:
            server_calculated_hash = calculate_file_sha256(staged_db_file_path)
            server_calculated_size = os.path.getsize(staged_db_file_path)

            agent_reported_hash_post_compress = agent_report_data.get("compress_process", {}).get("sha256_checksum")
            agent_reported_size_post_compress = agent_report_data.get("compress_process", {}).get("size_bytes")

            if server_calculated_hash != agent_reported_hash_post_compress or \
               server_calculated_size != agent_reported_size_post_compress:
                entry_status = BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
                entry_message = (f"Échec de l'intégrité du transfert pour {job.database_name}. "
                                 f"Agent (hash/size): {agent_reported_hash_post_compress}/{agent_reported_size_post_compress}, "
                                 f"Serveur (hash/size): {server_calculated_hash}/{server_calculated_size}.")
                logger.error(entry_message)
                return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result
            
            logger.info(f"Intégrité du transfert vérifiée et correcte pour {job.database_name}.")
            entry_status = BackupEntryStatus.SUCCESS # Potentiel succès à ce stade
            entry_message = "Sauvegarde transférée avec intégrité."

        except (CryptoUtilityError, FileOperationError) as e:
            entry_status = BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
            entry_message = f"Impossible de vérifier le fichier stagé pour {job.database_name}: {e}. Intégrité non confirmée."
            logger.error(entry_message)
            return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result
        except Exception as e:
            entry_status = BackupEntryStatus.TRANSFER_INTEGRITY_FAILED # Capture d'autres erreurs inattendues de lecture fichier
            entry_message = f"Erreur inattendue lors de la vérification fichier stagé pour {job.database_name}: {e}. Intégrité non confirmée."
            logger.critical(entry_message, exc_info=True)
            return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result

        # 4. HASH_MISMATCH (si tout le reste est OK jusqu'ici)
        if job.previous_successful_hash_global and server_calculated_hash == job.previous_successful_hash_global:
            entry_status = BackupEntryStatus.HASH_MISMATCH
            entry_message = f"Hachage de la sauvegarde pour {job.database_name} identique au précédent succès. BD potentiellement inchangée."
            hash_comparison_result = False # Hachage identique
            logger.warning(entry_message)
        else:
            hash_comparison_result = True # Hachage différent (indique un changement ou premier succès)

        return server_calculated_hash, server_calculated_size, entry_status, entry_message, hash_comparison_result


    def _save_backup_entry_and_update_job(
        self,
        job: ExpectedBackupJob,
        entry_status: BackupEntryStatus,
        entry_message: str,
        now_utc: datetime,
        overall_status_data: dict,
        agent_report_data: dict,
        server_calculated_staged_hash: str,
        server_calculated_staged_size: int,
        hash_comparison_result: bool
    ):
        """
        Crée une nouvelle entrée d'historique de sauvegarde et met à jour le job attendu.
        """
        # Informations du rapport STATUS.json (si disponible)
        status_file_name_for_entry = os.path.basename(overall_status_data.get("status_file_path")) if overall_status_data and overall_status_data.get("status_file_path") else None
        overall_agent_id = overall_status_data.get("agent_id") if overall_status_data and overall_status_data.get("agent_id") else job.agent_id_responsible # Préfère celui du rapport si présent

        # Créer une nouvelle entrée dans l'historique
        new_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=now_utc,
            status=entry_status,
            message=entry_message,
            
            operation_log_file_name=status_file_name_for_entry,
            agent_id=overall_agent_id,
            agent_overall_status=overall_status_data.get("overall_status") if overall_status_data else None,
            
            # Remplir les détails du rapport agent si disponibles
            agent_backup_process_status=agent_report_data.get("backup_process", {}).get("status") if agent_report_data else None,
            agent_backup_process_start_time=parse_iso_datetime(agent_report_data["backup_process"]["backup_process_start_time"]) if agent_report_data and agent_report_data.get("backup_process",{}).get("backup_process_start_time") else None,
            agent_backup_process_timestamp=parse_iso_datetime(agent_report_data["backup_process"]["timestamp"]) if agent_report_data and agent_report_data.get("backup_process",{}).get("timestamp") else None,
            agent_backup_hash_pre_compress=agent_report_data.get("backup_process", {}).get("sha256_checksum") if agent_report_data else None,
            agent_backup_size_pre_compress=agent_report_data.get("backup_process", {}).get("size_bytes") if agent_report_data else None,

            agent_compress_process_status=agent_report_data.get("compress_process", {}).get("status") if agent_report_data else None,
            agent_compress_process_start_time=parse_iso_datetime(agent_report_data["compress_process"]["compress_process_start_time"]) if agent_report_data and agent_report_data.get("compress_process",{}).get("compress_process_start_time") else None,
            agent_compress_process_timestamp=parse_iso_datetime(agent_report_data["compress_process"]["timestamp"]) if agent_report_data and agent_report_data.get("compress_process",{}).get("timestamp") else None,
            agent_compress_hash_post_compress=agent_report_data.get("compress_process", {}).get("sha256_checksum") if agent_report_data else None,
            agent_compress_size_post_compress=agent_report_data.get("compress_process", {}).get("size_bytes") if agent_report_data else None,

            agent_transfer_process_status=agent_report_data.get("transfer_process", {}).get("status") if agent_report_data else None,
            agent_transfer_process_start_time=parse_iso_datetime(agent_report_data["transfer_process"]["transfer_process_start_time"]) if agent_report_data and agent_report_data.get("transfer_process",{}).get("transfer_process_start_time") else None,
            agent_transfer_process_timestamp=parse_iso_datetime(agent_report_data["transfer_process"]["timestamp"]) if agent_report_data and agent_report_data.get("transfer_process",{}).get("timestamp") else None,
            agent_transfer_error_message=agent_report_data.get("transfer_process", {}).get("error_message") if agent_report_data else None,
            agent_staged_file_name=agent_report_data.get("staged_file_name") if agent_report_data else None,
            agent_logs_summary=agent_report_data.get("logs_summary") if agent_report_data else None,
            
            # Détails calculés par le serveur
            server_calculated_staged_hash=server_calculated_staged_hash,
            server_calculated_staged_size=server_calculated_staged_size,
            previous_successful_hash_global=job.previous_successful_hash_global, # Le hash qui a été comparé
            hash_comparison_result=hash_comparison_result # Le résultat de la comparaison
        )
        self.db.add(new_entry)

        # Mapping explicite entre BackupEntryStatus et JobStatus
        status_map = {
            BackupEntryStatus.SUCCESS: JobStatus.OK,
            BackupEntryStatus.FAILED: JobStatus.FAILED,
            BackupEntryStatus.MISSING: JobStatus.MISSING,
            BackupEntryStatus.HASH_MISMATCH: JobStatus.HASH_MISMATCH,
            BackupEntryStatus.TRANSFER_INTEGRITY_FAILED: JobStatus.TRANSFER_INTEGRITY_FAILED,
        }
        job.current_status = status_map.get(entry_status, JobStatus.UNKNOWN)
        job.last_checked_timestamp = now_utc
        
        # Mettre à jour le dernier hash réussi et timestamp uniquement si la sauvegarde est un succès réel.
        # Un HASH_MISMATCH n'est pas un nouveau succès en termes de contenu, donc on ne met pas à jour le previous_successful_hash_global
        if entry_status == BackupEntryStatus.SUCCESS:
            job.last_successful_backup_timestamp = now_utc 
            job.previous_successful_hash_global = server_calculated_staged_hash # Le dernier hash calculé par le serveur

        self.db.commit()
        self.db.refresh(job) # Recharge l'objet job pour les prochaines utilisations dans le même scan
        logger.info(f"Statut du job {job.database_name} mis à jour en DB : {getattr(job.current_status, 'value', job.current_status)}")

    def _perform_post_scan_actions(self, job: ExpectedBackupJob, entry_status: BackupEntryStatus, staged_db_file_path: str):
        """
        Déclenche les actions post-scan comme la promotion du fichier et la notification.
        Ces services seront appelés ici.
        """
        from app.services.backup_manager import promote_backup, BackupManagerError
        # from app.services.notifier import send_alert_email # À décommenter quand notifier est implémenté

        if entry_status == BackupEntryStatus.SUCCESS:
            logger.info(f"Sauvegarde pour {job.database_name} est SUCCESS. Tentative de promotion du fichier.")
            try:
                promoted_path = promote_backup(staged_db_file_path, job)
                logger.info(f"Fichier de sauvegarde promu avec succès à : {promoted_path}")
                # Le fichier stagé n'est plus supprimé ici, il reste en place pour les synchronisations futures
            except BackupManagerError as e:
                logger.error(f"Échec de la promotion du fichier pour {job.database_name}: {e}")
                # On pourrait vouloir changer le job.current_status en un nouveau statut 'PROMOTION_FAILED'
                # ou envoyer une notification urgente ici, même si l'entrée est SUCCESS.
        elif entry_status in [BackupEntryStatus.FAILED, BackupEntryStatus.MISSING, BackupEntryStatus.TRANSFER_INTEGRITY_FAILED, BackupEntryStatus.HASH_MISMATCH]:
            logger.warning(f"Alerte pour {job.database_name}: {entry_status.value}. Notification requise (implémentation future).")
            # Envoyer la notification ici
            # try:
            #     send_alert_email(job.notification_recipients, f"Alerte Sauvegarde {job.database_name}: {entry_status.value}", entry_message)
            # except Exception as e:
            #     logger.error(f"Échec de l'envoi de notification pour {job.database_name}: {e}")
        else:
            logger.debug(f"Aucune action post-scan spécifique pour le statut {entry_status.value} du job {job.database_name}.")

    def _archive_status_file(self, source_path: str, archive_dir: str):
        """
        Déplace un fichier STATUS.json vers un répertoire d'archive après traitement.
        """
        try:
            dest_path = os.path.join(archive_dir, os.path.basename(source_path))
            move_file(source_path, dest_path)
            logger.info(f"Fichier STATUS.json archivé : {source_path} -> {dest_path}")
        except FileOperationError as e:
            logger.error(f"Impossible d'archiver le fichier STATUS.json '{source_path}': {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'archivage du STATUS.json '{source_path}': {e}", exc_info=True)


# Fonction d'entrée pour le scheduler (si non encapsulée dans une classe plus grande)
# C'est cette fonction qui sera appelée par APScheduler.
def run_scanner(db_session: Session):
    """
    Fonction wrapper pour exécuter le scanner, destinée à être appelée par APScheduler.
    """
    scanner = BackupScanner(db_session)
    scanner.scan_all_jobs()
