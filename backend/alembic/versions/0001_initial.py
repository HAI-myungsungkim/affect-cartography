"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("participant_code", sa.String(32), nullable=False, unique=True),
        sa.Column("real_name", sa.String(64), nullable=False),
        sa.Column("device_id_hash", sa.String(64), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("first_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notify_morning_start", sa.Time(), nullable=False, server_default="09:00:00"),
        sa.Column("notify_morning_end", sa.Time(), nullable=False, server_default="12:00:00"),
        sa.Column("notify_afternoon_start", sa.Time(), nullable=False, server_default="13:00:00"),
        sa.Column("notify_afternoon_end", sa.Time(), nullable=False, server_default="17:00:00"),
        sa.Column("notify_evening_start", sa.Time(), nullable=False, server_default="19:00:00"),
        sa.Column("notify_evening_end", sa.Time(), nullable=False, server_default="22:00:00"),
        sa.Column(
            "record_mode",
            sa.Enum("point", "trajectory", name="record_mode"),
            nullable=False, server_default="point",
        ),
        sa.Column("trajectory_practice_done", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("study_phase", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.Enum("active", "dropped", "completed", name="user_status"),
            nullable=False, server_default="active",
        ),
    )
    op.create_index("ix_users_participant_code", "users", ["participant_code"])
    op.create_index("ix_users_device_id_hash", "users", ["device_id_hash"])

    # affect_records
    op.create_table(
        "affect_records",
        sa.Column("record_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("valence", sa.Float(), nullable=False),
        sa.Column("arousal", sa.Float(), nullable=False),
        sa.Column("quadrant", sa.Enum("q1", "q2", "q3", "q4", name="quadrant"), nullable=False),
        sa.Column("mode", sa.Enum("point", "trajectory", name="affect_mode"),
                  nullable=False, server_default="point"),
        sa.Column("trajectory_points", postgresql.JSONB(), nullable=True),
        sa.Column("duration_window_minutes", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("is_practice", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("response_latency_ms", sa.Integer(), nullable=True),
        sa.Column("prompt_id", sa.String(64), nullable=True),
        sa.CheckConstraint("valence >= -1.0 AND valence <= 1.0", name="ck_valence_range"),
        sa.CheckConstraint("arousal >= -1.0 AND arousal <= 1.0", name="ck_arousal_range"),
    )
    op.create_index("ix_affect_user_time", "affect_records", ["user_id", "timestamp"])

    # emotion_records
    op.create_table(
        "emotion_records",
        sa.Column("emotion_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("affect_records.record_id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("selected_word", sa.String(32), nullable=False),
        sa.Column("intensity", sa.Integer(), nullable=False),
        sa.Column("exploration_path", postgresql.JSONB(), server_default="[]"),
        sa.Column("final_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("intensity BETWEEN 1 AND 5", name="ck_intensity_range"),
    )
    op.create_index("ix_emotion_word", "emotion_records", ["selected_word"])

    # emotion_dictionary
    op.create_table(
        "emotion_dictionary",
        sa.Column("word", sa.String(32), primary_key=True),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("valence", sa.Float(), nullable=False),
        sa.Column("arousal", sa.Float(), nullable=False),
        sa.Column("neighbors", postgresql.JSONB(), server_default="[]"),
        sa.Column("reviewed_by_researcher", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("source", sa.String(32), nullable=False, server_default="gpt-4o-draft"),
    )

    # agent_dialogues
    op.create_table(
        "agent_dialogues",
        sa.Column("dialogue_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("affect_records.record_id", ondelete="CASCADE"), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.Enum("user", "agent", name="speaker"), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_dialogue_record", "agent_dialogues", ["record_id", "turn_index"])

    # intervention_responses
    op.create_table(
        "intervention_responses",
        sa.Column("response_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("affect_records.record_id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "intervention_type",
            sa.Enum("self_distancing", "grounding", "activation", name="intervention_type"),
            nullable=False,
        ),
        sa.Column("user_response_text", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # safety_flags
    op.create_table(
        "safety_flags",
        sa.Column("flag_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("affect_records.record_id", ondelete="SET NULL"), nullable=True),
        sa.Column(
            "flag_type",
            sa.Enum("suicide_ideation", "self_harm", "severe_distress", "other", name="flag_type"),
            nullable=False,
        ),
        sa.Column("trigger_text", sa.Text(), nullable=True),
        sa.Column("matched_keywords", sa.String(256), nullable=True),
        sa.Column("raised_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_by", sa.String(64), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_safety_user", "safety_flags", ["user_id", "raised_at"])

    # admin_settings
    op.create_table(
        "admin_settings",
        sa.Column("setting_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("admin_settings")
    op.drop_table("safety_flags")
    op.drop_table("intervention_responses")
    op.drop_table("agent_dialogues")
    op.drop_table("emotion_dictionary")
    op.drop_table("emotion_records")
    op.drop_table("affect_records")
    op.drop_table("users")
    for enum in ["flag_type", "intervention_type", "speaker", "affect_mode",
                 "quadrant", "user_status", "record_mode"]:
        op.execute(f"DROP TYPE IF EXISTS {enum}")
