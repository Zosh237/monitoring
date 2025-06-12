# test_datetime_utils.py
# Script de test temporaire pour valider le service app/utils/datetime_utils.py (Avec Coloration).

import os
import sys
import logging
from datetime import datetime, timezone, timedelta

# Ajoute le répertoire racine du projet au PYTHONPATH.
sys.path.append(os.path.abspath('.'))

# --- Définition des codes ANSI pour la coloration ---
# Ces codes sont supportés par la plupart des terminaux modernes.
COLOR_GREEN = '\033[92m'  # Vert pour le succès
COLOR_RED = '\033[91m'    # Rouge pour l'échec
COLOR_YELLOW = '\033[93m' # Jaune pour les avertissements/informations
COLOR_BLUE = '\033[94m'   # Bleu pour les titres de section
COLOR_RESET = '\033[0m'   # Réinitialise la couleur à la couleur par défaut du terminal

# Configure un logging de base pour voir les messages du service lors des tests locaux.
# Nous allons modifier le formateur pour inclure la coloration.
logging.basicConfig(
    level=logging.DEBUG,
    format=f'{COLOR_YELLOW}[%(asctime)s]{COLOR_RESET} - [%(levelname)s] - %(message)s'
)

# Importe les fonctions du service à tester.
from app.utils.datetime_utils import get_utc_now, parse_iso_datetime, format_datetime_to_iso, is_time_within_window, DateTimeUtilityError

def run_tests():
    """Exécute tous les tests pour les utilitaires de date/heure."""
    print(f"\n{COLOR_BLUE}--- Début des tests du service de manipulation de dates/heures ---{COLOR_RESET}")

    # --- Test 1: get_utc_now ---
    print(f"\n{COLOR_BLUE}--- Test 1: get_utc_now ---{COLOR_RESET}")
    now_utc = get_utc_now()
    try:
        # Vérifie que l'objet datetime est bien conscient de l'UTC (offset à 0)
        assert now_utc.tzinfo is not None and now_utc.tzinfo.utcoffset(now_utc) == timedelta(0)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} get_utc_now() retourne un datetime conscient de l'UTC: {now_utc}")
    except AssertionError:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} get_utc_now() ne retourne pas un datetime conscient de l'UTC: {now_utc}")

    # --- Test 2: parse_iso_datetime ---
    print(f"\n{COLOR_BLUE}--- Test 2: parse_iso_datetime ---{COLOR_RESET}")
    iso_str_z = "2025-06-12T20:00:00Z"
    iso_str_offset = "2025-06-12T21:00:00+01:00" # Exemple d'offset, devrait être 20:00:00 UTC
    iso_str_no_seconds = "2025-06-12T20:00Z" # Test avec format sans secondes

    try:
        dt_z = parse_iso_datetime(iso_str_z)
        assert dt_z.hour == 20 and dt_z.minute == 0 and dt_z.tzinfo == timezone.utc
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Parsing de '{iso_str_z}' -> {dt_z}")

        dt_offset = parse_iso_datetime(iso_str_offset)
        assert dt_offset.hour == 20 and dt_offset.minute == 0 and dt_offset.tzinfo == timezone.utc
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Parsing de '{iso_str_offset}' (avec offset) -> {dt_offset}")

        dt_no_seconds = parse_iso_datetime(iso_str_no_seconds)
        assert dt_no_seconds.hour == 20 and dt_no_seconds.minute == 0 and dt_no_seconds.second == 0
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Parsing de '{iso_str_no_seconds}' (sans secondes) -> {dt_no_seconds}")

        # Test d'erreur: format ISO invalide
        invalid_iso = "2025/06/12 20:00:00"
        try:
            parse_iso_datetime(invalid_iso)
            print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Parsing de '{invalid_iso}' a réussi inopinément. Erreur attendue.")
        except DateTimeUtilityError as e:
            print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue pour format ISO invalide : {e}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur inattendue lors du test parse_iso_datetime : {e}")


    # --- Test 3: format_datetime_to_iso ---
    print(f"\n{COLOR_BLUE}--- Test 3: format_datetime_to_iso ---{COLOR_RESET}")
    dt_aware_utc = datetime(2025, 6, 12, 14, 30, 15, tzinfo=timezone.utc)
    dt_naive = datetime(2025, 6, 12, 14, 30, 15) # Objet datetime sans fuseau horaire

    try:
        formatted_aware = format_datetime_to_iso(dt_aware_utc)
        assert formatted_aware == "2025-06-12T14:30:15Z"
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Formatage datetime conscient UTC : {formatted_aware}")

        formatted_naive = format_datetime_to_iso(dt_naive)
        # Un avertissement sera loggé par la fonction, mais le formatage devrait être correct
        assert formatted_naive == "2025-06-12T14:30:15Z"
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Formatage datetime naïf (assumé UTC) : {formatted_naive}")
    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur inattendue lors du test format_datetime_to_iso : {e}")

    # --- Test 4: is_time_within_window ---
    print(f"\n{COLOR_BLUE}--- Test 4: is_time_within_window ---{COLOR_RESET}")
    # Heure attendue: 13h00 UTC, fenêtre de +/- 15 min (12h45:00 à 13h15:00)
    expected_h = 13
    expected_m = 0
    window = 15

    # Horodatages dans la fenêtre
    time_in_window_at_lower_bound = datetime(2025, 6, 12, 12, 45, 0, tzinfo=timezone.utc)
    time_in_window_at_center = datetime(2025, 6, 12, 13, 0, 0, tzinfo=timezone.utc)
    time_in_window_at_upper_bound = datetime(2025, 6, 12, 13, 15, 0, tzinfo=timezone.utc)
    
    # Horodatages en dehors de la fenêtre
    time_out_window_below = datetime(2025, 6, 12, 12, 44, 59, tzinfo=timezone.utc)
    time_out_window_above = datetime(2025, 6, 12, 13, 15, 1, tzinfo=timezone.utc)
    
    # Test avec un jour différent (l'heure reste dans la fenêtre pour son jour)
    time_different_day_in_window = datetime(2025, 6, 13, 13, 0, 0, tzinfo=timezone.utc) 

    try:
        assert is_time_within_window(time_in_window_at_lower_bound, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_in_window_at_lower_bound} (borne inférieure) est dans la fenêtre.")
        assert is_time_within_window(time_in_window_at_center, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_in_window_at_center} (centre) est dans la fenêtre.")
        assert is_time_within_window(time_in_window_at_upper_bound, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_in_window_at_upper_bound} (borne supérieure) est dans la fenêtre.")

        assert not is_time_within_window(time_out_window_below, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_out_window_below} est en dehors de la fenêtre (trop tôt).")
        assert not is_time_within_window(time_out_window_above, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_out_window_above} est en dehors de la fenêtre (trop tard).")
        
        # Le test vérifie l'heure sur le même jour.
        assert is_time_within_window(time_different_day_in_window, expected_h, expected_m, window)
        print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} {time_different_day_in_window} est dans la fenêtre pour son jour.")

        # Test d'erreur: datetime naïf (sans fuseau horaire)
        try:
            is_time_within_window(datetime(2025, 6, 12, 13, 0, 0), expected_h, expected_m, window)
            print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} is_time_within_window() avec datetime naïf a réussi inopinément. Erreur attendue.")
        except DateTimeUtilityError as e:
            print(f"{COLOR_GREEN}SUCCÈS:{COLOR_RESET} Erreur attendue pour datetime naïf : {e}")

    except Exception as e:
        print(f"{COLOR_RED}ÉCHEC:{COLOR_RESET} Erreur inattendue lors du test is_time_within_window : {e}")


    print(f"\n{COLOR_BLUE}--- Fin des tests du service de manipulation de dates/heures ---{COLOR_RESET}")

if __name__ == "__main__":
    run_tests()
