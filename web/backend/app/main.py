from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
import time
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse

from app.services.m3u_parser import parse_m3u
from app.services.fetcher import fetch_url, decrypt_content_generic, custom_headers

app = FastAPI(title="Cricfy Web Clone", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

# In-memory cache
cache = {}
CACHE_TTL = 3600

def load_json(file_name):
    path = DATA_DIR / file_name
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(file_name, data):
    path = DATA_DIR / file_name
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "hybrid", "time": time.time()}

@app.get("/api/providers")
def get_providers():
    providers = load_json("providers.json")
    return providers

@app.get("/api/matches")
def get_matches(category: str = Query(None)):
    matches = load_json("matches.json")
    if category:
        matches = [m for m in matches if m["category"] == category or category == "all"]
    return matches

@app.get("/api/match/{match_id}")
def get_match(match_id: str):
    matches = load_json("matches.json")
    match = next((m for m in matches if m["id"] == match_id), None)
    if not match:
        raise HTTPException(404, "Match not found")
    return match

@app.post("/api/matches")
async def add_match(request: Request):
    """Manual mode: add a new live match"""
    data = await request.json()
    matches = load_json("matches.json")
    # Generate ID
    new_id = f"match_{int(time.time())}"
    data["id"] = new_id
    if "providers" not in data:
        data["providers"] = []
    matches.append(data)
    save_json("matches.json", matches)
    return {"success": True, "id": new_id, "match": data}

@app.delete("/api/match/{match_id}")
def delete_match(match_id: str):
    matches = load_json("matches.json")
    new_matches = [m for m in matches if m["id"] != match_id]
    if len(new_matches) == len(matches):
        raise HTTPException(404, "Match not found")
    save_json("matches.json", new_matches)
    return {"success": True}

@app.get("/api/channels")
def get_channels(provider_url: str = Query(...), decrypt: bool = Query(False)):
    """Auto mode: fetch M3U from provider_url like Cricfy does"""
    cache_key = f"channels_{provider_url}"
    if cache_key in cache:
        cached_time, cached_data = cache[cache_key]
        if time.time() - cached_time < CACHE_TTL:
            return cached_data

    try:
        content = fetch_url(provider_url)
        if decrypt:
            content = decrypt_content_generic(content)
        channels = parse_m3u(content)
        result = [c.to_dict() for c in channels[:200]]  # limit to 200 for demo
        cache[cache_key] = (time.time(), result)
        return result
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch channels: {str(e)}")

@app.get("/api/proxy/m3u8")
def proxy_m3u8(url: str = Query(...)):
    """
    Proxy for HLS to handle CORS and headers.
    This is needed because browsers block custom headers for HLS.
    Usage: /api/proxy/m3u8?url=https://example.com/live.m3u8
    """
    try:
        resp = requests.get(url, headers=custom_headers, timeout=10, stream=True)
        resp.raise_for_status()
        content = resp.text

        # Rewrite URLs in m3u8 to go through our proxy for .ts segments
        # This makes live work like Cricfy's provider switching
        base_url = url.rsplit('/', 1)[0] + '/'
        lines = []
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                if not line.startswith('http'):
                    absolute = urljoin(base_url, line)
                else:
                    absolute = line
                # For ts segments, proxy via /api/proxy/segment
                if absolute.endswith('.ts') or '.ts?' in absolute:
                    proxied = f"/api/proxy/segment?url={absolute}"
                    lines.append(proxied)
                elif absolute.endswith('.m3u8'):
                    proxied = f"/api/proxy/m3u8?url={absolute}"
                    lines.append(proxied)
                else:
                    lines.append(absolute)
            else:
                lines.append(line)
        
        rewritten = "\n".join(lines)
        return StreamingResponse(iter([rewritten]), media_type="application/vnd.apple.mpegurl", headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(500, f"Proxy failed: {str(e)}")

@app.get("/api/proxy/segment")
def proxy_segment(url: str = Query(...)):
    try:
        resp = requests.get(url, headers=custom_headers, timeout=15, stream=True)
        resp.raise_for_status()
        return StreamingResponse(resp.iter_content(chunk_size=8192), media_type=resp.headers.get("content-type", "video/MP2T"), headers={"Access-Control-Allow-Origin": "*"})
    except Exception as e:
        raise HTTPException(500, f"Segment proxy failed: {str(e)}")

# Serve frontend static files if built
if FRONTEND_DIR.exists():
    @app.get("/")
    def serve_index():
        index_path = FRONTEND_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Frontend not built yet. API is running at /api/docs"}

@app.get("/api/sources/guide")
def sources_guide():
    return {
        "legal_options": [
            {
                "name": "Own Your Stream (Best for Local Leagues)",
                "how": "Use OBS Studio -> RTMP to OvenMediaEngine / AWS IVS / Mux. You own rights. Cost: $0-50/month",
                "example_hls": "rtmp://your-server/live -> https://your-server/hls/stream.m3u8"
            },
            {
                "name": "Free Legal YouTube Embeds",
                "how": "Many leagues stream free officially on YouTube. Use YouTube IFrame API, not HLS. No bandwidth cost.",
                "example": "Ethiopian Premier League, some African leagues, FIFA youth tournaments"
            },
            {
                "name": "Public Test Streams (for demo)",
                "how": "Use for testing player",
                "urls": [
                    "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8",
                    "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8"
                ]
            },
            {
                "name": "Your Own M3U Aggregator (Like Cricfy but legal)",
                "how": "Create your own cats.json file on your server with list of YOUR legal M3U URLs. Point auto provider to it.",
                "format": '{"title": "My Football", "catLink": "https://yourdomain.com/football.m3u"}'
            }
        ],
        "illegal_warning": "Do NOT scrape Cricfy, Sportzfy, or pirated IPTV. You will get DMCA takedown, hosting banned."
    }
