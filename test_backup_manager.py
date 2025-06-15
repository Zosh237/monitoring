# test_backup_manager.py
# Script de tests fonctionnels pour valider le service app/services/backup_manager.py.

import os
import sys
import logging
import shutil
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch # Ne plus mocker config.settings, mais d'autres mocks si besoin
import traceback # Importe le module traceback pour imprimer les traces d'erreurs complètes

# ATTENTION: Assurez-vous d'exécuter ce script depuis la racine de votre projet (dossier 'monitoring_server').
# Cette ligne ajoute la racine du projet au PYTHONPATH afin que Python puisse trouver les modules 'app' et 'config'.
sys.path.append(os.path.abspath('.'))

# --- Configuration du logging pour les tests ---
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

# --- Importations des modules de l'application ---
# Ces importations devraient maintenant fonctionner correctement si le sys.path est bien configuré.
from app.core.database import Base # Pour créer les tables de test (même si pas directement utilisées par promote_backup)
from app.models.models import ExpectedBackupJob, BackupFrequency
from app.services.backup_manager import promote_backup, BackupManagerError
from app.utils.file_operations import ensure_directory_exists, create_dummy_file, delete_file, FileOperationError

# --- Chemins de test (relatifs à la racine du projet) ---
TEST_BASE_DIR = "temp_backup_manager_test_env"
STAGING_AREA = os.path.join(TEST_BASE_DIR, "staging_area")
VALIDATED_BACKUPS_BASE_PATH = os.path.join(TEST_BASE_DIR, "validated_backups")

# --- Fonctions utilitaires de test ---
def setup_test_environment():
    """Crée les répertoires de test et nettoie les anciens si existent."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
        logger.info(f"Ancien répertoire de test '{TEST_BASE_DIR}' supprimé.")
    ensure_directory_exists(STAGING_AREA)
    ensure_directory_exists(VALIDATED_BACKUPS_BASE_PATH)
    logger.info(f"Répertoires de test créés sous '{TEST_BASE_DIR}'.")

def cleanup_test_environment():
    """Supprime tous les répertoires de test."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
        logger.info(f"Répertoire de test '{TEST_BASE_DIR}' nettoyé.")

def run_tests():
    """Exécute la suite de tests fonctionnels pour backup_manager."""
    setup_test_environment()

    # Configuration de la base de données de test en mémoire (pour instancier ExpectedBackupJob)
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        current_year = datetime.utcnow().year

        # --- SCÉNARIO 1: Promotion réussie d'un fichier ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 1: Promotion réussie d'un fichier ---{COLOR_RESET}")
        job_promo_1 = ExpectedBackupJob(
            year=current_year, company_name="CorpA", city="VilleX", neighborhood="Zone1", database_name="db_promo_ok",
            expected_hour_utc=10, expected_minute_utc=0, agent_id_responsible="agent_promo_1",
            agent_deposit_path_template="path_not_used_by_promote", agent_log_deposit_path_template="path_not_used_by_promote",
            final_storage_path_template="{year}/{company_name}/{city}/{db_name}.sql.gz",
            expected_frequency=BackupFrequency.DAILY, days_of_week="MO", is_active=True
        )
        db.add(job_promo_1)
        db.commit()
        db.refresh(job_promo_1)

        # Créez le fichier stagé
        staged_file_name_1 = f"{job_promo_1.database_name}.sql.gz" 
        staged_file_path_1 = os.path.join(STAGING_AREA, staged_file_name_1)
        create_dummy_file(staged_file_path_1, b"Contenu du fichier de sauvegarde stage 1.")

        # Appelle la fonction à tester, en passant explicitement VALIDATED_BACKUPS_BASE_PATH
        promoted_path_1 = promote_backup(staged_file_path_1, job_promo_1, base_validated_path=VALIDATED_BACKUPS_BASE_PATH)

        # Reconstruit le chemin attendu en miroir de la logique de promote_backup
        expected_relative_path_1 = job_promo_1.final_storage_path_template.format(
            year=job_promo_1.year,
            company_name=job_promo_1.company_name,
            city=job_promo_1.city,
            db_name=job_promo_1.database_name
        )
        expected_dest_path_1 = os.path.join(VALIDATED_BACKUPS_BASE_PATH, expected_relative_path_1)
        
        print(f"DEBUG TEST SCENARIO 1 - Chemin Promu (Fonction) : '{os.path.normpath(promoted_path_1)}'")
        print(f"DEBUG TEST SCENARIO 1 - Chemin Attendu (Test)   : '{os.path.normpath(expected_dest_path_1)}'")

        # Assertions
        assert os.path.normpath(promoted_path_1) == os.path.normpath(expected_dest_path_1), \
            f"ÉCHEC: Le chemin promu ne correspond pas au chemin attendu.\nAttendu: '{os.path.normpath(expected_dest_path_1)}'\nObtenu: '{os.path.normpath(promoted_path_1)}'"
        assert os.path.exists(os.path.normpath(expected_dest_path_1)), \
            f"ÉCHEC: Le fichier promu n'existe pas à la destination attendue: '{os.path.normpath(expected_dest_path_1)}'"
        assert os.path.exists(os.path.normpath(staged_file_path_1)), \
            f"ÉCHEC: Le fichier original dans la zone de staging a été supprimé: '{os.path.normpath(staged_file_path_1)}'"
        
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 1 validé - Fichier promu avec succès (original non déplacé).")

        # --- SCÉNARIO 2: Création des répertoires de destination si inexistants ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 2: Création des répertoires de destination si inexistants ---{COLOR_RESET}")
        job_promo_2 = ExpectedBackupJob(
            year=current_year, company_name="CorpB", city="VilleY", neighborhood="Zone2", database_name="db_promo_new_path",
            expected_hour_utc=10, expected_minute_utc=0, agent_id_responsible="agent_promo_2",
            agent_deposit_path_template="path_not_used", agent_log_deposit_path_template="path_not_used",
            final_storage_path_template="{year}/{company_name}/{city}/{db_name}.sql.gz",
            expected_frequency=BackupFrequency.DAILY, days_of_week="TU", is_active=True
        )
        db.add(job_promo_2)
        db.commit()
        db.refresh(job_promo_2)

        staged_file_name_2 = f"{job_promo_2.database_name}.sql.gz"
        staged_file_path_2 = os.path.join(STAGING_AREA, staged_file_name_2)
        create_dummy_file(staged_file_path_2, b"Contenu du fichier de sauvegarde stage 2.")

        # Nettoyer spécifiquement le sous-répertoire qui devrait être créé
        expected_relative_path_2 = job_promo_2.final_storage_path_template.format(
            year=job_promo_2.year,
            company_name=job_promo_2.company_name,
            city=job_promo_2.city,
            db_name=job_promo_2.database_name
        )
        expected_dest_dir_2 = os.path.join(VALIDATED_BACKUPS_BASE_PATH, os.path.dirname(expected_relative_path_2))
        if os.path.exists(expected_dest_dir_2):
            shutil.rmtree(expected_dest_dir_2)

        # Appelle la fonction à tester, en passant explicitement VALIDATED_BACKUPS_BASE_PATH
        promoted_path_2 = promote_backup(staged_file_path_2, job_promo_2, base_validated_path=VALIDATED_BACKUPS_BASE_PATH)
        
        # Recalculer le chemin attendu après l'appel à promote_backup pour comparaison
        expected_relative_path_2_after_call = job_promo_2.final_storage_path_template.format(
            year=job_promo_2.year,
            company_name=job_promo_2.company_name,
            city=job_promo_2.city,
            db_name=job_promo_2.database_name
        )
        expected_dest_path_2 = os.path.join(VALIDATED_BACKUPS_BASE_PATH, expected_relative_path_2_after_call)


        print(f"DEBUG TEST SCENARIO 2 - Chemin Promu (Fonction) : '{os.path.normpath(promoted_path_2)}'")
        print(f"DEBUG TEST SCENARIO 2 - Chemin Attendu (Test)   : '{os.path.normpath(expected_dest_path_2)}'")

        # Assertions
        assert os.path.exists(os.path.normpath(os.path.dirname(expected_dest_path_2))), \
            f"ÉCHEC: Le répertoire de destination '{os.path.normpath(os.path.dirname(expected_dest_path_2))}' n'a pas été créé."
        assert os.path.normpath(promoted_path_2) == os.path.normpath(expected_dest_path_2), \
            f"ÉCHEC: Le chemin promu ne correspond pas au chemin attendu. Attendu: '{os.path.normpath(expected_dest_path_2)}'\nObtenu: '{os.path.normpath(promoted_path_2)}'"
        assert os.path.exists(os.path.normpath(staged_file_path_2)), \
            f"ÉCHEC: Le fichier original dans la zone de staging a été supprimé: '{os.path.normpath(staged_file_path_2)}'"

        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 2 validé - Répertoires de destination créés si inexistants.")

        # --- SCÉNARIO 3: Échec de l'opération de copie (simulé) ---
        print(f"\n{COLOR_BLUE}--- SCÉNARIO 3: Échec de l'opération de copie (simulé) ---{COLOR_RESET}")
        job_promo_3 = ExpectedBackupJob(
            year=current_year, company_name="CorpC", city="VilleZ", neighborhood="Zone3", database_name="db_promo_fail",
            expected_hour_utc=10, expected_minute_utc=0, agent_id_responsible="agent_promo_3",
            agent_deposit_path_template="path_not_used", agent_log_deposit_path_template="path_not_used",
            final_storage_path_template="{year}/{company_name}/{city}/{db_name}.sql.gz",
            expected_frequency=BackupFrequency.DAILY, days_of_week="WE", is_active=True
        )
        db.add(job_promo_3)
        db.commit()
        db.refresh(job_promo_3)

        staged_file_name_3 = f"{job_promo_3.database_name}.sql.gz"
        staged_file_path_3 = os.path.join(STAGING_AREA, staged_file_name_3)
        create_dummy_file(staged_file_path_3, b"Contenu du fichier de sauvegarde stage 3.")

        with patch('app.utils.file_operations.copy_file', side_effect=FileOperationError("Erreur de copie simulée.")):
            try:
                # Appelle la fonction à tester, en passant explicitement VALIDATED_BACKUPS_BASE_PATH
                promote_backup(staged_file_path_3, job_promo_3, base_validated_path=VALIDATED_BACKUPS_BASE_PATH)
                assert False, "ÉCHEC: BackupManagerError n'a pas été levée comme attendu lors d'une erreur de copie."
            except BackupManagerError as e:
                logger.info(f"{COLOR_GREEN}v Exception BackupManagerError attrapée comme prévu: {e}{COLOR_RESET}")
                assert os.path.exists(os.path.normpath(staged_file_path_3)), \
                    f"ÉCHEC: Le fichier original dans la zone de staging a été supprimé malgré l'échec de la copie: '{os.path.normpath(staged_file_path_3)}'"
                
                expected_relative_path_3 = job_promo_3.final_storage_path_template.format(
                    year=job_promo_3.year,
                    company_name=job_promo_3.company_name,
                    city=job_promo_3.city,
                    db_name=job_promo_3.database_name
                )
                expected_dest_path_3 = os.path.join(VALIDATED_BACKUPS_BASE_PATH, expected_relative_path_3)


                print(f"DEBUG TEST SCENARIO 3 - Chemin Promu (Fonction) : N/A (échec attendu)")
                print(f"DEBUG TEST SCENARIO 3 - Chemin Attendu (Test)   : '{os.path.normpath(expected_dest_path_3)}'")
                
                assert not os.path.exists(os.path.normpath(expected_dest_path_3)), \
                    f"ÉCHEC: Le fichier de destination a été créé malgré l'échec de la copie: '{os.path.normpath(expected_dest_path_3)}'"
                print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 3 validé - Gestion des échecs de copie (original non déplacé, destination vide).")


    except AssertionError as e:
        logger.error(f"{COLOR_RED}ÉCHEC DU TEST:{COLOR_RESET} {e}")
        traceback.print_exc() # Imprime le traceback complet pour les erreurs d'assertion
        sys.exit(1)
    except Exception as e:
        logger.critical(f"{COLOR_RED}ERREUR CRITIQUE PENDANT LES TESTS:{COLOR_RESET} {e}", exc_info=True)
        traceback.print_exc() # Imprime le traceback complet pour toutes les autres exceptions
        sys.exit(1)
    finally:
        db.close()
        cleanup_test_environment()
        print(f"\n{COLOR_BLUE}--- Tous les tests fonctionnels du gestionnaire de sauvegardes ont été exécutés. ---{COLOR_RESET}")

if __name__ == "__main__":
    run_tests()
