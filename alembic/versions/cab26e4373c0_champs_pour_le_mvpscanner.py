"""Champs pour le MVPSCanner

Revision ID: cab26e4373c0
Revises: e0b121a34984
Create Date: 2025-06-17 16:25:16.697493

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cab26e4373c0'
down_revision: Union[str, None] = 'e0b121a34984'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Récupération du bind et de l'inspecteur pour vérifier les colonnes existantes de backup_entries
    conn = op.get_bind()
    from sqlalchemy.engine import reflection
    insp = reflection.Inspector.from_engine(conn)
    backup_columns = [col["name"] for col in insp.get_columns("backup_entries")]

    # Utilisation du batch mode pour manipuler la table backup_entries sur SQLite
    with op.batch_alter_table('backup_entries') as batch_op:
        if 'agent_compress_hash_post_compress' in backup_columns:
            batch_op.drop_column('agent_compress_hash_post_compress')
        if 'agent_compress_size_post_compress' in backup_columns:
            batch_op.drop_column('agent_compress_size_post_compress')
        if 'agent_transfer_process_start_time' in backup_columns:
            batch_op.drop_column('agent_transfer_process_start_time')
        if 'agent_backup_process_start_time' in backup_columns:
            batch_op.drop_column('agent_backup_process_start_time')
        if 'agent_transfer_process_timestamp' in backup_columns:
            batch_op.drop_column('agent_transfer_process_timestamp')
        if 'agent_transfer_process_status' in backup_columns:
            batch_op.drop_column('agent_transfer_process_status')
        if 'agent_backup_process_status' in backup_columns:
            batch_op.drop_column('agent_backup_process_status')
        if 'agent_staged_file_name' in backup_columns:
            batch_op.drop_column('agent_staged_file_name')
        if 'agent_logs_summary' in backup_columns:
            batch_op.drop_column('agent_logs_summary')
        if 'agent_transfer_error_message' in backup_columns:
            batch_op.drop_column('agent_transfer_error_message')
        if 'agent_compress_process_status' in backup_columns:
            batch_op.drop_column('agent_compress_process_status')
        if 'agent_compress_process_timestamp' in backup_columns:
            batch_op.drop_column('agent_compress_process_timestamp')
        if 'agent_backup_size_pre_compress' in backup_columns:
            batch_op.drop_column('agent_backup_size_pre_compress')
        if 'agent_compress_process_start_time' in backup_columns:
            batch_op.drop_column('agent_compress_process_start_time')
        if 'agent_backup_hash_pre_compress' in backup_columns:
            batch_op.drop_column('agent_backup_hash_pre_compress')
        if 'agent_backup_process_timestamp' in backup_columns:
            batch_op.drop_column('agent_backup_process_timestamp')
    
    # Pour la table expected_backup_jobs, on utilise également le batch mode pour modifier la contrainte unique.
    with op.batch_alter_table('expected_backup_jobs') as batch_op:
        batch_op.drop_constraint('_unique_job_config', type_='unique')
        batch_op.create_unique_constraint('_unique_job_config', 
                                          ['year', 'company_name', 'city', 'neighborhood', 'database_name'])
    
    # Suppression des colonnes dans expected_backup_jobs
    op.drop_column('expected_backup_jobs', 'expected_minute_utc')
    op.drop_column('expected_backup_jobs', 'expected_frequency')
    op.drop_column('expected_backup_jobs', 'days_of_week')
    op.drop_column('expected_backup_jobs', 'expected_hour_utc')


def downgrade() -> None:
    """Downgrade schema."""
    # Réintégration des colonnes dans expected_backup_jobs
    op.add_column('expected_backup_jobs', sa.Column('expected_hour_utc', sa.INTEGER(), nullable=False))
    op.add_column('expected_backup_jobs', sa.Column('days_of_week', sa.VARCHAR(), nullable=False))
    op.add_column('expected_backup_jobs', sa.Column('expected_frequency', sa.VARCHAR(length=7), nullable=False))
    op.add_column('expected_backup_jobs', sa.Column('expected_minute_utc', sa.INTEGER(), nullable=False))
    
    with op.batch_alter_table('expected_backup_jobs') as batch_op:
        batch_op.drop_constraint('_unique_job_config', type_='unique')
        batch_op.create_unique_constraint(
            '_unique_job_config',
            ['year', 'company_name', 'city', 'neighborhood', 'database_name', 'expected_hour_utc', 'expected_minute_utc']
        )
    
    # Réajout des colonnes supprimées dans backup_entries
    op.add_column('backup_entries', sa.Column('agent_backup_process_timestamp', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_backup_hash_pre_compress', sa.VARCHAR(length=64), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_compress_process_start_time', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_backup_size_pre_compress', sa.BIGINT(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_compress_process_timestamp', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_compress_process_status', sa.BOOLEAN(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_transfer_error_message', sa.TEXT(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_logs_summary', sa.TEXT(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_staged_file_name', sa.VARCHAR(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_backup_process_status', sa.BOOLEAN(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_transfer_process_status', sa.BOOLEAN(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_transfer_process_timestamp', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_backup_process_start_time', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_transfer_process_start_time', sa.DATETIME(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_compress_size_post_compress', sa.BIGINT(), nullable=True))
    op.add_column('backup_entries', sa.Column('agent_compress_hash_post_compress', sa.VARCHAR(length=64), nullable=True))
