# Bili Atelier

Bili Atelier is a small full-stack app for inspecting a public Bilibili collection, choosing quality, selecting episodes, and downloading them into a local folder.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + `yt-dlp`
- Runtime downloads: `yt-dlp`, optional `ffmpeg`

## Project Layout

- `src/` - frontend app
- `api/` - FastAPI backend
- `docs/` - product and acceptance docs
- `downloads/` - local output folder created at runtime

## Run The Backend

```powershell
pip install -r api/requirements.txt
pnpm dev:api
```

## Run The Frontend

```powershell
pnpm install
pnpm dev:web
```

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`.

## One-Click Start

On Windows, double-click `start.bat` in the project root. It will:

- create `.venv` if needed
- install frontend dependencies when `node_modules` is missing
- sync backend Python dependencies when `api/requirements.txt` changes
- open separate terminal windows for the backend and frontend dev servers

## Notes

- This MVP is designed for public or authorized content only.
- The backend uses an in-memory job store, so job history resets when the server restarts.
- If `ffmpeg` is not in `PATH`, the backend also checks `C:\My_Apps\TRCCCAP\ffmpeg.exe`.
