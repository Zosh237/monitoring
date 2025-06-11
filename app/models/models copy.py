from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, Text, ForeignKey, BigInteger,Boolean, UniqueConstraint 
from sqlalchemy.orm import relationship

#Import de la classe de base déclarative
from app.core.database import Base

# --- Définition des Enums pour la cohérence des données ---
class JobStatus(str, Enum):
    OK = "ok"
    FAILED = "failed"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"
    UNKNOWN = "unknown"

class BackupFrequency(str, Enum):
    """
    Frequence attendue de la sauvegarde (pour la configuration du job).
    """
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    HOURLY = "hourly"
    ONCE = 'once'
    
class BackupEntryStatus(str, Enum):
    """
    Statut d'une entrée d'historique de  sauvegarder spécifique.
    Indique le résultat d'une exécution de sauvegarde.
    """
    SUCCESS = "success"
    FAILED = "failed"
    MISSING = "missing"
    HASH_MISMATCH = "hash_mismatch"
    
# --- TABLE 1: ExpectedBackupJob (Configuration des Jobs à Surveiller) ---
class ExpectedBackupJob(Base):
    """
    Modèle de base de données pour les jobs de sauvegarde attendus.
    Chaque entrée définit une base de données spécifique à surveiller,
    sa fréquence et son créneau horaire. 
    """
    __tablename__ = "expected_backup_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Identifiants uniques du job de sauvegarde
    year = Column(Integer, nullable=False, comment="Année de la structure de dossier (ex: 2025)")
    company_name = Column(String, nullable=False, index=True, comment="Nom de l'entreprise (ex: Sirpacam)")
    city = Column(String, nullable=False, index=True, comment="Ville de l'agence (ex: Douala, Yaoundé)")
    database_name = Column(String, nullable=False, index=True, comment="Nom de la base de données (ex: compta_db)")

    # Heure et minute attendues du cycle de sauvegarde (UTC)
    expected_hour_utc = Column(Integer, nullable=False, comment="Heure attendue de fin de sauvegarde (0-23 UTC)")
    expected_minute_utc = Column(Integer, nullable=False, comment="Minute attendue de fin de sauvegarde (0-59 UTC)")

    # Contrainte unique pour identifier un job par sa combinaison complète
    __table_args__ = (
        UniqueConstraint('year', 'company_name', 'city', 'database_name',
                         'expected_hour_utc', 'expected_minute_utc',
                         name='_unique_job_config'),
    )

    # Chemin de base où les fichiers de cette BD sont stockés sur le serveur
    # Ex: /mnt/backups/2025/Sirpacam/Douala/compta_db/
    expected_storage_base_path = Column(String, nullable=False, comment="Chemin racine du stockage de la BD sur le serveur")

    # Fréquence et jours de la semaine attendus
    expected_frequency = Column(Enum(BackupFrequency), nullable=False, comment="Fréquence de la sauvegarde attendue")
    # Stocké comme une chaîne de caractères séparée par des virgules (ex: "MO,TU,WE,TH,FR,SA")
    days_of_week = Column(String, nullable=False, comment="Jours de la semaine où la sauvegarde est attendue (codes courts)")

    # Statut actuel et métadonnées de monitoring
    current_status = Column(Enum(JobStatus), default=JobStatus.UNKNOWN, nullable=False, comment="Statut actuel du job (mis à jour par le scanner)")
    last_checked_timestamp = Column(DateTime, nullable=True, comment="Dernier horodatage où ce job a été scanné")
    last_successful_backup_timestamp = Column(DateTime, nullable=True, comment="Horodatage de la dernière sauvegarde réussie trouvée pour ce job")

    # Informations pour les notifications
    notification_recipients = Column(String, nullable=True, comment="Adresses email ou canaux de notification")

    # Contrôles administratifs
    is_active = Column(Boolean, default=True, nullable=False, comment="Indique si ce job est activement surveillé")
    created_at = Column(DateTime, default=datetime.utcnow, comment="Date de création de l'entrée")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="Date de dernière mise à jour de l'entrée")

    # Relation avec les entrées d'historique de sauvegarde
    # 'lazy=True' signifie que les entrées ne seront chargées que si on y accède.
    backup_entries = relationship("BackupEntry", back_populates="expected_job", order_by="desc(BackupEntry.timestamp)", lazy=True)

    def __repr__(self):
        return (f"<ExpectedBackupJob(company='{self.company_name}', city='{self.city}', "
                f"db='{self.database_name}', year={self.year}, "
                f"expected_time={self.expected_hour_utc:02d}:{self.expected_minute_utc:02d} UTC, "
                f"status='{self.current_status.value}')>")

# --- TABLE 2: BackupEntry (Historique des Événements de Sauvegarde) ---
class BackupEntry(Base):
    """
    Modèle de base de données pour l'historique des événements de sauvegarde.
    Chaque entrée représente une tentative de sauvegarde et son résultat.
    """
    __tablename__ = "backup_entries"

    id = Column(Integer, primary_key=True, index=True)

    # Clé étrangère vers le job attendu auquel cette entrée d'historique se rapporte
    expected_job_id = Column(Integer, ForeignKey("expected_backup_jobs.id"), nullable=False, index=True,
                             comment="ID du job de sauvegarde attendu auquel cette entrée se réfère")
    expected_job = relationship("ExpectedBackupJob", back_populates="backup_entries")

    # Informations sur l'événement de sauvegarde
    # 'timestamp' est le moment où le scanner a détecté/enregistré cet événement.
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, comment="Horodatage de la détection/enregistrement de l'événement par le serveur")
    status = Column(Enum(BackupEntryStatus), nullable=False, index=True, comment="Statut de l'événement de sauvegarde")
    message = Column(Text, nullable=True, comment="Message détaillé sur l'événement (succès, échec, alerte)")

    # Métadonnées du fichier de statut logé
    log_file_name = Column(String, nullable=True, comment="Nom du fichier de statut logé (ex: compta_db_YYYYMMDD_HHMM_SUCCESS.json)")
    
    # Détails du fichier de sauvegarde tel que rapporté par l'agent et transféré
    backup_file_name = Column(String, nullable=True, comment="Nom du fichier de BD (ex: compta_db.sql.gz)")
    file_size_bytes = Column(BigInteger, nullable=True, comment="Taille du fichier de BD en octets")
    checksum_sha256 = Column(String(64), nullable=True, index=True, comment="Hachage SHA256 du fichier de BD (transféré et stagé)")

    # Informations pour la détection du hachage inchangé
    previous_checksum_sha256 = Column(String(64), nullable=True, comment="Hachage SHA256 de la dernière sauvegarde réussie connue pour cette BD")
    hash_comparison_result = Column(Boolean, nullable=True, comment="Résultat de la comparaison des hachages (True si différent, False si identique)")

    created_at = Column(DateTime, default=datetime.utcnow, comment="Date de création de l'entrée d'historique")

    def __repr__(self):
        return (f"<BackupEntry(job_id={self.expected_job_id}, status='{self.status.value}', "
                f"timestamp='{self.timestamp}', hash_ok={self.hash_comparison_result})>")

