from pathlib import Path

from openpyxl import Workbook

from rinse.ingest import read_source

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_excel_skips_cover_and_empty_sheets():
    df, info = read_source(str(EXAMPLES / "schools_with_cover.xlsx"))
    assert list(df.columns) == ["District", "Schools"]
    assert df.values.tolist() == [["Mysuru", 12], ["Bengaluru", 20]]
    assert info["format"] == "xlsx"
    assert info["title_rows_skipped"] == 1


def test_excel_uses_first_table_in_workbook_order(tmp_path):
    book = Workbook()
    book.active.append(["District", "Schools"])
    book.active.append(["Mysuru", 12])
    later = book.create_sheet("Later")
    later.append(["District", "Schools"])
    later.append(["Bengaluru", 20])
    path = tmp_path / "tables.xlsx"
    book.save(path)
    df, info = read_source(str(path))
    assert df.values.tolist() == [["Mysuru", 12]]
    assert info["title_rows_skipped"] == 0


def test_excel_keeps_single_column_tables(tmp_path):
    book = Workbook()
    book.active.append(["Cover"])
    data = book.create_sheet("Data")
    data.append(["District"])
    data.append(["Mysuru"])
    path = tmp_path / "single.xlsx"
    book.save(path)
    df, _ = read_source(str(path))
    assert list(df.columns) == ["District"]
    assert df.values.tolist() == [["Mysuru"]]


def test_excel_without_data_rows_returns_empty_frame(tmp_path):
    book = Workbook()
    book.active.append(["  "])
    book.create_sheet("Headers").append(["District", "Schools"])
    path = tmp_path / "empty.xlsx"
    book.save(path)
    df, info = read_source(str(path))
    assert df.empty
    assert info["title_rows_skipped"] == 0
