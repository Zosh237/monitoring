Voici un résumé clair de la logique métier mise à jour et actuellement implémentée dans votre service de scanner (app/services/scanner.py), intégrant vos dernières précisions :

Objectif Principal du Scanner
Le BackupScanner est le cœur de votre système de monitoring. Sa mission est d'automatiser la surveillance des sauvegardes en :

Détectant les rapports d'agents distants (STATUS.json).

Validant leur contenu et l'intégrité des fichiers de sauvegarde associés (.sql.gz) directement à leur emplacement de staging.

Déterminant le statut précis de chaque job de sauvegarde (réussi, manquant, échec, etc.).

Mettant à jour l'état de ces jobs dans la base de données.

Gérant le cycle de vie des fichiers de rapport (STATUS.json) par archivage, tout en laissant les fichiers de sauvegarde stagés en place sans les déplacer ni les supprimer.

Phases Opérationnelles du Scan (scan_all_jobs)
Le processus de scan se déroule en trois phases séquentielles pour garantir robustesse et cohérence :

Phase 1: Collecte et Traitement Initial de Tous les Rapports d'Agents

Parcours des Répertoires d'Agents : Le scanner liste tous les dossiers présents sous le BACKUP_STORAGE_ROOT (le répertoire racine où les agents déposent leurs données).

Validation des Noms de Dossiers d'Agents : Chaque nom de dossier d'agent (ENTREPRISE_VILLE_QUARTIER) est validé. Si un nom est incorrect ou si le dossier log est absent, le dossier est ignoré avec un avertissement.

Découverte et Validation des STATUS.json :

Pour chaque dossier d'agent valide, le scanner recherche tous les fichiers STATUS.json dans leur sous-dossier log. Le format de nom attendu est HORODATAGE_ENTREPRISE_VILLE_QUARTIER.json.

Chaque fichier STATUS.json trouvé est :

Validé structurellement (format JSON correct, présence des champs obligatoires comme operation_end_time, agent_id, databases).

Vérifié pour sa fraîcheur : Le operation_end_time interne du rapport doit être récent (moins de MAX_STATUS_FILE_AGE_DAYS).

Vérifié pour la cohérence de l'ID Agent : L'agent_id mentionné dans le fichier JSON doit correspondre au nom du dossier de l'agent.

Cartographie des Rapports Pertinents : Le scanner construit une carte interne (all_relevant_reports_map). Pour chaque combinaison unique d'(agent_id, database_name), seule l'information du rapport valide le plus récent et pertinent (respectant les critères de fraîcheur et de cohérence) est conservée dans cette carte pour une utilisation ultérieure.

Pré-Marquage des Fichiers STATUS.json pour Archivage : Indépendamment de leur validité ou pertinence pour un job spécifique, tous les fichiers STATUS.json rencontrés (valides, invalides, ou trop anciens) sont ajoutés à une file d'attente (self.status_files_to_archive) pour être déplacés physiquement vers un répertoire _archive après l'évaluation de tous les jobs. Il n'y a aucune zone de quarantaine pour ces fichiers.

Phase 2: Évaluation et Mise à Jour de Chaque Job de Sauvegarde Attendu

Parcours des Jobs Configurés : Le scanner récupère tous les ExpectedBackupJob actifs depuis la base de données.

Recherche du Rapport Pertinent par Job : Pour chaque ExpectedBackupJob :

Le scanner tente de trouver un rapport correspondant dans la all_relevant_reports_map collectée en Phase 1.

Si un rapport est trouvé, une vérification cruciale est effectuée via _is_report_relevant_for_job_cycle. Cette fonction détermine si le operation_end_time du rapport se situe dans la fenêtre de collecte attendue (SCANNER_REPORT_COLLECTION_WINDOW_MINUTES) autour de l'expected_hour_utc du job, assurant qu'un rapport "tardif" ou "en avance" n'est pas appliqué au mauvais cycle.

Traitement du Rapport ou Détermination du Statut Manquant :

Si un rapport pertinent est trouvé : La méthode _process_single_db_from_status_data est appelée. Elle :

Récupère les statuts (BACKUP, COMPRESS, TRANSFER), hachages et tailles rapportés par l'agent.

Vérifie l'intégrité côté serveur : Calcule le hachage et la taille réels du fichier .sql.gz dans son emplacement de staging actuel.

Détermine le BackupEntryStatus et le JobStatus :

FAILED : Si l'agent lui-même a rapporté un échec pour l'une des phases (BACKUP, COMPRESS, TRANSFER).

TRANSFER_INTEGRITY_FAILED : Si l'agent a rapporté un succès de transfert, mais le serveur détecte une incohérence (fichier .sql.gz manquant dans le staging, ou hachages/tailles ne correspondant pas).

SUCCESS : Si toutes les étapes de l'agent sont réussies ET l'intégrité côté serveur est validée.

HASH_MISMATCH : Si la sauvegarde est un SUCCESS, mais le hachage calculé par le serveur est différent du previous_successful_hash_global du job. C'est une réussite technique, mais une alerte sur un changement de contenu. Le JobStatus global du job reste OK.

Enregistre BackupEntry : Une entrée détaillée est ajoutée à la base de données avec toutes les informations du rapport de l'agent et les résultats des vérifications du serveur.

Met à jour ExpectedBackupJob : Le statut global du job est mis à jour (OK, FAILED, TRANSFER_INTEGRITY_FAILED). Pour les SUCCESS, le previous_successful_hash_global du job est mis à jour avec le nouveau hachage du fichier stagé.

Gestion des Fichiers Stagés Post-Traitement : Les fichiers stagés (.sql.gz) ne sont PAS déplacés ni supprimés. Ils restent dans leur répertoire d'origine dans la zone de staging.

Si aucun rapport pertinent n'est trouvé pour le job : La méthode _handle_missing_or_unknown_job est appelée. Elle vérifie si l'heure actuelle a dépassé la date limite de collecte du rapport pour le cycle de ce job.

Si la date limite est dépassée : Le job est marqué MISSING et une BackupEntry de type MISSING est créée.

Si la date limite n'est pas encore dépassée : Le job reste dans son statut initial (UNKNOWN).

Phase 3: Exécution des Opérations de Fichiers Collectées (uniquement STATUS.json)

Une fois que tous les jobs ont été évalués et que les mises à jour de la base de données ont été faites et committées :

Tous les fichiers STATUS.json qui ont été marqués pour archivage (self.status_files_to_archive) sont déplacés vers leur répertoire _archive respectif.

Principes Clés de la Logique Actuelle
Découplage : La détection des rapports est séparée de l'évaluation des jobs et des opérations de fichiers, rendant le système plus robuste.

Fichiers Stagés (Source Unique) : Les fichiers .sql.gz restent à leur emplacement de dépôt (database sous le répertoire de l'agent) et sont considérés comme le stockage final. Aucune copie, déplacement ou suppression n'est effectuée sur ces fichiers.

Rapports STATUS.json (Consommables) : Sont toujours archivés après traitement, quel que soit leur statut ou leur pertinence, pour éviter le re-traitement.

Absence de Quarantaine : Aucune zone de quarantaine n'est utilisée. Les fichiers problématiques restent en place ou sont loggués comme tels.

Granularité des Statuts : Distinction claire entre les différents types d'échecs (agent-rapporté, intégrité du transfert, changement de contenu).

Contrôle Temporel : La pertinence d'un rapport pour un cycle de sauvegarde est strictement vérifiée par une fenêtre de temps, évitant l'application de rapports obsolètes.