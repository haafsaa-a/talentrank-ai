"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-04-28 09:45:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create CandidateStatus enum
    candidate_status = postgresql.ENUM('pending', 'linkedin_pending', 'scraping', 'done', 'failed', name='candidatestatus')
    candidate_status.create(op.get_bind())

    # Create candidates table
    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('github_url', sa.String(), nullable=True),
        sa.Column('portfolio_url', sa.String(), nullable=True),
        sa.Column('linkedin_connected', sa.Boolean(), nullable=True),
        sa.Column('linkedin_access_token', sa.String(), nullable=True),
        sa.Column('status', candidate_status, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('state_token', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_candidates_email'), 'candidates', ['email'], unique=True)

    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('candidate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('top_projects', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('experience_years', sa.Integer(), nullable=True),
        sa.Column('domain_tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('talent_rank_score', sa.Float(), nullable=True),
        sa.Column('raw_github_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_portfolio_text', sa.Text(), nullable=True),
        sa.Column('raw_linkedin_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id')
    )

def downgrade() -> None:
    op.drop_table('profiles')
    op.drop_index(op.f('ix_candidates_email'), table_name='candidates')
    op.drop_table('candidates')
    
    candidate_status = postgresql.ENUM('pending', 'linkedin_pending', 'scraping', 'done', 'failed', name='candidatestatus')
    candidate_status.drop(op.get_bind())
