import os
from app.models.models import ExpectedBackupJob
from config.settings import settings

def get_expected_final_path(job: ExpectedBackupJob, base_validated_path: str = None) -> str:
    """
    Construit le chemin de stockage final attendu pour un fichier de sauvegarde.
    Utilise le template défini dans ExpectedBackupJob et les attributs du job.
    
    Args:
        job: Le job de sauvegarde
        base_validated_path: Chemin de base alternatif (optionnel)
        
    Returns:
        str: Le chemin complet du fichier de destination
        
    Raises:
        ValueError: Si aucun chemin de base n'est configuré
    """
    actual_base_path = base_validated_path if base_validated_path is not None else settings.VALIDATED_BACKUPS_BASE_PATH
    
    if not actual_base_path:
        raise ValueError("VALIDATED_BACKUPS_BASE_PATH n'est pas configuré dans les paramètres.")

    relative_path = job.final_storage_path_template.format(
        year=job.year,
        company_name=job.company_name,
        city=job.city,
        db_name=job.database_name
    )
    return os.path.join(actual_base_path, relative_path) 