# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

ライフコーチ兼業務改善コンサルタントBot。Googleカレンダーの予定とGoogleスプレッドシートの振り返りログを入力として、構造化されたコーチングレポートをGoogle Docsに出力し、サマリーをGoogle Sheetsに追記する。


## 技術スタック

- 言語: Python
- 外部API: Google Calendar API, Google Sheets API, Google Docs API
- 認証: OAuth 2.0（google-auth, google-api-python-client）
- AI生成: Claude API（anthropic SDK）

## セットアップ

```bash
pip install google-api-python-client google-auth google-auth-oauthlib anthropic
```

Google Cloud Console で以下のAPIを有効化し、`credentials.json` を取得する:
- Google Calendar API
- Google Sheets API
- Google Docs API

## アーキテクチャ

```
Google Calendar（当日の予定）
Google Sheets（過去の振り返りログ）
        ↓
    main.py（メインオーケストレーター）
        ↓
    coach.py（Claude APIでレポート生成）
        ↓
Google Docs（①〜⑥の詳細レポートを新規作成、日付でファイル名管理）
Google Sheets（サマリーを1行追記 → 次回以降の入力データになる）
```

## 出力フォーマット

コーチングレポートは以下の6セクション構成:
1. 今日の予定サマリー
2. 過去の傾向分析
3. リスク予測
4. 今日の戦略
5. 行動アドバイス（具体的な行動のみ、抽象論禁止）
6. コーチング（共感→問いかけ→次の一歩）

## 制約・トーン

- 曖昧な表現禁止（「頑張る」など）
- 具体的な行動を必ず提示
- 過去データに基づいたアドバイスを優先
- 信頼できるコーチ口調、やや厳しめだが前向き
