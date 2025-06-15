Plan Détaillé : Planificateur, Notifications et API
Nous allons détailler les étapes pour implémenter le planificateur automatique, le système de notification pour les alertes, et la première version de l'API RESTful pour la consultation des données.

Phase 1 (Suite) : Finalisation de la Logique Métier et Planification
2. Mise en Place du Planificateur (APScheduler)
Concept : Le scanner (actuellement la fonction run_scanner) doit être exécuté automatiquement et périodiquement sans intervention manuelle. APScheduler est une bibliothèque Python qui permet de planifier des tâches (jobs) pour qu'elles s'exécutent à des intervalles définis (par exemple, toutes les heures, toutes les minutes).

Algorithme :

Initialiser APScheduler.

Définir le JobStore (où les jobs planifiés seront stockés si l'application redémarre). Pour un démarrage simple, une MemoryJobStore peut suffire, mais pour la persistance, un SQLAlchemyJobStore serait idéal pour stocker les jobs dans la même base de données que l'application.

Ajouter un job récurrent pour appeler la fonction run_scanner.

Démarrer le planificateur.

Gérer la fermeture propre du planificateur à l'arrêt de l'application.

Implémentation Détaillée :

Création du module app/core/scheduler.py :

Ce module contiendra la logique d'initialisation et de gestion d'APScheduler.

Il importera run_scanner depuis app/services/scanner.py et la session de base de données.

Exemple de structure :

# app/core/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import logging

from app.services.scanner import run_scanner
from app.core.database import SessionLocal, engine
from config.settings import settings

logger = logging.getLogger(__name__)

# Optionnel: Configurer un job store persistant si vous avez besoin que les jobs survivent aux redémarrages
# jobstores = {
#     'default': SQLAlchemyJobStore(url=settings.DATABASE_URL)
# }
# executors = {
#     'default': ThreadPoolExecutor(20),
#     'processpool': ProcessPoolExecutor(5)
# }
# job_defaults = {
#     'coalesce': False,
#     'max_instances': 1
# }

scheduler = BackgroundScheduler()

def start_scheduler():
    # Initialisation de la base de données pour les sessions du scheduler
    # Note: SessionLocal est un callable qui crée une nouvelle session
    # Chaque exécution de job doit obtenir sa propre session

    # Ajouter le job pour exécuter le scanner
    # Intervalle défini dans les settings (ex: settings.SCANNER_INTERVAL_MINUTES)
    # Utilise un job id fixe pour éviter les doublons si le scheduler redémarre sans persistance
    scheduler.add_job(
        run_scanner_job,
        'interval',
        minutes=settings.SCANNER_INTERVAL_MINUTES,
        id='backup_scanner_job',
        replace_existing=True,
        misfire_grace_time=60 # Tolérance de 60 secondes pour un démarrage manqué
    )
    logger.info(f"Planificateur démarré. Le scanner s'exécutera toutes les {settings.SCANNER_INTERVAL_MINUTES} minutes.")
    scheduler.start()

def run_scanner_job():
    """Fonction wrapper pour exécuter le scanner avec sa propre session DB."""
    db_session = SessionLocal()
    try:
        logger.info("Exécution du job du scanner de sauvegardes...")
        run_scanner(db_session)
        logger.info("Job du scanner de sauvegardes terminé.")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du scanner : {e}", exc_info=True)
    finally:
        db_session.close()

def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Planificateur arrêté.")


Mise à jour de config/settings.py :

Ajouter une variable de configuration pour l'intervalle du scanner, par exemple :

# config/settings.py
# ...
SCANNER_INTERVAL_MINUTES: int = 15 # Exécuter toutes les 15 minutes
# ...

Intégration dans le point d'entrée de l'application :

Le start_scheduler() doit être appelé une fois que l'application démarre. Si vous avez une application FastAPI, cela peut être fait via un événement de démarrage (@app.on_event("startup")).

Le shutdown_scheduler() doit être appelé à l'arrêt de l'application (@app.on_event("shutdown")).

Phase 2 : Communication et Visibilité
1. Implémentation du Système de Notification
Concept : En cas d'anomalie de sauvegarde (échec, fichier manquant, hachage incorrect), le système doit alerter les parties prenantes. Pour commencer, nous pourrions implémenter une notification par e-mail, car c'est un canal universel.

Algorithme :

Définir un service de notification générique capable d'envoyer des messages.

Dans le BackupScanner, après la mise à jour du BackupEntry et de ExpectedBackupJob, vérifier le statut final.

Si le statut est FAILED, MISSING, HASH_MISMATCH, ou TRANSFER_INTEGRITY_FAILED, déclencher l'envoi d'une notification.

La notification devrait inclure des détails clés : nom de la base de données, agent responsable, statut, et message d'erreur si disponible.

Implémentation Détaillée :

Création du module app/services/notification_service.py :

Ce module gérera l'envoi d'e-mails via smtplib ou une bibliothèque plus abstraite comme FastMail (si vous utilisez FastAPI).

Exemple simple avec smtplib (nécessite une configuration SMTP) :

# app/services/notification_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from config.settings import settings
from app.models.models import ExpectedBackupJob, BackupEntry, JobStatus, BackupEntryStatus

logger = logging.getLogger(__name__)

class NotificationError(Exception):
    """Exception personnalisée pour les erreurs de notification."""
    pass

def send_email_notification(
    recipient_email: str,
    subject: str,
    body: str
):
    """Envoie une notification par e-mail."""
    if not settings.EMAIL_HOST or not settings.EMAIL_PORT or \
       not settings.EMAIL_USERNAME or not settings.EMAIL_PASSWORD or \
       not settings.EMAIL_SENDER:
        logger.warning("Paramètres d'e-mail non configurés. Notification par e-mail désactivée.")
        return

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_SENDER
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
        server.starttls() # Chiffrement TLS
        server.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.EMAIL_SENDER, recipient_email, text)
        server.quit()
        logger.info(f"E-mail de notification envoyé à {recipient_email} avec le sujet : '{subject}'")
    except Exception as e:
        logger.error(f"Échec de l'envoi de l'e-mail de notification à {recipient_email}: {e}", exc_info=True)
        raise NotificationError(f"Échec de l'envoi de l'e-mail : {e}")

def notify_backup_status_change(
    job: ExpectedBackupJob,
    backup_entry: BackupEntry
):
    """Notifie d'un changement de statut de sauvegarde."""
    subject = f"Alerte Sauvegarde - {job.database_name} - Statut: {backup_entry.status.value.upper()}"
    body = (
        f"Cher administrateur,\n\n"
        f"Le statut de la sauvegarde pour la base de données '{job.database_name}' a changé.\n\n"
        f"Détails du Job :\n"
        f"  ID Job : {job.id}\n"
        f"  Nom BD : {job.database_name}\n"
        f"  Agent : {job.agent_id_responsible}\n"
        f"  Compagnie : {job.company_name}\n"
        f"  Ville : {job.city}\n\n"
        f"Détails de l'Entrée de Sauvegarde :\n"
        f"  ID Entrée : {backup_entry.id}\n"
        f"  Statut : {backup_entry.status.value.upper()}\n"
        f"  Horodatage Agent : {backup_entry.agent_report_timestamp_utc.isoformat() if backup_entry.agent_report_timestamp_utc else 'N/A'}\n"
        f"  Message d'erreur : {backup_entry.agent_transfer_error_message or 'Aucun'}\n"
        f"  Hachage Attendu (Agent) : {backup_entry.agent_reported_hash_sha256 or 'N/A'}\n"
        f"  Hachage Calculé (Serveur) : {backup_entry.server_calculated_staged_hash or 'N/A'}\n"
        f"  Taille Attendu (Agent) : {backup_entry.agent_reported_size_bytes or 'N/A'}\n"
        f"  Taille Calculée (Serveur) : {backup_entry.server_calculated_staged_size or 'N/A'}\n"
        f"  Statut global du Job : {job.current_status.value.upper()}\n\n"
        f"Veuillez vérifier le système.\n\n"
        f"Cordialement,\nVotre Système de Surveillance des Sauvegardes"
    )

    # Envoyer à l'adresse email de l'administrateur configurée
    if settings.ADMIN_EMAIL_RECIPIENT:
        send_email_notification(settings.ADMIN_EMAIL_RECIPIENT, subject, body)
    else:
        logger.warning("Aucun destinataire d'e-mail administrateur configuré pour les notifications.")


Mise à jour de config/settings.py :

Ajouter les variables de configuration pour l'envoi d'e-mails :

# config/settings.py
# ...
EMAIL_HOST: Optional[str] = os.getenv("EMAIL_HOST")
EMAIL_PORT: Optional[int] = os.getenv("EMAIL_PORT", 587)
EMAIL_USERNAME: Optional[str] = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD: Optional[str] = os.getenv("EMAIL_PASSWORD")
EMAIL_SENDER: Optional[str] = os.getenv("EMAIL_SENDER")
ADMIN_EMAIL_RECIPIENT: Optional[str] = os.getenv("ADMIN_EMAIL_RECIPIENT") # L'adresse où envoyer les alertes
# ...

Intégration dans app/services/scanner.py :

Après la logique de mise à jour des statuts dans _process_relevant_job (ou une méthode similaire), appeler notify_backup_status_change si un statut critique est détecté.

Par exemple, à la fin de _process_relevant_job ou dans une nouvelle méthode comme _update_and_notify_backup_entry:

# app/services/scanner.py (Extraits pour montrer l'intégration)
# ...
from app.services.notification_service import notify_backup_status_change, NotificationError
# ...

class BackupScanner:
    # ...
    def _process_job_status(self, db_session: Session, job: ExpectedBackupJob, relevant_entry: Dict[str, Any], staged_db_file_path: Optional[str]):
        # ... (votre logique existante pour déterminer backup_entry_status et job_status) ...

        # Après avoir déterminé backup_entry_status et job_status et mis à jour la DB:
        # Vérifier si une notification est nécessaire
        if backup_entry_status in [
            BackupEntryStatus.FAILED,
            BackupEntryStatus.MISSING,
            BackupEntryStatus.HASH_MISMATCH,
            BackupEntryStatus.TRANSFER_INTEGRITY_FAILED
        ]:
            try:
                # Créer ou récupérer l'objet BackupEntry pour la notification
                # Il est important que cette entrée soit déjà persistée en DB
                new_backup_entry = db_session.query(BackupEntry).filter_by(
                    expected_job_id=job.id,
                    agent_report_timestamp_utc=parse_iso_datetime(relevant_entry['operation_timestamp_utc']) # Ou un autre identifiant unique
                ).first()
                if new_backup_entry:
                    notify_backup_status_change(job, new_backup_entry)
            except NotificationError as e:
                self.logger.error(f"Échec de l'envoi de la notification pour le job {job.database_name}: {e}")
            except Exception as e:
                self.logger.error(f"Erreur inattendue lors de la notification pour le job {job.database_name}: {e}", exc_info=True)

        # ... (reste de la logique _process_job_status) ...

Phase 3 : Interface Utilisateur et Gestion
1. Développement de l'API RESTful
Concept : L'API RESTful permettra aux applications clientes (comme le futur tableau de bord web ou d'autres systèmes) d'interagir avec les données de surveillance des sauvegardes. Nous utiliserons FastAPI pour cela, car il est moderne, rapide et inclut une documentation interactive (Swagger UI) prête à l'emploi.

Algorithme :

Initialiser une application FastAPI.

Créer des schémas de données (Pydantic Models) pour la validation des requêtes et la sérialisation des réponses (pour ExpectedBackupJob et BackupEntry).

Définir des routers pour organiser les endpoints logiquement (par exemple, un pour les jobs, un pour les entrées de sauvegarde).

Implémenter les opérations de lecture (GET) pour lister tous les jobs et un job par ID.

Implémenter les opérations de lecture (GET) pour lister toutes les entrées de sauvegarde et une entrée par ID, avec des filtres (par job_id, status) et pagination.

Implémenter les opérations de création (POST) et de mise à jour (PUT) pour ExpectedBackupJob.

Implémentation Détaillée :

Installation des dépendances :

pip install fastapi uvicorn sqlalchemy pydantic

Fichier principal de l'API (main.py ou app/main.py) :

# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.core.database import SessionLocal, engine, Base
from app.models import models
from app.schemas import schemas # Nous allons créer ce fichier
from app.core.scheduler import start_scheduler, shutdown_scheduler # Pour le scheduler

# Créer les tables de base de données (si elles n'existent pas)
Base.metadata.create_all(bind=engine)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Surveillance des Sauvegardes",
    description="API pour gérer et consulter les jobs de sauvegarde et leurs statuts.",
    version="1.0.0",
)

# Dépendance pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    logger.info("Démarrage de l'application FastAPI...")
    start_scheduler() # Démarrer le planificateur
    logger.info("Application FastAPI démarrée et scheduler activé.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Arrêt de l'application FastAPI...")
    shutdown_scheduler() # Arrêter le planificateur
    logger.info("Application FastAPI arrêtée et scheduler désactivé.")

@app.get("/")
async def root():
    return {"message": "Bienvenue sur l'API de surveillance des sauvegardes ! Accédez à /docs pour la documentation."}

# --- Endpoints pour ExpectedBackupJob ---

@app.post("/jobs/", response_model=schemas.ExpectedBackupJobResponse, status_code=status.HTTP_201_CREATED)
def create_job(job: schemas.ExpectedBackupJobCreate, db: Session = Depends(get_db)):
    db_job = models.ExpectedBackupJob(**job.dict())
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

@app.get("/jobs/", response_model=List[schemas.ExpectedBackupJobResponse])
def read_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(models.ExpectedBackupJob).offset(skip).limit(limit).all()
    return jobs

@app.get("/jobs/{job_id}", response_model=schemas.ExpectedBackupJobResponse)
def read_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(models.ExpectedBackupJob).filter(models.ExpectedBackupJob.id == job_id).first()
    if job is None:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    return job

@app.put("/jobs/{job_id}", response_model=schemas.ExpectedBackupJobResponse)
def update_job(job_id: int, job_update: schemas.ExpectedBackupJobUpdate, db: Session = Depends(get_db)):
    db_job = db.query(models.ExpectedBackupJob).filter(models.ExpectedBackupJob.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job non trouvé")

    for key, value in job_update.dict(exclude_unset=True).items():
        setattr(db_job, key, value)

    db.commit()
    db.refresh(db_job)
    return db_job

@app.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)):
    db_job = db.query(models.ExpectedBackupJob).filter(models.ExpectedBackupJob.id == job_id).first()
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job non trouvé")
    db.delete(db_job)
    db.commit()
    return # No content

# --- Endpoints pour BackupEntry ---

@app.get("/backup_entries/", response_model=List[schemas.BackupEntryResponse])
def read_backup_entries(
    job_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(models.BackupEntry)
    if job_id:
        query = query.filter(models.BackupEntry.expected_job_id == job_id)
    if status:
        try:
            # Assurez-vous que le statut fourni est valide pour l'enum
            valid_status = models.BackupEntryStatus(status.lower())
            query = query.filter(models.BackupEntry.status == valid_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Statut de sauvegarde invalide: {status}")

    # Note: Pour les dates ou plages horaires, il faudra ajouter des paramètres spécifiques.
    entries = query.offset(skip).limit(limit).all()
    return entries

@app.get("/backup_entries/{entry_id}", response_model=schemas.BackupEntryResponse)
def read_backup_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.query(models.BackupEntry).filter(models.BackupEntry.id == entry_id).first()
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrée de sauvegarde non trouvée")
    return entry

# Pour exécuter l'application, utiliser : uvicorn app.main:app --reload

Création du module app/schemas/schemas.py :

Ce fichier définira les modèles Pydantic pour la validation des données d'entrée (requêtes) et de sortie (réponses de l'API).

Ces schémas refléteront les modèles de base de données mais permettront une validation et une sérialisation/désérialisation propres.

# app/schemas/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List
from app.models.models import JobStatus, BackupFrequency, BackupEntryStatus # Importe les Enums

# --- Schémas pour ExpectedBackupJob ---
class ExpectedBackupJobBase(BaseModel):
    database_name: str
    agent_id_responsible: str
    company_name: str
    city: str
    expected_hour_utc: int = Field(..., ge=0, le=23) # Heure attendue (UTC)
    expected_minute_utc: int = Field(..., ge=0, le=59) # Minute attendue (UTC)
    backup_frequency: BackupFrequency # Utilise l'Enum
    final_storage_path_template: str

class ExpectedBackupJobCreate(ExpectedBackupJobBase):
    # Des champs spécifiques à la création si nécessaire, sinon hérite tout de Base
    pass

class ExpectedBackupJobUpdate(ExpectedBackupJobBase):
    # Tous les champs sont optionnels pour une mise à jour partielle
    database_name: Optional[str] = None
    agent_id_responsible: Optional[str] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    expected_hour_utc: Optional[int] = Field(None, ge=0, le=23)
    expected_minute_utc: Optional[int] = Field(None, ge=0, le=59)
    backup_frequency: Optional[BackupFrequency] = None
    final_storage_path_template: Optional[str] = None
    current_status: Optional[JobStatus] = JobStatus.UNKNOWN # Statut du job
    last_checked_at_utc: Optional[datetime] = None
    last_successful_backup_utc: Optional[datetime] = None
    last_failed_backup_utc: Optional[datetime] = None
    email_for_notifications: Optional[EmailStr] = None # Exemple: email spécifique pour ce job

class ExpectedBackupJobResponse(ExpectedBackupJobBase):
    id: int
    current_status: JobStatus
    last_checked_at_utc: Optional[datetime]
    last_successful_backup_utc: Optional[datetime]
    last_failed_backup_utc: Optional[datetime]
    created_at: datetime

    class Config:
        orm_mode = True # Permet à Pydantic de lire des objets ORM

# --- Schémas pour BackupEntry ---
class BackupEntryBase(BaseModel):
    expected_job_id: int
    status: BackupEntryStatus # Utilise l'Enum
    agent_report_timestamp_utc: datetime
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
    previous_successful_hash_global: Optional[str] = None
    hash_comparison_result: Optional[bool] = None

class BackupEntryResponse(BackupEntryBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

Mise à jour de app/models/models.py :

Assurez-vous que les Enum (comme JobStatus, BackupFrequency, BackupEntryStatus) sont correctement définies et importables.

Vérifiez que tous les champs nécessaires pour les schémas Pydantic sont présents dans les modèles SQLAlchemy.

Ce plan vous fournira un backend API fonctionnel capable d'automatiser le scan via le scheduler et d'alerter en cas de problèmes. La prochaine étape sera de construire une interface utilisateur pour consommer cette API.