"""initial_tables

Revision ID: 001_initial_tables
Revises: 
Create Date: 2026-10-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial_tables'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Admins ──
    op.create_table(
        'admins',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )

    # ── Devices ──
    op.create_table(
        'devices',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('secret_key_hash', sa.String(length=255), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # ── Plans ──
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.PrimaryKeyConstraint('id')
    )

    # ── Members ──
    op.create_table(
        'members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone', sa.String(length=15), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('extra', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone')
    )

    # ── Memberships ──
    op.create_table(
        'memberships',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_memberships_member_end', 'memberships', ['member_id', 'end_date'])

    # ── Cards ──
    op.create_table(
        'cards',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=20), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uid')
    )
    op.create_index('ix_cards_uid', 'cards', ['uid'])

    # ── Attendance ──
    op.create_table(
        'attendance',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('attendance_date', sa.Date(), nullable=False),
        sa.Column('checkin_time', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('member_id', 'attendance_date', name='uq_member_date')
    )
    op.create_index('ix_attendance_date', 'attendance', ['attendance_date'])

    # ── ScanLog ──
    op.create_table(
        'scan_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uid', sa.String(length=20), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum('marked', 'already_marked', 'expired', 'unknown', 'inactive', 'linked', 'rejected', name='scanresult'), nullable=False),
        sa.Column('response_ms', sa.Integer(), nullable=True),
        sa.Column('scanned_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # ── PendingAssignments ──
    op.create_table(
        'pending_assignments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'done', 'expired', name='assignmentstatus'), server_default='pending', nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['members.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('pending_assignments')
    op.drop_table('scan_log')
    op.drop_index('ix_attendance_date', table_name='attendance')
    op.drop_table('attendance')
    op.drop_index('ix_cards_uid', table_name='cards')
    op.drop_table('cards')
    op.drop_index('ix_memberships_member_end', table_name='memberships')
    op.drop_table('memberships')
    op.drop_table('members')
    op.drop_table('plans')
    op.drop_table('devices')
    op.drop_table('admins')
