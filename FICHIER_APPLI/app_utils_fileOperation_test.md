Vérification et Test Local de app/utils/file_operations.py
Pour s'assurer que le service app/utils/file_operations.py fonctionne comme prévu, nous allons créer un script de test local. Ce script simule des scénarios réels de création de répertoires, de déplacement de fichiers et de suppression, y compris des cas d'erreur.

Algorithme du Script de Test Local
Le script de test effectuera les actions suivantes :

Préparation :

Créer un répertoire temporaire pour les tests (temp_file_ops_test).

Créer des fichiers de test à l'intérieur de ce répertoire.

Configurer un logging de base pour visualiser les messages du service.

Tests des fonctions :

ensure_directory_exists :

Tester la création d'un répertoire simple.

Tester la création d'une arborescence imbriquée.

Tester la fonction sur un répertoire qui existe déjà (ne devrait pas échouer).

move_file :

Tester le déplacement d'un fichier existant vers un nouveau répertoire.

Tester le déplacement d'un fichier existant pour écraser un fichier existant à destination.

Tester le déplacement d'un fichier inexistant (devrait lever une erreur).

Tester le déplacement vers un chemin où la création du répertoire parent échoue (devrait lever une erreur).

delete_file :

Tester la suppression d'un fichier existant.

Tester la suppression d'un fichier non existant (ne devrait pas lever d'erreur).

Tester la suppression d'un fichier protégé ou verrouillé (devrait lever une erreur).

Nettoyage : Supprimer tous les répertoires et fichiers temporaires créés par les tests.