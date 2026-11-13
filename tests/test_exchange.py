import csv
import io
import json
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).parents[1]


def test_import_all_legacy_rows_without_changing_values(client, profile):
    count = 0
    for path in sorted((ROOT / "annotations").rglob("*.csv")):
        text = path.read_text(encoding="utf-8-sig")
        request = {"csv": text, "filename": path.relative_to(ROOT).as_posix()}
        preview = client.post("/api/import/preview", json=request)
        assert preview.status_code == 200, preview.text
        assert not preview.json()["errors"]
        assert all(not row["errors"] for row in preview.json()["rows"])
        imported = client.post("/api/import/apply", json=request).json()
        count += imported["imported"]
        assert client.post("/api/import/apply", json=request).json()["imported"] == 0
    assert count == 66
    response = client.get("/api/export")
    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        exported = list(csv.DictReader(io.StringIO(archive.read("annotations.csv").decode("utf-8-sig"))))
        assert len(exported) == 66
        assert {row["annotator_name"] for row in exported} == {"brian", "miles"}
        assert all(row["status"] == "legacy" for row in exported)
        for path in (ROOT / "annotations").rglob("*.csv"):
            for original in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig"))):
                matches = [row for row in exported if row["annotator_name"] == path.parent.name
                           and all(row[key] == value for key, value in original.items() if key != "date")]
                assert matches, original
        provenance = json.loads(archive.read("provenance.json"))
        assert len(provenance["observations"]) == 66
        reimport = client.post("/api/import/apply", json={
            "csv": archive.read("annotations.csv").decode("utf-8-sig"), "filename": "annotations.csv",
        }).json()
        assert reimport["imported"] == 0
        assert not reimport["errors"]


def test_preview_bad_rows_and_distinct_annotators(client, profile):
    text = 'pmid,mutation,phenotype,date\n123,TEST:A1G,"Quoted, observation",2026.10.22\ninvalid,,,bad\n'
    preview = client.post("/api/import/preview", json={"csv": text, "annotator": "One"}).json()
    assert len(preview["rows"]) == 2
    assert preview["rows"][0]["fields"]["date"] == "10/22/2026"
    assert preview["rows"][1]["errors"]
    assert client.post("/api/import/apply", json={"csv": text, "annotator": "One"}).status_code == 422
    valid = text.split("invalid")[0]
    for name in ("One", "Two"):
        assert client.post("/api/import/apply", json={"csv": valid, "annotator": name}).json()["imported"] == 1
    assert len(client.get("/api/papers/123/observations").json()) == 2


def test_backup_restore_and_bad_backup_preserve_data(client, paper):
    observation = client.post("/api/papers/123/observations", json={}).json()
    backup = client.get("/api/backup").content
    client.post("/api/papers/123/observations", json={})
    assert len(client.get("/api/papers/123/observations").json()) == 2
    assert client.post("/api/restore", content=b"not sqlite").status_code == 422
    assert len(client.get("/api/papers/123/observations").json()) == 2
    assert client.post("/api/restore", content=backup).status_code == 200
    assert client.get("/api/papers/123/observations").json() == [observation]
    assert client.app.state.store.path.with_suffix(".before-restore.sqlite3").is_file()


def test_partial_work_and_screening_notes_export(client, paper):
    client.post("/api/papers/123/observations", json={})
    client.put("/api/papers/123/review", json={"progress": "deferred", "notes": "A screening note", "revision": 0})
    with ZipFile(io.BytesIO(client.get("/api/export").content)) as archive:
        assert "A screening note" in archive.read("papers.csv").decode()
        assert "draft" in archive.read("annotations.csv").decode()
    with ZipFile(io.BytesIO(client.get("/api/export?completed_only=true").content)) as archive:
        assert len(archive.read("annotations.csv").decode().splitlines()) == 1


def test_restore_remembers_the_running_app_rule_snapshots(client, profile):
    digest = next(iter(client.app.state.service.versions.values()))
    with client.app.state.store.connection() as conn:
        conn.execute("DELETE FROM settings WHERE id = ?", ("resource:" + digest,))
    older_backup = client.get("/api/backup").content
    assert client.post("/api/restore", content=older_backup).status_code == 200
    with ZipFile(io.BytesIO(client.get("/api/export").content)) as archive:
        provenance = json.loads(archive.read("provenance.json"))
        assert digest in {item["hash"] for item in provenance["resource_snapshots"]}
