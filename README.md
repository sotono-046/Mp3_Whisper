# Whisper.cpp MP3 文字起こし CLI

ローカルの MP3 ファイルを [ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp) を用いて文字起こしする簡易 CLI です。  
セットアップ用スクリプトと Python ラッパーを同梱しており、モデルの取得とバイナリビルドを済ませればすぐに実行できます。

## 前提条件

- macOS or Linux
- `cmake`、C/C++ コンパイラ（Xcode Command Line Tools など）
- `python3`
- `ffmpeg`（MP3 → WAV 変換に使用）
- ネットワーク接続（モデルダウンロード時）

Homebrew を利用している場合の例:

```bash
brew install cmake ffmpeg python
```

## セットアップ

1. whisper.cpp のソースは `vendor/whisper.cpp` に配置済みです。別のバージョンが必要な場合は適宜更新してください。
2. whisper.cpp をビルド:

   ```bash
   ./scripts/setup_whisper.sh
   ```

   成功すると `vendor/whisper.cpp/build/bin/whisper-cli` が生成されます。

3. モデルをダウンロード（例: `base`）:

   ```bash
   ./scripts/download_model.sh base
   ```

   ダウンロードされたモデルは `vendor/whisper.cpp/models/ggml-base.bin` に配置されます。

## 文字起こしの実行

```bash
python3 src/transcribe_mp3.py /path/to/audio.mp3
```

既定では以下を使用します。

- バイナリ: `vendor/whisper.cpp/build/bin/whisper-cli`
- モデル: `vendor/whisper.cpp/models/ggml-base.bin`
- 出力先: `transcripts/<元ファイル名>.txt`
- 言語: 日本語 (`-l ja`)

主なオプション:

- `-m /path/to/model.bin` : 使いたいモデルを指定
- `-b /path/to/whisper-cli` : ビルドしたバイナリを指定
- `-o /path/to/output_dir` : 出力ディレクトリを指定
- `-l ja` : 言語コードを明示（`auto` を指定すると自動判定）
- `--temperature 0.1` : サンプリング温度を調整
- `--beam-size 8 --best-of 8` : ビームサーチの幅と保持候補数を拡大
- `--enable-vad` : VAD (音声区間検出) を有効化（`--vad-model` でパス指定可能）
- `--allow-nst` : 音楽などの非音声トークン抑制を無効化
- `--keep-temp` : 中間の WAV ファイルを保存

出力テキストは標準出力にも表示され、ファイルにも保存されます。

## 動作確認のヒント

1. `vendor/whisper.cpp/samples/jfk.wav` など WAV サンプルを MP3 へ変換:

   ```bash
   ffmpeg -i vendor/whisper.cpp/samples/jfk.wav -codec:a libmp3lame -qscale:a 2 samples/jfk.mp3
   ```

2. 変換した MP3 を CLI で処理:

   ```bash
   python3 src/transcribe_mp3.py samples/jfk.mp3
   ```

`ffmpeg` 未導入の場合、上記コマンドおよび CLI はエラーになります。先にインストールしてください。

## 精度向上のポイント

- より大きいモデルを利用する: `./scripts/download_model.sh large-v3` で `ggml-large-v3.bin` を取得し、`-m vendor/whisper.cpp/models/ggml-large-v3.bin` を指定すると日本語の認識率が向上します。
- ビームサーチ幅・温度を調整する: `--beam-size 8 --best-of 8 --temperature 0.1` など安定寄りのパラメータにすると誤認識が減ることがあります。
- 音声区間検出 (VAD) を有効化する: `--enable-vad` を付与し、事前に `vendor/whisper.cpp/models/download-vad-model.sh` で VAD モデル (`ggml-silero-v5.1.2.bin`) を取得すると無音区間で「音楽」トークンが出にくくなります。
- 録音音量が低い場合は `ffmpeg` などで正規化してから処理すると改善することがあります。

## ディレクトリ構成

```
.
├── README.md
├── scripts
│   ├── download_model.sh        # モデル取得ラッパー
│   └── setup_whisper.sh         # whisper.cpp のビルドスクリプト
├── src
│   └── transcribe_mp3.py        # MP3 文字起こし CLI
└── vendor
    └── whisper.cpp              # whisper.cpp サブディレクトリ
```

## 今後の拡張例

- `--timestamps` などの追加引数パススルー
- GUI 化（Electron など）
