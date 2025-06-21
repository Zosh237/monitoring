#!/usr/bin/env python3
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
import argparse
import json
import hashlib
import random
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob
from sqlalchemy.exc import SQLAlchemyError

VALID_CONTENT = b"VALIDZSTCONTENT123\n"
VALID_HASH = hashlib.sha256(VALID_CONTENT).hexdigest()


def parse_database_key(db_key):
    parts = db_key.split("_")
    if len(parts) < 4:
        raise ValueError(f"Nom de base invalide : {db_key}")
    return parts[0], parts[1], "_".join(parts[2:-1]), int(parts[-1])


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def get_basename(path):
    return os.path.basename(path)


def calculate_sha256(path):
    if not os.path.exists(path):
        return None
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha.update(chunk)
    return sha.hexdigest()


def write_zst_file(path, expected_hash=None):
    if os.path.exists(path):
        return

    if expected_hash == VALID_HASH:
        with open(path, "wb") as f:
            f.write(VALID_CONTENT)
    else:
        with open(path, "wb") as f:
            f.write(os.urandom(2048))


def create_log_file(log_dir, agent_id, operation_end_time, databases, db_dir):
    ts = operation_end_time.replace(":", "-")
    log_file = f"{ts}_{agent_id}.json"
    log_path = os.path.join(log_dir, log_file)
    if os.path.exists(log_path):
        return

    for db_key, db_data in databases.items():
        comp_block = db_data.get("COMPRESS", {})
        backup_block = db_data.get("BACKUP", {})
        staged_name = get_basename(db_data.get("staged_file_name", ""))
        dump_path = os.path.join(db_dir, staged_name)

        # 1. SHA256 depuis fichier s’il faut
        if not comp_block.get("sha256"):
            actual_hash = calculate_sha256(dump_path)
            if actual_hash:
                comp_block["sha256"] = actual_hash

        # 2. sha256_checksum dans BACKUP
        if comp_block.get("sha256") and backup_block is not None:
            backup_block["sha256_checksum"] = comp_block["sha256"]

    payload = {
        "operation_start_time": datetime.utcnow().isoformat() + "Z",
        "operation_end_time": operation_end_time + "Z",
        "agent_id": agent_id,
        "overall_status": "completed",
        "databases": databases
    }

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)


def process_json_file(json_path, agent_root):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    agent_id = data.get("agent_id")
    databases = data.get("databases")
    operation_end_time = data.get("operation_end_time")
    if not agent_id or not databases:
        print("Champs requis manquants dans le JSON.")
        sys.exit(1)

    agent_path = os.path.abspath(os.path.join(agent_root, agent_id))
    log_dir = os.path.join(agent_path, "log")
    db_dir = os.path.join(agent_path, "databases")
    ensure_directory(log_dir)
    ensure_directory(db_dir)

    session = SessionLocal()
    for db_key, db_info in databases.items():
        try:
            company, city, neighborhood, year = parse_database_key(db_key)
        except ValueError as e:
            print(e)
            continue

        existing = session.query(ExpectedBackupJob).filter_by(
            database_name=db_key,
            agent_id_responsible=agent_id
        ).first()
        if not existing:
            job = ExpectedBackupJob(
                year=year,
                company_name=company,
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

        staged = db_info.get("staged_file_name")
        compress_hash = db_info.get("COMPRESS", {}).get("sha256", "")
        filename = get_basename(staged)
        full_path = os.path.join(db_dir, filename)
        write_zst_file(full_path, expected_hash=compress_hash)

    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        print("Erreur SQL :", e)
    finally:
        session.close()

    create_log_file(log_dir, agent_id, operation_end_time, databases, db_dir)
    print(f"✅ Agent {agent_id} mis à jour dans {agent_path}")


def main():
    parser = argparse.ArgumentParser(description="Créer ExpectedBackupJob + structure agent.")
    parser.add_argument("json_path", help="Chemin du fichier JSON de rapport")
    parser.add_argument("--agent-root", default="scanner_test_root", help="Racine des agents")
    args = parser.parse_args()
    process_json_file(args.json_path, args.agent_root)


if __name__ == "__main__":
    main()
