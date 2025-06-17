Début

1. Parcourir le dossier racine (BACKUP_STORAGE_ROOT) :
   Pour chaque sous-dossier "agent" dans ce dossier racine :
   
   1.1. Définir :
        - chemin_log = "agent/log"            // Dossier contenant les fichiers JSON
        - chemin_databases = "agent/databases" // Dossier contenant les backups de l'agent

   1.2. Pour chaque fichier JSON dans chemin_log :
       
       1.2.1. Charger le fichier JSON (ex: "HORODATAGE_ENTREPRISE_VILLE_QUARTIER.json")
              - Cette opération permet d'extraire le dictionnaire "databases" du rapport, qui contient :
                   • Pour chaque clé (nom de base de données),
                     - staged_file_name
                     - Informations sur les opérations BACKUP, COMPRESS, TRANSFER
                     - Plus précisément, le hash attendu "sha256_checksum" de la section COMPRESS
       
       1.2.2. Récupérer et, si nécessaire, extraire les informations contextuelles depuis le nom du fichier
              (extraction de l'ENTREPRISE, VILLE, QUARTIER) pour filtrer les ExpectedBackupJob actifs depuis la base.
       
       1.2.3. Dans la base, filtrer les ExpectedBackupJob actifs qui correspondent aux critères (ENTREPRISE, VILLE, QUARTIER)
              (ou utiliser directement la correspondance entre job.database_name et la clé dans JSON).
       
       1.2.4. Pour chaque ExpectedBackupJob filtré (job actif) :
       
             Si job.database_name existe dans le dictionnaire "databases" du JSON :
             
               1.2.4.1. Récupérer le sous-dictionnaire associé à cette clé :
                        - staged_file_name (nom complet du fichier backup)
                        - expected_hash = hash (issu de la section COMPRESS, champ "sha256_checksum")
               
               1.2.4.2. Construire le chemin complet du fichier backup dans chemin_databases (ex: chemin_databases/staged_file_name)
               
               1.2.4.3. Si le fichier backup existe :
                          - Calculer le hash du fichier (computed_hash).
                          - Comparaison :
                               • Si computed_hash ≠ expected_hash :
                                     → Marquer job.current_status = "FAILED"
                                     → Créer une BackupEntry indiquant l'erreur de hash
                               • Sinon, si computed_hash == expected_hash :
                                     → Comparer computed_hash avec job.calculated_hash (hash enregistré lors d’un scan antérieur):
                                           - S'il n'existe pas encore ou si computed_hash diffère de job.calculated_hash :
                                                 → Mettre à jour job.calculated_hash avec computed_hash
                                                 → Marquer job.current_status = "SUCCESS"
                                                 → Créer une BackupEntry indiquant "Backup validé et mis à jour."
                                           - Sinon (computed_hash identique à job.calculated_hash) :
                                                 → Marquer job.current_status = "HASH_MISMATCH"
                                                 → Créer une BackupEntry indiquant que le backup n'a pas évolué entre deux scans.
               
               1.2.4.4. Mettre à jour job.last_checked_timestamp avec la date/heure actuelle.
               
               1.2.4.5. Ajouter la mise à jour dans la session de base de données.
             
             Sinon (la clé job.database_name n'est pas présente dans le dictionnaire "databases") :
                - Marquer job.current_status = "MISSING"
                - Mettre à jour job.last_checked_timestamp.
                - Créer une BackupEntry avec le statut "MISSING" et un message explicatif.
       
       1.2.5. Après le traitement de tous les jobs relatifs à ce fichier JSON, effectuer un commit sur la base.
       
       1.2.6. Archiver le rapport JSON :
                - Déplacer le fichier JSON traité vers un sous-dossier "_archive" du dossier log.
   
2. Fin pour chaque agent

Fin
