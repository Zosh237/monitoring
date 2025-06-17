from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config.settings import settings

import os

print(f"Chemin absolu de la base principale : {os.path.abspath(settings.DATABASE_URL)}")

# Moteur pour la base principale
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

# Moteur pour la base de test
TEST_DATABASE_URL = "sqlite:///./data/db/test_sql_app.db"  # ✅ Base séparée pour les tests
test_engine = create_engine(
    TEST_DATABASE_URL,
    echo=False,  # Moins de logs pour les tests
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
)

# Sessions pour base principale et tests
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Déclaration des modèles
Base = declarative_base()

# Fonction pour obtenir une session de la base principale
def get_db():
    db = SessionLocal()
    if db.bind.dialect.name == "sqlite":
        db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        db.close()

# Fonction pour obtenir une session de la base de test
def get_test_db():
    db = TestSessionLocal()
    if db.bind.dialect.name == "sqlite":
        db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        db.close()
