# Rinse

**Turn any Indian public dataset into a clean, versioned API in one command.**

Built by Team Akira at Devf8rge × Hacktoberfest Hack Day 2026, Bengaluru (PS-10 · Open Data to Open API · Track 5 · Open source for Bharat).

## The problem

Files from data.gov.in and state portals are messy. One district appears as `Mysore`, `MYSURU` and `mysuru district`. Dates mix `15-08-2023`, `16/08/2023` and `01-Sep-2023`. Money is written as `Rs. 1,25,000/-` or `2.5 lakh`. There are title rows above the header and a `Total` row at the bottom. Every team cleans the same files by hand, and nothing updates when the source changes.

## What Rinse does

```
rinse add <url-or-file>
```

1. **Fetches** a CSV, Excel or JSON file from a URL or your disk (including the data.gov.in JSON format).
2. **Cleans Indian formats**
   - finds the real header row and skips title rows; drops `Total` rows
   - district and state names → one standard spelling (`Mysore` → `Mysuru`, `Orissa` → `Odisha`)
   - dates (day-first, Indian style) → `YYYY-MM-DD`
   - numbers: `1,23,456`, `₹`, `Rs. 500/-`, `lakh`, `crore`, `%` → real numbers
   - `NA`, `N.A.`, `-`, `nil` → null; headers → `snake_case`
3. **Serves a REST API** with OpenAPI docs at `/docs`, filtering and CSV export, plus a **web explorer** at `/ui`.
4. **Versions every change.** `rinse update` (or `rinse watch` on a schedule) re-fetches the source; if the data changed you get a new version and a changelog entry. Old versions stay queryable.
5. **Clients** for Python and JavaScript.

## Setup (3 steps)

```bash
git clone https://github.com/ashmita-kamath/rinse.git && cd rinse
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Python 3.9+.

## Try it

```bash
rinse add examples/karnataka_schools_v1.csv --name schools
rinse serve
```

Open **http://127.0.0.1:8000/ui** to browse, filter, compare versions and download clean CSV. API docs are at http://127.0.0.1:8000/docs.

API endpoints:

```
GET /datasets                                   list datasets
GET /datasets/schools                           columns, kinds, cleaning report
GET /datasets/schools/rows?district_name=mysuru exact match (case-insensitive)
GET /datasets/schools/rows?grant_amount_rs__gte=100000
GET /datasets/schools/rows?district_name__contains=bengaluru
GET /datasets/schools/rows?version=1            any older version
GET /datasets/schools/versions                  changelog
GET /datasets/schools/export.csv                clean CSV download
```

Filters: `col=value`, or `col__gte`, `__lte`, `__gt`, `__lt`, `__ne`, `__contains`. Paging: `limit` (max 1000), `offset`.

See versioning work:

```bash
rinse add examples/karnataka_schools_v2.csv --name schools
rinse log schools
```

### Python client

```python
from rinse.client import Rinse

api = Rinse("http://127.0.0.1:8000")
api.rows("schools", district_name="Mysuru")
api.versions("schools")
df = api.to_dataframe("schools")
```

### JavaScript client

No dependencies; works in the browser and Node 18+. The server hosts it at `/static/rinse.js` (source: `rinse/static/rinse.js`).

```js
import { Rinse } from "http://127.0.0.1:8000/static/rinse.js";

const api = new Rinse("http://127.0.0.1:8000");
const { rows, total } = await api.rows("schools", { district_name: "Mysuru" });
const log = await api.versions("schools");
```

### Scheduled re-checks

```bash
rinse update --all
rinse watch --interval 3600
```

`watch` re-checks every source each hour and creates a new version only when the data actually changed.

### Docker

```bash
docker compose up --build
```

Starts the API on port 8000 and a watcher that re-checks sources hourly, sharing one database volume. Add data with:

```bash
docker compose exec api rinse add examples/karnataka_schools_v1.csv --name schools
```

### All commands

| Command | What it does |
|---|---|
| `rinse add <src> [--name N] [--describe]` | fetch, clean, store as a new version |
| `rinse update <name>` / `--all` | re-fetch from the saved source; new version only if data changed |
| `rinse watch [--interval 3600]` | re-check all sources on a schedule |
| `rinse list` | all datasets |
| `rinse log <name>` | changelog |
| `rinse show <name>` | first rows |
| `rinse clean <src> -o out.csv` | clean a file only, no API |
| `rinse serve [--port 8000]` | start the API and web explorer (`/ui`) |

### Official district list (LGD)

Download the district list from the Local Government Directory (lgdirectory.gov.in) as CSV, then:

```bash
export RINSE_LGD=/path/to/lgd_districts.csv
```

Unknown district spellings are then fuzzy-matched to the official LGD names.

### Optional: local open-weight AI

`--describe` asks **Qwen2.5 1.5B** running locally in [Ollama](https://ollama.com) to write a one-line description for every column, shown in `/datasets/{name}`. Nothing leaves your machine, and Rinse works fine without it.

```bash
ollama pull qwen2.5:1.5b
rinse add examples/karnataka_schools_v1.csv --name schools --describe
```

Settings: `RINSE_DB` (database file, default `rinse.db`), `OLLAMA_URL`, `RINSE_MODEL`.

## How it works

```
source (URL / file) → ingest.py → cleaners/ → store.py (SQLite, one table per version) → api.py (FastAPI) → /ui, Python + JS clients
```

Cleaning rules live in `rinse/cleaners/` and the spelling lists in `rinse/rules/*.csv`, so adding a rule is a small, self-contained PR.

## Tests

```bash
pytest
```

## AI tools used

- **Claude (Anthropic)** was used as a coding assistant during the hackathon. Every team member has reviewed the code and can explain it.
- The product itself uses **no closed AI APIs**. The optional column-description feature uses the open-weight **Qwen2.5 1.5B** model locally via Ollama.

## Credits

- [FastAPI](https://fastapi.tiangolo.com/), [Uvicorn](https://www.uvicorn.org/), [pandas](https://pandas.pydata.org/), [openpyxl](https://openpyxl.readthedocs.io/), [pytest](https://pytest.org/)
- [Ollama](https://ollama.com/) and [Qwen2.5](https://github.com/QwenLM/Qwen2.5) (optional)
- Data: [data.gov.in](https://data.gov.in) (Open Government Data Platform India), [Local Government Directory](https://lgdirectory.gov.in)
- `examples/` contains small illustrative files made for this demo, not official data.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Your first PR can be one line in a rule file plus a test.

## Team Akira

- Ashmita Kamath — backend, data pipeline
- Dhanishtha — frontend, docs, demo

## License

[MIT](LICENSE)
