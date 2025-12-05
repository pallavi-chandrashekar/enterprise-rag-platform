"""add_content_tsv_to_chunk

Revision ID: 0002
Revises: 0001
Create Date: 2025-12-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import TSVECTOR


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('chunks', sa.Column('content_tsv', TSVECTOR(), nullable=True))
    op.create_index('ix_chunks_content_tsv', 'chunks', ['content_tsv'], unique=False, postgresql_using='gin')

    op.execute("""
        CREATE OR REPLACE FUNCTION content_tsv_update_trigger()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.content_tsv := to_tsvector('english', NEW.content);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER tsvector_update_before_insert_or_update
        BEFORE INSERT OR UPDATE ON chunks
        FOR EACH ROW EXECUTE PROCEDURE content_tsv_update_trigger();
    """)


def downgrade():
    op.execute("DROP TRIGGER IF EXISTS tsvector_update_before_insert_or_update ON chunks;")
    op.execute("DROP FUNCTION IF EXISTS content_tsv_update_trigger();")
    op.drop_index('ix_chunks_content_tsv', table_name='chunks')
    op.drop_column('chunks', 'content_tsv')
