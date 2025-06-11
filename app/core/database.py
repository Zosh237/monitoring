from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

import os
print(f"Chemin absolu de la base : {os.path.abspath('./data/db/sql_app.db')}")


SQLALCHEMY_DATABASE_URL =   settings.DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base est la classe de base pour nos modèles SQLAlchemy.
# Les modèles que nous définirons hériteront de cette classe.
Base = declarative_base()

# Fonction d'utilité pour obtenir une session de base de données.
# C'est une "dépendance" pour FastAPI : elle s'assure qu'une session est ouverte
# pour chaque requête API et qu'elle est correctement fermée après.
def get_db():
    db = SessionLocal() # Ouvre une nouvelle session
    try:
        yield db       # Passe la session au code qui l'a demandée
    finally:
        db.close()     # S'assure que la session est fermée, même en cas d'erreur
