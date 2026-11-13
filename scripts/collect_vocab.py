"""Collect every raw value used in controlled fields.

For each field listed in CONTROLLED_FIELDS, reads all annotation CSVs and
rewrites vocab/<field>/raw.csv with every unique value, how often it was
used, and by who. Creates vocab/<field>/standard.csv with headers if missing,
but never overwrites it.

Run from the repo root:  python scripts/collect_vocab.py
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

CONTROLLED_FIELDS = [
    "phenotype",
    "animal_model",
]

SKIP_VALUES = {"", "na", "n/a", " "}

# Canonical column first; retain compatibility with older annotation sheets.
DATE_COLUMNS = ("date", "date_annotated")

ROOT = Path(__file__).resolve().parent.parent
ANNOTATIONS = ROOT / "annotations"
VOCAB = ROOT / "vocab"

MAP_HEADER = ["raw_value", "standard_value", "date", "note"]


def normalize(value: str) -> str:
    """Strip and collapse internal whitespace."""
    return " ".join(value.split())


def annotation_date(row: dict) -> str:
    """ISO dates sort chronologically even when input sheets use different formats."""
    for column in DATE_COLUMNS:
        value = normalize(row.get(column) or "")
        for pattern in ("%m/%d/%Y", "%Y.%m.%d", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, pattern).date().isoformat()
            except ValueError:
                continue
    return ""


def collect():
    """Return {field: {key: {value, count, annotators, first_seen}}}."""
    found = {f: defaultdict(lambda: {"value": "", "count": 0,
                                     "annotators": set(), "dates": []})
             for f in CONTROLLED_FIELDS}

    if not ANNOTATIONS.is_dir():
        sys.exit(f"No annotations directory at {ANNOTATIONS}")

    for path in sorted(ANNOTATIONS.rglob("*.csv")):
        # annotator = the folder directly under annotations/
        try:
            annotator = path.relative_to(ANNOTATIONS).parts[0]
        except ValueError:
            continue

        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                continue
            for row in reader:
                date = annotation_date(row)
                row_annotator = normalize(row.get("annotator_name") or "") or annotator
                for field in CONTROLLED_FIELDS:
                    if field not in reader.fieldnames:
                        continue
                    value = normalize(row.get(field) or "")
                    if value.lower() in SKIP_VALUES:
                        continue
                    entry = found[field][value.lower()]
                    if not entry["value"]:
                        entry["value"] = value 
                    entry["count"] += 1
                    entry["annotators"].add(row_annotator)
                    if date:
                        entry["dates"].append(date)
    return found


def read_mapped(field: str) -> set:
    """Lowercased raw_values already present in this field's standard.csv."""
    map_path = VOCAB / field / "standard.csv"
    if not map_path.is_file():
        return set()
    with open(map_path, newline="", encoding="utf-8-sig") as f:
        return {normalize(r.get("raw_value") or "").lower()
                for r in csv.DictReader(f)}


def write_field(field: str, entries: dict) -> list:
    """Write raw.csv, ensure standard.csv exists, return unmapped values."""
    folder = VOCAB / field
    folder.mkdir(parents=True, exist_ok=True)

    rows = sorted(entries.values(),
                  key=lambda e: (-e["count"], e["value"].lower()))

    with open(folder / "raw.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["raw_value", "count", "annotators", "first_seen"])
        for e in rows:
            w.writerow([e["value"], e["count"],
                        ";".join(sorted(e["annotators"])),
                        min(e["dates"]) if e["dates"] else ""])

    map_path = folder / "standard.csv"
    if not map_path.is_file():
        with open(map_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(MAP_HEADER)

    mapped = read_mapped(field)
    return [e["value"] for e in rows if e["value"].lower() not in mapped]


def main():
    found = collect()
    total_unmapped = 0

    for field in CONTROLLED_FIELDS:
        unmapped = write_field(field, found[field])
        total_unmapped += len(unmapped)
        print(f"{field}: {len(found[field])} unique value(s), "
              f"{len(unmapped)} not yet in standard.csv")
        for value in unmapped:
            print(f"    - {value}")

    print(f"\n{total_unmapped} total raw values")


if __name__ == "__main__":
    main()
