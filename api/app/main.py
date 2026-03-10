from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import CollectionInspectRequest, CollectionSummary, DownloadJobResponse, DownloadRequest
from .services.bilibili import JobStore, inspect_collection, launch_download_job, sanitize_filename
from .settings import get_settings


settings = get_settings()
job_store = JobStore()

app = FastAPI(
    title="Bili Atelier API",
    version="0.1.0",
    summary="Inspect and download public Bilibili collections for local archival workflows.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/collections/inspect", response_model=CollectionSummary)
def inspect(request: CollectionInspectRequest) -> CollectionSummary:
    return CollectionSummary.model_validate(inspect_collection(str(request.url), settings))


@app.post("/api/downloads", response_model=DownloadJobResponse)
def create_download(request: DownloadRequest) -> DownloadJobResponse:
    collection = inspect_collection(str(request.source_url), settings)
    selected_ids = set(request.episode_ids)
    episodes = [
        episode for episode in collection["episodes"] if not selected_ids or episode["id"] in selected_ids
    ]
    if not episodes:
        raise HTTPException(status_code=400, detail="请至少勾选一个分集后再开始下载。")

    collection_dir = Path(settings.download_dir) / sanitize_filename(collection["title"])
    collection_dir.mkdir(parents=True, exist_ok=True)
    items = [
        {
            "episode_id": episode["id"],
            "title": episode["title"],
            "status": "pending",
            "output_path": None,
            "detail": "排队中",
        }
        for episode in episodes
    ]

    job = job_store.create_job(
        source_url=str(request.source_url),
        collection_title=collection["title"],
        quality_id=request.quality_id,
        download_directory=collection_dir,
        items=items,
    )
    launch_download_job(
        store=job_store,
        settings=settings,
        job_id=job["job_id"],
        episodes=episodes,
        quality_id=request.quality_id,
        download_directory=collection_dir,
    )
    return DownloadJobResponse.model_validate(job_store.get_job(job["job_id"]))


@app.get("/api/downloads/{job_id}", response_model=DownloadJobResponse)
def get_download(job_id: str) -> DownloadJobResponse:
    return DownloadJobResponse.model_validate(job_store.get_job(job_id))
