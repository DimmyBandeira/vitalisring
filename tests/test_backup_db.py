import sqlite3

import pytest

from scripts.backup_db import backup_database


def test_backup_is_consistent_and_never_overwrites(tmp_path):
    source, destination = tmp_path / "source.sqlite", tmp_path / "backup.sqlite"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE sample (value TEXT)")
        db.execute("INSERT INTO sample VALUES ('preserved')")
        db.commit()
    assert backup_database(source, destination) == destination.resolve()
    with sqlite3.connect(destination) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "preserved"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with pytest.raises(FileExistsError):
        backup_database(source, destination)
