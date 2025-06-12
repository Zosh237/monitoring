# app/utils/crypto.py
# Ce module fournit des fonctions utilitaires pour les opérations cryptographiques,
# notamment le calcul de hachages SHA256 pour les fichiers.

import hashlib
import os
import logging

logger = logging.getLogger(__name__)

class CryptoUtilityError(Exception):
    """Exception personnalisée levée en cas d'erreur lors d'une opération cryptographique."""
    pass

def calculate_file_sha256(file_path: str, chunk_size: int = 8192) -> str:
    """
    Calcule le hachage SHA256 d'un fichier volumineux en le lisant par blocs.

    Args:
        file_path (str): Le chemin complet du fichier dont le hachage doit être calculé.
        chunk_size (int): La taille des blocs (en octets) à lire à la fois. Par défaut à 8192 octets.

    Returns:
        str: Le hachage SHA256 du fichier sous forme de chaîne hexadécimale de 64 caractères.

    Raises:
        CryptoUtilityError: Si le fichier n'existe pas, est inaccessible, ou si une erreur de lecture survient.
    """
    logger.debug(f"Tentative de calcul du hachage SHA256 pour le fichier : {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Fichier non trouvé pour le calcul du hachage : '{file_path}'")
        raise CryptoUtilityError(f"Le fichier n'existe pas : '{file_path}'")
    
    if not os.path.isfile(file_path):
        logger.error(f"Le chemin spécifié n'est pas un fichier : '{file_path}'")
        raise CryptoUtilityError(f"Le chemin n'est pas un fichier : '{file_path}'")

    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:  # Ouvrir en mode lecture binaire
            # Lire le fichier par blocs et mettre à jour le hachage
            for byte_block in iter(lambda: f.read(chunk_size), b""):
                sha256_hash.update(byte_block)
        
        hex_digest = sha256_hash.hexdigest()
        logger.debug(f"Hachage SHA256 calculé pour '{file_path}' : {hex_digest}")
        return hex_digest
    except IOError as e:
        logger.error(f"Erreur de lecture du fichier '{file_path}' lors du calcul du hachage : {e}")
        raise CryptoUtilityError(f"Erreur de lecture du fichier pour le hachage : '{file_path}' - {e}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors du calcul du hachage pour '{file_path}' : {e}")
        raise CryptoUtilityError(f"Erreur inattendue lors du calcul du hachage : '{file_path}' - {e}")

