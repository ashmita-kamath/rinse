"""Tiny Python client for an Rinse server (standard library only).

    from rinse.client import Rinse
    api = Rinse("http://127.0.0.1:8000")
    api.rows("school_data", district="Mysuru", enrolment__gte=500)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


class RinseError(Exception):
    pass


class Rinse:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        try:
            with urllib.request.urlopen(url, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RinseError(f"{exc.code}: {detail}") from exc

    def datasets(self) -> List[Dict[str, Any]]:
        return self._get("/datasets")

    def dataset(self, name: str) -> Dict[str, Any]:
        return self._get(f"/datasets/{name}")

    def versions(self, name: str) -> List[Dict[str, Any]]:
        return self._get(f"/datasets/{name}/versions")

    def rows(self, name: str, limit: int = 100, offset: int = 0,
             version: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        params = {"limit": limit, "offset": offset, "version": version, **filters}
        return self._get(f"/datasets/{name}/rows", params)["rows"]

    def all_rows(self, name: str, version: Optional[int] = None, **filters: Any) -> List[Dict[str, Any]]:
        out, offset = [], 0
        while True:
            page = self.rows(name, limit=1000, offset=offset, version=version, **filters)
            out.extend(page)
            if len(page) < 1000:
                return out
            offset += 1000

    def to_dataframe(self, name: str, **filters: Any):
        import pandas as pd
        return pd.DataFrame(self.all_rows(name, **filters))
