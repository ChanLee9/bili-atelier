from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class CollectionInspectRequest(BaseModel):
    url: HttpUrl


class DownloadRequest(BaseModel):
    source_url: HttpUrl
    quality_id: str = Field(min_length=1)
    episode_ids: list[str] = Field(default_factory=list)


class QualityOption(BaseModel):
    id: str
    label: str
    badge: str
    description: str


class EpisodeSummary(BaseModel):
    id: str
    index: int
    title: str
    duration_text: str
    source_url: HttpUrl
    thumbnail: str | None = None
    selected: bool = True


class CollectionSummary(BaseModel):
    title: str
    source_url: HttpUrl
    uploader: str | None = None
    thumbnail: str | None = None
    episode_count: int
    episodes: list[EpisodeSummary]
    quality_options: list[QualityOption]


class DownloadItem(BaseModel):
    episode_id: str
    title: str
    status: Literal["pending", "running", "completed", "failed"]
    output_path: str | None = None
    detail: str | None = None


class DownloadJobResponse(BaseModel):
    job_id: str
    status: Literal["queued", "running", "completed", "failed"]
    source_url: HttpUrl
    collection_title: str
    quality_id: str
    download_directory: str
    total_episodes: int
    completed_episodes: int
    failed_episodes: int
    progress_ratio: float
    items: list[DownloadItem]
    error: str | None = None
