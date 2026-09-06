"""Tests for featuregraph.storage.postgres.

The schema-building and row-preparation logic is tested directly (no
database needed). The read/write round trip additionally needs a reachable
Postgres: set DATABASE_URL to run it, otherwise it is skipped.
"""

import os

import pandas as pd
import pytest

psycopg = pytest.importorskip("psycopg")

from featuregraph.storage import postgres as fg_postgres  # noqa: E402


def test_connect_requires_a_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        fg_postgres.connect()


def test_create_table_rejects_an_empty_schema() -> None:
    with pytest.raises(ValueError, match="at least one column"):
        fg_postgres.create_table(object(), "objects", {})


def test_insert_rows_is_a_no_op_for_an_empty_frame() -> None:
    # No connection is touched, so a live database is not required here.
    fg_postgres.insert_rows(object(), "objects", pd.DataFrame(columns=["a"]))


@pytest.fixture
def live_connection():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        pytest.skip("DATABASE_URL is not set; skipping the live Postgres round trip.")
    try:
        conn = psycopg.connect(dsn, connect_timeout=3)
    except psycopg.OperationalError as error:
        pytest.skip(f"Postgres is not reachable at DATABASE_URL: {error}")
    yield conn
    conn.close()


def test_create_table_then_insert_and_read_round_trips(live_connection) -> None:
    table_name = "featuregraph_storage_test_objects"
    frame = pd.DataFrame(
        {
            "object_id": ["a-O000", "a-O001"],
            "duration": [1.5, float("nan")],
            "sample_count": [3, 7],
        }
    )

    fg_postgres.create_table(
        live_connection,
        table_name,
        {
            "object_id": "TEXT PRIMARY KEY",
            "duration": "DOUBLE PRECISION",
            "sample_count": "BIGINT NOT NULL",
        },
        if_exists="replace",
    )
    fg_postgres.insert_rows(live_connection, table_name, frame)
    result = fg_postgres.read_table(live_connection, table_name).sort_values(
        "object_id"
    ).reset_index(drop=True)

    assert result["object_id"].tolist() == ["a-O000", "a-O001"]
    assert result["sample_count"].tolist() == [3, 7]
    assert result["duration"].iloc[0] == 1.5
    assert pd.isna(result["duration"].iloc[1])


def test_create_table_if_exists_skip_leaves_existing_data(live_connection) -> None:
    table_name = "featuregraph_storage_test_skip"
    fg_postgres.create_table(
        live_connection,
        table_name,
        {"object_id": "TEXT PRIMARY KEY"},
        if_exists="replace",
    )
    fg_postgres.insert_rows(
        live_connection, table_name, pd.DataFrame({"object_id": ["kept"]})
    )

    fg_postgres.create_table(
        live_connection,
        table_name,
        {"object_id": "TEXT PRIMARY KEY"},
        if_exists="skip",
    )

    result = fg_postgres.read_table(live_connection, table_name)
    assert result["object_id"].tolist() == ["kept"]


def test_create_table_if_exists_fail_raises(live_connection) -> None:
    table_name = "featuregraph_storage_test_fail"
    fg_postgres.create_table(
        live_connection,
        table_name,
        {"object_id": "TEXT PRIMARY KEY"},
        if_exists="replace",
    )

    with pytest.raises(ValueError, match="already exists"):
        fg_postgres.create_table(
            live_connection,
            table_name,
            {"object_id": "TEXT PRIMARY KEY"},
        )


def test_create_table_accepts_a_table_level_constraint(live_connection) -> None:
    table_name = "featuregraph_storage_test_composite_key"
    fg_postgres.create_table(
        live_connection,
        table_name,
        {"group_id": "BIGINT NOT NULL", "object_id": "BIGINT NOT NULL"},
        constraints=["PRIMARY KEY (group_id, object_id)"],
        if_exists="replace",
    )
    fg_postgres.insert_rows(
        live_connection,
        table_name,
        pd.DataFrame({"group_id": [1, 1, 2], "object_id": [1, 2, 1]}),
    )

    with pytest.raises(psycopg.errors.UniqueViolation):
        with live_connection.cursor() as cursor:
            cursor.execute(f"INSERT INTO {table_name} VALUES (1, 1)")
    live_connection.rollback()

    result = fg_postgres.read_table(live_connection, table_name)
    assert len(result) == 3
