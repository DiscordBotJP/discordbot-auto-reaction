# AGENTS.md

このリポジトリで作業するときの共通ルールです。

## 基本コンテキスト

- Railway / Railpack で `python main.py` を常駐起動する Discord Bot です。
- Python は `.python-version` と `runtime.txt` に合わせます。
- Secret は `DISCORD_BOT_TOKEN` と `MONGO_URL` を使います。`TOKEN` は旧設定との互換 fallback です。
- ops-log-hub 連携は任意です。`OPS_LOG_HUB_URL` と `OPS_LOG_HUB_KEY` がない場合も Bot は起動します。
- アーキテクチャの要約は `docs/ARCHITECTURE.md` を先に読んでください。
- HTTP サーバーはありません。Railway の公開ドメインや HTTP healthcheck を前提にしないでください。

## 主要コマンド

```bash
python -m pip install -r requirements.txt
python -m py_compile $(find . -path './.git' -prune -o -name '*.py' -print)
python main.py
```

## ドキュメント更新

アップデートを行う場合は、同じ Pull Request で関連ドキュメントも更新します。

対象例:

- コード
- 設定
- 依存関係
- 仕様
- 権限
- データ構造
- 導入手順
- 運用手順

確認対象:

- README.md
- docs/SPECIFICATION.md
- docs/SETUP.md
- docs/OPERATIONS.md
- docs/TROUBLESHOOTING.md
- docs/ARCHITECTURE.md
- AGENTS.md

Pull Request には、更新したドキュメントの一覧を記載します。
