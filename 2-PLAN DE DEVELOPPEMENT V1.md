Feuille de Route Détaillée : Étapes d'Implémentation du Monitoring de Sauvegardes
Ce document décompose notre projet de serveur de monitoring de sauvegardes en étapes d'implémentation claires et actionnables, en tenant compte de notre progression actuelle et des décisions de brainstorming.

1. Récapitulatif de l'État Actuel (Bases Solides)
Nous avons complété toutes les fondations essentielles du projet. C'est la base de notre progression future.

✅ Structure du Projet : Arborescence des dossiers conforme à la structure MVP.

✅ Environnement Docker : Dockerfile, docker-compose.yml, requirements.txt configurés et testés pour le démarrage de l'application FastAPI.

✅ Configuration : Fichiers config/settings.py (avec Pydantic) et config/logging.yaml mis en place pour une gestion centralisée des paramètres et de la journalisation.

✅ Base de Données (SQLite) : app/core/database.py (connexion SQLAlchemy) et app/models/models.py (modèles ExpectedBackupJob et BackupEntry mis à jour avec tous les nouveaux champs et statuts). Le script scripts/init_database.py est fonctionnel pour la réinitialisation.

✅ Service de Validation : app/services/validation_service.py (lecture et validation du STATUS.json) est implémenté et a été testé localement.

2. Prochaines Étapes d'Implémentation (Jour 1 - Après-midi et Jour 2 - Matin)
Nous allons maintenant nous concentrer sur le cœur de la logique métier : le scanner de sauvegardes.

Phase 1 : Logique du Scanner (Jour 1 - Après-midi et Jour 2 - Matin)
L'objectif est de développer le "cerveau" de l'application qui va analyser les rapports d'agents et les fichiers de sauvegarde.

Étape 1.1 : Implémentation du Service Utilitaire de Hachage (app/utils/crypto.py)
Avant que le scanner ne compare les hachages, il doit être capable de les calculer pour les fichiers reçus.

Concept : Créer une fonction utilitaire pour calculer le SHA256 d'un fichier volumineux de manière efficace.

Action :

Créer le fichier app/utils/crypto.py.

Implémenter une fonction calculate_file_sha256(file_path: str) -> str qui prend un chemin de fichier et retourne son hachage SHA256.

Utiliser des "chunks" pour gérer les fichiers de grande taille sans charger tout en mémoire.

Vérification : Écrire un petit script local pour tester la fonction avec un fichier de test (texte ou binaire).

Étape 1.2 : Implémentation du Service de Manipulation de Fichiers (app/utils/file_operations.py)
Le scanner devra créer des dossiers et déplacer des fichiers.

Concept : Créer des fonctions pour des opérations courantes sur les fichiers et dossiers (création de répertoire, déplacement/renommage atomique, suppression).

Action :

Créer le fichier app/utils/file_operations.py.

Implémenter des fonctions comme ensure_directory_exists(path: str), move_file(source_path: str, destination_path: str).

Pour move_file, veiller à utiliser une opération de déplacement atomique si possible (ex: os.replace ou shutil.move en s'assurant qu'il est atomique sur le même système de fichiers) pour éviter la perte de données en cas d'interruption.

Vérification : Tester ces fonctions avec des fichiers et dossiers temporaires.

Étape 1.3 : Implémentation du Service Utilitaire de Dates/Heures (app/utils/datetime_utils.py)
Pour la gestion des fenêtres de temps du scanner.

Concept : Fonctions pour convertir des timestamps (UTC vers local et inversement), obtenir des fenêtres de temps.

Action :

Créer le fichier app/utils/datetime_utils.py.

Implémenter des fonctions comme get_utc_now(), parse_iso_datetime(iso_string: str) -> datetime, format_datetime_to_iso(dt: datetime) -> str.

Définir une fonction pour déterminer la "fenêtre de temps attendue" pour un ExpectedBackupJob.

Vérification : Tester les fonctions avec des exemples de dates et de fuseaux horaires.

Étape 1.4 : Implémentation du Scanner Principal (app/services/scanner.py)
C'est le cœur de la logique de monitoring.

Concept : Le scanner va lire les ExpectedBackupJob de la DB, trouver les STATUS.json globaux, valider les fichiers de sauvegarde, déterminer les statuts et mettre à jour la DB.

Action :

Créer le fichier app/services/scanner.py.

Implémenter la fonction principale scan_backups(db: Session) qui :

Récupère tous les ExpectedBackupJob actifs de la base de données.

Pour chaque ExpectedBackupJob, détermine la fenêtre de temps et le chemin attendu du STATUS.json global (en utilisant agent_id_responsible et agent_log_deposit_path_template).

Tente de lire et valider le STATUS.json global (en utilisant validation_service).

Pour chaque base de données dans le STATUS.json global :

Récupère le ExpectedBackupJob correspondant.

Extrait les statuts de processus de l'agent.

Si transfer_process.status est true :

Construit le chemin du fichier stagé (agent_deposit_path_template).

Calcule server_calculated_staged_hash et server_calculated_staged_size (en utilisant crypto.py).

Compare ces valeurs avec agent_compress_hash_post_compress et agent_compress_size_post_compress. Si différence -> TRANSFER_INTEGRITY_FAILED.

Détermine le statut final (MISSING, FAILED, TRANSFER_INTEGRITY_FAILED, HASH_MISMATCH, SUCCESS).

Met à jour le previous_successful_hash_global dans la base de données pour la détection du HASH_MISMATCH pour le prochain scan.

Crée une BackupEntry détaillée en DB avec toutes les informations collectées.

Met à jour le current_status et last_checked_timestamp du ExpectedBackupJob.

Vérification : Test unitaire avec des données de test simulées (fichiers STATUS.json et structures de dossiers) pour vérifier tous les chemins de statut.

3. Prochaines Étapes : Promotion et Notifications (Jour 2 - Après-midi)
Une fois le scanner capable de déterminer les statuts, il doit agir en conséquence.

Phase 2 : Promotion des Fichiers et Notifications
Étape 2.1 : Implémentation du Service de Promotion (app/services/backup_manager.py)
Ce service sera appelé par le scanner pour gérer le déplacement des fichiers.

Concept : Fonctionnalité de déplacement atomique des fichiers validés vers leur destination finale et gestion des échecs.

Action :

Créer le fichier app/services/backup_manager.py.

Implémenter la fonction promote_backup(source_path: str, destination_template: str, job: ExpectedBackupJob) :

Construit le chemin de destination final en utilisant final_storage_path_template et les informations du job (année, entreprise, ville, nom de BD).

Crée l'arborescence de destination si elle n'existe pas.

Déplace atomiquement le fichier de source_path vers destination_path.

Gère la suppression de l'ancien fichier de destination si nécessaire (remplacement).

Implémenter une fonction handle_failed_staging(file_path: str, reason: str) pour gérer les fichiers qui ne sont pas promus (ex: déplacer vers un dossier de quarantaine ou simplement logguer).

Vérification : Tests unitaires pour la promotion et la gestion des échecs de promotion avec des fichiers réels.

Étape 2.2 : Implémentation du Service de Notification (app/services/notifier.py)
Concept : Envoi d'emails pour les alertes critiques.

Action :

Créer le fichier app/services/notifier.py.

Implémenter une fonction send_alert_email(recipients: str, subject: str, body: str).

Utiliser les paramètres SMTP de config/settings.py.

Vérification : Test de l'envoi d'un email (en utilisant un service SMTP de test ou une configuration réelle temporaire).

4. Intégration et Automatisation (Jour 3)
Phase 3 : Intégration et Planification
Étape 3.1 : Intégration du Scanner dans FastAPI (app/main.py)
Concept : Le scanner doit être exécuté périodiquement au sein de l'application FastAPI.

Action :

Dans app/main.py, configurer APScheduler.

Ajouter le scan_backups du scanner.py comme une tâche planifiée qui s'exécute toutes les SCANNER_INTERVAL_MINUTES (depuis settings.py).

Assurer que la session de base de données est correctement gérée pour la tâche du scheduler.

Vérification : Démarrer l'application Docker et vérifier les logs pour confirmer que le scanner se déclenche comme prévu.

Étape 3.2 : Mise en place des Endpoints API de base (app/api/monitoring.py, app/api/health.py)
Concept : Fournir une interface web simple pour visualiser le statut des jobs.

Action :

Dans app/api/monitoring.py, implémenter des endpoints pour :

GET /api/jobs : Lister tous les ExpectedBackupJob avec leur current_status.

GET /api/jobs/{job_id}/history : Afficher l'historique des BackupEntry pour un job donné.

Dans app/api/health.py, implémenter un simple GET /health qui renvoie un statut OK.

Enregistrer ces routes dans app/main.py.

Vérification : Tester les endpoints via un navigateur ou un outil comme Postman/curl.

5. Interface Web Simple (Jour 3 - Fin / Jour 4)
Phase 4 : Interface Utilisateur
Étape 4.1 : Développement du Frontend Minimaliste
Concept : Une page HTML statique pour afficher les données de l'API.

Action :

Développer frontend/templates/dashboard.html (structure HTML, inclure style.css et app.js).

Développer frontend/static/css/style.css (mise en forme basique).

Développer frontend/static/js/app.js (JavaScript pour appeler l'API et afficher les données sur la page).

Vérification : Accéder à la page via le navigateur et vérifier que les données des jobs s'affichent correctement.

6. Finalisation et Tests (Jour 4 - Fin / Jour 5)
Phase 5 : Tests et Documentation
Étape 5.1 : Tests d'Intégration
Concept : Tester l'ensemble du flux (de la simulation de dépôt de STATUS.json à la mise à jour de la DB et la promotion de fichier).

Action :

Écrire des tests dans tests/integration/ qui simulent le dépôt de fichiers et vérifient l'état final de la DB et des fichiers.

Étape 5.2 : Documentation de Base
Concept : Fournir une documentation suffisante pour le déploiement et l'utilisation.

Action : Mettre à jour README.md avec les instructions de démarrage, la configuration, et l'accès à l'API.

Cette feuille de route détaillée nous permettra de progresser de manière structurée et de valider chaque fonctionnalité à mesure que nous l'implémentons.