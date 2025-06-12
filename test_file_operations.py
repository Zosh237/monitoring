# test_file_operations.py
# Script de test temporaire pour valider le service app/utils/file_operations.py.

import os
import sys
import logging
import shutil # Pour le nettoyage du dossier de test

# Ajoute le répertoire racine du projet au PYTHONPATH.
# Ceci est crucial pour que Python puisse trouver les modules de votre application
# (ex: 'app.utils.file_operations') lorsque vous exécutez ce script depuis la racine du projet.
sys.path.append(os.path.abspath('.'))

# Configure un logging de base pour voir les messages du service lors des tests locaux.
logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] - %(levelname)s - %(message)s')

# Importe les fonctions du service à tester.
from app.utils.file_operations import ensure_directory_exists, move_file, delete_file, FileOperationError

# Définition des chemins de test temporaires
TEST_BASE_DIR = "temp_file_ops_test"

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

def create_dummy_file(path: str, content: str = "test content") -> None:
    """Crée un fichier factice avec du contenu."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)
    logging.debug(f"Fichier factice créé : {path}")

def run_tests():
    """Exécute tous les tests pour les opérations de fichier."""
    print("\n--- Début des tests du service de manipulation de fichiers ---")

    # --- Test ensure_directory_exists ---
    print("\n--- Test : ensure_directory_exists ---")
    test_dir_1 = os.path.join(TEST_BASE_DIR, "dir1")
    test_dir_2 = os.path.join(TEST_BASE_DIR, "parent", "child", "grandchild")

    try:
        ensure_directory_exists(test_dir_1)
        assert os.path.isdir(test_dir_1)
        print(f"SUCCÈS: Création de '{test_dir_1}'")

        ensure_directory_exists(test_dir_1) # Tester sur un existant
        print(f"SUCCÈS: Répertoire existant '{test_dir_1}' géré sans erreur")

        ensure_directory_exists(test_dir_2)
        assert os.path.isdir(test_dir_2)
        print(f"SUCCÈS: Création récursive de '{test_dir_2}'")
    except Exception as e:
        print(f"ÉCHEC: Erreur dans ensure_directory_exists : {e}")

    # --- Test move_file ---
    print("\n--- Test : move_file ---")
    source_file_1 = os.path.join(TEST_BASE_DIR, "source1.txt")
    dest_file_1 = os.path.join(TEST_BASE_DIR, "dest_dir", "destination1.txt")
    source_file_2 = os.path.join(TEST_BASE_DIR, "source2.txt")
    dest_file_2_overwrite = os.path.join(TEST_BASE_DIR, "dest_dir", "destination1.txt") # Pour écraser dest_file_1

    # Préparation pour move_file
    create_dummy_file(source_file_1, "Contenu du fichier source 1")
    create_dummy_file(source_file_2, "Contenu du fichier source 2")

    # Test 1: Déplacement simple
    try:
        move_file(source_file_1, dest_file_1)
        assert not os.path.exists(source_file_1)
        assert os.path.exists(dest_file_1)
        with open(dest_file_1, 'r') as f:
            assert f.read() == "Contenu du fichier source 1"
        print(f"SUCCÈS: Déplacement de '{source_file_1}' vers '{dest_file_1}'")
    except Exception as e:
        print(f"ÉCHEC: Erreur lors du déplacement simple : {e}")

    # Test 2: Déplacement pour écraser une destination existante
    try:
        # source_file_2 sera déplacé vers dest_file_2_overwrite (qui est le même que dest_file_1)
        move_file(source_file_2, dest_file_2_overwrite)
        assert not os.path.exists(source_file_2)
        assert os.path.exists(dest_file_2_overwrite)
        with open(dest_file_2_overwrite, 'r') as f:
            assert f.read() == "Contenu du fichier source 2" # Vérifier que le contenu a changé
        print(f"SUCCÈS: Déplacement de '{source_file_2}' vers '{dest_file_2_overwrite}' (écrasement)")
    except Exception as e:
        print(f"ÉCHEC: Erreur lors du déplacement avec écrasement : {e}")

    # Test 3: Déplacement d'un fichier non existant
    non_existent_file = os.path.join(TEST_BASE_DIR, "non_existent.txt")
    try:
        move_file(non_existent_file, os.path.join(TEST_BASE_DIR, "some_dest.txt"))
        print("ÉCHEC: Déplacement de fichier non existant a réussi inopinément.")
    except FileOperationError as e:
        print(f"SUCCÈS: Erreur attendue pour fichier non existant : {e}")
    except Exception as e:
        print(f"ÉCHEC: Erreur inattendue pour fichier non existant : {e}")

    # --- Test delete_file ---
    print("\n--- Test : delete_file ---")
    file_to_delete_1 = os.path.join(TEST_BASE_DIR, "file_to_delete_1.txt")
    file_to_delete_2 = os.path.join(TEST_BASE_DIR, "file_to_delete_2.txt") # Ce fichier existera pas

    create_dummy_file(file_to_delete_1)

    # Test 1: Suppression d'un fichier existant
    try:
        delete_file(file_to_delete_1)
        assert not os.path.exists(file_to_delete_1)
        print(f"SUCCÈS: Suppression de '{file_to_delete_1}'")
    except Exception as e:
        print(f"ÉCHEC: Erreur lors de la suppression de fichier existant : {e}")

    # Test 2: Suppression d'un fichier non existant (devrait ignorer/avertir, pas échouer)
    try:
        delete_file(file_to_delete_2)
        print(f"SUCCÈS: Suppression de fichier non existant '{file_to_delete_2}' gérée sans erreur.")
    except Exception as e:
        print(f"ÉCHEC: Erreur inattendue lors de la suppression de fichier non existant : {e}")

    print("\n--- Fin des tests du service de manipulation de fichiers ---")

if __name__ == "__main__":
    setup_test_environment()
    try:
        run_tests()
    finally:
        cleanup_test_environment()