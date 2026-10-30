import pandas as pd

from rinse.cleaners import clean_dataframe
from rinse.cleaners.dates import parse_date
from rinse.cleaners.headers import clean_headers
from rinse.cleaners.numbers import parse_number
from rinse.cleaners.places import canonical_place, place_kind


def test_dates_day_first():
    assert parse_date("15-08-2023") == "2023-08-15"
    assert parse_date("05/09/2023") == "2023-09-05"
    assert parse_date("17.08.23") == "2023-08-17"
    assert parse_date("01-Sep-2023") == "2023-09-01"
    assert parse_date("2023-09-02") == "2023-09-02"
    assert parse_date("not a date") is None


def test_indian_numbers():
    assert parse_number("1,25,000")[0] == 125000
    assert parse_number("Rs. 1,25,000/-")[0] == 125000
    assert parse_number("₹ 95,000")[0] == 95000
    assert parse_number("2.5 lakh")[0] == 250000
    assert parse_number("1.2 crore")[0] == 12000000
    assert parse_number("92.5%")[0] == 92.5
    assert parse_number("(500)")[0] == -500
    assert parse_number("Mysuru")[0] is None


def test_district_names():
    for spelling in ["Mysore", "MYSORE", "mysuru", "Mysuru District", " mysore  "]:
        assert canonical_place(spelling, "district") == "Mysuru"
    assert canonical_place("BANGALORE", "district") == "Bengaluru Urban"
    assert canonical_place("DAKSHINA KANNADA", "district") == "Dakshina Kannada"


def test_state_names():
    assert canonical_place("ORISSA", "state") == "Odisha"
    assert canonical_place("Jammu & Kashmir", "state") == "Jammu and Kashmir"


def test_place_column_detection():
    assert place_kind("district_name") == "district"
    assert place_kind("state_ut") == "state"
    assert place_kind("district_code") is None
    assert place_kind("distance_km") is None


def test_headers():
    cols, _ = clean_headers(["Sl. No.", "District Name", "Pass %", "District Name", "2021"])
    assert cols == ["sl_no", "district_name", "pass_pct", "district_name_2", "c_2021"]


def test_full_pipeline():
    raw = pd.DataFrame({
        "District": ["MYSORE", "Mysuru", "Total"],
        "Release Date": ["15-08-2023", "16/08/2023", None],
        "Amount": ["1,25,000", "2.5 lakh", None],
    }, dtype=object)
    df, report = clean_dataframe(raw)
    assert list(df["district"]) == ["Mysuru", "Mysuru"]
    assert list(df["release_date"]) == ["2023-08-15", "2023-08-16"]
    assert list(df["amount"]) == [125000, 250000]
    assert report["kinds"]["release_date"] == "date"
