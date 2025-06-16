# API de Surveillance des Sauvegardes

## Vue d'ensemble

Cette API RESTful, construite avec FastAPI, permet de gérer et surveiller les sauvegardes de bases de données. Elle offre des endpoints pour gérer les jobs de sauvegarde attendus et suivre leur statut.

## Structure du Projet

```
app/
├── api/
│   ├── api.py
│   └── endpoints/
│       ├── expected_backup_jobs.py
│       └── backup_entries.py
├── core/
│   ├── config.py
│   └── database.py
├── crud/
│   ├── expected_backup_job.py
│   └── backup_entry.py
├── schemas/
│   ├── expected_backup_job.py
│   └── backup_entry.py
└── main.py
```

## Endpoints Disponibles

### Jobs de Sauvegarde (`/api/v1/jobs/`)

- `POST /` : Créer un nouveau job de sauvegarde
- `GET /{job_id}` : Récupérer un job spécifique
- `GET /` : Lister tous les jobs (avec pagination)
- `PUT /{job_id}` : Mettre à jour un job
- `DELETE /{job_id}` : Supprimer un job

### Entrées de Sauvegarde (`/api/v1/entries/`)

- `GET /{entry_id}` : Récupérer une entrée spécifique
- `GET /` : Lister toutes les entrées (avec pagination)
- `GET /by_job/{job_id}` : Lister les entrées d'un job spécifique

## Modèles de Données

### ExpectedBackupJob

```python
class ExpectedBackupJobBase(BaseModel):
    database_name: str
    agent_id_responsible: str
    company_name: str
    city: str
    expected_hour_utc: int
    expected_minute_utc: int
    backup_frequency: BackupFrequency
    final_storage_path_template: str
```

### BackupEntry

```python
class BackupEntryInDB(BaseModel):
    id: int
    expected_job_id: int
    status: JobStatus
    backup_timestamp_utc: datetime
    backup_hash: Optional[str]
    backup_size_bytes: Optional[int]
    error_message: Optional[str]
    created_at: datetime
```

## Configuration

L'application utilise un fichier `.env` pour la configuration avec les paramètres suivants :

- `DATABASE_URL` : URL de connexion à la base de données
- `SMTP_*` : Configuration du serveur SMTP pour les notifications
- `CORS_ORIGINS` : Liste des origines autorisées pour CORS

## Sécurité

- Validation des données avec Pydantic
- Gestion des erreurs HTTP appropriée
- Configuration CORS sécurisée
- Variables d'environnement pour les données sensibles

## Documentation

La documentation interactive de l'API est disponible aux endpoints suivants :
- `/docs` : Documentation Swagger UI
- `/redoc` : Documentation ReDoc

## Tests

Les tests unitaires et d'intégration sont disponibles dans le dossier `tests/` :
- Tests des modèles Pydantic
- Tests des opérations CRUD
- Tests des endpoints API
- Tests de validation des données

## Démarrage

1. Installer les dépendances :
```bash
pip install -r requirements.txt
```

2. Configurer les variables d'environnement dans `.env`

3. Lancer l'application :
```bash
uvicorn app.main:app --reload
```

## Développement Futur

- Ajout d'authentification JWT
- Implémentation de rate limiting
- Ajout de métriques de performance
- Intégration avec des outils de monitoring
- Support pour d'autres types de notifications 