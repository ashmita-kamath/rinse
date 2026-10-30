"""The one-command flow: fetch -> clean -> store as a new version."""
from __future__ import annotations

from typing import Any, Dict, Optional

from . import store
from .cleaners import clean_dataframe
from .ingest import read_source


def add_dataset(source: str, name: Optional[str] = None, con=None) -> Dict[str, Any]:
    con = con or store.connect()
    if not name:
        stem = source.rstrip("/").split("/")[-1].split("?")[0].rsplit(".", 1)[0]
        name = store.slugify(stem or "dataset")
    store.check_name(name)
    raw, info = read_source(source)
    df, report = clean_dataframe(raw)
    if info.get("title_rows_skipped"):
        report["notes"].insert(0, f"skipped {info['title_rows_skipped']} title rows above the header")
    version, changes = store.save_version(con, name, source, df, report)
    return {"name": name, "version": version, "changed": changes is not None,
            "changes": changes, "cleaning": report, "rows": len(df), "format": info["format"],
            "frame": df}


def update_dataset(name: str, con=None) -> Dict[str, Any]:
    con = con or store.connect()
    meta = store.get_dataset(con, name)
    return add_dataset(meta["source"], name=name, con=con)
