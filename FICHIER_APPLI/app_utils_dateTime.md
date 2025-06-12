Explication Détaillée : app/utils/datetime_utils.py (Version Simplifiée)
Ce document explique en détail le service app/utils/datetime_utils.py, qui fournit des fonctions essentielles pour la manipulation des dates et des heures dans notre application de monitoring. L'accent est mis sur la clarté et la simplicité du code.

Concept : À quoi sert app/utils/datetime_utils.py ?
Le module app/utils/datetime_utils.py est une boîte à outils dédiée à toutes les opérations liées aux dates et heures de notre projet. Les systèmes de monitoring dépendent fortement de la précision temporelle : pour horodater les événements, vérifier les délais, ou analyser les tendances.

Regrouper ces fonctions ici permet :

Uniformité : Assurer que toutes les manipulations de date/heure se font de la même manière (par exemple, toujours en UTC pour la cohérence).

Lisibilité : Rendre le code principal de l'application plus clair, car il n'aura pas à gérer les détails complexes des formats de date ou des fuseaux horaires.

Robustesse : Centraliser la gestion des erreurs de formatage ou de conversion.

Algorithme des Fonctions Clés (Simplifié)
Voici les fonctions principales de ce module et leur logique simplifiée :

1. get_utc_now() -> datetime
Objectif : Obtenir l'horodatage actuel, toujours en Temps Universel Coordonné (UTC).

Pourquoi UTC ? : C'est une meilleure pratique pour les systèmes distribués. Cela évite les confusions liées aux changements d'heure d'été/hiver et aux différents fuseaux horaires.

Algorithme : Utiliser la fonction native de Python datetime.now() en lui spécifiant le fuseau horaire timezone.utc.

2. parse_iso_datetime(iso_string: str) -> datetime
Objectif : Convertir une chaîne de caractères représentant une date/heure (au format standard ISO 8601, par exemple "2025-06-12T20:00:00Z") en un objet datetime compréhensible par Python, et s'assurer qu'il est bien en UTC.

Pourquoi ISO 8601 ? : C'est un format international standardisé, facile à lire par les machines et les humains.

Algorithme :

Utiliser datetime.fromisoformat() : C'est la méthode Python recommandée pour ce format.

Adapter la chaîne : fromisoformat() gère la plupart des formats ISO, mais le suffixe 'Z' (pour Zulu/UTC) est parfois mieux interprété comme '+00:00'. On effectue donc un simple remplacement.

Rendre l'objet "conscient" de son fuseau horaire : S'assurer que l'objet datetime sait qu'il est en UTC (en lui assignant timezone.utc si ce n'est pas déjà fait).

Gérer les erreurs : Lever une exception si la chaîne n'est pas au bon format.

3. format_datetime_to_iso(dt: datetime) -> str
Objectif : Faire l'inverse de la fonction précédente : convertir un objet datetime Python en une chaîne de caractères au format ISO 8601 (avec 'Z' pour UTC).

Algorithme :

Convertir l'objet datetime en UTC s'il ne l'est pas déjà.

Utiliser la méthode isoformat() de l'objet datetime pour obtenir le format standard.

Remplacer l'offset +00:00 par Z pour un format plus concis et couramment utilisé pour l'UTC.

4. is_time_within_window(target_time: datetime, expected_hour_utc: int, expected_minute_utc: int, window_minutes: int) -> bool
Objectif : Vérifier si un horodatage donné (par exemple, celui d'une sauvegarde) se situe dans une "fenêtre" de temps spécifique autour d'une heure attendue. Par exemple, si une sauvegarde est attendue à 20h00 UTC, est-ce que le timestamp de la sauvegarde se trouve entre 19h45 et 20h15 (pour une fenêtre de +/- 15 minutes) ?

Algorithme :

Vérifier la conscience du fuseau horaire : S'assurer que target_time est bien un objet datetime qui connaît son fuseau horaire (et qu'il est en UTC). C'est essentiel pour éviter des erreurs de calcul.

Définir l'heure attendue comme référence : Créer un objet datetime pour l'heure exacte attendue (expected_hour_utc, expected_minute_utc) pour la même date que le target_time.

Calculer les bornes de la fenêtre :

Borne inférieure : heure_attendue - window_minutes.

Borne supérieure : heure_attendue + window_minutes.

Comparaison : Vérifier si target_time est supérieur ou égal à la borne inférieure ET inférieur ou égal à la borne supérieure.