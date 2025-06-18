#!/usr/bin/env python3
"""
Script pour créer dynamiquement des ExpectedBackupJob à partir d'un fichier JSON.

Usage:
    python create_expected_jobs_from_json.py chemin_du_fichier.json

Le fichier JSON doit contenir, par exemple :
{
  "operation_start_time": "2025-06-12T12:53:52Z",
  "operation_end_time": "2025-06-12T12:56:06Z",
  "agent_id": "sirpacam_douala_newbell",
  "overall_status": "completed",
  "databases": {
    "SDMC_DOUALA_AKWA_2023": { ... },
    "SIRPACAM_NEWBELL_INFO_2024": { ... },
    "SOCIA_BLU_DETAIL_NB_2024": { ... }
  }
}
"""

import sys
import json
from datetime import datetime
from app.core.database import SessionLocal, engine, Base
from app.models.models import ExpectedBackupJob
from sqlalchemy.exc import SQLAlchemyError

def parse_database_key(db_key: str):
    """
    Parse la chaîne db_key pour en extraire company_name, city, neighborhood et year.
    On suppose que db_key a la forme "COMPANY_CITY_NEIGHBORHOOD_YEAR" ou avec
    plusieurs éléments pour le quartier.
    """
    parts = db_key.split("_")
    if len(parts) < 4:
        raise ValueError(f"Le nom de la base '{db_key}' ne respecte pas le format attendu.")
    
    company_name = parts[0]
    city = parts[1]
    year = int(parts[-1])
    if len(parts) == 4:
        neighborhood = parts[2]
    else:
        # Si plus de 4 parties, tout ce qui est entre city et year est considéré comme le quartier.
        neighborhood = "_".join(parts[2:-1])
    return company_name, city, neighborhood, year

def create_expected_jobs_from_json(json_file_path: str):
    # Charger le JSON
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier JSON: {e}")
        sys.exit(1)
    
    # On s'attend à retrouver "agent_id" et "databases" dans le JSON.
    agent_id = data.get("agent_id")
    databases = data.get("databases")
    
    if agent_id is None or databases is None:
        print("Le fichier JSON doit contenir les clés 'agent_id' et 'databases'.")
        sys.exit(1)
    
    session = SessionLocal()
    jobs_created = []
    try:
        for db_key in databases.keys():
            try:
                company_name, city, neighborhood, year = parse_database_key(db_key)
            except ValueError as ve:
                print(f"Erreur de parsing pour '{db_key}': {ve}")
                continue

            # Créer un objet ExpectedBackupJob avec des templates par défaut pour les chemins.
            job = ExpectedBackupJob(
                year=year,
                company_name=company_name,
                city=city,
                neighborhood=neighborhood,
                database_name=db_key,
                agent_id_responsible=agent_id,
                agent_deposit_path_template="{agent_id}/databases/{database_name}",
                agent_log_deposit_path_template="{agent_id}/log",
                final_storage_path_template="final_backup/{company_name}/{database_name}",
                current_status="UNKNOWN",
                notification_recipients="admin@example.com",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(job)
            jobs_created.append(job)
        
        session.commit()
        print(f"{len(jobs_created)} ExpectedBackupJob(s) created successfully!")
    except SQLAlchemyError as e:
        session.rollback()
        print("Erreur lors de l'insertion en base de données:", e)
    finally:
        session.close()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python create_expected_jobs_from_json.py chemin_du_fichier.json")
        sys.exit(1)
    json_file_path = sys.argv[1]
    create_expected_jobs_from_json(json_file_path)
