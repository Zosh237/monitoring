from datetime import datetime
from typing import Optional
from pydantic import BaseModel
import enum

# Enumération pour le statut d'un ExpectedBackupJob
class JobStatusEnum(str, enum.Enum):
    UNKNOWN = "UNKNOWN"        # Statut inconnu ou non évalué
    SUCCESS = "SUCCESS"        # Sauvegarde réussie
    MISSING = "MISSING"        # Sauvegarde manquante
    HASH_MISMATCH = "HASH_MISMATCH"  # Hachage ne correspondant pas
    FAILED = "FAILED"

# Schéma de base pour ExpectedBackupJob, utilisé pour la création et la modification via l'API
class ExpectedBackupJobBase(BaseModel):
    # Année associée au job (ex : 2025)
    year: int
    # Nom de l'entreprise possédant ce job
    company_name: str
    # Ville de l'agence correspondante
    city: str
    # Quartier ou zone spécifique de l'agence
    neighborhood: str  
    # Nom de la base de données concernée par la sauvegarde
    database_name: str
    # Identifiant de l'agent responsable de ce job
    agent_id_responsible: str
    # Chemin template pour le dépôt des fichiers de base de données envoyé par l'agent
    agent_deposit_path_template: str
    # Chemin template pour le dépôt des logs de l'agent (ex: {agent_id}/log/)
    agent_log_deposit_path_template: str
    # Chemin template pour le dépôt final des sauvegardes validées
    final_storage_path_template: str
    # Statut actuel du job, avec l'énumération associée
    current_status: JobStatusEnum
    # Date et heure de la dernière vérification effectuée
    last_checked_timestamp: Optional[datetime] = None
    # Date et heure de la dernière sauvegarde réussie
    last_successful_backup_timestamp: Optional[datetime] = None
    # Liste ou chaîne des destinataires de notification, si applicable
    notification_recipients: Optional[str] = None
    # Indique si ce job est activé
    is_active: bool

# Schéma pour la création d'un ExpectedBackupJob (identique à la base)
class ExpectedBackupJobCreate(ExpectedBackupJobBase):
    pass

# Schéma pour la mise à jour d'un ExpectedBackupJob - tous les champs sont optionnels
class ExpectedBackupJobUpdate(BaseModel):
    year: Optional[int] = None
    company_name: Optional[str] = None
    city: Optional[str] = None
    neighborhood: Optional[str] = None  
    database_name: Optional[str] = None
    agent_id_responsible: Optional[str] = None
    agent_deposit_path_template: Optional[str] = None
    agent_log_deposit_path_template: Optional[str] = None
    final_storage_path_template: Optional[str] = None
    current_status: Optional[JobStatusEnum] = None
    last_checked_timestamp: Optional[datetime] = None
    last_successful_backup_timestamp: Optional[datetime] = None
    notification_recipients: Optional[str] = None
    is_active: Optional[bool] = None

# Schéma complet retourné par l'API, incluant l'id et les métadonnées temporelles
class ExpectedBackupJob(ExpectedBackupJobBase):
    id: int
    # Date de création de l'enregistrement
    created_at: datetime
    # Date de dernière modification de l'enregistrement
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True  # Permet de convertir un objet ORM en ce schéma Pydantic
