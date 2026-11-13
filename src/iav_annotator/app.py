import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import __version__
from .db import Store, all_rows, get
from .exchange import apply_import, export_bundle, preview_import, repository_imports
from .models import (
    Configuration,
    ImportPreview,
    ImportRequest,
    Observation,
    ObservationInput,
    Paper,
    PMIDInput,
    Profile,
    ProfileInput,
    Review,
    ReviewInput,
    Source,
)
from .resources import PACKAGE, configuration
from .service import Service


def default_database() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
    return base / "IAVAnnotator" / "annotations.sqlite3"


def create_app(database: Path | None = None, *, transport=None) -> FastAPI:
    app = FastAPI(title="IAV Annotator", version=__version__)
    store = Store(database or Path(os.environ.get("IAV_ANNOTATOR_DB", default_database())))
    service = Service(store, transport)
    app_config = configuration()
    app.state.store = store
    app.state.service = service

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        # Loopback binding plus host/origin checks prevent cross-site writes and DNS rebinding.
        host = request.url.hostname
        if host not in ("127.0.0.1", "localhost", "::1", "testserver"):
            return JSONResponse({"detail": "Use the local application address."}, status_code=403)
        origin = request.headers.get("origin")
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"detail": "Cross-origin writes are not allowed."}, status_code=403)
            if request.headers.get("sec-fetch-site") == "cross-site":
                return JSONResponse({"detail": "Cross-site writes are not allowed."}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    @app.get("/api/config", response_model=Configuration)
    def config():
        return app_config

    @app.get("/api/profile", response_model=Profile | None)
    def profile():
        with store.connection() as conn:
            if not get(conn, "settings", "active_profile"):
                return None
            return service.profile(conn)

    @app.post("/api/profile", response_model=Profile)
    def save_profile(data: ProfileInput):
        return service.save_profile(data)

    @app.get("/api/papers", response_model=list[Paper])
    def papers():
        return service.list_papers()

    @app.post("/api/papers", response_model=Paper)
    async def retrieve(data: PMIDInput):
        return await service.retrieve(data.pmid)

    @app.get("/api/papers/{pmid}", response_model=Paper)
    def paper(pmid: str):
        return service.paper(pmid)

    @app.post("/api/papers/{pmid}/retry", response_model=Paper)
    async def retry(pmid: str):
        try:
            value = PMIDInput(pmid=pmid)
        except ValidationError as exc:
            raise HTTPException(422, "PMID must contain digits only.") from exc
        return await service.retrieve(value.pmid)

    @app.put("/api/papers/{pmid}/review", response_model=Review)
    def save_review(pmid: str, data: ReviewInput):
        return service.review(pmid, data)

    @app.get("/api/sources/{source_id}", response_model=Source)
    def source(source_id: str):
        with store.connection() as conn:
            data = get(conn, "sources", source_id)
            if not data:
                raise HTTPException(404, "Source version not found.")
            return data

    @app.get("/api/papers/{pmid}/observations", response_model=list[Observation])
    def observations(pmid: str):
        with store.connection() as conn:
            return [o for o in all_rows(conn, "observations") if o["pmid"] == pmid]

    @app.post("/api/papers/{pmid}/observations", response_model=Observation)
    def create_observation(pmid: str, data: ObservationInput):
        return service.create_observation(pmid, data.context_from)

    @app.get("/api/observations/{observation_id}", response_model=Observation)
    def observation(observation_id: str):
        with store.connection() as conn:
            return service.observation(conn, observation_id)

    @app.put("/api/observations/{observation_id}", response_model=Observation)
    def save_observation(observation_id: str, data: Observation):
        return service.save_observation(observation_id, data)

    @app.post("/api/observations/{observation_id}/duplicate", response_model=Observation)
    def duplicate(observation_id: str):
        with store.connection() as conn:
            observation = service.observation(conn, observation_id)
        return service.create_observation(observation.pmid, observation_id, duplicate=True)

    @app.get("/api/observations/{observation_id}/revisions")
    def revisions(observation_id: str):
        with store.connection() as conn:
            service.observation(conn, observation_id)
            return [r for r in all_rows(conn, "revisions") if r["observation"]["id"] == observation_id]

    @app.post("/api/import/preview", response_model=ImportPreview)
    def import_preview(data: ImportRequest):
        return preview_import(data, service)

    @app.post("/api/import/apply", response_model=ImportPreview)
    def import_apply(data: ImportRequest):
        return apply_import(data, service)

    @app.get("/api/import/repository", response_model=list[ImportRequest])
    def import_repository():
        return repository_imports()

    @app.get("/api/export")
    def export(completed_only: bool = False):
        return Response(export_bundle(service, completed_only), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="iav-annotations.zip"'})

    @app.get("/api/backup")
    def backup():
        return Response(store.backup(), media_type="application/octet-stream",
                        headers={"Content-Disposition": 'attachment; filename="iav-backup.sqlite3"'})

    @app.post("/api/restore")
    async def restore(request: Request):
        chunks, size = [], 0
        async for chunk in request.stream():
            size += len(chunk)
            if size > 250_000_000:
                raise HTTPException(413, "Backup exceeds the 250 MB restore limit.")
            chunks.append(chunk)
        try:
            store.restore(b"".join(chunks))
            service.remember_resources()
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"restored": True}

    static = PACKAGE / "static"
    if (static / "index.html").is_file():
        # https://fastapi.tiangolo.com/tutorial/static-files/
        app.mount("/", StaticFiles(directory=static, html=True), name="frontend")
    return app
