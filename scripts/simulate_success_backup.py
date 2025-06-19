import gzip
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# -------- CONFIG DE L’AGENT À SIMULER --------
ENTREPRISE = "sirpacam"
VILLE = "douala"
QUARTIER = "newbell"
STORAGE_ROOT = Path("scanner_test_root")  # ← change ici si besoin
# ---------------------------------------------

def sha256_of_file(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def simulate_success():
    now = datetime.utcnow()
    year = now.year

    agent_id = f"{ENTREPRISE}_{VILLE}_{QUARTIER}".lower()
    db_name = f"{ENTREPRISE.upper()}_{VILLE.upper()}_{year}"
    file_name = f"{db_name.lower()}.sql.gz"

    base_dir = STORAGE_ROOT / agent_id
    db_dir = base_dir / "databases"
    log_dir = base_dir / "log"
    db_path = db_dir / file_name
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"{timestamp}_{ENTREPRISE.upper()}_{VILLE.upper()}_{QUARTIER.upper()}.json"

    # Créer les dossiers nécessaires
    db_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Génère le fichier compressé
    sql_content = f"-- Simulated SQL backup for {db_name} at {now.isoformat()}"
    with gzip.open(db_path, "wt", encoding="utf-8") as f:
        f.write(sql_content)

    hash_value = sha256_of_file(db_path)

    # Génère le log JSON
    log_data = {
        "agent_id": agent_id,
        "overall_status": "OK",
        "databases": {
            db_name: {
                "staged_file_name": file_name,
                "COMPRESS": {
                    "sha256_checksum": hash_value
                }
            }
        }
    }
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, indent=2)

    # Injecte le job dans la base
    db = SessionLocal()
    job = ExpectedBackupJob(
        year=year,
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
        calculated_hash=None,
        is_active=True,
        created_at=now,
        updated_at=now
    )
    db.merge(job)
    db.commit()
    db.close()

    print(f"✅ Simulation terminée pour {agent_id}")
    print(f"   → Base : {file_name}")
    print(f"   → Log JSON : {log_path.name}")
    print(f"   → Hash compressé = {hash_value[:12]}...")


if __name__ == "__main__":
    simulate_success()
