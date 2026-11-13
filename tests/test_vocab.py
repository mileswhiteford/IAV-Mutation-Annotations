import importlib.util
from pathlib import Path


def test_collector_uses_canonical_and_legacy_dates_and_export_attribution(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts" / "collect_vocab.py"
    spec = importlib.util.spec_from_file_location("collect_vocab", script)
    collector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(collector)
    folder = tmp_path / "annotations" / "export"
    folder.mkdir(parents=True)
    (folder / "canonical.csv").write_text(
        "phenotype,animal_model,date,annotator_name\nA result,,10/22/2026,Contributor\n",
        encoding="utf-8",
    )
    (folder / "legacy.csv").write_text(
        "phenotype,animal_model,date_annotated\nA result,,2025.12.31\n", encoding="utf-8",
    )
    monkeypatch.setattr(collector, "ANNOTATIONS", tmp_path / "annotations")
    entries = collector.collect()["phenotype"]["a result"]
    assert entries["annotators"] == {"Contributor", "export"}
    assert sorted(entries["dates"]) == ["2025-12-31", "2026-10-22"]
