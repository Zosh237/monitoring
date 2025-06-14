import os
import shutil
from datetime import datetime
from config.settings import settings

class BackupManagerError(Exception):
    pass

def promote_backup(staged_db_file_path, job):
    """
    Copie le fichier de sauvegarde validé vers la zone de stockage final avec un nom horodaté.
    Le fichier original dans la zone de staging reste en place.
    """
    try:
        # Construire le chemin de destination avec la structure YEAR/COMPANY/CITY/NEIGHBORHOOD/DB_NAME
        destination_dir = os.path.join(
            settings.VALIDATED_BACKUPS_BASE_PATH,
            str(job.year),
            job.company_name,
            job.city,
            job.neighborhood,
            job.database_name
        )
        os.makedirs(destination_dir, exist_ok=True)

        # Générer le nom du fichier avec horodatage
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination_filename = f"{job.database_name}_{timestamp}.sql.gz"
        destination_path = os.path.join(destination_dir, destination_filename)

        # Copier le fichier
        shutil.copy2(staged_db_file_path, destination_path)
        
        return destination_path
    except Exception as e:
        raise BackupManagerError(f"Erreur lors de la promotion du fichier : {str(e)}")
