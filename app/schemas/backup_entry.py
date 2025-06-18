from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import enum

# Enumération pour le statut d'une entrée de sauvegarde
class BackupEntryStatusEnum(str, enum.Enum):
    UNKNOWN = "UNKNOWN"        # Statut inconnu
    SUCCESS = "SUCCESS"        # Sauvegarde validée avec succès
    MISSING = "MISSING"        # Sauvegarde introuvable
    HASH_MISMATCH = "HASH_MISMATCH"  # Erreur de validation de hachage

# Schéma de base pour une BackupEntry, centralisant les informations essentielles
class BackupEntryBase(BaseModel):
    # Référence au job attendu par son identifiant
    expected_job_id: int
    # Horodatage de la détection par le serveur
    timestamp: datetime
    # Statut de l'entrée tel que déterminé par le scanner
    status: BackupEntryStatusEnum
    # Message détaillé décrivant l'événement ou l'erreur éventuelle
    message: Optional[str] = None
    # Nom du fichier STATUS.json ayant déclenché ce relevé
    operation_log_file_name: Optional[str] = None
    # Identifiant de l'agent ayant généré le rapport
    agent_id: Optional[str] = None
    # Statut global rapporté par l'agent
    agent_overall_status: Optional[str] = None
    # Hachage calculé du fichier validé sur le serveur
    server_calculated_staged_hash: Optional[str] = None
    # Taille calculée du fichier validé sur le serveur
    server_calculated_staged_size: Optional[int] = None
    # Dernier hachage de sauvegarde globale réussie, utilisé pour comparer les sauvegardes successives
    previous_successful_hash_global: Optional[str] = None
    # Résultat de la comparaison des hachages (True si différent, False si identique)
    hash_comparison_result: Optional[bool] = None
    #calculated_hash: Optional[str] = None

# Schéma utilisé lors de la création d'une BackupEntry via l'API
class BackupEntryCreate(BackupEntryBase):
    pass

# Schéma complet retourné par l'API, incluant l'identifiant et la date de création
class BackupEntry(BackupEntryBase):
    id: int
    # Date de création de l'entrée
    created_at: datetime

    class Config:
        orm_mode = True  # Permet la conversion d'un objet ORM en ce schéma Pydantic
