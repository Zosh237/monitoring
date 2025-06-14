Objectif : Mettre à jour les fichiers Python app/services/scanner.py et test_scanner.py pour refléter la nouvelle logique de gestion des fichiers de sauvegarde réussis. Désormais, un fichier de sauvegarde validé (statut SUCCESS) dans la zone de staging doit être copié vers la zone de stockage final (/mnt/backups/validated) avec un nom horodaté, et non déplacé ou supprimé de la zone de staging. Le fichier dans la zone de staging doit rester en place pour les synchronisations rsync futures par l'agent.

Contexte Important :
app/utils/file_operations.py contient maintenant une fonction copy_file(source_path, destination_path) qui effectue une copie et non un déplacement.

app/services/backup_manager.py a été mis à jour pour utiliser copy_file et nomme les fichiers promus avec un horodatage (ex: db_name_YYYYMMDD_HHMMSS.sql.gz).

Modifications Requises :
1. Fichier : app/services/scanner.py
Action : Modifier la méthode _perform_post_scan_actions(self, job: ExpectedBackupJob, entry_status: BackupEntryStatus, staged_db_file_path: str).

Détails :

Lorsque entry_status == BackupEntryStatus.SUCCESS, la ligne suivante qui supprime le fichier stagé doit être commentée ou supprimée :

# Ancien comportement (à supprimer/commenter pour succès):
# delete_file(staged_db_file_path)

Raison : Le fichier de base de données dans la zone de staging (staged_db_file_path) doit persister car il représente la version la plus récente synchronisée par l'agent et servira de base pour les prochaines synchronisations rsync incrémentales. Seule une copie est faite vers la zone validated.

2. Fichier : test_scanner.py
Actions : Mettre à jour les assertions dans la fonction run_tests() pour les scénarios de succès.

Détails :

Scénario 1 (SCÉNARIO 1: Sauvegarde SUCCESS pour un site avec deux BDs (cycle 13h)) :

Pour db1 et db2 :

Modifier l'assertion de suppression du fichier stagé pour vérifier sa présence :

# Ancien: assert not os.path.exists(staged_db_path_db1)
# Nouveau:
assert os.path.exists(staged_db_path_db1) # Fichier stagé doit rester présent
print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 1.1 (db1_13h) validé. Statut: {{getattr(updated_job_db1.current_status, 'value', updated_job_db1.current_status)}}, Entrée: {{getattr(latest_entry_db1.status, 'value', latest_entry_db1.status)}}. Fichier stagé PRÉSENT.")

Ajouter une nouvelle assertion pour vérifier que le fichier a été copié dans le répertoire VALIDATED_BACKUPS_BASE_PATH avec un nom horodaté.

# Exemple pour db1:
promoted_file_name_db1_pattern = rf"{job_site1_db1.database_name}_\d{{8}}_\d{{6}}\.sql\.gz$"
destination_dir_db1 = os.path.join(app_settings.VALIDATED_BACKUPS_BASE_PATH, str(job_site1_db1.year), job_site1_db1.company_name, job_site1_db1.city, job_site1_db1.neighborhood, job_site1_db1.database_name)

# Lister les fichiers dans le dossier de destination et vérifier le pattern
promoted_files_db1 = [f for f in os.listdir(destination_dir_db1) if re.match(promoted_file_name_db1_pattern, f)]
assert len(promoted_files_db1) == 1 # Un seul fichier horodaté attendu
assert os.path.exists(os.path.join(destination_dir_db1, promoted_files_db1[0]))
print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Fichier promu db1_13h trouvé à : {{os.path.join(destination_dir_db1, promoted_files_db1[0])}}")

(Appliquer une logique similaire pour db2.)

Scénario 3 (SCÉNARIO 3: Sauvegarde FAILED pour une BD spécifique + SUCCESS pour une autre (même site/rapport)) :

Pour la BD en succès (db_success_site3) :

Modifier l'assertion de suppression du fichier stagé pour vérifier sa présence :

# Ancien: assert not os.path.exists(staged_db_path_success_site3)
# Nouveau:
assert os.path.exists(staged_db_path_success_site3) # Fichier stagé doit rester présent
print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Scénario 3.2 (BD réussie) validé. Statut: {{getattr(updated_job_success_site3.current_status, 'value', updated_job_success_site3.current_status)}}, Entrée: {{getattr(latest_entry_success_site3.status, 'value', latest_entry_success_site3.status)}}. Fichier stagé PRÉSENT.")

Ajouter une nouvelle assertion pour vérifier que le fichier a été copié dans le répertoire VALIDATED_BACKUPS_BASE_PATH avec un nom horodaté.

# Exemple pour db_success_site3:
promoted_file_name_success_site3_pattern = rf"{job_site3_db_success.database_name}_\d{{8}}_\d{{6}}\.sql\.gz$"
destination_dir_success_site3 = os.path.join(app_settings.VALIDATED_BACKUPS_BASE_PATH, str(job_site3_db_success.year), job_site3_db_success.company_name, job_site3_db_success.city, job_site3_db_success.neighborhood, job_site3_db_success.database_name)

promoted_files_success_site3 = [f for f in os.listdir(destination_dir_success_site3) if re.match(promoted_file_name_success_site3_pattern, f)]
assert len(promoted_files_success_site3) == 1
assert os.path.exists(os.path.join(destination_dir_success_site3, promoted_files_success_site3[0]))
print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Fichier promu pour db_success_site3 trouvé à : {{os.path.join(destination_dir_success_site3, promoted_files_success_site3[0])}}")

Ces modifications garantiront que le comportement du scanner et de ses tests est en parfaite adéquation avec la nouvelle stratégie de gestion des fichiers de sauvegarde.