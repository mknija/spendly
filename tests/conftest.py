import importlib
import sys

import pytest

import database.db as db_module


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test_spendly.db"))

    if "app" in sys.modules:
        app_module = importlib.reload(sys.modules["app"])
    else:
        app_module = importlib.import_module("app")

    app_module.app.config["TESTING"] = True
    yield app_module.app
