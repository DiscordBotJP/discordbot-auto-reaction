# Cloudflare D1保存への切り替え

BotはRailwayで起動し、保存処理を認証付きWorker API経由でD1へ送ります。Discord Gatewayの動作は変わりません。

## 設定

| 環境変数 | 意味 |
|---|---|
| `DATABASE_PROVIDER` | `mongodb`（既定）または`d1`。未指定の既存サービスはMongoDBを維持します |
| `MONGO_URL` | MongoDBモードの接続先 |
| `DATA_SERVICE_URL` | D1モードのデータサービスHTTPS URL |
| `DATA_SERVICE_TOKEN` | D1モードのBot専用Bearer token。秘密値として管理します |

`d1`ではURL・tokenが不足すると起動時に失敗します。MongoDBへ自動で戻ることはありません。D1のスキーマとインデックスは共通データサービスのデプロイで管理します。Botから任意SQLを実行しません。

`cloudflare_storage.py`は共通データサービス（`Eutopia18/eutopia-data-service`）のPythonアダプターを同梱しています。更新するときは元のクライアントとテストを確認してコピーします。MongoDBの全API互換ではなく、このBotが使う操作だけが対象です。

## 移行

1. 元DBを退避し、D1へデータを取り込みます。Discord IDの整数・文字列の型、ObjectId、日時を保持し、件数と内容を照合します。
2. 同じBot専用tokenに必要なdatabase/collectionの権限だけを設定します。
3. Botの書き込みを止めて最終差分を反映し、`DATABASE_PROVIDER=d1`とURL・tokenを設定して起動します。
4. 初期キャッシュ、読み取り、更新、再起動を確認します。トークンや文書本文をログへ出しません。
5. 元DBを消す前に、全利用元が移行済みであることと復元方法を確認します。

切り戻しでは元のMongoDBへD1上の切り替え後の書き込みを戻す必要があります。単にproviderを戻すと新しいデータを失うため、障害時は書き込みを止めてから整合性を確認します。

## 検証

```sh
python -m unittest discover -s tests
```

本番のDiscord投稿を発生させないローカル検証です。

## このBotの範囲

`auto_reaction.emojis`と`auto_reaction.reaction_checks`を使用します。D1モードでは起動時のMongoDB `create_index`を呼びません。インデックスはデータサービスのスキーマで作成します。MongoDBモードでは既存のインデックス作成を維持します。同じリポジトリを使う別サービスはproviderを設定するまでMongoDBのままです。
