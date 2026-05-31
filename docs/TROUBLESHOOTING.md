# トラブルシューティング

`discordbot-auto-reaction` の導入・運用時に発生しやすい問題と確認手順をまとめます。

## 1. Bot が起動しない

### 1.1 `RuntimeError: DISCORD_BOT_TOKEN environment variable is required`

原因: `DISCORD_BOT_TOKEN` が設定されていません。

ローカルでは `.env`、Railway では Variables に `DISCORD_BOT_TOKEN` を設定してください。

### 1.2 `RuntimeError: MONGO_URL environment variable is required`

原因: `MONGO_URL` が設定されていません。

ローカルでは `.env`、Railway では Variables に `MONGO_URL` を設定してください。

### 1.3 旧設定 `TOKEN` のみを使っている

原因: 新規設定では `DISCORD_BOT_TOKEN` を使います。`TOKEN` は旧設定との互換 fallback です。

対処:

- ローカルでは `.env` に `DISCORD_BOT_TOKEN=...` を設定する
- Railway などでは Variables に `DISCORD_BOT_TOKEN` を設定する
- `.env` のファイル名が正しいか確認する
- `load_dotenv()` が呼ばれているか確認する

### 1.4 `MONGO_URL` の接続失敗

原因: 環境変数 `MONGO_URL` が設定されていません。

対処:

- ローカルでは `.env` に `MONGO_URL=...` を設定する
- ホスティング環境では Variables に `MONGO_URL` を設定する
- MongoDB 接続 URL に改行や余分な空白が入っていないか確認する

### 1.5 `ModuleNotFoundError` が依存ライブラリで発生する

原因: `requirements.txt` の依存関係が未インストールです。

対処:

```bash
pip install -r requirements.txt
```

仮想環境を使っている場合は、仮想環境を有効化してから実行してください。

## 2. Bot がオンラインにならない

確認項目:

1. Discord Bot Token が正しいか
2. Token を再生成した後、古い Token を使っていないか
3. Bot が削除・無効化されていないか
4. ホスティング環境のプロセスが落ちていないか
5. `python main.py` が実行されているか
6. Python バージョンが 3.14.5 か

## 3. Bot メンションで設定できない

### 3.1 Message Content Intent が無効

Bot メンションによる設定は `message.content` を読みます。
Discord Developer Portal で Message Content Intent を有効にしてください。

### 3.2 投稿者にチャンネル管理権限がない

設定・解除には `manage_channels` 権限が必要です。

サーバー管理者であっても、チャンネル権限の上書きにより権限が不足する場合があります。

### 3.3 Bot メンションの形式が違う

設定は、メッセージ本文を空白で分割した先頭要素が Bot メンションと一致する場合にだけ処理されます。

有効な例:

```text
@BotName 👍 ✅
```

無効になりやすい例:

```text
こんにちは @BotName 👍
```

Bot メンションは先頭に置いてください。

### 3.4 絵文字が抽出できていない

設定時に 1 つ以上の絵文字を抽出できない場合、設定は保存されません。

カスタム絵文字は次の形式が対象です。

```text
<:name:id>
<a:name:id>
```

## 4. Slash Command が表示されない

確認項目:

1. Bot 招待時に `applications.commands` Scope を付けたか
2. Bot を招待し直したか
3. 起動時に `bot.tree.sync()` が成功しているか
4. Discord クライアント側の反映待ちではないか
5. コマンド実行者に必要権限があるか
6. 対象が Guild 内チャンネルか

現行実装の Slash Command は Guild 限定です。DM では使用できません。

## 5. 右クリックメニューが表示されない

確認項目:

1. Bot 招待時に `applications.commands` Scope を付けたか
2. Bot が再起動され、コマンド同期が完了しているか
3. メッセージを右クリックしているか
4. サーバー内のメッセージか
5. 実行ユーザーに必要権限があるか

`リアクション補完` は管理者向けです。
`リアクション確認` は対象メッセージの投稿者本人のみ実行できます。

## 6. 自動リアクションが付かない

確認項目:

1. `/リアクション設定確認` で設定が表示されるか
2. Bot に Add Reactions 権限があるか
3. Bot に Read Message History 権限があるか
4. Bot に View Channel 権限があるか
5. カスタム絵文字の場合、Bot がその絵文字を使用できるか
6. 外部絵文字の場合、Use External Emojis 権限があるか
7. 対象メッセージが Bot 自身の投稿ではないか
8. Discord API のレート制限や一時障害ではないか

現行実装では `message.add_reaction()` の `HTTPException` は無視されるため、失敗理由は Discord 上には表示されません。

## 7. `/リアクション補完` が終わらない、または遅い

原因: チャンネル全履歴を対象にしているためです。

処理量は概ね次に比例します。

```text
対象メッセージ数 × 設定絵文字数
```

対処:

- メッセージ数が少ないチャンネルで先に試す
- 設定絵文字数を減らす
- 大規模チャンネルでは実行タイミングを選ぶ
- 可能であれば単一メッセージ補完を使う

## 8. カスタム絵文字だけ付かない

確認項目:

1. Bot が絵文字の所属サーバーに参加しているか
2. 対象チャンネルで Use External Emojis が許可されているか
3. 絵文字が削除されていないか
4. 絵文字 ID が正しいか
5. アニメーション絵文字 `<a:name:id>` の形式が正しいか

## 9. 設定が再起動後に消える

確認項目:

1. MongoDB 接続 URL が正しいか
2. MongoDB の `auto_reaction.emojis` にドキュメントが存在するか
3. `upsert_emojis()` 実行時にエラーが出ていないか
4. 起動時の `cache_emojis()` でエラーが出ていないか
5. 別の MongoDB 環境を見ていないか

## 10. MongoDB に接続できない

確認項目:

1. `MONGO_URL` が正しいか
2. ユーザー名・パスワードが正しいか
3. MongoDB Atlas の Network Access で接続元が許可されているか
4. Database User に読み書き権限があるか
5. 接続 URL に特殊文字が含まれる場合、URL エンコードされているか

## 11. `リアクション確認` の DM が届かない

確認項目:

1. 実行者が対象メッセージの投稿者本人か
2. ユーザーがサーバーメンバーからの DM を許可しているか
3. Bot から DM を受け取れる状態か
4. Bot がブロックされていないか
5. リアクションが 1 件以上存在するか

現行実装では、DM 送信失敗時の専用エラーメッセージは定義されていません。

## 12. `リアクション確認` で他人のメッセージを確認できない

仕様です。

この機能は、自分のメッセージに付いたリアクション内訳のみ確認できます。他人のメッセージを対象にすると、次のメッセージが表示されます。

```text
自分のメッセージのみ確認することができます
```

## 13. 設定を変更したのに反映されない

Bot メンションによる設定変更を行った場合は、MongoDB とメモリキャッシュの両方が更新されます。

MongoDB を直接編集した場合は、稼働中 Bot のメモリキャッシュには即時反映されません。Bot を再起動してください。

## 14. ログ確認の観点

障害時は、ホスティング環境のログで次を確認してください。

- 起動直後の import error
- Discord Token の認証エラー
- MongoDB 接続エラー
- Extension 読み込みエラー
- `bot.tree.sync()` の失敗
- コマンド実行時の例外
- DM 送信時の例外

## 15. 最小切り分け手順

問題の原因が不明な場合は、次の順に確認してください。

1. Bot がオンラインか
2. `python main.py` の起動ログにエラーがないか
3. `.env` / Variables に `TOKEN` と `MONGO_URL` があるか
4. `DISCORD_BOT_TOKEN` と `MONGO_URL` が設定されているか
5. Message Content Intent が有効か
6. Bot 招待 URL に `applications.commands` が含まれているか
7. 対象チャンネルで Bot に Add Reactions があるか
8. `@BotName 👍` で設定できるか
9. `/リアクション設定確認` で設定を読めるか
10. 単一メッセージの `リアクション補完` が成功するか
