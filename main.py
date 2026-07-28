import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from starlette.background import BackgroundTask
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pytubefix import YouTube
from pytubefix.cli import on_progress

app = FastAPI(title="IWantYT Downloader API", version="1.0.0")

# Enable CORS for local development & browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "crystalytdl_downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

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
        return "Live / Unknown"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"

@app.get("/api/info")
def get_video_info(url: str = Query(..., description="YouTube Video URL")):
    """Fetches video metadata, title, author, duration, thumbnail, and stream options."""
    try:
        yt = YouTube(url)
        
        # Format duration
        duration_str = format_duration(yt.length)
        
        # Stream qualities available
        streams = []
        # Audio option
        streams.append({"id": "audio", "label": "Audio Only (MP3)", "type": "audio", "badge": "MP3 Audio"})
        
        # Progressive video options (video + audio combined)
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
        
        # Ensure highest resolution is listed first
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
    except Exception as error:
        # Fallback using yt-dlp if pytubefix encounters issues
        try:
            import yt_dlp
            ydl_opts = {'quiet': True, 'skip_download': True}
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
        except Exception as fallback_err:
            raise HTTPException(status_code=400, detail=f"Failed to fetch video details: {str(error)}")

@app.get("/api/download")
def download_video(
    url: str = Query(..., description="YouTube URL"),
    quality: str = Query("highest", description="Stream quality ID (highest, 1080p, 720p, 360p, audio)")
):
    """Downloads YouTube video or audio and streams it back to the client as an attachment."""
    unique_id = str(uuid.uuid4())[:8]
    
    try:
        yt = YouTube(url)
        clean_title = sanitize_filename(yt.title)
        
        if quality == "audio":
            stream = yt.streams.get_audio_only()
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
            media_type="application/octet-stream",
            background=BackgroundTask(cleanup_file, str(out_file_path))
        )

    except Exception as main_err:
        # Fallback to yt-dlp if pytubefix fails download
        try:
            import yt_dlp
            out_tmpl = str(DOWNLOAD_DIR / f"%(title)s_{unique_id}.%(ext)s")
            
            if quality == "audio":
                ydl_opts = {
                    'format': 'bestaudio/best',
                    'outtmpl': out_tmpl,
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }],
                    'quiet': True
                }
            else:
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                    'outtmpl': out_tmpl,
                    'quiet': True
                }
                
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                if not os.path.exists(downloaded_file):
                    # Check for mp3 extension if audio
                    base, _ = os.path.splitext(downloaded_file)
                    if os.path.exists(f"{base}.mp3"):
                        downloaded_file = f"{base}.mp3"
                
                clean_t = sanitize_filename(info.get('title', 'youtube_video'))
                ext = downloaded_file.split('.')[-1]
                user_filename = f"{clean_t}.{ext}"

                return FileResponse(
                    path=downloaded_file,
                    filename=user_filename,
                    media_type="application/octet-stream",
                    background=BackgroundTask(cleanup_file, downloaded_file)
                )
        except Exception as fallback_err:
            raise HTTPException(status_code=500, detail=f"Download failed: {str(main_err)} | Fallback: {str(fallback_err)}")

# Serve frontend static assets
static_path = Path(__file__).parent / "static"
static_path.mkdir(exist_ok=True)
app.mount("/", StaticFiles(directory=str(static_path), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
