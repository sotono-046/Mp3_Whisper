#!/usr/bin/env bash

# whisper.cpp が提供するモデルダウンロードスクリプトの薄いラッパー
# 例: ./scripts/download_model.sh base

set -euo pipefail

MODEL="${1:-base}"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="${REPO_DIR}/vendor/whisper.cpp"
SCRIPT_PATH="${WHISPER_DIR}/models/download-ggml-model.sh"

if [[ ! -f "${SCRIPT_PATH}" ]]; then
  echo "download-ggml-model.sh が見つかりません。vendor/whisper.cpp の配置を確認してください。" >&2
  exit 1
fi

bash "${SCRIPT_PATH}" "${MODEL}"
