"""Cria backup consistente do SQLite sem sobrescrever arquivos existentes."""

import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def backup_database(source: Path, destination: Path) -> Path:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Banco não encontrado: {source}")
    if destination.exists():
        raise FileExistsError(f"Destino já existe: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as origin, sqlite3.connect(destination) as target:
        origin.backup(target)
        check = target.execute("PRAGMA integrity_check").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"Backup inválido: {check}")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=os.environ.get("DB_PATH", "ring_data.sqlite"))
    parser.add_argument("--destination")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = Path(args.destination or f"backups/ring_data-{stamp}.sqlite")
    print(backup_database(Path(args.source), destination))


if __name__ == "__main__":
    main()
