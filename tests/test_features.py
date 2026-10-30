from pathlib import Path

import pytest
from fastapi.testclient import TestClient

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("RINSE_DB", str(tmp_path / "test.db"))
    from rinse.api import app
    from rinse.core import add_dataset

    add_dataset(str(EXAMPLES / "karnataka_schools_v1.csv"), name="schools")
    return TestClient(app)


def test_web_ui_and_js_client_are_served(client):
    page = client.get("/ui")
    assert page.status_code == 200
    assert "rinse.js" in page.text
    js = client.get("/static/rinse.js")
    assert js.status_code == 200
    assert "export class Rinse" in js.text


def test_update_all_versions_only_changed_data(client, capsys):
    from rinse.cli import update_all

    assert update_all() == 0
    assert "no changes" in capsys.readouterr().out


def test_cli_update_requires_name_or_all(client):
    from rinse.cli import main

    with pytest.raises(SystemExit):
        main(["update"])


def test_csv_export(client):
    res = client.get("/datasets/schools/export.csv")
    assert res.status_code == 200
    assert res.text.splitlines()[0].startswith("sl_no,district_name")
    assert "Mysuru" in res.text


def test_changelog_wording(client):
    log = client.get("/datasets/schools/versions").json()
    assert log[0]["changes"]["summary"] == "initial import (8 rows)"
