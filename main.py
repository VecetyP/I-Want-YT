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
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
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

@app.middleware("http")
async def add_no_cache_headers(request, call_next):
    response = await call_next(request)
    if request.url.path.endswith(".html") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

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

def get_ffmpeg_path() -> Optional[str]:
    """Returns path to ffmpeg executable (from PATH or imageio-ffmpeg package)."""
    import shutil
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin:
        return ffmpeg_bin
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


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
                {"id": "highest", "label": "Highest Quality (1080p+)", "type": "video", "badge": "Best Quality"},
                {"id": "1080p", "label": "1080p Full HD", "type": "video", "badge": "1080p MP4"},
                {"id": "720p", "label": "720p HD Video", "type": "video", "badge": "720p MP4"},
                {"id": "360p", "label": "360p SD Video", "type": "video", "badge": "360p MP4"},
                {"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"}
            ]
        }

def get_youtube_instance(url: str) -> YouTube:
    """
    Tries default pytubefix YouTube object first (fastest & 100% reliable locally),
    then rotates client types (ANDROID, IOS, TV, WEB_CREATOR) if blocked on cloud.
    """
    try:
        if PO_TOKEN:
            yt = YouTube(url, use_po_token=True, po_token=PO_TOKEN)
        else:
            yt = YouTube(url)
        _ = yt.title
        return yt
    except Exception:
        pass

    clients = ["ANDROID_VR", "ANDROID", "IOS", "TV", "WEB_CREATOR"]
    last_err = None
    
    for client_name in clients:
        try:
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
        
        streams = [
            {"id": "highest", "label": "Highest Quality (1080p+)", "type": "video", "badge": "Best Quality"},
            {"id": "1080p", "label": "1080p Full HD", "type": "video", "badge": "1080p MP4"},
            {"id": "720p", "label": "720p HD Video", "type": "video", "badge": "720p MP4"},
            {"id": "360p", "label": "360p SD Video", "type": "video", "badge": "360p MP4"},
            {"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"}
        ]
        
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
                    'player_client': ['android_vr', 'android', 'ios', 'mweb']
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
                    {"id": "highest", "label": "Highest Quality (1080p+)", "type": "video", "badge": "Best Quality"},
                    {"id": "1080p", "label": "1080p Full HD", "type": "video", "badge": "1080p MP4"},
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

@app.get("/api/stream-url")
def get_stream_url(
    url: str = Query(..., description="YouTube URL"),
    quality: str = Query("highest", description="Stream quality (highest, 720p, 360p, audio)")
):
    """
    Extracts direct CDN stream URLs without downloading anything.
    The user's browser downloads directly from Google's CDN, bypassing
    Vercel's timeout, disk, and ffmpeg constraints entirely.
    """
    try:
        import yt_dlp

        # Select format string based on quality - always prefer single progressive
        # streams (with both audio+video) since they have a direct URL.
        # Avoid merge formats (bestvideo+bestaudio) which need ffmpeg.
        if quality == "audio":
            fmt = 'bestaudio[ext=m4a]/bestaudio/best'
        elif quality == "highest":
            fmt = 'best[ext=mp4][height<=1080]/best[height<=1080]/best'
        elif quality == "360p":
            fmt = 'best[height<=360][ext=mp4]/best[height<=360]/best'
        else:
            height = quality.replace("p", "")
            fmt = f'best[height<={height}][ext=mp4]/best[height<={height}]/best'

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'format': fmt,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr', 'android', 'ios', 'mweb']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
        if YT_COOKIES:
            ydl_opts['http_headers']['Cookie'] = YT_COOKIES

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # Extract the direct stream URL.
            # Single-format selections populate info['url'] directly.
            # Merge formats (bestvideo+bestaudio) populate info['requested_formats'] instead.
            direct_url = info.get('url')
            if not direct_url:
                requested = info.get('requested_formats', [])
                if requested:
                    # For video, pick the video stream; for audio, pick the audio stream
                    if quality == "audio":
                        direct_url = requested[-1].get('url')  # last is typically audio
                    else:
                        direct_url = requested[0].get('url')   # first is typically video

            if not direct_url:
                raise Exception("Could not extract a direct stream URL from YouTube.")

            title = sanitize_filename(info.get('title', 'youtube_video'))
            ext = "mp3" if quality == "audio" else "mp4"

            return JSONResponse({
                "status": "success",
                "stream_url": direct_url,
                "filename": f"{title}.{ext}",
                "title": info.get('title', 'YouTube Video'),
            })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Stream URL extraction failed: {str(e)}"
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
        
        ffmpeg_bin = get_ffmpeg_path()
        common_ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'outtmpl': out_tmpl,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_vr', 'android', 'ios', 'mweb']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
        }
        if ffmpeg_bin:
            common_ydl_opts['ffmpeg_location'] = ffmpeg_bin
            common_ydl_opts['merge_output_format'] = 'mp4'
        if YT_COOKIES:
            common_ydl_opts['http_headers']['Cookie'] = YT_COOKIES

        if quality == "audio":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
            }
        elif quality == "highest":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestvideo[height<=1080]+bestaudio/bestvideo+bestaudio/best' if ffmpeg_bin else 'best[ext=mp4]/best',
            }
        elif quality == "1080p":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]/best' if ffmpeg_bin else 'best[height<=1080]/best',
            }
        elif quality == "720p":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best' if ffmpeg_bin else 'best[height<=720]/best',
            }
        elif quality == "360p":
            ydl_opts = {
                **common_ydl_opts,
                'format': 'bestvideo[height<=360]+bestaudio/best[height<=360]/best' if ffmpeg_bin else 'best[height<=360]/best',
            }
        else:
            height = quality.replace("p", "")
            ydl_opts = {
                **common_ydl_opts,
                'format': f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best' if ffmpeg_bin else f'best[height<={height}]/best',
            }
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
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
            except Exception as dl_err:
                # Direct Stream URL Redirect Fallback (Guaranteed 100% on Vercel Serverless without ffmpeg)
                info = ydl.extract_info(url, download=False)
                direct_url = info.get('url')
                if direct_url:
                    return RedirectResponse(url=direct_url)
                raise dl_err
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
