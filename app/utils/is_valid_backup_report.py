def is_valid_backup_report(report: dict) -> bool:
    """
    Valide entièrement la structure d'un rapport JSON de sauvegarde.
    Retourne True si tout est conforme, sinon False.
    """
    import datetime

    if not isinstance(report, dict):
        print("❌ Le rapport JSON doit être un dictionnaire.")
        return False

    # Vérifie les champs racine
    required_root_fields = {
        "agent_id": str,
        "operation_start_time": str,
        "operation_end_time": str,
        "databases": dict
    }

    for key, expected_type in required_root_fields.items():
        if key not in report:
            print(f"❌ Champ manquant en racine : {key}")
            return False
        if not isinstance(report[key], expected_type):
            print(f"❌ Type incorrect pour '{key}' : attendu {expected_type.__name__}")
            return False

    # Vérifie que les timestamps sont bien formés (ISO 8601)
    try:
        datetime.datetime.fromisoformat(report["operation_start_time"].replace("Z", "+00:00"))
        datetime.datetime.fromisoformat(report["operation_end_time"].replace("Z", "+00:00"))
    except Exception:
        print("❌ Les timestamps de début ou de fin ne sont pas valides.")
        return False

    # Vérifie le contenu de chaque base de données
    for db_key, db_entry in report["databases"].items():
        if not isinstance(db_entry, dict):
            print(f"❌ La base '{db_key}' doit contenir un dictionnaire.")
            return False

        for section in ["BACKUP", "COMPRESS", "TRANSFER"]:
            if section not in db_entry:
                print(f"❌ Section '{section}' manquante dans la base '{db_key}'")
                return False
            if not isinstance(db_entry[section], dict):
                print(f"❌ Section '{section}' dans la base '{db_key}' doit être un dictionnaire.")
                return False

        # Vérification section BACKUP
        backup = db_entry["BACKUP"]
        for key in ["status", "start_time", "end_time", "sha256_checksum", "size"]:
            if key not in backup:
                print(f"❌ Champ '{key}' manquant dans BACKUP de '{db_key}'")
                return False

        # Vérification section COMPRESS
        compress = db_entry["COMPRESS"]
        for key in ["status", "start_time", "end_time", "sha256_checksum", "size"]:
            if key not in compress:
                print(f"❌ Champ '{key}' manquant dans COMPRESS de '{db_key}'")
                return False

        # Vérification section TRANSFER
        transfer = db_entry["TRANSFER"]
        for key in ["status", "start_time", "end_time", "error_message"]:
            if key not in transfer:
                print(f"❌ Champ '{key}' manquant dans TRANSFER de '{db_key}'")
                return False

        # Vérifie la présence de staged_file_name
        if "staged_file_name" not in db_entry or not isinstance(db_entry["staged_file_name"], str):
            print(f"❌ Champ 'staged_file_name' manquant ou invalide dans '{db_key}'")
            return False

    # Si tout est OK
    return True
