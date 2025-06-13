# Documentation du Projet de Monitoring des Sauvegardes

## 1. Vue d'ensemble
Ce projet est un système de monitoring des sauvegardes de bases de données, conçu pour suivre et valider les sauvegardes automatiques de plusieurs sites et entreprises.

### 1.1 Architecture
- **Base de données** : SQLite (pour les tests) / PostgreSQL (pour la production)
- **Framework** : SQLAlchemy pour l'ORM
- **Structure** : Architecture modulaire avec séparation claire des responsabilités

## 2. Composants Principaux

### 2.1 Modèles de Données (`app/models/models.py`)
#### Enums
- `JobStatus` : États possibles d'un job de sauvegarde
  - OK, FAILED, MISSING, HASH_MISMATCH, TRANSFER_INTEGRITY_FAILED, UNKNOWN
- `BackupFrequency` : Fréquences de sauvegarde
  - DAILY, WEEKLY, MONTHLY, HOURLY, ONCE
- `BackupEntryStatus` : États des entrées de sauvegarde
  - SUCCESS, FAILED, MISSING, HASH_MISMATCH, TRANSFER_INTEGRITY_FAILED

#### Tables Principales
1. **ExpectedBackupJob**
   - Configuration des jobs de sauvegarde attendus
   - Champs clés : company_name, city, neighborhood, database_name
   - Horaires : expected_hour_utc, expected_minute_utc
   - Chemins : agent_deposit_path_template, final_storage_path_template

2. **BackupEntry**
   - Historique des événements de sauvegarde
   - Suivi des statuts et validations
   - Informations détaillées sur les processus (backup, compression, transfert)

### 2.2 Services

#### Scanner (`app/services/scanner.py`)
- Classe `BackupScanner` : Cœur du système de monitoring
- Fonctionnalités principales :
  - Scan des jobs de sauvegarde
  - Validation des rapports STATUS.json
  - Gestion des statuts et des entrées
  - Archivage des rapports

#### Validation Service (`app/services/validation_service.py`)
- Validation des fichiers STATUS.json
- Vérification de la fraîcheur des rapports
- Validation des données de sauvegarde

## 3. Flux de Travail

### 3.1 Cycle de Monitoring
1. **Initialisation**
   - Configuration des jobs de sauvegarde
   - Définition des chemins et horaires

2. **Exécution**
   - Scan périodique des jobs
   - Vérification des rapports STATUS.json
   - Validation des sauvegardes

3. **Traitement**
   - Mise à jour des statuts
   - Création des entrées d'historique
   - Archivage des rapports

### 3.2 Gestion des Erreurs
- Détection des sauvegardes manquantes
- Validation de l'intégrité des fichiers
- Gestion des échecs de transfert

## 4. Tests

### 4.1 Scénarios de Test (`test_scanner.py`)
1. **Scénario 1** : Sauvegarde réussie pour un site avec deux BDs
2. **Scénario 2** : Sauvegarde manquante pour un site entier
3. **Scénario 3** : Échec + Succès sur même site/rapport
4. **Scénario 4** : STATUS.json trop ancien
5. **Scénario 5** : Job avec cycle 20h, scanné tôt
6. **Scénario 6** : Rapport non pertinent

## 5. Configuration

### 5.1 Paramètres Importants
- `SCANNER_REPORT_COLLECTION_WINDOW_MINUTES` : Fenêtre de collecte des rapports
- `MAX_STATUS_FILE_AGE_DAYS` : Âge maximum des fichiers STATUS.json
- `BACKUP_STORAGE_ROOT` : Racine du stockage des sauvegardes
- `VALIDATED_BACKUPS_BASE_PATH` : Chemin des sauvegardes validées

## 6. Bonnes Pratiques

### 6.1 Sécurité
- Validation des hachages SHA256
- Vérification des timestamps
- Archivage sécurisé des rapports

### 6.2 Performance
- Indexation des champs fréquemment utilisés
- Gestion efficace des sessions DB
- Nettoyage automatique des fichiers temporaires

## 7. Maintenance

### 7.1 Nettoyage
- Archivage automatique des rapports
- Gestion des fichiers temporaires
- Rotation des logs

### 7.2 Surveillance
- Monitoring des statuts
- Alertes sur les échecs
- Historique des opérations

## 8. Dépendances
- SQLAlchemy
- Python 3.x
- Bibliothèques standard Python (datetime, json, os, etc.)

## 9. Limitations et Améliorations Futures
- Support de plus de types de bases de données
- Interface web pour la gestion
- Système de notifications avancé
- Support de la compression multi-niveaux 