import asyncio
import json
import math
import re
from datetime import date, datetime

from fastapi import HTTPException

from .bioc import fetch_source
from .db import all_rows, get, now, put, uid
from .models import (
    Observation,
    Paper,
    Profile,
    ProfileInput,
    Review,
    ReviewInput,
    SchemaFields,
    Source,
)
from .resources import registry, text_resource, versions

MUTATION = re.compile(r"[A-Za-z][A-Za-z0-9-]*:(?:[ACDEFGHIKLMNPQRSTVWY][1-9]\d*[ACDEFGHIKLMNPQRSTVWY-]|-[1-9]\d*[ACDEFGHIKLMNPQRSTVWY])")
CONTEXT = ("author", "paper_id", "pmcid", "backbone", "recombinant", "subtype", "protein",
           "numbering", "cell_type", "animal_model", "binding_assay", "temperature")


def normalize_date(value: str) -> str:
    if not value:
        return ""
    for pattern in ("%m/%d/%Y", "%Y.%m.%d", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip(), pattern).strftime("%m/%d/%Y")
        except ValueError:
            pass
    raise ValueError("Use an annotation date in MM/DD/YYYY format")


def validate_fields(fields: SchemaFields) -> list[str]:
    errors = []
    if fields.mutation.strip():
        parts = [part.strip() for part in fields.mutation.split(",")]
        if any(not MUTATION.fullmatch(part) for part in parts):
            errors.append("Mutation must use Protein:ResiduePositionResidue notation; separate combinations with commas.")
        if fields.numbering.strip() and not any(part.startswith(("HA:", "NA:")) for part in parts):
            errors.append("Numbering is only recorded for HA or NA mutations.")
    if fields.temperature.strip():
        try:
            if not math.isfinite(float(fields.temperature)):
                raise ValueError
        except ValueError:
            errors.append("Temperature must be a single numeric value in degrees Celsius.")
    try:
        normalize_date(fields.date)
    except ValueError as exc:
        errors.append(str(exc))
    return errors


class Service:
    def __init__(self, store, transport=None):
        self.store = store
        self.transport = transport
        self.registry = registry()
        self.versions = versions()
        self.resource_snapshots = [{"path": name, "hash": digest, "text": text_resource(name)}
                                   for name, digest in self.versions.items()]
        self.remember_resources()

    def remember_resources(self):
        with self.store.connection() as conn:
            for snapshot in self.resource_snapshots:
                put(conn, "settings", "resource:" + snapshot["hash"], snapshot)

    def profile(self, conn) -> Profile:
        active = get(conn, "settings", "active_profile")
        data = get(conn, "profiles", active["id"]) if active else None
        if not data:
            raise HTTPException(400, "Enter your annotator name first.")
        return Profile.model_validate(data)

    def save_profile(self, data: ProfileInput) -> Profile:
        if not data.name.strip():
            raise HTTPException(422, "Enter your annotator name.")
        with self.store.connection() as conn:
            active = get(conn, "settings", "active_profile")
            profile = Profile(id=active["id"] if active else uid(),
                              name=data.name.strip(), email=data.email.strip())
            put(conn, "profiles", profile.id, profile.model_dump())
            put(conn, "settings", "active_profile", {"id": profile.id})
        return profile

    def ensure_paper(self, conn, pmid: str) -> dict:
        paper = get(conn, "papers", pmid)
        if paper:
            return paper
        known = self.registry.get(pmid, {})
        paper = Paper(pmid=pmid, **{key: known.get(key, "") for key in
                                   ("title", "pmcid", "paper_id", "author", "doi", "citation")}).model_dump()
        put(conn, "papers", pmid, paper)
        return paper

    def paper(self, pmid: str) -> Paper:
        with self.store.connection() as conn:
            data = get(conn, "papers", pmid)
            if not data:
                raise HTTPException(404, "Paper not found.")
            profile = self.profile(conn)
            data["review"] = get(conn, "reviews", f"{pmid}:{profile.id}") or Review().model_dump()
            sources = [Source.model_validate(json.loads(row[0])) for row in conn.execute(
                "SELECT data FROM sources WHERE json_extract(data, '$.pmid') = ? ORDER BY rowid", (pmid,))]
            latest = {}
            for source in sources:
                latest[source.kind] = source
            for kind, source_id in data.get("current_sources", {}).items():
                chosen = next((s for s in sources if s.id == source_id), None)
                if chosen:
                    latest[kind] = chosen
            selected = latest.get("pmc") or latest.get("pubmed")
            data["passages"] = selected.model_dump()["passages"] if selected else []
            data["sources"] = [s.model_copy(update={"raw": "", "passages": []}) for s in sources]
            data["observation_count"] = conn.execute(
                "SELECT COUNT(*) FROM observations WHERE json_extract(data, '$.pmid') = ?", (pmid,)).fetchone()[0]
            return Paper.model_validate(data)

    def list_papers(self) -> list[Paper]:
        with self.store.connection() as conn:
            profile = self.profile(conn)
            counts = dict(conn.execute("SELECT json_extract(data, '$.pmid'), COUNT(*) FROM observations GROUP BY json_extract(data, '$.pmid')"))
            reviews = {r["pmid"]: r for r in all_rows(conn, "reviews")
                       if r["annotator_id"] == profile.id}
            return [Paper.model_validate({**paper, "review": reviews.get(paper["pmid"], Review().model_dump()),
                                          "observation_count": counts.get(paper["pmid"], 0)})
                    for paper in all_rows(conn, "papers")]

    async def retrieve(self, pmid: str) -> Paper:
        with self.store.connection() as conn:
            self.profile(conn)
            self.ensure_paper(conn, pmid)
        results = await asyncio.gather(*(fetch_source(pmid, kind, self.transport)
                                         for kind in ("pubmed", "pmc")))
        with self.store.connection() as conn:
            paper = self.ensure_paper(conn, pmid)
            for kind, result in zip(("pubmed", "pmc"), results):
                paper["retrieval"][kind] = {"state": result.state, "message": result.message,
                                             "attempted_at": now()}
                if result.source:
                    source = result.source
                    existing = [json.loads(row[0]) for row in conn.execute(
                        "SELECT data FROM sources WHERE json_extract(data, '$.pmid') = ? "
                        "AND json_extract(data, '$.kind') = ? AND json_extract(data, '$.hash') = ?",
                        (pmid, kind, source.hash))]
                    if not existing:
                        put(conn, "sources", source.id, source.model_dump())
                    paper.setdefault("current_sources", {})[kind] = existing[0]["id"] if existing else source.id
                    titles = [p.text for p in source.passages if p.section == "title"]
                    if titles:
                        paper["title"] = titles[0]
                    for passage in source.passages:
                        if passage.section == "title":
                            doi = passage.infons.get("article-id_doi")
                            if doi:
                                paper["doi"] = str(doi)
                    match = re.search(r'"(?:id|pmcid)"\s*:\s*"(PMC\d+)"', source.raw)
                    if match:
                        paper["pmcid"] = match[1]
            put(conn, "papers", pmid, paper)
        return self.paper(pmid)

    def review(self, pmid: str, update: ReviewInput) -> Review:
        with self.store.connection() as conn:
            if not get(conn, "papers", pmid):
                raise HTTPException(404, "Paper not found.")
            profile = self.profile(conn)
            key = f"{pmid}:{profile.id}"
            previous = get(conn, "reviews", key)
            if (previous["revision"] if previous else 0) != update.revision:
                raise HTTPException(409, "Paper notes changed in another tab. Reload before editing.")
            review = Review(**update.model_dump(exclude={"revision"}), revision=update.revision + 1,
                            pmid=pmid, annotator_id=profile.id, updated_at=now())
            put(conn, "reviews", key, review.model_dump())
            return review

    def observation(self, conn, observation_id: str) -> Observation:
        data = get(conn, "observations", observation_id)
        if not data:
            raise HTTPException(404, "Observation not found.")
        return Observation.model_validate(data)

    def record(self, conn, observation: Observation):
        data = observation.model_dump()
        put(conn, "observations", observation.id, data)
        put(conn, "revisions", f"{observation.id}:{observation.revision}",
            {"observation": data, "editor": self.profile(conn).model_dump()})

    def create_observation(self, pmid: str, context_from=None, duplicate=False) -> Observation:
        with self.store.connection() as conn:
            profile = self.profile(conn)
            paper = get(conn, "papers", pmid)
            if not paper:
                raise HTTPException(404, "Paper not found.")
            fields = SchemaFields(pmid=pmid, author=paper["author"], paper_id=paper["paper_id"],
                                  pmcid=paper["pmcid"], date=date.today().strftime("%m/%d/%Y"))
            provenance = {}
            if context_from:
                previous = self.observation(conn, context_from)
                if previous.pmid != pmid:
                    raise HTTPException(422, "Reuse context from the same paper.")
                keys = list(SchemaFields.model_fields) if duplicate else CONTEXT
                for key in keys:
                    if key not in ("pmid", "date"):
                        setattr(fields, key, getattr(previous.fields, key))
                provenance["copied_from"] = previous.id
            observation = Observation(id=uid(), pmid=pmid, annotator_id=profile.id,
                                      annotator_name=profile.name, annotator_email=profile.email,
                                      fields=fields, revision=1, created_at=now(), updated_at=now(),
                                      versions=self.versions, provenance=provenance)
            self.record(conn, observation)
            return observation

    def validate_evidence(self, conn, observation: Observation):
        for evidence in observation.evidence:
            source_data = get(conn, "sources", evidence.source_id)
            if not source_data or source_data["pmid"] != observation.pmid:
                raise HTTPException(422, "Evidence must belong to this paper and a cached source version.")
            source = Source.model_validate(source_data)
            passage = next((p for p in source.passages if p.id == evidence.passage_id), None)
            if not passage or evidence.end > len(passage.text) or evidence.start >= evidence.end:
                raise HTTPException(422, "The evidence location is invalid.")
            if passage.text[evidence.start:evidence.end] != evidence.quote:
                raise HTTPException(422, "The evidence quotation does not match its cached passage.")
            if source.kind != "pmc":
                raise HTTPException(422, "Abstracts cannot supply Results or Methods evidence.")
            if passage.section != evidence.role and (passage.section != "uncertain" or not evidence.section_confirmed):
                raise HTTPException(422, "Select evidence from the appropriate section; confirm uncertain sections.")

    def save_observation(self, observation_id: str, update: Observation) -> Observation:
        with self.store.connection() as conn:
            previous = self.observation(conn, observation_id)
            for key in ("id", "pmid", "annotator_id", "annotator_name", "annotator_email", "created_at"):
                if getattr(update, key) != getattr(previous, key):
                    raise HTTPException(422, f"Cannot change observation {key}.")
            if update.revision != previous.revision:
                raise HTTPException(409, "This observation changed in another tab. Reload before editing.")
            if update.fields.pmid != update.pmid:
                raise HTTPException(422, "Observation PMID must match its paper.")
            # Original import and duplication provenance are server-owned.
            update.provenance = previous.provenance
            self.validate_evidence(conn, update)
            if update.status == "complete":
                errors = validate_fields(update.fields)
                for field in ("mutation", "phenotype", "date"):
                    if not getattr(update.fields, field).strip():
                        errors.append(f"{field.replace('_', ' ').capitalize()} is required for completion.")
                if not any(e.role == "results" for e in update.evidence):
                    errors.append("Results evidence is required for completion.")
                if errors:
                    raise HTTPException(422, errors)
            try:
                update.fields.date = normalize_date(update.fields.date)
            except ValueError:
                if update.status == "complete":
                    raise
            update.revision += 1
            update.updated_at = now()
            update.versions = self.versions
            self.record(conn, update)
            return update
