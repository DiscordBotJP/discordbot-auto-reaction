# discordbot-auto-reaction

Discord チャンネルごとに設定した絵文字を、投稿されたメッセージへ自動付与する Discord Bot です。
既存メッセージへのリアクション補完と、自分のメッセージに付いたリアクションの内訳確認にも対応しています。

## 概要

この Bot は、サーバー内の特定チャンネルに対して「このチャンネルでは常にこの絵文字を付ける」という設定を保存し、以後そのチャンネルへ投稿されたメッセージへ自動でリアクションを付与します。

主な用途は次のとおりです。

- お知らせ・募集・投票導線などに毎回同じリアクションを付ける
- イベント用チャンネルで、参加・確認・投票用の絵文字を統一する
- 既存メッセージに対して、設定済みリアクションを一括補完する
- 自分の投稿に付いたリアクションのユーザー内訳を DM で確認する

## ドキュメント

| ドキュメント | 内容 |
| --- | --- |
| [アーキテクチャ](docs/ARCHITECTURE.md) | 人間と AI エージェント向けの構成、責務、変更時の注意点 |
| [仕様書](docs/SPECIFICATION.md) | 機能、権限、データ構造、処理フロー、制約を網羅した仕様書 |
| [導入手順](docs/SETUP.md) | ローカル環境、Discord Developer Portal、MongoDB、起動手順 |
| [運用手順](docs/OPERATIONS.md) | 日常運用、設定変更、補完実行、バックアップ、リリース手順 |
| [トラブルシューティング](docs/TROUBLESHOOTING.md) | 起動失敗、コマンド未表示、リアクション不可、DM 不達などの対処 |

## 主な機能

### 1. チャンネル別の自動リアクション

管理権限を持つユーザーがチャンネルごとに絵文字を設定すると、そのチャンネルに投稿されたメッセージへ Bot が自動でリアクションを付けます。

対応する絵文字は次の 2 種類です。

- Unicode 絵文字
- Discord カスタム絵文字

### 2. 設定済みリアクションの確認

スラッシュコマンド `/リアクション設定確認` で、現在のチャンネルに設定されている絵文字を確認できます。

### 3. 既存メッセージへのリアクション補完

スラッシュコマンド `/リアクション補完` で、現在のチャンネル内の全メッセージに対して、設定済み絵文字を一括付与できます。

また、メッセージ右クリックメニューの `リアクション補完` から、指定した 1 件のメッセージだけにリアクションを補完できます。

### 4. リアクション内訳の確認

メッセージ右クリックメニューの `リアクション確認` から、自分のメッセージに付いたリアクションの内訳を dashboard に保存し、DM でも受け取れます。

Bot ユーザーは集計対象から除外されます。

## 技術構成

| 項目 | 内容 |
| --- | --- |
| 言語 | Python |
| Python バージョン | 3.14.5 |
| Discord ライブラリ | discord.py 2.7.1 |
| 永続化 | MongoDB |
| MongoDB クライアント | motor |
| 絵文字抽出 | emoji / re |
| 補助ライブラリ | Daug |
| 起動ファイル | `main.py` |
| 実行環境 | Railway / Railpack |

## ディレクトリ構成

```text
.
├── main.py
├── railway.json
├── .python-version
├── requirements.txt
├── runtime.txt
├── Procfile
├── LICENSE
├── constants/
│   └── __init__.py
├── extensions/
│   ├── auto_reaction.py
│   └── reaction_listup.py
└── utils/
    ├── __init__.py
    ├── database.py
    └── ops_log.py
```

## 必要な Discord 設定

### OAuth2 Scopes

Bot を招待する際は、最低限次のスコープが必要です。

- `bot`
- `applications.commands`

### Bot Permissions

運用チャンネルで最低限必要な権限は次のとおりです。

- チャンネルを見る
- メッセージを送信
- メッセージ履歴を読む
- リアクションを追加
- 外部の絵文字を使用
- 埋め込みリンク
- アプリケーションコマンドを使用

設定操作を行うユーザーには、機能に応じて次の権限が必要です。

| 操作 | 必要権限 |
| --- | --- |
| Bot メンションによるリアクション設定・解除 | チャンネル管理 |
| `/リアクション設定確認` | 管理者 |
| `/リアクション補完` | 管理者 |
| 右クリックメニュー `リアクション補完` | 管理者 |
| 右クリックメニュー `リアクション確認` | 対象メッセージの投稿者本人 |

### Privileged Gateway Intents

現在の実装では `discord.Intents.all()` を使用し、メッセージ本文を読んで設定コマンドを判定します。
Discord Developer Portal で、少なくとも Message Content Intent を有効にしてください。

`Intents.all()` のまま運用する場合、Developer Portal 側の Privileged Gateway Intents 設定とコード側の Intents 指定が一致している必要があります。

## 導入手順

### 1. 依存関係をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell の場合は次のように有効化します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. `.env` を作成

```env
DISCORD_BOT_TOKEN=
MONGO_URL=
OPS_LOG_HUB_URL=
OPS_LOG_HUB_KEY=
OPS_LOG_PROJECT=discordbot-auto-reaction
OPS_LOG_ENVIRONMENT=production
```

`OPS_LOG_HUB_URL` は `https://<ops-log-hub-domain>/api/ingest/discord-bot` の形式です。

`OPS_LOG_HUB_URL` と `OPS_LOG_HUB_KEY` が未設定の場合、Bot はログ送信なしで動作します。

### 3. Bot を起動

```bash
python main.py
```

起動時に次の処理が行われます。

1. `extensions.auto_reaction` を読み込む
2. `extensions.reaction_listup` を読み込む
3. アプリケーションコマンドを Discord に同期する
4. MongoDB からリアクション設定を読み込み、メモリキャッシュに反映する
5. ops-log-hub 設定がある場合、起動完了イベントを送信する

## 運用ログ

ops-log-hub を設定すると、以下のイベントを送信します。

- `startup`: Bot 起動完了
- `command_error`: slash command / prefix command の未処理エラー
- `config_error`: 起動時の拡張読み込み、slash command 同期、DB キャッシュ初期化の失敗

メッセージ本文、Token、Webhook URL などの secret は送信しません。

## 使い方

### チャンネルに自動リアクションを設定する

対象チャンネルで、Bot へのメンションと絵文字を投稿します。

```text
@BotName 👍 ✅ 🎉
```

設定に成功すると、Bot が `自動リアクション設定を追加しました` と返信します。
以後、そのチャンネルに投稿されたメッセージへ設定済みの絵文字が付与されます。

### チャンネルの自動リアクション設定を解除する

対象チャンネルで、Bot へのメンションのみを投稿します。

```text
@BotName
```

設定に成功すると、Bot が `自動リアクション設定を解除しました` と返信します。

### 設定内容を確認する

対象チャンネルで次のスラッシュコマンドを実行します。

```text
/リアクション設定確認
```

### チャンネル内の既存メッセージへ補完する

対象チャンネルで次のスラッシュコマンドを実行します。

```text
/リアクション補完
```

この操作はチャンネル内の全メッセージを走査します。メッセージ数が多いチャンネルでは時間がかかり、Discord API のレート制限を受ける可能性があります。

### 単一メッセージへ補完する

対象メッセージを右クリックし、アプリメニューから `リアクション補完` を実行します。

### 自分のメッセージのリアクション内訳を確認する

自分が投稿したメッセージを右クリックし、アプリメニューから `リアクション確認` を実行します。
Bot が MongoDB に確認結果を保存し、DM にもリアクション別のユーザー一覧を送信します。

## コマンド一覧

| 種別 | 名称 | 用途 | 実行条件 |
| --- | --- | --- | --- |
| メンション | `@BotName 絵文字...` | 現在のチャンネルに自動リアクションを設定 | チャンネル管理権限 |
| メンション | `@BotName` | 現在のチャンネルの設定を解除 | チャンネル管理権限 |
| Slash Command | `/リアクション設定確認` | 現在のチャンネルの設定を確認 | 管理者 |
| Slash Command | `/リアクション補完` | 現在のチャンネルの全履歴へ補完 | 管理者 |
| Message Context Menu | `リアクション補完` | 選択した 1 件のメッセージへ補完 | 管理者 |
| Message Context Menu | `リアクション確認` | 自分のメッセージのリアクション内訳を dashboard / DM で確認 | 投稿者本人 |

## データ仕様

MongoDB の `auto_reaction` データベースに、チャンネル単位の設定とリアクション確認結果を保存します。

### 自動リアクション設定: `emojis`

```json
{
  "channel_id": 123456789012345678,
  "emojis": ["👍", "✅", "<:custom:123456789012345678>"]
}
```

| フィールド | 型 | 内容 |
| --- | --- | --- |
| `channel_id` | integer | Discord チャンネル ID |
| `emojis` | string[] | 自動付与する絵文字の配列 |

### リアクション確認結果: `reaction_checks`

```json
{
  "checked_at": "2026-06-09T12:00:00+09:00",
  "requested_by_user_id": "123456789012345678",
  "guild_id": "123456789012345678",
  "guild_name": "Example Server",
  "channel_id": "123456789012345678",
  "channel_name": "general",
  "message_id": "123456789012345678",
  "message_jump_url": "https://discord.com/channels/...",
  "reaction_total": 3,
  "reaction_kind_count": 2,
  "reactions": [
    {
      "emoji": "👍",
      "count": 2,
      "users": [
        {
          "user_id": "123456789012345678",
          "name": "user_name",
          "display_name": "表示名"
        }
      ]
    }
  ]
}
```

dashboard の `/user` は、`requested_by_user_id` がログイン中 Discord ユーザー ID と一致する `reaction_checks` だけを表示します。

起動時に MongoDB から全設定を読み込み、メモリキャッシュに展開します。
設定追加・更新・削除時は MongoDB とメモリキャッシュの両方を更新します。

## デプロイ

`Procfile` は次の内容です。

```Procfile
worker: python main.py
```

Railway では `railway.json` の Railpack 設定と `python main.py` の start command を使用します。
この Bot は HTTP サーバーを提供しないため、公開ドメインや HTTP healthcheck は不要です。

詳細は [導入手順](docs/SETUP.md) と [運用手順](docs/OPERATIONS.md) を参照してください。

## 既知の注意点

- 自動リアクションは Discord API の制約を受けます。Bot が使用できないカスタム絵文字、権限不足、削除済み絵文字などは付与できません。
- チャンネル全履歴への補完は大量の API リクエストを発生させます。大規模チャンネルでは実行タイミングに注意してください。
- `リアクション確認` は DM を使用します。対象ユーザーが DM を閉じている場合、結果を受け取れない可能性があります。
- 現在の実装では `discord.Intents.all()` を使用しています。必要最小限の Intents に絞る場合はコード側の調整が必要です。

## ライセンス

MIT License
