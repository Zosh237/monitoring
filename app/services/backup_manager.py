# app/services/backup_manager.py

import os
import logging
from datetime import datetime

from app.models.models import ExpectedBackupJob
import app.utils.file_operations as file_ops
from app.utils.path_utils import get_expected_final_path
from config.settings import settings

logger = logging.getLogger(__name__)

class BackupManagerError(Exception):
    """Exception personnalisée pour les erreurs du gestionnaire de sauvegardes."""
    pass

def promote_backup(staged_file_path: str, job: ExpectedBackupJob, base_validated_path: str = None) -> str:
    """
    Copie un fichier de sauvegarde validé de la zone de staging
    vers son emplacement de stockage final et permanent.
    Si un fichier du même nom existe déjà à destination, il sera remplacé.
    Le fichier dans la zone de staging n'est PAS supprimé.
    """
    try:
        logger.debug(f"promote_backup: Début de la promotion pour le job '{job.database_name}'")
        logger.debug(f"promote_backup: Fichier stagé d'origine : '{staged_file_path}'")
        logger.debug(f"promote_backup: Valeurs du job - Année='{job.year}', Société='{job.company_name}', Ville='{job.city}', DB='{job.database_name}'")
        logger.debug(f"promote_backup: Template de stockage final : '{job.final_storage_path_template}'")

        destination_file_path = get_expected_final_path(job, base_validated_path)
        destination_dir = os.path.dirname(destination_file_path)

        logger.debug(f"promote_backup: Répertoire de destination calculé : '{destination_dir}'")
        logger.debug(f"promote_backup: Chemin final du fichier de destination calculé : '{destination_file_path}'")

        file_ops.ensure_directory_exists(destination_dir)
        logger.debug(f"promote_backup: Répertoire de destination assuré : '{destination_dir}'")

        file_ops.copy_file(staged_file_path, destination_file_path)
        logger.info(f"Sauvegarde pour '{job.database_name}' copiée avec succès de '{staged_file_path}' vers '{destination_file_path}'.")

        return destination_file_path

    except file_ops.FileOperationError as e:
        logger.error(f"Échec de la promotion (copie) de la sauvegarde pour '{job.database_name}'. Erreur de fichier : {e}")
        raise BackupManagerError(f"Échec de la promotion (copie) de la sauvegarde : {e}")
    except Exception as e:
        logger.critical(f"Erreur inattendue lors de la promotion (copie) de la sauvegarde pour '{job.database_name}' : {e}", exc_info=True)
        raise BackupManagerError(f"Erreur interne lors de la promotion (copie) : {e}")

def cleanup_old_backups(job: ExpectedBackupJob, retention_count: int):
    logger.debug(f"Nettoyage des anciennes sauvegardes pour le job {job.database_name} - Fonctionnalité non implémentée (rétention par écrasement).")
    pass
