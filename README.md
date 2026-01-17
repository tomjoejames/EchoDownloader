# Echo Downloader 🎧📹

![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-active-success)
<img width="848" height="917" alt="Screenshot from 2026-01-17 13-43-08" src="https://github.com/user-attachments/assets/661e28e0-e266-4855-b76e-0110103e199b" />

**Echo Downloader** is a lightweight, local desktop-style application for downloading YouTube videos as **MP3 (audio)** or **MP4 (video)** at the highest available quality.

It runs a local Flask server and opens a clean browser UI automatically, giving you an **app-like experience without Electron or heavy frameworks**.

---
[Screencast from 2026-01-17 13-41-27.webm](https://github.com/user-attachments/assets/33ec46de-4ed1-49b0-9003-cff4750a4b08)

built by [Tom Joe James](https://tomjoejames.com)
## ✨ Features

- 🎵 MP3 (audio-only, high quality)
- 🎬 MP4 (best available video + audio)
- 📊 Live progress bar, speed & ETA
- 🔀 Queue mode or parallel downloads
- 🖼️ Automatic video preview (thumbnail + title)
- ❌ Cancel running downloads
- 📂 Open download folder per job
- 🌙 Modern dark UI
- 💻 Works on **Windows & Linux**
- 🚀 No cloud, fully local

---

## 🧩 Requirements (All Platforms)

- **Python 3.10 or newer**
- **yt-dlp**
- **ffmpeg**
- A modern browser (Chrome, Edge, Firefox)

---

# ⚡ Quick Start (Non-Technical Users)

If you already have Python installed:

```bash
git clone https://github.com/yourusername/echo-downloader.git
cd echo-downloader
python app.py
```

Your browser will open automatically at:

```
http://127.0.0.1:8000
```

Paste a YouTube link → choose MP3 or MP4 → Download.

---

# 🐧 Linux (Ubuntu / Debian)

## 1️⃣ Install system dependencies

```bash
sudo apt update
sudo apt install -y python3 python3-venv ffmpeg
```

Install yt-dlp:

```bash
pip install -U yt-dlp
```

---

## 2️⃣ Clone the repository

```bash
git clone https://github.com/yourusername/echo-downloader.git
cd echo-downloader
```

---

## 3️⃣ Create & activate virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

---

## 4️⃣ Install Python dependencies

```bash
pip install flask yt-dlp
```

---

## 5️⃣ Run the app

```bash
python app.py
```

Browser opens automatically.

---

## 📦 Linux AppImage (Optional)

You can package Echo Downloader as a **single portable AppImage**:

```bash
./appimagetool EchoDownloader.AppDir
```

This produces:

```
EchoDownloader-x86_64.AppImage
```

Runs on most Linux distros without installation.

---

# 🪟 Windows

## 1️⃣ Install Python

Download Python from:
👉 [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)

⚠️ Check **"Add Python to PATH"** during install.

---

## 2️⃣ Install ffmpeg

1. Download from: [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. Extract
3. Add `bin` folder to **System PATH**

---

## 3️⃣ Install yt-dlp

```bat
pip install -U yt-dlp
```

---

## 4️⃣ Clone repository

```bat
git clone https://github.com/yourusername/echo-downloader.git
cd echo-downloader
```

---

## 5️⃣ Create & activate virtual environment

```bat
python -m venv venv
venv\Scripts\activate
```

---

## 6️⃣ Install dependencies

```bat
pip install flask yt-dlp
```

---

## 7️⃣ Run the app

```bat
python app.py
```

Browser opens automatically.

---

# 🧱 Windows Standalone `.exe` (Optional)

> ⚠️ Windows `.exe` **must be built on Windows**.

### Build with PyInstaller:

```bat
pyinstaller ^
  --onefile ^
  --noconsole ^
  --icon=icon.ico ^
  --add-data "index.html;." ^
  app.py
```

Output:

```
dist/app.exe
```

Rename to:

```
EchoDownloader.exe
```

Place `yt-dlp.exe` and `ffmpeg.exe` next to the `.exe`.

---

# 📁 Download Locations

```
downloads/
├── audio/   → MP3 files
└── video/   → MP4 files
```

---

# ❓ FAQ

### ❔ Preview fails to load

* yt-dlp may be blocked temporarily by YouTube
* Try another link
* Some videos restrict metadata

### ❔ Download shows "error"

* Check terminal logs
* Ensure ffmpeg is installed
* Some videos are age/region restricted

### ❔ Why is it browser-based?

* Faster
* Lighter
* No Electron bloat
* Native system browser rendering

---

# 🔐 Security Notes

* Runs **only on localhost**
* No external servers
* No telemetry
* No credentials stored
* All downloads are local

---

# 🗺️ Roadmap

* 🔌 WebSocket progress (no polling)
* 💾 Resume downloads
* 🧠 Filename sanitization rules
* 🪟 System tray integration
* 📦 Windows installer (NSIS/MSI)
* 🚀 Auto-download dependencies

---

# 🤝 Contributing

Contributions are welcome.

1. Fork the repo
2. Create a feature branch
3. Commit changes
4. Open a Pull Request

Please keep changes clean and documented.

---

# ⚠️ Legal Notice

This project is for **personal and educational use only**.

Downloading copyrighted content may violate YouTube's Terms of Service or local laws.
You are responsible for how you use this software.

---

# 📜 License

MIT License

---

## ⭐ Credits

* **yt-dlp** – download engine
* **ffmpeg** – media processing
* **Flask** – local web server

---

Enjoy using **Echo Downloader** 🚀
