import shutil
from pathlib import Path

# Chemin vers le dossier à supprimer
target_dir = Path("monitoring/test_manuel/SIRPACAM_DOUALA_NEWBELL")

if target_dir.exists() and target_dir.is_dir():
    shutil.rmtree(target_dir)
    print(f"Dossier supprimé : {target_dir.resolve()}")
else:
    print(f"Aucun dossier trouvé à : {target_dir.resolve()}")
