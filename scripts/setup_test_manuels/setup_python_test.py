import os
import json
from pathlib import Path

# Définir le chemin de base
base_path = Path("test_manuel/SIRPACAM_DOUALA_NEWBELL")

# Crée les sous-dossiers databases/ et log/
db_path = base_path / "databases"
log_path = base_path / "log"
db_path.mkdir(parents=True, exist_ok=True)
log_path.mkdir(parents=True, exist_ok=True)

# Crée les fichiers .sql.gz fictifs
(db_path / "socia_blu_detail_nb_2024.sql.gz").write_text("Contenu fictif de sauvegarde 1", encoding="utf-8")
(db_path / "sirpacam_newbell_info_2024.sql.gz").write_text("Contenu fictif de sauvegarde 2", encoding="utf-8")

# Contenu du fichier JSON (repris de ton exemple)
status_data = {
    "operation_start_time": "2025-06-12T12:53:52Z",
    "operation_end_time": "2025-06-12T12:56:06Z",
    "agent_id": "sirpacam_douala_newbell",
    "overall_status": "completed",
    "databases": {
        "SDMC_DOUALA_AKWA_2023": {
            "BACKUP": {
                "status": True,
                "start_time": "2025-06-12T12:53:52Z",
                "end_time": "2025-06-12T12:54:26Z",
                "sha256_checksum": "a6af41c0b61d32d5935ed71ccd8d124b091ef150192d623451476401de13fce3",
                "size": 188178944
            },
            "COMPRESS": {
                "status": True,
                "start_time": "2025-06-12T12:55:15Z",
                "end_time": "2025-06-12T12:56:03Z",
                "sha256_checksum": "4b63a9e31c52cca0a959cda76464c8e82c738f6ee22c20949d8a80a6fc0cdcb6",
                "size": 19972513
            },
            "TRANSFER": {
                "status": True,
                "start_time": "2025-06-12T12:56:06Z",
                "end_time": "2025-06-12T12:56:06Z",
                "error_message": None
            },
            "staged_file_name": "sdmc_douala_akwa_2023.sql.gz"
        },
        "SIRPACAM_NEWBELL_INFO_2024": {
            "BACKUP": {
                "status": True,
                "start_time": "2025-06-12T12:54:26Z",
                "end_time": "2025-06-12T12:54:33Z",
                "sha256_checksum": "eb097c55fb457f5e0edfe2fb7179e7027545fec230c26411484a26d6ddc0523f",
                "size": 72885760
            },
            "COMPRESS": {
                "status": True,
                "start_time": "2025-06-12T12:54:39Z",
                "end_time": "2025-06-12T12:54:58Z",
                "sha256_checksum": "f34b9d761b600e83c6375cce955a02fbdf7b86c80008e3b88c2a2b05de1aed08",
                "size": 5541419
            },
            "TRANSFER": {
                "status": True,
                "start_time": "2025-06-12T12:56:06Z",
                "end_time": "2025-06-12T12:56:06Z",
                "error_message": None
            },
            "staged_file_name": "sirpacam_newbell_info_2024.sql.gz"
        },
        "SOCIA_BLU_DETAIL_NB_2024": {
            "BACKUP": {
                "status": True,
                "start_time": "2025-06-12T12:54:33Z",
                "end_time": "2025-06-12T12:54:39Z",
                "sha256_checksum": "f4b1e1c04732c8a13f97f4dd3ed14f565ed1922195514c023482bb7aac0c1275",
                "size": 56817152
            },
            "COMPRESS": {
                "status": True,
                "start_time": "2025-06-12T12:54:59Z",
                "end_time": "2025-06-12T12:55:12Z",
                "sha256_checksum": "7a9c94696bfb5c1446a3d36e3202244400666e0f57eb809479bb1754daa0346d",
                "size": 3822283
            },
            "TRANSFER": {
                "status": True,
                "start_time": "2025-06-12T12:56:06Z",
                "end_time": "2025-06-12T12:56:06Z",
                "error_message": None
            },
            "staged_file_name": "socia_blu_detail_nb_2024.sql.gz"
        }
    }
}

# Écriture du fichier JSON dans le dossier log/
json_path = log_path / "HORODATAGE_SIRPACAM_DOUALA_NEWBELL.json"
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(status_data, f, indent=2)

print(f"Structure de test créée sous {base_path.resolve()}")
