"""
calendar_client.py
------------------
Google Calendar API を使って予定を取得するモジュール。
すべてのカレンダー（マイカレンダー・共有カレンダー等）から予定を取得する。
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


def end_of_week(date: datetime) -> datetime:
    """
    指定日が属する週の日曜日（週末）を返す。
    例: 水曜日 → その週の日曜日
    """
    # weekday(): 月=0 〜 日=6  →  日曜まであと何日か = 6 - weekday()
    days_until_sunday = 6 - date.weekday()
    return date + timedelta(days=days_until_sunday)


def get_all_calendar_ids(calendar_service) -> list[str]:
    """
    アカウントに登録されているすべてのカレンダーのIDを取得する。

    Google カレンダーは「マイカレンダー」「他のカレンダー」など
    複数のカレンダーを持てる。"primary" だけだとメインカレンダーしか
    取れないので、この関数で全IDを取ってから予定を取得する。

    Returns:
        list[str]: カレンダーIDのリスト
    """
    result = calendar_service.calendarList().list().execute()
    calendars = result.get("items", [])

    ids = [cal["id"] for cal in calendars]
    names = [cal.get("summary", cal["id"]) for cal in calendars]
    print(f"カレンダー一覧: {', '.join(names)}")
    return ids


def get_events_for_date(
    calendar_service,
    target_date: datetime,
    calendar_ids: list[str],
) -> list[dict]:
    """指定した1日分の予定をすべてのカレンダーから取得する。"""
    day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = target_date.replace(hour=23, minute=59, second=59, microsecond=0)
    return _fetch_events(calendar_service, day_start.isoformat(), day_end.isoformat(), calendar_ids)


def get_events_for_range(
    calendar_service,
    start_date: datetime,
    end_date: datetime,
    calendar_ids: list[str],
) -> list[dict]:
    """指定した期間の予定をすべてのカレンダーから取得する。"""
    time_min = start_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    time_max = end_date.replace(hour=23, minute=59, second=59, microsecond=0).isoformat()
    return _fetch_events(calendar_service, time_min, time_max, calendar_ids)


def _fetch_events(
    calendar_service,
    time_min: str,
    time_max: str,
    calendar_ids: list[str],
) -> list[dict]:
    """
    複数のカレンダーから予定を取得してまとめて返す（内部処理）。

    各カレンダーIDに対してAPIを叩き、結果を開始時刻順にソートして返す。
    同じ予定が複数カレンダーに存在しても重複はしない（iCalUID で判定）。
    """
    seen_uids = set()   # 重複排除用（ iCalUID = 予定の一意ID ）
    all_events = []

    for cal_id in calendar_ids:
        result = calendar_service.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,   # 繰り返しイベントを個別に展開
            orderBy="startTime",
        ).execute()

        for event in result.get("items", []):
            # iCalUID が同じ予定は別カレンダーでも同一予定なのでスキップ
            uid = event.get("iCalUID", event.get("id", ""))
            if uid in seen_uids:
                continue
            seen_uids.add(uid)

            start_raw = event.get("start", {})
            end_raw = event.get("end", {})

            # 参加者リスト（自分以外の名前/メアドを取得）
            attendees = [
                a.get("displayName") or a.get("email", "")
                for a in event.get("attendees", [])
                if not a.get("self")  # self=True は自分自身なのでスキップ
            ]

            all_events.append({
                "title":       event.get("summary", "（タイトルなし）"),
                "start_raw":   start_raw.get("dateTime") or start_raw.get("date", ""),
                "end_raw":     end_raw.get("dateTime") or end_raw.get("date", ""),
                "description": event.get("description", ""),
                "location":    event.get("location", ""),
                "attendees":   attendees,
            })

    # 複数カレンダーの結果をまとめたので、開始時刻順に並べ直す
    # 文字列ではなく datetime で比較する（UTC と JST が混在してもズレない）
    def sort_key(e: dict):
        s = e["start_raw"]
        if "T" in s:
            return _parse_dt(s)
        # 終日予定は JST の 00:00 として扱う
        return datetime.fromisoformat(s).replace(tzinfo=JST)

    all_events.sort(key=sort_key)
    return all_events


def events_to_text(events: list[dict], show_date: bool = False) -> str:
    """
    予定リストをテキストに変換する。

    Args:
        events: get_events_for_date() または get_events_for_range() の戻り値
        show_date: True にすると「4/12（日）09:00」のように日付も表示する
                   今後の予定など日付が変わる場合に使う

    Returns:
        str: 予定を箇条書きにしたテキスト（予定がなければ「予定なし」）
    """
    if not events:
        return "予定なし"

    lines = []
    for event in events:
        start = _format_dt(event["start_raw"], show_date=show_date)
        end = _format_dt(event["end_raw"], show_date=False)  # 終了時刻は時刻のみ
        line = f"・{start}〜{end} ：{event['title']}"

        if event["location"]:
            line += f"（場所: {event['location']}）"

        if event.get("attendees"):
            line += f"\n  └ 参加者: {', '.join(event['attendees'])}"

        if event["description"]:
            desc = event["description"].replace("\n", " ")[:100]
            line += f"\n  └ 詳細: {desc}"

        lines.append(line)

    return "\n".join(lines)


def _parse_dt(dt_str: str) -> datetime:
    """
    ISO 8601 文字列を datetime に変換し、JST に統一する。

    Google Calendar API は "Z"（UTC）と "+09:00"（JST）の
    両方を返すことがあるため、必ず JST に変換してから返す。
    """
    # Python 3.10 以下は "Z" を解釈できないので "+00:00" に置換する
    normalized = dt_str.replace("Z", "+00:00")
    dt = datetime.fromisoformat(normalized)

    # タイムゾーン情報がない場合（まれにある）は JST と仮定する
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=JST)

    # JST に変換して返す（UTCで来ていても +9時間される）
    return dt.astimezone(JST)


def _format_dt(dt_str: str, show_date: bool = False) -> str:
    """
    ISO 8601 形式の日時文字列を読みやすい形式に変換する。

    show_date=False → 「09:00」または「終日」
    show_date=True  → 「4/12（日）09:00」または「4/12（日）終日」
    """
    if not dt_str:
        return "不明"

    try:
        if "T" in dt_str:
            dt = _parse_dt(dt_str)  # JST に統一してから表示
            time_part = dt.strftime("%H:%M")
            if show_date:
                wd = WEEKDAYS[dt.weekday()]
                return f"{dt.month}/{dt.day}（{wd}）{time_part}"
            return time_part
        else:
            dt = datetime.fromisoformat(dt_str)
            if show_date:
                wd = WEEKDAYS[dt.weekday()]
                return f"{dt.month}/{dt.day}（{wd}）終日"
            return "終日"
    except ValueError:
        return dt_str

