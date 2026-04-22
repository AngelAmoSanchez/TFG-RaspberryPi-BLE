
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None

def upgrade():
    op.create_table('devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.String(50), nullable=False),
        sa.Column('name', sa.String(100)),
        sa.Column('location', sa.String(200)),
        sa.Column('is_active', sa.Integer(), default=1),
        sa.Column('last_seen', sa.DateTime()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_devices_device_id', 'devices', ['device_id'], unique=True)
    
    op.create_table('detections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_hash', sa.String(64), nullable=False),
        sa.Column('rssi', sa.Integer(), nullable=False),
        sa.Column('zone', sa.Enum('near', 'medium', 'far', name='zoneenum'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('device_id', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_detections_device_hash', 'detections', ['device_hash'])
    op.create_index('ix_detections_timestamp', 'detections', ['timestamp'])
    op.create_index('ix_detections_zone', 'detections', ['zone'])
    op.create_index('idx_device_hash_timestamp', 'detections', ['device_hash', 'timestamp'])
    
    op.create_table('aggregated_stats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('period_type', sa.String(20), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('zone', sa.Enum('near', 'medium', 'far', name='zoneenum'), nullable=False),
        sa.Column('unique_devices', sa.Integer(), default=0),
        sa.Column('total_detections', sa.Integer(), default=0),
        sa.Column('estimated_people', sa.Integer(), default=0),
        sa.Column('avg_rssi', sa.Float()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('aggregated_stats')
    op.drop_table('detections')
    op.drop_table('devices')
