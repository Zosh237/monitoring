import json
import os
import logging
from datetime import datetime
from app.core.exceptions import StatusFileValidationError

# Obtenir une instance de logger pour ce module.
# Le nom 'app.services.validation_service' correspond à la hiérarchie de votre logger définie dans logging.yaml.
logger = logging.getLogger(__name__)



def validate_status_file(file_path: str) -> dict:
    """
    Lit et valide le contenu d'un fichier STATUS.json
    
    Args: 
        file_path (str): Le chemin absolu vers le fichier STATUS.json à valider.

    Returns:
        dict: Un dictionnaire contenant les données du STATUS.json si la validation réussit.

    Raises:
        StatusFileValidationError: Si le fichier est manquant, malformé, ou si des champs obligatoires sont absents/invalides.
    """
    logger.debug(f"Essaie de validation du fichier STATUS.json : {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Le fichier STATUS.json n'a pas été trouvé dans l'arborescence: {file_path}")
        raise StatusFileValidationError(f"STATUS.json n'a pas été trouvé: {file_path}")

    #Lecture du fichier JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        logger.debug(f"Successfully loaded JSON from {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in {file_path}: {e}")
        raise StatusFileValidationError(f"Invalid JSON format: {file_path} - {e}")
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        raise StatusFileValidationError(f"Error reading file: {file_path} - {e}")

    # Validation des champs obligatoires
    required_fields = ["status", "timestamp", "file_name", "file_size_bytes", "checksum_sha256"]
    for field in required_fields:
        if field not in status_data:
            logger.error(f"Missing required field '{field}' in STATUS.json: {file_path}")
            raise StatusFileValidationError(f"Missing required field '{field}' in STATUS.json: {file_path}")

    # Validation du champ 'status'
    if status_data["status"] not in ["success", "failed"]:
        logger.error(f"Invalid 'status' value '{status_data['status']}' in STATUS.json: {file_path}")
        raise StatusFileValidationError(f"Invalid 'status' value: {status_data['status']} in {file_path}")

    # Validation du champ 'timestamp' (format ISO 8601 UTC)
    try:
        # Essayer de parser le timestamp pour s'assurer qu'il est valide
        # Le 'Z' à la fin indique UTC. datetime.fromisoformat supporte cela.
        datetime.fromisoformat(status_data["timestamp"].replace('Z', '+00:00'))
    except ValueError:
        logger.error(f"Invalid 'timestamp' format in STATUS.json: {status_data['timestamp']} in {file_path}. Expected ISO 8601 UTC.")
        raise StatusFileValidationError(f"Invalid 'timestamp' format: {status_data['timestamp']} in {file_path}. Expected ISO 8601 UTC.")

    # Validation du champ 'file_size_bytes' (doit être un entier positif)
    if not isinstance(status_data["file_size_bytes"], int) or status_data["file_size_bytes"] < 0:
        logger.error(f"Invalid 'file_size_bytes' value or type: {status_data['file_size_bytes']} in {file_path}. Expected a positive integer.")
        raise StatusFileValidationError(f"Invalid 'file_size_bytes': {status_data['file_size_bytes']} in {file_path}")

    # Validation du champ 'checksum_sha256' (doit être une chaîne de 64 caractères hexadécimaux)
    # Une expression régulière plus robuste pourrait être utilisée pour vérifier le format hexadécimal.
    if not isinstance(status_data["checksum_sha256"], str) or len(status_data["checksum_sha256"]) != 64:
        logger.error(f"Invalid 'checksum_sha256' format or length: {status_data['checksum_sha256']} in {file_path}. Expected a 64-char string.")
        raise StatusFileValidationError(f"Invalid 'checksum_sha256': {status_data['checksum_sha256']} in {file_path}")

    # Si le statut est 'failed', le champ 'error_message' est fortement recommandé.
    if status_data["status"] == "failed" and "error_message" not in status_data:
        logger.warning(f"Missing recommended field 'error_message' for 'failed' status in STATUS.json: {file_path}")
        # Note: Nous ne levons pas d'exception ici car ce n'est que recommandé, pas obligatoire.

    logger.info(f"STATUS.json file validated successfully: {file_path}. Status: {status_data['status']}")
    return status_data
