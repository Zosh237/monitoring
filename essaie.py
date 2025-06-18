def process_expected_job(job, databases_data, agent_databases_folder, agent_id, operation_log_file_name, agent_status, db_session):
    """
    Traite un ExpectedBackupJob à partir des informations fournies dans databases_data (extrait du JSON).
    
    Pour le job correspondant, la logique est la suivante :
      - Si la clé job.database_name est présente dans databases_data :
          1. Extraire staged_file_name et expected_hash (issu de la section COMPRESS).
          2. Vérifier l'existence du fichier backup dans agent_databases_folder.
             a. Si présent, calculer le hash.
                • Si computed_hash != expected_hash → job = FAILED.
                • Si computed_hash == expected_hash :
                    - Si aucun hash n'est enregistré ou si computed_hash diffère du hash stocké → job = SUCCESS.
                    - Sinon, si computed_hash est identique au hash déjà enregistré → job = HASH_MISMATCH.
             b. Sinon → job = MISSING.
      - Sinon → job = MISSING.
      
    Dans tous les cas, une entrée BackupEntry appropriée est créée,
    et une notification est envoyée si le statut n'est pas SUCCESS.
    """
    now = datetime.now(timezone.utc)
    computed_hash = None
    staged_file_name = None
    message = ""
    status = ""
    backup_file_path = None

    if job.database_name in databases_data:
        data = databases_data[job.database_name]
        staged_file_name = data.get("staged_file_name")
        compress_section = data.get("COMPRESS", {})
        expected_hash = compress_section.get("sha256_checksum")
        backup_file_path = os.path.join(agent_databases_folder, staged_file_name)
        if os.path.exists(backup_file_path):
            try:
                computed_hash = calculate_file_sha256(backup_file_path)
            except Exception as err:
                job.current_status = "FAILED"
                job.error_message = f"Erreur lors du calcul du hash: {err}"
                job.last_checked_timestamp = now
                backup_entry = BackupEntry(
                    expected_job_id=job.id,
                    timestamp=now,
                    status="FAILED",
                    message=job.error_message,
                    calculated_hash=""
                )
                db_session.add(job)
                db_session.add(backup_entry)
                send_notification(job, job.error_message)
                return

            if computed_hash != expected_hash:
                job.current_status = "FAILED"
                message = "Hash calculé différent du hash attendu."
            else:
                # Le hash correspond ; on vérifie s'il a changé depuis le dernier scan.
                if job.calculated_hash is None or job.calculated_hash != computed_hash:
                    job.current_status = "SUCCESS"
                    job.calculated_hash = computed_hash
                    message = "Backup validé et mis à jour."
                else:
                    job.current_status = "HASH_MISMATCH"
                    message = "Backup inchangé entre deux scans (HASH_MISMATCH)."
            job.last_checked_timestamp = now
            backup_entry = BackupEntry(
                expected_job_id=job.id,
                timestamp=now,
                status=job.current_status,
                message=message,
                calculated_hash=computed_hash
            )
            db_session.add(job)
            db_session.add(backup_entry)
            if job.current_status == "SUCCESS":
                # Copier le backup validé vers l'espace de validation.
                validated_backup_path = os.path.join(settings.VALIDATED_BACKUPS_BASE_PATH, staged_file_name)
                try:
                    shutil.copy2(backup_file_path, validated_backup_path)
                except Exception as err:
                    job.current_status = "FAILED"
                    job.error_message = f"Erreur lors de la copie: {err}"
                    backup_entry.message += " / Copie échouée."
                    db_session.add(job)
                    db_session.add(backup_entry)
                    send_notification(job, job.error_message)
                    return
            if job.current_status != "SUCCESS":
                send_notification(job, message)
        else:
            job.current_status = "MISSING"
            job.last_checked_timestamp = now
            backup_entry = BackupEntry(
                expected_job_id=job.id,
                timestamp=now,
                status="MISSING",
                message=f"Fichier backup introuvable: {staged_file_name}",
                calculated_hash=computed_hash if computed_hash else "",
            )
            db_session.add(job)
            db_session.add(backup_entry)
            send_notification(job, backup_entry.message)
    else:
        job.current_status = "MISSING"
        job.last_checked_timestamp = now
        backup_entry = BackupEntry(
            expected_job_id=job.id,
            timestamp=now,
            status="MISSING",
            message="Aucune entrée dans le rapport pour ce job.",
            calculated_hash=computed_hash if computed_hash else "",
            agent_id=agent_id,
            agent_overall_status=agent_status,
            server_calculated_staged_hash=computed_hash,
            server_calculated_staged_size=os.path.getsize(backup_file_path) if os.path.exists(backup_file_path) else None,
            previous_successful_hash_global=job.calculated_hash,
            hash_comparison_result=(computed_hash != job.calculated_hash) if job.calculated_hash else None,
        )
        db_session.add(job)
        db_session.add(backup_entry)

        send_notification(job, backup_entry.message)
