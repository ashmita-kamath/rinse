"""Parse Indian number formats: 1,23,456 / Rs. 500/- / 2.5 lakh / 3 crore / 45%."""
from __future__ import annotations

import math
import re
from typing import Optional, Set, Tuple

import pandas as pd

MULTIPLIERS = {
    "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "l": 1e5,
    "crore": 1e7, "crores": 1e7, "cr": 1e7,
    "thousand": 1e3, "k": 1e3, "million": 1e6, "mn": 1e6, "billion": 1e9,
}
CURRENCY_RE = re.compile(r"^(₹|rs\.?|inr)\s*", re.I)
NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")
WORD_RE = re.compile(r"^(.*?\d)\s*([a-z]+)\.?$", re.I)
CODE_HINTS = {"code", "id", "pin", "pincode", "phone", "mobile", "lgd", "census", "udise"}


def parse_number(value) -> Tuple[Optional[float], Set[str]]:
    """Return (number or None, set of unit tags seen)."""
    tags: Set[str] = set()
    if value is None or isinstance(value, bool):
        return None, tags
    if isinstance(value, (int, float)):
        return (None if math.isnan(float(value)) else float(value)), tags
    s = " ".join(str(value).split())
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1].strip()
    if s.endswith("/-"):
        s = s[:-2].strip()
        tags.add("INR")
    if CURRENCY_RE.match(s):
        s = CURRENCY_RE.sub("", s)
        tags.add("INR")
    if s.endswith("%"):
        s = s[:-1].strip()
        tags.add("%")
    factor = 1.0
    m = WORD_RE.match(s)
    if m and m.group(2).lower() in MULTIPLIERS:
        factor = MULTIPLIERS[m.group(2).lower()]
        tags.add(m.group(2).lower())
        s = m.group(1)
    s = s.replace(",", "").replace(" ", "")
    if not NUMBER_RE.match(s):
        return None, set()
    number = float(s) * factor
    return (-number if negative else number), tags


def is_code_column(column: str) -> bool:
    return any(t in CODE_HINTS for t in column.split("_"))


def numeric_column(column: str, series: pd.Series) -> Optional[Tuple[pd.Series, Set[str]]]:
    """If >=90% of values are numbers, return the converted column and unit tags."""
    if is_code_column(column):
        return None
    values = series.dropna()
    if values.empty:
        return None
    parsed = [parse_number(v) for v in series]
    good = sum(1 for (n, _), v in zip(parsed, series) if v is not None and n is not None)
    if good / len(values) < 0.9:
        return None
    nums = [n for n, _ in parsed]
    tags: Set[str] = set()
    for _, t in parsed:
        tags |= t
    real = [n for n in nums if n is not None]
    if real and all(float(n).is_integer() and abs(n) < 2 ** 53 for n in real):
        out = pd.Series([None if n is None else int(n) for n in nums], index=series.index, dtype="Int64")
    else:
        out = pd.Series([math.nan if n is None else n for n in nums], index=series.index, dtype="float64")
    return out, tags
