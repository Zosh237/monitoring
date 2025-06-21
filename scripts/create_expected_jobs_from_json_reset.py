#!/usr/bin/env python3

import os
import sys

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import SessionLocal, engine
from app.models import models  # Assure-toi que tous tes modèles sont importés ici

def reset_database():
    """
    Supprime toutes les données de toutes les tables.
    Ne supprime pas les tables elles-mêmes (pas de DROP).
    """
    session = SessionLocal()
    try:
        print("🔄 Réinitialisation de la base...")
        for table in reversed(models.Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
        print("✅ Toutes les données ont été supprimées avec succès.")
    except SQLAlchemyError as e:
        session.rollback()
        print("❌ Erreur lors de la suppression :", e)
    finally:
        session.close()

if __name__ == "__main__":
    confirmation = input("⚠️ Cette opération va supprimer toutes les données. Continuer ? (oui/non) : ")
    if confirmation.lower() in ["oui", "o", "yes", "y"]:
        reset_database()
    else:
        print("⏹ Opération annulée.")
