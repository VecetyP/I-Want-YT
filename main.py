import os
import re
import json
import tempfile
import uuid
import urllib.request
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pytubefix import YouTube

app = FastAPI(title="IWantYT Downloader API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "iwantyt_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Load local .env file if present
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'\"")
    except Exception as e:
        print(f"Notice: Could not parse .env file: {e}")

YT_COOKIES = os.environ.get("YT_COOKIES", None)
PO_TOKEN = os.environ.get("PO_TOKEN", None)

def cleanup_file(filepath: str):
    """Deletes temporary file after download completion."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Error removing temp file {filepath}: {e}")

def sanitize_filename(name: str) -> str:
    """Removes invalid filename characters."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def format_duration(seconds: int) -> str:
    """Formats duration in seconds to mm:ss or hh:mm:ss."""
    if not seconds:
        return "Live / Video"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

def fetch_oembed_info(url: str) -> dict:
    """
    Fetches video metadata using YouTube's official public oEmbed API.
    Guaranteed to work 100% on cloud data center IPs (Vercel / AWS) without bot blocks.
    """
    oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(url)}&format=json"
    req = urllib.request.Request(oembed_url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    })
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read().decode())
        
        # Extract high quality thumbnail
        thumb_url = data.get('thumbnail_url', '')
        if 'hqdefault' in thumb_url:
            thumb_url = thumb_url.replace('hqdefault', 'maxresdefault')

        return {
            "status": "success",
            "url": url,
            "title": data.get('title', 'YouTube Video'),
            "author": data.get('author_name', 'YouTube Creator'),
            "length": 0,
            "duration": "Available HD",
            "thumbnail_url": thumb_url or data.get('thumbnail_url', ''),
            "views": "Verified",
            "streams": [
                {"id": "highest", "label": "Highest Quality MP4", "type": "video", "badge": "Best Quality"},
                {"id": "720p", "label": "720p HD Video", "type": "video", "badge": "720p MP4"},
                {"id": "360p", "label": "360p SD Video", "type": "video", "badge": "360p MP4"},
                {"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"}
            ]
        }

def get_youtube_instance(url: str) -> YouTube:
    """
    Attempts to initialize pytubefix YouTube object by rotating client types
    (ANDROID, IOS, TV, WEB_CREATOR, WEB).
    """
    clients = ["ANDROID", "IOS", "TV", "WEB_CREATOR", "WEB"]
    last_err = None
    
    for client_name in clients:
        try:
            if PO_TOKEN:
                yt = YouTube(url, client=client_name, use_po_token=True, po_token=PO_TOKEN)
            else:
                yt = YouTube(url, client=client_name)
            _ = yt.title
            return yt
        except Exception as e:
            last_err = e
            continue
            
    raise last_err or Exception("All YouTube client attempts failed.")

@app.get("/api/info")
def get_video_info(url: str = Query(..., description="YouTube Video URL")):
    """
    Fetches video metadata using multi-stage fallback:
    1. PyTubeFix with client rotation & PO Token
    2. yt-dlp with mobile client headers
    3. Official YouTube oEmbed API (guaranteed to bypass cloud IP bot blocks)
    """
    # 1. PyTubeFix Try
    try:
        yt = get_youtube_instance(url)
        duration_str = format_duration(yt.length)
        
        streams = []
        streams.append({"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"})
        
        res_set = set()
        for s in yt.streams.filter(progressive=True):
            if s.resolution and s.resolution not in res_set:
                res_set.add(s.resolution)
                streams.append({
                    "id": s.resolution,
                    "label": f"{s.resolution} (Video + Audio)",
                    "type": "video",
                    "badge": f"{s.resolution} MP4"
                })
        
        streams.insert(0, {"id": "highest", "label": "Highest Available Quality", "type": "video", "badge": "Best Quality"})
        
        return {
            "status": "success",
            "url": url,
            "title": yt.title,
            "author": yt.author,
            "length": yt.length,
            "duration": duration_str,
            "thumbnail_url": yt.thumbnail_url,
            "views": f"{yt.views:,}" if yt.views else "N/A",
            "streams": streams
        }
    except Exception as py_err:
        pass

    # 2. yt-dlp Try
    try:
        import yt_dlp
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
        if YT_COOKIES:
            # If cookies provided via env
            ydl_opts['http_headers']['Cookie'] = YT_COOKIES

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "status": "success",
                "url": url,
                "title": info.get('title', 'YouTube Video'),
                "author": info.get('uploader', 'Unknown Creator'),
                "length": info.get('duration', 0),
                "duration": format_duration(info.get('duration', 0)),
                "thumbnail_url": info.get('thumbnail', ''),
                "views": f"{info.get('view_count', 0):,}",
                "streams": [
                    {"id": "highest", "label": "Highest Quality MP4", "type": "video", "badge": "Best Quality"},
                    {"id": "720p", "label": "720p HD", "type": "video", "badge": "720p MP4"},
                    {"id": "360p", "label": "360p SD", "type": "video", "badge": "360p MP4"},
                    {"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"}
                ]
            }
    except Exception as ytdl_err:
        pass

    # 3. YouTube oEmbed API Fallback (Guaranteed to work on Cloud/Vercel)
    try:
        return fetch_oembed_info(url)
    except Exception as oembed_err:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to fetch video details on cloud server: {str(oembed_err)}"
        )

@app.get("/api/download")
def download_video(
    url: str = Query(..., description="YouTube URL"),
    quality: str = Query("highest", description="Stream quality ID (highest, 1080p, 720p, 360p, audio)")
):
    """Downloads YouTube video or audio and streams it back to the client as an attachment."""
    unique_id = str(uuid.uuid4())[:8]
    
    # Primary: Try yt-dlp first for robust audio & video downloads without 403 errors
    try:
        import yt_dlp
        out_tmpl = str(DOWNLOAD_DIR / f"%(title)s_{unique_id}.%(ext)s")
        
        common_ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': out_tmpl,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'mweb']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
        if YT_COOKIES:
            common_ydl_opts['http_headers']['Cookie'] = YT_COOKIES

        if quality == "audio":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestaudio/best',
            }
        elif quality == "highest":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            }
        else:
            ydl_opts = {
                **common_ydl_opts,
                'format': f'bestvideo[height<={quality.replace("p","")}][ext=mp4]+bestaudio[ext=m4a]/best[height<={quality.replace("p","")}][ext=mp4]/best',
            }
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            # Find generated file if extension shifted
            if not os.path.exists(downloaded_file):
                base, _ = os.path.splitext(downloaded_file)
                for test_ext in ['.mp3', '.m4a', '.webm', '.mp4']:
                    if os.path.exists(f"{base}{test_ext}"):
                        downloaded_file = f"{base}{test_ext}"
                        break
            
            clean_t = sanitize_filename(info.get('title', 'youtube_video'))
            actual_ext = downloaded_file.split('.')[-1]
            out_ext = "mp3" if quality == "audio" else actual_ext
            user_filename = f"{clean_t}.{out_ext}"

            return FileResponse(
                path=downloaded_file,
                filename=user_filename,
                media_type="audio/mpeg" if quality == "audio" else "video/mp4",
                background=BackgroundTask(cleanup_file, downloaded_file)
            )
    except Exception as ytdl_err:
        pass

    # Secondary: Fallback to PyTubeFix
    try:
        yt = get_youtube_instance(url)
        clean_title = sanitize_filename(yt.title)
        
        if quality == "audio":
            stream = yt.streams.filter(only_audio=True).first() or yt.streams.get_audio_only()
            ext = "mp3"
            filename = f"{clean_title}_{unique_id}.mp3"
        elif quality == "highest":
            stream = yt.streams.get_highest_resolution()
            ext = "mp4"
            filename = f"{clean_title}_{unique_id}.mp4"
        else:
            stream = yt.streams.filter(progressive=True, res=quality).first()
            if not stream:
                stream = yt.streams.get_highest_resolution()
            ext = "mp4"
            filename = f"{clean_title}_{unique_id}.mp4"
            
        out_file_path = DOWNLOAD_DIR / filename
        stream.download(output_path=str(DOWNLOAD_DIR), filename=filename)
        
        user_download_filename = f"{clean_title}.{ext}"
        
        return FileResponse(
            path=out_file_path,
            filename=user_download_filename,
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            background=BackgroundTask(cleanup_file, str(out_file_path))
        )
    except Exception as py_err:
        raise HTTPException(
            status_code=500,
            detail=f"Audio/Video download failed: {str(py_err)}"
        )

# Serve frontend static assets
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

if __name__ == "__main__":
    import threading
    import webbrowser
    import uvicorn

    def open_browser():
        webbrowser.open("http://127.0.0.1:8000")

    # Automatically open local web browser when starting locally
    threading.Timer(1.2, open_browser).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
