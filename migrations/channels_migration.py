"""
Миграция для создания таблицы channels
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Версия миграции
revision = '20250309002'
down_revision = '20250309001'  # Ссылка на предыдущую миграцию (users)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Выполняет создание таблицы channels
    """
    # Создание таблицы channels
    op.create_table(
        'channels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('chat_type', sa.String(length=50), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('added_by', sa.BigInteger(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('chat_id')
    )
    
    # Создание индексов для channels
    op.create_index('idx_channels_chat_id', 'channels', ['chat_id'], unique=True)
    op.create_index('idx_channels_is_default', 'channels', ['is_default'], unique=False)
    
    # Добавление внешнего ключа к таблице channels, связывающего added_by с users.user_id
    op.create_foreign_key(
        'fk_channels_user',
        'channels', 'users',
        ['added_by'], ['user_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Отмена создания таблицы channels
    """
    # Удаление внешнего ключа
    op.drop_constraint('fk_channels_user', 'channels', type_='foreignkey')
    
    # Удаление индексов
    op.drop_index('idx_channels_is_default', table_name='channels')
    op.drop_index('idx_channels_chat_id', table_name='channels')
    
    # Удаление таблицы
    op.drop_table('channels') 