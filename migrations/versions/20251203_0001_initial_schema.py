"""initial schema for telemedicina calls, auth, metrics

Revision ID: 20251203_0001
Revises:
Create Date: 2025-12-03 17:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20251203_0001"
down_revision = None
branch_labels = None
depends_on = None

user_role_enum = sa.Enum("doctor", "patient", name="userrole")
call_status_enum = sa.Enum(
    "waiting",
    "assigned",
    "ringing",
    "in_progress",
    "reconnecting",
    "ended",
    "cancelled",
    name="callstatus",
)


def upgrade() -> None:

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('utc', NOW())"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('utc', NOW())"),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "rooms",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('utc', NOW())"),
            nullable=False,
        ),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_table(
        "calls",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("patient_id", sa.String(length=36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("doctor_id", sa.String(length=36), sa.ForeignKey("users.id")),
        sa.Column(
            "status",
            call_status_enum,
            nullable=False,
            server_default=sa.text("'waiting'::callstatus"),
        ),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('utc', NOW())"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("last_resume_at", sa.DateTime(timezone=True)),
        sa.Column("total_reconnects", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index(op.f("ix_calls_room_id"), "calls", ["room_id"], unique=False)
    op.create_index(op.f("ix_calls_patient_id"), "calls", ["patient_id"], unique=False)
    op.create_index(op.f("ix_calls_doctor_id"), "calls", ["doctor_id"], unique=False)
    op.create_index(op.f("ix_calls_status"), "calls", ["status"], unique=False)

    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_id", sa.String(length=64), sa.ForeignKey("rooms.id"), nullable=False),
        sa.Column("sid", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), sa.ForeignKey("users.id")),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("TIMEZONE('utc', NOW())"),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True)),
    )
    op.create_index(op.f("ix_participants_room_id"), "participants", ["room_id"], unique=False)
    op.create_index(op.f("ix_participants_sid"), "participants", ["sid"], unique=False)
    op.create_index(op.f("ix_participants_user_id"), "participants", ["user_id"], unique=False)
    op.create_index(
        "ix_participants_room_sid",
        "participants",
        ["room_id", "sid"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_participants_room_sid", table_name="participants")
    op.drop_index(op.f("ix_participants_user_id"), table_name="participants")
    op.drop_index(op.f("ix_participants_sid"), table_name="participants")
    op.drop_index(op.f("ix_participants_room_id"), table_name="participants")
    op.drop_table("participants")

    op.drop_index(op.f("ix_calls_status"), table_name="calls")
    op.drop_index(op.f("ix_calls_doctor_id"), table_name="calls")
    op.drop_index(op.f("ix_calls_patient_id"), table_name="calls")
    op.drop_index(op.f("ix_calls_room_id"), table_name="calls")
    op.drop_table("calls")

    op.drop_table("rooms")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    op.execute(sa.text("DROP TYPE IF EXISTS callstatus"))
    op.execute(sa.text("DROP TYPE IF EXISTS userrole"))
