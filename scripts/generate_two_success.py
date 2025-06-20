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

# === AGENTS À GÉNÉRER ===
AGENTS = [
    {
        "entreprise": "sirpacam",
        "ville": "yaounde",
        "quartier": "mvogada",
        "database": ("SIRPACAM_YDE_MVOGADA_2024", 72_885_760)
    },
    {
        "entreprise": "sociblue",
        "ville": "bafoussam",
        "quartier": "centreville",
        "database": ("SOCIBLUE_BAF_CV_2024", 58_881_920)
    }
]

STORAGE_ROOT = Path("scanner_test_root")

def sha256(file_path: Path) -> str:
    with file_path.open("rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def create_agent(agent_info):
    now = datetime.utcnow()
    entreprise, ville, quartier = agent_info["entreprise"], agent_info["ville"], agent_info["quartier"]
    agent_id = f"{entreprise}_{ville}_{quartier}".lower()
    db_name, raw_size = agent_info["database"]
    file_name = f"{db_name.lower()}.sql.gz"

    base_dir = STORAGE_ROOT / agent_id
    db_dir = base_dir / "databases"
    log_dir = base_dir / "log"
    db_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    db_path = db_dir / file_name
    with gzip.open(db_path, "wt", encoding="utf-8") as f:
        f.write(f"-- Simulated DB for {db_name} at {now.isoformat()}")

    compress_hash = sha256(db_path)
    compress_size = os.path.getsize(db_path)

    log = {
        "operation_start_time": now.isoformat(),
        "operation_end_time": now.isoformat(),
        "agent_id": agent_id,
        "overall_status": "completed",
        "databases": {
            db_name: {
                "BACKUP": {
                    "status": True,
                    "start_time": now.isoformat(),
                    "end_time": now.isoformat(),
                    "sha256_checksum": "raw-placeholder",
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
        }
    }

    timestamp = now.strftime("%Y%m%d_%H%M%S")
    log_file = f"{timestamp}_{entreprise.upper()}_{ville.upper()}_{quartier.upper()}.json"
    with open(log_dir / log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    db = SessionLocal()
    job = ExpectedBackupJob(
        year=int(db_name[-4:]),
        company_name=entreprise.upper(),
        city=ville.upper(),
        neighborhood=quartier.upper(),
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
    db.merge(job)
    db.commit()
    db.close()

    print(f"🟢 Agent généré : {agent_id} → DB = {db_name}")
    print(f"   → rapport : {log_file}")
    print(f"   → hash = {compress_hash[:12]}...")


def main():
    for agent in AGENTS:
        create_agent(agent)


if __name__ == "__main__":
    main()
