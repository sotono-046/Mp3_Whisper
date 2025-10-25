## プロジェクト概要

Whisper.cpp MP3 文字起こしツールは、`vendor/whisper.cpp` に同梱された whisper.cpp バイナリを利用し、ローカル環境で MP3 → テキスト変換を行うためのラッパーです。CLI と Web GUI の両方を提供し、下記の手順でセットアップできます。

---

## 必要環境

- macOS または Linux
- `cmake` と C/C++ コンパイラ（Xcode Command Line Tools 等）
- `python3`
- `ffmpeg`（MP3 → WAV 変換に利用）
- モデルダウンロード用のネットワーク接続

Homebrew 利用時のインストール例:

```bash
brew install cmake ffmpeg python
```

---

## 初期セットアップ

1. whisper.cpp のソースは `vendor/whisper.cpp` に配置済みです。必要であれば upstream と同期してください。
2. whisper-cli バイナリをビルドします。

   ```bash
   ./scripts/setup_whisper.sh
   ```

   成功すると `vendor/whisper.cpp/build/bin/whisper-cli` が生成されます。

3. 必要なモデルをダウンロードします（例: base）。

   ```bash
   ./scripts/download_model.sh base
   ```

   ダウンロードされたモデルは `vendor/whisper.cpp/models/ggml-base.bin` に配置されます。

---

## CLI での動作確認

1. 任意の MP3 ファイルを用意し、以下のコマンドを実行します。

   ```bash
   python3 src/transcribe_mp3.py /path/to/audio.mp3
   ```

2. 既定パラメータ

   - バイナリ: `vendor/whisper.cpp/build/bin/whisper-cli`
   - モデル: `vendor/whisper.cpp/models/ggml-base.bin`
   - 出力先: `transcripts/<元ファイル名>.txt`
   - 言語: 日本語 (`-l ja`)

3. 代表的なオプション

   - `-m /path/to/model.bin` : 利用するモデルを明示
   - `-b /path/to/whisper-cli` : バイナリパスを指定
   - `-o /path/to/output_dir` : 出力ディレクトリを変更
   - `-l auto` : 言語自動検出
   - `--beam-size`, `--best-of`, `--temperature` : 推論パラメータ調整
   - `--enable-vad`, `--vad-model` : VAD モデルを利用
   - `--allow-nst` : 非音声トークン抑制解除

4. 動作確認のヒント

   - `vendor/whisper.cpp/samples/jfk.wav` を MP3 に変換し、テストに利用できます。

     ```bash
     ffmpeg -i vendor/whisper.cpp/samples/jfk.wav -codec:a libmp3lame -qscale:a 2 samples/jfk.mp3
     python3 src/transcribe_mp3.py samples/jfk.mp3
     ```

`ffmpeg` が認識されない場合は、事前にインストールされているか確認してください。

---
