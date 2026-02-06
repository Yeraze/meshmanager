"""Trim whitespace from mqtt_host and fix topic pattern.

Fixes MQTT connection failure caused by trailing whitespace in mqtt_host,
and adds wildcard suffix to mqtt_topic_pattern for proper subtopic matching.

Revision ID: f3g4h5i6j7k8
Revises: e2f3g4h5i6j7
Create Date: 2026-02-06
"""

from alembic import op


# revision identifiers
revision = "f3g4h5i6j7k8"
down_revision = "e2f3g4h5i6j7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Trim whitespace from mqtt_host for all sources
    op.execute("""
        UPDATE sources
        SET mqtt_host = TRIM(mqtt_host)
        WHERE mqtt_host IS NOT NULL
          AND mqtt_host != TRIM(mqtt_host)
    """)

    # Fix topic pattern: add wildcard suffix if missing
    op.execute("""
        UPDATE sources
        SET mqtt_topic_pattern = mqtt_topic_pattern || '/#'
        WHERE mqtt_topic_pattern IS NOT NULL
          AND mqtt_topic_pattern NOT LIKE '%/#'
          AND mqtt_topic_pattern NOT LIKE '%/#/'
          AND mqtt_topic_pattern NOT LIKE '%#'
    """)


def downgrade() -> None:
    # Cannot reliably restore original whitespace or remove added wildcards
    pass
