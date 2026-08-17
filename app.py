from pathlib import Path
import re
import threading
import uuid
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_from_directory
import yt_dlp

BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
jobs = {}
jobs_lock = threading.Lock()

YOUTUBE_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com",
    "youtu.be", "www.youtu.be", "music.youtube.com"
}


def is_youtube_url(url: str) -> bool:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower()
        return parsed.scheme in {"http", "https"} and (
            host in YOUTUBE_HOSTS or host.endswith(".youtube.com")
        )
    except Exception:
        return False


def ydl_options():
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
        # Ask yt-dlp to expose formats instead of choosing one.
    }


def simplify_format(f):
    vcodec = f.get("vcodec")
    acodec = f.get("acodec")
    has_video = bool(vcodec and vcodec != "none")
    has_audio = bool(acodec and acodec != "none")

    if has_video and has_audio:
        kind = "video_audio"
    elif has_video:
        kind = "video"
    elif has_audio:
        kind = "audio"
    else:
        kind = "other"

    return {
        "id": f.get("format_id"),
        "format": f.get("format"),
        "ext": f.get("ext"),
        "resolution": f.get("resolution"),
        "width": f.get("width"),
        "height": f.get("height"),
        "fps": f.get("fps"),
        "filesize": f.get("filesize") or f.get("filesize_approx"),
        "tbr": f.get("tbr"),
        "vcodec": None if not has_video else vcodec,
        "acodec": None if not has_audio else acodec,
        "dynamic_range": f.get("dynamic_range"),
        "container": f.get("container"),
        "kind": kind,
        "needs_merge": has_video and has_audio and "+" in str(f.get("format_id", "")),
    }


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/downloads/<path:name>")
def downloads(name):
    return send_from_directory(DOWNLOAD_DIR, name, as_attachment=True)


@app.post("/api/info")
def info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()

    if not is_youtube_url(url):
        return jsonify({"error": "Please enter a valid YouTube URL."}), 400

    try:
        with yt_dlp.YoutubeDL(ydl_options()) as ydl:
            info_data = ydl.extract_info(url, download=False)

        formats = [
            simplify_format(f)
            for f in info_data.get("formats", [])
            if f.get("vcodec") != "none" or f.get("acodec") != "none"
        ]

        # Keep formats with useful media information and remove duplicates.
        seen = set()
        clean = []
        for f in formats:
            key = (
                f["id"], f["kind"], f["resolution"], f["ext"],
                f["vcodec"], f["acodec"]
            )
            if key not in seen:
                seen.add(key)
                clean.append(f)

        def sort_key(f):
            return (
                {"video_audio": 0, "video": 1, "audio": 2, "other": 3}.get(f["kind"], 9),
                -(f["height"] or 0),
                -(f["fps"] or 0),
                -(f["tbr"] or 0),
                f["ext"] or ""
            )

        clean.sort(key=sort_key)

        return jsonify({
            "id": info_data.get("id"),
            "title": info_data.get("title"),
            "channel": info_data.get("channel") or info_data.get("uploader"),
            "duration": info_data.get("duration"),
            "thumbnail": info_data.get("thumbnail"),
            "webpage_url": info_data.get("webpage_url"),
            "formats": clean,
        })

    except Exception as exc:
        return jsonify({
            "error": str(exc),
            "hint": "If YouTube asks for verification, update yt-dlp and make sure a supported JS runtime is installed."
        }), 500


def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
    return name.strip(" .")[:180] or "youtube_video"


def run_download(job_id, url, format_id, title):
    try:
        outtmpl = str(DOWNLOAD_DIR / f"{safe_filename(title)}.%(ext)s")
        opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "format": format_id,
            "outtmpl": outtmpl,
            "progress_hooks": [
                lambda d: progress_hook(job_id, d)
            ],
        }

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        with jobs_lock:
            jobs[job_id]["status"] = "finished"
            jobs[job_id]["message"] = "Download completed."

            # Find newest file matching the title.
            candidates = sorted(
                DOWNLOAD_DIR.glob(f"{safe_filename(title)}.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if candidates:
                jobs[job_id]["file"] = candidates[0].name

    except Exception as exc:
        with jobs_lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["message"] = str(exc)


def progress_hook(job_id, d):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return

        job["status"] = d.get("status", "downloading")

        if d.get("total_bytes") or d.get("total_bytes_estimate"):
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            done = d.get("downloaded_bytes", 0)
            job["percent"] = round(done * 100 / total, 1) if total else 0

        job["speed"] = d.get("_speed_str") or ""
        job["eta"] = d.get("_eta_str") or ""


@app.post("/api/download")
def download():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    format_id = str(data.get("format_id") or "").strip()
    title = str(data.get("title") or "youtube_video")

    if not is_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400

    if not format_id or len(format_id) > 200:
        return jsonify({"error": "Invalid format."}), 400

    job_id = uuid.uuid4().hex

    with jobs_lock:
        jobs[job_id] = {
            "status": "starting",
            "percent": 0,
            "speed": "",
            "eta": "",
            "message": "Starting download..."
        }

    thread = threading.Thread(
        target=run_download,
        args=(job_id, url, format_id, title),
        daemon=True
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)

    if not job:
        return jsonify({"error": "Job not found."}), 404

    result = dict(job)
    if result.get("file"):
        result["download_url"] = f"/downloads/{result['file']}"
    return jsonify(result)


if __name__ == "__main__":
    print("YouTube Stream Downloader")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(host="127.0.0.1", port=5000, debug=False)
