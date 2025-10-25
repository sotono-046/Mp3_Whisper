"""Web GUI を提供する Flask アプリケーション。"""

from __future__ import annotations

import os
import secrets
import tempfile
import uuid
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from .transcribe_mp3 import TranscriptionError, transcribe_mp3_file

REPO_ROOT = Path(__file__).resolve().parents[1]
WHISPER_DIR = REPO_ROOT / "vendor" / "whisper.cpp"

_env_binary = os.environ.get("WHISPER_BINARY_PATH")
DEFAULT_BINARY = (
    Path(_env_binary) if _env_binary else WHISPER_DIR / "build" / "bin" / "whisper-cli"
)

_env_model = os.environ.get("WHISPER_MODEL_PATH")
DEFAULT_MODEL = (
    Path(_env_model) if _env_model else WHISPER_DIR / "models" / "ggml-base.bin"
)

_env_vad = os.environ.get("WHISPER_VAD_MODEL_PATH")
DEFAULT_VAD_MODEL = (
    Path(_env_vad) if _env_vad else WHISPER_DIR / "models" / "ggml-silero-v5.1.2.bin"
)

_env_output = os.environ.get("WHISPER_OUTPUT_DIR")
DEFAULT_OUTPUT_DIR = Path(_env_output) if _env_output else REPO_ROOT / "transcripts"
TEMP_ROOT = REPO_ROOT / "tmp"

ALLOWED_EXTENSIONS = {"mp3"}

APP_TITLE = os.environ.get("WHISPER_GUI_TITLE", "MP3 Whisper")
RESULT_HEADING = "文字起こし結果"

app = Flask(__name__)
app.secret_key = os.environ.get("WHISPER_GUI_SECRET", secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("WHISPER_GUI_MAX_UPLOAD", 256 * 1024 * 1024)
)

TEMP_ROOT.mkdir(parents=True, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template(
            "index.html",
            app_title=APP_TITLE,
            default_binary=str(DEFAULT_BINARY),
            default_model=str(DEFAULT_MODEL),
        )

    uploaded = request.files.get("mp3")
    if uploaded is None or uploaded.filename == "":
        flash("ファイルが選択されていません。", "error")
        return redirect(url_for("index"))

    filename = secure_filename(uploaded.filename)
    if not allowed_file(filename):
        flash("MP3 ファイルのみアップロードできます。", "error")
        return redirect(url_for("index"))

    language = request.form.get("language", "ja").strip() or "ja"
    beam_size = parse_int(request.form.get("beam_size", "5"), 5)
    best_of = parse_int(request.form.get("best_of", "5"), 5)
    temperature = parse_float(request.form.get("temperature", "0.0"), 0.0)
    threads = parse_int(request.form.get("threads", "0"), 0)
    enable_vad = "enable_vad" in request.form
    allow_nst = "allow_nst" in request.form

    unique_suffix = uuid.uuid4().hex[:8]
    output_name = f"{Path(filename).stem}_{unique_suffix}"

    try:
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT, prefix="upload_") as temp_dir:
            upload_path = Path(temp_dir) / filename
            uploaded.save(upload_path)

            text, transcript_path = transcribe_mp3_file(
                upload_path,
                model=DEFAULT_MODEL,
                binary=DEFAULT_BINARY,
                output_dir=DEFAULT_OUTPUT_DIR,
                language=language,
                threads=threads,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                suppress_nst=not allow_nst,
                enable_vad=enable_vad,
                vad_model=DEFAULT_VAD_MODEL,
                keep_temp=False,
                output_name=output_name,
            )
    except FileNotFoundError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except TranscriptionError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except Exception as exc:  # 予期せぬ例外
        flash(f"予期せぬエラーが発生しました: {exc}", "error")
        return redirect(url_for("index"))

    transcript_url = url_for("download_transcript", filename=transcript_path.name)

    return render_template(
        "result.html",
        result_title=f"{APP_TITLE} - {RESULT_HEADING}",
        result_heading=RESULT_HEADING,
        original_name=filename,
        transcript_text=text,
        transcript_url=transcript_url,
    )


@app.route("/transcripts/<path:filename>")
def download_transcript(filename: str):
    safe_name = secure_filename(filename)
    target = DEFAULT_OUTPUT_DIR / safe_name
    if not target.exists():
        flash("指定された文字起こしファイルが見つかりません。", "error")
        return redirect(url_for("index"))
    return send_from_directory(DEFAULT_OUTPUT_DIR, safe_name, as_attachment=True)


def run_app() -> None:
    host = os.environ.get("WHISPER_GUI_HOST", "127.0.0.1")
    port = int(os.environ.get("WHISPER_GUI_PORT", "5000"))
    debug = os.environ.get("WHISPER_GUI_DEBUG", "0") == "1"

    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_app()
