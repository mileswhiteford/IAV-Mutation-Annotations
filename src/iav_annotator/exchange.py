"""Loss-aware CSV exchange and provenance bundles. CSV never overwrites records."""

import csv
import hashlib
import io
import json
import re
from pathlib import PurePosixPath
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from .db import all_rows, get, now, put
from .models import ImportPreview, ImportRequest, ImportRow, Observation, Profile, SchemaFields
from .resources import resource_path
from .service import normalize_date, validate_fields

csv.field_size_limit(20_000_000)


def stable_id(value: str) -> str:
    return str(uuid5(NAMESPACE_URL, "iav-annotator:" + value))


def preview_import(request: ImportRequest, service) -> ImportPreview:
    try:
        reader = csv.DictReader(io.StringIO(request.csv.lstrip("\ufeff")))
        headers = reader.fieldnames or []
        if "pmid" not in headers:
            return ImportPreview(rows=[], errors=["The CSV must have a pmid column."])
        if len(set(headers)) != len(headers):
            return ImportPreview(rows=[], errors=["The CSV contains duplicate column headers."])
        rows = []
        filename = PurePosixPath(request.filename.replace("\\", "/"))
        inferred_name = filename.parent.name if "annotations" in filename.parts[:-1] else ""
        for line, original in enumerate(reader, 2):
            if line > 10001:
                return ImportPreview(rows=[], errors=["Import at most 10,000 rows at a time."])
            errors, warnings = [], []
            if None in original:
                errors.append("This row has more values than the CSV header.")
            values = {key: original.get(key) or "" for key in SchemaFields.model_fields}
            if not values["date"]:
                values["date"] = original.get("date_annotated") or ""
            try:
                values["date"] = normalize_date(values["date"])
            except ValueError as exc:
                errors.append(str(exc))
            if not re.fullmatch(r"[1-9][0-9]{0,11}", values["pmid"]):
                errors.append("PMID must contain digits only.")
            name = original.get("annotator_name") or request.annotator.strip() or inferred_name
            if not name:
                errors.append("Provide the annotator name; author identifies the paper's researcher.")
            annotator_id = original.get("annotator_id") or stable_id("annotator:" + name)
            email = original.get("annotator_email") or ""
            identity = json.dumps([annotator_id, request.filename, line, original], sort_keys=True)
            observation_id = original.get("observation_id") or stable_id(identity)
            fields = SchemaFields(**values)
            warnings.extend(validate_fields(fields))
            warnings.append("CSV has no verified evidence anchors; new imports require review before completion.")
            with service.store.connection() as conn:
                existing = get(conn, "observations", observation_id)
                if existing and (existing["fields"] != fields.model_dump()
                                 or existing["annotator_id"] != annotator_id):
                    errors.append("This observation ID already exists with different values. CSV import does not overwrite it.")
            rows.append(ImportRow(line=line, fields=fields, annotator_id=annotator_id,
                                  annotator_name=name, annotator_email=email,
                                  observation_id=observation_id, warnings=warnings,
                                  errors=errors, original={str(k): v for k, v in original.items()}))
        return ImportPreview(rows=rows)
    except (csv.Error, ValueError) as exc:
        return ImportPreview(rows=[], errors=[f"Cannot read this CSV: {exc}"])


def apply_import(request: ImportRequest, service) -> ImportPreview:
    preview = preview_import(request, service)
    if preview.errors or any(row.errors for row in preview.rows):
        raise HTTPException(422, preview.model_dump())
    digest = hashlib.sha256(request.csv.encode("utf-8")).hexdigest()
    with service.store.connection() as conn:
        service.profile(conn)
        for row in preview.rows:
            if get(conn, "observations", row.observation_id):
                preview.skipped += 1
                continue
            if not get(conn, "profiles", row.annotator_id):
                put(conn, "profiles", row.annotator_id,
                    Profile(id=row.annotator_id, name=row.annotator_name,
                            email=row.annotator_email).model_dump())
            service.ensure_paper(conn, row.fields.pmid)
            status = "draft" if row.original.get("status") == "draft" else "legacy"
            observation = Observation(
                id=row.observation_id, pmid=row.fields.pmid, annotator_id=row.annotator_id,
                annotator_name=row.annotator_name, annotator_email=row.annotator_email,
                fields=row.fields, status=status, review_flag=True, revision=1,
                created_at=now(), updated_at=now(), versions={},
                provenance={"filename": request.filename, "line": row.line, "file_hash": digest,
                            "original": row.original, "imported_at": now()},
            )
            service.record(conn, observation)
            preview.imported += 1
    return preview


def repository_imports() -> list[ImportRequest]:
    base = resource_path("annotations")
    return [ImportRequest(csv=path.read_text(encoding="utf-8-sig"), annotator=path.parent.name,
                          filename=f"annotations/{path.parent.name}/{path.name}")
            for path in sorted(base.rglob("*.csv"))]


def csv_text(headers: list[str], rows: list[dict]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return "\ufeff" + stream.getvalue()


def export_bundle(service, completed_only: bool = False) -> bytes:
    with service.store.connection() as conn:
        observations = [o for o in all_rows(conn, "observations")
                        if not completed_only or o["status"] == "complete"]
        papers = all_rows(conn, "papers")
        reviews = all_rows(conn, "reviews")
        profiles = {p["id"]: p for p in all_rows(conn, "profiles")}
        ids = {o["id"] for o in observations}
        provenance = {
            "format_version": 1, "exported_at": now(), "observations": observations,
            "revisions": [r for r in all_rows(conn, "revisions") if r["observation"]["id"] in ids],
            "sources": [{key: value for key, value in s.items() if key != "raw"}
                        for s in all_rows(conn, "sources")],
            "resource_snapshots": [s for s in all_rows(conn, "settings") if "hash" in s],
            "profiles": list(profiles.values()), "papers": papers, "reviews": reviews,
        }
    rows = []
    for observation in observations:
        rows.append({**observation["fields"], "observation_id": observation["id"],
                     **{key: observation.get(key, "") for key in
                        ("annotator_id", "annotator_name", "annotator_email", "status", "review_flag")}})
    paper_rows = []
    for paper in papers:
        entries = [r for r in reviews if r.get("pmid") == paper["pmid"]]
        if not entries:
            entries = [{}]
        for review in entries:
            owner = profiles.get(review.get("annotator_id"), {})
            paper_rows.append({**paper, **review, "annotator_name": owner.get("name", ""),
                               "annotator_email": owner.get("email", "")})
    output = io.BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("annotations.csv", csv_text(
            list(SchemaFields.model_fields) + ["observation_id", "annotator_id", "annotator_name",
                                               "status", "annotator_email", "review_flag"], rows))
        archive.writestr("papers.csv", csv_text(
            ["pmid", "pmcid", "paper_id", "author", "title", "doi", "citation", "annotator_id",
             "annotator_name", "annotator_email", "progress", "notes", "updated_at"], paper_rows))
        archive.writestr("provenance.json", json.dumps(provenance, ensure_ascii=False, indent=2))
        archive.writestr("README.txt", (
            "annotations.csv contains all saved work unless completed-only was requested.\n"
            "Read status and review_flag before downstream use. Legacy rows lack verified evidence.\n"
            "author identifies the paper researcher; annotator_* identifies the contributor.\n"
            "provenance.json preserves evidence, source passages, rule snapshots, and edit history.\n"
            "CSV reimport retains attribution/IDs but does not import evidence or update existing rows.\n"
            "Use an application backup to restore the complete local database.\n"
        ))
    return output.getvalue()
