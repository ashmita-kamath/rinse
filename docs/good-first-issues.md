# Good first issues

Copy each into a GitHub issue and add the `good first issue` label.

---

## 1. Add Karnataka district renames still missing from the alias list

`rinse/rules/district_aliases.csv` covers common old names (Mysore, Belgaum, Gulbarga...). Add any remaining Karnataka spellings you find in data.gov.in files, with the official LGD name as canonical, and a test in `tests/test_cleaners.py`.

## 2. Record units written in headers, like `Amount (Rs. in lakh)`

Many files put the unit in the column header instead of the values. Detect `in lakh`, `in crore`, `in Rs.` and `in %` in headers (`rinse/cleaners/headers.py`), store the unit in the cleaning report, and show it in `GET /datasets/{name}` next to the column. Add tests.

## 3. Read the first non-empty sheet of an Excel workbook

`ingest.py` always reads sheet 0. Some files keep a cover sheet first. Pick the first sheet that has a table, and add an example `.xlsx` plus a test.
