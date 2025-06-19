import gzip
import hashlib
import json
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from datetime import datetime
from pathlib import Path

from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob






# -------- CONFIGURATION DE L’AGENT À GÉNÉRER --------
ENTREPRISE = "sirpacam"
VILLE = "douala"
QUARTIER = "newbell"
STORAGE_ROOT = Path("scanner_test_root")  # à adapter selon ton environnement
DATABASES = [
    f"{ENTREPRISE.upper()}_{VILLE.upper()}_2023",
    f"{ENTREPRISE.upper()}_{VILLE.upper()}_2024",
    f"{ENTREPRISE.upper()}_{VILLE.upper()}_2025"
]
# ---------------------------------------------------

def sha256_of_file(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def generate_agent_with_success():
    now = datetime.utcnow()
    agent_id = f"{ENTREPRISE}_{VILLE}_{QUARTIER}".lower()
    base_dir = STORAGE_ROOT / agent_id
    db_dir = base_dir / "databases"
    log_dir = base_dir / "log"
    db_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)

    # Contenu du log JSON global
    json_data = {
        "agent_id": agent_id,
        "overall_status": "OK",
        "databases": {}
    }

    db_session = SessionLocal()

    for db_name in DATABASES:
        file_name = f"{db_name.lower()}.sql.gz"
        db_path = db_dir / file_name

        sql_content = f"-- Simulated SQL for {db_name} at {now.isoformat()}"
        with gzip.open(db_path, "wt", encoding="utf-8") as f:
            f.write(sql_content)

        hash_val = sha256_of_file(db_path)

        # Compléter le JSON de log
        json_data["databases"][db_name] = {
            "staged_file_name": file_name,
            "COMPRESS": {
                "sha256_checksum": hash_val
            }
        }

        # Injecter le job sans hash de référence → pour premier succès
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

    # Écrire le fichier log JSON
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    log_name = f"{timestamp}_{ENTREPRISE.upper()}_{VILLE.upper()}_{QUARTIER.upper()}.json"
    with open(log_dir / log_name, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

    db_session.commit()
    db_session.close()

    print(f"✅ Agent généré : {agent_id}")
    print(f"   → {len(DATABASES)} bases injectées")
    print(f"   → Log : {log_name}")
    print("   → Scanner prêt à promouvoir en SUCCESS 🎯")


if __name__ == "__main__":
    generate_agent_with_success()
