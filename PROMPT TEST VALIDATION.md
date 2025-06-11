Prompt pour l'IA de Code : Test du Service de Validation
Objectif : Exécuter une série de tests sur le service Python app.services.validation_service.validate_status_file afin de vérifier sa capacité à valider des fichiers JSON de statut de sauvegarde.

Contexte : Le service validate_status_file lève une exception StatusFileValidationError en cas d'échec de validation.

Étapes d'exécution :

Création de l'environnement de test :

Créer un répertoire temporaire à la racine du projet nommé temp_test_logs/my_db_name/logs.

Créer les fichiers JSON suivants dans temp_test_logs/my_db_name/logs/ avec le contenu spécifié :

Fichier 1 (Valide) : my_db_name_20250610_1300_SUCCESS.json

{
    "status": "success",
    "timestamp": "2025-06-10T13:05:00Z",
    "file_name": "my_db_name.sql.gz",
    "file_size_bytes": 1024000,
    "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
    "duration_seconds": 120
}

Fichier 2 (JSON Malformé) : invalid_json.json

{ "status": "success", "timestamp": "2025-06-10T13:05:00Z"

Fichier 3 (Champ Obligatoire Manquant - file_name) : missing_field.json

{
    "status": "success",
    "timestamp": "2025-06-10T13:05:00Z",
    "file_size_bytes": 1024000,
    "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
}

Fichier 4 (Timestamp Invalide) : invalid_timestamp.json

{
    "status": "success",
    "timestamp": "2025/06/10 13:05:00",
    "file_name": "my_db_name.sql.gz",
    "file_size_bytes": 1024000,
    "checksum_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789"
}

Exécution des tests et validation des résultats :

Test 1 (Valide) :

Appeler validate_status_file() avec le chemin de my_db_name_20250610_1300_SUCCESS.json.

Attendu : La fonction doit retourner un dictionnaire validé sans lever d'exception. Vérifier que status est "success" et file_size_bytes est 1024000.

Test 2 (Fichier non existant) :

Appeler validate_status_file() avec un chemin vers un fichier qui n'existe pas (par exemple, NON_EXISTENT_PATH).

Attendu : La fonction doit lever une StatusFileValidationError.

Test 3 (JSON malformé) :

Appeler validate_status_file() avec le chemin de invalid_json.json.

Attendu : La fonction doit lever une StatusFileValidationError.

Test 4 (Champ obligatoire manquant) :

Appeler validate_status_file() avec le chemin de missing_field.json.

Attendu : La fonction doit lever une StatusFileValidationError.

Test 5 (Timestamp invalide) :

Appeler validate_status_file() avec le chemin de invalid_timestamp.json.

Attendu : La fonction doit lever une StatusFileValidationError.

Nettoyage :

Supprimer le répertoire temporaire temp_test_logs/ et tout son contenu après l'exécution de tous les tests.

Contexte d'exécution : L'IA doit simuler un environnement Python où le module app.services.validation_service est importable (en ajoutant le répertoire racine du projet au sys.path si nécessaire). Le logging de base doit être configuré pour afficher les messages DEBUG ou INFO en console.