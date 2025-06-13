Vérification et Test Local de app/utils/crypto.py
Pour s'assurer que le service app/utils/crypto.py fonctionne comme prévu, nous allons créer un script de test local. Ce script permettra de vérifier que la fonction calculate_file_sha256 calcule correctement les hachages, y compris pour des fichiers de tailles différentes, et qu'elle gère les erreurs.

Algorithme du Script de Test Local
Le script de test effectuera les actions suivantes :

Préparation :

Créer un répertoire temporaire pour les tests (temp_crypto_test).

Créer plusieurs fichiers de test de différentes tailles (vide, petit, moyen).

Configurer un logging de base pour visualiser les messages du service.

Tests des fonctions :

calculate_file_sha256 :

Tester le calcul du hachage pour un fichier vide.

Tester le calcul du hachage pour un petit fichier avec un contenu connu (et vérifier le hachage attendu).

Tester le calcul du hachage pour un fichier plus grand (pour vérifier la lecture par blocs).

Tester le calcul du hachage pour un fichier qui n'existe pas (devrait lever une CryptoUtilityError).

Tester le calcul du hachage pour un chemin qui n'est pas un fichier (ex: un répertoire).

Nettoyage : Supprimer tous les répertoires et fichiers temporaires créés par les tests.