"""
gmail_sender.py
---------------
Gmail API を使って予定サマリーをメールで送信するモジュール。
"""

import base64
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def send_coaching_report(
    gmail_service,
    report_text: str,
    target_date: datetime = None,
    to_address: str = None,
) -> str:
    """
    予定サマリーをメールで送信する。

    Args:
        gmail_service: Gmail API のサービスオブジェクト
        report_text: 送信するサマリーテキスト
        target_date: 対象日（省略すると今日）
        to_address: 送信先メールアドレス（省略すると自分自身に送信）

    Returns:
        str: 送信したメールのID
    """
    if target_date is None:
        target_date = datetime.now(JST)

    if to_address is None:
        to_address = _get_my_email(gmail_service)

    wd = WEEKDAYS[target_date.weekday()]
    date_str = target_date.strftime(f"%Y年%m月%d日（{wd}）")
    subject = f"【今日の準備】{date_str}"

    plain_body, html_body = _build_email_body(report_text, date_str)

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["To"] = to_address
    message["From"] = to_address
    message.attach(MIMEText(plain_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body,  "html",  "utf-8"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    print(f"{to_address} にメール送信中...")
    sent = gmail_service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"送信完了（件名: {subject}）")
    return sent["id"]


def _get_my_email(gmail_service) -> str:
    """ログイン中のGmailアカウントのメールアドレスを取得する。"""
    profile = gmail_service.users().getProfile(userId="me").execute()
    return profile["emailAddress"]


def _build_email_body(report_text: str, date_display: str) -> tuple[str, str]:
    """プレーンテキスト版とHTML版のメール本文を作成する。"""

    # ---- プレーンテキスト ----
    plain = f"今日の準備 - {date_display}\n{'=' * 40}\n\n{report_text}"

    # ---- HTML ----
    html_report = _report_to_html(report_text)
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head><meta charset="UTF-8"></head>
<body style="font-family:'Helvetica Neue',Arial,sans-serif;max-width:680px;margin:0 auto;padding:24px;color:#333;">
  <h1 style="font-size:20px;color:#1a1a2e;border-bottom:3px solid #4a6cf7;padding-bottom:8px;">
    今日の準備 - {date_display}
  </h1>
  {html_report}
  <p style="margin-top:32px;font-size:12px;color:#888;">このメールは自動生成されました。</p>
</body>
</html>"""

    return plain, html


def _report_to_html(report_text: str) -> str:
    """
    レポートテキストの【...】見出しをHTMLの<h2>に、
    箇条書き（・）を<li>に変換する。
    """
    # セクション番号ごとのアクセントカラー
    SECTION_COLORS = {"①": "#4a6cf7", "②": "#f7824a", "③": "#4af74a"}

    html_lines = []
    in_list = False

    for line in report_text.split("\n"):
        stripped = line.strip()

        if not stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            html_lines.append("<br>")
            continue

        if stripped.startswith("【") and "】" in stripped:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            color = next((c for k, c in SECTION_COLORS.items() if k in stripped), "#1a1a2e")
            title = stripped.replace("【", "").replace("】", "")
            html_lines.append(
                f'<h2 style="font-size:16px;color:{color};margin-top:24px;'
                f'margin-bottom:8px;border-left:4px solid {color};padding-left:10px;">'
                f"{title}</h2>"
            )
            continue

        if stripped.startswith("・") or stripped.startswith("•"):
            if not in_list:
                html_lines.append('<ul style="margin:4px 0;padding-left:20px;">')
                in_list = True
            content = stripped.lstrip("・•").strip()
            html_lines.append(f'<li style="margin:4px 0;">{content}</li>')
            continue

        if in_list:
            html_lines.append("</ul>")
            in_list = False
        html_lines.append(f'<p style="margin:4px 0;">{stripped}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)
