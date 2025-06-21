import os

def extraire_nom_fichier(staged_file_name, extensions_valides=None):
    """
    Extrait le nom de fichier à partir d'un chemin complet ou partiel,
    et valide son extension contre une liste d’extensions autorisées.

    :param staged_file_name: Chemin ou nom du fichier (ex: "/home/lam/Backup/EL_HADJ_BAFOUSSAM_2025.zst")
    :param extensions_valides: Liste d’extensions acceptées (ex: [".zst", ".gz", ".db.sql"])
    :return: Le nom du fichier si extension valide, sinon None
    """
    if not staged_file_name:
        return None

    if extensions_valides is None:
        extensions_valides = [".zst", ".gz", ".db.sql"]

    # Extraire juste le nom du fichier
    nom_fichier = os.path.basename(staged_file_name)

    # Valider contre les extensions reconnues
    for ext in extensions_valides:
        if nom_fichier.endswith(ext):
            return nom_fichier

    return None  # Si aucune extension ne correspond


# Exemples d'utilisation
if __name__ == "__main__":
    exemples = [
        "/home/lam/Backup/SDMC_BAFOUSSAM_2025.zst",
        "SOCIA_EXO_DETAIL_BAF_2025.db.sql",
        "fake_folder/fichier_sauvegarde.gz",
        "autre_fichier.txt"
    ]

    for chemin in exemples:
        result = extraire_nom_fichier(chemin)
        print(f"{chemin} ➜ {result}")
