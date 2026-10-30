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


def test_rows_are_clean(client):
    body = client.get("/datasets/schools/rows").json()
    assert body["total"] == 8
    first = body["rows"][0]
    assert first["district_name"] == "Mysuru"
    assert first["date_of_release"] == "2023-08-15"
    assert first["grant_amount_rs"] == 125000


def test_filters(client):
    assert client.get("/datasets/schools/rows?district_name=mysuru").json()["total"] == 3
    assert client.get("/datasets/schools/rows?grant_amount_rs__gte=1000000").json()["total"] == 1
    assert client.get("/datasets/schools/rows?nope=1").status_code == 400


def test_versioning(client):
    from rinse.core import add_dataset

    same = add_dataset(str(EXAMPLES / "karnataka_schools_v1.csv"), name="schools")
    assert same["changed"] is False

    res = add_dataset(str(EXAMPLES / "karnataka_schools_v2.csv"), name="schools")
    assert res["version"] == 2
    assert res["changes"]["rows_added"] == 2
    assert res["changes"]["rows_removed"] == 1

    log = client.get("/datasets/schools/versions").json()
    assert [v["version"] for v in log] == [2, 1]
    assert client.get("/datasets/schools/rows?version=1").json()["total"] == 8
    assert client.get("/datasets/schools/rows").json()["total"] == 9


def test_docs_and_404(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/datasets/missing").status_code == 404
