# Plan MVP - 5 Jours - Serveur de Monitoring de Sauvegardes

## 🎯 **Objectif MVP : Système Fonctionnel Minimum**

**Fonctionnalités essentielles uniquement :**
- Scanner automatique qui détecte SUCCESS/FAILED/MISSING
- Promotion staging → current_version
- API basique pour consulter les statuts
- Interface web simple
- Notifications email critiques

**Ce qu'on ÉLIMINE du MVP :**
- Dashboard sophistiqué
- HASH_MISMATCH (trop complexe pour MVP)
- Gestion avancée des erreurs
- Métriques détaillées
- Tests d'intégration complets

---

## 📅 **Planning 5 Jours - Mode Sprint**

### **JOUR 1 : Core Backend (8h)**

#### Matin (4h) : Fondations
```python
# 1h - Setup projet + Docker
mkdir backup-monitoring-server && cd backup-monitoring-server
# Structure basique + requirements.txt + docker-compose.yml

# 2h - Configuration + Modèles DB
config/settings.py          # Pydantic settings
app/models/database.py      # SQLAlchemy models (simplifiés)
scripts/init_database.py    # Init DB

# 1h - Tests fondations
test_database.py           # Tests modèles DB
```

#### Après-midi (4h) : Parser + Validation
```python
# 2h - Parser STATUS.json
app/services/validation_service.py    # Parser + validation JSON

# 1h - Scanner de base (V1)
app/services/backup_scanner.py        # Scanner basique (SUCCESS/FAILED seulement)

# 1h - Tests parser + scanner
test_validation_service.py
test_backup_scanner.py
```

**Livrable J1 :** DB + Parser + Scanner basique fonctionnels

# === RAPPORT DE FIN JOUR 1 ===

## 1. Analyse des fichiers principaux

### a) `app/models/models.py`
- Définit deux tables principales : `ExpectedBackupJob` (configuration attendue des sauvegardes) et `BackupEntry` (résultat d'une sauvegarde).
- Utilise SQLAlchemy ORM, des Enum pour les statuts, et des contraintes d'unicité pertinentes.
- Structure adaptée au MVP, conforme au plan (SUCCESS/FAILED/MISSING, pas de gestion avancée des erreurs ni de hash complexe pour l'instant).

### b) `app/core/database.py`
- Configure la connexion à la base via SQLAlchemy, en utilisant les settings Pydantic.
- Fournit la session et la base déclarative pour les modèles.
- Affiche le chemin absolu de la base pour le debug.

### c) `config/settings.py`
- Centralise la configuration (URL de la base, racine des backups, intervalle du scanner, jours attendus, timezone, etc.).
- Utilise Pydantic pour charger les variables d'environnement et un .env.
- Prêt pour extension future (Docker, prod, etc.).

### d) `config/logging.yaml`
- Définit une configuration de logging robuste (console + fichier, rotation, formats détaillés).
- Prêt pour usage en dev et prod.

### e) `scripts/init_database.py`
- Script d'initialisation de la base : importe les modèles, crée les tables si besoin.
- Utilise `Base.metadata.create_all(bind=engine)`.

## 2. Problème rencontré

- **Erreur lors de l'exécution de `scripts/init_database.py` :**
  - `ModuleNotFoundError: No module named 'app'`
  - Cause : le script était lancé directement (`python scripts/init_database.py`), ce qui ne permet pas à Python de reconnaître le dossier `app` comme un package (problème de PYTHONPATH).

## 3. Correction apportée

- **Solution :**
  - Exécuter le script comme un module avec le flag `-m` :
    ```bash
    venv\Scripts\python -m scripts.init_database
    ```
  - Cela permet à Python de traiter le projet comme un package, rendant les imports relatifs fonctionnels.
  - Résultat :
    - Connexion à la base réussie
    - Création des tables sans erreur
    - Logs SQLAlchemy affichés

## 4. Conseils et bonnes pratiques

- Toujours exécuter les scripts qui importent des modules du projet avec `-m` depuis la racine du projet.
- Vérifier que l'environnement virtuel est activé et que toutes les dépendances sont installées (`pip install -r requirements.txt`).
- Pour les tests automatisés, utiliser la même logique d'import.

## 5. Prochaines étapes (Jour 2)
- Développer le parser STATUS.json et le scanner de sauvegardes.
- Écrire les premiers tests unitaires sur la base et le parser.
- Continuer à travailler dans l'environnement virtuel pour garantir l'isolation des dépendances.

---

**Fin du rapport d'activité – Jour 1.**

---

### **JOUR 2 : Logique Métier Core (8h)**

#### Matin (4h) : Scanner Complet
```python
# 3h - Scanner avec logique temporelle
backup_scanner.py    # Ajouter détection MISSING (fenêtres de temps)
                     # Intégration avec DB (ExpectedBackupJob)

# 1h - Manager de promotion
backup_manager.py    # Staging → current_version (copie sécurisée)
```

#### Après-midi (4h) : Tests + Debug
```python
# 2h - Tests complets scanner
test_backup_scanner.py    # Cas SUCCESS/FAILED/MISSING

# 2h - Tests promotion + debug
test_backup_manager.py    # Tests copie fichiers
# Debugging et stabilisation
```

**Livrable J2 :** Scanner complet + Promotion fichiers + Tests

---

### **JOUR 3 : API + Interface (8h)**

#### Matin (4h) : API FastAPI
```python
# 2h - API de base
app/main.py              # FastAPI app
app/api/monitoring.py    # Endpoints essentiels :
                        # GET /api/jobs (liste jobs)
                        # GET /api/jobs/{id} (détail job)
                        # POST /api/jobs (créer job)

# 2h - Tests API
test_api.py             # Tests endpoints de base
```

#### Après-midi (4h) : Interface Web Basique
```html
<!-- 3h - Frontend minimaliste -->
frontend/templates/dashboard.html    <!-- Liste des jobs + statuts -->
frontend/static/css/style.css       <!-- CSS basique -->
frontend/static/js/app.js           <!-- JS pour refresh auto -->

<!-- 1h - Intégration frontend/backend -->
```

**Livrable J3 :** API fonctionnelle + Interface web basique

---

### **JOUR 4 : Scheduler + Notifications (8h)**

#### Matin (4h) : Automatisation
```python
# 2h - Scheduler APScheduler
app/core/scheduler.py    # Configuration scheduler
main.py                  # Intégration scheduler dans FastAPI

# 2h - Service de notification
app/services/notification_service.py    # Email basique pour FAILED/MISSING
```

#### Après-midi (4h) : Docker + Déploiement
```yaml
# 2h - Configuration Docker
Dockerfile              # Image application
docker-compose.yml       # Service complet
.env.example            # Variables d'environnement

# 2h - Tests déploiement
# Build + run + validation fonctionnement
```

**Livrable J4 :** Système automatisé + Dockerisé

---

### **JOUR 5 : Finalisation + Tests (8h)**

#### Matin (4h) : Tests de Bout en Bout
```python
# 2h - Scénarios de test complets
tests/integration/test_end_to_end.py    # Test complet avec vrais fichiers

# 2h - Documentation minimale
README.md               # Installation + configuration
docs/quick_start.md     # Guide de démarrage rapide
```

#### Après-midi (4h) : Polish + Livraison
```python
# 2h - Corrections bugs critiques
# Stabilisation des derniers problèmes

# 1h - Configuration production
# Variables d'environnement, logs, monitoring basique

# 1h - Package final
# Build final, documentation de déploiement
```

**Livrable J5 :** MVP complet et déployable

---

## ⚡ **Stratégie d'Exécution Rapide**

### **Simplifications MVP :**

1. **Base de données :** SQLite uniquement (pas PostgreSQL)
2. **Tests :** Unitaires essentiels seulement
3. **Interface :** HTML/CSS/JS vanilla (pas de framework)
4. **Notifications :** Email basique seulement
5. **Configuration :** Fichier .env simple
6. **Erreurs :** Gestion basique (logs + exceptions)

### **Architecture Épurée MVP :**
```
app/
├── main.py                    # FastAPI + scheduler
├── models/database.py         # Modèles SQLAlchemy
├── services/
│   ├── backup_scanner.py      # Scanner principal
│   ├── backup_manager.py      # Promotion fichiers
│   ├── validation_service.py  # Parser STATUS.json
│   └── notification_service.py # Notifications email
├── api/monitoring.py          # API endpoints
└── core/
    ├── database.py           # Connexion DB
    └── scheduler.py          # APScheduler
```

### **Tests Minimum Viable :**
```
tests/
├── test_validation_service.py    # Parser JSON
├── test_backup_scanner.py        # Logique scanner
├── test_backup_manager.py        # Promotion fichiers
└── test_api.py                   # Endpoints API
```

---

## 🎯 **Métriques de Réussite MVP**

**Fin Jour 5, le système doit :**
- ✅ Scanner automatiquement toutes les 15 minutes
- ✅ Détecter SUCCESS/FAILED/MISSING
- ✅ Promouvoir les fichiers staging → current_version
- ✅ Afficher les statuts dans une interface web
- ✅ Envoyer des emails en cas de FAILED/MISSING
- ✅ Être déployable via Docker
- ✅ Avoir une documentation de base

**Ce qui peut attendre après MVP :**
- HASH_MISMATCH detection
- Dashboard avancé avec graphiques
- Authentification
- Tests d'intégration poussés
- Migration PostgreSQL
- Monitoring avancé du système

---

## 🚀 **Démarrage Immédiat**

**Prêt ? On commence par quoi :**

1. **Setup projet (30 min)** - Structure + Docker + requirements.txt
2. **Configuration DB (1h)** - Models SQLAlchemy + settings Pydantic  
3. **Parser JSON (1h)** - Service de validation STATUS.json

**Quelle partie voulez-vous que je code en premier ?** 💻