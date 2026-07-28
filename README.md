# IWantYT — YouTube Downloader

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**IWantYT** is a YouTube video & audio downloader web application.

---

## Features

- **Multi-Quality Stream Selection**: Choose between Highest Resolution (1080p+), 720p HD, 360p SD, or Audio-Only MP3 extraction.
- **Download Progress & History**: Live download status feedback and local session history saved in `localStorage`.
- **Direct File Delivery**: Streams files directly to your browser's download manager with temporary file auto-cleanup.

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pytubefix, yt-dlp
- **Frontend**: HTML5, Vanilla CSS3, Vanilla JavaScript (ES6+), FontAwesome Icons

---

### One-Click Local Launcher (Recommended)

- **Windows**: Double-click `run.bat` (or run `run.bat` in CMD / PowerShell).
- **macOS / Linux**: Run `chmod +x run.sh && ./run.sh` in terminal.

This automatically creates a virtual environment, installs required dependencies, launches the server, and opens **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your web browser!

---

### Manual Setup

1. **Clone the Repository**
   ```bash
   git clone https://github.com/VecetyP/I-Want-YT.git
   cd I-Want-YT
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Server**
   ```bash
   python main.py
   ```

---

## Project Structure

```text
youtube_downloader_app/
│
├── main.py              # FastAPI server & download endpoints (/api/info, /api/download)
├── requirements.txt     # Python package dependencies
├── .gitignore           # Git ignore rules for bytecode & temp files
├── LICENSE              # MIT Open Source License
└── static/              # Frontend static web application assets
    ├── index.html       # UI layout
    ├── style.css        # Custom CSS design system, & animations
    └── app.js           # Client-side API fetch logic & session history
```

---

## API Reference

### `GET /api/info`
Fetches video metadata and available download stream qualities.

**Query Parameters:**
- `url` (string, required): YouTube video URL.

**Response Example:**
```json
{
  "status": "success",
  "url": "https://www.youtube.com/watch?v=...",
  "title": "Video Title Example",
  "author": "Creator Channel",
  "duration": "03:45",
  "thumbnail_url": "https://i.ytimg.com/...",
  "views": "150,000",
  "streams": [
    { "id": "highest", "label": "Highest Available Quality", "badge": "Best Quality" },
    { "id": "audio", "label": "Audio Only (MP3)", "badge": "MP3 Audio" }
  ]
}
```

### `GET /api/download`
Downloads the specified video or audio stream and returns it as an attachment.

**Query Parameters:**
- `url` (string, required): YouTube video URL.
- `quality` (string, optional): Stream quality ID (`highest`, `1080p`, `720p`, `360p`, `audio`).

---

## License

This project is licensed under the [MIT License](LICENSE).
