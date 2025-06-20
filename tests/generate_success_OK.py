#!/usr/bin/env python3
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
import os
import sys
import json
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob
from sqlalchemy.exc import SQLAlchemyError

def parse_database_key(db_key: str):
    parts = db_key.split("_")
    if len(parts) < 4:
        raise ValueError(f"Nom de base invalide : '{db_key}'")
    company_name = parts[0]
    city = parts[1]
    year = int(parts[-1])
    if len(parts) == 4:
        neighborhood = parts[2]
    else:
        neighborhood = "_".join(parts[2:-1])
    return company_name, city, neighborhood, year

def create_expected_jobs_from_json(json_file_path: str):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Erreur lecture JSON : {e}")
        sys.exit(1)

    agent_id = data.get("agent_id")
    databases = data.get("databases")

    if not agent_id or not databases:
        print("❌ Le fichier JSON doit contenir 'agent_id' et 'databases'")
        sys.exit(1)

    session = SessionLocal()
    jobs_created = []

    try:
        for db_key, db_content in databases.items():
            try:
                company_name, city, neighborhood, year = parse_database_key(db_key)
            except ValueError as ve:
                print(f"⛔ Parsing refusé pour '{db_key}' : {ve}")
                continue

            staged_path = db_content.get("staged_file_name")
            if not staged_path or not isinstance(staged_path, str):
                print(f"⚠️  Aucun 'staged_file_name' valide pour '{db_key}'")
                continue

            # On extrait uniquement le nom du fichier (pas le chemin complet)
            staged_file_name = os.path.basename(staged_path)

            job = ExpectedBackupJob(
                year=year,
                company_name=company_name,
                city=city,
                neighborhood=neighborhood,
                database_name=db_key,
                agent_id_responsible=agent_id,
                agent_deposit_path_template=f"{agent_id}/databases/{staged_file_name}",
                agent_log_deposit_path_template=f"{agent_id}/log",
                final_storage_path_template=f"validated/{company_name}/{year}/{city}/{staged_file_name}",
                current_status="UNKNOWN",
                notification_recipients="admin@example.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            session.add(job)
            jobs_created.append(job)
            print(f"✔ Job injecté : {db_key} → {staged_file_name}")

        session.commit()
        print(f"\n✅ {len(jobs_created)} ExpectedBackupJob(s) créés avec succès.")
    except SQLAlchemyError as e:
        session.rollback()
        print(f"❌ Erreur base de données : {e}")
    finally:
        session.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage : python create_expected_jobs_from_json.py chemin/vers/fichier.json")
        sys.exit(1)

    create_expected_jobs_from_json(sys.argv[1])
