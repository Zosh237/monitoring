import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.schemas.expected_backup_job import ExpectedBackupJobCreate
from app.crud.expected_backup_job import create_expected_backup_job

def extract_agent_info(agent_folder: Path) -> tuple[str, Path]:
    agent_id = agent_folder.name.lower()
    log_dir = agent_folder / "log"

    status_files = list(log_dir.glob("HORODATAGE_*.json"))
    if not status_files:
        raise FileNotFoundError(f"Aucun fichier JSON horodaté trouvé dans {log_dir}")
    
    return agent_id, status_files[0]

def infer_location_parts(agent_id: str) -> tuple[str, str, str]:
    """Extrait company_name, city, neighborhood à partir de sirpacam_douala_newbell"""
    parts = agent_id.split("_")
    if len(parts) < 3:
        raise ValueError("agent_id mal formé pour extraire company_name, city, neighborhood")
    return parts[0], parts[1], "_".join(parts[2:])

def create_expected_jobs_from_status(agent_path: Path, db: Session):
    agent_id, status_file = extract_agent_info(agent_path)
    company_name, city, neighborhood = infer_location_parts(agent_id)

    with open(status_file, encoding="utf-8") as f:
        content = json.load(f)

    databases = content.get("databases", {})
    created = []

    for db_name, section in databases.items():
        backup = section.get("BACKUP", {})
        staged_filename = section.get("staged_file_name", "")
        size = backup.get("size")
        checksum = backup.get("sha256_checksum")
        end_time = backup.get("end_time") or section.get("COMPRESS", {}).get("end_time")

        try:
            parsed_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except Exception:
            print(f"⛔ Timestamp invalide pour {db_name}")
            continue

        job = ExpectedBackupJobCreate(
            agent_id_responsible=agent_id,
            database_name=db_name,
            expected_backup_time=parsed_time,
            expected_filename=staged_filename,
            expected_file_size=size,
            expected_checksum=checksum,
            year=parsed_time.year,
            company_name=company_name.upper(),
            city=city.upper(),
            neighborhood=neighborhood.upper(),
            expected_hour_utc=parsed_time.hour,
            expected_minute_utc=parsed_time.minute,
            expected_frequency = "daily",
            days_of_week = "mon,tue,wed,thu,fri",

            agent_deposit_path_template=f"/agents/{agent_id}/databases/{{filename}}",
            agent_log_deposit_path_template=f"/agents/{agent_id}/log/{{filename}}",
            final_storage_path_template=f"/backups/{company_name.upper()}/{city.upper()}/{neighborhood.upper()}/{{filename}}"
        )

        db_job = create_expected_backup_job(db, job)
        created.append(db_job.database_name)
        print(f"✅ Créé : {db_job.database_name}")

    if not created:
        print("⚠️ Aucun job n'a été créé.")
    else:
        print(f"\n🎯 Total : {len(created)} job(s) créé(s) pour l'agent '{agent_id}'.")

def main():
    root_dir = Path("test_manuel")
    agent_name = input("📌 Nom du dossier agent (dans test_manuel/) : ").strip()
    agent_path = root_dir / agent_name

    if not agent_path.exists():
        print(f"❌ Dossier '{agent_path}' introuvable.")
        return

    db: Session = SessionLocal()
    try:
        create_expected_jobs_from_status(agent_path, db)
    finally:
        db.close()

if __name__ == "__main__":
    main()
