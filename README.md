# IWantYT — Glassmorphism YouTube Downloader

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi)
![UI](https://img.shields.io/badge/Design-Glassmorphism-purple?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**IWantYT** is a modern, high-performance YouTube video & audio downloader web application built with a **FastAPI** backend and an **Iridescent Light Theme Glassmorphism** frontend interface.

---

## Features

- **Iridescent Glassmorphism Light Theme**: Frosted glass panels (`backdrop-filter: blur(24px)`), smooth pastel mesh gradients, ambient floating glow effects, and modern typography.
- **Fast & Responsive**: Real-time URL validation, video thumbnail & metadata fetching (author, views, duration).
- **Multi-Quality Stream Selection**: Choose between Highest Resolution (1080p+), 720p HD, 360p SD, or Audio-Only MP3 extraction.
- **Dual Engine Reliability**: Primary downloading powered by `pytubefix` with seamless automatic fallback to `yt-dlp`.
- **Download Progress & History**: Live download status feedback and local session history saved in `localStorage`.
- **Direct File Delivery**: Streams files directly to your browser's download manager with temporary file auto-cleanup.

---

## Tech Stack

- **Backend**: Python 3.10+, FastAPI, Uvicorn, Pytubefix, yt-dlp
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism Tokens), Vanilla JavaScript (ES6+), FontAwesome Icons

---

## Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY_NAME.git
cd YOUR_REPOSITORY_NAME
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Web Application
```bash
python main.py
```

Or run via Uvicorn directly:
```bash
uvicorn main:app --reload --port 8000
```

### 4. Open in Browser
Visit **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

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
    ├── index.html       # Light Glassmorphism UI layout
    ├── style.css        # Custom CSS design system, glass effects & animations
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
