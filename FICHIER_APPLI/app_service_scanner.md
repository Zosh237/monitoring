Explication Détaillée : app/services/scanner.py
Ce document détaille l'implémentation du service app/services/scanner.py, le cœur de notre système de monitoring de sauvegardes. Ce module est responsable de la logique de détection, de validation, de classification des statuts, et de la mise à jour de la base de données.

Concept : Qu'est-ce que app/services/scanner.py ?
Le scanner.py est le cerveau de notre application, orchestrant l'ensemble du processus de surveillance des sauvegardes. Il ne s'agit pas d'un service qui tourne en permanence et consomme des ressources, mais plutôt d'une tâche planifiée (qui sera configurée via APScheduler dans app/main.py) qui s'exécutera à intervalles réguliers (par exemple, toutes les 15 minutes). Son rôle principal est de :

Identifier les jobs de sauvegarde attendus : Il interroge la base de données (ExpectedBackupJob) pour obtenir la liste des bases de données que le système est configuré pour surveiller, y compris leurs horaires de sauvegarde attendus et les agents responsables.

Rechercher et traiter les rapports (STATUS.json) : Pour chaque job attendu, il va activement chercher le fichier STATUS.json global correspondant, déposé par l'agent dans la zone de dépôt spécifiée (/mnt/agent_deposits/{agent_id}/log/).

Valider les rapports et les fichiers de sauvegarde : Il utilise d'autres services utilitaires (app.services.validation_service pour la structure du STATUS.json et app.utils.crypto pour l'intégrité du fichier .sql.gz dans la zone de dépôt) pour s'assurer de la validité et de l'intégrité des informations et des données brutes.

Déterminer le statut de chaque sauvegarde : C'est la logique décisionnelle du scanner. En se basant sur une analyse combinée du rapport de l'agent (le STATUS.json) et de ses propres vérifications côté serveur, il attribue un statut précis à la sauvegarde (par exemple, SUCCESS, FAILED, MISSING, TRANSFER_INTEGRITY_FAILED, ou HASH_MISMATCH).

Mettre à jour la base de données : Il persiste les résultats de son analyse. Il enregistre un historique détaillé (BackupEntry) de chaque événement de sauvegarde, incluant toutes les informations rapportées par l'agent et celles validées par le serveur. Il met également à jour le statut actuel (current_status) du job de sauvegarde attendu pour refléter le dernier état connu.

Déclencher des actions (promotion/notification) : En fonction du statut déterminé, le scanner initiera d'autres actions clés : la promotion des fichiers de sauvegarde valides vers leur destination finale (current_version/) et l'envoi de notifications aux parties prenantes en cas de problèmes détectés.

Importance du Service
Le scanner est la pièce maîtresse qui transforme de simples fichiers déposés par des agents en un système de monitoring intelligent, proactif et fiable. Sans lui, les fichiers resteraient des données brutes non analysées, et le système ne pourrait pas fournir d'alertes significatives ni maintenir un historique cohérent. Sa robustesse est fondamentale car toute erreur dans sa logique pourrait entraîner des alertes incorrectes, des fichiers non promus, ou pire, une fausse sensation de sécurité. Il est la garantie que les données de sauvegarde sont non seulement présentes, mais aussi validées et à jour.

Algorithme du Scanner Principal (scan_backups)
La fonction principale scan_backups(db: Session) sera le point d'entrée de la logique de scan, exécutée par le scheduler.

Initialisation :

Obtenir une session de base de données : La fonction scan_backups reçoit une instance de session de base de données (db: Session), généralement fournie par le mécanisme de dépendance injection de FastAPI ou par le scheduler. Cela assure une gestion correcte des transactions avec la base de données.

Récupérer tous les ExpectedBackupJob actifs : Le scanner commence par interroger la base de données pour obtenir la liste de tous les jobs de sauvegarde qui sont marqués comme is_active=True. Seuls ces jobs feront l'objet d'un scan.

Boucle sur les Jobs Attendus :

Pour chaque ExpectedBackupJob (job) récupéré de la base de données, le scanner exécute une logique d'analyse dédiée à ce job spécifique.

Déterminer les chemins et les fenêtres de temps :

Calculer la date/heure UTC de la dernière sauvegarde attendue : Basé sur job.expected_hour_utc et job.expected_minute_utc, le scanner détermine la date exacte pour laquelle une sauvegarde devrait avoir eu lieu. Il doit gérer les cas où l'heure de scan actuelle est avant l'heure attendue du jour (ce qui signifie que le cycle attendu le plus récent était hier) ou après (le cycle attendu est aujourd'hui). Ceci est crucial pour corréler le scan avec le bon cycle de sauvegarde de l'agent.

Définir la fenêtre de temps (window_minutes) : Une window_minutes (par exemple, 30 minutes, configurable via settings.SCANNER_DETECTION_WINDOW_MINUTES) est définie autour de l'heure attendue. Le scanner cherchera des fichiers STATUS.json dont le timestamp se situe dans cette fenêtre. Cela permet de prendre en compte de légers retards de transfert ou d'exécution des agents.

Construire le chemin attendu du STATUS.json global : En utilisant settings.AGENT_DEPOSITS_BASE_PATH, job.agent_id_responsible, et job.agent_log_deposit_path_template, le scanner construit le chemin complet du dossier où le STATUS.json devrait se trouver (ex: /mnt/agent_deposits/agent_douala_prod_01/log/). Il s'attend à un nom de fichier prévisible (comme OPERATION_YYYYMMDD_HHMM_AGENT_ID.json).

Construire le chemin attendu du fichier de sauvegarde stagé (.sql.gz) : De même, il construit le chemin complet du fichier de base de données dans la zone de dépôt de l'agent (ex: /mnt/agent_deposits/agent_douala_prod_01/database/compta_db.sql.gz) pour pouvoir le vérifier et le déplacer plus tard.

Recherche et Traitement du STATUS.json :

Recherche du fichier : Pour le MVP, le scanner va lister les fichiers dans le répertoire de logs de l'agent et tenter de trouver un STATUS.json dont le nom correspond au cycle attendu et à l'ID de l'agent. Dans une version plus robuste, cela pourrait impliquer une logique de recherche plus complexe pour trouver le STATUS.json le plus pertinent en cas de multiples rapports ou de noms moins prévisibles.

Validation du STATUS.json : Le service app.services.validation_service.validate_status_file() est appelé pour analyser et valider la structure et le contenu du fichier STATUS.json global.

Gestion des cas "manquant" ou "invalide" :

Si le STATUS.json attendu n'est pas trouvé, ou si la base de données spécifique au job n'est pas rapportée dans le STATUS.json global, le statut est classifié comme MISSING.

Si le STATUS.json est trouvé mais sa validation échoue (StatusFileValidationError), le statut est classifié comme FAILED, car le rapport de l'agent lui-même est compromis.

Une BackupEntry est immédiatement créée en base de données pour enregistrer cette anomalie, et le job.current_status est mis à jour. Le scanner passe alors au job suivant.

Si STATUS.json trouvé et valide :

Extraction des informations de l'agent : Le scanner extrait les statuts détaillés (backup_process, compress_process, transfer_process) pour la base de données spécifique depuis le dictionnaire imbriqué databases du STATUS.json global. Ces informations représentent la "déclaration de l'agent".

Contrôle d'Intégrité Côté Serveur (TRANSFER_INTEGRITY_FAILED) :

Condition : Cette vérification est déclenchée uniquement si l'agent a rapporté un transfer_process.status: true (l'agent affirme avoir transféré le fichier avec succès).

Calcul du hachage et de la taille du fichier stagé : Le scanner utilise app.utils.crypto.calculate_file_sha256() pour calculer le hachage SHA256 du fichier .sql.gz réellement présent dans la zone de dépôt de l'agent (staged_db_file_path). Il obtient également sa taille réelle (os.path.getsize()). Ces valeurs sont la "mesure du serveur".

Comparaison : Le hachage et la taille calculés par le serveur sont ensuite comparés avec les valeurs (agent_compress_hash_post_compress et agent_compress_size_post_compress) que l'agent a rapportées dans le STATUS.json après la compression.

Détection d'erreur : Si ces valeurs ne concordent pas, cela signifie que le fichier a été altéré, corrompu ou incomplet pendant ou après le transfert, même si l'agent l'a jugé bon. Le statut est alors marqué comme TRANSFER_INTEGRITY_FAILED. Ce statut prime sur un SUCCESS de l'agent.

Gestion des échecs de calcul : Si le serveur ne peut pas calculer le hachage (fichier absent, permissions), cela déclenche également un TRANSFER_INTEGRITY_FAILED.

Détection HASH_MISMATCH :

Condition : Cette vérification n'est effectuée que si le statut de la sauvegarde est toujours potentiellement SUCCESS (c'est-à-dire, n'a pas été classifié comme FAILED, MISSING, ou TRANSFER_INTEGRITY_FAILED précédemment).

Récupération du hachage précédent : Le scanner récupère le job.previous_successful_hash_global de l'objet ExpectedBackupJob. Ce champ stocke le hachage SHA256 de la dernière sauvegarde réussie de cette base de données, telle que validée par le serveur.

Comparaison : Le server_calculated_staged_hash (le hachage du fichier reçu actuellement) est comparé au job.previous_successful_hash_global.

Détection : Si les deux hachages sont identiques, le statut est marqué comme HASH_MISMATCH. Cela peut indiquer que la base de données n'a pas changé depuis la dernière sauvegarde. C'est une alerte informative, pas un échec critique (sauf si la BD est censée être très dynamique).

Détermination du Statut Final :

Le statut final de la BackupEntry (l'historique) est déterminé par un ordre de priorité strict pour refléter la gravité de la situation : MISSING (pas de rapport) > FAILED (rapport invalide ou échec agent) > TRANSFER_INTEGRITY_FAILED (problème serveur sur le fichier) > HASH_MISMATCH (BD inchangée) > SUCCESS.

Enregistrement des Données :

Création de BackupEntry : Une nouvelle instance de BackupEntry est créée, remplie avec toutes les informations collectées : le statut final déterminé par le scanner, un message descriptif, les données brutes du rapport de l'agent (agent_...), et les résultats des vérifications du serveur (server_calculated_staged_hash, server_calculated_staged_size).

Mise à jour de ExpectedBackupJob : Le job.current_status est mis à jour avec le statut final déterminé. Le job.last_checked_timestamp est mis à jour à l'heure actuelle du scan. Si le statut final est SUCCESS, alors job.last_successful_backup_timestamp est également mis à jour, et surtout, job.previous_successful_hash_global est mis à jour avec le server_calculated_staged_hash actuel.

Commit en DB : La nouvelle BackupEntry est ajoutée à la session de base de données, et les modifications apportées au job sont commises. db.refresh(job) est utilisé pour recharger l'objet job depuis la base de données après le commit, assurant qu'il reflète les dernières valeurs (particulièrement utile pour les prochains cycles de scan ou si d'autres parties du code accèdent à cet objet).

Actions Post-Scan (Promotion et Notification) :

Ces appels seront implémentés dans les prochaines étapes (avec app/services/backup_manager.py et app/services/notifier.py).

Si le statut est SUCCESS, le service de promotion sera appelé pour déplacer le fichier de la zone de dépôt vers la zone validée.

Si le statut est FAILED, MISSING, TRANSFER_INTEGRITY_FAILED, ou HASH_MISMATCH, le service de notification sera appelé pour envoyer une alerte.

Gestion des Multiples Agents et Simultanéité (Explication Détaillée)
Votre question est très pertinente concernant le comportement du scanner face à plusieurs agents et leurs fichiers de statut. Voici comment cela fonctionne dans notre conception actuelle et les considérations pour la simultanéité :

1. Le Fichier STATUS.json est Global Par Agent et Par Opération
C'est un point clé de notre nouveau design. Si un agent est configuré pour sauvegarder 20 bases de données en un seul cycle (ex: à 13h UTC), il générera un unique fichier STATUS.json pour toutes ces 20 bases de données. Ce fichier contiendra un dictionnaire databases où chaque clé est le nom d'une base de données, et la valeur est son rapport détaillé pour ce cycle d'opération.

Exemple de nom de fichier STATUS.json : OPERATION_20250612_1300_agent_douala_prod_01.json

Ce fichier serait déposé dans /mnt/agent_deposits/agent_douala_prod_01/log/.

2. Comment le Scanner Traite les Multiples Agents et BDs
Notre scanner est conçu pour itérer à travers les ExpectedBackupJob configurés dans la base de données, qui sont les "attentes" du serveur.

Lien Job-Agent : Chaque ExpectedBackupJob dans notre base de données est associé à un agent_id_responsible (par exemple, le job pour compta_db de Sirpacam à Douala est géré par agent_douala_prod_01).

Itération Séquentielle : La fonction scan_backups récupère tous les jobs actifs de la base de données et les traite séquentiellement, un par un.

jobs = db.query(ExpectedBackupJob).filter(ExpectedBackupJob.is_active == True).all()
for job in jobs:
    # Logique de scan pour ce job spécifique
    # ... qui va chercher le STATUS.json de son agent_id_responsible

Recherche du STATUS.json pertinent : Lorsque le scanner traite un job (disons, job_compta_db pour agent_douala_prod_01), il construit le chemin d'accès au fichier STATUS.json global spécifique à cet agent et à ce cycle de temps attendu.

Il sait que le STATUS.json pour agent_douala_prod_01 devrait être dans /mnt/agent_deposits/agent_douala_prod_01/log/.

Il s'attend à un nom de fichier comme OPERATION_YYYYMMDD_HHMM_agent_douala_prod_01.json.

Il lira ce fichier STATUS.json global.

Extraction des données de la BD : Une fois le STATUS.json de l'agent lu et validé, le scanner accède au dictionnaire "databases" à l'intérieur de ce STATUS.json pour trouver les informations spécifiques à la database_name du job en cours de traitement.

# Dans le code du scanner :
overall_status_data = validate_status_file(latest_status_file_path)
agent_report_data = overall_status_data.get("databases", {}).get(job.database_name) # Ici, on extrait la section pertinente pour le job

Traitement Séquentiel, Rapport Global :

Si l'agent A gère BD1, BD2, et BD3, tous rapportés dans le même STATUS.json_A.

Quand le scanner traite le ExpectedBackupJob pour BD1 (associé à agent_A), il lira STATUS.json_A et traitera la section de BD1.

Plus tard, quand il traitera le ExpectedBackupJob pour BD2 (aussi associé à agent_A), il lira STATUS.json_A à nouveau (ou pourrait le mettre en cache si l'optimisation est nécessaire) et traitera la section de BD2.

Ceci garantit que chaque base de données attendue est bien vérifiée par rapport au rapport global de son agent.

3. Simultanéité et Optimisation pour l'Avenir
Dans la version actuelle du MVP, la fonction scan_backups est exécutée de manière séquentielle pour tous les jobs. Cela signifie qu'elle ne traite qu'un job de sauvegarde à la fois, et donc un agent à la fois.

Avantages de la Séquentialité pour le MVP :

Simplicité : Moins complexe à développer et à déboguer.

Gestion des ressources : Un seul thread/processus interagit avec le système de fichiers et la base de données, évitant les problèmes de concurrence.

Suffisant pour de nombreux cas : Pour des centaines de jobs qui ne se chevauchent pas trop fréquemment, une exécution séquentielle toutes les 15 minutes est souvent suffisante.

Quand envisager la Simultanéité (Future) :

Si vous avez un très grand nombre d'agents/jobs (milliers) ou si les scans prennent beaucoup de temps (par exemple, des calculs de hachage sur de très gros fichiers), une exécution séquentielle pourrait devenir un goulot d'étranglement.

Options de Concurrence Future :

Multithreading/Multiprocessing : Utiliser les modules concurrent.futures (ThreadPoolExecutor ou ProcessPoolExecutor) de Python pour traiter les jobs en parallèle. Cela nécessiterait une gestion plus complexe des sessions de base de données et des accès concurrents aux fichiers.

File d'Attente de Messages (ex: RabbitMQ, Kafka) : Les agents pourraient envoyer leurs STATUS.json à une file d'attente. Le scanner (ou des "workers" du scanner) lirait ensuite depuis cette file. Cela découplerait la réception des rapports de leur traitement et permettrait une scalabilité horizontale des scanners.

Réflexion du Scheduler : APScheduler peut lancer des tâches dans différents threads ou processus. On pourrait lancer scan_backups dans un ProcessPoolExecutor fourni par APScheduler.

En résumé pour votre question :

Gestion des BDs par Agent : Oui, chaque ExpectedBackupJob est lié à un agent_id_responsible. Le STATUS.json que le scanner recherche est celui de cet agent, et il contient les statuts de toutes les BDs gérées par cet agent dans ce cycle. Le scanner extrait la portion du rapport pertinente pour le job.database_name en cours.

Lancer les scans simultanément : Dans la conception actuelle du MVP, le scan se fait séquentiellement pour tous les jobs de tous les agents par une seule exécution de la fonction scan_backups. Pour le moment, cela est suffisant pour le MVP. Si des goulots d'étranglement apparaissent, une optimisation vers une exécution parallèle (multithreading/multiprocessing) ou une architecture basée sur des files d'attente serait une évolution logique.

Pour l'implémentation du scanner (app/services/scanner.py), nous nous tiendrons à l'approche séquentielle décrite précédemment. Cela nous permettra de nous concentrer sur la logique métier complexe avant d'introduire des considérations de performance et de concurrence, qui sont souvent des optimisations ultérieures.

Cette explication plus détaillée vous aide-t-elle à visualiser le comportement du scanner avec plusieurs agents ?