#!/usr/bin/env python
"""Validate that all NOT NULL columns with Python defaults also declare server_default.

Introspects SQLAlchemy models via Base.metadata. For each NOT NULL column that
has a Python-side ``default`` (not a FK, not a PK), checks that the model also
declares ``server_default``. Exits non-zero if any are missing.

Usage:
    python scripts/validate_server_defaults.py
"""

import sys
from pathlib import Path

# Ensure the backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import DateTime  # noqa: E402

from app.database import Base  # noqa: E402

# Import all models so they register with Base.metadata
from app.models import (  # noqa: E402, F401
    Channel,
    Message,
    Node,
    Source,
    User,
)


def validate() -> list[str]:
    """Return a list of error messages for columns missing server_default."""
    errors: list[str] = []

    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            # Skip primary keys — always explicitly provided
            if column.primary_key:
                continue

            # Skip foreign keys — always explicitly provided
            if column.foreign_keys:
                continue

            # Skip nullable columns — NULL is the implicit server default
            if column.nullable:
                continue

            # Skip DateTime columns — timestamps use callable defaults (utc_now)
            # and are always explicitly provided in both ORM and raw SQL
            if isinstance(column.type, DateTime):
                continue

            # Only check columns that have a Python-side default
            if column.default is None:
                continue

            # Column has a Python default but no server_default
            if column.server_default is None:
                errors.append(
                    f"  {table.name}.{column.name}: "
                    f"has default= but missing server_default="
                )

    return errors


def main() -> None:
    errors = validate()
    if errors:
        print("ERROR: The following columns have Python defaults but no server_default:")
        print()
        for err in errors:
            print(err)
        print()
        print(
            "Add server_default= to these mapped_column() calls and create "
            "a migration with ALTER TABLE ... SET DEFAULT."
        )
        sys.exit(1)
    else:
        print("OK: All NOT NULL columns with Python defaults have server_default declarations.")


if __name__ == "__main__":
    main()
