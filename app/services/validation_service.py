# app/services/validation_service.py
# Ce service est responsable de la lecture et de la validation des fichiers STATUS.json
# générés par les agents de sauvegarde.

import json
import os
import logging
from datetime import datetime, timezone, timedelta # Importe timezone et timedelta pour les checks ISO 8601

# Importe l'exception personnalisée (assurez-vous que app/core/exceptions.py existe et la définit)
# Par exemple, dans app/core/exceptions.py:
# class StatusFileValidationError(Exception):
#    pass
from app.core.exceptions import StatusFileValidationError

logger = logging.getLogger(__name__)

def validate_status_file(file_path: str) -> dict:
    """
    Lit et valide le contenu d'un fichier STATUS.json selon la structure réelle observée,
    avec une logique de permissivité ajustée.

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

    # --- Validation des champs globaux OBLIGATOIRES (structure fondamentale du rapport) ---
    # operation_start_time, operation_end_time, agent_id, overall_status, et databases sont désormais obligatoires.
    required_global_fields = ["operation_start_time", "operation_end_time", "agent_id", "overall_status", "databases"]
    for field in required_global_fields:
        if field not in status_data:
            logger.error(f"Champ global obligatoire manquant '{field}' dans STATUS.json: {file_path}")
            raise StatusFileValidationError(f"Champ global obligatoire manquant '{field}' dans STATUS.json: {file_path}")

    # Validation du champ 'overall_status'
    if status_data["overall_status"] not in ["completed", "failed_globally"]:
        logger.error(f"Valeur invalide pour 'overall_status': '{status_data['overall_status']}' dans {file_path}. Attendue 'completed' ou 'failed_globally'.")
        raise StatusFileValidationError(f"Valeur 'overall_status' invalide: {status_data['overall_status']} dans {file_path}")

    # Validation des champs de timestamp globaux (ISO 8601 UTC)
    for ts_field in ["operation_start_time", "operation_end_time"]:
        try:
            # datetime.fromisoformat supporte le 'Z' pour UTC
            dt_obj = datetime.fromisoformat(status_data[ts_field].replace('Z', '+00:00'))
            if dt_obj.tzinfo is None or dt_obj.tzinfo.utcoffset(dt_obj) != timedelta(0):
                 logger.warning(f"Le timestamp '{ts_field}' ({status_data[ts_field]}) dans {file_path} n'est pas spécifié comme UTC ou a un décalage horaire. Il devrait être en UTC.")
        except (ValueError, AttributeError): # AttributeError pour le cas où ce n'est pas une string
            logger.error(f"Format invalide pour le champ '{ts_field}' dans STATUS.json: {status_data.get(ts_field)} dans {file_path}. Attendu ISO 8601 UTC.")
            raise StatusFileValidationError(f"Format invalide pour '{ts_field}': {status_data.get(ts_field)} dans {file_path}. Attendu ISO 8601 UTC.")

    # Validation de agent_id (doit être une chaîne)
    if not isinstance(status_data["agent_id"], str):
        logger.error(f"Le champ 'agent_id' n'est pas une chaîne de caractères dans {file_path}.")
        raise StatusFileValidationError(f"Le champ 'agent_id' doit être une chaîne dans {file_path}.")

    # Validation de la section 'databases'
    if not isinstance(status_data["databases"], dict):
        logger.error(f"Le champ 'databases' dans STATUS.json n'est pas un dictionnaire: {file_path}")
        raise StatusFileValidationError(f"Le champ 'databases' doit être un dictionnaire dans {file_path}")

    if not status_data["databases"]:
        logger.warning(f"La section 'databases' est vide dans STATUS.json: {file_path}. Cela peut indiquer un problème, mais non bloquant pour la validation de la structure.")

    # Validation de la structure de chaque entrée de base de données (plus permissive sur les détails des processus)
    # Les clés de processus sont maintenant en majuscules
    db_process_keys = ["BACKUP", "COMPRESS", "TRANSFER"]
    for db_name, db_data in status_data["databases"].items():
        if not isinstance(db_data, dict):
            logger.error(f"L'entrée pour la base de données '{db_name}' dans STATUS.json n'est pas un dictionnaire: {file_path}")
            raise StatusFileValidationError(f"Entrée BD '{db_name}' invalide dans {file_path}")
        
        # Le champ 'staged_file_name' est obligatoire au niveau de la BD
        if "staged_file_name" not in db_data or not isinstance(db_data["staged_file_name"], str):
            logger.error(f"Champ 'staged_file_name' manquant ou invalide pour la BD '{db_name}' dans STATUS.json: {file_path}")
            raise StatusFileValidationError(f"Champ 'staged_file_name' manquant/invalide pour BD '{db_name}' dans {file_path}")

        for process_key in db_process_keys:
            # Chaque bloc de processus (BACKUP, COMPRESS, TRANSFER) est OBLIGATOIRE
            if process_key not in db_data or not isinstance(db_data[process_key], dict):
                logger.error(f"Processus obligatoire manquant ou invalide '{process_key}' pour la BD '{db_name}' dans STATUS.json: {file_path}")
                raise StatusFileValidationError(f"Processus '{process_key}' manquant/invalide pour BD '{db_name}' dans {file_path}")

            process_data = db_data[process_key]
            
            # Le champ 'status' est obligatoire à l'intérieur de chaque processus
            if "status" not in process_data or not isinstance(process_data["status"], bool):
                logger.error(f"Statut obligatoire manquant ou invalide dans le processus '{process_key}' pour la BD '{db_name}' dans STATUS.json: {file_path}")
                raise StatusFileValidationError(f"Statut '{process_key}' manquant/invalide pour BD '{db_name}' dans {file_path}")
            
            # Validation des timestamps de processus (start_time, end_time) - optionnels mais si présents, format valide
            for proc_ts_field in ["start_time", "end_time"]:
                if proc_ts_field in process_data and process_data[proc_ts_field] is not None:
                    try:
                        datetime.fromisoformat(process_data[proc_ts_field].replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        logger.warning(f"Format timestamp invalide dans '{process_key}.{proc_ts_field}' pour BD '{db_name}' dans {file_path}: {process_data.get(proc_ts_field)}. Non bloquant.")

            # Validation des checksum et size (si présents, format valide)
            if "sha256_checksum" in process_data and process_data["sha256_checksum"] is not None:
                if not isinstance(process_data["sha256_checksum"], str) or len(process_data["sha256_checksum"]) != 64:
                    logger.warning(f"Format ou longueur invalide pour 'sha256_checksum' dans '{process_key}' pour BD '{db_name}' dans {file_path}: {process_data.get('sha256_checksum')}. Non bloquant.")
            
            if "size" in process_data and process_data["size"] is not None:
                if not isinstance(process_data["size"], int) or process_data["size"] < 0:
                    logger.warning(f"Valeur ou type invalide pour 'size' dans '{process_key}' pour BD '{db_name}' dans {file_path}: {process_data.get('size')}. Non bloquant.")
            
            # error_message pour TRANSFER est optionnel
            if process_key == "TRANSFER" and "error_message" in process_data and process_data["error_message"] is not None and not isinstance(process_data["error_message"], str):
                 logger.warning(f"Le champ 'error_message' du processus TRANSFER n'est pas une chaîne de caractères dans {file_path}. Non bloquant.")


    logger.info(f"Fichier STATUS.json validé avec succès (structure globale permissive) : {file_path}. Statut global: {status_data['overall_status']}")
    return status_data
