"""
Миграция для создания таблицы posts
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# Версия миграции
revision = '20250309003'
down_revision = '20250309002'  # Ссылка на предыдущую миграцию (channels)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Выполняет создание таблицы posts
    """
    # Создание таблицы posts
    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('post_name', sa.String(length=255), nullable=False, comment="Название поста"),
        sa.Column('post_description', sa.Text(), nullable=False, comment="Текст поста"),
        sa.Column('post_image', sa.String(length=255), nullable=True, comment="Ссылка на изображение поста"),
        sa.Column('post_tag', sa.String(length=100), nullable=True, comment="Тег поста"),
        sa.Column('username', sa.String(length=100), nullable=False, comment="Имя пользователя, создавшего пост"),
        sa.Column('user_id', sa.BigInteger(), nullable=False, comment="ID пользователя, создавшего пост"),
        sa.Column('created_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment="Дата создания поста"),
        sa.Column('is_published', sa.Integer(), nullable=False, comment="Флаг публикации поста (0 - черновик, 1 - опубликован)"),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True, comment="Дата и время публикации поста"),
        sa.Column('target_chat_id', sa.BigInteger(), nullable=True, comment="ID чата, в который должен быть опубликован пост"),
        sa.Column('target_chat_title', sa.String(length=255), nullable=True, comment="Название чата для публикации"),
        sa.Column('change_username', sa.String(length=100), nullable=True, comment="Имя пользователя, который последним редактировал пост"),
        sa.Column('change_date', sa.DateTime(timezone=True), nullable=True, comment="Дата и время последнего редактирования"),
        sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False, comment="Флаг архивации поста"),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True, comment="Дата и время архивации поста"),
        sa.Column('archived_by', sa.BigInteger(), nullable=True, comment="ID пользователя, который архивировал пост"),
        sa.Column('message_id', sa.BigInteger(), nullable=True, comment="ID сообщения в Telegram после публикации"),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создание индексов для posts
    op.create_index('idx_posts_user_id', 'posts', ['user_id'], unique=False)
    op.create_index('idx_posts_post_tag', 'posts', ['post_tag'], unique=False)
    op.create_index('idx_posts_is_published', 'posts', ['is_published'], unique=False)
    op.create_index('idx_posts_is_archived', 'posts', ['is_archived'], unique=False)
    op.create_index('idx_posts_created_date', 'posts', ['created_date'], unique=False)
    
    # Добавление внешнего ключа к таблице posts, связывающего user_id с users.user_id
    op.create_foreign_key(
        'fk_posts_user',
        'posts', 'users',
        ['user_id'], ['user_id'],
        ondelete='CASCADE'
    )
    
    # Добавление внешнего ключа к таблице posts, связывающего target_chat_id с channels.chat_id
    op.create_foreign_key(
        'fk_posts_channel',
        'posts', 'channels',
        ['target_chat_id'], ['chat_id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """
    Отмена создания таблицы posts
    """
    # Удаление внешних ключей
    op.drop_constraint('fk_posts_channel', 'posts', type_='foreignkey')
    op.drop_constraint('fk_posts_user', 'posts', type_='foreignkey')
    
    # Удаление индексов
    op.drop_index('idx_posts_created_date', table_name='posts')
    op.drop_index('idx_posts_is_archived', table_name='posts')
    op.drop_index('idx_posts_is_published', table_name='posts')
    op.drop_index('idx_posts_post_tag', table_name='posts')
    op.drop_index('idx_posts_user_id', table_name='posts')
    
    # Удаление таблицы
    op.drop_table('posts') 