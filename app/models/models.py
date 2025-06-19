# app/models/models.py
# Ce fichier définit les modèles de base de données (tables) pour l'application de monitoring des sauvegardes.

from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLEnum, Text, ForeignKey, BigInteger, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

# Importe la classe de base déclarative.
from app.core.database import Base

# --- Définition des Enums ---

class JobStatus(str, enum.Enum):
    #OK = "OK"
    SUCCESS = "SUCCESS"
    MISSING = "MISSING"
    HASH_MISMATCH = "HASH_MISMATCH"
    UNCHANGED = "UNCHANGED" 
    #RANSFER_INTEGRITY_FAILED = "TRANSFER_INTEGRITY_FAILED"
    UNKNOWN = "UNKNOWN"

#class BackupFrequency(str, enum.Enum):
#    DAILY = "daily"
#    WEEKLY = "weekly"
#    MONTHLY = "monthly"
#    HOURLY = "hourly"
#    ONCE = "once"

class BackupEntryStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    MISSING = "MISSING"
    HASH_MISMATCH = "HASH_MISMATCH"
    TRANSFER_INTEGRITY_FAILED = "TRANSFER_INTEGRITY_FAILED"
    UNKNOWN = "UNKNOWN"


# --- TABLE 1: ExpectedBackupJob ---
class ExpectedBackupJob(Base):
    __tablename__ = "expected_backup_jobs"

    id = Column(Integer, primary_key=True, index=True)
    year = Column(Integer, nullable=False, comment="Année (ex: 2025)")
    company_name = Column(String, nullable=False, index=True, comment="Nom de l'entreprise")
    city = Column(String, nullable=False, index=True, comment="Ville de l'agence")
    neighborhood = Column(String, nullable=False, index=True, comment="Quartier ou zone spécifique de l'agence") # NOUVEAU CHAMP
    database_name = Column(String, nullable=False, index=True, comment="Nom de la base de données")
    #expected_hour_utc = Column(Integer, nullable=False, comment="Heure attendue de fin de sauvegarde (UTC)")
    #expected_minute_utc = Column(Integer, nullable=False, comment="Minute attendue de fin de sauvegarde (UTC)")
    
    __table_args__ = (
        UniqueConstraint('year', 'company_name', 'city', 'neighborhood', 'database_name', # AJUSTÉ: Ajout de 'neighborhood'
                       
                       name='_unique_job_config'),
    )

    # Chemins de stockage pour l'agent et la destination finale
    agent_id_responsible = Column(String, nullable=False, index=True, comment="ID de l'agent responsable de ce job")
    agent_deposit_path_template = Column(String, nullable=False, comment="Template du chemin de dépôt des fichiers de BD par l'agent")
    # AJUSTÉ: le template du STATUS.json n'est plus horaire mais basé sur entreprise/ville/quartier
    agent_log_deposit_path_template = Column(String, nullable=False, comment="Template du chemin de dépôt du dossier des logs par l'agent (ex: {agent_id}/log/)") 
    final_storage_path_template = Column(String, nullable=False, comment="Template du chemin final de stockage des sauvegardes validées")

    #expected_frequency = Column(SQLEnum(*[f.value for f in BackupFrequency]), nullable=False)
    #days_of_week = Column(String, nullable=False)
    
    #current_status = Column(SQLEnum(*[s.value for s in JobStatus]), default=JobStatus.UNKNOWN.value, nullable=False)
    current_status = Column(String, nullable=False, default=JobStatus.UNKNOWN.value)  # Utiliser la valeur de l'énumération
    
    last_checked_timestamp = Column(DateTime, nullable=True)
    last_successful_backup_timestamp = Column(DateTime, nullable=True)
    notification_recipients = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, comment="Date de création")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Date de dernière mise à jour")

    # Relation avec les entrées d'historique de sauvegarde   ....................MODIF
    backup_entries = relationship("BackupEntry"
                                  , back_populates="expected_job"
                                  , order_by="desc(BackupEntry.timestamp)"
                                  , lazy=True
                                  ,cascade="all, delete-orphan"
                                  , passive_deletes=True, 
    )

    previous_successful_hash_global = Column(String(64), nullable=True, comment="Dernier hash global de succès pour cette BD")

    def __repr__(self):
        return (f"<ExpectedBackupJob(company='{self.company_name}', city='{self.city}', "
                f"neighborhood='{self.neighborhood}', db='{self.database_name}', year={self.year}, " # AJUSTÉ: Ajout de 'neighborhood'
                f"agent='{self.agent_id_responsible}', "
                #f"expected_time={self.expected_hour_utc:02d}:{self.expected_minute_utc:02d} UTC, "
                f"status='{self.current_status}')>")


# --- TABLE 2: BackupEntry ---
class BackupEntry(Base):
    """
    Modèle de base de données pour l'historique des événements de sauvegarde.
    Chaque entrée enregistre les rapports de l'agent et les validations du serveur.
    """
    __tablename__ = "backup_entries"

    id = Column(Integer
                , primary_key=True
                , index=True
    )
    #expected_job_id = Column(Integer, ForeignKey("expected_backup_jobs.id"), nullable=False, index=True)
    expected_job = relationship("ExpectedBackupJob", back_populates="backup_entries") # Correction ici du back_populates
    expected_job_id = Column(Integer, ForeignKey("expected_backup_jobs.id", ondelete="CASCADE"), nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Horodatage de la détection par le serveur")
    status = Column(SQLEnum(*[s.value for s in BackupEntryStatus]), nullable=False, index=True)
    message = Column(Text, nullable=True, comment="Message détaillé sur l'événement")
    
    #calculated_hash = Column(String, nullable=True) 
    expected_hash = Column(String, nullable=True) 
    
    
    # Champs provenant du rapport STATUS.json de l'agent
    operation_log_file_name = Column(String, nullable=True, comment="Nom du fichier STATUS.json global ayant déclenché cette entrée")
    agent_id = Column(String, nullable=True, comment="ID de l'agent ayant produit le rapport")
    agent_overall_status = Column(String, nullable=True, comment="Statut global de l'opération rapporté par l'agent")

    #agent_backup_process_status = Column(Boolean, nullable=True)
    #agent_backup_process_start_time = Column(DateTime, nullable=True)
    #agent_backup_process_timestamp = Column(DateTime, nullable=True)
    #agent_backup_hash_pre_compress = Column(String(64), nullable=True)
    #agent_backup_size_pre_compress = Column(BigInteger, nullable=True)

    #agent_compress_process_status = Column(Boolean, nullable=True)
    #agent_compress_process_start_time = Column(DateTime, nullable=True)
    #agent_compress_process_timestamp = Column(DateTime, nullable=True)
    #agent_compress_hash_post_compress = Column(String(64), nullable=True)
    #agent_compress_size_post_compress = Column(BigInteger, nullable=True)

    #agent_transfer_process_status = Column(Boolean, nullable=True)
    #agent_transfer_process_start_time = Column(DateTime, nullable=True)
    #agent_transfer_process_timestamp = Column(DateTime, nullable=True)
    #agent_transfer_error_message = Column(Text, nullable=True)
    #agent_staged_file_name = Column(String, nullable=True)
    #agent_logs_summary = Column(Text, nullable=True)

    # Champs de validation côté serveur
    server_calculated_staged_hash = Column(String(64), nullable=True, comment="Hachage du fichier dans la zone de dépôt calculé par le serveur")
    server_calculated_staged_size = Column(BigInteger, nullable=True, comment="Taille du fichier dans la zone de dépôt calculée par le serveur")

    # Vérification de Hachage pour HASH_MISMATCH
    previous_successful_hash_global = Column(String(64), nullable=True, comment="Hachage de la dernière sauvegarde globale réussie pour cette BD")
    hash_comparison_result = Column(Boolean, nullable=True, comment="Résultat de la comparaison des hachages (True si différent, False si identique)")

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (f"<BackupEntry(job_id={self.expected_job_id}, status='{self.status.value}', "
                f"timestamp='{self.timestamp}', agent_status={self.agent_transfer_process_status}, "
                f"server_hash_ok={self.hash_comparison_result})>")
