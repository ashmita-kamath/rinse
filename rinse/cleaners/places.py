"""Standardise Indian district and state names.

Spellings come from rule files in rinse/rules/ (alias,canonical).
Optionally, point RINSE_LGD at an LGD district export CSV and unknown
names are fuzzy-matched against the official list.
"""
from __future__ import annotations

import csv
import difflib
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"
SMALL_WORDS = {"and", "of", "the"}
SUFFIX_RE = re.compile(r"\s*\b(district|dist\.?|zilla|jilla)$", re.I)
CODE_HINTS = {"code", "id", "no", "lgd", "census"}


def norm_key(value: str) -> str:
    s = value.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def smart_title(value: str) -> str:
    words = value.split(" ")
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if i > 0 and lw in SMALL_WORDS:
            out.append(lw)
        elif w.isupper() or w.islower():
            out.append(w[:1].upper() + w[1:].lower())
        else:
            out.append(w)
    return " ".join(out)


@lru_cache(maxsize=None)
def load_aliases(filename: str) -> Dict[str, str]:
    path = RULES_DIR / filename
    aliases: Dict[str, str] = {}
    if not path.exists():
        return aliases
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            alias = (row.get("alias") or "").strip()
            canonical = (row.get("canonical") or "").strip()
            if alias and canonical:
                aliases[norm_key(alias)] = canonical
                aliases[norm_key(canonical)] = canonical
    return aliases


@lru_cache(maxsize=None)
def load_lgd_districts(path: Optional[str]) -> Dict[str, str]:
    """Read an LGD district export and return normalised-name -> official name."""
    if not path or not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        col = None
        for name in fields:
            low = name.lower()
            if "district" in low and "name" in low and "local" not in low:
                col = name
                break
        if col is None:
            return {}
        out = {}
        for row in reader:
            official = (row.get(col) or "").strip()
            if official:
                out[norm_key(official)] = smart_title(official)
        return out


def canonical_place(value, kind: str = "district"):
    if value is None:
        return None
    s = " ".join(str(value).replace("\xa0", " ").split())
    if not s:
        return None
    if kind == "district":
        stripped = SUFFIX_RE.sub("", s).strip()
        if stripped:
            s = stripped
    key = norm_key(s)
    aliases = load_aliases(f"{kind}_aliases.csv")
    if key in aliases:
        return aliases[key]
    if kind == "district":
        lgd = load_lgd_districts(os.environ.get("RINSE_LGD"))
        if lgd:
            if key in lgd:
                return lgd[key]
            match = difflib.get_close_matches(key, list(lgd.keys()), n=1, cutoff=0.9)
            if match:
                return lgd[match[0]]
    return smart_title(s)


def place_kind(column: str) -> Optional[str]:
    """Guess if a snake_case column holds districts or states."""
    tokens: List[str] = column.split("_")
    if any(t in CODE_HINTS for t in tokens):
        return None
    if "district" in tokens or "districts" in tokens or column in {"dist", "dist_name"}:
        return "district"
    if "state" in tokens or "states" in tokens or column in {"state_ut", "states_uts"}:
        return "state"
    return None
