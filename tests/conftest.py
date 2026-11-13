import httpx
import pytest
from fastapi.testclient import TestClient

from iav_annotator.app import create_app


@pytest.fixture
def bioc():
    return [{"documents": [{"id": "PMC123", "infons": {"pmid": "123"}, "passages": [
        {"offset": 0, "infons": {"type": "title"}, "text": "A test article"},
        {"offset": 20, "infons": {"section_type": "RESULTS", "type": "paragraph"},
         "text": "An observed difference. α🙂 An observed difference."},
        {"offset": 90, "infons": {"section_type": "METHODS", "type": "paragraph"},
         "text": "An experimental context."},
    ]}]}]


@pytest.fixture
def client(tmp_path, bioc):
    def respond(request):
        if "pubmed.cgi" in str(request.url):
            return httpx.Response(200, json=[{"documents": [{"id": "123", "passages": [
                {"infons": {"type": "title"}, "text": "A test article"},
                {"infons": {"type": "abstract"}, "text": "Screening only."},
            ]}]}])
        return httpx.Response(200, json=bioc)

    app = create_app(tmp_path / "annotations.sqlite3", transport=httpx.MockTransport(respond))
    with TestClient(app) as c:
        yield c


@pytest.fixture
def profile(client):
    result = client.post("/api/profile", json={"name": "Researcher", "email": ""})
    assert result.status_code == 200
    return result.json()


@pytest.fixture
def paper(client, profile):
    result = client.post("/api/papers", json={"pmid": "123"})
    assert result.status_code == 200
    return result.json()
