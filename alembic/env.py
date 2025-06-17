import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ajoutez le chemin racine du projet pour que vos modules soient trouvés.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importez la configuration de votre projet et Base depuis vos modules.
from config.settings import settings  # charge votre configuration
from app.core.database import Base  # la Base de SQLAlchemy
from app.models import models  # Assurez-vous que ce module charge tous vos modèles

config = context.config

fileConfig(config.config_file_name)

# Remplacez l'url dans alembic.ini par l'URL de votre configuration
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Définir la metadata à partir de Base.metadata
target_metadata = Base.metadata

# Debug : affichez les tables détectées (à retirer après vérification)
#print("Tables détectées :", list(target_metadata.tables.keys()))

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
