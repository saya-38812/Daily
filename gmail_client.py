"""
gmail_client.py
---------------
Gmail API を使って、最近の重要なメールを取得するモジュール。

【取得対象】
・未読メール（直近3日分）
・重要マークがついたメール
・件名に「締切」「期限」「deadline」「due」「依頼」「お願い」などが含まれるメール

取得したメールは extract_tasks.py に渡して、Claudeにタスク・期限を抽出させる。
"""


import base64
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# タスクや期限に関係しそうなキーワード（件名フィルタ用）
TASK_KEYWORDS = [
    "締切", "期限", "deadline", "due", "依頼", "お願い", "確認",
    "回答", "返信", "承認", "提出", "レビュー", "対応", "urgent", "至急",
]


def get_recent_emails(gmail_service, days: int = 3, max_results: int = 20) -> list[dict]:
    """
    直近 days 日分の重要そうなメールを取得する。

    Args:
        gmail_service: Gmail API のサービスオブジェクト
        days: 何日前までのメールを取得するか（デフォルト3日）
        max_results: 取得するメールの最大件数

    Returns:
        list[dict]: メール情報のリスト。各要素は以下のキーを持つ
            - id: メールID
            - subject: 件名
            - sender: 送信者
            - date: 受信日時
            - snippet: 本文の冒頭（Gmailが自動生成する要約）
            - body: 本文（最初の1500文字）
    """
    print(f"Gmail から直近 {days} 日のメールを取得中...")

    # 検索クエリを作成（Gmail の検索構文を使う）
    # newer_than:3d = 3日以内
    # OR でキーワードを繋ぐ（件名に含まれるもの or 重要マーク付き）
    keyword_query = " OR ".join([f"subject:{kw}" for kw in TASK_KEYWORDS])
    query = f"(is:unread OR is:important OR ({keyword_query})) newer_than:{days}d"

    # メールの一覧を取得（IDのみ）
    result = gmail_service.users().messages().list(
        userId="me",
        q=query,
        maxResults=max_results,
    ).execute()

    messages_meta = result.get("messages", [])

    if not messages_meta:
        print("該当するメールが見つかりませんでした。")
        return []

    # 各メールの詳細を取得する
    emails = []
    for meta in messages_meta:
        email_data = _get_email_detail(gmail_service, meta["id"])
        if email_data:
            emails.append(email_data)

    print(f"{len(emails)} 件のメールを取得しました。")
    return emails


def _get_email_detail(gmail_service, message_id: str) -> dict | None:
    """
    メールIDからメールの詳細情報を取得する。

    Args:
        gmail_service: Gmail API のサービスオブジェクト
        message_id: メールのID

    Returns:
        dict: メール情報、取得失敗時は None
    """
    try:
        message = gmail_service.users().messages().get(
            userId="me",
            id=message_id,
            format="full",  # ヘッダー＋本文をすべて取得
        ).execute()

        # ヘッダーから件名・送信者・日付を取り出す
        headers = message.get("payload", {}).get("headers", [])
        header_map = {h["name"]: h["value"] for h in headers}

        subject = header_map.get("Subject", "（件名なし）")
        sender = header_map.get("From", "不明")
        date_str = header_map.get("Date", "")

        # 日付を読みやすい形式に変換
        date_display = _parse_email_date(date_str)

        # 本文を取得（BASE64デコードが必要）
        body = _extract_body(message.get("payload", {}))

        # Gmailが自動生成する冒頭要約
        snippet = message.get("snippet", "")

        return {
            "id": message_id,
            "subject": subject,
            "sender": sender,
            "date": date_display,
            "snippet": snippet,
            "body": body[:1500],  # 長すぎる本文は1500文字で切る
        }

    except Exception as e:
        print(f"メール取得エラー (id={message_id}): {e}")
        return None


def _extract_body(payload: dict) -> str:
    """
    Gmail API のペイロードから本文テキストを抽出する。

    メールは「マルチパート」構造になっている場合がある。
    text/plain（プレーンテキスト）を優先して取得する。

    Args:
        payload: Gmail API の message.payload

    Returns:
        str: 本文テキスト（取得できない場合は空文字）
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    # シンプルなテキストメール
    if mime_type == "text/plain" and body_data:
        return _decode_base64(body_data)

    # HTML メール（プレーンテキストを優先するため、HTMLはタグを除去）
    if mime_type == "text/html" and body_data:
        html = _decode_base64(body_data)
        return _strip_html_tags(html)

    # マルチパートメール（複数パートを再帰的に探す）
    parts = payload.get("parts", [])
    for part in parts:
        result = _extract_body(part)
        if result:
            return result

    return ""


def _decode_base64(data: str) -> str:
    """Gmail のBASE64エンコードされたデータをデコードする"""
    try:
        # Gmail は URL-safe BASE64 を使っているので urlsafe_b64decode を使う
        decoded_bytes = base64.urlsafe_b64decode(data + "==")
        return decoded_bytes.decode("utf-8", errors="replace")
    except Exception:
        return ""


def _strip_html_tags(html: str) -> str:
    """HTMLタグを除去してプレーンテキストにする"""
    clean = re.sub(r"<[^>]+>", "", html)
    # 連続する空白・改行を整理する
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _parse_email_date(date_str: str) -> str:
    """
    メールヘッダーの Date 文字列を読みやすい形式に変換する。
    例: "Thu, 11 Apr 2026 09:00:00 +0900" → "2026/04/11 09:00"
    """
    if not date_str:
        return "不明"
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        dt_jst = dt.astimezone(JST)
        return dt_jst.strftime("%Y/%m/%d %H:%M")
    except Exception:
        return date_str[:20]


def emails_to_text(emails: list[dict]) -> str:
    """
    メールリストを Claude に渡すためのテキストに変換する。

    Args:
        emails: get_recent_emails() の戻り値

    Returns:
        str: メール情報をまとめたテキスト
    """
    if not emails:
        return "タスク・期限に関連するメールはありませんでした。"

    lines = [f"【直近のメール一覧（{len(emails)}件）】"]
    for i, email in enumerate(emails, 1):
        lines.append(f"\n--- メール {i} ---")
        lines.append(f"受信日時: {email['date']}")
        lines.append(f"送信者: {email['sender']}")
        lines.append(f"件名: {email['subject']}")
        lines.append(f"要約: {email['snippet']}")
        if email["body"] and email["body"] != email["snippet"]:
            lines.append(f"本文（冒頭）:\n{email['body'][:500]}")

    return "\n".join(lines)
