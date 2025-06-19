#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import hashlib
import argparse
import json
import random
import sys

# Fix import root for 'app.'
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob

AGENTS = [
    {"entreprise": "SIRPACAM", "ville": "DOUALA", "quartier": "NEWBELL"},
    {"entreprise": "SDMC", "ville": "YAOUNDE", "quartier": "BASTOS"},
    {"entreprise": "SOCIA", "ville": "BLU", "quartier": "DLA"},
    {"entreprise": "INFOCRED", "ville": "BUEA", "quartier": "CENTRAL"},
]

YEARS = [2024, 2023, 2022, 2021, 2020]  # une base par année


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_file(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def generate_backup_content(name: str, variant="normal"):
    base = f"-- Backup SQL for {name}"
    if variant == "corrupt":
        base = f"-- Fake corrupted content for {name}"
    return base


def create_agent_structure(agent_meta: dict, root_path: Path):
    entrep, ville, quartier = agent_meta["entreprise"], agent_meta["ville"], agent_meta["quartier"]
    agent_id = f"{entrep}_{ville}_{quartier}"
    agent_dir = root_path / agent_id
    log_dir = agent_dir / "log"
    db_dir = agent_dir / "databases"
    log_dir.mkdir(parents=True, exist_ok=True)
    db_dir.mkdir(parents=True, exist_ok=True)

    databases = {}
    previous_hash = None
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    for i, year in enumerate(YEARS):
        db_name = f"{entrep}_{ville}_{year}"
        file_name = f"{db_name.lower()}.sql.gz"
        backup_path = db_dir / file_name
        scenario = ["SUCCESS", "FAILED", "HASH_MISMATCH", "MISSING", "INACTIVE"][i]

        if scenario == "SUCCESS":
            content = generate_backup_content(db_name)
            hash_value = sha256_of(content)
            write_file(backup_path, content)

        elif scenario == "FAILED":
            content = generate_backup_content(db_name, variant="corrupt")
            hash_value = sha256_of("bad content")
            write_file(backup_path, content)

        elif scenario == "HASH_MISMATCH":
            content = generate_backup_content(db_name)
            hash_value = previous_hash or sha256_of(content)
            write_file(backup_path, content)

        elif scenario == "MISSING":
            content = None
            hash_value = sha256_of("pretend content")  # fichier non livré

        elif scenario == "INACTIVE":
            content = generate_backup_content(db_name)
            hash_value = sha256_of(content)
            write_file(backup_path, content)

        previous_hash = hash_value

        databases[db_name] = {
            "BACKUP": {
                "status": True,
                "start_time": now,
                "end_time": now,
                "sha256_checksum": hash_value,
                "size": random.randint(10_000_000, 50_000_000)
            },
            "COMPRESS": {
                "status": True,
                "start_time": now,
                "end_time": now,
                "sha256_checksum": hash_value,
                "size": random.randint(1_000_000, 5_000_000)
            },
            "TRANSFER": {
                "status": True,
                "start_time": now,
                "end_time": now,
                "error_message": None
            },
            "staged_file_name": file_name
        }

    report = {
        "agent_id": agent_id.lower(),
        "overall_status": "completed",
        "operation_start_time": now,
        "operation_end_time": now,
        "databases": databases
    }

    safe_time = now.replace(":", "-")
    json_path = log_dir / f"{safe_time}_{agent_id}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"✅ Agent '{agent_id}' créé avec 5 bases simulées.")
    return agent_id, list(databases.keys())


def inject_jobs_in_db(all_jobs_by_agent: dict):
    print("\n📍 Base utilisée : ", SessionLocal().bind.url)

    db = SessionLocal()
    now = datetime.utcnow()

    for agent_id, db_names in all_jobs_by_agent.items():
        parts = agent_id.split("_")
        entreprise = parts[0]
        ville = parts[1]
        quartier = "_".join(parts[2:])

        for i, db_name in enumerate(db_names):
            year = int(db_name.split("_")[-1])
            is_active = False if i == 4 else True
            job = ExpectedBackupJob(
                database_name=db_name,
                agent_id_responsible=agent_id.lower(),
                city=ville.title(),
                neighborhood=quartier.title(),
                company_name=entreprise,
                year=year,
                current_status="UNKNOWN",
                is_active=is_active,
                created_at=now,
                agent_deposit_path_template=f"/mnt/backups/{agent_id}/databases/{db_name.lower()}.sql.gz",
                agent_log_deposit_path_template=f"/mnt/backups/{agent_id}/log/",
                final_storage_path_template=f"/mnt/validated/{db_name.lower()}.sql.gz",
            )
            db.merge(job)

    db.commit()
    db.close()
    print("✅ Jobs injectés dans la base de données.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, help="Chemin racine des agents à générer")
    parser.add_argument("--inject", action="store_true", help="Injecte les jobs ExpectedBackupJob en base")
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    root_path.mkdir(parents=True, exist_ok=True)

    print(f"\n🧪 Dossier racine : {root_path}\n")

    all_jobs_by_agent = {}
    for agent in AGENTS:
        agent_id, db_names = create_agent_structure(agent, root_path)
        all_jobs_by_agent[agent_id] = db_names

    if args.inject:
        inject_jobs_in_db(all_jobs_by_agent)

    print("\n🎉 Génération terminée. Scanner prêt à l’usage.\n")


if __name__ == "__main__":
    main()
