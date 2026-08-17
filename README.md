# YouTube Stream Downloader

A small local web application powered by Flask and yt-dlp.

Paste a YouTube URL into the browser UI and the app extracts the formats currently available for that video. You can filter **Video + Audio**, **Video only**, and **Audio only**, then download a selected format.

## Important architecture note

This is a **local application**, not a GitHub Pages-only website.

A static HTML page hosted on GitHub Pages cannot execute `yt-dlp` or download arbitrary media on the user's computer. This project therefore runs a small local Flask server:

Browser → Flask → yt-dlp → download

You can publish the source code on GitHub. Anyone can clone/download it and run it locally.

## Requirements

- Python 3.10+
- Internet connection
- A current yt-dlp installation from the Python package
- For merging separate video and audio streams, FFmpeg is recommended/required by yt-dlp.

The project installs `yt-dlp[default]`, which includes yt-dlp's default Python dependencies.

For current YouTube extraction, yt-dlp may also require a supported JavaScript runtime. Deno is the recommended runtime in the yt-dlp documentation. If YouTube extraction reports that a JS runtime is missing, install Deno and make sure it is available on PATH.

## Windows

Double-click:

`run_windows.bat`

Or from PowerShell:

```powershell
.\run_windows.bat
```

Then open:

`http://127.0.0.1:5000`

The script creates a `.venv` and installs the dependencies automatically.

## Linux / macOS

```bash
chmod +x run_linux_mac.sh
./run_linux_mac.sh
```

Then open:

`http://127.0.0.1:5000`

## Manual setup

```bash
python -m venv .venv
```

Activate the environment.

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python app.py
```

## Features

- Paste a YouTube URL
- Extract current available formats
- Video + audio formats
- Video-only formats
- Audio-only formats
- Resolution, FPS, codecs and estimated file size
- Download selected format
- Download progress
- Local downloads folder
- Responsive dark UI
- No database
- No external server required

## GitHub Pages

Do not upload this expecting `index.html` on GitHub Pages to perform extraction. GitHub Pages is static hosting and cannot run the Flask/yt-dlp backend.

If you want a public hosted version, deploy the Python backend separately on a server and connect the frontend to it. Be aware that public downloader services have significant bandwidth, abuse, copyright, and hosting considerations.

## Legal / responsible use

yt-dlp is a general-purpose downloader. Only download content when you have permission or the applicable rights to do so and comply with the source site's terms and applicable law.

## License

This project's original code is released under the MIT License. yt-dlp remains a separate project under its own license.
