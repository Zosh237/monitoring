# scripts/init_database.py
# Ce script est utilisé pour initialiser ou réinitialiser la base de données.
# Par défaut, il tente de créer les tables si elles n'existent pas.
# Une option de réinitialisation complète (suppression puis recréation) est fournie.

import sys
import os
import argparse # Pour gérer les arguments de la ligne de commande
import logging # Pour le logging

# Configure un logging de base pour ce script (indépendant du logging de l'app)
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ajoute le répertoire parent du script au PYTHONPATH pour que les imports 'app.core' et 'app.models' fonctionnent.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importe 'Base' et 'engine' depuis le module de base de données de notre application.
from app.core.database import Base, engine

# Importe explicitement tous les modèles pour que SQLAlchemy les connaisse.
# Base.metadata.create_all() a besoin de tous les modèles héritant de Base
# pour identifier les tables à créer.
import app.models.models

def init_db(reset_all: bool = False):
    """
    Crée les tables définies par les modèles SQLAlchemy si elles n'existent pas.
    Si reset_all est True, supprime toutes les tables avant de les recréer.

    Args:
        reset_all (bool): Si True, toutes les tables existantes sont supprimées
                          avant d'être recréées. Utile pour les changements de schéma.
    """
    if reset_all:
        logger.info("Mode RÉINITIALISATION COMPLÈTE activé : Suppression de toutes les tables existantes...")
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Toutes les tables ont été supprimées avec succès.")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression des tables : {e}")
            sys.exit(1) # Quitte si la suppression échoue

    logger.info("Tentative de CRÉATION/MISE À JOUR des tables de la base de données...")
    try:
        # create_all() ne crée que les tables qui n'existent pas déjà.
        # Pour les changements de colonnes dans des tables existantes,
        # une réinitialisation complète (reset_all=True) ou un outil de migration est nécessaire.
        Base.metadata.create_all(bind=engine)
        logger.info("Tables de la base de données créées ou vérifiées. Les nouvelles tables/champs ont été ajoutés si nécessaires.")
    except Exception as e:
        logger.critical(f"Erreur CRITIQUE lors de la création/vérification des tables : {e}")
        sys.exit(1) # Quitte si la création échoue


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Initialise ou réinitialise la base de données du serveur de monitoring."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprime toutes les tables existantes avant de les recréer. Utile pour les changements de schéma."
    )
    args = parser.parse_args()

    init_db(reset_all=args.reset)
