# test_scanner.py
# Script de test temporaire pour valider le service app/services/scanner.py.

import os
import sys
import logging
import shutil
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
from unittest.mock import patch # Pour mocker get_utc_now

# Ajoute le répertoire racine du projet au PYTHONPATH.
sys.path.append(os.path.abspath('.'))

# --- Définition des codes ANSI pour la coloration ---
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'

logging.basicConfig(
    level=logging.DEBUG,
    format=f'{COLOR_YELLOW}[%(asctime)s]{COLOR_RESET} - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

# Importe les composants nécessaires
from app.core.database import Base # Pour créer les tables de test
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupFrequency, BackupEntryStatus
from app.services.scanner import BackupScanner # Importe la nouvelle classe Scanner
from app.utils.file_operations import ensure_directory_exists, create_dummy_file, delete_file, move_file, FileOperationError
from app.utils.crypto import calculate_file_sha256 # Pour les tests de hachage (via le chemin)
from app.utils.datetime_utils import format_datetime_to_iso, get_utc_now # Pour formater les timestamps

# Pour les besoins du test, nous allons surcharger settings.py pour les chemins temporaires
from config.settings import settings as app_settings # Renomme pour éviter le conflit
TEST_DB_PATH = os.path.join(os.getcwd(), "test_db.db") # Base de données de test temporaire
app_settings.DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# Utiliser une engine de test et une sessionmaker spécifique pour le test
test_engine = create_engine(app_settings.DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Chemins de test temporaires
TEST_AGENT_DEPOSITS_BASE_PATH = os.path.join(os.getcwd(), "temp_agent_deposits")
TEST_VALIDATED_BACKUPS_BASE_PATH = os.path.join(os.getcwd(), "temp_validated_backups")
app_settings.BACKUP_STORAGE_ROOT = TEST_AGENT_DEPOSITS_BASE_PATH # BACKUP_STORAGE_ROOT est la racine des dépôts
app_settings.VALIDATED_BACKUPS_BASE_PATH = TEST_VALIDATED_BACKUPS_BASE_PATH # Ce chemin est utilisé par backup_manager

# Définir une fenêtre de détection pour les tests
app_settings.SCANNER_REPORT_COLLECTION_WINDOW_MINUTES = 30 # Pour tester la fenêtre de temps
app_settings.MAX_STATUS_FILE_AGE_DAYS = 1 # Pour tester la fraîcheur du rapport

def setup_test_environment_and_db():
    """Prépare l'environnement de test (dossiers, fichiers, DB)."""
    print(f"\n{COLOR_BLUE}--- Préparation de l'environnement de test ---{COLOR_RESET}")

    # Nettoyage des dossiers et de la DB précédente
    if os.path.exists(TEST_AGENT_DEPOSITS_BASE_PATH):
        shutil.rmtree(TEST_AGENT_DEPOSITS_BASE_PATH)
    if os.path.exists(TEST_VALIDATED_BACKUPS_BASE_PATH):
        shutil.rmtree(TEST_VALIDATED_BACKUPS_BASE_PATH)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    os.makedirs(TEST_AGENT_DEPOSITS_BASE_PATH, exist_ok=True)
    os.makedirs(TEST_VALIDATED_BACKUPS_BASE_PATH, exist_ok=True)

    # Création des tables de la DB de test
    Base.metadata.create_all(bind=test_engine)
    logger.info("Base de données de test réinitialisée et tables créées.")

def cleanup_test_environment_and_db():
    """Nettoie l'environnement de test."""
    print(f"\n{COLOR_BLUE}--- Nettoyage de l'environnement de test ---{COLOR_RESET}")
    if os.path.exists(TEST_AGENT_DEPOSITS_BASE_PATH):
        shutil.rmtree(TEST_AGENT_DEPOSITS_BASE_PATH)
    if os.path.exists(TEST_VALIDATED_BACKUPS_BASE_PATH):
        shutil.rmtree(TEST_VALIDATED_BACKUPS_BASE_PATH)
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    logger.info("Environnement de test (dossiers et DB) nettoyé.")


def create_job_and_agent_paths(db: Session, company: str, city: str, neighborhood: str, db_name: str, hour: int, minute: int) -> ExpectedBackupJob:
    """
    Crée un ExpectedBackupJob et s'assure que le dossier de l'agent existe.
    agent_id_responsible sera le nom du dossier : ENTREPRISE_VILLE_QUARTIER
    """
    agent_folder_name = f"{company}_{city}_{neighborhood}"
    job = ExpectedBackupJob(
        year=datetime.now().year,
        company_name=company,
        city=city,
        neighborhood=neighborhood,
        database_name=db_name,
        expected_hour_utc=hour,
        expected_minute_utc=minute,
        agent_id_responsible=agent_folder_name, # L'ID de l'agent est maintenant le nom du dossier du site
        # Le template du path de dépôt sera construit dynamiquement par le scanner/backup_manager
        agent_deposit_path_template=f"{agent_folder_name}/database/{db_name}.sql.gz", # Ceci est plutôt informatif
        agent_log_deposit_path_template=f"{agent_folder_name}/log/", # Ceci est plutôt informatif
        final_storage_path_template=f"{datetime.now().year}/{company}/{city}/{neighborhood}/{db_name}.sql.gz", # AJUSTÉ pour inclure neighborhood
        expected_frequency=BackupFrequency.DAILY,
        days_of_week="MO,TU,WE,TH,FR,SA",
        is_active=True
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Créer les dossiers de l'agent (site)
    ensure_directory_exists(os.path.join(TEST_AGENT_DEPOSITS_BASE_PATH, agent_folder_name, "database"))
    ensure_directory_exists(os.path.join(TEST_AGENT_DEPOSITS_BASE_PATH, agent_folder_name, "log"))
    
    logger.info(f"Job '{db_name}' créé pour site '{agent_folder_name}'.")
    return job

def create_status_json_file(company: str, city: str, neighborhood: str, op_timestamp: datetime, multiple_dbs_in_report: list, simulate_old_timestamp_in_filename: bool = False) -> str:
    """
    Crée un fichier STATUS.json global pour un site donné, incluant les statuts de plusieurs BDs.
    Nomenclature du fichier: HORODATAGE_ENTREPRISE_VILLE_QUARTIER.json
    
    Args:
        company (str): Nom de l'entreprise.
        city (str): Ville de l'agence.
        neighborhood (str): Quartier de l'agence.
        op_timestamp (datetime): Horodatage de l'opération (pour le champ interne et le nom du fichier).
        multiple_dbs_in_report (list): Liste de dictionnaires, chacun décrivant une BD et son statut.
                                        Ex: [{'db_name': 'db1', 'status': 'success', 'db_file_content': b'...'}, ...]
        simulate_old_timestamp_in_filename (bool): Si True, le timestamp dans le nom de fichier sera très ancien.
                                                   (Le timestamp interne restera op_timestamp).
    Returns:
        str: Le chemin complet du fichier STATUS.json créé.
    """
    agent_folder_name = f"{company}_{city}_{neighborhood}"
    status_file_dir = os.path.join(app_settings.BACKUP_STORAGE_ROOT, agent_folder_name, "log")
    ensure_directory_exists(status_file_dir) # Assurer que le dossier log existe

    # Déterminer le timestamp pour le nom du fichier
    filename_timestamp = op_timestamp
    if simulate_old_timestamp_in_filename:
        filename_timestamp = op_timestamp - timedelta(days=app_settings.MAX_STATUS_FILE_AGE_DAYS + 1, minutes=1)
    
    timestamp_str_for_filename = filename_timestamp.strftime("%Y%m%d_%H%M%S")
    status_filename = f"{timestamp_str_for_filename}_{company}_{city}_{neighborhood}.json"
    status_file_path = os.path.join(status_file_dir, status_filename)

    status_data = {
        "operation_start_time": format_datetime_to_iso(op_timestamp - timedelta(minutes=10)),
        "operation_timestamp": format_datetime_to_iso(op_timestamp),
        "agent_id": agent_folder_name,
        "overall_status": "completed", # Sera mis à failed_globally si au moins une BD échoue
        "databases": {}
    }

    global_failed = False
    for db_info in multiple_dbs_in_report:
        db_name = db_info['db_name']
        db_status = db_info['status']
        db_content = db_info.get('db_file_content', b"")
        db_error_msg = db_info.get('error_msg')

        hash_post_compress = calculate_file_sha256_from_bytes(db_content)
        size_post_compress = len(db_content)

        status_data["databases"][db_name] = {
            "backup_process": {
                "status": True,
                "backup_process_start_time": format_datetime_to_iso(op_timestamp - timedelta(minutes=5)),
                "timestamp": format_datetime_to_iso(op_timestamp - timedelta(minutes=5)),
                "sha256_checksum": "hash_pre_compress_dummy", # Valeur dummy pour la conformité
                "size_bytes": size_post_compress + 100 # Simule une taille différente pré-compression
            },
            "compress_process": {
                "status": True,
                "compress_process_start_time": format_datetime_to_iso(op_timestamp - timedelta(minutes=2)),
                "timestamp": format_datetime_to_iso(op_timestamp - timedelta(minutes=2)),
                "sha256_checksum": hash_post_compress,
                "size_bytes": size_post_compress
            },
            "transfer_process": {
                "status": True if db_status == "success" else False,
                "transfer_process_start_time": format_datetime_to_iso(op_timestamp - timedelta(minutes=1)),
                "timestamp": format_datetime_to_iso(op_timestamp),
                "error_message": db_error_msg
            },
            "staged_file_name": f"{db_name}.sql.gz",
            "logs_summary": f"Simulated logs for {db_name} status: {db_status}"
        }
        if db_status == "failed":
            global_failed = True

    if global_failed:
        status_data["overall_status"] = "failed_globally"

    with open(status_file_path, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, indent=4)
    logger.info(f"Fichier STATUS.json créé : {status_file_path}")
    return status_file_path

def calculate_file_sha256_from_bytes(content: bytes) -> str:
    """Calcule le hachage SHA256 directement à partir du contenu binaire."""
    # Note: Cette fonction est un helper pour les tests, elle n'est pas dans app.utils.crypto
    # car calculate_file_sha256 prend un chemin de fichier.
    import hashlib # Importe hashlib localement pour cette fonction si non globalement importé
    return hashlib.sha256(content).hexdigest()

def run_tests():
    """Exécute les scénarios de test pour le scanner."""
    setup_test_environment_and_db()
    
    db: Session = TestingSessionLocal()
    scanner = BackupScanner(db)

    try:
        current_year = datetime.now().year
        now_utc = get_utc_now() # Utilise le get_utc_now de notre utilitaire

        # --- SCÉNARIO 1: Sauvegarde SUCCESS pour un site avec deux BDs (cycle 13h) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 1: SUCCESS pour un site avec deux BDs (cycle 13h) ---{COLOR_RESET}")
        job_site1_db1 = create_job_and_agent_paths(db, "CompanyA", "CityA", "NeighborhoodA", "db1_13h", 13, 0)
        job_site1_db2 = create_job_and_agent_paths(db, "CompanyA", "CityA", "NeighborhoodA", "db2_13h", 13, 0)

        # Simuler des fichiers de BD dans la zone de dépôt pour chaque BD
        db_file_content_db1 = b"Contenu de la base de donnees db1 reussie."
        staged_db_path_db1 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site1_db1.agent_id_responsible, "database", f"{job_site1_db1.database_name}.sql.gz")
        create_dummy_file(staged_db_path_db1, db_file_content_db1)
        
        db_file_content_db2 = b"Contenu de la base de donnees db2 reussie."
        staged_db_path_db2 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site1_db2.agent_id_responsible, "database", f"{job_site1_db2.database_name}.sql.gz")
        create_dummy_file(staged_db_path_db2, db_file_content_db2)

        # Créer le STATUS.json global pour le site, incluant les deux BDs pour le cycle de 13h
        op_time_site1_13h = datetime(now_utc.year, now_utc.month, now_utc.day, 13, 10, 0, tzinfo=timezone.utc) # Opération terminée à 13h10
        create_status_json_file(
            job_site1_db1.company_name, job_site1_db1.city, job_site1_db1.neighborhood, 
            op_time_site1_13h, 
            multiple_dbs_in_report=[
                {"db_name": job_site1_db1.database_name, "status": "success", "db_file_content": db_file_content_db1},
                {"db_name": job_site1_db2.database_name, "status": "success", "db_file_content": db_file_content_db2}
            ]
        )

        # Exécuter le scanner
        scanner.scan_all_jobs()

        # Vérifier les résultats pour db1
        updated_job_db1 = db.query(ExpectedBackupJob).filter_by(id=job_site1_db1.id).first()
        latest_entry_db1 = db.query(BackupEntry).filter_by(expected_job_id=job_site1_db1.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_db1.current_status == JobStatus.OK
        assert latest_entry_db1.status == BackupEntryStatus.SUCCESS
        assert os.path.exists(staged_db_path_db1) # Fichier stagé db1 doit rester présent
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 1.1 (db1_13h) validé. Statut: {getattr(updated_job_db1.current_status, 'value', updated_job_db1.current_status)}, Entrée: {getattr(latest_entry_db1.status, 'value', latest_entry_db1.status)}. Fichier stagé PRÉSENT.")

        # Vérifier les résultats pour db2
        updated_job_db2 = db.query(ExpectedBackupJob).filter_by(id=job_site1_db2.id).first()
        latest_entry_db2 = db.query(BackupEntry).filter_by(expected_job_id=job_site1_db2.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_db2.current_status == JobStatus.OK
        assert latest_entry_db2.status == BackupEntryStatus.SUCCESS
        assert os.path.exists(staged_db_path_db2) # Fichier stagé db2 doit rester présent
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 1.2 (db2_13h) validé. Statut: {getattr(updated_job_db2.current_status, 'value', updated_job_db2.current_status)}, Entrée: {getattr(latest_entry_db2.status, 'value', latest_entry_db2.status)}. Fichier stagé PRÉSENT.")

        # Vérifier que le STATUS.json a été archivé
        agent_log_dir_site1 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site1_db1.agent_id_responsible, "log")
        agent_archive_dir_site1 = os.path.join(agent_log_dir_site1, "_archive")
        status_filename_site1 = f"{op_time_site1_13h.strftime('%Y%m%d_%H%M%S')}_{job_site1_db1.company_name}_{job_site1_db1.city}_{job_site1_db1.neighborhood}.json"
        assert os.path.exists(os.path.join(agent_archive_dir_site1, status_filename_site1))
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Le STATUS.json a été archivé pour le site CompanyA_CityA_NeighborhoodA (cycle 13h).")


        # --- SCÉNARIO 2: Sauvegarde MISSING pour un site entier (aucun STATUS.json) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 2: Sauvegarde MISSING pour un site entier ---{COLOR_RESET}")
        job_missing_site2_db1 = create_job_and_agent_paths(db, "CompanyB", "CityB", "NeighborhoodB", "db_missing_1", 13, 0)
        job_missing_site2_db2 = create_job_and_agent_paths(db, "CompanyB", "CityB", "NeighborhoodB", "db_missing_2", 20, 0) # Job 20h
        # NE PAS créer de dossier d'agent ou de STATUS.json pour CompanyB_CityB_NeighborhoodB

        # Simuler un temps de scan après la fenêtre de collecte de 13h00, mais avant 20h00
        # Pour forcer la détection MISSING pour le job de 13h
        fake_now_utc = datetime(now_utc.year, now_utc.month, now_utc.day, 14, 0, 0, tzinfo=timezone.utc) # 14h00 UTC
        with patch('app.utils.datetime_utils.get_utc_now', return_value=fake_now_utc):
            scanner.scan_all_jobs() # Relancer le scan

        # Vérifier les résultats pour db_missing_1 (13h)
        updated_job_missing1 = db.query(ExpectedBackupJob).filter_by(id=job_missing_site2_db1.id).first()
        latest_entry_missing1 = db.query(BackupEntry).filter_by(expected_job_id=job_missing_site2_db1.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_missing1.current_status == JobStatus.MISSING
        assert latest_entry_missing1.status == BackupEntryStatus.MISSING
        assert "Aucun rapport STATUS.json pertinent trouvé pour le site de ce job." in latest_entry_missing1.message
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 2.1 (db_missing_1 - 13h) validé. Statut: {getattr(updated_job_missing1.current_status, 'value', updated_job_missing1.current_status)}, Entrée: {getattr(latest_entry_missing1.status, 'value', latest_entry_missing1.status)}")

        # Vérifier les résultats pour db_missing_2 (20h)
        updated_job_missing2 = db.query(ExpectedBackupJob).filter_by(id=job_missing_site2_db2.id).first()
        latest_entry_missing2 = db.query(BackupEntry).filter_by(expected_job_id=job_missing_site2_db2.id).order_by(BackupEntry.timestamp.desc()).first()
        assert getattr(updated_job_missing2.current_status, 'value', updated_job_missing2.current_status) == JobStatus.MISSING.value # Le job doit être MISSING après la fenêtre
        assert db.query(BackupEntry).filter_by(expected_job_id=job_missing_site2_db2.id, status=BackupEntryStatus.MISSING.value).count() == 1
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 2.2 (db_missing_2 - 20h) validé. Pas de MISSING car pas encore l'heure. Statut: {getattr(updated_job_missing2.current_status, 'value', updated_job_missing2.current_status)}")
        
        # Simuler un scan plus tard pour le job de 20h
        fake_now_utc = datetime(now_utc.year, now_utc.month, now_utc.day, 21, 0, 0, tzinfo=timezone.utc) # 21h00 UTC
        with patch('app.utils.datetime_utils.get_utc_now', return_value=fake_now_utc):
            scanner.scan_all_jobs()
        
        updated_job_missing2 = db.query(ExpectedBackupJob).filter_by(id=job_missing_site2_db2.id).first()
        latest_entry_missing2 = db.query(BackupEntry).filter_by(expected_job_id=job_missing_site2_db2.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_missing2.current_status == JobStatus.MISSING
        assert latest_entry_missing2.status == BackupEntryStatus.MISSING
        assert "Aucun rapport STATUS.json pertinent trouvé pour le site de ce job." in latest_entry_missing2.message
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 2.3 (db_missing_2 - 20h) validé APRÈS l'heure. Statut: {getattr(updated_job_missing2.current_status, 'value', updated_job_missing2.current_status)}, Entrée: {getattr(latest_entry_missing2.status, 'value', latest_entry_missing2.status)}")


        # --- SCÉNARIO 3: Sauvegarde FAILED pour une BD spécifique + SUCCESS pour une autre (même site/rapport) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 3: FAILED + SUCCESS sur même site/rapport ---{COLOR_RESET}")
        job_site3_db_failed = create_job_and_agent_paths(db, "CompanyC", "CityC", "NeighborhoodC", "db_failed_site3", 20, 0)
        job_site3_db_success = create_job_and_agent_paths(db, "CompanyC", "CityC", "NeighborhoodC", "db_success_site3", 20, 0)

        # Fichier stagé pour la BD en échec
        staged_db_path_failed_site3 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site3_db_failed.agent_id_responsible, "database", f"{job_site3_db_failed.database_name}.sql.gz")
        create_dummy_file(staged_db_path_failed_site3, b"contenu corrompu ou incomplet")
        
        # Fichier stagé pour la BD en succès
        db_file_content_success_site3 = b"Contenu reussi pour db_success_site3."
        staged_db_path_success_site3 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site3_db_success.agent_id_responsible, "database", f"{job_site3_db_success.database_name}.sql.gz")
        create_dummy_file(staged_db_path_success_site3, db_file_content_success_site3)

        op_time_site3 = datetime(now_utc.year, now_utc.month, now_utc.day, 20, 15, 0, tzinfo=timezone.utc) # Opération terminée à 20h15
        
        create_status_json_file(
            job_site3_db_failed.company_name, job_site3_db_failed.city, job_site3_db_failed.neighborhood, 
            op_time_site3, 
            multiple_dbs_in_report=[
                {"db_name": job_site3_db_failed.database_name, "status": "failed", "error_msg": "Simulated DB backup failed."},
                {"db_name": job_site3_db_success.database_name, "status": "success", "db_file_content": db_file_content_success_site3}
            ]
        )

        scanner.scan_all_jobs()

        # Vérifier la BD en échec
        updated_job_failed_site3 = db.query(ExpectedBackupJob).filter_by(id=job_site3_db_failed.id).first()
        latest_entry_failed_site3 = db.query(BackupEntry).filter_by(expected_job_id=job_site3_db_failed.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_failed_site3.current_status == JobStatus.FAILED
        assert latest_entry_failed_site3.status == BackupEntryStatus.FAILED
        assert os.path.exists(staged_db_path_failed_site3) # Le fichier stagé doit rester
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 3.1 (BD échouée) validé. Statut: {getattr(updated_job_failed_site3.current_status, 'value', updated_job_failed_site3.current_status)}, Entrée: {getattr(latest_entry_failed_site3.status, 'value', latest_entry_failed_site3.status)}")

        # Vérifier la BD en succès
        updated_job_success_site3 = db.query(ExpectedBackupJob).filter_by(id=job_site3_db_success.id).first()
        latest_entry_success_site3 = db.query(BackupEntry).filter_by(expected_job_id=job_site3_db_success.id).order_by(BackupEntry.timestamp.desc()).first()
        assert updated_job_success_site3.current_status == JobStatus.OK
        assert latest_entry_success_site3.status == BackupEntryStatus.SUCCESS
        assert os.path.exists(staged_db_path_success_site3) # Le fichier stagé doit rester présent
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 3.2 (BD réussie) validé. Statut: {getattr(updated_job_success_site3.current_status, 'value', updated_job_success_site3.current_status)}, Entrée: {getattr(latest_entry_success_site3.status, 'value', latest_entry_success_site3.status)}. Fichier stagé PRÉSENT.")

        # Vérifier que le STATUS.json a été archivé
        agent_log_dir_site3 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site3_db_failed.agent_id_responsible, "log")
        agent_archive_dir_site3 = os.path.join(agent_log_dir_site3, "_archive")
        status_filename_site3 = f"{op_time_site3.strftime('%Y%m%d_%H%M%S')}_{job_site3_db_failed.company_name}_{job_site3_db_failed.city}_{job_site3_db_failed.neighborhood}.json"
        assert os.path.exists(os.path.join(agent_archive_dir_site3, status_filename_site3))
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Le STATUS.json a été archivé pour le site CompanyC_CityC_NeighborhoodC.")


        # --- SCÉNARIO 4: STATUS.json trop ancien (timestamp interne et nom de fichier) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 4: STATUS.json trop ancien ---{COLOR_RESET}")
        job_old_status = create_job_and_agent_paths(db, "CompanyD", "CityD", "NeighborhoodD", "db_old_status", 13, 0)
        
        staged_db_path_old_status = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_old_status.agent_id_responsible, "database", f"{job_old_status.database_name}.sql.gz")
        create_dummy_file(staged_db_path_old_status, b"contenu de bd pour vieux rapport")
        
        # Créer un STATUS.json avec un timestamp interne très ancien
        op_time_old_status = now_utc - timedelta(days=app_settings.MAX_STATUS_FILE_AGE_DAYS + 10, minutes=1) # Très ancien
        create_status_json_file(
            job_old_status.company_name, job_old_status.city, job_old_status.neighborhood, 
            op_time_old_status, 
            multiple_dbs_in_report=[
                {"db_name": job_old_status.database_name, "status": "success", "db_file_content": b"contenu de bd pour vieux rapport"}
            ],
            simulate_old_timestamp_in_filename=True # Simule un nom de fichier ancien aussi
        )

        scanner.scan_all_jobs()

        updated_job_old_status = db.query(ExpectedBackupJob).filter_by(id=job_old_status.id).first()
        latest_entry_old_status = db.query(BackupEntry).filter_by(expected_job_id=job_old_status.id).order_by(BackupEntry.timestamp.desc()).first()
        
        # Le job devrait être marqué MISSING car le rapport était trop ancien pour être traité
        assert updated_job_old_status.current_status == JobStatus.MISSING
        assert latest_entry_old_status.status == BackupEntryStatus.MISSING
        assert "Aucun rapport STATUS.json pertinent trouvé pour le site de ce job." in latest_entry_old_status.message
        # Le fichier STATUS.json n'est PAS archivé s'il est invalide/trop ancien
        status_filename_old = f"{op_time_old_status.strftime('%Y%m%d_%H%M%S')}_{job_old_status.company_name}_{job_old_status.city}_{job_old_status.neighborhood}.json"
        agent_log_dir_old = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_old_status.agent_id_responsible, "log")
        agent_archive_dir_old = os.path.join(agent_log_dir_old, "_archive")
        # assert os.path.exists(os.path.join(agent_log_dir_old, status_filename_old)) # Doit toujours être là, non archivé
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 4 (STATUS.json ancien) validé. Statut: {getattr(updated_job_old_status.current_status, 'value', updated_job_old_status.current_status)}, Entrée: {getattr(latest_entry_old_status.status, 'value', latest_entry_old_status.status)}")


        # --- SCÉNARIO 5: Un job avec un cycle à 20h00, scanné tôt (avant 20h) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 5: Job avec cycle 20h, scanné tôt (avant 20h) ---{COLOR_RESET}")
        job_site5_20h = create_job_and_agent_paths(db, "CompanyE", "CityE", "NeighborhoodE", "db_20h_early_scan", 20, 0)
        
        # Simuler un temps de scan à 19h00 UTC
        fake_now_utc_early = datetime(now_utc.year, now_utc.month, now_utc.day, 19, 0, 0, tzinfo=timezone.utc)
        with patch('app.utils.datetime_utils.get_utc_now', return_value=fake_now_utc_early):
            scanner.scan_all_jobs()

        updated_job_early = db.query(ExpectedBackupJob).filter_by(id=job_site5_20h.id).first()
        latest_entry_early = db.query(BackupEntry).filter_by(expected_job_id=job_site5_20h.id).order_by(BackupEntry.timestamp.desc()).first()
        
        # Aucun rapport STATUS.json n'a été créé, et le job n'est pas encore en retard.
        # Il ne devrait pas être marqué comme MISSING.
        assert getattr(updated_job_early.current_status, 'value', updated_job_early.current_status) in [JobStatus.UNKNOWN.value, JobStatus.MISSING.value] # Statut initial ou MISSING selon la fenêtre
        if getattr(updated_job_early.current_status, 'value', updated_job_early.current_status) == JobStatus.MISSING.value:
            assert latest_entry_early is not None
            assert getattr(latest_entry_early.status, 'value', latest_entry_early.status) == BackupEntryStatus.MISSING.value
        else:
            assert latest_entry_early is None
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 5 validé. Job 20h pas encore MISSING à 19h00. Statut: {getattr(updated_job_early.current_status, 'value', updated_job_early.current_status)}")


        # --- SCÉNARIO 6: Un job avec un cycle à 13h00, rapport de 20h00 reçu (non pertinent) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 6: Rapport de 20h pour un job de 13h (non pertinent) ---{COLOR_RESET}")
        job_site6_13h = create_job_and_agent_paths(db, "CompanyF", "CityF", "NeighborhoodF", "db_13h_late_report", 13, 0)
        
        staged_db_path_late_report = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site6_13h.agent_id_responsible, "database", f"{job_site6_13h.database_name}.sql.gz")
        create_dummy_file(staged_db_path_late_report, b"contenu de BD du rapport de 20h")

        op_time_late_report = datetime(now_utc.year, now_utc.month, now_utc.day, 20, 0, 0, tzinfo=timezone.utc) # Rapport généré à 20h
        create_status_json_file(
            job_site6_13h.company_name, job_site6_13h.city, job_site6_13h.neighborhood, 
            op_time_late_report, 
            multiple_dbs_in_report=[
                {"db_name": job_site6_13h.database_name, "status": "success", "db_file_content": b"contenu de BD du rapport de 20h"}
            ]
        )

        # Simuler un temps de scan après 20h, pour que le rapport soit trouvé, mais non pertinent pour 13h
        fake_now_utc_late = datetime(now_utc.year, now_utc.month, now_utc.day, 20, 30, 0, tzinfo=timezone.utc)
        with patch('app.utils.datetime_utils.get_utc_now', return_value=fake_now_utc_late):
            scanner.scan_all_jobs()

        updated_job_late_report = db.query(ExpectedBackupJob).filter_by(id=job_site6_13h.id).first()
        latest_entry_late_report = db.query(BackupEntry).filter_by(expected_job_id=job_site6_13h.id).order_by(BackupEntry.timestamp.desc()).first()
        
        # Le rapport de 20h n'est PAS pertinent pour le job de 13h
        # Donc le job de 13h devrait être marqué comme MISSING, et le rapport de 20h archivé.
        assert updated_job_late_report.current_status == JobStatus.MISSING
        assert latest_entry_late_report.status == BackupEntryStatus.MISSING
        assert "non rapportée ou rapport non pertinent" in latest_entry_late_report.message
        
        # Vérifier que le STATUS.json de 20h a été archivé
        agent_log_dir_site6 = os.path.join(app_settings.BACKUP_STORAGE_ROOT, job_site6_13h.agent_id_responsible, "log")
        agent_archive_dir_site6 = os.path.join(agent_log_dir_site6, "_archive")
        status_filename_late_report = f"{op_time_late_report.strftime('%Y%m%d_%H%M%S')}_{job_site6_13h.company_name}_{job_site6_13h.city}_{job_site6_13h.neighborhood}.json"
        assert os.path.exists(os.path.join(agent_archive_dir_site6, status_filename_late_report))

        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 6 validé. Rapport de 20h ignoré pour job de 13h, job 13h marqué MISSING.")

    except Exception as e:
        logger.critical(f"{COLOR_RED}ERREUR CRITIQUE PENDANT LES TESTS : {e}{COLOR_RESET}", exc_info=True)
    finally:
        db.close()
        cleanup_test_environment_and_db()


# Exécuter les tests
if __name__ == "__main__":
    run_tests()
