#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="$REPO_ROOT/vendor/whisper.cpp"
BIN_PATH="$WHISPER_DIR/build/bin/whisper-cli"
MODEL_VARIANT="${WHISPER_MODEL_VARIANT:-base}"
MODEL_PATH="$WHISPER_DIR/models/ggml-${MODEL_VARIANT}.bin"
VAD_MODEL_PATH="${WHISPER_VAD_MODEL_PATH:-$WHISPER_DIR/models/ggml-silero-v5.1.2.bin}"

VENV_DIR="${WHISPER_VENV_DIR:-$REPO_ROOT/.venv}"
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# venv 内の Python / pip を利用する
export PATH="$VENV_DIR/bin:$PATH"
PYTHON="${PYTHON:-python3}"

if [ -z "${SKIP_PIP_INSTALL:-}" ]; then
  "$PYTHON" -m pip install --upgrade pip
  "$PYTHON" -m pip install -r "$REPO_ROOT/requirements.txt"
fi

if [ ! -x "$BIN_PATH" ]; then
  bash "$REPO_ROOT/scripts/setup_whisper.sh"
fi

if [ ! -f "$MODEL_PATH" ]; then
  bash "$REPO_ROOT/scripts/download_model.sh" "$MODEL_VARIANT"
fi

if [ ! -f "$VAD_MODEL_PATH" ] && [ -z "${WHISPER_VAD_MODEL_PATH:-}" ]; then
  # VAD が必要な場合だけダウンロードする。明示的にパス指定されていなければ取得しておく。
  bash "$WHISPER_DIR/models/download-vad-model.sh"
fi

OUTPUT_DIR="${WHISPER_OUTPUT_DIR:-$REPO_ROOT/transcripts}"
mkdir -p "$OUTPUT_DIR"
mkdir -p "$REPO_ROOT/tmp"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "⚠️  ffmpeg が見つかりません。MP3 → WAV 変換でエラーになります。" >&2
fi

export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
export WHISPER_BINARY_PATH="$BIN_PATH"
export WHISPER_MODEL_PATH="$MODEL_PATH"
export WHISPER_OUTPUT_DIR="$OUTPUT_DIR"
if [ -f "$VAD_MODEL_PATH" ]; then
  export WHISPER_VAD_MODEL_PATH="$VAD_MODEL_PATH"
fi

if [ -z "${WHISPER_GUI_MAX_UPLOAD:-}" ]; then
  export WHISPER_GUI_MAX_UPLOAD=$((3 * 1024 * 1024 * 1024))
fi

HOST="${WHISPER_GUI_HOST:-127.0.0.1}"
PORT="${WHISPER_GUI_PORT:-5000}"
export WHISPER_GUI_HOST="$HOST"
export WHISPER_GUI_PORT="$PORT"

if [ "$HOST" = "0.0.0.0" ] || [ "$HOST" = "::" ]; then
  OPEN_HOST="127.0.0.1"
else
  OPEN_HOST="$HOST"
fi

if [ "${WHISPER_GUI_AUTO_OPEN:-1}" = "1" ]; then
  (
    sleep "${WHISPER_GUI_AUTO_OPEN_DELAY:-3}"
    "$PYTHON" -m webbrowser "http://${OPEN_HOST}:${PORT}/" >/dev/null 2>&1 || true
  ) &
fi

exec "$PYTHON" -m src.web_app
