import json

import httpx
import pytest
from fastapi.testclient import TestClient

from iav_annotator.app import create_app
from iav_annotator.bioc import parse_source


@pytest.mark.parametrize("shape", ["collection", "document", "list_documents"])
def test_supported_bioc_shapes_and_section_inheritance(bioc, shape):
    document = bioc[0]["documents"][0]
    document["passages"] = [
        {"text": "Results", "infons": {"type": "title_1"}},
        {"text": "A subsection", "infons": {"type": "title_2"}},
        {"text": "A finding", "infons": {"type": "paragraph"}},
        {"text": "Discussion", "infons": {"type": "title_1"}},
        {"text": "An interpretation", "infons": {"type": "paragraph"}},
    ]
    payload = {"collection": bioc, "document": document, "list_documents": [document]}[shape]
    result = parse_source("123", "pmc", json.dumps(payload), "https://example.test")
    assert result.passages[2].section == "results"
    assert result.passages[4].section == "other"


@pytest.mark.parametrize("mode,state", [("unavailable", "unavailable"), ("bad_json", "error"),
                                       ("timeout", "error"), ("throttled", "error")])
def test_pmc_failure_does_not_discard_pubmed(tmp_path, mode, state):
    calls = []

    def respond(request):
        if "pubmed.cgi" in str(request.url):
            return httpx.Response(200, json=[{"documents": [{"id": "123", "passages": [
                {"text": "An abstract", "infons": {"type": "abstract"}},
            ]}]}])
        calls.append(request)
        if mode == "timeout":
            raise httpx.ReadTimeout("Timeout", request=request)
        return {"unavailable": httpx.Response(404),
                "bad_json": httpx.Response(200, text="<html>upstream error</html>"),
                "throttled": httpx.Response(429)}[mode]

    with TestClient(create_app(tmp_path / "test.sqlite3", transport=httpx.MockTransport(respond))) as client:
        client.post("/api/profile", json={"name": "Test"})
        paper = client.post("/api/papers", json={"pmid": "123"}).json()
        assert paper["retrieval"]["pmc"]["state"] == state
        assert paper["passages"][0]["text"] == "An abstract"
        assert len(calls) == (3 if mode in ("timeout", "throttled") else 1)


def test_refresh_keeps_old_source_and_cached_read_needs_no_network(client, paper, bioc):
    original = paper["passages"][1]
    bioc[0]["documents"][0]["passages"][1]["text"] = "A corrected version."
    refreshed = client.post("/api/papers/123/retry").json()
    assert len(refreshed["sources"]) == 3  # unchanged PubMed is not duplicated
    old_source = client.get("/api/sources/" + original["source_id"]).json()
    assert old_source["passages"][1]["text"] == original["text"]
    assert client.get("/api/papers/123").json()["passages"][1]["text"] == "A corrected version."
    bioc[0]["documents"][0]["passages"][1]["text"] = original["text"]
    reverted = client.post("/api/papers/123/retry").json()
    assert reverted["passages"][1]["text"] == original["text"]
    assert len(reverted["sources"]) == 3


def test_paper_list_returns_summaries_without_article_payloads(client, paper):
    summary = client.get("/api/papers").json()[0]
    assert summary["pmid"] == "123"
    assert summary["passages"] == []
    assert summary["sources"] == []


def test_abstract_cannot_be_relabeled_as_results(client, paper):
    observation = client.post("/api/papers/123/observations", json={}).json()
    source_id = next(s["id"] for s in paper["sources"] if s["kind"] == "pubmed")
    passage = client.get("/api/sources/" + source_id).json()["passages"][1]
    observation["evidence"] = [{"source_id": source_id, "passage_id": passage["id"],
                               "start": 0, "end": len(passage["text"]), "quote": passage["text"],
                               "role": "results", "section_confirmed": True}]
    assert client.put("/api/observations/" + observation["id"], json=observation).status_code == 422


@pytest.mark.parametrize("section", ["INTRO", "DISCUSS", "REF", "CONCL", "SUPPL"])
def test_known_non_evidence_bioc_sections_are_not_offered_for_confirmation(section):
    payload = {"passages": [{"text": "Not Results evidence", "infons": {
        "type": "paragraph", "section_type": section,
    }}]}
    source = parse_source("123", "pmc", json.dumps(payload), "https://example.test")
    assert source.passages[0].section == "other"


def test_identifier_metadata_is_filled_for_unregistered_papers(client, profile, bioc):
    bioc[0]["documents"][0]["passages"][0]["infons"].update({
        "article-id_doi": "10.0000/fictional-test", "article-id_pmc": "PMC123",
    })
    paper = client.post("/api/papers", json={"pmid": "123"}).json()
    assert paper["doi"] == "10.0000/fictional-test"
    assert paper["pmcid"] == "PMC123"
