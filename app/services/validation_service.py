import json
import os
import logging
from datetime import datetime, timezone, timedelta # Importe timezone et timedelta pour les checks ISO 8601
from app.core.exceptions import StatusFileValidationError

logger = logging.getLogger(__name__)

def validate_status_file(file_path: str) -> dict:
    """
    Lit et valide le contenu d'un fichier STATUS.json selon la nouvelle structure globale.
    Il vérifie la présence des champs globaux et la structure de base des entrées de bases de données.
    La validation détaillée des champs de processus individuels (checksum, size) est effectuée par le scanner.
    
    Args: 
        file_path (str): Le chemin absolu vers le fichier STATUS.json à valider.

    Returns:
        dict: Un dictionnaire contenant les données du STATUS.json si la validation réussit.

    Raises:
        StatusFileValidationError: Si le fichier est manquant, malformé, ou si des champs obligatoires sont absents/invalides.
    """
    logger.debug(f"Tentative de validation du fichier STATUS.json : {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"Le fichier STATUS.json n'a pas été trouvé : {file_path}")
        raise StatusFileValidationError(f"STATUS.json n'a pas été trouvé : {file_path}")

    # Lecture du fichier JSON
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
        logger.debug(f"Contenu JSON chargé avec succès depuis {file_path}")
    except json.JSONDecodeError as e:
        logger.error(f"Format JSON invalide dans {file_path}: {e}")
        raise StatusFileValidationError(f"Format JSON invalide : {file_path} - {e}")
    except Exception as e:
        logger.error(f"Erreur de lecture du fichier {file_path}: {e}")
        raise StatusFileValidationError(f"Erreur de lecture du fichier : {file_path} - {e}")

    # --- Validation des champs obligatoires globaux ---
    required_global_fields = ["operation_start_time", "operation_timestamp", "agent_id", "overall_status", "databases"]
    for field in required_global_fields:
        if field not in status_data:
            logger.error(f"Champ global obligatoire manquant '{field}' dans STATUS.json: {file_path}")
            raise StatusFileValidationError(f"Champ global obligatoire manquant '{field}' dans STATUS.json: {file_path}")

    # Validation du champ 'overall_status'
    if status_data["overall_status"] not in ["completed", "failed_globally"]:
        logger.error(f"Valeur invalide pour 'overall_status': '{status_data['overall_status']}' dans {file_path}. Attendue 'completed' ou 'failed_globally'.")
        raise StatusFileValidationError(f"Valeur 'overall_status' invalide: {status_data['overall_status']} dans {file_path}")

    # Validation des champs de timestamp globaux (ISO 8601 UTC)
    for ts_field in ["operation_start_time", "operation_timestamp"]:
        try:
            # datetime.fromisoformat supporte le 'Z' pour UTC à partir de Python 3.11,
            # pour une meilleure compatibilité, on peut remplacer 'Z' par '+00:00'
            dt_obj = datetime.fromisoformat(status_data[ts_field].replace('Z', '+00:00'))
            # S'assurer que le timestamp est bien en UTC
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) != timedelta(0):
                 logger.warning(f"Le timestamp '{ts_field}' ({status_data[ts_field]}) dans {file_path} n'est pas spécifié comme UTC ou a un décalage horaire. Il devrait être en UTC.")
        except ValueError:
            logger.error(f"Format invalide pour le champ '{ts_field}' dans STATUS.json: {status_data[ts_field]} dans {file_path}. Attendu ISO 8601 UTC.")
            raise StatusFileValidationError(f"Format invalide pour '{ts_field}': {status_data[ts_field]} dans {file_path}. Attendu ISO 8601 UTC.")

    # Validation de la section 'databases'
    if not isinstance(status_data["databases"], dict):
        logger.error(f"Le champ 'databases' dans STATUS.json n'est pas un dictionnaire: {file_path}")
        raise StatusFileValidationError(f"Le champ 'databases' doit être un dictionnaire dans {file_path}")

    if not status_data["databases"]:
        logger.warning(f"La section 'databases' est vide dans STATUS.json: {file_path}. Cela peut indiquer un problème.")

    # Validation de la structure de chaque entrée de base de données (légère)
    db_process_keys = ["backup_process", "compress_process", "transfer_process"]
    for db_name, db_data in status_data["databases"].items():
        if not isinstance(db_data, dict):
            logger.error(f"L'entrée pour la base de données '{db_name}' dans STATUS.json n'est pas un dictionnaire: {file_path}")
            raise StatusFileValidationError(f"Entrée BD '{db_name}' invalide dans {file_path}")
        
        for process_key in db_process_keys:
            if process_key not in db_data or not isinstance(db_data[process_key], dict):
                logger.error(f"Processus obligatoire manquant ou invalide '{process_key}' pour la BD '{db_name}' dans STATUS.json: {file_path}")
                raise StatusFileValidationError(f"Processus '{process_key}' manquant/invalide pour BD '{db_name}' dans {file_path}")
            
            # Chaque processus devrait avoir au moins un statut booléen
            if "status" not in db_data[process_key] or not isinstance(db_data[process_key]["status"], bool):
                logger.error(f"Statut obligatoire manquant ou invalide dans le processus '{process_key}' pour la BD '{db_name}' dans STATUS.json: {file_path}")
                raise StatusFileValidationError(f"Statut '{process_key}' manquant/invalide pour BD '{db_name}' dans {file_path}")

    logger.info(f"Fichier STATUS.json validé avec succès (structure globale) : {file_path}. Statut global: {status_data['overall_status']}")
    return status_data

