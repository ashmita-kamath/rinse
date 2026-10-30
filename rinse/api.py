"""REST API with auto-generated OpenAPI docs at /docs."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from . import __version__, store

RESERVED = {"limit", "offset", "version"}
STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Rinse",
    version=__version__,
    description=(
        "Clean, versioned APIs for Indian public datasets.\n\n"
        "**Filtering:** `/datasets/{name}/rows?district=Mysuru` for exact match (case-insensitive). "
        "Add `__gte`, `__lte`, `__gt`, `__lt`, `__ne` or `__contains` to a column name, "
        "e.g. `?amount__gte=100000` or `?district__contains=bengaluru`."
    ),
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _con():
    return store.connect()


@app.get("/", tags=["meta"])
def home():
    con = _con()
    return {"name": "Rinse", "version": __version__, "docs": "/docs", "ui": "/ui",
            "datasets": [d["name"] for d in store.list_datasets(con)]}


@app.get("/ui", include_in_schema=False)
def ui():
    return FileResponse(STATIC / "index.html")


@app.get("/ui/", include_in_schema=False)
def ui_slash():
    return RedirectResponse("/ui")


@app.get("/datasets", tags=["datasets"], summary="List all datasets")
def datasets():
    return store.list_datasets(_con())


@app.get("/datasets/{name}", tags=["datasets"], summary="Dataset info, columns and cleaning report")
def dataset(name: str):
    try:
        return store.get_dataset(_con(), name)
    except store.NotFound:
        raise HTTPException(404, f"dataset '{name}' not found")


@app.get("/datasets/{name}/rows", tags=["datasets"], summary="Query rows (filters as query params)")
def rows(
    name: str,
    request: Request,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    version: Optional[int] = Query(None, ge=1, description="Defaults to the latest version"),
):
    filters = store.parse_filters({k: v for k, v in request.query_params.items() if k not in RESERVED})
    try:
        return store.read_rows(_con(), name, version=version, filters=filters, limit=limit, offset=offset)
    except store.NotFound as exc:
        raise HTTPException(404, f"not found: {exc}")
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/datasets/{name}/versions", tags=["versions"], summary="Changelog: every version and what changed")
def versions(name: str):
    try:
        return store.get_versions(_con(), name)
    except store.NotFound:
        raise HTTPException(404, f"dataset '{name}' not found")


@app.get("/datasets/{name}/export.csv", tags=["datasets"], summary="Download the clean data as CSV")
def export_csv(name: str, version: Optional[int] = Query(None, ge=1)):
    con = _con()
    try:
        v = version or store.latest_version(con, name)
        if v is None:
            raise store.NotFound(name)
        df = store.read_table(con, store.table_name(name, v))
    except (store.NotFound, pd.errors.DatabaseError):
        raise HTTPException(404, f"dataset '{name}' not found")
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}_v{v}.csv"'})
