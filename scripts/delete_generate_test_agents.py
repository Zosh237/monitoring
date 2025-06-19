import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import ExpectedBackupJob
from sqlalchemy import or_


def delete_test_jobs():
    db = SessionLocal()

    test_agents = [
        "sirpacam_douala_newbell",
        "sdmc_yaounde_bastos",
        "socia_blu_dla",
        "infocred_buea_central"
    ]
    conditions = [ExpectedBackupJob.agent_id_responsible.ilike(agent) for agent in test_agents]
    jobs = (
    db.query(ExpectedBackupJob)
    .filter(ExpectedBackupJob.agent_id_responsible.ilike("%_douala_newbell"))
    .union_all(
        db.query(ExpectedBackupJob).filter(ExpectedBackupJob.agent_id_responsible.ilike("%_yaounde_bastos")),
        db.query(ExpectedBackupJob).filter(ExpectedBackupJob.agent_id_responsible.ilike("%socia%")),
        db.query(ExpectedBackupJob).filter(ExpectedBackupJob.agent_id_responsible.ilike("%infocred%"))
    
    ).all()
    )

    print(f"Jobs trouvés : {[job.database_name for job in jobs]}")
    agents = db.query(ExpectedBackupJob.agent_id_responsible).distinct().all()
    print("\n📋 Agents enregistrés en base :")
    for a in agents:
        print(f" - {a[0]!r}")

    deleted_count = (
    db.query(ExpectedBackupJob)
    .filter(ExpectedBackupJob.agent_id_responsible.in_([
        "sirpacam_douala_newbell",
        "sdmc_yaounde_bastos",
        "socia_blu_dla",
        "infocred_buea_central"
    ]))
        .delete(synchronize_session=False)
    )

    db.commit()
    db.close()
    print(f"🧹 {deleted_count} jobs de test supprimés avec succès.")

if __name__ == "__main__":
    delete_test_jobs()
