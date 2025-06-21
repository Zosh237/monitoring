#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob
from config.settings import settings  # 🔧 Ajouté pour accéder aux variables centralisées
from sqlalchemy.exc import SQLAlchemyError

def parse_database_key(db_key: str):
    parts = db_key.split("_")
    if len(parts) < 3:
        raise ValueError(f"Nom de base invalide : {db_key}")
    try:
        year = int(parts[-1])
    except ValueError:
        raise ValueError(f"Le dernier élément de '{db_key}' n'est pas une année valide.")
    company_name = parts[0]
    city = parts[1]
    neighborhood = "_".join(parts[2:-1]) if len(parts) > 3 else ""
    return company_name, city, neighborhood, year

def create_expected_jobs_from_json(json_file_path: str):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur de lecture JSON : {e}")
        sys.exit(1)

    agent_id = data.get("agent_id")
    databases = data.get("databases")

    if not agent_id or not databases:
        print("Le fichier doit contenir 'agent_id' et 'databases'.")
        sys.exit(1)

    session = SessionLocal()
    jobs_created = []
    already_existing = []

    try:
        for db_key in databases.keys():
            try:
                company_name, city, neighborhood, year = parse_database_key(db_key)
            except ValueError as ve:
                print(f"⚠️ {ve}")
                continue

            exists = session.query(ExpectedBackupJob).filter_by(
                database_name=db_key,
                agent_id_responsible=agent_id
            ).first()

            if exists:
                already_existing.append(db_key)
                continue

            job = ExpectedBackupJob(
                year=year,
                company_name=company_name,
                city=city,
                neighborhood=neighborhood,
                database_name=db_key,
                agent_id_responsible=agent_id,
                agent_deposit_path_template=f"{agent_id}/databases/{db_key}",
                agent_log_deposit_path_template=f"/{settings.BACKUP_STORAGE_ROOT}/{agent_id}/log",
                final_storage_path_template=f"/{settings.VALIDATED_BACKUPS_BASE_PATH}/{company_name}/{city}/{year}",
                notification_recipients=settings.ADMIN_EMAIL_RECIPIENT,
                current_status="UNKNOWN",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            session.add(job)
            jobs_created.append(db_key)

        session.commit()

        print("\n📋 Rapport de création des ExpectedBackupJob")
        print(f"🔍 Bases analysées       : {len(databases)}")
        print(f"✅ Bases créées          : {len(jobs_created)}")
        print(f"♻️ Bases déjà existantes : {len(already_existing)}")

        if jobs_created:
            print("\n📦 Noms des bases créées :")
            for db in jobs_created:
                print(f"  - {db}")
        if already_existing:
            print("\n🔁 Bases ignorées (déjà en BDD) :")
            for db in already_existing:
                print(f"  - {db}")

    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Erreur SQL :", e)
    finally:
        session.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage : python create_expected_jobs_from_json.py chemin_du_fichier.json")
        sys.exit(1)

    json_file_path = sys.argv[1]
    create_expected_jobs_from_json(json_file_path)
