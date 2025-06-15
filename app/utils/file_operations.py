# app/utils/file_operations.py
# Ce module fournit des fonctions utilitaires pour la manipulation sécurisée des fichiers
# et des répertoires sur le système de stockage du serveur.

import os
import shutil # Pour des opérations de haut niveau sur les fichiers, comme le déplacement
import logging

# Obtenir une instance de logger pour ce module.
logger = logging.getLogger(__name__)

class FileOperationError(Exception):
    """Exception personnalisée levée en cas d'erreur lors d'une opération sur fichier."""
    pass

def ensure_directory_exists(path: str) -> None:
    """
    S'assure qu'un répertoire existe. Le crée, y compris les parents, si nécessaire.

    Args:
        path (str): Le chemin du répertoire à créer.

    Raises:
        FileOperationError: Si le répertoire ne peut pas être créé pour une raison inattendue.
    """
    logger.debug(f"Vérification/création du répertoire : {path}")
    try:
        os.makedirs(path, exist_ok=True) # exist_ok=True évite une erreur si le répertoire existe déjà
        logger.debug(f"Répertoire assuré : {path}")
    except OSError as e:
        logger.error(f"Erreur lors de la création du répertoire '{path}': {e}")
        raise FileOperationError(f"Impossible de créer le répertoire '{path}': {e}")


def move_file(source_path: str, destination_path: str) -> None:
    """
    Déplace un fichier de la source à la destination.
    Utilise os.replace pour une opération atomique sur le même système de fichiers.
    Se rabat sur shutil.move si os.replace échoue (ex: systèmes de fichiers différents).

    Args:
        source_path (str): Le chemin du fichier source.
        destination_path (str): Le chemin complet de la destination (incluant le nouveau nom de fichier).

    Raises:
        FileOperationError: Si le fichier source n'existe pas, ou si le déplacement échoue.
    """
    logger.debug(f"Tentative de déplacement du fichier de '{source_path}' vers '{destination_path}'")

    if not os.path.exists(source_path):
        logger.error(f"Le fichier source n'existe pas pour le déplacement : '{source_path}'")
        raise FileOperationError(f"Le fichier source n'existe pas : '{source_path}'")

    # S'assurer que le répertoire de destination existe
    destination_dir = os.path.dirname(destination_path)
    if destination_dir: # Si la destination_path inclut un répertoire
        try:
            ensure_directory_exists(destination_dir)
        except FileOperationError as e:
            logger.error(f"Impossible de préparer le répertoire de destination pour le déplacement : {e}")
            raise FileOperationError(f"Impossible de préparer le répertoire de destination '{destination_dir}' pour le déplacement.")

    try:
        # Tenter d'utiliser os.replace pour une opération atomique.
        # os.replace écrasera la destination si elle existe.
        os.replace(source_path, destination_path)
        logger.info(f"Fichier déplacé atomiquement : '{source_path}' -> '{destination_path}'")
    except OSError as e:
        # os.replace échoue si les chemins ne sont pas sur le même système de fichiers
        # ou pour d'autres erreurs spécifiques. Dans ce cas, se rabattre sur shutil.move.
        logger.warning(f"os.replace a échoué pour '{source_path}' vers '{destination_path}' ({e}). Utilisation de shutil.move.")
        try:
            shutil.move(source_path, destination_path)
            logger.info(f"Fichier déplacé avec shutil.move : '{source_path}' -> '{destination_path}'")
        except shutil.Error as se:
            logger.error(f"shutil.move a échoué pour '{source_path}' vers '{destination_path}' : {se}")
            raise FileOperationError(f"Échec du déplacement du fichier '{source_path}' vers '{destination_path}': {se}")
        except Exception as se: # Attrape d'autres erreurs potentielles de shutil.move
            logger.error(f"Erreur inattendue lors du déplacement avec shutil.move de '{source_path}' vers '{destination_path}' : {se}")
            raise FileOperationError(f"Échec du déplacement du fichier '{source_path}' vers '{destination_path}': {se}")
    except Exception as e: # Attrape d'autres erreurs inattendues d'os.replace
        logger.error(f"Erreur inattendue lors du déplacement avec os.replace de '{source_path}' vers '{destination_path}' : {e}")
        raise FileOperationError(f"Échec du déplacement du fichier '{source_path}' vers '{destination_path}': {e}")


def create_dummy_file(file_path: str, content: bytes = b"dummy content"):
    """
    Crée un fichier factice avec un contenu donné. Utile pour les tests.

    Args:
        file_path (str): Le chemin complet du fichier à créer.
        content (bytes): Le contenu binaire à écrire dans le fichier.

    Raises:
        FileOperationError: Si la création du fichier échoue.
    """
    try:
        # S'assurer que le répertoire parent existe avant de créer le fichier
        ensure_directory_exists(os.path.dirname(file_path))
        with open(file_path, "wb") as f:
            f.write(content)
        logger.debug(f"Fichier factice créé : {file_path} (taille: {len(content)} octets)")
    except Exception as e:
        logger.error(f"Échec de la création du fichier factice '{file_path}': {e}")
        raise FileOperationError(f"Impossible de créer le fichier factice '{file_path}': {e}")

def copy_file(source_path: str, destination_path: str):
    """
    Copie un fichier de l'emplacement source vers l'emplacement de destination.
    Écrase le fichier de destination s'il existe déjà.

    Args:
        source_path (str): Le chemin absolu du fichier source.
        destination_path (str): Le chemin absolu où le fichier doit être copié.

    Raises:
        FileOperationError: Si la copie échoue.
    """
    logger.debug(f"Tentative de copie du fichier de '{source_path}' vers '{destination_path}'")
    if not os.path.exists(source_path):
        logger.error(f"Fichier source non trouvé pour la copie : {source_path}")
        raise FileOperationError(f"Fichier source non trouvé : {source_path}")
    
    # Assurer que le répertoire de destination existe avant de copier
    destination_dir = os.path.dirname(destination_path)
    ensure_directory_exists(destination_dir)

    try:
        shutil.copy2(source_path, destination_path) # copy2 préserve les métadonnées du fichier
        logger.info(f"Fichier copié avec succès : '{source_path}' -> '{destination_path}'")
    except shutil.Error as e:
        logger.error(f"Erreur de copie de fichier de '{source_path}' vers '{destination_path}': {e}")
        raise FileOperationError(f"Échec de la copie du fichier : {e}")
    except OSError as e:
        logger.error(f"Erreur système lors de la copie de fichier de '{source_path}' vers '{destination_path}': {e}")
        raise FileOperationError(f"Erreur système lors de la copie du fichier : {e}")
    except Exception as e:
        logger.critical(f"Erreur inattendue lors de la copie de '{source_path}' vers '{destination_path}': {e}", exc_info=True)
        raise FileOperationError(f"Erreur interne lors de la copie du fichier : {e}")


def delete_file(file_path: str) -> None:
    """
    Supprime un fichier.

    Args:
        file_path (str): Le chemin du fichier à supprimer.

    Raises:
        FileOperationError: Si le fichier n'existe pas ou si la suppression échoue.
    """
    logger.debug(f"Tentative de suppression du fichier : {file_path}")
    if not os.path.exists(file_path):
        logger.warning(f"Tentative de suppression d'un fichier non existant : '{file_path}'. Opération ignorée.")
        return # Ne lève pas d'erreur si le fichier n'existe pas déjà pour la suppression.

    try:
        os.remove(file_path)
        logger.info(f"Fichier supprimé : '{file_path}'")
    except OSError as e:
        logger.error(f"Erreur lors de la suppression du fichier '{file_path}' : {e}")
        raise FileOperationError(f"Impossible de supprimer le fichier '{file_path}' : {e}")
