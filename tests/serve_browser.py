"""Isolated browser-test server with fictional article fixtures; never contacts NCBI."""

import sys
from pathlib import Path
from uuid import uuid4

import httpx
import uvicorn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from iav_annotator.app import create_app


def respond(request):
    pmid = request.url.path.split("/")[-2]
    if "pmcoa" in str(request.url) and pmid == "124":
        return httpx.Response(404)
    fulltext = "pmcoa" in str(request.url)
    passages = [
        {"text": "A fictional article for interface testing", "infons": {"type": "title"}},
        {"text": "This is an abstract for screening.", "infons": {"type": "abstract"}},
    ]
    if fulltext:
        passages += [
            {"text": "An observed difference. α🙂 An observed difference.",
             "infons": {"type": "paragraph", "section_type": "RESULTS"}},
            {"text": "The experimental system was described here.",
             "infons": {"type": "paragraph", "section_type": "METHODS"}},
            {"text": "A table supplied with the article.",
             "infons": {"type": "table_caption", "section_type": "RESULTS"}},
        ]
    return httpx.Response(200, json=[{"documents": [{"id": "PMC123" if fulltext else pmid,
                                                   "passages": passages}]}])


app = create_app(ROOT / ".artifacts" / f"browser-tests-{uuid4()}.sqlite3", transport=httpx.MockTransport(respond))
uvicorn.run(app, host="127.0.0.1", port=8766, log_level="warning")
