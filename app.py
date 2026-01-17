from flask import Flask, request, jsonify, send_from_directory
import subprocess
import threading
import uuid
import json
import os
import signal
import time
from pathlib import Path

app = Flask(__name__)

# Enable CORS for local development
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# ================= CONFIGURATION =================
class Config:
    BASE_DIR = Path("downloads").resolve()
    AUDIO_DIR = BASE_DIR / "audio"
    VIDEO_DIR = BASE_DIR / "video"
    HISTORY_FILE = Path("history.json")
    MAX_PARALLEL = 3
    MAX_HISTORY_ENTRIES = 50
    
    # Updated User-Agent to match current Chrome on Windows (most common)
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    
    # Cookie strategy - NO COOKIES works best!
    # YouTube's bot detection is triggered by cookie extraction
    # Going cookieless actually works better for most videos
    COOKIE_STRATEGY = []
    
    # Only use cookies if you need age-restricted or private videos:
    # COOKIE_STRATEGY = ["--cookies", "cookies.txt"]  # Manual export recommended
    
    # Common yt-dlp options
    COMMON_OPTS = [
        "--user-agent", USER_AGENT,
        "--no-playlist",
        "--extractor-retries", "5",
        "--retries", "10",
        "--fragment-retries", "10",
        "--socket-timeout", "30",
        *COOKIE_STRATEGY,
    ]

# Create directories
Config.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
Config.VIDEO_DIR.mkdir(parents=True, exist_ok=True)

# ================= STATE =================
jobs = {}  # job_id -> job dict
queue = []  # list of job_ids
active_jobs = set()  # running job_ids
QUEUE_MODE = False
jobs_lock = threading.Lock()

# ================= HELPERS =================
def load_history():
    """Load download history from JSON file."""
    try:
        if not Config.HISTORY_FILE.exists():
            return []
        with open(Config.HISTORY_FILE, "r", encoding="utf-8") as f:
            data = f.read().strip()
            return json.loads(data) if data else []
    except (json.JSONDecodeError, IOError) as e:
        app.logger.error(f"Error loading history: {e}")
        return []

def save_history(entry):
    """Save a new entry to download history."""
    try:
        data = load_history()
        data.insert(0, entry)
        with open(Config.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data[:Config.MAX_HISTORY_ENTRIES], f, indent=2)
    except IOError as e:
        app.logger.error(f"Error saving history: {e}")

def human_speed(bps):
    """Convert bytes per second to human-readable format."""
    if not bps:
        return ""
    try:
        bps = float(bps)
        if bps >= 1024**2:
            return f"{bps/1024**2:.2f} MB/s"
        return f"{bps/1024:.1f} KB/s"
    except (ValueError, TypeError):
        return ""

def human_eta(sec):
    """Convert seconds to human-readable ETA."""
    if sec is None:
        return ""
    try:
        sec = int(sec)
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"
    except (ValueError, TypeError):
        return ""

# ================= QUEUE CONTROL =================
def start_next_from_queue():
    """Start the next job from queue if conditions allow."""
    with jobs_lock:
        if not QUEUE_MODE:
            return
        if active_jobs:
            return
        if not queue:
            return
        
        job_id = queue.pop(0)
        job = jobs.get(job_id)
        if job:
            threading.Thread(
                target=run_job,
                args=(job_id, job["cmd"]),
                daemon=True
            ).start()

# ================= DOWNLOAD RUNNER =================
def run_job(job_id, cmd):
    """Execute a download job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return
        job["status"] = "downloading"
    
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        with jobs_lock:
            job["process"] = proc
            active_jobs.add(job_id)
        
        # Process output
        for line in proc.stdout:
            if line.startswith("{"):
                try:
                    data = json.loads(line)
                    p = data.get("progress", {})
                    with jobs_lock:
                        job["percent"] = p.get("percent", job["percent"])
                        job["speed"] = human_speed(p.get("speed"))
                        job["eta"] = human_eta(p.get("eta"))
                except json.JSONDecodeError:
                    pass
        
        # Capture any errors
        stderr_output = proc.stderr.read()
        proc.wait()
        
        with jobs_lock:
            active_jobs.discard(job_id)
            
            if job["status"] == "cancelled":
                pass
            elif proc.returncode == 0:
                job["status"] = "done"
                job["percent"] = 100
                save_history({
                    "title": job["title"],
                    "type": job["mode"]
                })
            else:
                job["status"] = "error"
                app.logger.error(f"Job {job_id} failed with return code {proc.returncode}")
                if stderr_output:
                    app.logger.error(f"Job {job_id} stderr: {stderr_output[:1000]}")
        
    except Exception as e:
        app.logger.error(f"Error running job {job_id}: {e}")
        with jobs_lock:
            active_jobs.discard(job_id)
            job["status"] = "error"
    
    if QUEUE_MODE:
        start_next_from_queue()

# ================= ROUTES =================
@app.route("/")
def home():
    """Serve the main HTML page."""
    return send_from_directory(".", "index.html")

@app.route("/info", methods=["POST"])
def info():
    """Get video metadata without downloading."""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    app.logger.info(f"Info request received: {data}")
    
    if not data or "url" not in data:
        app.logger.error("Missing URL in request")
        return jsonify({"error": "URL required"}), 400
    
    url = data.get("url", "").strip()
    
    if not url:
        app.logger.error("Empty URL provided")
        return jsonify({"error": "URL cannot be empty"}), 400
    
    app.logger.info(f"Fetching info for URL: {url}")
    
    cmd = [
        "yt-dlp",
        *Config.COMMON_OPTS,
        "--dump-json",
        "--skip-download",
        "--no-warnings",  # CRITICAL: Suppress warnings that break JSON parsing
        # Avoid rate limiting
        "--sleep-requests", "1",
        url
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Log the actual output for debugging
        if result.stdout:
            app.logger.info(f"yt-dlp stdout length: {len(result.stdout)} chars")
        if result.stderr:
            app.logger.warning(f"yt-dlp stderr: {result.stderr[:500]}")
        
        if result.returncode != 0:
            error_output = result.stderr or result.stdout or "Unknown error"
            app.logger.error(f"yt-dlp failed (code {result.returncode}): {error_output}")
            
            # Parse common errors
            if "Sign in to confirm you're not a bot" in error_output or "Sign in to confirm" in error_output:
                return jsonify({"error": "YouTube bot detection. Try: 1) Sign into Chrome/Firefox 2) Install cookies.txt"}), 400
            elif "Video unavailable" in error_output:
                return jsonify({"error": "Video is unavailable or private"}), 400
            elif "Sign in to confirm your age" in error_output:
                return jsonify({"error": "Age-restricted video. Sign into your browser first."}), 400
            elif "This video is available to Music Premium members" in error_output:
                return jsonify({"error": "Premium-only content"}), 400
            elif "No supported JavaScript runtime" in error_output:
                return jsonify({"error": "Node.js required. Install: sudo apt install nodejs"}), 400
            elif "ERROR: unable to extract" in error_output or "ERROR: unable to download" in error_output:
                return jsonify({"error": "Failed to extract video info. YouTube may be blocking requests."}), 400
            else:
                return jsonify({"error": f"yt-dlp error: {error_output[:200]}"}), 400
        
        # Try to parse the JSON output
        if not result.stdout or not result.stdout.strip():
            app.logger.error("yt-dlp returned empty output")
            return jsonify({"error": "No data returned from yt-dlp. Check if cookies are working."}), 500
        
        # Extract only the JSON line (in case there are warnings)
        lines = result.stdout.strip().split('\n')
        json_line = None
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                json_line = line
                break
        
        if not json_line:
            app.logger.error(f"No JSON found in output. First 200 chars: {result.stdout[:200]}")
            return jsonify({"error": "Invalid output from yt-dlp"}), 500
        
        metadata = json.loads(json_line)
        app.logger.info(f"Successfully fetched info for: {metadata.get('title', 'Unknown')}")
        return jsonify({
            "title": metadata.get("title", "Unknown"),
            "thumbnail": metadata.get("thumbnail", "")
        })
        
    except subprocess.TimeoutExpired:
        app.logger.error("yt-dlp request timed out")
        return jsonify({"error": "Request timed out"}), 408
    except json.JSONDecodeError as e:
        app.logger.error(f"JSON decode error: {e}. Output was: {result.stdout[:200] if result.stdout else 'empty'}")
        return jsonify({"error": "Invalid response from yt-dlp. YouTube may be blocking requests."}), 500
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

@app.route("/mode", methods=["POST"])
def mode():
    """Toggle queue mode on/off."""
    global QUEUE_MODE
    data = request.get_json()
    if data:
        QUEUE_MODE = bool(data.get("queue", False))
    return jsonify({"queue": QUEUE_MODE})

@app.route("/download", methods=["POST"])
def download():
    """Start a new download job."""
    # Handle both JSON and form data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    
    app.logger.info(f"Download request: {data}")
    
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    url = data.get("url", "").strip()
    mode = data.get("mode", "mp4")
    
    if not url:
        app.logger.error("Missing URL in download request")
        return jsonify({"error": "URL required"}), 400
    
    if mode not in ["mp3", "mp4"]:
        app.logger.error(f"Invalid mode: {mode}")
        return jsonify({"error": "Invalid mode. Use 'mp3' or 'mp4'"}), 400
    
    job_id = str(uuid.uuid4())
    
    if mode == "mp3":
        outdir = Config.AUDIO_DIR
        cmd = [
            "yt-dlp",
            *Config.COMMON_OPTS,
            "--newline",
            "--no-warnings",
            "--progress-template", "%(progress)j",
            "-x",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            # Don't specify format - let yt-dlp choose best
            "-o", f"{outdir}/%(title)s.%(ext)s",
            url
        ]
    else:
        outdir = Config.VIDEO_DIR
        cmd = [
            "yt-dlp",
            *Config.COMMON_OPTS,
            "--newline",
            "--no-warnings",
            "--progress-template", "%(progress)j",
            # Don't force specific format - let yt-dlp auto-select and merge
            # This avoids the 403 errors from trying to download protected streams
            "-o", f"{outdir}/%(title)s.%(ext)s",
            url
        ]
    
    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "title": url,
            "mode": mode,
            "folder": str(outdir),
            "status": "queued" if QUEUE_MODE else "starting",
            "percent": 0,
            "speed": "",
            "eta": "",
            "cmd": cmd,
            "process": None
        }
        
        if QUEUE_MODE:
            queue.append(job_id)
            start_next_from_queue()
        else:
            if len(active_jobs) < Config.MAX_PARALLEL:
                threading.Thread(
                    target=run_job,
                    args=(job_id, cmd),
                    daemon=True
                ).start()
            else:
                jobs[job_id]["status"] = "queued"
                queue.append(job_id)
    
    return jsonify({"job_id": job_id})

@app.route("/progress")
def progress():
    """Get progress of all jobs."""
    with jobs_lock:
        safe = {}
        for job_id, j in jobs.items():
            safe[job_id] = {
                "status": j["status"],
                "percent": j.get("percent", 0),
                "speed": j.get("speed", ""),
                "eta": j.get("eta", ""),
                "mode": j.get("mode", "mp4")
            }
    return jsonify(safe)

@app.route("/cancel/<job_id>", methods=["POST"])
def cancel(job_id):
    """Cancel a running or queued job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"ok": True})
        
        job["status"] = "cancelled"
        
        if job.get("process"):
            try:
                job["process"].send_signal(signal.SIGTERM)
            except Exception as e:
                app.logger.error(f"Error terminating process: {e}")
    
    def cleanup():
        time.sleep(0.6)
        with jobs_lock:
            jobs.pop(job_id, None)
            active_jobs.discard(job_id)
            if job_id in queue:
                queue.remove(job_id)
        start_next_from_queue()
    
    threading.Thread(target=cleanup, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/open/<job_id>")
def open_folder(job_id):
    """Open the download folder for a completed job."""
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404
        folder = job["folder"]
    
    try:
        subprocess.Popen(["xdg-open", folder])
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.error(f"Error opening folder: {e}")
        return jsonify({"error": "Failed to open folder"}), 500

@app.route("/history")
def history():
    """Get download history."""
    return jsonify(load_history())

# ================= RUN =================
# ================= RUN =================
if __name__ == "__main__":
    import logging
    import threading
    import webbrowser
    import os
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    app.logger.info("Starting Echo Downloader")
    app.logger.info(f"Audio directory: {Config.AUDIO_DIR}")
    app.logger.info(f"Video directory: {Config.VIDEO_DIR}")

    # Open browser only once (important for Windows & PyInstaller)
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8000")

    # PyInstaller-safe check
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.2, open_browser).start()

    # IMPORTANT: debug=False always for Windows exe
    app.run(
        host="127.0.0.1",
        port=8000,
        debug=False,
        threaded=True
    )
