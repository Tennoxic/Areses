from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd38d07e8feac'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('sources',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('site_url', sa.String(), nullable=True),
    sa.Column('favicon_url', sa.String(), nullable=True),
    sa.Column('fetch_interval_minutes', sa.Integer(), server_default='60', nullable=False),
    sa.Column('http_username', sa.String(), nullable=True),
    sa.Column('http_password', sa.String(), nullable=True),
    sa.Column('custom_headers', sa.Text(), nullable=True),
    sa.Column('etag', sa.String(), nullable=True),
    sa.Column('last_modified', sa.String(), nullable=True),
    sa.Column('last_fetched_at', sa.DateTime(), nullable=True),
    sa.Column('next_fetch_at', sa.DateTime(), nullable=False),
    sa.Column('last_fetch_status', sa.String(), nullable=True),
    sa.Column('last_error_message', sa.Text(), nullable=True),
    sa.Column('consecutive_fail_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('backoff_multiplier', sa.Integer(), server_default='1', nullable=False),
    sa.Column('active', sa.Boolean(), server_default='1', nullable=False),
    sa.Column('is_fetching', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_index('ix_sources_next_fetch_at', 'sources', ['next_fetch_at'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('password_hash', sa.String(), nullable=False),
    sa.Column('is_admin', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('articles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('url', sa.String(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('author', sa.String(), nullable=True),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('ai_summary', sa.Text(), nullable=True),
    sa.Column('word_count', sa.Integer(), nullable=True),
    sa.Column('reading_time_minutes', sa.Integer(), nullable=True),
    sa.Column('summary_pending', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('enclosure_url', sa.String(), nullable=True),
    sa.Column('enclosure_type', sa.String(), nullable=True),
    sa.Column('extraction_failed', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('published_at', sa.DateTime(), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('url')
    )
    op.create_index('ix_articles_source_id_fetched_at', 'articles', ['source_id', 'fetched_at'], unique=False)
    op.create_table('folders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['folders.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('password_reset_tokens',
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('token')
    )
    op.create_table('push_subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('endpoint', sa.Text(), nullable=False),
    sa.Column('p256dh', sa.String(), nullable=False),
    sa.Column('auth', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('endpoint')
    )
    op.create_table('saved_searches',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('query', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sessions',
    sa.Column('token', sa.String(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('token')
    )
    op.create_table('settings',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('key', sa.String(), nullable=False),
    sa.Column('value', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'key')
    )
    op.create_table('subscriptions',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('source_id', sa.Integer(), nullable=False),
    sa.Column('folder_id', sa.Integer(), nullable=True),
    sa.Column('custom_name', sa.String(), nullable=True),
    sa.Column('summarize_enabled', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('auto_read_pattern', sa.String(), nullable=True),
    sa.Column('notify_enabled', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('hidden', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('fetch_interval_minutes_override', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['folder_id'], ['folders.id'], ),
    sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'source_id')
    )
    op.create_table('user_article_state',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.Column('is_read', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('read_at', sa.DateTime(), nullable=True),
    sa.Column('starred', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('read_later', sa.Boolean(), server_default='0', nullable=False),
    sa.Column('scroll_position', sa.Float(), server_default='0', nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['articles.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'article_id')
    )
    op.create_index('ix_user_article_state_user_id_is_read_article_id', 'user_article_state', ['user_id', 'is_read', 'article_id'], unique=False)

    op.execute(
        """
        CREATE VIRTUAL TABLE articles_fts USING fts5(
            title, author, content,
            content='articles', content_rowid='id',
            tokenize='porter unicode61'
        )
        """
    )
    op.execute(
        """
        CREATE TRIGGER articles_fts_ai AFTER INSERT ON articles BEGIN
            INSERT INTO articles_fts(rowid, title, author, content)
            VALUES (new.id, new.title, new.author, new.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER articles_fts_ad AFTER DELETE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, author, content)
            VALUES ('delete', old.id, old.title, old.author, old.content);
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER articles_fts_au AFTER UPDATE ON articles BEGIN
            INSERT INTO articles_fts(articles_fts, rowid, title, author, content)
            VALUES ('delete', old.id, old.title, old.author, old.content);
            INSERT INTO articles_fts(rowid, title, author, content)
            VALUES (new.id, new.title, new.author, new.content);
        END
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS articles_fts_au")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ad")
    op.execute("DROP TRIGGER IF EXISTS articles_fts_ai")
    op.execute("DROP TABLE IF EXISTS articles_fts")
    op.drop_index('ix_user_article_state_user_id_is_read_article_id', table_name='user_article_state')
    op.drop_table('user_article_state')
    op.drop_table('subscriptions')
    op.drop_table('settings')
    op.drop_table('sessions')
    op.drop_table('saved_searches')
    op.drop_table('push_subscriptions')
    op.drop_table('password_reset_tokens')
    op.drop_table('folders')
    op.drop_index('ix_articles_source_id_fetched_at', table_name='articles')
    op.drop_table('articles')
    op.drop_table('users')
    op.drop_index('ix_sources_next_fetch_at', table_name='sources')
    op.drop_table('sources')
