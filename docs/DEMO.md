# 3-minute demo script

Before going on stage: `rm -f rinse.db`, terminal font large, browser tab ready.

**0:00 – Problem (20s)**
Open `examples/karnataka_schools_v1.csv`. Point at: title rows, `MYSORE` / `Mysuru` / `mysuru district`, three date styles, `Rs. 1,25,000/-`, `2.5 lakh`, `NA`, the `Total` row.
"Every team that uses this file cleans it by hand. We made that one command."

**0:20 – One command (40s)**
```
rinse add examples/karnataka_schools_v1.csv --name schools
```
Read out the cleaning report: 2 title rows skipped, Total row dropped, 8 spellings → 5 districts, dates to ISO, lakh/crore/₹ to numbers.

**1:00 – Live API (50s)**
```
rinse serve
```
Browser: `http://127.0.0.1:8000/docs` → try `/datasets/schools/rows` with `district_name=mysuru`, then `grant_amount_rs__gte=1000000` (only the 1.2 crore row).

**1:50 – Versioning (40s)**
New terminal:
```
rinse add examples/karnataka_schools_v2.csv --name schools
rinse log schools
```
"The source changed: one amount was corrected and Tumkur was added. Rinse made v2, and v1 is still at `?version=1`."

**2:30 – Python client + open source (30s)**
```
python3 -c "from rinse.client import Rinse; print(Rinse().rows('schools', district_name='Mysuru'))"
```
"MIT licence. Adding a district spelling is one line in a CSV plus a test. Local Qwen model for column docs, no closed AI APIs."

## Likely Q&A

- **What if a district isn't in your list?** It's title-cased; with the LGD list loaded (`RINSE_LGD`) it's fuzzy-matched to the official name. New aliases are one-line PRs.
- **How do you detect changes?** Each row is hashed; we compare row hashes between versions, so we know rows added and removed without needing an ID column.
- **Why SQLite?** Zero setup, one file, easy to self-host. Each version is its own table so old versions stay queryable.
- **How do you avoid SQL injection with dynamic filters?** Column names are checked against the table's real columns, and all values are bound parameters.
- **Day-first vs month-first dates?** Indian files are day-first, so we only try day-first patterns plus ISO.
