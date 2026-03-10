# Bili Atelier Spec

## Product Vision

Bili Atelier is a desktop-first web app for collecting publicly accessible Bilibili series or multi-part videos into a tidy local archive. The experience should feel calm, premium, and intentional: light surfaces, vivid accents, strong typography, and a gallery-like selection flow.

## Primary User Flow

1. Paste a Bilibili collection or multi-part video URL.
2. Inspect the collection and fetch episode metadata.
3. Review the available episodes.
4. Choose a quality preset.
5. Select some or all episodes.
6. Start the download job.
7. Watch job progress until the local files are saved.

## Scope

- Single-page frontend with premium visual treatment.
- Backend inspection endpoint backed by `yt-dlp`.
- Download job endpoint with in-memory progress tracking.
- Quality presets mapped to common video heights.
- Download output stored inside the project `downloads/` folder.

## Out Of Scope

- Login cookies or member-only downloads.
- Persistent database storage.
- Multi-user authentication.
- Cloud storage uploads.

## Backend Responsibilities

- Validate incoming Bilibili URLs.
- Inspect collections and flatten episode metadata.
- Expose quality presets.
- Create and track download jobs.
- Save downloaded files to a stable folder.

## Frontend Responsibilities

- Present the URL intake flow.
- Show collection artwork and episode cards.
- Let users select quality and episodes.
- Show job progress and output paths.
- Keep the interface polished across desktop and mobile.
