from __future__ import annotations

import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import HTTPException

from ..settings import AppSettings


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


@dataclass(frozen=True)
class QualityProfile:
    id: str
    label: str
    badge: str
    description: str
    format_selector: str


QUALITY_PROFILES = [
    QualityProfile(
        id="360p",
        label="360p",
        badge="轻量",
        description="体积更小，适合快速保存和轻量离线查看。",
        format_selector="bestvideo*[height<=360]+bestaudio/best[height<=360]/best",
    ),
    QualityProfile(
        id="480p",
        label="480p",
        badge="均衡",
        description="清晰度和文件体积比较平衡，适合大多数收藏场景。",
        format_selector="bestvideo*[height<=480]+bestaudio/best[height<=480]/best",
    ),
    QualityProfile(
        id="720p",
        label="720p",
        badge="推荐",
        description="画质和体积更均衡，适合作为默认下载选择。",
        format_selector="bestvideo*[height<=720]+bestaudio/best[height<=720]/best",
    ),
    QualityProfile(
        id="1080p",
        label="1080p",
        badge="高画质",
        description="适合希望保留更高细节的离线观看体验。",
        format_selector="bestvideo*[height<=1080]+bestaudio/best[height<=1080]/best",
    ),
    QualityProfile(
        id="best",
        label="最佳可用",
        badge="极致",
        description="尽量获取当前内容可访问到的最佳画质和音频。",
        format_selector="bestvideo+bestaudio/best",
    ),
]

QUALITY_BY_ID = {profile.id: profile for profile in QUALITY_PROFILES}


def is_supported_bilibili_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host == "b23.tv" or host.endswith(".b23.tv") or host.endswith("bilibili.com")


def format_duration(seconds: int | None) -> str:
    if not seconds:
        return "--:--"
    minutes, remaining = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minutes:02d}:{remaining:02d}"
    return f"{minutes:02d}:{remaining:02d}"


def sanitize_filename(value: str) -> str:
    cleaned = INVALID_FILENAME.sub(" ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(". ")
    return cleaned[:100] or "untitled"


def episode_source_url(entry: dict[str, Any], fallback_url: str) -> str:
    direct_url = entry.get("webpage_url") or entry.get("original_url")
    if direct_url:
        return str(direct_url)

    http_headers = entry.get("http_headers")
    if isinstance(http_headers, dict):
        referer = http_headers.get("Referer") or http_headers.get("referer")
        if isinstance(referer, str) and referer.startswith(("http://", "https://")):
            return referer

    raw_url = entry.get("url") or entry.get("id") or entry.get("display_id")
    if isinstance(raw_url, str):
        if raw_url.startswith("http://") or raw_url.startswith("https://"):
            return raw_url
        if "_p" in raw_url and raw_url.startswith("BV"):
            base_id, _, part = raw_url.partition("_p")
            if part.isdigit():
                return f"https://www.bilibili.com/video/{base_id}?p={part}"
        if raw_url.startswith("BV"):
            return f"https://www.bilibili.com/video/{raw_url}"

    return fallback_url


def parse_download_output_paths(stdout: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        candidate = line.strip()
        if not candidate or candidate in seen:
            continue
        paths.append(candidate)
        seen.add(candidate)
    return paths


def command_json(command: list[str], *, timeout: float | None = None) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="调用 yt-dlp 超时，请稍后重试。") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown yt-dlp error"
        raise HTTPException(status_code=400, detail=stderr)

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="解析 yt-dlp 返回结果失败，请稍后重试。",
        ) from exc


def inspect_collection(url: str, settings: AppSettings) -> dict[str, Any]:
    if not is_supported_bilibili_url(url):
        raise HTTPException(status_code=400, detail="请输入有效的 bilibili.com 或 b23.tv 链接。")

    try:
        payload = command_json(
            [
                settings.yt_dlp_path,
                "--dump-single-json",
                "--no-warnings",
                url,
            ],
            timeout=15,
        )
    except HTTPException:
        payload = command_json(
            [
                settings.yt_dlp_path,
                "--dump-single-json",
                "--flat-playlist",
                "--no-warnings",
                url,
            ],
            timeout=15,
        )

    raw_entries = payload.get("entries") or [payload]
    primary_entry = raw_entries[0] if raw_entries else payload
    episodes: list[dict[str, Any]] = []
    for index, entry in enumerate(raw_entries, start=1):
        episode_id = str(entry.get("id") or entry.get("display_id") or index)
        episodes.append(
            {
                "id": episode_id,
                "index": index,
                "title": str(entry.get("title") or f"第 {index} 集"),
                "duration_text": format_duration(entry.get("duration")),
                "source_url": episode_source_url(entry, str(payload.get("webpage_url") or url)),
                "thumbnail": entry.get("thumbnail") or payload.get("thumbnail"),
                "selected": True,
            }
        )

    return {
        "title": str(payload.get("title") or "Untitled Collection"),
        "source_url": str(payload.get("webpage_url") or url),
        "uploader": payload.get("uploader") or payload.get("channel") or primary_entry.get("uploader"),
        "thumbnail": payload.get("thumbnail") or primary_entry.get("thumbnail"),
        "episode_count": len(episodes),
        "episodes": episodes,
        "quality_options": [
            {
                "id": profile.id,
                "label": profile.label,
                "badge": profile.badge,
                "description": profile.description,
            }
            for profile in QUALITY_PROFILES
        ],
    }


def build_download_command(
    *,
    settings: AppSettings,
    episode_url: str,
    output_template: str,
    quality_id: str,
) -> list[str]:
    profile = QUALITY_BY_ID.get(quality_id)
    if profile is None:
        raise HTTPException(status_code=400, detail=f"不支持的清晰度选项：{quality_id}")

    command = [
        settings.yt_dlp_path,
        episode_url,
        "--format",
        profile.format_selector,
        "--concurrent-fragments",
        str(settings.concurrent_fragments),
        "--merge-output-format",
        "mp4",
        "--no-warnings",
        "--print",
        "after_move:filepath",
        "--output",
        output_template,
    ]
    if settings.ffmpeg_path:
        command.extend(["--ffmpeg-location", settings.ffmpeg_path])
    return command


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def create_job(
        self,
        *,
        source_url: str,
        collection_title: str,
        quality_id: str,
        download_directory: Path,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        job_id = uuid4().hex[:10]
        job = {
            "job_id": job_id,
            "status": "queued",
            "source_url": source_url,
            "collection_title": collection_title,
            "quality_id": quality_id,
            "download_directory": str(download_directory),
            "total_episodes": len(items),
            "completed_episodes": 0,
            "failed_episodes": 0,
            "progress_ratio": 0.0,
            "items": items,
            "error": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        return job.copy()

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise HTTPException(status_code=404, detail="Download job not found.")
            return json.loads(json.dumps(job))

    def update_item(
        self,
        job_id: str,
        episode_id: str,
        *,
        status: str,
        output_path: str | None = None,
        detail: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for item in job["items"]:
                if item["episode_id"] == episode_id:
                    item["status"] = status
                    item["output_path"] = output_path
                    item["detail"] = detail
                    break

            completed = sum(1 for item in job["items"] if item["status"] == "completed")
            failed = sum(1 for item in job["items"] if item["status"] == "failed")
            total = job["total_episodes"] or 1
            job["completed_episodes"] = completed
            job["failed_episodes"] = failed
            job["progress_ratio"] = round((completed + failed) / total, 3)

            if completed + failed == job["total_episodes"]:
                job["status"] = "failed" if failed and completed == 0 else "completed"
            elif any(item["status"] == "running" for item in job["items"]):
                job["status"] = "running"

    def fail_job(self, job_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "failed"
            job["error"] = message


def launch_download_job(
    *,
    store: JobStore,
    settings: AppSettings,
    job_id: str,
    episodes: list[dict[str, Any]],
    quality_id: str,
    download_directory: Path,
) -> None:
    def run() -> None:
        if settings.ffmpeg_path is None:
            detail = "未找到 ffmpeg，无法把 Bilibili 的音频和视频合并成单个文件。请先安装 ffmpeg，或重新安装后端依赖后再试。"
            for episode in episodes:
                store.update_item(job_id, episode["id"], status="failed", detail=detail)
            store.fail_job(job_id, detail)
            return

        def process_episode(episode: dict[str, Any]) -> None:
            episode_id = episode["id"]
            safe_title = sanitize_filename(f"{episode['index']:02d}-{episode['title']}")
            output_template = str(download_directory / f"{safe_title}.%(ext)s")
            store.update_item(job_id, episode_id, status="running", detail="正在下载")
            command = build_download_command(
                settings=settings,
                episode_url=episode["source_url"],
                output_template=output_template,
                quality_id=quality_id,
            )
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode != 0:
                detail = completed.stderr.strip() or completed.stdout.strip() or "下载失败"
                store.update_item(job_id, episode_id, status="failed", detail=detail)
                return

            output_paths = parse_download_output_paths(completed.stdout)
            if len(output_paths) != 1:
                detail = "下载完成，但未能生成单个带声音的视频文件，请检查 ffmpeg 是否可用。"
                store.update_item(job_id, episode_id, status="failed", detail=detail)
                return

            output_path = output_paths[0]
            if not Path(output_path).exists():
                detail = "下载已结束，但无法定位最终输出文件。"
                store.update_item(job_id, episode_id, status="failed", detail=detail)
                return

            detail = completed.stderr.strip() or "已保存"
            store.update_item(
                job_id,
                episode_id,
                status="completed",
                output_path=output_path,
                detail=detail,
            )

        try:
            with ThreadPoolExecutor(max_workers=settings.max_download_workers) as executor:
                futures = [executor.submit(process_episode, episode) for episode in episodes]
                for future in futures:
                    future.result()
        except HTTPException as exc:
            store.fail_job(job_id, str(exc.detail))
        except Exception as exc:  # pragma: no cover
            store.fail_job(job_id, str(exc))

    Thread(target=run, daemon=True).start()
