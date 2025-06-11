# Importe 'Base' et 'engine' depuis le module de base de données de notre application.
# 'Base' est la classe de base déclarative pour nos modèles.
# 'engine' est le moteur de connexion à la base de données.
from app.core.database import Base, engine

import app.models.models

def init_db():
    """
    Crée toutes les tables définies par les modèles SQLAlchemy
    dans la base de données connectée via l'engine
    """
    print("Tentative de création des tables de la base de données...")
    Base.metadata.create_all(bind=engine)
    print("Tables de la BD créées (ou déjà existante)")
    
if __name__ == "__main__":
    init_db()