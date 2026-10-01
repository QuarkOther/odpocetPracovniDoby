import json
import os

import pymysql
import pytest

import db


class FakeCursor:
    def __init__(self, executed):
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))


class FakeConn:
    def __init__(self):
        self.executed = []
        self.closed = False

    def cursor(self):
        return FakeCursor(self.executed)

    def close(self):
        self.closed = True


def test_log_visit_serializes_headers(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(db, "get_connection", lambda: conn)
    data = {"visitor_id": "v", "raw_headers": {"User-Agent": "ž"}}
    db.log_visit(data)
    sql, params = conn.executed[0]
    assert sql == db.INSERT_SQL
    assert json.loads(params["raw_headers"]) == {"User-Agent": "ž"}
    assert data["raw_headers"] == {"User-Agent": "ž"}  # vstup se nemění
    assert conn.closed


def test_log_visit_truncates_long_strings(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(db, "get_connection", lambda: conn)
    db.log_visit({"user_agent": "x" * 1000, "path": "/", "is_bot": True})
    params = conn.executed[0][1]
    assert len(params["user_agent"]) == 512
    assert params["path"] == "/"
    assert params["is_bot"] is True
    assert db._COLUMN_MAX_LENGTHS["visitor_id"] == 36
    assert db._COLUMN_MAX_LENGTHS["query_string"] == 1024


def test_log_visit_swallows_errors(monkeypatch, capsys):
    def fail():
        raise pymysql.OperationalError(2003, "Can't connect")

    monkeypatch.setattr(db, "get_connection", fail)
    db.log_visit({"raw_headers": None})
    assert "Nepodařilo se zalogovat" in capsys.readouterr().out


def test_init_db_retries_then_gives_up(monkeypatch, capsys, real_init_db):
    attempts = []

    def fail():
        attempts.append(1)
        raise pymysql.OperationalError(2003, "Can't connect")

    monkeypatch.setattr(db, "get_connection", fail)
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    real_init_db(retries=3, delay=0)
    assert len(attempts) == 3
    assert "Nepodařilo se inicializovat" in capsys.readouterr().out


# --- Integrační testy proti skutečné MySQL -----------------------------------
# Spuštění: MYSQL_TEST_HOST=127.0.0.1 MYSQL_TEST_PORT=33306 MYSQL_PASSWORD=... pytest

needs_mysql = pytest.mark.skipif(
    not os.environ.get("MYSQL_TEST_HOST"), reason="MYSQL_TEST_HOST není nastaven"
)


@pytest.fixture
def mysql(monkeypatch, real_init_db):
    monkeypatch.setattr(db, "MYSQL_HOST", os.environ["MYSQL_TEST_HOST"])
    monkeypatch.setattr(db, "MYSQL_PORT", int(os.environ.get("MYSQL_TEST_PORT", "3306")))
    real_init_db(retries=20, delay=3)
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE visits")
    yield conn
    conn.close()


def _fetch_all(conn):
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute("SELECT * FROM visits ORDER BY id")
        return cur.fetchall()


@needs_mysql
def test_mysql_request_is_stored(mysql, client, monkeypatch):
    import geo
    from test_app import CHROME_UA

    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: None)
    client.get("/?a=b", headers={
        "User-Agent": CHROME_UA,
        "CF-Connecting-IP": "1.2.3.4",
        "CF-IPCountry": "CZ",
        "CF-IPCity": "Ostrava",
        "CF-IPLatitude": "49.8209",
        "CF-IPLongitude": "18.2625",
    })
    rows = _fetch_all(mysql)
    assert len(rows) == 1
    row = rows[0]
    assert row["ip_address"] == "1.2.3.4"
    assert row["path"] == "/"
    assert row["query_string"] == "a=b"
    assert row["browser_name"] == "Chrome"
    assert row["device_type"] == "pc"
    assert row["is_bot"] == 0
    assert row["country_code"] == "CZ"
    assert row["city"] == "Ostrava"
    assert float(row["latitude"]) == pytest.approx(49.8209)
    assert row["response_status_code"] == 200
    assert row["visited_at"] is not None
    assert json.loads(row["raw_headers"])["Cf-Connecting-Ip"] == "1.2.3.4"


@needs_mysql
def test_mysql_long_values_are_stored(mysql, client, monkeypatch):
    """Dlouhý User-Agent / Referer / path nesmí způsobit ztrátu celého záznamu."""
    import geo

    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: None)
    long_ua = "Mozilla/5.0 " + "X" * 1000
    client.get("/" + "a" * 300, headers={"User-Agent": long_ua, "Referer": "https://e.org/" + "r" * 600})
    client.set_cookie("visitor_id", "v" * 500)
    client.get("/", headers={"User-Agent": long_ua})
    rows = _fetch_all(mysql)
    assert len(rows) == 2
    assert rows[0]["user_agent"].startswith("Mozilla/5.0 X")
    assert len(rows[0]["user_agent"]) == 512
    assert len(rows[0]["path"]) == 255
    assert len(rows[1]["visitor_id"]) == 36
