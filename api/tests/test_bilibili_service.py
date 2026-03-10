from pathlib import Path

from api.app.services.bilibili import (
    QUALITY_BY_ID,
    build_download_command,
    episode_source_url,
    format_duration,
    inspect_collection,
    is_supported_bilibili_url,
)
from api.app.settings import AppSettings


class DummySettings(AppSettings):
    pass


def test_is_supported_bilibili_url() -> None:
    assert is_supported_bilibili_url("https://www.bilibili.com/video/BV1xx")
    assert is_supported_bilibili_url("https://space.bilibili.com/123/lists?sid=321")
    assert not is_supported_bilibili_url("https://example.com/video")


def test_format_duration() -> None:
    assert format_duration(65) == "01:05"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(None) == "--:--"


def test_episode_source_url_prefers_webpage_url() -> None:
    entry = {"webpage_url": "https://www.bilibili.com/video/BV123"}
    assert episode_source_url(entry, "https://fallback") == "https://www.bilibili.com/video/BV123"


def test_episode_source_url_handles_bilibili_part_ids() -> None:
    entry = {"id": "BV1abc123_p7"}
    assert episode_source_url(entry, "https://fallback") == "https://www.bilibili.com/video/BV1abc123?p=7"


def test_build_download_command_uses_quality_profile() -> None:
    settings = DummySettings(
        project_root=Path("D:/Projects/bili-atelier"),
        download_dir=Path("D:/Projects/bili-atelier/downloads"),
        yt_dlp_path="yt-dlp",
        ffmpeg_path="C:/My_Apps/TRCCCAP/ffmpeg.exe",
        max_download_workers=8,
        concurrent_fragments=6,
        allowed_origins=("http://127.0.0.1:5173",),
    )
    command = build_download_command(
        settings=settings,
        episode_url="https://www.bilibili.com/video/BV123",
        output_template="downloads/test.%(ext)s",
        quality_id="720p",
    )

    assert command[0] == "yt-dlp"
    assert "--format" in command
    assert QUALITY_BY_ID["720p"].format_selector in command
    assert "--concurrent-fragments" in command
    assert "6" in command
    assert "--ffmpeg-location" in command


def test_inspect_collection_transforms_payload(monkeypatch) -> None:
    settings = DummySettings(
        project_root=Path("D:/Projects/bili-atelier"),
        download_dir=Path("D:/Projects/bili-atelier/downloads"),
        yt_dlp_path="yt-dlp",
        ffmpeg_path=None,
        max_download_workers=8,
        concurrent_fragments=6,
        allowed_origins=("http://127.0.0.1:5173",),
    )

    def fake_command_json(_: list[str]) -> dict[str, object]:
        return {
            "title": "Sketchbook Series",
            "uploader": "atelier",
            "thumbnail": "https://image.example/cover.jpg",
            "entries": [
                {
                    "id": "BV001",
                    "title": "Episode 1",
                    "duration": 90,
                    "webpage_url": "https://www.bilibili.com/video/BV001",
                },
                {
                    "id": "BV002",
                    "title": "Episode 2",
                    "duration": 120,
                    "webpage_url": "https://www.bilibili.com/video/BV002",
                },
            ],
        }

    monkeypatch.setattr("api.app.services.bilibili.command_json", fake_command_json)

    result = inspect_collection("https://www.bilibili.com/video/BV000", settings)
    assert result["title"] == "Sketchbook Series"
    assert result["episode_count"] == 2
    assert result["episodes"][0]["duration_text"] == "01:30"
    assert result["quality_options"][2]["id"] == "720p"
