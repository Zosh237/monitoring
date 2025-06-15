Prompt d'implémentation de l'API FastAPI et des Tests
Objectif Général
Développer une API RESTful robuste en utilisant FastAPI pour permettre la gestion et la consultation des données relatives aux jobs de sauvegarde (ExpectedBackupJob) et à leurs entrées de statut (BackupEntry). Cette implémentation suivra une structure de projet logique et courante, en intégrant les services existants (scheduler, scanner, notifier) sans les modifier, et inclura des tests complets pour chaque fonctionnalité de l'API.

Architecture API et Concepts Clés
FastAPI : Framework web moderne, rapide (haute performance), basé sur les standards Python types hints, offrant une validation automatique des données, sérialisation/désérialisation, et une documentation OpenAPI (Swagger UI/ReDoc) intégrée.

Pydantic (app/schemas) : Utilisé pour définir les schémas de données pour les requêtes (body des requêtes) et les réponses (objets retournés par l'API). Il assure une validation automatique et la sérialisation/désérialisation des données.

SQLAlchemy (app/models) : L'ORM (Object-Relational Mapper) utilisé pour interagir avec la base de données. Les modèles sont déjà définis.

CRUD Operations (app/crud) : Une couche dédiée aux opérations de Création, Lecture (Read), Mise à Jour (Update), Suppression (Delete) de la base de données, permettant de séparer la logique d'accès aux données des endpoints de l'API.

Dépendances FastAPI : Utilisation de Depends pour injecter la session de base de données (get_db) dans les endpoints, assurant une gestion propre des sessions.

Modularité (app/api/endpoints) : Les routes API seront organisées en modules séparés (APIRouter) pour une meilleure maintenabilité et évolutivité.

Intégration existante : Le scheduler est déjà configuré pour démarrer et s'arrêter avec l'application FastAPI via les on_event dans app/main.py. Le scanner et le notifier sont des services backend appelés par le scheduler, et l'API se contentera de consulter les résultats de leurs opérations en base de données.

Structure de Dossiers Proposée (Exemple)
.
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── __init__.py
│   │       ├── expected_backup_jobs.py  # Endpoints pour ExpectedBackupJob
│   │       └── backup_entries.py        # Endpoints pour BackupEntry (lecture seule)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── database.py                  # Configuration DB et get_db()
│   │   └── scheduler.py                 # (Existe déjà)
│   ├── crud/
│   │   └── __init__.py
│   │   └── expected_backup_job.py       # Fonctions CRUD pour ExpectedBackupJob
│   │   └── backup_entry.py              # Fonctions de lecture pour BackupEntry
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py                    # (Existe déjà) Définitions SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── expected_backup_job.py       # Schémas Pydantic pour ExpectedBackupJob
│   │   └── backup_entry.py              # Schémas Pydantic pour BackupEntry
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scanner.py                   # (Existe déjà)
│   │   └── notifier.py                  # (Existe déjà)
│   └── main.py                          # Application FastAPI principale
├── config/
│   └── settings.py                      # (Existe déjà) Paramètres de l'application
├── tests/
│   ├── __init__.py
│   ├── test_api_expected_backup_jobs.py # Tests des endpoints ExpectedBackupJob
│   ├── test_api_backup_entries.py       # Tests des endpoints BackupEntry
│   ├── test_scheduler.py                # (Existe déjà)
│   ├── test_scanner.py                  # (Existe déjà)
│   ├── test_notifier.py                 # (Existe déjà)
│   └── conftest.py                      # Fixtures partagées pour les tests (DB, client API)
└── .env                                 # Variables d'environnement
└── README.md
└── requirements.txt

Algorithme Détaillé d'Implémentation de l'API
Phase 1: Définition des Schémas Pydantic (app/schemas)

app/schemas/expected_backup_job.py :

Créer une classe ExpectedBackupJobBase (Pydantic BaseModel) avec les champs communs pour la création et la mise à jour (ex: database_name, agent_id_responsible, company_name, city, expected_hour_utc, expected_minute_utc, backup_frequency, final_storage_path_template).

Créer une classe ExpectedBackupJobCreate qui hérite de ExpectedBackupJobBase (peut ne rien ajouter si Base suffit).

Créer une classe ExpectedBackupJobUpdate qui hérite de ExpectedBackupJobBase et rend tous les champs Optional pour les mises à jour partielles.

Créer une classe ExpectedBackupJobInDB qui hérite de ExpectedBackupJobBase et ajoute l'ID et les champs spécifiques à la base de données (ex: id, current_status, last_checked_at_utc, last_successful_backup_utc, last_failed_backup_utc, created_at). Configurer orm_mode = True pour la compatibilité avec SQLAlchemy.

app/schemas/backup_entry.py :

Créer une classe BackupEntryInDB (Pydantic BaseModel) pour représenter les données d'une entrée de sauvegarde. Inclure tous les champs pertinents du modèle SQLAlchemy BackupEntry (ex: id, expected_job_id, status, agent_report_timestamp_utc, etc.). Configurer orm_mode = True.

Phase 2: Création de la Couche CRUD (app/crud)

app/crud/expected_backup_job.py :

Créer des fonctions pour :

create_expected_backup_job(db: Session, job: ExpectedBackupJobCreate) : Crée un nouveau job.

get_expected_backup_job(db: Session, job_id: int) : Récupère un job par ID.

get_expected_backup_jobs(db: Session, skip: int = 0, limit: int = 100) : Récupère une liste de jobs avec pagination.

update_expected_backup_job(db: Session, job_id: int, job_update: ExpectedBackupJobUpdate) : Met à jour un job existant.

delete_expected_backup_job(db: Session, job_id: int) : Supprime un job.

app/crud/backup_entry.py :

Créer des fonctions pour (lecture seule) :

get_backup_entry(db: Session, entry_id: int) : Récupère une entrée par ID.

get_backup_entries(db: Session, skip: int = 0, limit: int = 100) : Récupère toutes les entrées.

get_backup_entries_by_job_id(db: Session, job_id: int, skip: int = 0, limit: int = 100) : Récupère les entrées pour un job spécifique.

Phase 3: Définition des Endpoints API (app/api/endpoints)

app/api/endpoints/expected_backup_jobs.py :

Initialiser un APIRouter.

Créer les endpoints pour les opérations CRUD sur ExpectedBackupJob :

POST /jobs/ : Crée un job. Prend ExpectedBackupJobCreate comme corps de requête et retourne ExpectedBackupJobInDB.

GET /jobs/{job_id} : Récupère un job. Retourne ExpectedBackupJobInDB.

GET /jobs/ : Récupère tous les jobs. Retourne List[ExpectedBackupJobInDB].

PUT /jobs/{job_id} : Met à jour un job. Prend ExpectedBackupJobUpdate comme corps de requête et retourne ExpectedBackupJobInDB.

DELETE /jobs/{job_id} : Supprime un job. Retourne un message de succès ou une erreur.

Utiliser la dépendance get_db pour injecter la session DB.

Gérer les erreurs HTTP (ex: HTTPException pour 404 Not Found).

app/api/endpoints/backup_entries.py :

Initialiser un APIRouter.

Créer les endpoints pour la lecture de BackupEntry :

GET /entries/{entry_id} : Récupère une entrée. Retourne BackupEntryInDB.

GET /entries/ : Récupère toutes les entrées. Retourne List[BackupEntryInDB].

GET /jobs/{job_id}/entries : Récupère les entrées pour un job spécifique. Retourne List[BackupEntryInDB].

Utiliser la dépendance get_db.

Gérer les erreurs HTTP.

Phase 4: Intégration dans l'Application Principale (app/main.py)

Importer tous les APIRouter des endpoints.

Ajouter les routeurs à l'application FastAPI principale en utilisant app.include_router().

Implémentation du Code (Fichiers à créer/modifier)
1. Création de app/schemas/expected_backup_job.py

# app/schemas/expected_backup_job.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.models import JobStatus, BackupFrequency # Importe les Enums existantes

class ExpectedBackupJobBase(BaseModel):
    """Schéma de base pour les données d'un ExpectedBackupJob."""
    database_name: str
    agent_id_responsible: str
    company_name: str
    city: str
    expected_hour_utc: int
    expected_minute_utc: int
    backup_frequency: BackupFrequency # Utilise l'Enum de models
    final_storage_path_template: str

class ExpectedBackupJobCreate(ExpectedBackupJobBase):
    """Schéma pour la création d'un ExpectedBackupJob."""
    # Aucun champ supplémentaire requis pour la création, hérite de Base
    pass

class ExpectedBackupJobUpdate(ExpectedBackupJobBase):
    """Schéma pour la mise à jour d'un ExpectedBackupJob (tous les champs sont optionnels)."""
    database_name: Optional[str] = None
    agent_id_responsible: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    expected_hour_utc: Optional[int] = None
    expected_minute_utc: Optional[int] = None
    backup_frequency: Optional[BackupFrequency] = None
    final_storage_path_template: Optional[str] = None
    # Vous pouvez ajouter ici des champs spécifiques à la mise à jour si nécessaire
    # Par exemple, pour changer explicitement le statut via l'API (non recommandé pour le statut auto)

class ExpectedBackupJobInDB(ExpectedBackupJobBase):
    """Schéma pour la représentation d'un ExpectedBackupJob tel qu'il est stocké en DB,
    incluant les champs générés par la DB ou mis à jour automatiquement.
    """
    id: int
    current_status: JobStatus # Utilise l'Enum de models
    last_checked_at_utc: Optional[datetime] = None
    last_successful_backup_utc: Optional[datetime] = None
    last_failed_backup_utc: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True # Active le mode ORM pour la compatibilité avec SQLAlchemy
        use_enum_values = True # Pour que les Enums soient sérialisées en leurs valeurs brutes (str)


2. Création de app/schemas/backup_entry.py

# app/schemas/backup_entry.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.models import BackupEntryStatus # Importe l'Enum existante

class BackupEntryInDB(BaseModel):
    """Schéma pour la représentation d'un BackupEntry tel qu'il est stocké en DB."""
    id: int
    expected_job_id: int
    status: BackupEntryStatus # Utilise l'Enum de models
    agent_report_timestamp_utc: Optional[datetime] = None
    agent_reported_hash_sha256: Optional[str] = None
    agent_reported_size_bytes: Optional[int] = None
    agent_compress_size_pre_compress: Optional[int] = None
    agent_compress_size_post_compress: Optional[int] = None
    agent_transfer_process_status: Optional[bool] = None
    agent_transfer_process_start_time: Optional[datetime] = None
    agent_transfer_process_timestamp: Optional[datetime] = None
    agent_transfer_error_message: Optional[str] = None
    agent_staged_file_name: Optional[str] = None
    agent_logs_summary: Optional[str] = None
    server_calculated_staged_hash: Optional[str] = None
    server_calculated_staged_size: Optional[int] = None
    hash_comparison_result: Optional[bool] = None
    previous_successful_hash_global: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True # Active le mode ORM pour la compatibilité avec SQLAlchemy
        use_enum_values = True # Pour que les Enums soient sérialisées en leurs valeurs brutes (str)


3. Création de app/crud/expected_backup_job.py

# app/crud/expected_backup_job.py
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.models.models import ExpectedBackupJob, JobStatus
from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate
from datetime import datetime, timezone

def create_expected_backup_job(db: Session, job: ExpectedBackupJobCreate) -> ExpectedBackupJob:
    """
    Crée un nouveau job de sauvegarde attendu dans la base de données.
    """
    db_job = ExpectedBackupJob(
        **job.model_dump(), # Convertit le Pydantic BaseModel en dict
        current_status=JobStatus.UNKNOWN, # Statut initial par défaut
        created_at=datetime.now(timezone.utc)
    )
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def get_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Récupère un job de sauvegarde attendu par son ID.
    """
    return db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()

def get_expected_backup_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[ExpectedBackupJob]:
    """
    Récupère une liste de jobs de sauvegarde attendus avec pagination.
    """
    return db.query(ExpectedBackupJob).offset(skip).limit(limit).all()

def update_expected_backup_job(db: Session, job_id: int, job_update: ExpectedBackupJobUpdate) -> Optional[ExpectedBackupJob]:
    """
    Met à jour un job de sauvegarde attendu existant.
    """
    db_job = db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()
    if db_job:
        update_data = job_update.model_dump(exclude_unset=True) # Ne met à jour que les champs fournis
        for key, value in update_data.items():
            setattr(db_job, key, value)
        db.commit()
        db.refresh(db_job)
    return db_job

def delete_expected_backup_job(db: Session, job_id: int) -> Optional[ExpectedBackupJob]:
    """
    Supprime un job de sauvegarde attendu par son ID.
    """
    db_job = db.query(ExpectedBackupJob).filter(ExpectedBackupJob.id == job_id).first()
    if db_job:
        db.delete(db_job)
        db.commit()
    return db_job


4. Création de app/crud/backup_entry.py

# app/crud/backup_entry.py
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.models import BackupEntry

def get_backup_entry(db: Session, entry_id: int) -> Optional[BackupEntry]:
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    return db.query(BackupEntry).filter(BackupEntry.id == entry_id).first()

def get_backup_entries(db: Session, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste d'entrées de sauvegarde avec pagination.
    """
    # Ordonne par date de création pour une meilleure lisibilité
    return db.query(BackupEntry).order_by(BackupEntry.created_at.desc()).offset(skip).limit(limit).all()

def get_backup_entries_by_job_id(db: Session, job_id: int, skip: int = 0, limit: int = 100) -> List[BackupEntry]:
    """
    Récupère une liste d'entrées de sauvegarde pour un job spécifique, avec pagination.
    """
    return db.query(BackupEntry).filter(BackupEntry.expected_job_id == job_id).order_by(BackupEntry.created_at.desc()).offset(skip).limit(limit).all()


5. Création de app/api/endpoints/expected_backup_jobs.py

# app/api/endpoints/expected_backup_jobs.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate, ExpectedBackupJobInDB
from app.crud import expected_backup_job as crud_job # Renomme pour éviter le conflit
from app.core.database import get_db # Importe la dépendance de la DB

router = APIRouter(
    prefix="/jobs",
    tags=["Expected Backup Jobs"],
    responses={404: {"description": "Non trouvé"}},
)

@router.post("/", response_model=ExpectedBackupJobInDB, status_code=status.HTTP_201_CREATED)
def create_job(job: ExpectedBackupJobCreate, db: Session = Depends(get_db)):
    """
    Crée un nouveau job de sauvegarde attendu.
    """
    db_job = crud_job.create_expected_backup_job(db=db, job=job)
    return db_job

@router.get("/{job_id}", response_model=ExpectedBackupJobInDB)
def read_job(job_id: int, db: Session = Depends(get_db)):
    """
    Récupère un job de sauvegarde attendu par son ID.
    """
    db_job = crud_job.get_expected_backup_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.get("/", response_model=List[ExpectedBackupJobInDB])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de tous les jobs de sauvegarde attendus.
    """
    jobs = crud_job.get_expected_backup_jobs(db=db, skip=skip, limit=limit)
    return jobs

@router.put("/{job_id}", response_model=ExpectedBackupJobInDB)
def update_job(job_id: int, job_update: ExpectedBackupJobUpdate, db: Session = Depends(get_db)):
    """
    Met à jour un job de sauvegarde attendu existant.
    """
    db_job = crud_job.update_expected_backup_job(db=db, job_id=job_id, job_update=job_update)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return db_job

@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """
    Supprime un job de sauvegarde attendu.
    """
    db_job = crud_job.delete_expected_backup_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")
    return {"message": "Job supprimé avec succès"}


6. Création de app/api/endpoints/backup_entries.py

# app/api/endpoints/backup_entries.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.schemas.backup_entry import BackupEntryInDB
from app.crud import backup_entry as crud_entry # Renomme pour éviter le conflit
from app.crud import expected_backup_job as crud_job # Pour vérifier l'existence du job
from app.core.database import get_db # Importe la dépendance de la DB

router = APIRouter(
    prefix="/entries",
    tags=["Backup Entries"],
    responses={404: {"description": "Non trouvé"}},
)

@router.get("/{entry_id}", response_model=BackupEntryInDB)
def read_entry(entry_id: int, db: Session = Depends(get_db)):
    """
    Récupère une entrée de sauvegarde par son ID.
    """
    db_entry = crud_entry.get_backup_entry(db=db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée de sauvegarde non trouvée")
    return db_entry

@router.get("/", response_model=List[BackupEntryInDB])
def read_entries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste de toutes les entrées de sauvegarde.
    """
    entries = crud_entry.get_backup_entries(db=db, skip=skip, limit=limit)
    return entries

@router.get("/by_job/{job_id}", response_model=List[BackupEntryInDB])
def read_entries_by_job(job_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Récupère une liste d'entrées de sauvegarde pour un job spécifique par son ID.
    """
    # Vérifier si le job existe avant de chercher ses entrées
    job = crud_job.get_expected_backup_job(db=db, job_id=job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job non trouvé")

    entries = crud_entry.get_backup_entries_by_job_id(db=db, job_id=job_id, skip=skip, limit=limit)
    return entries


7. Modification de app/main.py

# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

# Importe les routeurs des endpoints
from app.api.endpoints import expected_backup_jobs, backup_entries

# Assurez-vous d'importer le scheduler (déjà fait, mais pour rappel)
from app.core.scheduler import start_scheduler, shutdown_scheduler

# Importe les composants de la base de données (déjà fait, mais pour rappel)
from app.core.database import Base, engine, get_db, SessionLocal

# Créer les tables de base de données (si elles n'existent pas)
# Base.metadata.create_all(bind=engine) # Cette ligne est déjà présente, ne pas la dupliquer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Surveillance des Sauvegardes",
    description="API pour gérer et consulter les jobs de sauvegarde et leurs statuts.",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    """
    Gestionnaire d'événements de démarrage de l'application.
    Démarre le planificateur APScheduler et crée les tables DB.
    """
    logger.info("Démarrage de l'application FastAPI...")
    # Crée les tables si elles n'existent pas (assure la base prête)
    Base.metadata.create_all(bind=engine)
    logger.info("Tables de base de données vérifiées/créées.")
    start_scheduler() # Démarre le planificateur ici
    logger.info("Application FastAPI démarrée et planificateur activé.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Gestionnaire d'événements d'arrêt de l'application.
    Arrête le planificateur APScheduler proprement.
    """
    logger.info("Arrêt de l'application FastAPI...")
    shutdown_scheduler() # Arrête le planificateur ici
    logger.info("Application FastAPI arrêtée et planificateur désactivé.")

# Inclure les routeurs API
app.include_router(expected_backup_jobs.router)
app.include_router(backup_entries.router)

# Endpoint racine (optionnel, pour vérifier si l'API est en ligne)
@app.get("/")
async def root():
    return {"message": "API de Surveillance des Sauvegardes est en ligne"}

# ... (Le reste de votre code d'API existant, s'il y en a) ...

Tests pour l'API FastAPI
Les tests de l'API utiliseront pytest avec la classe TestClient de fastapi.testclient. Il est crucial de mocker la base de données pour isoler les tests d'API et s'assurer qu'ils ne dépendent pas d'une base de données réelle ou volatile.

Objectif des Tests
Tests End-to-End (API) : Simuler des requêtes HTTP aux endpoints de l'API et vérifier les réponses (statut HTTP, corps de réponse).

Isolation de la Base de Données : Utiliser une base de données en mémoire (SQLite) ou des mocks pour SessionLocal afin que chaque test soit indépendant et reproductible.

Validation des Schémas : S'assurer que les données envoyées et reçues respectent les schémas Pydantic définis.

Gestion des Erreurs : Tester les réponses en cas de données invalides, ressources non trouvées, etc.

Création des fichiers de test : tests/test_api_expected_backup_jobs.py et tests/test_api_backup_entries.py
1. tests/conftest.py (pour les fixtures partagées)

C'est une bonne pratique de créer un fichier conftest.py à la racine du dossier tests pour définir des fixtures réutilisables.

# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db # Importe Base et get_db du projet réel
import os
import sys

# Assurez-vous que le chemin du projet est dans PYTHONPATH
sys.path.append(os.path.abspath('.'))

# Configuration du logging pour les tests
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fixture pour la base de données SQLite en mémoire
@pytest.fixture(scope="module")
def test_db():
    """
    Crée une base de données SQLite en mémoire pour les tests.
    Chaque test module obtient sa propre base de données.
    """
    # Utilise une URL de base de données en mémoire
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine) # Crée les tables
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    # Remplace la dépendance get_db de l'application FastAPI
    app.dependency_overrides[get_db] = override_get_db
    yield
    # Nettoyage (non nécessaire pour une DB en mémoire après le module)
    Base.metadata.drop_all(bind=engine) # Supprime les tables après le module

@pytest.fixture(scope="module")
def client(test_db):
    """
    Crée un client de test FastAPI pour interagir avec l'API.
    """
    # Le client utilisera la DB en mémoire définie par test_db
    with TestClient(app) as c:
        yield c


2. tests/test_api_expected_backup_jobs.py

# tests/test_api_expected_backup_jobs.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

# Assurez-vous que le chemin du projet est dans PYTHONPATH
import sys
import os
sys.path.append(os.path.abspath('.'))

from app.models.models import ExpectedBackupJob, JobStatus, BackupFrequency
from app.schemas.expected_backup_job import ExpectedBackupJobCreate, ExpectedBackupJobUpdate

logger = logging.getLogger(__name__)

# Les fixtures 'client' et 'test_db' sont fournies par conftest.py

# Données de test pour un job de sauvegarde
job_data = {
    "database_name": "prod_db_alpha",
    "agent_id_responsible": "AGENT_PARIS_001",
    "company_name": "CompanyA",
    "city": "Paris",
    "expected_hour_utc": 18,
    "expected_minute_utc": 30,
    "backup_frequency": "daily",
    "final_storage_path_template": "/mnt/backups/{year}/{company_name}/{city}/{database_name}_backup.zip"
}

def test_create_expected_backup_job(client: TestClient, test_db: None):
    """
    Teste la création d'un job de sauvegarde attendu via l'API.
    """
    logger.info("--- Test: Création d'un job de sauvegarde ---")
    response = client.post("/jobs/", json=job_data)

    assert response.status_code == 201, f"Échec: Statut HTTP attendu 201, reçu {response.status_code}. Détails: {response.json()}"
    created_job = response.json()
    
    assert created_job["database_name"] == job_data["database_name"]
    assert created_job["agent_id_responsible"] == job_data["agent_id_responsible"]
    assert created_job["company_name"] == job_data["company_name"]
    assert created_job["current_status"] == JobStatus.UNKNOWN.value # Statut par défaut
    assert "id" in created_job
    assert "created_at" in created_job
    logger.info(f"✓ Job créé avec succès: {created_job['id']}")


def test_get_expected_backup_job(client: TestClient, test_db: None):
    """
    Teste la récupération d'un job de sauvegarde par ID.
    """
    logger.info("--- Test: Récupération d'un job par ID ---")
    # Crée d'abord un job pour le récupérer
    create_response = client.post("/jobs/", json=job_data)
    created_job_id = create_response.json()["id"]

    response = client.get(f"/jobs/{created_job_id}")
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    fetched_job = response.json()

    assert fetched_job["id"] == created_job_id
    assert fetched_job["database_name"] == job_data["database_name"]
    logger.info(f"✓ Job {created_job_id} récupéré avec succès.")


def test_get_expected_backup_job_not_found(client: TestClient, test_db: None):
    """
    Teste la récupération d'un job inexistant.
    """
    logger.info("--- Test: Récupération d'un job inexistant ---")
    response = client.get("/jobs/99999") # ID qui n'existe probablement pas
    assert response.status_code == 404, f"Échec: Statut HTTP attendu 404, reçu {response.status_code}. Détails: {response.json()}"
    assert "Job non trouvé" in response.json()["detail"]
    logger.info(f"✓ Réponse 404 correcte pour job inexistant.")


def test_get_all_expected_backup_jobs(client: TestClient, test_db: None):
    """
    Teste la récupération de tous les jobs de sauvegarde.
    """
    logger.info("--- Test: Récupération de tous les jobs ---")
    # Crée plusieurs jobs pour avoir une liste
    client.post("/jobs/", json=job_data)
    client.post("/jobs/", json={**job_data, "database_name": "dev_db"})

    response = client.get("/jobs/")
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    jobs = response.json()
    assert len(jobs) >= 2 # Au moins les deux que nous venons de créer
    logger.info(f"✓ {len(jobs)} jobs récupérés avec succès.")


def test_update_expected_backup_job(client: TestClient, test_db: None):
    """
    Teste la mise à jour d'un job de sauvegarde.
    """
    logger.info("--- Test: Mise à jour d'un job ---")
    # Crée d'abord un job
    create_response = client.post("/jobs/", json=job_data)
    created_job_id = create_response.json()["id"]

    update_data = {"expected_hour_utc": 20, "backup_frequency": "weekly"}
    response = client.put(f"/jobs/{created_job_id}", json=update_data)
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    updated_job = response.json()

    assert updated_job["id"] == created_job_id
    assert updated_job["expected_hour_utc"] == update_data["expected_hour_utc"]
    assert updated_job["backup_frequency"] == update_data["backup_frequency"]
    assert updated_job["database_name"] == job_data["database_name"] # Les autres champs ne doivent pas changer
    logger.info(f"✓ Job {created_job_id} mis à jour avec succès.")


def test_update_expected_backup_job_not_found(client: TestClient, test_db: None):
    """
    Teste la mise à jour d'un job inexistant.
    """
    logger.info("--- Test: Mise à jour d'un job inexistant ---")
    update_data = {"expected_hour_utc": 20}
    response = client.put("/jobs/99999", json=update_data)
    assert response.status_code == 404, f"Échec: Statut HTTP attendu 404, reçu {response.status_code}. Détails: {response.json()}"
    assert "Job non trouvé" in response.json()["detail"]
    logger.info(f"✓ Réponse 404 correcte pour la mise à jour d'un job inexistant.")


def test_delete_expected_backup_job(client: TestClient, test_db: None):
    """
    Teste la suppression d'un job de sauvegarde.
    """
    logger.info("--- Test: Suppression d'un job ---")
    # Crée d'abord un job à supprimer
    create_response = client.post("/jobs/", json=job_data)
    created_job_id = create_response.json()["id"]

    response = client.delete(f"/jobs/{created_job_id}")
    assert response.status_code == 204, f"Échec: Statut HTTP attendu 204, reçu {response.status_code}. Détails: {response.json()}"
    logger.info(f"✓ Job {created_job_id} supprimé avec succès.")

    # Vérifie qu'il n'est plus récupérable
    get_response = client.get(f"/jobs/{created_job_id}")
    assert get_response.status_code == 404, f"Échec: Job toujours trouvable après suppression."
    logger.info(f"✓ Job {created_job_id} confirmé comme supprimé (non trouvé).")


def test_delete_expected_backup_job_not_found(client: TestClient, test_db: None):
    """
    Teste la suppression d'un job inexistant.
    """
    logger.info("--- Test: Suppression d'un job inexistant ---")
    response = client.delete("/jobs/99999")
    assert response.status_code == 404, f"Échec: Statut HTTP attendu 404, reçu {response.status_code}. Détails: {response.json()}"
    assert "Job non trouvé" in response.json()["detail"]
    logger.info(f"✓ Réponse 404 correcte pour la suppression d'un job inexistant.")


3. tests/test_api_backup_entries.py

# tests/test_api_backup_entries.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

# Assurez-vous que le chemin du projet est dans PYTHONPATH
import sys
import os
sys.path.append(os.path.abspath('.'))

from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus
from app.crud.expected_backup_job import create_expected_backup_job
from app.core.database import SessionLocal # Nécessaire pour créer des entrées directement dans la DB de test

logger = logging.getLogger(__name__)

# Les fixtures 'client' et 'test_db' sont fournies par conftest.py

# Données de test pour un job de sauvegarde
job_data = {
    "database_name": "prod_db_entries",
    "agent_id_responsible": "AGENT_MARSEILLE_002",
    "company_name": "CompanyB",
    "city": "Marseille",
    "expected_hour_utc": 22,
    "expected_minute_utc": 0,
    "backup_frequency": "daily",
    "final_storage_path_template": "/mnt/backups/{year}/{company_name}/{city}/{database_name}_backup.zip"
}

def create_test_backup_entry(db: Session, job_id: int, status: BackupEntryStatus, timestamp: datetime) -> BackupEntry:
    """Helper pour créer une BackupEntry directement dans la DB de test."""
    entry = BackupEntry(
        expected_job_id=job_id,
        status=status,
        agent_report_timestamp_utc=timestamp,
        agent_reported_hash_sha256="test_hash",
        agent_reported_size_bytes=1024,
        created_at=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

def test_get_backup_entry(client: TestClient, test_db: None):
    """
    Teste la récupération d'une entrée de sauvegarde par ID.
    """
    logger.info("--- Test: Récupération d'une entrée de sauvegarde par ID ---")
    # Crée un job et une entrée
    db: Session = SessionLocal() # Obtient une session pour créer des données de test
    job = create_expected_backup_job(db, job_data)
    entry = create_test_backup_entry(db, job.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    db.close() # Important de fermer la session manuellement pour les helpers

    response = client.get(f"/entries/{entry.id}")
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    fetched_entry = response.json()

    assert fetched_entry["id"] == entry.id
    assert fetched_entry["expected_job_id"] == job.id
    assert fetched_entry["status"] == BackupEntryStatus.SUCCESS.value
    logger.info(f"✓ Entrée de sauvegarde {entry.id} récupérée avec succès.")


def test_get_backup_entry_not_found(client: TestClient, test_db: None):
    """
    Teste la récupération d'une entrée de sauvegarde inexistante.
    """
    logger.info("--- Test: Récupération d'une entrée de sauvegarde inexistante ---")
    response = client.get("/entries/99999")
    assert response.status_code == 404, f"Échec: Statut HTTP attendu 404, reçu {response.status_code}. Détails: {response.json()}"
    assert "Entrée de sauvegarde non trouvée" in response.json()["detail"]
    logger.info(f"✓ Réponse 404 correcte pour entrée inexistante.")


def test_get_all_backup_entries(client: TestClient, test_db: None):
    """
    Teste la récupération de toutes les entrées de sauvegarde.
    """
    logger.info("--- Test: Récupération de toutes les entrées de sauvegarde ---")
    db: Session = SessionLocal()
    job1 = create_expected_backup_job(db, job_data)
    create_test_backup_entry(db, job1.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc) - timedelta(days=1))
    create_test_backup_entry(db, job1.id, BackupEntryStatus.FAILED, datetime.now(timezone.utc))
    db.close()

    response = client.get("/entries/")
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    entries = response.json()
    assert len(entries) >= 2
    logger.info(f"✓ {len(entries)} entrées de sauvegarde récupérées avec succès.")


def test_get_backup_entries_by_job_id(client: TestClient, test_db: None):
    """
    Teste la récupération des entrées de sauvegarde pour un job spécifique.
    """
    logger.info("--- Test: Récupération des entrées par Job ID ---")
    db: Session = SessionLocal()
    job1 = create_expected_backup_job(db, job_data)
    job2_data = {**job_data, "database_name": "another_db", "agent_id_responsible": "AGENT_LYON_003"}
    job2 = create_expected_backup_job(db, job2_data)

    create_test_backup_entry(db, job1.id, BackupEntryStatus.SUCCESS, datetime.now(timezone.utc))
    create_test_backup_entry(db, job1.id, BackupEntryStatus.HASH_MISMATCH, datetime.now(timezone.utc) - timedelta(hours=1))
    create_test_backup_entry(db, job2.id, BackupEntryStatus.FAILED, datetime.now(timezone.utc))
    db.close()

    response = client.get(f"/entries/by_job/{job1.id}")
    assert response.status_code == 200, f"Échec: Statut HTTP attendu 200, reçu {response.status_code}. Détails: {response.json()}"
    entries_for_job1 = response.json()
    assert len(entries_for_job1) == 2
    assert all(e["expected_job_id"] == job1.id for e in entries_for_job1)
    logger.info(f"✓ {len(entries_for_job1)} entrées récupérées pour le Job {job1.id}.")

    response_job2 = client.get(f"/entries/by_job/{job2.id}")
    assert response_job2.status_code == 200
    entries_for_job2 = response_job2.json()
    assert len(entries_for_job2) == 1
    logger.info(f"✓ {len(entries_for_job2)} entrées récupérées pour le Job {job2.id}.")


def test_get_backup_entries_by_job_id_not_found(client: TestClient, test_db: None):
    """
    Teste la récupération des entrées pour un job inexistant.
    """
    logger.info("--- Test: Récupération des entrées par Job ID inexistant ---")
    response = client.get("/entries/by_job/99999")
    assert response.status_code == 404, f"Échec: Statut HTTP attendu 404, reçu {response.status_code}. Détails: {response.json()}"
    assert "Job non trouvé" in response.json()["detail"]
    logger.info(f"✓ Réponse 404 correcte pour job ID inexistant lors de la recherche d'entrées.")


Considérations pour les Tests
TestClient : Le TestClient simule les requêtes HTTP sans lancer un vrai serveur, ce qui est très rapide.

Base de Données en Mémoire : L'utilisation de sqlite:///:memory: avec SQLAlchemy est essentielle pour l'isolation des tests. Chaque session de test module aura sa propre base de données vierge.

app.dependency_overrides : Cette fonctionnalité de FastAPI permet de remplacer la dépendance get_db par une version qui fournit une session de la base de données de test en mémoire.

Organisation des Tests : Séparer les tests par ressource API (test_api_expected_backup_jobs.py, test_api_backup_entries.py) aide à la clarté et à la gestion.

Création de Données de Test : Pour tester les endpoints, il est souvent nécessaire de créer des données de test au préalable (en utilisant directement les fonctions CRUD ou les modèles SQLAlchemy avec la session de test).

Ce prompt détaillé fournira à l'IA toutes les informations nécessaires pour implémenter l'API FastAPI et ses tests de manière structurée et conforme aux meilleures pratiques.