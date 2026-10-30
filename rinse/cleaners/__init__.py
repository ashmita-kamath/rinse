"""Cleaning pipeline: headers -> nulls -> junk rows -> places -> dates -> numbers."""
from __future__ import annotations

import re
from typing import Any, Dict, Tuple

import pandas as pd

from .dates import is_date_column, parse_date
from .headers import clean_headers
from .nulls import is_text, normalise_nulls
from .numbers import numeric_column
from .places import canonical_place, place_kind

TOTAL_RE = re.compile(r"^(grand\s+)?total\b", re.I)


def drop_junk_rows(df: pd.DataFrame, report: Dict[str, Any]) -> pd.DataFrame:
    before = len(df)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    if before - len(df):
        report["notes"].append(f"dropped {before - len(df)} empty rows")
    if len(df.columns):
        totals = pd.Series(False, index=df.index)
        for col in list(df.columns)[:2]:
            totals |= df[col].map(lambda v: isinstance(v, str) and bool(TOTAL_RE.match(v)))
        if totals.any():
            report["notes"].append(f"dropped {int(totals.sum())} 'Total' summary rows")
            df = df[~totals]
    return df.reset_index(drop=True)


def clean_dataframe(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    report: Dict[str, Any] = {"renamed": {}, "kinds": {}, "notes": []}
    df = df.copy()
    new_cols, renamed = clean_headers(list(df.columns))
    df.columns = new_cols
    report["renamed"] = renamed
    df = normalise_nulls(df)
    df = drop_junk_rows(df, report)

    for col in df.columns:
        series = df[col]
        if not is_text(series):
            report["kinds"][col] = "number" if pd.api.types.is_numeric_dtype(series) else "text"
            continue

        kind = place_kind(col)
        if kind:
            cleaned = series.map(lambda v, k=kind: canonical_place(v, k))
            changed = int((cleaned.fillna("") != series.fillna("")).sum())
            before_u, after_u = series.dropna().nunique(), cleaned.dropna().nunique()
            df[col] = cleaned
            report["kinds"][col] = kind
            if changed:
                report["notes"].append(
                    f"{col}: standardised {changed} {kind} names ({before_u} spellings -> {after_u} unique)"
                )
            continue

        if is_date_column(col, series):
            parsed = series.map(parse_date)
            unparsed = parsed.isna() & series.notna()
            df[col] = parsed.where(~unparsed, series)
            report["kinds"][col] = "date"
            msg = f"{col}: converted dates to YYYY-MM-DD"
            if unparsed.any():
                msg += f" ({int(unparsed.sum())} unreadable values kept as-is)"
            report["notes"].append(msg)
            continue

        result = numeric_column(col, series)
        if result is not None:
            df[col], tags = result
            report["kinds"][col] = "number"
            if tags:
                report["notes"].append(f"{col}: parsed numbers ({', '.join(sorted(tags))} handled)")
            continue

        report["kinds"][col] = "text"
    return df, report
