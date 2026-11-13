from fastapi.testclient import TestClient

from iav_annotator.app import create_app


def test_profile_draft_and_notes_survive_restart(client, profile, paper):
    result = client.post("/api/papers/123/observations", json={})
    assert result.status_code == 200
    observation = result.json()
    assert observation["annotator_id"] == profile["id"]
    assert observation["fields"]["paper_id"] == ""
    assert observation["status"] == "draft"
    assert client.put("/api/papers/123/review", json={
        "progress": "deferred", "notes": "Read later", "revision": 0,
    }).status_code == 200
    with TestClient(create_app(client.app.state.store.path)) as reopened:
        assert reopened.get("/api/profile").json()["id"] == profile["id"]
        assert reopened.get("/api/papers/123").json()["review"]["notes"] == "Read later"
        assert reopened.get(f'/api/observations/{observation["id"]}').json() == observation


def test_completion_evidence_duplication_and_conflict(client, paper):
    observation = client.post("/api/papers/123/observations", json={}).json()
    url = f'/api/observations/{observation["id"]}'
    observation["fields"].update(mutation="TEST:A1G", phenotype="No observed difference")
    observation["status"] = "complete"
    assert client.put(url, json=observation).status_code == 422
    passage = next(p for p in paper["passages"] if p["section"] == "results")
    text = passage["text"]
    start = text.rindex("An observed difference.")
    observation["evidence"] = [{"source_id": passage["source_id"], "passage_id": passage["id"],
                               "start": start, "end": len(text), "quote": text[start:],
                               "role": "results", "section_confirmed": False}]
    saved = client.put(url, json=observation)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    assert client.put(url, json=observation).status_code == 409
    duplicate = client.post(url + "/duplicate").json()
    assert duplicate["id"] != observation["id"]
    assert duplicate["status"] == "draft"
    assert duplicate["evidence"] == []
    assert duplicate["fields"]["phenotype"] == observation["fields"]["phenotype"]


def test_methods_cannot_substitute_for_results(client, paper):
    observation = client.post("/api/papers/123/observations", json={}).json()
    passage = next(p for p in paper["passages"] if p["section"] == "methods")
    observation["fields"].update(mutation="TEST:A1G", phenotype="An observation")
    observation["status"] = "complete"
    evidence = {"source_id": passage["source_id"], "passage_id": passage["id"], "start": 0,
                "end": len(passage["text"]), "quote": passage["text"], "role": "methods"}
    observation["evidence"] = [evidence]
    assert client.put(f'/api/observations/{observation["id"]}', json=observation).status_code == 422
    evidence.update(role="results", section_confirmed=True)
    assert client.put(f'/api/observations/{observation["id"]}', json=observation).status_code == 422


def test_invalid_pmid_and_cross_origin_writes_are_rejected(client, profile):
    assert client.post("/api/papers", json={"pmid": "https://example.org"}).status_code == 422
    assert client.post("/api/profile", json={"name": "Other"},
                       headers={"Origin": "https://untrusted.example"}).status_code == 403
    assert client.post("/api/papers/not-a-pmid/retry").status_code == 422


def test_evidence_offsets_and_same_paper_are_checked(client, paper):
    observation = client.post("/api/papers/123/observations", json={}).json()
    passage = next(p for p in paper["passages"] if p["section"] == "results")
    evidence = {"source_id": passage["source_id"], "passage_id": passage["id"],
                "start": 1, "end": 10, "quote": "incorrect", "role": "results"}
    observation["evidence"] = [evidence]
    assert client.put("/api/observations/" + observation["id"], json=observation).status_code == 422
    evidence.update(start=0, end=len(passage["text"]), quote=passage["text"])
    assert client.put("/api/observations/" + observation["id"], json=observation).status_code == 200


def test_uncertain_section_requires_explicit_confirmation(client, paper, bioc):
    bioc[0]["documents"][0]["passages"].append({
        "text": "An unclassified passage", "infons": {"type": "paragraph", "section_type": "UNKNOWN"},
    })
    refreshed = client.post("/api/papers/123/retry").json()
    observation = client.post("/api/papers/123/observations", json={}).json()
    passage = next(p for p in refreshed["passages"] if p["section"] == "uncertain")
    observation["evidence"] = [{"source_id": passage["source_id"], "passage_id": passage["id"],
                               "start": 0, "end": len(passage["text"]), "quote": passage["text"],
                               "role": "results"}]
    url = "/api/observations/" + observation["id"]
    assert client.put(url, json=observation).status_code == 422
    observation["evidence"][0]["section_confirmed"] = True
    assert client.put(url, json=observation).status_code == 200


def test_edits_to_legacy_records_preserve_owner_and_record_editor(client, paper):
    imported = client.post("/api/import/apply", json={
        "csv": "pmid,mutation,phenotype\n123,TEST:A1G,A recorded observation\n",
        "annotator": "Original contributor",
    })
    assert imported.status_code == 200
    observation = client.get("/api/papers/123/observations").json()[0]
    observation["fields"]["notes"] = "Reviewed by another contributor"
    saved = client.put("/api/observations/" + observation["id"], json=observation).json()
    assert saved["annotator_name"] == "Original contributor"
    history = client.get(f'/api/observations/{observation["id"]}/revisions').json()
    assert history[-1]["editor"]["name"] == "Researcher"
