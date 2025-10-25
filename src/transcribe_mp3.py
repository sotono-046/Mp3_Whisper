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


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    whisper_dir = repo_root / "vendor" / "whisper.cpp"
    default_binary = whisper_dir / "build" / "bin" / "whisper-cli"
    default_model = whisper_dir / "models" / "ggml-base.bin"
    default_vad_model = whisper_dir / "models" / "ggml-silero-v5.1.2.bin"
    default_output = repo_root / "transcripts"

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
        sys.exit(f"whisper-cli が見つかりません: {binary}")
    if not model.exists():
        sys.exit(f"モデルファイルが見つかりません: {model}")
    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg が見つかりません。インストールしてください。")


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


def main() -> None:
    args = parse_args()
    if args.language and args.language.lower() == "auto":
        args.language = None

    mp3_path: Path = args.input
    if not mp3_path.exists():
        sys.exit(f"入力ファイルが存在しません: {mp3_path}")

    ensure_dependencies(args.binary, args.model)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="whisper_wav_") as temp_dir:
        wav_path = Path(temp_dir) / (mp3_path.stem + ".wav")
        convert_to_wav(mp3_path, wav_path)

        output_base = args.output_dir / mp3_path.stem
        if args.enable_vad and not args.vad_model.exists():
            sys.exit(
                "VAD モデルが見つかりません。"
                " vendor/whisper.cpp/models/download-vad-model.sh を実行して"
                " `ggml-silero-v5.1.2.bin` を取得してください。"
            )

        threads = args.threads if args.threads > 0 else (os.cpu_count() or 1)
        suppress_nst = not args.allow_nst
        run_whisper(
            args.binary,
            args.model,
            wav_path,
            output_base,
            args.language,
            threads=threads,
            beam_size=args.beam_size,
            best_of=args.best_of,
            temperature=args.temperature,
            suppress_nst=suppress_nst,
            enable_vad=args.enable_vad,
            vad_model=args.vad_model,
        )

        transcript_path = output_base.with_suffix(".txt")
        if not transcript_path.exists():
            sys.exit("文字起こし結果ファイルが生成されませんでした。whisper-cli の出力を確認してください。")

        text = transcript_path.read_text(encoding="utf-8")

        target_txt = args.output_dir / f"{mp3_path.stem}.txt"
        target_txt.write_text(text, encoding="utf-8")

        print(text)

        if args.keep_temp:
            target_wav = args.output_dir / wav_path.name
            shutil.copy2(wav_path, target_wav)


if __name__ == "__main__":
    main()
