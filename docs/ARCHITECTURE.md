# アーキテクチャ

この文書は、人間の保守者と AI エージェントが短時間で設計意図を把握するための作業用コンテキストです。

## 1. システム概要

`discordbot-auto-reaction` は、Discord Gateway に常時接続する単一プロセスの Bot です。HTTP サーバーはありません。Railway では worker 的な常駐プロセスとして `python main.py` を起動します。

## 2. 実行環境

| 項目 | 値 |
| --- | --- |
| 主対象 | Railway / Railpack |
| Python | 3.14.5 |
| discord.py | 2.7.1 |
| 起動 | `python main.py` |
| 必須 Secret | `DISCORD_BOT_TOKEN`, `MONGO_URL` |
| 任意 Secret | `OPS_LOG_HUB_URL`, `OPS_LOG_HUB_KEY` |
| 永続化 | MongoDB |

Railway の設定は `railway.json` に置きます。Python バージョンは `.python-version` を主、`runtime.txt` を互換用として扱います。

## 3. モジュール責務

| パス | 責務 |
| --- | --- |
| `main.py` | Bot インスタンス作成、Extension load、コマンド同期、初期キャッシュ、ops-log-hub への起動/エラー通知 |
| `constants/__init__.py` | `.env` / 環境変数から設定を読み込み、必須 Secret 未設定時に fail-fast |
| `caches/__init__.py` | チャンネル別リアクション設定のプロセスメモリキャッシュ |
| `utils/database.py` | MongoDB 接続、設定の取得・更新・削除、起動時キャッシュ復元 |
| `utils/__init__.py` | Unicode / Discord カスタム絵文字の抽出 |
| `utils/ops_log.py` | ops-log-hub への任意の運用イベント送信 |
| `extensions/auto_reaction.py` | 自動リアクション、設定確認、全履歴補完、単一補完 |
| `extensions/reaction_listup.py` | 自分のメッセージに付いたリアクション内訳の DM 送信 |

## 4. 起動フロー

1. `constants` が環境変数を読み込む。
2. `DISCORD_BOT_TOKEN` または `MONGO_URL` が未設定なら起動を止める。
3. `MyBot` が `discord.Intents.all()` で初期化される。
4. `setup_hook()` が `extensions.auto_reaction` と `extensions.reaction_listup` を load する。
5. `bot.tree.sync()` でアプリケーションコマンドを同期する。
6. `cache_emojis()` が MongoDB の `auto_reaction.emojis` を `caches.emojis_cache` に読み込む。
7. ops-log-hub 設定がある場合、起動完了または設定エラーを送信する。

## 5. データモデル

MongoDB:

```json
{
  "channel_id": 123456789012345678,
  "emojis": ["👍", "✅", "<:custom:123456789012345678>"]
}
```

キャッシュ:

```python
emojis_cache: dict[int, list[str]]
```

MongoDB を直接編集しても、稼働中プロセスのキャッシュには反映されません。直接編集後は Railway で redeploy / restart してください。

## 6. Railway 運用上の前提

- 1 サービス 1 レプリカを前提にします。
- 複数レプリカにするとメモリキャッシュが分岐します。
- 公開 HTTP endpoint は不要です。
- Railway Variables に Secret を置き、リポジトリには `.env` をコミットしません。
- `railway.json` の restart policy は `ON_FAILURE` です。

## 7. 既知の設計課題

- Intents が必要最小限ではありません。
- `channel_id` の unique index がありません。
- リアクション付与失敗の集計や通知がありません。
- 全履歴補完に上限、進捗、キャンセルがありません。
- DM 送信失敗時のユーザー向け fallback がありません。
- テストと CI がありません。
