"""Parse Indian-style dates (day first) into ISO 8601 (YYYY-MM-DD)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

import pandas as pd

FORMATS = [
    "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y",
    "%d-%m-%y", "%d/%m/%y", "%d.%m.%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d-%b-%Y", "%d %b %Y", "%d-%B-%Y", "%d %B %Y", "%d-%b-%y", "%d %b, %Y",
    "%b %d, %Y", "%B %d, %Y",
    "%b-%Y", "%B-%Y", "%b %Y", "%B %Y", "%b-%y",
]
NAME_HINT = re.compile(r"(date|dated|_dt$|^dt_|_on$|^as_of)")


def parse_date(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return None if pd.isna(value) else value.strftime("%Y-%m-%d")
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    s = " ".join(str(value).split())
    s = re.sub(r"[ T]00:00(:00)?$", "", s)
    for fmt in FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def is_date_column(column: str, series: pd.Series) -> bool:
    values = series.dropna()
    if values.empty:
        return False
    sample = values.head(300)
    if all(isinstance(v, (int, float)) for v in sample):
        return False
    ok = sum(parse_date(v) is not None for v in sample) / len(sample)
    if NAME_HINT.search(column):
        return ok >= 0.6
    return ok >= 0.9
