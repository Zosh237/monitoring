Prompt d'implémentation du Scheduler et des Tests
Objectif Général
Mettre en place le planificateur automatique (APScheduler) pour exécuter le scanner de sauvegardes à intervalles réguliers. Ce prompt inclut également le développement de tests unitaires et d'intégration robustes pour garantir le bon fonctionnement de cette nouvelle fonctionnalité. L'implémentation doit se faire sans modifier ou casser le code existant.

Module à Implémenter : Le Planificateur (Scheduler)
Concept
Le planificateur est un composant essentiel qui permet d'automatiser l'exécution de tâches périodiques. Dans notre cas, il orchestrera l'appel à la fonction run_scanner (qui se trouve dans app/services/scanner.py) à des intervalles prédéfinis. Nous utiliserons APScheduler en mode BackgroundScheduler, ce qui signifie qu'il s'exécutera dans un thread séparé en arrière-plan, sans bloquer l'application principale (l'API FastAPI).

Algorithme Détaillé
Création du module app/core/scheduler.py :

Ce module encapsulera toute la logique liée au démarrage, à l'arrêt et à la gestion des jobs du planificateur.

Il importera BackgroundScheduler d'APScheduler.

Il importera run_scanner depuis app/services/scanner.py.

Il importera SessionLocal (le callable pour obtenir une session DB) et engine depuis app/core/database.py.

Il définira une fonction run_scanner_job qui sera le wrapper exécuté par le scheduler. Cette fonction sera responsable de :

Créer une nouvelle session de base de données à chaque exécution du job.

Appeler run_scanner en lui passant cette session.

Gérer les exceptions qui pourraient survenir lors de l'exécution de run_scanner.

Assurer la fermeture de la session de base de données (même en cas d'erreur).

Il définira une fonction start_scheduler qui initialisera et démarrera le BackgroundScheduler, ajoutera le run_scanner_job avec un intervalle configurable (par exemple, toutes les 15 minutes), et gérera la journalisation (logging). Le job aura un id fixe pour permettre le remplacement en cas de redémarrage.

Il définira une fonction shutdown_scheduler qui arrêtera proprement le planificateur.

Modification de la configuration (config/settings.py) :

Ajouter une variable pour configurer l'intervalle d'exécution du scanner (par exemple, SCANNER_INTERVAL_MINUTES).

Intégration dans l'application principale (app/main.py) :

Utiliser les décorateurs @app.on_event("startup") et @app.on_event("shutdown") de FastAPI pour appeler respectivement start_scheduler() et shutdown_scheduler(). Cela garantira que le planificateur démarre avec l'application et s'arrête proprement.

Implémentation du Code (Fichiers à créer/modifier)
Voici les fichiers à implémenter ou à étendre.

1. Création de app/core/scheduler.py

# app/core/scheduler.py
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session # Importer Session pour le type hinting

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
        # 'id' est utilisé pour identifier le job et le remplacer s'il existe déjà
        # 'replace_existing=True' est utile pour éviter les doublons si le service redémarre
        # 'misfire_grace_time' permet une petite tolérance si le système est trop occupé
        scheduler.add_job(
            run_scanner_job,
            'interval',
            minutes=settings.SCANNER_INTERVAL_MINUTES,
            id='backup_scanner_main_job',
            replace_existing=True,
            misfire_grace_time=60 # Permet au job de s'exécuter jusqu'à 60 secondes après l'heure prévue
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


2. Extension de config/settings.py

Ajouter la ligne suivante dans la classe Settings:

# config/settings.py (extrait)
# ... autres imports ...
import os # Assurez-vous que os est importé

class Settings(BaseSettings):
    # ... autres paramètres ...

    # Paramètres pour le scanner et le planificateur
    SCANNER_INTERVAL_MINUTES: int = int(os.getenv("SCANNER_INTERVAL_MINUTES", 15)) # Intervalle par défaut de 15 minutes

    # ... autres paramètres ...

3. Extension de app/main.py

Intégrer les fonctions start_scheduler et shutdown_scheduler aux événements de démarrage et d'arrêt de FastAPI.

# app/main.py (extrait)
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

# Assurez-vous d'importer le scheduler
from app.core.scheduler import start_scheduler, shutdown_scheduler

# ... autres imports ...

# Créer les tables de base de données (si elles n'existent pas)
# Base.metadata.create_all(bind=engine) # Cette ligne est déjà présente, ne pas la dupliquer

logger = logging.getLogger(__name__)

app = FastAPI(
    title="API de Surveillance des Sauvegardes",
    description="API pour gérer et consulter les jobs de sauvegarde et leurs statuts.",
    version="1.0.0",
)

# Dépendance pour obtenir une session de base de données (déjà présente)
# def get_db(): ...

@app.on_event("startup")
async def startup_event():
    """
    Gestionnaire d'événements de démarrage de l'application.
    Démarre le planificateur APScheduler.
    """
    logger.info("Démarrage de l'application FastAPI...")
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

# ... Le reste de votre code d'API (endpoints) ...

4. Vérification de app/services/scanner.py

Assurez-vous que la fonction run_scanner dans app/services/scanner.py accepte bien un objet Session comme argument, comme prévu. D'après le code fourni précédemment, c'est déjà le cas.

# app/services/scanner.py (extrait, pour vérification, pas de modification nécessaire ici)
# ...
from sqlalchemy.orm import Session
# ...

# Fonction d'entrée pour le scheduler (si non encapsulée dans une classe plus grande)
# C'est cette fonction qui sera appelée par APScheduler.
def run_scanner(session: Session): # Assurez-vous que cette signature est correcte
    """
    Fonction principale pour exécuter le scan des sauvegardes.
    Elle initialise BackupScanner et exécute scan_all_jobs.
    """
    # ... votre logique de scanner existante ...
    scanner = BackupScanner(session)
    scanner.scan_all_jobs()
    session.commit() # Important pour persister les changements du scanner
    # ...

Tests pour le Module Scheduler
Il est crucial de tester le comportement du planificateur pour s'assurer qu'il démarre, s'arrête, et exécute les jobs comme prévu.

Objectif des Tests
Vérifier que le scheduler démarre et s'arrête correctement.

Confirmer qu'un job est bien ajouté et qu'il appelle la fonction cible (run_scanner_job).

S'assurer que run_scanner_job gère correctement la session de base de données et les exceptions.

Création du fichier de test : tests/test_scheduler.py
# tests/test_scheduler.py
import pytest
import logging
import time
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from datetime import datetime

# Ajustez le répertoire racine du projet au PYTHONPATH.
import sys
import os
sys.path.append(os.path.abspath('.'))

# Importe les modules à tester
from app.core.scheduler import start_scheduler, shutdown_scheduler, scheduler, run_scanner_job
from app.services.scanner import run_scanner # On va le mocker
from app.core.database import SessionLocal # On va le mocker

# Configuration du logging pour les tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Couleurs pour les logs de test
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_YELLOW = '\033[93m'
COLOR_BLUE = '\033[94m'
COLOR_RESET = '\033[0m'

@pytest.fixture(autouse=True)
def reset_scheduler_state():
    """
    Fixture pour s'assurer que le scheduler est arrêté avant et après chaque test.
    """
    logger.info(f"{COLOR_BLUE}--- Préparation du test : Arrêt du scheduler si actif ---{COLOR_RESET}")
    if scheduler.running:
        scheduler.shutdown(wait=False) # Shutdown non bloquant
        # Attendre un court instant pour s'assurer de l'arrêt si possible
        time.sleep(0.1)
    yield
    logger.info(f"{COLOR_BLUE}--- Nettoyage après test : Arrêt du scheduler ---{COLOR_RESET}")
    if scheduler.running:
        scheduler.shutdown(wait=False)
        time.sleep(0.1)

@pytest.fixture
def mock_db_session():
    """
    Fixture pour mocker une session SQLAlchemy.
    """
    mock_session = MagicMock(spec=Session)
    yield mock_session
    mock_session.close.assert_called_once() # S'assurer que la session est fermée

@pytest.fixture
def mock_session_local(mock_db_session):
    """
    Fixture pour mocker SessionLocal et s'assurer qu'elle retourne notre mock_db_session.
    """
    with patch('app.core.database.SessionLocal') as mock:
        mock.return_value = mock_db_session
        yield mock

@pytest.fixture
def mock_run_scanner():
    """
    Fixture pour mocker la fonction run_scanner du module scanner.
    """
    with patch('app.services.scanner.run_scanner') as mock:
        yield mock

# Test 1: Vérifier le démarrage et l'arrêt du scheduler
def test_scheduler_start_and_shutdown(reset_scheduler_state):
    """
    Teste que le scheduler démarre et s'arrête correctement.
    """
    logger.info(f"{COLOR_BLUE}--- Test 1: Démarrage et arrêt du scheduler ---{COLOR_RESET}")
    assert not scheduler.running
    start_scheduler()
    time.sleep(0.1) # Laisser un petit temps pour que le thread démarre
    assert scheduler.running
    logger.info(f"{COLOR_GREEN}✓ Le scheduler a démarré.{COLOR_RESET}")

    shutdown_scheduler()
    time.sleep(0.1) # Laisser un petit temps pour que le thread s'arrête
    assert not scheduler.running
    logger.info(f"{COLOR_GREEN}✓ Le scheduler s'est arrêté.{COLOR_RESET}")

# Test 2: Vérifier qu'un job est ajouté et exécuté
def test_scheduler_job_execution(mock_run_scanner, mock_session_local, reset_scheduler_state):
    """
    Teste que le job est ajouté et que run_scanner_job est exécuté.
    On ne teste pas l'intervalle exact, mais qu'il est capable de s'exécuter.
    """
    logger.info(f"{COLOR_BLUE}--- Test 2: Exécution du job du scheduler ---{COLOR_RESET}")

    # Patch temporaire pour simuler un intervalle très court pour le test
    with patch('config.settings.settings.SCANNER_INTERVAL_MINUTES', 0.01): # Très court intervalle pour le test
        start_scheduler()
        time.sleep(0.5) # Attendre assez longtemps pour que le job ait une chance de s'exécuter

        # Vérifier que run_scanner_job a été appelé
        # Attention: dans un BackgroundScheduler, le job est lancé dans un thread séparé.
        # Il faut s'assurer que le job a eu le temps de s'exécuter.
        # Ici, on ne peut pas directement vérifier l'appel de run_scanner_job facilement.
        # On va vérifier que run_scanner (qui est appelé par run_scanner_job) a été appelé.
        mock_run_scanner.assert_called_once_with(mock_session_local.return_value)
        logger.info(f"{COLOR_GREEN}✓ run_scanner a été appelé par le scheduler.{COLOR_RESET}")

        shutdown_scheduler()
        logger.info(f"{COLOR_GREEN}✓ Le test d'exécution du job est complet.{COLOR_RESET}")


# Test 3: Vérifier la gestion de la session DB dans run_scanner_job
def test_run_scanner_job_db_session_management(mock_run_scanner, mock_session_local):
    """
    Teste que run_scanner_job crée et ferme correctement une session DB.
    """
    logger.info(f"{COLOR_BLUE}--- Test 3: Gestion de la session DB par le job ---{COLOR_RESET}")
    run_scanner_job()
    
    mock_session_local.assert_called_once() # Vérifie que SessionLocal a été appelée pour créer une session
    mock_session_local.return_value.close.assert_called_once() # Vérifie que la session a été fermée
    mock_run_scanner.assert_called_once_with(mock_session_local.return_value) # Vérifie que la session est passée à run_scanner
    logger.info(f"{COLOR_GREEN}✓ Session DB créée, passée à scanner et fermée correctement.{COLOR_RESET}")

# Test 4: Vérifier la gestion des exceptions dans run_scanner_job
def test_run_scanner_job_exception_handling(mock_run_scanner, mock_session_local, caplog):
    """
    Teste que run_scanner_job gère les exceptions sans crasher le processus.
    """
    logger.info(f"{COLOR_BLUE}--- Test 4: Gestion des exceptions par le job ---{COLOR_RESET}")
    mock_run_scanner.side_effect = Exception("Erreur simulée dans le scanner")

    with caplog.at_level(logging.ERROR): # Capture les logs de niveau ERROR
        run_scanner_job()
        
        # Vérifie que l'erreur a été loguée
        assert "Erreur lors de l'exécution du job du scanner de sauvegardes" in caplog.text
        assert "Erreur simulée dans le scanner" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ L'exception a été loguée comme prévu.{COLOR_RESET}")

    # S'assurer que la session est toujours fermée même en cas d'exception
    mock_session_local.return_value.close.assert_called_once()
    logger.info(f"{COLOR_GREEN}✓ Session DB fermée même après une exception.{COLOR_RESET}")

# Test 5: Ne démarre pas le scheduler s'il est déjà en cours
def test_scheduler_not_start_if_running(reset_scheduler_state, caplog):
    logger.info(f"{COLOR_BLUE}--- Test 5: Le scheduler ne démarre pas s'il est déjà en cours ---{COLOR_RESET}")
    start_scheduler()
    time.sleep(0.1) # Laisser le temps de démarrer
    assert scheduler.running
    
    with caplog.at_level(logging.INFO):
        start_scheduler() # Tente de démarrer à nouveau
        assert "Le planificateur est déjà en cours d'exécution." in caplog.text
        logger.info(f"{COLOR_GREEN}✓ Le scheduler n'a pas redémarré inutilement.{COLOR_RESET}")
    
    shutdown_scheduler()

# Test 6: Le scheduler ne s'arrête pas s'il n'est pas en cours
def test_scheduler_not_shutdown_if_not_running(reset_scheduler_state, caplog):
    logger.info(f"{COLOR_BLUE}--- Test 6: Le scheduler ne s'arrête pas s'il n'est pas en cours ---{COLOR_RESET}")
    assert not scheduler.running
    
    with caplog.at_level(logging.INFO):
        shutdown_scheduler() # Tente d'arrêter quand il n'est pas en cours
        assert "Le planificateur n'était pas en cours d'exécution." in caplog.text
        logger.info(f"{COLOR_GREEN}✓ Le scheduler n'a pas tenté d'arrêter inutilement.{COLOR_RESET}")


Considérations pour les Tests
Isolation : L'utilisation de unittest.mock.patch est essentielle pour isoler le scheduler des dépendances externes comme la base de données (SessionLocal) ou la logique de scan (run_scanner). Cela permet de tester le scheduler lui-même sans dépendre du comportement des autres modules.

Fixtures Pytest : Les fixtures sont utilisées pour configurer l'environnement de test (comme le mock de la session DB) et pour nettoyer après chaque test (reset_scheduler_state).

time.sleep() : Dans les tests de threading avec BackgroundScheduler, de petits time.sleep() sont parfois nécessaires pour donner au thread du scheduler le temps de démarrer ou d'exécuter son job. Cependant, il faut être prudent car cela peut rendre les tests non déterministes si les durées sont trop justes. Pour des tests plus robustes d'exécution de job, des techniques d'attente basées sur des conditions (plutôt que des délais fixes) peuvent être utilisées, mais pour ce niveau d'implémentation, cela devrait suffire.

caplog : La fixture caplog de pytest est utilisée pour capturer les messages de log et s'assurer que les erreurs sont bien journalisées.

Ce plan détaillé, avec les modifications de code et les tests inclus, permettra une implémentation complète et vérifiée du planificateur sans impacter le code existant.