"""Authoritative repository resources, copied into wheels by the build hook."""

import csv
import hashlib
import re
from pathlib import Path

from .models import Configuration, FieldDefinition

PACKAGE = Path(__file__).parent
ROOT = PACKAGE.parents[1]


def resource_path(name: str) -> Path:
    bundled = PACKAGE / "resources" / name
    return bundled if bundled.exists() else ROOT / name


def text_resource(name: str) -> str:
    return resource_path(name).read_text(encoding="utf-8-sig")


def versions() -> dict[str, str]:
    paths = ["protocol.md", "schema/schema.md", "schema/schema_template.csv", "decisions.md",
             "vocab/phenotype/standard.csv", "vocab/animal_model/standard.csv"]
    return {name: hashlib.sha256(resource_path(name).read_bytes()).hexdigest() for name in paths}


def configuration() -> Configuration:
    schema = text_resource("schema/schema.md")
    definitions = dict(re.findall(r"^## (\w+)\s*\n(.*?)(?=^## |\Z)", schema, re.MULTILINE | re.DOTALL))
    header = text_resource("schema/schema_template.csv").strip().split(",")
    vocabulary = {}
    for name in ("phenotype", "animal_model"):
        with resource_path(f"vocab/{name}/standard.csv").open(encoding="utf-8-sig") as stream:
            vocabulary[name] = sorted({row["standard_value"] for row in csv.DictReader(stream)
                                       if row.get("standard_value")})
    return Configuration(
        fields=[FieldDefinition(name=name, description=definitions.get(name, "").strip())
                for name in header], protocol=text_resource("protocol.md"),
        versions=versions(), vocabulary=vocabulary,
    )


def registry() -> dict[str, dict]:
    with resource_path("papers.csv").open(encoding="utf-8-sig", newline="") as stream:
        return {row["pmid"]: row for row in csv.DictReader(stream)}
