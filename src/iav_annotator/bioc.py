"""BioC adapters. Raw text is preserved; offsets count Unicode code points."""

import asyncio
import hashlib
import json
import re
from dataclasses import dataclass

import httpx

from .db import now, uid
from .models import Passage, Source

BASE = "https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful"


@dataclass
class Retrieval:
    state: str
    message: str
    source: Source | None = None


def documents(payload) -> list[dict]:
    if isinstance(payload, dict) and isinstance(payload.get("documents"), list):
        return payload["documents"]
    if isinstance(payload, dict) and isinstance(payload.get("passages"), list):
        return [payload]
    if isinstance(payload, list):
        docs = []
        for item in payload:
            docs.extend(documents(item))
        return docs
    raise ValueError("Unexpected BioC document structure")


def section_label(value: str) -> str:
    value = re.sub(r"[^a-z]+", " ", value.lower()).strip()
    if "result" in value and ("discussion" in value or "method" in value):
        return "uncertain"
    if re.search(r"\bresults?\b", value):
        return "results"
    if re.search(r"\b(methods?|materials|experimental procedures)\b", value):
        return "methods"
    if "abstract" in value:
        return "abstract"
    if value in {"intro", "discuss", "ref", "concl", "suppl", "comp int", "auth cont"} or any(
        word in value for word in ("introduction", "discussion", "conclusion", "reference",
                                  "background", "acknowledg", "funding", "title", "supplement")
    ):
        return "other"
    return "uncertain"


def parse_source(pmid: str, kind: str, raw: str, url: str) -> Source:
    docs = documents(json.loads(raw))
    if not docs or not any(doc.get("passages") for doc in docs):
        raise LookupError("No BioC passages are available")
    source_id = uid()
    passages = []
    for doc_index, doc in enumerate(docs):
        current = "uncertain"
        heading = ""
        for index, passage in enumerate(doc.get("passages", [])):
            text = passage.get("text", "")
            if not isinstance(text, str):
                raise TypeError("BioC passage text is not a string")
            infons = passage.get("infons") or {}
            passage_type = str(infons.get("type", "")).lower()
            section_type = str(infons.get("section_type", ""))
            is_heading = passage_type in ("title_1", "title_2", "title_3", "section_title")
            if is_heading:
                classification = section_label(section_type or text)
                # Subheadings inherit a known section; top-level headings reset it.
                if passage_type not in ("title_2", "title_3") or classification not in ("other", "uncertain"):
                    current = classification
                heading = text
            label = section_label(section_type) if section_type else current
            if "abstract" in passage_type:
                label = "abstract"
            elif passage_type in ("title", "front"):
                label = "title"
            if kind == "pubmed" and label not in ("title", "abstract"):
                label = "abstract"
            if not text:
                continue
            passages.append(Passage(id=f"{source_id}:{doc_index}:{index}", source_id=source_id,
                                    text=text, section=label, heading=heading,
                                    offset=int(passage.get("offset", 0)), infons=infons))
    if not passages:
        raise LookupError("No readable BioC passages are available")
    return Source(id=source_id, pmid=pmid, kind=kind, url=url, retrieved_at=now(),
                  hash=hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw=raw, passages=passages)


async def fetch_source(pmid: str, kind: str, transport=None) -> Retrieval:
    endpoint = "pubmed" if kind == "pubmed" else "pmcoa"
    url = f"{BASE}/{endpoint}.cgi/BioC_json/{pmid}/unicode"
    # API references: https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PubMed/
    # and https://www.ncbi.nlm.nih.gov/research/bionlp/APIs/BioC-PMC/
    async with httpx.AsyncClient(transport=transport, timeout=20, follow_redirects=True,
                                 headers={"User-Agent": "IAV-Annotator/0.1 (local curation)"}) as client:
        for attempt in range(3):
            try:
                response = await client.get(url)
                if response.status_code in (404, 410):
                    return Retrieval("unavailable", "No article is available from this BioC service.")
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < 2:
                        await asyncio.sleep(0.3 * 2**attempt)
                        continue
                    return Retrieval("error", f"NCBI returned HTTP {response.status_code}; retry later.")
                response.raise_for_status()
                raw = response.text
                # NCBI sometimes returns a plain-text unavailability message with HTTP 200.
                if re.search(r"^(?:error\s*:\s*)?(?:no (?:result|record|document|article)|\[error\]|not available)",
                             raw.strip(), re.IGNORECASE):
                    return Retrieval("unavailable", "No article is available from this BioC service.")
                source = parse_source(pmid, kind, raw, url)
                return Retrieval("available", "Cached locally.", source)
            except LookupError as exc:
                return Retrieval("unavailable", str(exc))
            except (ValueError, TypeError, KeyError) as exc:
                return Retrieval("error", f"The BioC response could not be read: {exc}")
            except httpx.HTTPError:
                if attempt < 2:
                    await asyncio.sleep(0.3 * 2**attempt)
                else:
                    return Retrieval("error", "Could not reach NCBI. Cached articles remain available; retry later.")
    return Retrieval("error", "Retrieval did not finish.")
