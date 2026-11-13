import sqlite3

import pytest

from iav_annotator.db import Store


def test_unrelated_sqlite_file_is_rejected_without_initializing_app_tables(tmp_path):
    path = tmp_path / "unrelated.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE other_project(value TEXT)")
    with pytest.raises(ValueError, match="annotation database"):
        Store(path)
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == [("other_project",)]
