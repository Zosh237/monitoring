# test_validation.py
# Script de test temporaire pour valider le service de validation STATUS.json.

import os
import sys
import json
import logging
import shutil # Pour la suppression récursive des dossiers

# Ajoute le répertoire parent (monitoring_server/) au PYTHONPATH.
# Ceci est crucial pour que Python puisse trouver les modules de votre application
# (ex: 'app.services.validation_service') lorsque vous exécutez ce script depuis la racine du projet.
# os.path.abspath('.') donne le chemin absolu du répertoire courant.
sys.path.append(os.path.abspath('.'))

# Configure un logging de base pour voir les messages du service de validation lors des tests locaux.
# Ce logging simple est utilisé ici car nous ne chargeons pas le logging.yaml complet pour un script de test unitaire.
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] - %(levelname)s - %(message)s')

# Importe la fonction de validation et l'exception personnalisée de votre service.
from app.services.validation_service import validate_status_file, StatusFileValidationError

# Chemins de test (relatifs à la racine du projet)
TEST_BASE_DIR = "temp_test_logs"
VALID_FILE_PATH = os.path.join(TEST_BASE_DIR, "my_db_name", "logs", "my_db_name_20250610_1300_SUCCESS.json")
INVALID_JSON_PATH = os.path.join(TEST_BASE_DIR, "my_db_name", "logs", "invalid_json.json")
MISSING_FIELD_PATH = os.path.join(TEST_BASE_DIR, "my_db_name", "logs", "missing_field.json")
NON_EXISTENT_PATH = os.path.join(TEST_BASE_DIR, "my_db_name", "logs", "non_existent.json")
INVALID_TIMESTAMP_PATH = os.path.join(TEST_BASE_DIR, "my_db_name", "logs", "invalid_timestamp.json")

def create_test_files():
    """Crée les fichiers de test nécessaires pour la validation."""
    os.makedirs(os.path.join(TEST_BASE_DIR, "my_db_name", "logs"), exist_ok=True)

    # Fichier valide
    with open(VALID_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "status": "success",
            "timestamp": "2025-06-10T13:05:00Z",
            "file_name": "my_db_name.sql.gz",
            "file_size_bytes": 1024000,
            "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
            "duration_seconds": 120
        }, f)

    # Fichier JSON malformé
    with open(INVALID_JSON_PATH, 'w', encoding='utf-8') as f:
        f.write("{'status': 'success', 'timestamp': '2025-06-10T13:05:00Z'") # JSON invalide

    # Fichier avec champ obligatoire manquant
    with open(MISSING_FIELD_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "status": "success",
            "timestamp": "2025-06-10T13:05:00Z",
            "file_size_bytes": 1024000,
            "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
            # file_name est manquant
        }, f)

    # Fichier avec timestamp invalide
    with open(INVALID_TIMESTAMP_PATH, 'w', encoding='utf-8') as f:
        json.dump({
            "status": "success",
            "timestamp": "2025/06/10 13:05:00", # Format incorrect
            "file_name": "my_db_name.sql.gz",
            "file_size_bytes": 1024000,
            "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
        }, f)

def cleanup_test_files():
    """Supprime les fichiers et dossiers de test temporaires."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
    print("Fichiers et répertoires de test temporaires nettoyés.")

def run_local_tests():
    print("\n--- Exécution des tests locaux du service de validation ---")

    # TEST 1: Fichier valide
    print("\n--- TEST 1: Fichier STATUS.json valide ---")
    try:
        validated_data = validate_status_file(VALID_FILE_PATH)
        print(f"SUCCÈS: Données validées : {validated_data}")
        assert validated_data["status"] == "success"
        assert validated_data["file_size_bytes"] == 1024000
    except StatusFileValidationError as e:
        print(f"ÉCHEC TEST 1: Erreur inattendue : {e}")
    except AssertionError:
        print("ÉCHEC TEST 1: L'assertion des données a échoué.")

    # TEST 2: Fichier non existant
    print("\n--- TEST 2: Fichier non existant ---")
    try:
        validate_status_file(NON_EXISTENT_PATH)
        print("ÉCHEC TEST 2: Une erreur était attendue pour un fichier non existant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"SUCCÈS: Erreur attendue interceptée pour un fichier non existant : {e}")

    # TEST 3: JSON malformé
    print("\n--- TEST 3: Fichier JSON malformé ---")
    try:
        validate_status_file(INVALID_JSON_PATH)
        print("ÉCHEC TEST 3: Une erreur était attendue pour un JSON malformé, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"SUCCÈS: Erreur attendue interceptée pour un JSON malformé : {e}")

    # TEST 4: Champ obligatoire manquant
    print("\n--- TEST 4: Champ obligatoire manquant ---")
    try:
        validate_status_file(MISSING_FIELD_PATH)
        print("ÉCHEC TEST 4: Une erreur était attendue pour un champ manquant, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"SUCCÈS: Erreur attendue interceptée pour un champ manquant : {e}")

    # TEST 5: Timestamp invalide
    print("\n--- TEST 5: Format d'horodatage invalide ---")
    try:
        validate_status_file(INVALID_TIMESTAMP_PATH)
        print("ÉCHEC TEST 5: Une erreur était attendue pour un horodatage invalide, mais le test a réussi.")
    except StatusFileValidationError as e:
        print(f"SUCCÈS: Erreur attendue interceptée pour un horodatage invalide : {e}")

    print("\n--- Tests locaux terminés ---")

if __name__ == "__main__":
    create_test_files() # Crée les fichiers de test avant l'exécution
    try:
        run_local_tests()
    finally:
        cleanup_test_files() # Nettoie toujours les fichiers de test après l'exécution
