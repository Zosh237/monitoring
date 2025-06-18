#!/usr/bin/env python3
"""
Script de création d'exemples d'ExpectedBackupJob.

Ce script se connecte à la base de données, crée quelques jobs attendus et les enregistre.
Vous pouvez l'adapter en fonction de vos besoins ou l'exécuter pour tester la création en base.
"""

from datetime import datetime
from app.core.database import SessionLocal, engine, Base
from app.models.models import ExpectedBackupJob
import sys

# Assurez-vous que les tables existent avant d'insérer quoi que ce soit.
Base.metadata.create_all(bind=engine)

def create_sample_expected_jobs():
    session = SessionLocal()
    try:
        # Exemple 1 : pour la base de données "SDMC_DOUALA_AKWA_2023"
        job1 = ExpectedBackupJob(
            year=2025,
            company_name="SDMC Douala",
            city="Douala",
            neighborhood="Akwa",
            database_name="SDMC_DOUALA_AKWA_2023",
            agent_id_responsible="sirpacam_douala_newbell",
            agent_deposit_path_template="{agent_id}/databases/{database_name}",
            agent_log_deposit_path_template="{agent_id}/log",
            final_storage_path_template="final_backup/{company_name}/{database_name}",
            current_status="UNKNOWN",
            notification_recipients="admin@example.com",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Exemple 2 : pour la base de données "SIRPACAM_NEWBELL_INFO_2024"
        job2 = ExpectedBackupJob(
            year=2025,
            company_name="SIRPACAM Newbell",
            city="Douala",
            neighborhood="Newbell",
            database_name="SIRPACAM_NEWBELL_INFO_2024",
            agent_id_responsible="sirpacam_douala_newbell",
            agent_deposit_path_template="{agent_id}/databases/{database_name}",
            agent_log_deposit_path_template="{agent_id}/log",
            final_storage_path_template="final_backup/{company_name}/{database_name}",
            current_status="UNKNOWN",
            notification_recipients="admin@example.com",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # Exemple 3 : pour la base de données "SOCIA_BLU_DETAIL_NB_2024"
        job3 = ExpectedBackupJob(
            year=2025,
            company_name="Socia Blu",
            city="Douala",
            neighborhood="DetailNB",
            database_name="SOCIA_BLU_DETAIL_NB_2024",
            agent_id_responsible="sirpacam_douala_newbell",
            agent_deposit_path_template="{agent_id}/databases/{database_name}",
            agent_log_deposit_path_template="{agent_id}/log",
            final_storage_path_template="final_backup/{company_name}/{database_name}",
            current_status="UNKNOWN",
            notification_recipients="admin@example.com",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add_all([job1, job2, job3])
        session.commit()
        print("Expected jobs created successfully!")
        
    except Exception as e:
        session.rollback()
        print("Error creating expected jobs:", e)
        sys.exit(1)
    finally:
        session.close()

if __name__ == '__main__':
    create_sample_expected_jobs()
