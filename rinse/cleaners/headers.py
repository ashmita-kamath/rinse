"""Turn messy column headers into clean snake_case API field names."""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


def to_snake(name: object) -> str:
    s = str(name).replace("\xa0", " ").strip().lower()
    s = s.replace("&", " and ").replace("%", " pct ").replace("#", " no ")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    if not s:
        s = "column"
    if s[0].isdigit():
        s = "c_" + s
    return s


def clean_headers(columns: List[object]) -> Tuple[List[str], Dict[str, str]]:
    """Return new column names (unique, snake_case) and an old->new map."""
    seen: Dict[str, int] = {}
    new_cols: List[str] = []
    renamed: Dict[str, str] = {}
    for col in columns:
        base = to_snake(col)
        n = seen.get(base, 0)
        seen[base] = n + 1
        name = base if n == 0 else f"{base}_{n + 1}"
        new_cols.append(name)
        if str(col) != name:
            renamed[str(col)] = name
    return new_cols, renamed
