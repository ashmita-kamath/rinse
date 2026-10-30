# Contributing to Rinse

Thanks for helping make Indian open data easier to use. A first PR is usually **one rule plus one test**.

## Setup

```bash
git clone https://github.com/team-akira/rinse.git && cd rinse
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Easy contributions

**1. Add a district or state spelling**
Add a line to `rinse/rules/district_aliases.csv` or `state_aliases.csv`:

```
alias,canonical
Bijapur (Karnataka),Vijayapura
```

Then add an assert to `test_district_names` in `tests/test_cleaners.py`. Use the official LGD name as `canonical`.

**2. Add a number or unit format**
Edit `rinse/cleaners/numbers.py` (for example a new multiplier word) and add a case to `test_indian_numbers`.

**3. Add a date format**
Add the `strptime` pattern to `FORMATS` in `rinse/cleaners/dates.py` and a case to `test_dates_day_first`. Keep day-first order.

**4. Add a file-type adapter**
`rinse/ingest.py` detects the format in `sniff()` and reads it in `read_source()`. Add your format there with a small example file in `examples/`.

## Rules

- One change per PR, with a test.
- Run `pytest` before opening the PR.
- Do not commit real API keys or secrets.
- Only add sample data you are allowed to share, and say where it came from.
- Be kind. We follow the [MLH Code of Conduct](https://mlh.io/code-of-conduct).
