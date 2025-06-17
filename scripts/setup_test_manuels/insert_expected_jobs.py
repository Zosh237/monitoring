from datetime import datetime
from sqlalchemy.orm import Session
from app.schemas.expected_backup_job import ExpectedBackupJobCreate
from app.crud.expected_backup_job import create_expected_backup_job
from app.core.database import SessionLocal

# Créer une session manuelle (attention à fermer proprement en production)
db: Session = SessionLocal()

# Liste des jobs à insérer
expected_jobs = [
    {
        "agent_id_responsible": "sirpacam_douala_newbell",
        "database_name": "SDMC_DOUALA_AKWA_2023",
        "expected_backup_time": datetime.fromisoformat("2025-06-12T12:55:00+00:00"),
        "expected_filename": "sdmc_douala_akwa_2023.sql.gz",
        "expected_file_size": 188178944,
        "expected_checksum": "a6af41c0b61d32d5935ed71ccd8d124b091ef150192d623451476401de13fce3"
    },
    {
        "agent_id_responsible": "sirpacam_douala_newbell",
        "database_name": "SIRPACAM_NEWBELL_INFO_2024",
        "expected_backup_time": datetime.fromisoformat("2025-06-12T12:54:30+00:00"),
        "expected_filename": "sirpacam_newbell_info_2024.sql.gz",
        "expected_file_size": 72885760,
        "expected_checksum": "eb097c55fb457f5e0edfe2fb7179e7027545fec230c26411484a26d6ddc0523f"
    },
    {
        "agent_id_responsible": "sirpacam_douala_newbell",
        "database_name": "SOCIA_BLU_DETAIL_NB_2024",
        "expected_backup_time": datetime.fromisoformat("2025-06-12T12:54:37+00:00"),
        "expected_filename": "socia_blu_detail_nb_2024.sql.gz",
        "expected_file_size": 56817152,
        "expected_checksum": "f4b1e1c04732c8a13f97f4dd3ed14f565ed1922195514c023482bb7aac0c1275"
    }
]

# Insertion dans la base
for job_data in expected_jobs:
    job = ExpectedBackupJobCreate(**job_data)
    created = create_expected_backup_job(db, job)
    print(f"✅ Job créé : {created.database_name}")

db.close()
