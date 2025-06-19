# app/core/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.scanner_MVP import run_new_scanner  # Import du nouveau scanner
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialise le planificateur en arrière-plan
scheduler = BackgroundScheduler()

def run_new_scanner_job():
    """
    Fonction wrapper exécutée par APScheduler.
    Elle déclenche l'exécution du scanner sans passer d'arguments.
    """
    try:
        logger.info("Début de l'exécution planifiée du scanner de sauvegardes.")
        # Appelle la fonction principale du scanner sans passer de session DB (elle s'en charge en interne)
        run_new_scanner()
        logger.info("Exécution planifiée du scanner de sauvegardes terminée avec succès.")
    except Exception as e:
        # Capture toutes les exceptions et les logue pour éviter que le job ne crashe le scheduler
        logger.error(f"Erreur lors de l'exécution du job du scanner de sauvegardes : {e}", exc_info=True)
    finally:
        logger.debug("Job du scanner terminé.")

def start_scheduler():
    """
    Démarre le planificateur et ajoute le job du scanner.
    """
    if not scheduler.running:
        # Ajoute le job pour exécuter run_new_scanner_job à un intervalle défini
        scheduler.add_job(
            run_new_scanner_job,
            'interval',
            minutes=settings.SCANNER_INTERVAL_MINUTES,
            id='backup_scanner_main_job',
            replace_existing=True,
            misfire_grace_time=90,  # Facultatif, permet au job de s'exécuter jusqu'à 60 secondes après l'heure prévue
            max_instances=1,
            coalesce=True,
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
