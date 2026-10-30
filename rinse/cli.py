"""rinse command line."""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, store
from .cleaners import clean_dataframe
from .core import add_dataset, update_dataset
from .ingest import read_source


def _print_result(res) -> None:
    if not res["changed"]:
        print(f"= {res['name']}: no changes, still v{res['version']}")
        return
    print(f"+ {res['name']} v{res['version']}  ({res['rows']} rows, {res['format']})")
    print(f"  changelog: {res['changes']['summary']}")
    for note in res["cleaning"]["notes"]:
        print(f"  cleaned:   {note}")


def cmd_add(args) -> None:
    res = add_dataset(args.source, name=args.name)
    _print_result(res)
    if args.describe:
        from .ai import AIUnavailable, describe_columns
        try:
            docs = describe_columns(res["name"], res["frame"])
            store.set_descriptions(store.connect(), res["name"], docs)
            print(f"  ai docs:   described {len(docs)} columns with a local open model")
        except AIUnavailable as exc:
            print(f"  ai docs:   skipped ({exc})")
    print(f"  try:       rinse serve   then open http://127.0.0.1:8000/datasets/{res['name']}/rows")


def cmd_update(args) -> None:
    _print_result(update_dataset(args.name))


def cmd_list(args) -> None:
    rows = store.list_datasets(store.connect())
    if not rows:
        print("no datasets yet. run: rinse add <url-or-file>")
    for d in rows:
        print(f"{d['name']:<30} v{d['latest_version']:<4} {d['row_count']:>7} rows   {d['source']}")


def cmd_log(args) -> None:
    for v in store.get_versions(store.connect(), args.name):
        print(f"v{v['version']}  {v['created_at']}  {v['row_count']} rows  {v['changes']['summary']}")


def cmd_show(args) -> None:
    res = store.read_rows(store.connect(), args.name, limit=args.limit)
    print(json.dumps(res["rows"], indent=2, ensure_ascii=False, default=str))


def cmd_clean(args) -> None:
    raw, _ = read_source(args.source)
    df, report = clean_dataframe(raw)
    df.to_csv(args.output, index=False)
    print(f"wrote {len(df)} clean rows to {args.output}")
    for note in report["notes"]:
        print(f"  cleaned: {note}")


def cmd_serve(args) -> None:
    import uvicorn
    uvicorn.run("rinse.api:app", host=args.host, port=args.port, reload=False)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="rinse", description="Turn Indian public data into a clean, versioned API.")
    p.add_argument("--version", action="version", version=f"rinse {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("add", help="add a dataset from a URL or file (CSV, Excel, JSON)")
    a.add_argument("source")
    a.add_argument("--name", help="dataset name (default: from file name)")
    a.add_argument("--describe", action="store_true", help="write column docs with a local Qwen model via Ollama")
    a.set_defaults(func=cmd_add)

    u = sub.add_parser("update", help="re-fetch a dataset; creates a new version only if data changed")
    u.add_argument("name")
    u.set_defaults(func=cmd_update)

    sub.add_parser("list", help="list datasets").set_defaults(func=cmd_list)

    lg = sub.add_parser("log", help="show the changelog of a dataset")
    lg.add_argument("name")
    lg.set_defaults(func=cmd_log)

    sh = sub.add_parser("show", help="print the first rows of a dataset")
    sh.add_argument("name")
    sh.add_argument("--limit", type=int, default=5)
    sh.set_defaults(func=cmd_show)

    c = sub.add_parser("clean", help="just clean a file and save it as CSV (no API)")
    c.add_argument("source")
    c.add_argument("-o", "--output", default="clean.csv")
    c.set_defaults(func=cmd_clean)

    s = sub.add_parser("serve", help="start the REST API (docs at /docs)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8000)
    s.set_defaults(func=cmd_serve)

    args = p.parse_args(argv)
    try:
        args.func(args)
    except (store.NotFound, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
