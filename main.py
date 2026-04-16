"""
main.py
-------
今日・明日の予定に対する準備アドバイスをメールで送るメイン実行ファイル。

【実行の流れ】
1. .env から環境変数を読み込む
2. Google API に認証接続
3. Google Calendar から今日・明日の予定を全カレンダーから取得
4. Claude API で予定ごとの準備アドバイスを生成
5. Gmail でメールを送信

【実行方法】
    python main.py                # 今日基準で実行
    python main.py 2026-04-10    # 指定日を「今日」として実行
"""

import os
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

from google_auth import build_services
from calendar_client import get_all_calendar_ids, get_events_for_date, get_events_for_range, events_to_text, end_of_week
from coach import generate_preparation_advice
from gmail_sender import send_coaching_report

JST = ZoneInfo("Asia/Tokyo")


def main():
    load_dotenv()
    report_email_to = os.environ.get("REPORT_EMAIL_TO")

    target_date = _parse_date_arg()
    print(f"\n===== {target_date.strftime('%Y年%m月%d日')} の準備アドバイスを生成します =====\n")

    # Step 1: Google API に接続
    print("【Step 1/3】 Google API に接続中...")
    services = build_services()

    # Step 2: 全カレンダーから今日・明日・今週の予定を取得
    print("\n【Step 2/3】 Google Calendar から予定を取得中...")
    calendar_ids = get_all_calendar_ids(services["calendar"])

    today_text = events_to_text(
        get_events_for_date(services["calendar"], target_date, calendar_ids)
    )
    tomorrow_text = events_to_text(
        get_events_for_date(services["calendar"], target_date + timedelta(days=1), calendar_ids)
    )
    # 今週の残り = 明後日〜今週日曜（明後日以降に予定がない場合は空になる）
    week_end = end_of_week(target_date)
    week_start = target_date + timedelta(days=2)
    this_week_text = events_to_text(
        get_events_for_range(services["calendar"], week_start, week_end, calendar_ids),
        show_date=True,  # 日付が変わるので日付も表示
    ) if week_start <= week_end else "予定なし"

    print(f"\n--- 今日 ---\n{today_text}")
    print(f"\n--- 明日 ---\n{tomorrow_text}")
    print(f"\n--- 今週の残り ---\n{this_week_text}\n")

    # Step 3: Claude API で準備アドバイスを生成してメール送信
    print("【Step 3/3】 Claude API で準備アドバイスを生成中...")
    advice = generate_preparation_advice(
        today_events_text=today_text,
        tomorrow_events_text=tomorrow_text,
        this_week_events_text=this_week_text,
        target_date=target_date,
    )

    print("\n===== 生成されたアドバイス =====")
    print(advice)
    print("=" * 40)

    send_coaching_report(
        gmail_service=services["gmail"],
        report_text=advice,
        target_date=target_date,
        to_address=report_email_to,
    )

    to_display = report_email_to or "自分自身"
    print(f"\n完了！準備アドバイスを {to_display} に送信しました。")


def _parse_date_arg() -> datetime:
    """コマンドライン引数から対象日を取得する。引数がなければ今日を返す。"""
    date_args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not date_args:
        return datetime.now(JST)

    try:
        return datetime.strptime(date_args[0], "%Y-%m-%d").replace(tzinfo=JST)
    except ValueError:
        print(f"日付の形式が正しくありません: {date_args[0]}  例: python main.py 2026-04-10")
        sys.exit(1)


if __name__ == "__main__":
    main()
