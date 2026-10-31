"""Load CSV / Excel / JSON from a URL or a local path into a raw DataFrame.

Government files often have title rows above the real header, so we find
the header row instead of trusting row 1.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import urllib.request
from pathlib import Path
from typing import List, Tuple

import pandas as pd

USER_AGENT = "Rinse/0.1 (+https://github.com/ashmita-kamath/rinse)"


def fetch_bytes(source: str) -> bytes:
    if re.match(r"^https?://", source, re.I):
        req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    return Path(source).expanduser().read_bytes()


def sniff(data: bytes, source: str) -> str:
    if data[:2] == b"PK":
        return "xlsx"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    head = data.lstrip()[:1]
    if head in (b"{", b"["):
        return "json"
    return "csv"


def decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return isinstance(v, str) and not v.strip()


def promote_header(grid: List[list]) -> Tuple[pd.DataFrame, int]:
    """Pick the first 'full' row in the top 20 as the header. Returns (df, title_rows_skipped)."""
    rows = [r for r in grid if not all(_empty(v) for v in r)]
    if not rows:
        return pd.DataFrame(), 0
    width = max(len(r) for r in rows)
    rows = [list(r) + [None] * (width - len(r)) for r in rows]
    counts = [sum(not _empty(v) for v in r) for r in rows[:20]]
    target = max(counts)
    need = max(1, math.ceil(0.8 * target))
    idx = next(i for i, c in enumerate(counts) if c >= need)
    header = []
    for i, v in enumerate(rows[idx]):
        header.append(f"column_{i + 1}" if _empty(v) else str(v).strip())
    body = rows[idx + 1:]
    df = pd.DataFrame(body, columns=header, dtype=object)
    return df, idx


def read_source(source: str) -> Tuple[pd.DataFrame, dict]:
    data = fetch_bytes(source)
    kind = sniff(data, source)
    info = {"format": kind, "bytes": len(data), "title_rows_skipped": 0}

    if kind == "json":
        obj = json.loads(decode(data))
        records = obj.get("records", obj.get("data", [])) if isinstance(obj, dict) else obj
        df = pd.DataFrame(records, dtype=object)
        if isinstance(obj, dict) and isinstance(obj.get("fields"), list):
            names = {f.get("id"): f.get("name") or f.get("id") for f in obj["fields"] if isinstance(f, dict)}
            df = df.rename(columns=names)
        return df, info

    if kind in ("xlsx", "xls"):
        with pd.ExcelFile(io.BytesIO(data)) as workbook:
            for sheet in workbook.sheet_names:
                raw = pd.read_excel(workbook, sheet_name=sheet, header=None, dtype=object)
                grid = raw.where(pd.notna(raw), None).values.tolist()
                df, skipped = promote_header(grid)
                if not df.empty:
                    info["title_rows_skipped"] = skipped
                    return df, info
        return pd.DataFrame(), info
    else:
        text = decode(data)
        try:
            dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        grid = list(csv.reader(io.StringIO(text), dialect))

    df, skipped = promote_header(grid)
    info["title_rows_skipped"] = skipped
    return df, info
