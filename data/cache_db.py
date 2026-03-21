from __future__ import annotations

"""
SQLite cache registry.
Tracks all downloaded NetCDF files to avoid redundant downloads.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from loguru import logger


def initialize_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache_registry (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            source        TEXT    NOT NULL,
            dataset_id    TEXT    NOT NULL,
            variables     TEXT    NOT NULL,
            bbox_hash     TEXT    NOT NULL,
            start_date    TEXT    NOT NULL,
            end_date      TEXT    NOT NULL,
            min_depth     REAL,
            max_depth     REAL,
            file_path     TEXT    NOT NULL UNIQUE,
            file_size_mb  REAL,
            downloaded_at TEXT    NOT NULL,
            is_valid      INTEGER DEFAULT 1
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON cache_registry (source, dataset_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bbox   ON cache_registry (bbox_hash, start_date, end_date)")
    conn.commit()
    conn.close()
    logger.info(f"Cache DB initialized at {db_path}")


def _bbox_hash(bbox: dict) -> str:
    return hashlib.sha1(json.dumps(bbox, sort_keys=True).encode()).hexdigest()[:12]


def register_file(
    db_path: Path,
    source: str,
    dataset_id: str,
    variables: list,
    bbox: dict,
    start_date: str,
    end_date: str,
    min_depth: float,
    max_depth: float,
    file_path: Path,
) -> None:
    size_mb = file_path.stat().st_size / 1_048_576 if file_path.exists() else 0.0
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        INSERT OR REPLACE INTO cache_registry
        (source, dataset_id, variables, bbox_hash, start_date, end_date,
         min_depth, max_depth, file_path, file_size_mb, downloaded_at, is_valid)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,1)
    """, (
        source, dataset_id, json.dumps(sorted(variables)),
        _bbox_hash(bbox), start_date, end_date,
        min_depth, max_depth, str(file_path), size_mb,
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()
    logger.info(f"Registered cache entry: {file_path.name} ({size_mb:.1f} MB)")


def find_cached_file(
    db_path: Path,
    source: str,
    dataset_id: str,
    variables: list,
    bbox: dict,
    start_date: str,
    end_date: str,
    min_depth: float,
    max_depth: float,
    ttl_seconds: int = 604800,
) -> Path | None:
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("""
        SELECT file_path, downloaded_at FROM cache_registry
        WHERE source=? AND dataset_id=? AND variables=?
          AND bbox_hash=? AND start_date=? AND end_date=?
          AND min_depth=? AND max_depth=? AND is_valid=1
        ORDER BY downloaded_at DESC LIMIT 1
    """, (
        source, dataset_id, json.dumps(sorted(variables)),
        _bbox_hash(bbox), start_date, end_date, min_depth, max_depth,
    )).fetchone()
    conn.close()

    if row is None:
        return None

    file_path, downloaded_at = Path(row[0]), row[1]
    if not file_path.exists():
        return None

    age = (datetime.utcnow() - datetime.fromisoformat(downloaded_at)).total_seconds()
    if age > ttl_seconds:
        logger.info(f"Cache expired for {file_path.name} (age={age/3600:.1f}h)")
        return None

    return file_path


def list_all_cached(db_path: Path) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT source, dataset_id, variables, start_date, end_date,
               file_size_mb, downloaded_at, file_path
        FROM cache_registry WHERE is_valid=1
        ORDER BY downloaded_at DESC
    """).fetchall()
    conn.close()
    return [
        {
            "source": r[0], "dataset_id": r[1], "variables": json.loads(r[2]),
            "start_date": r[3], "end_date": r[4], "size_mb": r[5],
            "downloaded_at": r[6], "file_path": r[7],
        }
        for r in rows
    ]


def delete_cached_dataset(db_path: Path, source: str, dataset_id: str) -> dict:
    """Delete all cached files for a dataset and invalidate registry rows."""
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT file_path, file_size_mb
        FROM cache_registry
        WHERE source=? AND dataset_id=? AND is_valid=1
    """, (source, dataset_id)).fetchall()

    deleted_files = 0
    freed_mb = 0.0
    for file_path_str, file_size_mb in rows:
        file_path = Path(file_path_str)
        if file_path.exists():
            try:
                file_path.unlink()
                deleted_files += 1
                freed_mb += file_size_mb or 0.0
            except OSError as exc:
                logger.warning(f"Could not delete cached file {file_path}: {exc}")

    conn.execute("""
        UPDATE cache_registry
        SET is_valid=0
        WHERE source=? AND dataset_id=? AND is_valid=1
    """, (source, dataset_id))
    conn.commit()
    conn.close()

    logger.info(f"Deleted {deleted_files} cached files for {dataset_id} ({freed_mb:.1f} MB)")
    return {"deleted_files": deleted_files, "freed_mb": freed_mb}


def delete_cached_file(db_path: Path, file_path: str) -> dict:
    """Delete one cached file and invalidate its registry row."""
    conn = sqlite3.connect(str(db_path))
    row = conn.execute("""
        SELECT file_size_mb
        FROM cache_registry
        WHERE file_path=? AND is_valid=1
    """, (file_path,)).fetchone()

    if row is None:
        conn.close()
        return {"deleted": False, "freed_mb": 0.0}

    freed_mb = row[0] or 0.0
    path_obj = Path(file_path)
    deleted = False
    if path_obj.exists():
        try:
            path_obj.unlink()
            deleted = True
        except OSError as exc:
            logger.warning(f"Could not delete cached file {path_obj}: {exc}")

    conn.execute("""
        UPDATE cache_registry
        SET is_valid=0
        WHERE file_path=? AND is_valid=1
    """, (file_path,))
    conn.commit()
    conn.close()

    logger.info(f"Deleted cached file {file_path} ({freed_mb:.1f} MB)")
    return {"deleted": deleted, "freed_mb": freed_mb}
