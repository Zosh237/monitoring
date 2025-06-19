import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
import json
import gzip
import hashlib
from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob

# === CONFIGURATION ===
ENTREPRISE = "sirpacam"
VILLE = "douala"
QUARTIER = "newbell"
STORAGE_ROOT = Path("scanner_test_root")

DATABASES = {
    "SIRPACAM_DOUALA_2023": 188_178_944,
    "SIRPACAM_DOUALA_2024": 72_885_760,
    "SIRPACAM_DOUALA_2025": 56_817_152
}


def hash_file(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def generate_agent_report():
    now = datetime.utcnow()
    agent_id = f"{ENTREPRISE}_{VILLE}_{QUARTIER}".lower()
    base_dir = STORAGE_ROOT / agent_id
    db_dir = base_dir / "databases"
    log_dir = base_dir / "log"
    db_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    db_session = SessionLocal()
    databases = {}

    for db_name, raw_size in DATABASES.items():
        file_name = f"{db_name.lower()}.sql.gz"
        file_path = db_dir / file_name
        content = f"-- Simulated content for {db_name} at {now.isoformat()}"
        with gzip.open(file_path, "wt", encoding="utf-8") as f:
            f.write(content)

        compress_size = os.path.getsize(file_path)
        compress_hash = hash_file(file_path)

        databases[db_name] = {
            "BACKUP": {
                "status": True,
                "start_time": now.isoformat(),
                "end_time": now.isoformat(),
                "sha256_checksum": "placeholder-raw-hash",
                "size": raw_size
            },
            "COMPRESS": {
                "status": True,
                "start_time": now.isoformat(),
                "end_time": now.isoformat(),
                "sha256_checksum": compress_hash,
                "size": compress_size
            },
            "TRANSFER": {
                "status": True,
                "start_time": now.isoformat(),
                "end_time": now.isoformat(),
                "error_message": None
            },
            "staged_file_name": file_name
        }

        job = ExpectedBackupJob(
            year=int(db_name[-4:]),
            company_name=ENTREPRISE.upper(),
            city=VILLE.upper(),
            neighborhood=QUARTIER.upper(),
            database_name=db_name,
            agent_id_responsible=agent_id,
            agent_deposit_path_template=f"/mnt/backups/{agent_id}/databases/{file_name}",
            agent_log_deposit_path_template=f"/mnt/backups/{agent_id}/log/",
            final_storage_path_template=f"/mnt/validated/{file_name}",
            current_status="UNKNOWN",
            previous_successful_hash_global=None,
            is_active=True,
            created_at=now,
            updated_at=now
        )
        db_session.merge(job)

    report = {
        "operation_start_time": now.isoformat(),
        "operation_end_time": now.isoformat(),
        "agent_id": agent_id,
        "overall_status": "completed",
        "databases": databases
    }

    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{ENTREPRISE.upper()}_{VILLE.upper()}_{QUARTIER.upper()}.json"
    with open(log_dir / filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    db_session.commit()
    db_session.close()

    print(f"✅ Agent : {agent_id}")
    print(f"   → {len(DATABASES)} bases ajoutées")
    print(f"   → Rapport JSON enrichi : {filename}")
    print(f"   → Fichiers .sql.gz générés dans : {db_dir}")


if __name__ == "__main__":
    generate_agent_report()
