#!/usr/bin/env bash

# whisper.cpp のビルドを自動化するスクリプト
#  - vendor/whisper.cpp を前提に cmake + ninja/Make を用いて whisper-cli を構築
#  - 依存: cmake, C/C++コンパイラ、make もしくは ninja

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHISPER_DIR="${REPO_DIR}/vendor/whisper.cpp"
BUILD_DIR="${WHISPER_DIR}/build"

if [[ ! -d "${WHISPER_DIR}" ]]; then
  echo "vendor/whisper.cpp が見つかりません。先にリポジトリを取得してください。" >&2
  exit 1
fi

if ! command -v cmake >/dev/null 2>&1; then
  echo "cmake コマンドが必要です。インストールしてから再実行してください。" >&2
  exit 1
fi

CORES=1
if command -v sysctl >/dev/null 2>&1; then
  CORES="$(sysctl -n hw.ncpu)"
elif command -v nproc >/dev/null 2>&1; then
  CORES="$(nproc)"
fi

cmake -S "${WHISPER_DIR}" \
      -B "${BUILD_DIR}" \
      -DCMAKE_BUILD_TYPE=Release \
      -DWHISPER_BUILD_TESTS=OFF \
      -DWHISPER_BUILD_EXAMPLES=ON \
      -DWHISPER_BUILD_BENCHMARKS=OFF \
      -DWHISPER_BUILD_UNIT_TESTS=OFF

cmake --build "${BUILD_DIR}" --target whisper-cli --config Release -- -j"${CORES}"

echo "✅ whisper-cli のビルドが完了しました: ${BUILD_DIR}/bin/whisper-cli"
