"""A minimal Postgres connector: define a table's schema, then write rows to it.

Schema is explicit and caller-defined — this module does not infer column
types from a DataFrame. You declare each column's type (and any constraints)
once with :func:`create_table`, then write DataFrame rows into it with
:func:`insert_rows`. Requires the ``postgres`` extra::

    pip install "featuregraph[postgres]"

Example::

    from featuregraph.storage import postgres as fg_postgres

    conn = fg_postgres.connect()  # reads DATABASE_URL
    fg_postgres.create_table(
        conn,
        "clap_objects",
        {
            "object_id": "TEXT PRIMARY KEY",
            "object_type": "TEXT NOT NULL",
            "start_index": "BIGINT NOT NULL",
            "end_index": "BIGINT NOT NULL",
            "duration": "DOUBLE PRECISION",
        },
    )
    fg_postgres.insert_rows(conn, "clap_objects", result.object_table())
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

import pandas as pd

try:
    import psycopg
    from psycopg import sql
except ImportError as error:  # pragma: no cover - exercised via ImportError path
    raise ImportError(
        "featuregraph.storage.postgres requires the 'postgres' extra: "
        'pip install "featuregraph[postgres]"'
    ) from error


def connect(dsn: str | None = None) -> psycopg.Connection:
    """Open a connection, reading ``DATABASE_URL`` when ``dsn`` is not given."""
    resolved = dsn or os.environ.get("DATABASE_URL")
    if not resolved:
        raise ValueError(
            "A connection string is required: pass dsn= or set DATABASE_URL."
        )
    return psycopg.connect(resolved)


def create_table(
    conn: psycopg.Connection,
    table_name: str,
    columns: Mapping[str, str],
    *,
    if_exists: Literal["fail", "skip", "replace"] = "fail",
) -> None:
    """Create a table from an explicit, caller-defined schema.

    ``columns`` maps each column name to its Postgres type and any
    constraints, verbatim — for example ``{"object_id": "TEXT PRIMARY KEY",
    "duration": "DOUBLE PRECISION NOT NULL"}``. This module never infers a
    schema from data; you declare it once here.

    ``if_exists`` controls what happens when the table already exists:
    ``"fail"`` (the default) raises, ``"skip"`` leaves the existing table
    untouched, and ``"replace"`` drops and recreates it.
    """
    if not columns:
        raise ValueError("columns must define at least one column.")
    identifier = sql.Identifier(table_name)

    with conn.cursor() as cursor:
        cursor.execute("SELECT to_regclass(%s) IS NOT NULL", (table_name,))
        (exists,) = cursor.fetchone()

        if exists:
            if if_exists == "fail":
                raise ValueError(f"Table {table_name!r} already exists.")
            if if_exists == "skip":
                return
            cursor.execute(sql.SQL("DROP TABLE {}").format(identifier))

        column_definitions = sql.SQL(", ").join(
            sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(definition))
            for name, definition in columns.items()
        )
        cursor.execute(
            sql.SQL("CREATE TABLE {} ({})").format(identifier, column_definitions)
        )

    conn.commit()


def insert_rows(
    conn: psycopg.Connection,
    table_name: str,
    frame: pd.DataFrame,
) -> None:
    """Insert a DataFrame's rows into a table already created by :func:`create_table`.

    Every column in ``frame`` must already exist in the table; this function
    does not alter the schema. ``NaN``/``NaT`` values are written as SQL
    ``NULL``.
    """
    if frame.empty:
        return

    columns = list(frame.columns)
    insert = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    rows = frame.astype(object).where(frame.notna(), None).itertuples(
        index=False, name=None
    )
    with conn.cursor() as cursor:
        cursor.executemany(insert, list(rows))
    conn.commit()


def read_table(conn: psycopg.Connection, table_name: str) -> pd.DataFrame:
    """Read a table back as a DataFrame, for verification and inspection."""
    with conn.cursor() as cursor:
        cursor.execute(sql.SQL("SELECT * FROM {}").format(sql.Identifier(table_name)))
        columns = [column.name for column in cursor.description]
        rows = cursor.fetchall()
    return pd.DataFrame(rows, columns=columns)
