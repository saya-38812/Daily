# Daily Prep Bot

Googleカレンダーの予定を読み取り、**今日・明日・今週の準備事項**をClaude AIが生成してGmailで送ってくれるBot。

## できること

- Googleカレンダーの全カレンダーから予定を自動取得
- 各予定に対して「何を・いつまでに」形式の具体的な準備事項を生成
- 結果をGmailでメール送信（自分宛 or 指定アドレス）
- 日付を指定して過去・未来の日付でも実行可能


## 動作イメージ

```
Googleカレンダー（今日・明日・今週の予定）
        ↓
    main.py（予定を取得して整形）
        ↓
    coach.py（Claude APIで準備事項を生成）
        ↓
Gmail（準備アドバイスをメール送信）
```

## セットアップ

### 1. 必要なライブラリをインストール

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Console での設定

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成
2. 以下のAPIを有効化する
   - Google Calendar API
   - Gmail API
3. OAuth 2.0 クライアントIDを作成し、`credentials.json` としてこのフォルダに保存

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、各値を設定する。

```bash
cp .env.example .env
```

| 変数名 | 説明 | 必須 |
|---|---|---|
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com) で取得 | ✅ |
| `REPORT_EMAIL_TO` | 送信先メールアドレス（省略すると自分自身に送信） | |
| `SPREADSHEET_ID` | 振り返りログのスプレッドシートID | |
| `DOCS_FOLDER_ID` | Google DocsレポートのフォルダID | |

### 4. 初回認証

初回実行時はブラウザが開き、Googleアカウントの認証を求められる。認証後は `token.json` が生成され、次回以降は自動ログイン。

## 使い方

```bash
# 今日の準備アドバイスを生成・送信
python main.py

# 特定の日付を指定して実行
python main.py 2026-04-20
```

### タスクスケジューラで毎朝自動実行（Windows）

`run_daily.bat` をWindowsのタスクスケジューラに登録すると、毎朝決まった時間に自動実行できる。

## 出力例

```
【今日の準備】

▼ 週次MTG（10:00〜11:00）
・先週のタスク進捗をスプレッドシートにまとめる（9:30までに）
・議題案を事前にSlackで共有する（9:00までに）

【明日の準備】

▼ クライアント提案（14:00〜15:00）
・提案資料のPDFを印刷する（当日12:00までに）

【今週の準備】

準備が必要な予定はありません
```

## ファイル構成

```
Daily/
├── main.py              # メイン実行ファイル
├── coach.py             # Claude APIで準備アドバイスを生成
├── calendar_client.py   # Google Calendar APIのラッパー
├── gmail_sender.py      # Gmail APIでメール送信
├── google_auth.py       # Google OAuth認証
├── run_daily.bat        # タスクスケジューラ用バッチファイル
├── requirements.txt     # 依存ライブラリ
├── .env.example         # 環境変数のテンプレート
└── .env                 # 実際の環境変数（Gitに含めない）
```

## 注意事項

- `.env`・`credentials.json`・`token.json` は機密情報のため `.gitignore` で管理されており、GitHubには含まれない
- 初回実行時に `logs/` フォルダが自動生成される
