#!/usr/bin/env python3
"""MP3 を文字起こしするためのラッパー CLI."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class TranscriptionError(RuntimeError):
    """文字起こし処理で発生したエラーを表します。"""


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    whisper_dir = repo_root / "vendor" / "whisper.cpp"
    default_binary = whisper_dir / "build" / "bin" / "whisper-cli"
    default_model = whisper_dir / "models" / "ggml-base.bin"
    default_vad_model = whisper_dir / "models" / "ggml-silero-v5.1.2.bin"
    default_output = repo_root / "transcripts"

    env_binary = os.environ.get("WHISPER_BINARY_PATH")
    if env_binary:
        default_binary = Path(env_binary)

    env_model = os.environ.get("WHISPER_MODEL_PATH")
    if env_model:
        default_model = Path(env_model)

    env_vad_model = os.environ.get("WHISPER_VAD_MODEL_PATH")
    if env_vad_model:
        default_vad_model = Path(env_vad_model)

    env_output = os.environ.get("WHISPER_OUTPUT_DIR")
    if env_output:
        default_output = Path(env_output)

    parser = argparse.ArgumentParser(
        description="ローカル MP3 を whisper.cpp で文字起こしします。"
    )
    parser.add_argument("input", type=Path, help="文字起こし対象の MP3 ファイル")
    parser.add_argument(
        "-m",
        "--model",
        type=Path,
        default=default_model,
        help=f"ggml モデルファイルへのパス (既定: {default_model})",
    )
    parser.add_argument(
        "-b",
        "--binary",
        type=Path,
        default=default_binary,
        help=f"whisper-cli バイナリへのパス (既定: {default_binary})",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=default_output,
        help=f"出力ディレクトリ (既定: {default_output})",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default="ja",
        help="言語コード (例: ja, en)。'auto' を指定すると自動判定します (既定: ja)。",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="中間 WAV ファイルを削除せずに保存します。",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=0,
        help="whisper-cli に渡すスレッド数 (0 で自動判定)。",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="ビームサーチのビーム幅。",
    )
    parser.add_argument(
        "--best-of",
        type=int,
        default=5,
        help="保持する候補数。",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="サンプリング温度 (0.0〜1.0)。",
    )
    parser.add_argument(
        "--enable-vad",
        action="store_true",
        help="VAD (音声区間検出) を有効化します。",
    )
    parser.add_argument(
        "--vad-model",
        type=Path,
        default=default_vad_model,
        help=f"VAD 用モデルファイルパス (既定: {default_vad_model})",
    )
    parser.add_argument(
        "--allow-nst",
        action="store_true",
        help="非音声トークン (音楽など) の抑制を解除します。",
    )
    return parser.parse_args()


def ensure_dependencies(binary: Path, model: Path) -> None:
    if not binary.exists():
        raise TranscriptionError(f"whisper-cli が見つかりません: {binary}")
    if not model.exists():
        raise TranscriptionError(f"モデルファイルが見つかりません: {model}")
    if shutil.which("ffmpeg") is None:
        raise TranscriptionError("ffmpeg が見つかりません。インストールしてください。")


def convert_to_wav(source: Path, target: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ar",
        "16000",
        "-ac",
        "1",
        "-f",
        "wav",
        str(target),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)


def run_whisper(
    binary: Path,
    model: Path,
    wav_path: Path,
    output_base: Path,
    language: str | None,
    *,
    threads: int,
    beam_size: int,
    best_of: int,
    temperature: float,
    suppress_nst: bool,
    enable_vad: bool,
    vad_model: Path,
) -> None:
    cmd = [
        str(binary),
        "-m",
        str(model),
        "-f",
        str(wav_path),
        "-otxt",
        "-of",
        str(output_base),
    ]
    cmd.extend(["-t", str(threads)])
    cmd.extend(["-bs", str(beam_size), "-bo", str(best_of)])
    cmd.extend(["-tp", f"{temperature:.2f}"])
    if suppress_nst:
        cmd.append("--suppress-nst")
    if enable_vad:
        cmd.append("--vad")
        cmd.extend(["-vm", str(vad_model)])
    if language:
        cmd.extend(["-l", language])
    subprocess.run(cmd, check=True)


def transcribe_mp3_file(
    mp3_path: Path,
    *,
    model: Path,
    binary: Path,
    output_dir: Path,
    language: str | None,
    threads: int,
    beam_size: int,
    best_of: int,
    temperature: float,
    suppress_nst: bool,
    enable_vad: bool,
    vad_model: Path,
    keep_temp: bool = False,
    output_name: str | None = None,
) -> tuple[str, Path]:
    if language and language.lower() == "auto":
        language = None

    if not mp3_path.exists():
        raise FileNotFoundError(f"入力ファイルが存在しません: {mp3_path}")

    ensure_dependencies(binary, model)

    if enable_vad and not vad_model.exists():
        raise TranscriptionError(
            "VAD モデルが見つかりません。"
            " vendor/whisper.cpp/models/download-vad-model.sh を実行して"
            " `ggml-silero-v5.1.2.bin` を取得してください。"
        )

    resolved_threads = threads if threads > 0 else (os.cpu_count() or 1)

    output_dir.mkdir(parents=True, exist_ok=True)
    name = output_name or mp3_path.stem

    try:
        with tempfile.TemporaryDirectory(prefix="whisper_wav_") as temp_dir:
            wav_path = Path(temp_dir) / f"{name}.wav"
            convert_to_wav(mp3_path, wav_path)

            output_base = output_dir / name
            run_whisper(
                binary,
                model,
                wav_path,
                output_base,
                language,
                threads=resolved_threads,
                beam_size=beam_size,
                best_of=best_of,
                temperature=temperature,
                suppress_nst=suppress_nst,
                enable_vad=enable_vad,
                vad_model=vad_model,
            )

            transcript_path = output_base.with_suffix(".txt")
            if not transcript_path.exists():
                raise TranscriptionError(
                    "文字起こし結果ファイルが生成されませんでした。whisper-cli の出力を確認してください。"
                )

            text = transcript_path.read_text(encoding="utf-8")

            if keep_temp:
                target_wav = output_dir / wav_path.name
                shutil.copy2(wav_path, target_wav)

            return text, transcript_path
    except subprocess.CalledProcessError as exc:
        raise TranscriptionError("外部コマンドの実行に失敗しました。") from exc


def main() -> None:
    args = parse_args()
    mp3_path: Path = args.input
    suppress_nst = not args.allow_nst

    try:
        text, _ = transcribe_mp3_file(
            mp3_path,
            model=args.model,
            binary=args.binary,
            output_dir=args.output_dir,
            language=args.language,
            threads=args.threads,
            beam_size=args.beam_size,
            best_of=args.best_of,
            temperature=args.temperature,
            suppress_nst=suppress_nst,
            enable_vad=args.enable_vad,
            vad_model=args.vad_model,
            keep_temp=args.keep_temp,
            output_name=mp3_path.stem,
        )
    except FileNotFoundError as exc:
        sys.exit(str(exc))
    except TranscriptionError as exc:
        sys.exit(str(exc))

    target_txt = args.output_dir / f"{mp3_path.stem}.txt"
    target_txt.write_text(text, encoding="utf-8")

    print(text)


if __name__ == "__main__":
    main()
