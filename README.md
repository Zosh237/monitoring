# monitoring
Serveur de Monitoring de Sauvegardes
Table des Matières
Introduction

Fonctionnalités

Architecture

Prérequis

Démarrage Rapide

Via Docker Compose (Recommandé)

Développement Local (Environnement Virtuel)

Tests

Configuration

API Endpoints (à venir)

Structure du Projet

Contribuer (à venir)

Licence (à venir)

1. Introduction
Ce projet implémente un serveur centralisé pour le monitoring de l'état et de l'intégrité des sauvegardes de bases de données. Il est conçu pour recevoir les sauvegardes de plusieurs agents distants, les valider, gérer leur stockage en ne conservant que la dernière version saine, et notifier les administrateurs en cas d'anomalie.

2. Fonctionnalités
Réception et organisation des fichiers de sauvegarde et des rapports de statut des agents.

Validation autonome des fichiers de sauvegarde (hachage et taille) côté serveur.

Détection des statuts : succès, échec (de l'agent ou du transfert), manquant, intégrité de transfert compromise, base de données inchangée (HASH_MISMATCH).

Promotion atomique des sauvegardes validées vers une arborescence finale structurée.

Enregistrement détaillé de l'historique des événements de sauvegarde dans une base de données.

Notifications configurables (e-mail) en cas d'alerte.

Interface web simple pour visualiser les statuts (à venir).

3. Architecture
Le système est composé de :

Agents Distants : Effectuent les sauvegardes, les compressent, les transfèrent via rsync vers le serveur, et envoient un rapport STATUS.json global.

Serveur Central (Application Dockerisée) :

Zone de Dépôt/Staging : /mnt/agent_deposits/ pour la réception initiale des fichiers des agents.

Zone de Sauvegardes Validées : /mnt/validated_backups/ pour le stockage final des sauvegardes saines.

Application Python (FastAPI) : Exécute un scanner planifié qui gère la validation, le déplacement et la notification.

Base de Données (SQLite en dev / PostgreSQL en prod) : Stocke la configuration des jobs et l'historique détaillé.

4. Prérequis
Docker et Docker Compose installés.

Python 3.9+ et pip installés (pour le développement local et la gestion de venv).

5. Démarrage Rapide
Via Docker Compose (Recommandé)
C'est la méthode privilégiée pour le développement et la production, car elle encapsule toutes les dépendances.

Cloner le dépôt (si applicable) :

git clone [URL_DU_DEPOT]
cd serveur-de-monitoring-de-sauvegardes # ou le nom de votre dossier racine

Préparer le fichier d'environnement :
Copiez le modèle et ajustez les valeurs si nécessaire. Ne versionnez jamais votre fichier .env avec des secrets !

cp .env.example .env
# Ouvrez .env et configurez les variables (ex: SMTP si vous testez les notifications)

Lancer l'application :

docker compose up --build -d

--build : Construit les images Docker (nécessaire la première fois ou après des modifications du Dockerfile).

-d : Lance les conteneurs en arrière-plan.

Initialiser la base de données (première fois ou après un changement de schéma) :
Ceci crée ou recrée les tables de la base de données.

docker compose exec app python scripts/init_database.py --reset

--reset : Supprime les tables existantes avant de les recréer (utile pour les changements de schéma en développement).

Accéder à l'API :
L'API FastAPI devrait être accessible à l'adresse : http://localhost:8000

Voir les logs :

docker compose logs -f app

Développement Local (Environnement Virtuel)
Pour travailler directement sur le code Python sans Docker.

Créer et activer l'environnement virtuel :

python3 -m venv venv
# Sur Linux/macOS
source venv/bin/activate
# Sur Windows (CMD)
# venv\Scripts\activate.bat
# Sur Windows (PowerShell)
# .\venv\Scripts\Activate.ps1

Installer les dépendances :

pip install -r requirements.txt

Initialiser la base de données :

python scripts/init_database.py --reset

Lancer l'application (pour le développement local) :
(Note: L'application ne sera pas automatiquement déclenchée par un scheduler comme avec Docker, mais vous pouvez tester les endpoints FastAPI.)

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

--reload : Redémarre l'application à chaque modification de fichier.

6. Tests
Tests Unitaires des Utilitaires (local)
Service de Validation (app/services/validation_service.py) :

python test_validation.py

Service de Manipulation de Fichiers (app/utils/file_operations.py) :

python test_file_operations.py

Service de Dates/Heures (app/utils/datetime_utils.py) :

python test_datetime_utils.py

(Plus de tests unitaires seront ajoutés pour les services scanner, manager, etc.)

7. Configuration
Les paramètres de l'application sont gérés via le fichier config/settings.py et peuvent être surchargés par les variables d'environnement définies dans le fichier .env à la racine du projet. Consultez .env.example pour les variables disponibles.

8. API Endpoints (à venir)
Des endpoints API seront exposés via FastAPI pour interroger l'état des sauvegardes et l'historique.

/api/jobs : Liste des jobs de sauvegarde attendus.

/api/jobs/{job_id}/history : Historique des événements pour un job spécifique.

/health : Vérification de santé de l'application.

9. Structure du Projet
monitoring_server/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
│
├── config/
│   ├── settings.py
│   └── logging.yaml
│
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── database.py
│   │   └── exceptions.py
│   ├── models/
│   │   ├── models.py
│   │   └── schemas.py
│   ├── api/
│   │   ├── monitoring.py
│   │   └── health.py
│   ├── services/
│   │   ├── backup_manager.py
│   │   ├── scanner.py
│   │   ├── notifier.py
│   │   └── validation_service.py
│   └── utils/
│       ├── crypto.py
│       ├── file_operations.py
│       └── datetime_utils.py
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   └── templates/
│       └── dashboard.html
│
├── scripts/
│   └── init_database.py
│
└── tests/
    ├── unit/
    │   ├── test_models.py
    │   ├── test_validation_service.py
    │   ├── test_scanner.py
    │   ├── test_backup_manager.py
    │   └── test_file_operations.py
    └── conftest.py

10. Contribuer (à venir)
Guide pour les contributions.

11. Licence (à venir)
Informations sur la licence du projet.
