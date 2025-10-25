## Web GUI の起動手順

ブラウザから MP3 ファイルをアップロードして文字起こしする場合は、以下のコマンドを 1 回実行します。

```bash
./scripts/run_web.sh
```

スクリプトは自動で以下を行います。

- `.venv/` 仮想環境の作成と `pip install -r requirements.txt`
- `scripts/setup_whisper.sh` による whisper-cli のビルド（初回のみ）
- `scripts/download_model.sh` によるモデル取得（`WHISPER_MODEL_VARIANT` で指定可能）
- VAD モデルのダウンロード（未指定時）
- Flask サーバーの起動とブラウザ自動オープン (`http://127.0.0.1:5000/`)

アップロード可能なファイルサイズは既定で 3 GB (`WHISPER_GUI_MAX_UPLOAD`) です。より大きなファイルを扱う場合は環境変数で上限を調整してください。

---

## 主な環境変数

| 変数                                         | 役割                                                   | 既定値                           |
| -------------------------------------------- | ------------------------------------------------------ | -------------------------------- |
| `WHISPER_MODEL_VARIANT`                      | ダウンロードするモデルサイズ (`base`, `large-v3` など) | `base`                           |
| `WHISPER_OUTPUT_DIR`                         | 文字起こし結果の保存先                                 | `transcripts/`                   |
| `WHISPER_BINARY_PATH` / `WHISPER_MODEL_PATH` | 既存バイナリやモデルを利用したい場合に上書き           | 自動検出                         |
| `WHISPER_GUI_HOST` / `WHISPER_GUI_PORT`      | サーバーの bind 先                                     | `127.0.0.1` / `5000`             |
| `WHISPER_GUI_MAX_UPLOAD`                     | アップロード許容量（バイト）                           | `3 * 1024 * 1024 * 1024`         |
| `WHISPER_GUI_AUTO_OPEN`                      | ブラウザ自動起動を無効化する場合は `0`                 | `1`                              |
| `WHISPER_GUI_AUTO_OPEN_DELAY`                | ブラウザ起動までの遅延秒数                             | `3`                              |
| `WHISPER_GUI_TITLE`                          | Web ページのタイトル / 見出し                          | `Whisper.cpp MP3 文字起こし GUI` |
| `SKIP_PIP_INSTALL`                           | 依存インストールをスキップ                             | unset                            |

環境変数は起動コマンドの前に指定するか、`.env` 等で管理してください。

---

## ブラウザ操作の流れ

1. アップロードはドラッグ＆ドロップまたはクリックでファイル選択が可能です。
2. 言語やビーム幅などのパラメータを必要に応じて変更します。
3. 送信後はローディングオーバーレイが表示されるので、完了までブラウザを閉じずに待機してください。
4. 結果ページでは文字起こしテキストの表示と `.txt` ダウンロードリンクが提供されます。

---

## トラブルシューティング

- **PEP 668 (externally-managed-environment) が表示される**
  - スクリプト内で仮想環境を自動生成するため、通常は発生しません。既存 `.venv/` を削除した上で再実行してください。
- **HTTP 413 (Request Entity Too Large)**
  - `WHISPER_GUI_MAX_UPLOAD` をアップロードする MP3 サイズより大きく設定してください（例: `WHISPER_GUI_MAX_UPLOAD=$((5*1024*1024*1024)) ./scripts/run_web.sh`）。
- **ffmpeg が見つからないエラー**
  - `ffmpeg` が PATH に存在しない場合に発生します。パッケージマネージャでインストール後、再度実行してください。
- **ブラウザが自動で開かない**
  - 無効化している (`WHISPER_GUI_AUTO_OPEN=0`) か、ヘッドレス環境の可能性があります。手動で `http://<host>:<port>/` にアクセスしてください。

---

## 精度向上・運用 tips

- より大きいモデル (`large-v3` など) を利用すると認識精度が向上しますが、メモリ消費・推論時間が増えます。
- `--beam-size` と `--best-of` を大きくすると精度向上が見込める一方で処理時間が延びます。
- `--enable-vad` と VAD モデルを組み合わせると無音区間での誤検出を抑制できます。
- 長時間の MP3 は事前に分割し、並列に処理することでトータル時間を短縮できます。
