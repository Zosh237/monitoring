import os
import json
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import Base, ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.services.scanner import BackupScanner
from app.utils.file_operations import ensure_directory_exists
from app.utils.crypto import calculate_file_sha256
from config.settings import settings

# Couleurs pour les logs de test
COLOR_BLUE = '\033[94m'
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_RESET = '\033[0m'

@pytest.fixture(scope="function")
def db():
    """Crée une base de données SQLite en mémoire pour les tests."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture(scope="function")
def test_env():
    """Configure l'environnement de test avec des dossiers temporaires."""
    # Créer les dossiers temporaires
    test_root = os.path.join(os.getcwd(), "test_backup_storage")
    test_log_dir = os.path.join(test_root, "log")
    test_archive_dir = os.path.join(test_log_dir, "_archive")
    
    # Sauvegarder les chemins originaux
    original_storage_root = settings.BACKUP_STORAGE_ROOT
    
    # Configurer les chemins de test
    settings.BACKUP_STORAGE_ROOT = test_root
    
    # Créer les dossiers
    ensure_directory_exists(test_root)
    ensure_directory_exists(test_log_dir)
    ensure_directory_exists(test_archive_dir)
    
    yield {
        "test_root": test_root,
        "test_log_dir": test_log_dir,
        "test_archive_dir": test_archive_dir
    }

    # Nettoyage
    if os.path.exists(test_root):
        for root, dirs, files in os.walk(test_root, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(test_root)
    
    # Restaurer les chemins originaux
    settings.BACKUP_STORAGE_ROOT = original_storage_root

def create_job_and_agent_paths(db, company_name, city, neighborhood, database_name, hour, minute):
    agent_folder = f"{company_name}_{city}_{neighborhood}"
    job = ExpectedBackupJob(
        year=datetime.now(timezone.utc).year,
        company_name=company_name,
        city=city,
        neighborhood=neighborhood,
        database_name=database_name,
        expected_hour_utc=hour,
        expected_minute_utc=minute,
        agent_id_responsible=agent_folder,
        agent_deposit_path_template="/tmp/depot/{company}/{city}/{neighborhood}/{db}",
        agent_log_deposit_path_template="/tmp/logs/{company}/{city}/{neighborhood}/",
        final_storage_path_template="/tmp/final/{company}/{city}/{neighborhood}/{db}",
        expected_frequency="daily",
        days_of_week="0,1,2,3,4,5,6",
        is_active=True,
        current_status=JobStatus.UNKNOWN
    )
    db.add(job)
    db.commit()
    agent_path = os.path.join(settings.BACKUP_STORAGE_ROOT, agent_folder)
    ensure_directory_exists(agent_path)
    return job

def create_status_json_file(company_name, city, neighborhood, operation_time, multiple_dbs_in_report=None):
    """Crée un fichier STATUS.json avec les données fournies."""
    if multiple_dbs_in_report is None:
        multiple_dbs_in_report = []
    
    # Ajout des champs obligatoires attendus par le validateur/scanner
    status_data = {
        "operation_start_time": (operation_time - timedelta(minutes=10)).isoformat(),
        "operation_end_time": operation_time.isoformat(),
        "agent_id": f"{company_name}_{city}_{neighborhood}",
        "overall_status": "completed",
        "databases": {}
    }

    for db_info in multiple_dbs_in_report:
        db_name = db_info["db_name"]
        status = db_info["status"]
        db_file_content = db_info.get("db_file_content", b"")
        error_msg = db_info.get("error_msg", "")
        
        # Créer le fichier de base de données si nécessaire
        if status == "success" and db_file_content:
            db_file_path = os.path.join(
                settings.BACKUP_STORAGE_ROOT,
                f"{company_name}_{city}_{neighborhood}",
                "database",
                f"{db_name}.sql.gz"
            )
            ensure_directory_exists(os.path.dirname(db_file_path))
            with open(db_file_path, "wb") as f:
                f.write(db_file_content)
            
            # Calculer le hash et la taille
            file_hash = calculate_file_sha256(db_file_path)
            file_size = os.path.getsize(db_file_path)
        else:
            file_hash = ""
            file_size = 0
        
        # Ajout du champ obligatoire staged_file_name
        status_data["databases"][db_name] = {
            "staged_file_name": f"{db_name}.sql.gz",
            "BACKUP": {
                "status": True if status == "success" else False,
                "message": error_msg if status == "failed" else "Backup completed successfully",
                "sha256_checksum": file_hash,
                "size": file_size
            },
            "COMPRESS": {
                "status": True if status == "success" else False,
                "message": error_msg if status == "failed" else "Compression completed successfully",
                "sha256_checksum": file_hash,
                "size": file_size
            },
            "TRANSFER": {
                "status": True if status == "success" else False,
                "message": error_msg if status == "failed" else "Transfer completed successfully",
                "sha256_checksum": file_hash,
                "size": file_size
            }
        }
    
    # Créer le fichier STATUS.json
    timestamp = operation_time.strftime("%Y%m%d_%H%M%S")
    status_file_name = f"{timestamp}_{company_name}_{city}_{neighborhood}.json"
    status_file_path = os.path.join(
        settings.BACKUP_STORAGE_ROOT,
        f"{company_name}_{city}_{neighborhood}",
        "log",
        status_file_name
    )
    
    ensure_directory_exists(os.path.dirname(status_file_path))
    with open(status_file_path, "w") as f:
        json.dump(status_data, f, indent=2)
    
    return status_file_path

def test_scanner_scenarios(db, test_env):
    """Test complet du scanner avec tous les scénarios possibles."""
    now_utc = datetime.now(timezone.utc)

        # Test 1: Sauvegarde réussie pour un site avec deux BDs
    print(f"\n{COLOR_BLUE}--- Test 1: Sauvegarde réussie pour un site avec deux BDs ---{COLOR_RESET}")
    job_site1_db1 = create_job_and_agent_paths(db, "CompanyA", "CityA", "NeighborhoodA", "db1_13h", 13, 0)
    job_site1_db2 = create_job_and_agent_paths(db, "CompanyA", "CityA", "NeighborhoodA", "db2_13h", 13, 0)
    
    # Vérifier l'état initial
    db.refresh(job_site1_db1)
    db.refresh(job_site1_db2)
    assert job_site1_db1.current_status == JobStatus.UNKNOWN
    assert job_site1_db2.current_status == JobStatus.UNKNOWN

        # Création des fichiers de sauvegarde
    db_file_content_db1 = b"Contenu de la base de donnees db1 reussie."
    db_file_content_db2 = b"Contenu de la base de donnees db2 reussie."

    # Création du STATUS.json
    op_time_site1_13h = datetime(now_utc.year, now_utc.month, now_utc.day, 13, 10, 0, tzinfo=timezone.utc)
    create_status_json_file(
    "CompanyA", "CityA", "NeighborhoodA",
        op_time_site1_13h, 
        multiple_dbs_in_report=[
        {"db_name": "db1_13h", "status": "success", "db_file_content": db_file_content_db1},
        {"db_name": "db2_13h", "status": "success", "db_file_content": db_file_content_db2}
        ]
    )

        # Exécution du scanner
    scanner = BackupScanner(db)
    scanner.scan_all_jobs()

    # Vérification des résultats
    db.refresh(job_site1_db1)
    db.refresh(job_site1_db2)
    assert job_site1_db1.current_status == JobStatus.OK
    assert job_site1_db2.current_status == JobStatus.OK
    
    # Vérifier les entrées de sauvegarde
    backup_entry_db1 = db.query(BackupEntry).filter_by(expected_job_id=job_site1_db1.id).first()
    backup_entry_db2 = db.query(BackupEntry).filter_by(expected_job_id=job_site1_db2.id).first()
    assert backup_entry_db1 is not None
    assert backup_entry_db2 is not None
    assert backup_entry_db1.status == BackupEntryStatus.SUCCESS
    assert backup_entry_db2.status == BackupEntryStatus.SUCCESS

    # Test 2: Sauvegarde échouée pour un site
    print(f"\n{COLOR_BLUE}--- Test 2: Sauvegarde échouée pour un site ---{COLOR_RESET}")
    job_site2_db1 = create_job_and_agent_paths(db, "CompanyB", "CityB", "NeighborhoodB", "db1_14h", 14, 0)
    
    # Vérifier l'état initial
    db.refresh(job_site2_db1)
    assert job_site2_db1.current_status == JobStatus.UNKNOWN

    # Création du STATUS.json avec échec
    op_time_site2_14h = datetime(now_utc.year, now_utc.month, now_utc.day, 14, 10, 0, tzinfo=timezone.utc)
    create_status_json_file(
    "CompanyB", "CityB", "NeighborhoodB",
        op_time_site2_14h,
        multiple_dbs_in_report=[
        {"db_name": "db1_14h", "status": "failed", "error_msg": "Erreur de sauvegarde simulée"}
        ]
    )

    # Exécution du scanner
    scanner.scan_all_jobs()

    # Vérification des résultats
    db.refresh(job_site2_db1)
    assert job_site2_db1.current_status == JobStatus.FAILED
    
    # Vérifier l'entrée de sauvegarde
    backup_entry_site2 = db.query(BackupEntry).filter_by(expected_job_id=job_site2_db1.id).first()
    assert backup_entry_site2 is not None
    assert backup_entry_site2.status == BackupEntryStatus.FAILED
    assert "Erreur de sauvegarde simulée" in backup_entry_site2.message

    # Test 3: Sauvegarde manquante
    print(f"\n{COLOR_BLUE}--- Test 3: Sauvegarde manquante ---{COLOR_RESET}")
    job_site3_db1 = create_job_and_agent_paths(db, "CompanyC", "CityC", "NeighborhoodC", "db1_15h", 15, 0)

    # Vérifier l'état initial
    db.refresh(job_site3_db1)
    assert job_site3_db1.current_status == JobStatus.UNKNOWN
    
    # Simuler le temps actuel après la fenêtre de collecte
    op_time_site3_15h = datetime(now_utc.year, now_utc.month, now_utc.day, 15, 45, 0, tzinfo=timezone.utc)

    # Exécution du scanner
    scanner.scan_all_jobs()

    # Vérification des résultats
    db.refresh(job_site3_db1)
    assert job_site3_db1.current_status == JobStatus.MISSING
    
    # Vérifier l'entrée de sauvegarde
    backup_entry_site3 = db.query(BackupEntry).filter_by(expected_job_id=job_site3_db1.id).first()
    assert backup_entry_site3 is not None
    assert backup_entry_site3.status == BackupEntryStatus.MISSING
    
    # Test 4: Incohérence de hash
    print(f"\n{COLOR_BLUE}--- Test 4: Incohérence de hash ---{COLOR_RESET}")
    job_site4_db1 = create_job_and_agent_paths(db, "CompanyD", "CityD", "NeighborhoodD", "db1_16h", 16, 0)
    
    # Vérifier l'état initial
    db.refresh(job_site4_db1)
    assert job_site4_db1.current_status == JobStatus.UNKNOWN
    
    # Créer un fichier de base de données avec un contenu différent
    db_file_content_actual = b"Contenu reel de la base de donnees."
    db_file_content_reported = b"Contenu different rapporte dans le STATUS.json"
    
    # Création du STATUS.json avec un hash incorrect
    op_time_site4_16h = datetime(now_utc.year, now_utc.month, now_utc.day, 16, 10, 0, tzinfo=timezone.utc)
    create_status_json_file(
        "CompanyD", "CityD", "NeighborhoodD",
        op_time_site4_16h,
        multiple_dbs_in_report=[
            {"db_name": "db1_16h", "status": "success", "db_file_content": db_file_content_reported}
        ]
    )
    
    # Modifier le fichier de base de données après la création du STATUS.json
    db_file_path = os.path.join(
        settings.BACKUP_STORAGE_ROOT,
        "CompanyD_CityD_NeighborhoodD",
        "database",
        "db1_16h.sql.gz"
    )
    with open(db_file_path, "wb") as f:
        f.write(db_file_content_actual)
    
    # Exécution du scanner
    scanner.scan_all_jobs()
    
    # Vérification des résultats
    db.refresh(job_site4_db1)
    assert job_site4_db1.current_status == JobStatus.HASH_MISMATCH
    
    # Vérifier l'entrée de sauvegarde
    backup_entry_site4 = db.query(BackupEntry).filter_by(expected_job_id=job_site4_db1.id).first()
    assert backup_entry_site4 is not None
    assert backup_entry_site4.status == BackupEntryStatus.HASH_MISMATCH
    
    # Test 5: Échec de transfert
    print(f"\n{COLOR_BLUE}--- Test 5: Échec de transfert ---{COLOR_RESET}")
    job_site5_db1 = create_job_and_agent_paths(db, "CompanyE", "CityE", "NeighborhoodE", "db1_17h", 17, 0)
    
    # Vérifier l'état initial
    db.refresh(job_site5_db1)
    assert job_site5_db1.current_status == JobStatus.UNKNOWN
    
    # Création du STATUS.json avec échec de transfert
    op_time_site4_17h = datetime(now_utc.year, now_utc.month, now_utc.day, 17, 10, 0, tzinfo=timezone.utc)
    create_status_json_file(
        "CompanyE", "CityE", "NeighborhoodE",
        op_time_site4_17h,
        multiple_dbs_in_report=[
            {"db_name": "db1_17h", "status": "failed", "error_msg": "Échec du transfert du fichier"}
        ]
    )
    
    # Exécution du scanner
    scanner.scan_all_jobs()
    
    # Vérification des résultats
    db.refresh(job_site5_db1)
    assert job_site5_db1.current_status == JobStatus.TRANSFER_INTEGRITY_FAILED
    
    # Vérifier l'entrée de sauvegarde
    backup_entry_site5 = db.query(BackupEntry).filter_by(expected_job_id=job_site5_db1.id).first()
    assert backup_entry_site5 is not None
    assert backup_entry_site5.status == BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
    assert "Échec du transfert" in backup_entry_site5.message

    print(f"\n{COLOR_GREEN}Tous les tests ont réussi !{COLOR_RESET}")