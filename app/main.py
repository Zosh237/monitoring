import logging.config
import os
from fastapi import FastAPI
from app.core.database import Base, engine

# --- Configuration du Logging ---
# Chemin vers le fichier de configuration YAML du logging
LOGGING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'logging.yaml')

# Charger la configuration du logging
if os.path.exists(LOGGING_CONFIG_PATH):
    logging.config.fileConfig(LOGGING_CONFIG_PATH, disable_existing_loggers=False)
else:
    # Fallback pour le logging si le fichier de configuration n'est pas trouvé
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - [%(name)s] - %(levelname)s - %(message)s')

# Obtenir un logger pour cette application
logger = logging.getLogger('app') # 'app' correspond au nom défini dans logging.yaml

#--- Initialisation de l'Application FastAPI ---
app = FastAPI(
    title="Serveur de Monitoring de Sauvegardes",
    description="API pour surveiller l'état et l'intégrité des sauvegardes de bases de données.",
    version="0.1.0",
)

# --- Événements au démarrage de l'application ---
@app.on_event("startup")
async def startup_event():
    logger.info("Démarrage de l'application FastAPI...")
    # Crée les tables de la base de données si elles n'existent pas encore.
    # Ceci est fait au démarrage de l'application.
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Tables de la base de données vérifiées/créées.")
    except Exception as e:
        logger.critical(f"Erreur CRITIQUE lors de la création des tables de la base de données: {e}")
        # En production, vous voudriez peut-être terminer l'application ici si la DB est cruciale.

    logger.info("Application prête.")

# --- Endpoint de test simple ---
@app.get("/")
async def read_root():
    logger.info("Requête reçue sur l'endpoint racine (/).")
    return {"message": "Serveur de Monitoring de Sauvegardes est en ligne!"}

# --- Exemple d'utilisation du logger ailleurs dans le code ---
# (Pour démontrer comment vous l'utiliserez dans d'autres modules)
# Créez ce fichier si vous voulez tester : app/core/exceptions.py
#try:
#    import app.core.exceptions
#    logger.debug("Le module exceptions a été importé.")
#except ImportError:
#    logger.warning("Le module exceptions n'a pas pu être importé. Il est peut-être absent.")
