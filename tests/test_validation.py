# test_validation.py
# Script de test temporaire pour valider le service de validation STATUS.json.

import os
import sys
import json
import logging
import shutil # Pour la suppression récursive des dossiers
from datetime import datetime, timezone, timedelta # Ajout pour les timestamps

# Ajoute le répertoire parent (monitoring_server/) au PYTHONPATH.
sys.path.append(os.path.abspath('.'))

# --- Définition des codes ANSI pour la coloration ---
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m' # Réinitialise la couleur à la fin

# Configure un logging de base pour voir les messages du service de validation lors des tests locaux.
logging.basicConfig(level=logging.DEBUG, format=f'{COLOR_YELLOW}[%(asctime)s]{COLOR_RESET} - [%(levelname)s] - %(message)s')

# Importe la fonction de validation et l'exception personnalisée de votre service.
from app.services.validation_service import validate_status_file, StatusFileValidationError

# Chemins de test (relatifs à la racine du projet)
TEST_BASE_DIR = "temp_test_validation_logs"
VALID_FULL_REPORT_PATH = os.path.join(TEST_BASE_DIR, "valid_full_report.json")
INVALID_JSON_PATH = os.path.join(TEST_BASE_DIR, "invalid_json.json")
MISSING_CORE_GLOBAL_FIELD_PATH = os.path.join(TEST_BASE_DIR, "missing_core_global_field.json")
INVALID_OVERALL_STATUS_PATH = os.path.join(TEST_BASE_DIR, "invalid_overall_status.json")
INVALID_GLOBAL_TIMESTAMP_PATH = os.path.join(TEST_BASE_DIR, "invalid_global_timestamp.json")
INVALID_AGENT_ID_TYPE_PATH = os.path.join(TEST_BASE_DIR, "invalid_agent_id_type.json")
EMPTY_DATABASES_PATH = os.path.join(TEST_BASE_DIR, "empty_databases.json")
MISSING_PROCESS_BLOCK_PATH = os.path.join(TEST_BASE_DIR, "missing_process_block.json") # Should now fail
MISSING_PROCESS_STATUS_PATH = os.path.join(TEST_BASE_DIR, "missing_process_status.json")
INVALID_PROCESS_TIMESTAMP_PATH = os.path.join(TEST_BASE_DIR, "invalid_process_timestamp.json")
INVALID_PROCESS_CHECKSUM_PATH = os.path.join(TEST_BASE_DIR, "invalid_process_checksum.json")
INVALID_PROCESS_SIZE_PATH = os.path.join(TEST_BASE_DIR, "invalid_process_size.json")
MISSING_STAGED_FILE_NAME_PATH = os.path.join(TEST_BASE_DIR, "missing_staged_file_name.json")


def create_test_files():
    """Crée les fichiers de test nécessaires pour la validation, en respectant la structure réelle."""
    os.makedirs(TEST_BASE_DIR, exist_ok=True)

    # --- Fichier 1: Valide et complet (simule HORODATAGE_SIRPACAM_DOUALA_NEWBELL_FINAL.json) ---
    with open(VALID_FULL_REPORT_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "SDMC_DOUALA_AKWA_2023": {
                    "BACKUP": {
                        "status": True,
                        "start_time": "2025-06-12T12:53:52Z",
                        "end_time": "2025-06-12T12:54:26Z",
                        "sha256_checksum": "a6af41c0b61d32d5935ed71ccd8d124b091ef150192d623451476401de13fce3",
                        "size": 188178944
                    },
                    "COMPRESS": {
                        "status": True,
                        "start_time": "2025-06-12T12:55:15Z",
                        "end_time": "2025-06-12T12:56:03Z",
                        "sha256_checksum": "4b63a9e31c52cca0a959cda76464c8e82c738f6ee22c20949d8a80a6fc0cdcb6",
                        "size": 19972513
                    },
                    "TRANSFER": {
                        "status": True,
                        "start_time": "2025-06-12T12:56:06Z",
                        "end_time": "2025-06-12T12:56:06Z",
                        "error_message": None
                    },
                    "staged_file_name": "sdmc_douala_akwa_2023.sql.gz"
                }
            }
        }, f, indent=4)

    # --- Fichier 2: JSON malformé ---
    with open(INVALID_JSON_PATH, 'w', encoding='utf-8') as f:
        f.write("{'operation_end_time': '2025-06-12T20:00:00Z', 'overall_status': 'completed', 'databases': {") # JSON invalide

    # --- Fichier 3: Champ global obligatoire manquant (ex: agent_id) ---
    with open(MISSING_CORE_GLOBAL_FIELD_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "overall_status": "completed",
            "databases": {}
            # agent_id est manquant
        }, f, indent=4)

    # --- Fichier 4: Valeur invalide pour overall_status ---
    with open(INVALID_OVERALL_STATUS_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "invalid_status", # Valeur invalide
            "databases": {}
        }, f, indent=4)

    # --- Fichier 5: Timestamp global invalide (operation_end_time) ---
    with open(INVALID_GLOBAL_TIMESTAMP_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025/06/12 12:56:06", # Format incorrect
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {}
        }, f, indent=4)
    
    # --- Fichier 6: agent_id est présent mais pas une string ---
    with open(INVALID_AGENT_ID_TYPE_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": 12345, # Non string
            "overall_status": "completed",
            "databases": {}
        }, f, indent=4)

    # --- Fichier 7: Databases vide (devrait juste logger un warning, pas une erreur bloquante) ---
    with open(EMPTY_DATABASES_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {}
        }, f, indent=4)

    # --- Fichier 8: Bloc de processus entier manquant (devrait échouer car BACKUP/COMPRESS/TRANSFER sont obligatoires) ---
    with open(MISSING_PROCESS_BLOCK_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": { "status": True },
                    # COMPRESS est entièrement manquant, ce qui est une erreur car il est obligatoire
                    "TRANSFER": { "status": True },
                    "staged_file_name": "db1.sql.gz"
                }
            }
        }, f, indent=4)
    
    # --- Fichier 9: Champ 'status' manquant dans un processus de BD (doit échouer) ---
    with open(MISSING_PROCESS_STATUS_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": {
                        "start_time": "2025-06-12T12:50:00Z" # 'status' est manquant ici
                    },
                    "COMPRESS": { "status": True },
                    "TRANSFER": { "status": True },
                    "staged_file_name": "db1.sql.gz"
                }
            }
        }, f, indent=4)

    # --- Fichier 10: Timestamp de processus invalide (warning, non bloquant) ---
    with open(INVALID_PROCESS_TIMESTAMP_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": {
                        "status": True,
                        "start_time": "2025/06/12 12:50:00" # Format invalide
                    },
                    "COMPRESS": { "status": True },
                    "TRANSFER": { "status": True },
                    "staged_file_name": "db1.sql.gz"
                }
            }
        }, f, indent=4)

    # --- Fichier 11: Checksum de processus invalide (warning, non bloquant) ---
    with open(INVALID_PROCESS_CHECKSUM_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": {
                        "status": True,
                        "sha256_checksum": "short_hash" # Longueur invalide
                    },
                    "COMPRESS": { "status": True },
                    "TRANSFER": { "status": True },
                    "staged_file_name": "db1.sql.gz"
                }
            }
        }, f, indent=4)

    # --- Fichier 12: Taille de processus invalide (warning, non bloquant) ---
    with open(INVALID_PROCESS_SIZE_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": {
                        "status": True,
                        "size": "invalid_size" # Type invalide
                    },
                    "COMPRESS": { "status": True },
                    "TRANSFER": { "status": True },
                    "staged_file_name": "db1.sql.gz"
                }
            }
        }, f, indent=4)
    
    # --- Fichier 13: staged_file_name manquant (doit échouer) ---
    with open(MISSING_STAGED_FILE_NAME_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "operation_start_time": "2025-06-12T12:53:52Z",
            "operation_end_time": "2025-06-12T12:56:06Z",
            "agent_id": "sirpacam_douala_newbell",
            "overall_status": "completed",
            "databases": {
                "DATABASE_NAME_1": {
                    "BACKUP": { "status": True },
                    "COMPRESS": { "status": True },
                    "TRANSFER": { "status": True }
                    # staged_file_name est manquant
                }
            }
        }, f, indent=4)


def cleanup_test_files():
    """Supprime les fichiers et dossiers de test temporaires."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
    print(f"{COLOR_BLUE}Fichiers et répertoires de test temporaires nettoyés.{COLOR_RESET}")

def run_local_tests():
    print(f"\n{COLOR_BLUE}--- Exécution des tests locaux du service de validation ---{COLOR_RESET}")

    # TEST 1: Fichier valide et complet (nouvelle structure réelle)
    print(f"\n{COLOR_BLUE}--- TEST 1: Fichier STATUS.json valide (structure réelle) ---{COLOR_RESET}")
    try:
        validated_data = validate_status_file(VALID_FULL_REPORT_PATH)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Données validées : {validated_data}")
        assert validated_data["overall_status"] == "completed"
        assert "SDMC_DOUALA_AKWA_2023" in validated_data["databases"]
        assert validated_data["databases"]["SDMC_DOUALA_AKWA_2023"]["BACKUP"]["status"] == True
        assert validated_data["databases"]["SDMC_DOUALA_AKWA_2023"]["staged_file_name"] == "sdmc_douala_akwa_2023.sql.gz"
    except StatusFileValidationError as e:
        print(f"{COLOR_RED}ÉCHEC TEST 1:{COLOR_RESET} Erreur inattendue pour fichier valide : {e}")
    except AssertionError:
        print(f"{COLOR_RED}ÉCHEC TEST 1:{COLOR_RESET} L'assertion des données a échoué.")

    # TEST 2: Fichier non existant
    print(f"\n{COLOR_BLUE}--- TEST 2: Fichier non existant ---{COLOR_RESET}")
    try:
        validate_status_file(os.path.join(TEST_BASE_DIR, "non_existent.json"))
        print(f"{COLOR_RED}ÉCHEC TEST 2:{COLOR_RESET} Une erreur était attendue pour un fichier non existant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un fichier non existant : {e}")

    # TEST 3: JSON malformé
    print(f"\n{COLOR_BLUE}--- TEST 3: Fichier JSON malformé ---{COLOR_RESET}")
    try:
        validate_status_file(INVALID_JSON_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 3:{COLOR_RESET} Une erreur était attendue pour un JSON malformé, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un JSON malformé : {e}")

    # TEST 4: Champ global obligatoire manquant (ex: agent_id)
    print(f"\n{COLOR_BLUE}--- TEST 4: Champ global obligatoire manquant (agent_id) ---{COLOR_RESET}")
    try:
        validate_status_file(MISSING_CORE_GLOBAL_FIELD_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 4:{COLOR_RESET} Une erreur était attendue pour un champ global manquant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un champ global manquant : {e}")

    # TEST 5: Valeur invalide pour overall_status
    print(f"\n{COLOR_BLUE}--- TEST 5: Valeur invalide pour 'overall_status' ---{COLOR_RESET}")
    try:
        validate_status_file(INVALID_OVERALL_STATUS_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 5:{COLOR_RESET} Une erreur était attendue pour un overall_status invalide, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un overall_status invalide : {e}")

    # TEST 6: Timestamp global invalide (operation_end_time)
    print(f"\n{COLOR_BLUE}--- TEST 6: Format d'horodatage global invalide (operation_end_time) ---{COLOR_RESET}")
    try:
        validate_status_file(INVALID_GLOBAL_TIMESTAMP_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 6:{COLOR_RESET} Une erreur était attendue pour un horodatage global invalide, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un horodatage global invalide : {e}")

    # TEST 7: agent_id est présent mais pas une string
    print(f"\n{COLOR_BLUE}--- TEST 7: agent_id présent mais type incorrect ---{COLOR_RESET}")
    try:
        validate_status_file(INVALID_AGENT_ID_TYPE_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 7:{COLOR_RESET} Une erreur était attendue pour un agent_id de type incorrect, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un agent_id de type incorrect : {e}")
    
    # TEST 8: Databases vide (devrait juste logger un warning, pas une erreur)
    print(f"\n{COLOR_BLUE}--- TEST 8: Section 'databases' vide ---{COLOR_RESET}")
    try:
        validated_data = validate_status_file(EMPTY_DATABASES_PATH)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Données validées malgré une section 'databases' vide : {validated_data}")
        assert validated_data["databases"] == {}
    except StatusFileValidationError as e:
        print(f"{COLOR_RED}ÉCHEC TEST 8:{COLOR_RESET} Erreur inattendue pour une section 'databases' vide : {e}")

    # TEST 9: Bloc de processus entier manquant (doit échouer car processus BACKUP/COMPRESS/TRANSFER sont obligatoires)
    print(f"\n{COLOR_BLUE}--- TEST 9: Bloc de processus obligatoire manquant ---{COLOR_RESET}")
    try:
        validate_status_file(MISSING_PROCESS_BLOCK_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 9:{COLOR_RESET} Une erreur était attendue pour un bloc de processus manquant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un bloc de processus manquant : {e}")

    # TEST 10: Champ 'status' manquant dans un processus de BD (doit échouer)
    print(f"\n{COLOR_BLUE}--- TEST 10: Champ 'status' obligatoire manquant dans un processus de BD ---{COLOR_RESET}")
    try:
        validate_status_file(MISSING_PROCESS_STATUS_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 10:{COLOR_RESET} Une erreur était attendue pour un 'status' de processus manquant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un 'status' de processus manquant : {e}")

    # TEST 11: Timestamp de processus invalide (warning, non bloquant)
    print(f"\n{COLOR_BLUE}--- TEST 11: Format de timestamp de processus invalide (non bloquant) ---{COLOR_RESET}")
    try:
        validated_data = validate_status_file(INVALID_PROCESS_TIMESTAMP_PATH)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Données validées malgré un timestamp de processus invalide : {validated_data}")
        assert validated_data["overall_status"] == "completed"
    except StatusFileValidationError as e:
        print(f"{COLOR_RED}ÉCHEC TEST 11:{COLOR_RESET} Erreur inattendue pour un timestamp de processus invalide : {e}")

    # TEST 12: Checksum de processus invalide (warning, non bloquant)
    print(f"\n{COLOR_BLUE}--- TEST 12: Format de checksum de processus invalide (non bloquant) ---{COLOR_RESET}")
    try:
        validated_data = validate_status_file(INVALID_PROCESS_CHECKSUM_PATH)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Données validées malgré un checksum de processus invalide : {validated_data}")
        assert validated_data["overall_status"] == "completed"
    except StatusFileValidationError as e:
        print(f"{COLOR_RED}ÉCHEC TEST 12:{COLOR_RESET} Erreur inattendue pour un checksum de processus invalide : {e}")

    # TEST 13: Taille de processus invalide (warning, non bloquant)
    print(f"\n{COLOR_BLUE}--- TEST 13: Taille de processus invalide (non bloquant) ---{COLOR_RESET}")
    try:
        validated_data = validate_status_file(INVALID_PROCESS_SIZE_PATH)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Données validées malgré une taille de processus invalide : {validated_data}")
        assert validated_data["overall_status"] == "completed"
    except StatusFileValidationError as e:
        print(f"{COLOR_RED}ÉCHEC TEST 13:{COLOR_RESET} Erreur inattendue pour une taille de processus invalide : {e}")

    # TEST 14: staged_file_name manquant (doit échouer car maintenant obligatoire)
    print(f"\n{COLOR_BLUE}--- TEST 14: staged_file_name manquant (obligatoire) ---{COLOR_RESET}")
    try:
        validate_status_file(MISSING_STAGED_FILE_NAME_PATH)
        print(f"{COLOR_RED}ÉCHEC TEST 14:{COLOR_RESET} Une erreur était attendue pour un staged_file_name manquant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue interceptée pour un staged_file_name manquant : {e}")


    print(f"\n{COLOR_BLUE}--- Tests locaux terminés ---{COLOR_RESET}")

if __name__ == "__main__":
    create_test_files() # Crée les fichiers de test avant l'exécution
    try:
        run_local_tests()
    finally:
        cleanup_test_files() # Nettoie toujours les fichiers de test après l'exécution
