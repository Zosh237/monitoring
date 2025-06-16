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
from config.settings import settings # Pour le patching correct

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
        scheduler.shutdown(wait=True)
    yield
    logger.info(f"{COLOR_BLUE}--- Nettoyage après test : Arrêt du scheduler ---{COLOR_RESET}")
    if scheduler.running:
        scheduler.shutdown(wait=True)

@pytest.fixture
def mock_db_session():
    """
    Fixture pour mocker une session SQLAlchemy.
    """
    mock_session = MagicMock(spec=Session)
    return mock_session

@pytest.fixture
def mock_session_local(mock_db_session):
    """
    Fixture pour mocker SessionLocal et s'assurer qu'elle retourne notre mock_db_session.
    """
    with patch('app.core.scheduler.SessionLocal') as mock:
        mock.return_value = mock_db_session
        yield mock

@pytest.fixture
def mock_run_scanner():
    """
    Fixture pour mocker la fonction run_scanner du module scanner.
    """
    with patch('app.core.scheduler.run_scanner') as mock:
        yield mock

@pytest.fixture
def mock_settings():
    """
    Fixture pour mocker les paramètres de configuration.
    """
    with patch('app.core.scheduler.settings') as mock_settings:
        mock_settings.SCANNER_INTERVAL_MINUTES = 0.1  # 6 secondes pour les tests
        yield mock_settings

def test_scheduler_start_and_shutdown(reset_scheduler_state):
    """
    Teste que le scheduler démarre et s'arrête correctement.
    """
    logger.info(f"{COLOR_BLUE}--- Test 1: Démarrage et arrêt du scheduler ---{COLOR_RESET}")
    assert not scheduler.running
    start_scheduler()
    time.sleep(0.2)
    assert scheduler.running
    logger.info(f"{COLOR_GREEN}✓ Le scheduler a démarré.{COLOR_RESET}")

    shutdown_scheduler()
    time.sleep(0.2)
    assert not scheduler.running
    logger.info(f"{COLOR_GREEN}✓ Le scheduler s'est arrêté.{COLOR_RESET}")

def test_scheduler_job_execution(mock_run_scanner, mock_session_local, mock_settings, reset_scheduler_state):
    """
    Teste que le job est ajouté et que run_scanner_job est exécuté.
    """
    logger.info(f"{COLOR_BLUE}--- Test 2: Exécution du job du scheduler ---{COLOR_RESET}")
    
    # Exécuter directement run_scanner_job pour tester son comportement
    run_scanner_job()
    
    # Vérifier que run_scanner a été appelé avec la bonne session
    mock_run_scanner.assert_called_once_with(mock_session_local.return_value)
    logger.info(f"{COLOR_GREEN}✓ run_scanner a été appelé par le scheduler.{COLOR_RESET}")

def test_run_scanner_job_db_session_management(mock_run_scanner, mock_session_local):
    """
    Teste que run_scanner_job crée et ferme correctement une session DB.
    """
    logger.info(f"{COLOR_BLUE}--- Test 3: Gestion de la session DB par le job ---{COLOR_RESET}")
    
    # Exécuter run_scanner_job
    run_scanner_job()
    
    # Vérifier que SessionLocal a été appelé pour créer une session
    mock_session_local.assert_called_once()
    
    # Vérifier que run_scanner a été appelé avec la session
    mock_run_scanner.assert_called_once_with(mock_session_local.return_value)
    
    logger.info(f"{COLOR_GREEN}✓ Session DB créée et passée à scanner correctement.{COLOR_RESET}")

def test_run_scanner_job_exception_handling(mock_run_scanner, mock_session_local, caplog):
    """
    Teste que run_scanner_job gère les exceptions sans crasher le processus.
    """
    logger.info(f"{COLOR_BLUE}--- Test 4: Gestion des exceptions par le job ---{COLOR_RESET}")
    
    # Simuler une exception dans run_scanner
    mock_run_scanner.side_effect = Exception("Erreur simulée dans le scanner")

    with caplog.at_level(logging.ERROR):
        run_scanner_job()
        
        # Vérifier que l'erreur a été loguée
        assert "Erreur lors de l'exécution du job du scanner de sauvegardes" in caplog.text
        assert "Erreur simulée dans le scanner" in caplog.text
        logger.info(f"{COLOR_GREEN}✓ L'exception a été loguée comme prévu.{COLOR_RESET}")

def test_scheduler_not_start_if_running(reset_scheduler_state, caplog):
    """
    Teste que le scheduler ne démarre pas s'il est déjà en cours.
    """
    logger.info(f"{COLOR_BLUE}--- Test 5: Le scheduler ne démarre pas s'il est déjà en cours ---{COLOR_RESET}")
    start_scheduler()
    time.sleep(0.2)
    assert scheduler.running
    
    with caplog.at_level(logging.INFO):
        start_scheduler()
        assert "Le planificateur est déjà en cours d'exécution." in caplog.text
        logger.info(f"{COLOR_GREEN}✓ Le scheduler n'a pas redémarré inutilement.{COLOR_RESET}")
    
    shutdown_scheduler()

def test_scheduler_not_shutdown_if_not_running(reset_scheduler_state, caplog):
    """
    Teste que le scheduler ne s'arrête pas s'il n'est pas en cours.
    """
    logger.info(f"{COLOR_BLUE}--- Test 6: Le scheduler ne s'arrête pas s'il n'est pas en cours ---{COLOR_RESET}")
    assert not scheduler.running
    
    with caplog.at_level(logging.INFO):
        shutdown_scheduler()
        assert "Le planificateur n'était pas en cours d'exécution." in caplog.text
        logger.info(f"{COLOR_GREEN}✓ Le scheduler n'a pas tenté d'arrêter inutilement.{COLOR_RESET}") 