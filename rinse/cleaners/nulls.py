"""Normalise the many ways government files write 'no data'."""
from __future__ import annotations

import pandas as pd

NULL_TOKENS = {
    "", "na", "n.a.", "n.a", "n/a", "nan", "null", "none", "nil",
    "-", "--", "---", "...", "not available", "not applicable", "#n/a",
}


def is_text(series: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)


def clean_cell(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, str):
        s = " ".join(value.replace("\xa0", " ").split())
        if s.lower() in NULL_TOKENS:
            return None
        return s
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def normalise_nulls(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if is_text(df[col]):
            df[col] = df[col].astype(object).map(clean_cell)
    return df
