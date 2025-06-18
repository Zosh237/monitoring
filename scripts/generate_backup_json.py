#!/usr/bin/env python3
"""
Script pour générer un fichier JSON contenant au moins 10 bases de données.
Le fichier généré aura une structure similaire à l'exemple fourni.
Usage : python generate_backup_json.py
"""

import json
import random

def generate_base_entry(db_name: str) -> dict:
    """
    Génére une entrée exemple pour une base de données.
    
    Chaque entrée contient les sections :
      - BACKUP
      - COMPRESS
      - TRANSFER
      - staged_file_name
    """
    # Exemple de valeurs statiques ou générées aléatoirement pour simuler l'opération
    backup = {
        "status": True,
        "start_time": "2025-06-12T12:53:52Z",
        "end_time": "2025-06-12T12:54:26Z",
        "sha256_checksum": "a6af41c0b61d32d5935ed71ccd8d124b091ef150192d623451476401de13fce3",
        "size": random.randint(10000000, 200000000)
    }
    compress = {
        "status": True,
        "start_time": "2025-06-12T12:55:15Z",
        "end_time": "2025-06-12T12:56:03Z",
        "sha256_checksum": "4b63a9e31c52cca0a959cda76464c8e82c738f6ee22c20949d8a80a6fc0cdcb6",
        "size": random.randint(10000000, 200000000)
    }
    transfer = {
        "status": True,
        "start_time": "2025-06-12T12:56:06Z",
        "end_time": "2025-06-12T12:56:06Z",
        "error_message": None
    }
    staged_file_name = f"{db_name.lower()}.sql.gz"
    
    return {
        "BACKUP": backup,
        "COMPRESS": compress,
        "TRANSFER": transfer,
        "staged_file_name": staged_file_name
    }

def generate_json_data() -> dict:
    """
    Construit la structure de données avec :
      - Les métadonnées générales.
      - Le dictionnaire 'databases' avec au moins 10 entrées.
    """
    data = {
        "operation_start_time": "2025-06-12T12:53:52Z",
        "operation_end_time": "2025-06-12T12:56:06Z",
        "agent_id": "sirpacam_douala_newbell",
        "overall_status": "completed",
        "databases": {}
    }
    
    # Liste de 10 noms de bases de données (vous pouvez adapter ou en générer d'autres)
    db_names = [
        "SDMC_DOUALA_AKWA_2023",
        "SIRPACAM_NEWBELL_INFO_2024",
        "SOCIA_BLU_DETAIL_NB_2024",
        "DB4_SAMPLE_2025",
        "DB5_DEMO_2025",
        "DB6_REPORT_2025",
        "DB7_DATA_2025",
        "DB8_ARCHIVE_2025",
        "DB9_STAT_2025",
        "DB10_FINAL_2025"
    ]
    
    for db_name in db_names:
        data["databases"][db_name] = generate_base_entry(db_name)
    
    return data

def main():
    output_file = "generated_backup_data.json"
    json_data = generate_json_data()
    
    # Écriture du JSON dans un fichier avec une indentation pour plus de lisibilité
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)
    
    print(f"Fichier JSON généré : {output_file}")

if __name__ == "__main__":
    main()
