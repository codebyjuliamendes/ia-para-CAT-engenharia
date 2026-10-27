"""create cats table

Revision ID: 0001
Revises:
Create Date: 2026-10-27
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cats",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("nome", sa.String(70), nullable=False),
        sa.Column("cpf", sa.String(11), nullable=False),
        sa.Column("setor", sa.String(100)),
        sa.Column("data_acidente", sa.Date(), nullable=False),
        sa.Column("tipo_acidente", sa.Integer(), nullable=False),
        sa.Column("tipo_cat", sa.Integer(), nullable=False),
        sa.Column("gravidade", sa.String(20)),
        sa.Column("parte_codigo", sa.String(9)),
        sa.Column("parte_descricao", sa.String(200)),
        sa.Column("dias_perdidos", sa.Integer(), nullable=False),
        sa.Column("pendencias", sa.Integer(), nullable=False),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("analise", sa.JSON()),
        sa.Column("analise_revisada", sa.Boolean(), nullable=False),
        sa.Column("revisor", sa.Text()),
    )
    op.create_index("ix_cats_cpf", "cats", ["cpf"])
    op.create_index("ix_cats_data_acidente", "cats", ["data_acidente"])


def downgrade() -> None:
    op.drop_index("ix_cats_data_acidente", table_name="cats")
    op.drop_index("ix_cats_cpf", table_name="cats")
    op.drop_table("cats")
