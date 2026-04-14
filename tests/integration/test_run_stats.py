import sqlite3
from datetime import datetime
import pytest
from storage.database import init_schema, start_run, finish_run


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    yield conn
    conn.close()


def test_start_run_inserts_row_with_running_status(db):
    start_run(db, run_id="r1", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    row = db.execute("SELECT * FROM run_stats WHERE run_id = 'r1'").fetchone()
    assert row is not None
    assert row["status"] == "running"
    assert row["platform"] == "trendyol"


def test_finish_run_updates_status_and_counts(db):
    start_run(db, run_id="r2", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    finish_run(
        db, run_id="r2",
        status="success",
        products_found=500, products_saved=498, products_failed=2,
        finished_at=datetime(2026, 4, 14, 3, 25),
        duration_seconds=1500,
        error_message=None,
    )
    row = db.execute("SELECT * FROM run_stats WHERE run_id = 'r2'").fetchone()
    assert row["status"] == "success"
    assert row["products_found"] == 500
    assert row["products_saved"] == 498
    assert row["products_failed"] == 2
    assert row["duration_seconds"] == 1500


def test_finish_run_records_error_message(db):
    start_run(db, run_id="r3", platform="trendyol", category="kozmetik",
              started_at=datetime(2026, 4, 14, 3, 0))
    finish_run(
        db, run_id="r3",
        status="failed",
        products_found=0, products_saved=0, products_failed=0,
        finished_at=datetime(2026, 4, 14, 3, 1),
        duration_seconds=60,
        error_message="Anti-bot tetiklendi",
    )
    row = db.execute("SELECT error_message FROM run_stats WHERE run_id = 'r3'").fetchone()
    assert row["error_message"] == "Anti-bot tetiklendi"
