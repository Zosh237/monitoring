class BackupManagerError(Exception):
    pass

def promote_backup(staged_db_file_path, job):
    """Mock de promotion: supprime le fichier stagé pour simuler la promotion."""
    import os
    if os.path.exists(staged_db_file_path):
        os.remove(staged_db_file_path)
    # Retourne un chemin simulé de promotion
    return f"/mock/promoted/{job.database_name}.sql.gz"
