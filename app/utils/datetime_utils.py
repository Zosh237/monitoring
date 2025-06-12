# app/utils/datetime_utils.py
# Ce module fournit des fonctions utilitaires pour la manipulation des dates et des heures,
# en mettant l'accent sur la gestion de l'UTC et des formats ISO 8601.

from datetime import datetime, timezone, timedelta
import logging

# Initialisation du logger pour ce module.
logger = logging.getLogger(__name__)

class DateTimeUtilityError(Exception):
    """Exception personnalisée levée en cas d'erreur dans les opérations de date/heure."""
    pass

def get_utc_now() -> datetime:
    """
    Retourne l'horodatage actuel en temps universel coordonné (UTC),
    avec les informations de fuseau horaire incluses (aware datetime).
    """
    return datetime.now(timezone.utc)

def parse_iso_datetime(iso_string: str) -> datetime:
    """
    Parse une chaîne de caractères au format ISO 8601 (ex: "YYYY-MM-DDTHH:MM:SSZ")
    en un objet datetime UTC conscient du fuseau horaire.

    Args:
        iso_string (str): La chaîne de date/heure au format ISO 8601.

    Returns:
        datetime: L'objet datetime correspondant en UTC.

    Raises:
        DateTimeUtilityError: Si la chaîne n'est pas un format ISO valide.
    """
    try:
        # datetime.fromisoformat gère la plupart des offsets, mais le 'Z'
        # est souvent mieux traité en le remplaçant par l'offset UTC explicite.
        dt_obj = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        
        # S'assurer que l'objet datetime est bien en UTC.
        # Si le fuseau horaire n'est pas défini (naive datetime), on l'assume UTC.
        if dt_obj.tzinfo is None:
            dt_obj = dt_obj.replace(tzinfo=timezone.utc)
        else:
            # Si un fuseau horaire est présent, le convertir en UTC.
            dt_obj = dt_obj.astimezone(timezone.utc)
        
        return dt_obj
    except (ValueError, TypeError) as e:
        # Capture les erreurs de formatage ou de type incorrect de la chaîne.
        logger.error(f"Erreur de parsing ISO datetime '{iso_string}': {e}")
        raise DateTimeUtilityError(f"Format ISO datetime invalide: '{iso_string}'")

def format_datetime_to_iso(dt: datetime) -> str:
    """
    Formate un objet datetime en chaîne ISO 8601 avec 'Z' pour UTC.
    L'objet datetime d'entrée doit être conscient du fuseau horaire.

    Args:
        dt (datetime): L'objet datetime à formater.

    Returns:
        str: La chaîne de date/heure au format ISO 8601 (ex: "YYYY-MM-DDTHH:MM:SSZ").

    Raises:
        DateTimeUtilityError: Si l'objet datetime n'est pas conscient du fuseau horaire.
    """
    if dt.tzinfo is None:
        # Si l'objet datetime est "naïf" (sans information de fuseau horaire),
        # il est converti en UTC par défaut, et un avertissement est loggé.
        logger.warning(f"L'objet datetime n'est pas conscient du fuseau horaire. Assumé UTC pour le formatage: {dt}")
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        # S'assurer qu'il est en UTC avant de formater pour la cohérence.
        dt = dt.astimezone(timezone.utc) 

    # .isoformat() génère l'offset (+00:00) si tzinfo est UTC.
    # On le remplace par 'Z' pour un format plus standardisé dans nos rapports.
    return dt.isoformat(timespec='seconds').replace('+00:00', 'Z')

def is_time_within_window(
    target_time: datetime,
    expected_hour_utc: int,
    expected_minute_utc: int,
    window_minutes: int
) -> bool:
    """
    Vérifie si un horodatage cible tombe dans une fenêtre de temps autour d'une heure UTC attendue.

    Exemple: Si expected_hour_utc=13, expected_minute_utc=00 et window_minutes=15,
    la fenêtre est de 12h45 à 13h15 (inclusif aux bornes).

    Args:
        target_time (datetime): L'horodatage à vérifier (doit être UTC conscient).
        expected_hour_utc (int): L'heure UTC attendue (0-23).
        expected_minute_utc (int): La minute UTC attendue (0-59).
        window_minutes (int): La taille de la fenêtre en minutes (ex: 15 pour +/- 15 min).

    Returns:
        bool: True si target_time est dans la fenêtre, False sinon.

    Raises:
        DateTimeUtilityError: Si target_time n'est pas UTC conscient du fuseau horaire.
    """
    # Étape 1: Vérifier que l'horodatage cible est conscient du fuseau horaire.
    # C'est une exigence critique pour des comparaisons de temps fiables.
    if target_time.tzinfo is None or target_time.tzinfo.utcoffset(target_time) is None:
        logger.error(f"target_time n'est pas un datetime conscient du fuseau horaire : {target_time}. Doit être UTC.")
        raise DateTimeUtilityError("L'horodatage cible (target_time) doit être un objet datetime conscient du fuseau horaire UTC.")

    # Étape 2: S'assurer que l'horodatage cible est bien en UTC.
    # Cela standardise la comparaison.
    target_time_utc = target_time.astimezone(timezone.utc)

    # Étape 3: Définir l'horodatage "attendu" pour la même date que target_time.
    # On prend la date du target_time pour s'assurer que la fenêtre est calculée pour le bon jour.
    expected_datetime_central = target_time_utc.replace(
        hour=expected_hour_utc,
        minute=expected_minute_utc,
        second=0,
        microsecond=0
    )

    # Étape 4: Calculer les bornes inférieure et supérieure de la fenêtre de temps.
    # La fenêtre s'étend de 'window_minutes' avant à 'window_minutes' après l'heure centrale.
    lower_bound = expected_datetime_central - timedelta(minutes=window_minutes)
    upper_bound = expected_datetime_central + timedelta(minutes=window_minutes)

    # Étape 5: Vérifier si l'horodatage cible se situe dans la fenêtre.
    is_within = lower_bound <= target_time_utc <= upper_bound
    logger.debug(f"Vérification fenêtre: {lower_bound.time()} <= {target_time_utc.time()} <= {upper_bound.time()} (pour le jour {target_time_utc.date()}) -> {is_within}")
    return is_within

