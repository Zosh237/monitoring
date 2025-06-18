FROM python:3.11-slim

# Définir le dossier de travail
WORKDIR /monitoring

# Copier les fichiers de dépendances
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l’application
COPY . .

# Créer les répertoires pour les volumes montés
RUN mkdir -p /mnt/backups /mnt/validated

# Variables d’environnement
ENV BACKUP_STORAGE_ROOT=/mnt/backups
ENV VALIDATED_BACKUPS_BASE_PATH=/mnt/validated

# Exposer le port pour FastAPI
EXPOSE 8000

# Lancement via Uvicorn (à adapter selon l’emplacement réel de ton app)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
