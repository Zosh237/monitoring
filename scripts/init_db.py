from sqlalchemy.orm import sessionmaker
from app.models.models import Base
from app.core.database import SQLALCHEMY_DATABASE_URL

def init_db():
    # Créer le moteur de base de données
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    
    # Créer toutes les tables
    Base.metadata.create_all(bind=engine)
    
    print("Base de données initialisée avec succès")

if __name__ == "__main__":
    init_db() 