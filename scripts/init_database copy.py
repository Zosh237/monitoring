# Importe 'Base' et 'engine' depuis le module de base de données de notre application.
# 'Base' est la classe de base déclarative pour nos modèles.
# 'engine' est le moteur de connexion à la base de données.
from app.core.database import Base, engine
from app.models import models

def init_db():

    """
    Crée toutes les tables définies par les modèles SQLAlchemy
    dans la base de données connectée via l'engine
    """
    print("Tentative de création des tables de la base de données...")

    try:
        with engine.connect() as conn:
            print("✅ Connexion réussie à la base SQLite")
            print('Debut de Suppression des tables de la Base de données')
            Base.metadata.drop_all(bind=engine)
            print("Toutes les tables ont été supprimées.")
            print("Début de création des tables de la Base de données")
            Base.metadata.create_all(bind=engine)
            print("Tables de la BD créées (ou déjà existante)")
    except Exception as e:
            print(f"❌ Échec de connexion : {e}")

 
if __name__ == "__main__":
    init_db()