"""Optional: a local open-weight model (Qwen2.5 1.5B via Ollama) writes column docs.

Nothing leaves your machine. If Ollama is not running, Rinse works without it.
  ollama pull qwen2.5:1.5b
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Dict

import pandas as pd

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("RINSE_MODEL", "qwen2.5:1.5b")


class AIUnavailable(Exception):
    pass


def describe_columns(dataset: str, df: pd.DataFrame, timeout: int = 120) -> Dict[str, str]:
    sample = df.head(5).astype(object).where(pd.notna(df.head(5)), None).to_dict(orient="records")
    prompt = (
        "You write documentation for Indian government open datasets.\n"
        f"Dataset name: {dataset}\n"
        f"Columns: {list(df.columns)}\n"
        f"Sample rows: {json.dumps(sample, default=str)}\n"
        "Return ONLY a JSON object mapping every column name to one short, plain-English "
        "sentence describing what the column contains."
    )
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": "json"}).encode()
    req = urllib.request.Request(f"{OLLAMA_URL}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            answer = json.loads(resp.read().decode())["response"]
        parsed = json.loads(answer)
    except Exception as exc:
        raise AIUnavailable(f"could not reach {MODEL} at {OLLAMA_URL}: {exc}") from exc
    return {c: str(parsed[c])[:200] for c in df.columns if c in parsed and parsed[c]}
