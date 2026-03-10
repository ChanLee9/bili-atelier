from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


KNOWN_FFMPEG_PATHS = [
    Path(r"C:\My_Apps\TRCCCAP\ffmpeg.exe"),
]


@dataclass(frozen=True)
class AppSettings:
    project_root: Path
    download_dir: Path
    yt_dlp_path: str
    ffmpeg_path: str | None
    max_download_workers: int
    concurrent_fragments: int
    allowed_origins: tuple[str, ...]


def _resolve_ffmpeg() -> str | None:
    env_value = os.environ.get("BILI_ATELIER_FFMPEG_PATH")
    if env_value and Path(env_value).exists():
        return env_value

    for candidate in KNOWN_FFMPEG_PATHS:
        if candidate.exists():
            return str(candidate)

    return None


def get_settings() -> AppSettings:
    project_root = Path(__file__).resolve().parents[2]
    download_dir = Path(
        os.environ.get("BILI_ATELIER_DOWNLOAD_DIR", project_root / "downloads")
    )
    logical_cores = os.cpu_count() or 8
    default_workers = max(4, min(10, logical_cores // 2))
    default_fragments = max(4, min(8, logical_cores // 3))
    return AppSettings(
        project_root=project_root,
        download_dir=download_dir,
        yt_dlp_path=os.environ.get("BILI_ATELIER_YT_DLP", "yt-dlp"),
        ffmpeg_path=_resolve_ffmpeg(),
        max_download_workers=int(os.environ.get("BILI_ATELIER_MAX_DOWNLOAD_WORKERS", default_workers)),
        concurrent_fragments=int(os.environ.get("BILI_ATELIER_CONCURRENT_FRAGMENTS", default_fragments)),
        allowed_origins=("http://127.0.0.1:5173", "http://localhost:5173"),
    )
