"""SQLite storage. Every change to a dataset becomes a new version with a changelog."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
FILTER_OPS = {"eq": "=", "ne": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "contains": "LIKE"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    name TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    created_at TEXT,
    updated_at TEXT,
    latest_version INTEGER,
    descriptions TEXT
);
CREATE TABLE IF NOT EXISTS versions (
    name TEXT,
    version INTEGER,
    created_at TEXT,
    row_count INTEGER,
    columns TEXT,
    data_hash TEXT,
    changes TEXT,
    cleaning TEXT,
    PRIMARY KEY (name, version)
);
"""


class NotFound(Exception):
    pass


def db_path() -> str:
    return os.environ.get("RINSE_DB", "rinse.db")


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    con = sqlite3.connect(path or db_path(), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def quote(ident: str) -> str:
    return '"' + ident.replace('"', '""') + '"'


def table_name(name: str, version: int) -> str:
    return f"data__{name}__v{version}"


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    if not s or not s[0].isalpha():
        s = "ds_" + s
    return s[:63]


def check_name(name: str) -> None:
    if not NAME_RE.match(name):
        raise ValueError("dataset name must be lowercase letters, digits and _ (start with a letter)")


def read_table(con: sqlite3.Connection, table: str) -> pd.DataFrame:
    return pd.read_sql_query(f"SELECT * FROM {quote(table)}", con)


def _row_hashes(df: pd.DataFrame, cols: List[str]) -> Counter:
    if not cols or df.empty:
        return Counter()
    norm = df[cols].astype(object).where(pd.notna(df[cols]), None).astype(str)
    return Counter(pd.util.hash_pandas_object(norm, index=False).tolist())


def latest_version(con: sqlite3.Connection, name: str) -> Optional[int]:
    row = con.execute("SELECT latest_version FROM datasets WHERE name=?", (name,)).fetchone()
    return row["latest_version"] if row else None


def save_version(
    con: sqlite3.Connection, name: str, source: str, df: pd.DataFrame, cleaning: Dict[str, Any]
) -> Tuple[int, Optional[Dict[str, Any]]]:
    """Store df as a new version. Returns (version, changes); changes is None if nothing changed."""
    check_name(name)
    prev = latest_version(con, name)
    version = (prev or 0) + 1
    table = table_name(name, version)
    df.to_sql(table, con, index=False, if_exists="replace")
    new = read_table(con, table)
    cols = list(new.columns)
    new_hashes = _row_hashes(new, cols)
    digest = hashlib.sha256(
        (json.dumps(cols) + json.dumps(sorted(new_hashes.elements()))).encode()
    ).hexdigest()

    if prev:
        old_meta = con.execute(
            "SELECT data_hash, columns FROM versions WHERE name=? AND version=?", (name, prev)
        ).fetchone()
        if old_meta and old_meta["data_hash"] == digest:
            con.execute(f"DROP TABLE {quote(table)}")
            con.execute("UPDATE datasets SET updated_at=? WHERE name=?", (now(), name))
            con.commit()
            return prev, None
        old = read_table(con, table_name(name, prev))
        old_cols = list(old.columns)
        common = [c for c in cols if c in old_cols]
        old_h, new_h = _row_hashes(old, common), _row_hashes(new, common)
        changes = {
            "from_version": prev,
            "rows_added": sum((new_h - old_h).values()),
            "rows_removed": sum((old_h - new_h).values()),
            "columns_added": [c for c in cols if c not in old_cols],
            "columns_removed": [c for c in old_cols if c not in cols],
            "row_count": len(new),
        }
        parts = [plural(changes["rows_added"], "row") + " added", plural(changes["rows_removed"], "row") + " removed"]
        if changes["columns_added"]:
            parts.append("new columns: " + ", ".join(changes["columns_added"]))
        if changes["columns_removed"]:
            parts.append("removed columns: " + ", ".join(changes["columns_removed"]))
        changes["summary"] = "; ".join(parts)
    else:
        changes = {"summary": f"initial import ({plural(len(new), 'row')})", "rows_added": len(new),
                   "rows_removed": 0, "row_count": len(new)}

    ts = now()
    con.execute(
        "INSERT INTO versions VALUES (?,?,?,?,?,?,?,?)",
        (name, version, ts, len(new), json.dumps(cols), digest, json.dumps(changes), json.dumps(cleaning)),
    )
    if prev:
        con.execute("UPDATE datasets SET source=?, updated_at=?, latest_version=? WHERE name=?",
                    (source, ts, version, name))
    else:
        con.execute("INSERT INTO datasets VALUES (?,?,?,?,?,?)", (name, source, ts, ts, version, "{}"))
    con.commit()
    return version, changes


def set_descriptions(con: sqlite3.Connection, name: str, descriptions: Dict[str, str]) -> None:
    con.execute("UPDATE datasets SET descriptions=? WHERE name=?", (json.dumps(descriptions), name))
    con.commit()


def list_datasets(con: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = con.execute(
        "SELECT d.name, d.source, d.updated_at, d.latest_version, v.row_count FROM datasets d "
        "JOIN versions v ON v.name=d.name AND v.version=d.latest_version ORDER BY d.name"
    ).fetchall()
    return [dict(r) for r in rows]


def get_dataset(con: sqlite3.Connection, name: str) -> Dict[str, Any]:
    row = con.execute("SELECT * FROM datasets WHERE name=?", (name,)).fetchone()
    if not row:
        raise NotFound(name)
    meta = dict(row)
    meta["descriptions"] = json.loads(meta.get("descriptions") or "{}")
    v = con.execute("SELECT * FROM versions WHERE name=? AND version=?",
                    (name, meta["latest_version"])).fetchone()
    cleaning = json.loads(v["cleaning"])
    kinds = cleaning.get("kinds", {})
    meta["row_count"] = v["row_count"]
    meta["columns"] = [
        {"name": c, "kind": kinds.get(c, "text"), "description": meta["descriptions"].get(c)}
        for c in json.loads(v["columns"])
    ]
    meta["cleaning"] = cleaning
    return meta


def get_versions(con: sqlite3.Connection, name: str) -> List[Dict[str, Any]]:
    rows = con.execute(
        "SELECT version, created_at, row_count, changes FROM versions WHERE name=? ORDER BY version DESC",
        (name,),
    ).fetchall()
    if not rows:
        raise NotFound(name)
    return [{**{k: r[k] for k in ("version", "created_at", "row_count")},
             "changes": json.loads(r["changes"])} for r in rows]


def parse_filters(params: Dict[str, str]) -> List[Tuple[str, str, str]]:
    out = []
    for key, value in params.items():
        col, _, op = key.partition("__")
        out.append((col, op or "eq", value))
    return out


def read_rows(
    con: sqlite3.Connection,
    name: str,
    version: Optional[int] = None,
    filters: Optional[List[Tuple[str, str, str]]] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    latest = latest_version(con, name)
    if latest is None:
        raise NotFound(name)
    version = version or latest
    exists = con.execute("SELECT 1 FROM versions WHERE name=? AND version=?", (name, version)).fetchone()
    if not exists:
        raise NotFound(f"{name} v{version}")
    table = quote(table_name(name, version))
    columns = [r["name"] for r in con.execute(f"PRAGMA table_info({table})")]
    where, params = [], []
    for col, op, value in filters or []:
        if col not in columns:
            raise ValueError(f"unknown column '{col}'. Columns: {', '.join(columns)}")
        if op not in FILTER_OPS:
            raise ValueError(f"unknown filter '{op}'. Use one of: {', '.join(FILTER_OPS)}")
        if op == "contains":
            where.append(f"{quote(col)} LIKE ? COLLATE NOCASE")
            params.append(f"%{value}%")
        elif op == "eq":
            where.append(f"({quote(col)} = ? OR LOWER({quote(col)}) = LOWER(?))")
            params.extend([value, value])
        else:
            where.append(f"{quote(col)} {FILTER_OPS[op]} ?")
            params.append(value)
    clause = (" WHERE " + " AND ".join(where)) if where else ""
    total = con.execute(f"SELECT COUNT(*) FROM {table}{clause}", params).fetchone()[0]
    rows = con.execute(f"SELECT * FROM {table}{clause} LIMIT ? OFFSET ?", params + [limit, offset]).fetchall()
    return {"dataset": name, "version": version, "total": total, "limit": limit, "offset": offset,
            "rows": [dict(r) for r in rows]}
