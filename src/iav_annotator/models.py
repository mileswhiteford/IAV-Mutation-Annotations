from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileInput(StrictModel):
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(default="", max_length=254)


class Profile(ProfileInput):
    id: str


class SchemaFields(StrictModel):
    author: str = ""
    paper_id: str = ""
    pmid: str = ""
    pmcid: str = ""
    backbone: str = ""
    recombinant: str = ""
    subtype: str = ""
    protein: str = ""
    mutation: str = ""
    numbering: str = ""
    phenotype: str = ""
    cell_type: str = ""
    animal_model: str = ""
    binding_assay: str = ""
    temperature: str = ""
    notes: str = ""
    date: str = ""


class Evidence(StrictModel):
    source_id: str
    passage_id: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)
    role: Literal["results", "methods"]
    section_confirmed: bool = False


class Observation(StrictModel):
    id: str
    pmid: str
    annotator_id: str
    annotator_name: str
    annotator_email: str = ""
    status: Literal["draft", "complete", "legacy"] = "draft"
    fields: SchemaFields
    evidence: list[Evidence] = Field(default_factory=list)
    review_flag: bool = False
    revision: int = Field(ge=1)
    created_at: str
    updated_at: str
    versions: dict[str, str]
    provenance: dict = Field(default_factory=dict)


class ObservationInput(StrictModel):
    context_from: str | None = None


class ReviewInput(StrictModel):
    progress: Literal["in_progress", "deferred", "no_eligible", "finished"] = "in_progress"
    notes: str = Field(default="", max_length=100000)
    revision: int = Field(default=0, ge=0)


class Review(ReviewInput):
    pmid: str = ""
    annotator_id: str = ""
    updated_at: str = ""


class PMIDInput(StrictModel):
    pmid: str = Field(pattern=r"^[1-9][0-9]{0,11}$")


class Passage(StrictModel):
    id: str
    source_id: str
    text: str
    section: Literal["results", "methods", "abstract", "title", "other", "uncertain"]
    heading: str = ""
    offset: int = 0
    infons: dict = Field(default_factory=dict)


class Source(StrictModel):
    id: str
    pmid: str
    kind: Literal["pubmed", "pmc"]
    url: str
    retrieved_at: str
    hash: str
    raw: str
    passages: list[Passage]


class Paper(StrictModel):
    pmid: str
    title: str = ""
    pmcid: str = ""
    paper_id: str = ""
    author: str = ""
    doi: str = ""
    citation: str = ""
    current_sources: dict[str, str] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    retrieval: dict[str, dict] = Field(default_factory=dict)
    passages: list[Passage] = Field(default_factory=list)
    review: Review = Field(default_factory=Review)
    observation_count: int = 0


class ImportRequest(StrictModel):
    csv: str = Field(max_length=20_000_000)
    annotator: str = Field(default="", max_length=200)
    filename: str = Field(default="import.csv", max_length=1000)


class ImportRow(StrictModel):
    line: int
    fields: SchemaFields
    annotator_id: str
    annotator_name: str
    annotator_email: str = ""
    observation_id: str
    warnings: list[str]
    errors: list[str]
    original: dict


class ImportPreview(StrictModel):
    rows: list[ImportRow]
    errors: list[str] = Field(default_factory=list)
    imported: int = 0
    skipped: int = 0


class FieldDefinition(StrictModel):
    name: str
    description: str


class Configuration(StrictModel):
    fields: list[FieldDefinition]
    protocol: str
    versions: dict[str, str]
    vocabulary: dict[str, list[str]]
