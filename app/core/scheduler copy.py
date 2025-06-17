# app/core/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

# Importe la fonction run_scanner du service scanner
from app.services.scanner import run_scanner
# Importe SessionLocal pour obtenir une session de base de données
from app.core.database import SessionLocal
# Importe les paramètres de configuration de l'application
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialise le planificateur en arrière-plan
scheduler = BackgroundScheduler()

def run_scanner_job():
    """
    Fonction wrapper exécutée par APScheduler.
    Elle gère la création et la fermeture de la session SQLAlchemy pour le scanner.
    """
    db_session: Session = SessionLocal() # Crée une nouvelle session pour ce job
    try:
        logger.info("Début de l'exécution planifiée du scanner de sauvegardes.")
        # Appelle la fonction principale du scanner
        run_scanner(db_session)
        logger.info("Exécution planifiée du scanner de sauvegardes terminée avec succès.")
    except Exception as e:
        # Capture toutes les exceptions et les logue pour éviter que le job ne crashe le scheduler
        logger.error(f"Erreur lors de l'exécution du job du scanner de sauvegardes : {e}", exc_info=True)
    finally:
        # S'assure que la session de base de données est toujours fermée
        db_session.close()
        logger.debug("Session de base de données fermée pour le job du scanner.")

def start_scheduler():
    """
    Démarre le planificateur et ajoute le job du scanner.
    """
    if not scheduler.running:
        # Ajoute le job pour exécuter run_scanner_job à un intervalle défini
        scheduler.add_job(
            run_scanner_job,
            'interval',
            minutes=settings.SCANNER_INTERVAL_MINUTES,
            id='backup_scanner_main_job',
            replace_existing=True,
            #misfire_grace_time=60 # Permet au job de s'exécuter jusqu'à 60 secondes après l'heure prévue
        )
        logger.info(f"Job 'backup_scanner_main_job' ajouté au planificateur. Intervalle : {settings.SCANNER_INTERVAL_MINUTES} minutes.")
        scheduler.start()
        logger.info("Planificateur APScheduler démarré.")
    else:
        logger.info("Le planificateur est déjà en cours d'exécution.")

def shutdown_scheduler():
    """
    Arrête proprement le planificateur.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Planificateur APScheduler arrêté.")
    else:
        logger.info("Le planificateur n'était pas en cours d'exécution.") 