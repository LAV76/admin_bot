"""
Миграция для создания таблицы users и связанных таблиц
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Версия миграции
revision = '20250309001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Выполняет создание таблиц users, user_roles, role_history
    """
    # Создание таблицы users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('user_role', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('is_bot', sa.Boolean(), server_default=sa.text('false'), nullable=True),
        sa.Column('language_code', sa.String(length=10), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Создание индекса для user_id
    op.create_index('ix_users_user_id', 'users', ['user_id'], unique=True)
    
    # Создание таблицы user_roles
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role_type', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('created_by', sa.BigInteger(), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_type', name='user_role_unique')
    )
    
    # Создание индексов для user_roles
    op.create_index('idx_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('idx_user_roles_role_type', 'user_roles', ['role_type'], unique=False)
    
    # Создание таблицы role_history
    op.create_table(
        'role_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),  # 'add' или 'remove'
        sa.Column('admin_id', sa.BigInteger(), nullable=False),
        sa.Column('action_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание аудит-таблицы для ролей
    op.create_table(
        'role_audit',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('role_type', sa.String(length=50), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('performed_by', sa.BigInteger(), nullable=False),
        sa.Column('performed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индексов для role_audit
    op.create_index('idx_role_audit_user_id', 'role_audit', ['user_id'], unique=False)
    op.create_index('idx_role_audit_performed_at', 'role_audit', ['performed_at'], unique=False)


def downgrade() -> None:
    """
    Отмена создания таблиц - удаление таблиц в обратном порядке
    """
    # Удаление таблиц в обратном порядке их создания
    op.drop_index('idx_role_audit_performed_at', table_name='role_audit')
    op.drop_index('idx_role_audit_user_id', table_name='role_audit')
    op.drop_table('role_audit')
    op.drop_table('role_history')
    op.drop_index('idx_user_roles_role_type', table_name='user_roles')
    op.drop_index('idx_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')
    op.drop_index('ix_users_user_id', table_name='users')
    op.drop_table('users') 