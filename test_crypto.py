# test_crypto.py
# Script de test temporaire pour valider le service app/utils/crypto.py.

import os
import sys
import logging
import shutil # Pour le nettoyage du dossier de test
import hashlib # Pour calculer les hachages de référence

# Ajoute le répertoire racine du projet au PYTHONPATH.
sys.path.append(os.path.abspath('.'))

# Configure un logging de base pour voir les messages du service lors des tests locaux.
# Utilisation de couleurs pour une meilleure lisibilité.
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'

logging.basicConfig(
    level=logging.DEBUG,
    format=f'{COLOR_BLUE}[%(asctime)s]{COLOR_RESET} - [%(levelname)s] - %(message)s'
)

# Importe les fonctions du service à tester.
from app.utils.crypto import calculate_file_sha256, CryptoUtilityError

# Définition des chemins de test temporaires
TEST_BASE_DIR = "temp_crypto_test"

def setup_test_environment():
    """Crée un environnement de test propre."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR) # Nettoyage précédent si nécessaire
    os.makedirs(TEST_BASE_DIR)
    logging.info(f"Environnement de test créé : {TEST_BASE_DIR}")

def cleanup_test_environment():
    """Supprime l'environnement de test."""
    if os.path.exists(TEST_BASE_DIR):
        shutil.rmtree(TEST_BASE_DIR)
        logging.info(f"Environnement de test nettoyé : {TEST_BASE_DIR}")

def create_dummy_file(path: str, content: bytes) -> None:
    """Crée un fichier factice avec du contenu binaire."""
    # S'assurer que le répertoire parent existe avant de créer le fichier
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f: # 'wb' pour l'écriture binaire
        f.write(content)
    logging.debug(f"Fichier factice créé : {path} ({len(content)} octets)")

def calculate_reference_sha256(content: bytes) -> str:
    """Calcule le hachage SHA256 de référence pour un contenu donné."""
    return hashlib.sha256(content).hexdigest()

def run_tests():
    """Exécute tous les tests pour les utilitaires cryptographiques."""
    print(f"\n{COLOR_BLUE}--- Début des tests du service cryptographique ---{COLOR_RESET}")

    # --- Test 1: Fichier vide ---
    print(f"\n{COLOR_BLUE}--- Test 1: Fichier vide ---{COLOR_RESET}")
    empty_file = os.path.join(TEST_BASE_DIR, "empty.txt")
    create_dummy_file(empty_file, b"")
    expected_hash_empty = calculate_reference_sha256(b"") # Hachage SHA256 d'une chaîne vide
    try:
        calculated_hash = calculate_file_sha256(empty_file)
        assert calculated_hash == expected_hash_empty
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Hachage du fichier vide correct : {calculated_hash}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur lors du test du fichier vide : {e}")

    # --- Test 2: Petit fichier ---
    print(f"\n{COLOR_BLUE}--- Test 2: Petit fichier ---{COLOR_RESET}")
    small_file = os.path.join(TEST_BASE_DIR, "small.txt")
    small_content = b"Hello, world! This is a small test file."
    create_dummy_file(small_file, small_content)
    expected_hash_small = calculate_reference_sha256(small_content)
    try:
        calculated_hash = calculate_file_sha256(small_file)
        assert calculated_hash == expected_hash_small
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Hachage du petit fichier correct : {calculated_hash}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur lors du test du petit fichier : {e}")

    # --- Test 3: Fichier moyen (pour tester le chunking) ---
    print(f"\n{COLOR_BLUE}--- Test 3: Fichier moyen (test du chunking) ---{COLOR_RESET}")
    medium_file = os.path.join(TEST_BASE_DIR, "medium.bin")
    # Créer un contenu un peu plus grand que la taille de chunk par défaut (8192)
    medium_content = b"a" * 10000 + b"b" * 5000 + b"c" * 2000
    create_dummy_file(medium_file, medium_content)
    expected_hash_medium = calculate_reference_sha256(medium_content)
    try:
        calculated_hash = calculate_file_sha256(medium_file)
        assert calculated_hash == expected_hash_medium
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Hachage du fichier moyen correct : {calculated_hash}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur lors du test du fichier moyen : {e}")

    # --- Test 4: Fichier non existant ---
    print(f"\n{COLOR_BLUE}--- Test 4: Fichier non existant ---{COLOR_RESET}")
    non_existent_file = os.path.join(TEST_BASE_DIR, "non_existent.txt")
    try:
        calculate_file_sha256(non_existent_file)
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Calcul de hachage de fichier non existant a réussi inopinément.")
    except CryptoUtilityError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue pour fichier non existant : {e}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur inattendue pour fichier non existant : {e}")

    # --- Test 5: Chemin qui est un répertoire, pas un fichier ---
    print(f"\n{COLOR_BLUE}--- Test 5: Chemin est un répertoire ---{COLOR_RESET}")
    directory_path = os.path.join(TEST_BASE_DIR, "a_directory")
    os.makedirs(directory_path, exist_ok=True)
    try:
        calculate_file_sha256(directory_path)
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Calcul de hachage pour un répertoire a réussi inopinément.")
    except CryptoUtilityError as e:
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue pour chemin de répertoire : {e}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur inattendue pour chemin de répertoire : {e}")


    print(f"\n{COLOR_BLUE}--- Fin des tests du service cryptographique ---{COLOR_RESET}")

if __name__ == "__main__":
    setup_test_environment()
    try:
        run_tests()
    finally:
        cleanup_test_environment()

