import pytest
import os
from database import init_db, save_scan, get_scans

DB_NAME = "results.db"


@pytest.fixture(autouse=True)
def setup_db():
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    init_db()
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)


def test_init_db_creates_table():
    conn = __import__("sqlite3").connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'")
    assert cursor.fetchone() is not None
    conn.close()


def test_save_and_get_scans():
    save_scan("example.com", "abc123", "completed", '{"results": ["test"]}')
    scans = get_scans()
    assert len(scans) == 1
    assert scans[0]["domain"] == "example.com"
    assert scans[0]["task_id"] == "abc123"
    assert scans[0]["status"] == "completed"


def test_get_scans_returns_empty_when_no_scans():
    scans = get_scans()
    assert scans == []
