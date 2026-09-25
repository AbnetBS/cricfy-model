# Cricfy TV Web Clone - Hybrid Live System

This is the web version of Cricfy TV built from the Kodi plugin logic.

## What it does

**Hybrid Mode:**
1. **Manual Mode** (You control - Recommended): Add live football matches via Admin panel -> paste HLS .m3u8 link -> shows LIVE instantly like Cricfy
2. **Auto Mode** (Like Cricfy): Fetches M3U playlists from your own API URL, parses with same logic as Kodi plugin's `get_channels()`, shows channels

## How it shows LIVE like Cricfy

Cricfy shows LIVE because its M3U URLs point to live HLS streams (playlist.m3u8 that updates with .ts segments every few seconds).

Our web clone does same:
- Frontend uses hls.js to play HLS
- Backend proxy handles CORS & headers like `lib/req.py`
- Player has provider fallback like Cricfy: If Server 1 fails, click Server 2

## Quick Start

```bash
cd web/backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open http://localhost:8000 - Frontend served from ../frontend/index.html
API docs at http://localhost:8000/api/docs

## Adding Live Football (Manual)

1. Click "Add Live" in header
2. Title: "Ethiopia vs Kenya LIVE"
3. Stream URL: Your HLS link
   - For demo: https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8
   - For real: OBS -> Mux/Cloudflare/OvenMediaEngine -> HLS

## Adding Auto Provider (Like Cricfy's cats.txt)

Edit `backend/data/providers.json`:
```json
{
  "id": "my_football",
  "title": "My Football API",
  "image": "...",
  "catLink": "https://yourdomain.com/football.m3u",
  "type": "auto_m3u"
}
```

Your football.m3u should be:
```
#EXTM3U
#EXTINF:-1 tvg-logo="https://..." group-title="Football", Arsenal vs Man City LIVE
https://your-server.com/hls/arsenal.m3u8
```

System will fetch via `/api/channels?provider_url=...`

## Where to get LEGAL football sources

See `/api/sources/guide`

- **Own Stream**: OBS -> RTMP to OvenMediaEngine (free self-host) -> HLS. Best for local leagues you have rights to.
- **Cloudflare Stream / Mux**: Push RTMP, get HLS. $5/1000 mins.
- **YouTube**: Many leagues stream free officially on YouTube. Embed via iframe.
- **DO NOT** scrape pirated IPTV. You will get DMCA.

## Architecture vs Kodi Plugin

| Kodi Plugin | Web Clone |
|-------------|-----------|
| Firebase Remote Config -> API URL | Your own providers.json or your own API |
| decrypt_data() with SECRET1/2 | decrypt_content_generic() - you can use your own keys or plain M3U |
| StorageServer cache | In-memory cache dict |
| inputstream.adaptive | hls.js + video.js |
| xbmcgui.ListItem | React/Tailwind cards |

## Deployment

- Backend: Any VPS with Docker, or Render, Railway
- Frontend: Same server (FastAPI serves it) or Vercel
- CDN: Cloudflare for HLS caching
