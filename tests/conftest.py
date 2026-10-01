import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import db  # noqa: E402

# app.py volá db.init_db() při importu – v testech nechceme čekat na MySQL.
REAL_INIT_DB = db.init_db
db.init_db = lambda *args, **kwargs: None

import app as app_module  # noqa: E402
import geo  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_geo_cache():
    geo._cache.clear()
    yield
    geo._cache.clear()


@pytest.fixture
def logged(monkeypatch):
    """Zachytí všechny záznamy předané do db.log_visit a vypne externí geo API."""
    rows = []
    monkeypatch.setattr(db, "log_visit", rows.append)
    monkeypatch.setattr(geo, "_from_ip_api", lambda ip: None)
    return rows


@pytest.fixture
def real_init_db():
    return REAL_INIT_DB


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()
