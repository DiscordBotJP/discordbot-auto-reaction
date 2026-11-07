# 導入手順

> 保存層は`DATABASE_PROVIDER`で選択します。以下の`MONGO_URL`設定・MongoDB障害対応は`mongodb`モード向けです。D1モードの必須変数と切り戻し条件は[保存層の運用](STORAGE.md)を参照してください。D1の401/403はBot専用tokenと対象namespaceを、タイムアウトはWorkerの可用性を確認します。失敗時にMongoDBへ自動fallbackしません。

この文書は `discordbot-auto-reaction` を新規環境で起動するための手順をまとめたものです。

## 1. 前提条件

以下を用意してください。

- Python 3.14.5
- Discord Bot Token
- MongoDB 接続 URL
- Bot を招待できる Discord サーバー
- Bot に必要な権限を付与できる管理権限

このリポジトリでは `.python-version` に `3.14.5`、`runtime.txt` に `python-3.14.5` が指定されています。

## 2. Discord Developer Portal の設定

### 2.1 Application を作成

1. Discord Developer Portal を開く
2. `New Application` を選択
3. 任意のアプリケーション名を入力して作成
4. 左メニューの `Bot` から Bot を作成
5. Bot Token を取得する

Bot Token は外部へ公開しないでください。GitHub にコミットしてはいけません。

### 2.2 Privileged Gateway Intents

現在の実装では `discord.Intents.all()` を使用します。

`Bot` 設定画面で、少なくとも次を有効にしてください。

- Message Content Intent

運用方針として `Intents.all()` を維持する場合は、必要な Privileged Gateway Intents を Developer Portal 側でも有効化してください。

### 2.3 OAuth2 URL Generator

`OAuth2` → `URL Generator` で次の Scopes を選択します。

- `bot`
- `applications.commands`

Bot Permissions は最低限、次を選択してください。

- View Channels
- Send Messages
- Read Message History
- Add Reactions
- Use External Emojis
- Embed Links
- Use Application Commands

運用上、補完や確認を確実に行うため、対象チャンネルでこれらの権限が deny されていないことを確認してください。

## 3. MongoDB を用意する

MongoDB Atlas などで MongoDB を用意し、接続 URL を取得します。

接続 URL の例です。

```text
mongodb+srv://user:password@example.mongodb.net/?retryWrites=true&w=majority
```

Bot は次のデータベース・コレクションを使用します。

| 項目 | 名称 |
| --- | --- |
| database | `auto_reaction` |
| collection | `emojis` |

明示的にデータベースやコレクションを事前作成しなくても、初回 upsert 時に作成されます。

## 4. リポジトリを準備する

```bash
git clone https://github.com/DiscordBotJP/discordbot-auto-reaction.git
cd discordbot-auto-reaction
```

## 5. Python 仮想環境を作成する

macOS / Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## 6. 依存関係をインストールする

```bash
pip install -r requirements.txt
```

`requirements.txt` には次の依存関係が含まれます。

```text
emoji
discord.py==2.7.1
python-dotenv==1.2.2
motor==3.7.1
Daug==2023.12.9.1
```

## 7. `.env` を作成する

リポジトリ直下に `.env` を作成します。

```env
DISCORD_BOT_TOKEN=YOUR_DISCORD_BOT_TOKEN
MONGO_URL=YOUR_MONGODB_CONNECTION_URL
OPS_LOG_HUB_URL=
OPS_LOG_HUB_KEY=
OPS_LOG_PROJECT=discordbot-auto-reaction
OPS_LOG_ENVIRONMENT=development
```

`.env` は `.gitignore` により除外されています。誤ってコミットしないでください。

## 8. 起動する

```bash
python main.py
```

起動時に次が実行されます。

1. `extensions.auto_reaction` の読み込み
2. `extensions.reaction_listup` の読み込み
3. Discord アプリケーションコマンドの同期
4. MongoDB からリアクション設定を読み込み
5. メモリキャッシュへ設定を展開

## 9. Bot をサーバーへ招待する

OAuth2 URL Generator で生成した URL から、対象サーバーへ Bot を招待します。

招待後、対象チャンネルで Bot に次の権限があることを確認してください。

- チャンネルを見る
- メッセージを送信
- メッセージ履歴を読む
- リアクションを追加
- 外部の絵文字を使用
- 埋め込みリンク
- アプリケーションコマンドを使用

## 10. 動作確認

### 10.1 自動リアクションを設定する

対象チャンネルで、チャンネル管理権限を持つユーザーが次のように投稿します。

```text
@BotName 👍 ✅
```

成功すると、Bot が `自動リアクション設定を追加しました` と返信します。

### 10.2 投稿にリアクションが付くか確認する

同じチャンネルに任意のメッセージを投稿します。
設定した絵文字が自動で付与されれば成功です。

### 10.3 設定確認を実行する

```text
/リアクション設定確認
```

設定済み絵文字が Embed で表示されれば成功です。

### 10.4 設定を解除する

```text
@BotName
```

成功すると、Bot が `自動リアクション設定を解除しました` と返信します。

## 11. Railway での起動例

このリポジトリには `railway.json` と `Procfile` があります。Railway では Railpack builder と `python main.py` の start command を使います。

```Procfile
worker: python main.py
```

Railway で運用する場合は、プロジェクトの Variables に次を設定します。

| 変数名 | 内容 |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot Token |
| `MONGO_URL` | MongoDB 接続 URL |
| `OPS_LOG_HUB_URL` | 任意。ops-log-hub ingest URL |
| `OPS_LOG_HUB_KEY` | 任意。ops-log-hub ingest key |

この Bot は HTTP サーバーを提供しません。公開ドメインや HTTP healthcheck は不要です。

## 14. セットアップ後の確認項目

- Bot がオンラインになっている
- Slash Command が表示される
- Message Context Menu に `リアクション補完` と `リアクション確認` が表示される
- `@BotName 絵文字...` で設定できる
- 新規投稿へ自動リアクションが付く
- MongoDB の `auto_reaction.emojis` に設定が保存される
- Bot 再起動後も設定が復元される

## 15. よくある導入ミス

| 症状 | 主な原因 |
| --- | --- |
| `RuntimeError: DISCORD_BOT_TOKEN environment variable is required` | `DISCORD_BOT_TOKEN` が未設定 |
| `RuntimeError: MONGO_URL environment variable is required` | `MONGO_URL` が未設定 |
| Bot がメンション設定に反応しない | Message Content Intent が無効、またはチャンネル管理権限がない |
| Slash Command が出ない | `applications.commands` Scope なし、同期直後で反映待ち、Bot 再招待が必要 |
| リアクションが付かない | Bot に Add Reactions / Use External Emojis / Read Message History がない |
| MongoDB に保存されない | `MONGO_URL` の誤り、ネットワーク許可、認証失敗 |
