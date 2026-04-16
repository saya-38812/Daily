"""
tasks_client.py
---------------
Google Tasks API を使って、タスクの読み込み・作成・完了処理を行うモジュール。

【Google Tasks の構造】
- タスクリスト（TaskList）: フォルダのようなもの（複数作れる）
  └ タスク（Task）: 実際のToDoアイテム
        - タイトル
        - 期限（due）
        - メモ
        - ステータス（needsAction / completed）
"""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")



def get_all_tasks(tasks_service, include_completed: bool = False) -> dict[str, list[dict]]:
    """
    すべてのタスクリストからタスクを取得する。

    Args:
        tasks_service: Google Tasks API のサービスオブジェクト
        include_completed: 完了済みタスクも含めるか（デフォルト: 含めない）

    Returns:
        dict: タスクリスト名をキー、タスクのリストを値とする辞書
        例: {
            "マイタスク": [{"title": "...", "due": "...", ...}, ...],
            "仕事": [...],
        }
    """
    print("Google Tasks からタスクを取得中...")

    # まずタスクリストの一覧を取得する
    tasklists_result = tasks_service.tasklists().list().execute()
    tasklists = tasklists_result.get("items", [])

    if not tasklists:
        print("タスクリストが見つかりませんでした。")
        return {}

    all_tasks = {}

    for tasklist in tasklists:
        list_id = tasklist["id"]
        list_title = tasklist["title"]

        # 各タスクリストのタスクを取得
        tasks_result = tasks_service.tasks().list(
            tasklist=list_id,
            showCompleted=include_completed,
            showHidden=False,          # アーカイブされたタスクは除外
            maxResults=100,
        ).execute()

        raw_tasks = tasks_result.get("items", [])

        # タスクデータを整形する
        formatted_tasks = []
        for task in raw_tasks:
            # 期限の変換（RFC3339形式 → 読みやすい日本語）
            due_str = task.get("due", "")
            due_display = _format_due_date(due_str)

            # 期限が過ぎているかチェック
            is_overdue = _is_overdue(due_str)

            formatted_tasks.append({
                "id": task["id"],
                "tasklist_id": list_id,
                "title": task.get("title", "（タイトルなし）"),
                "due": due_display,
                "due_raw": due_str,         # 期限の計算に使う生データ
                "notes": task.get("notes", ""),
                "status": task.get("status", "needsAction"),
                "is_overdue": is_overdue,
            })

        if formatted_tasks:
            all_tasks[list_title] = formatted_tasks

    total = sum(len(tasks) for tasks in all_tasks.values())
    print(f"タスクを {total} 件取得しました（{len(all_tasks)} リスト）。")
    return all_tasks


def create_task(tasks_service, tasklist_id: str, title: str, due_date: str = None, notes: str = "") -> dict:
    """
    新しいタスクを作成する。

    Args:
        tasks_service: Google Tasks API のサービスオブジェクト
        tasklist_id: 追加先のタスクリストID
        title: タスクのタイトル
        due_date: 期限（"2026-04-15" のような形式、省略可）
        notes: メモ・詳細

    Returns:
        dict: 作成されたタスクの情報
    """
    task_body = {
        "title": title,
        "notes": notes,
        "status": "needsAction",
    }

    # 期限が指定されている場合は RFC3339 形式に変換して設定する
    if due_date:
        task_body["due"] = _date_to_rfc3339(due_date)

    created_task = tasks_service.tasks().insert(
        tasklist=tasklist_id,
        body=task_body,
    ).execute()

    print(f"タスクを作成しました: 「{title}」（期限: {due_date or '未設定'}）")
    return created_task


def get_default_tasklist_id(tasks_service) -> str:
    """
    デフォルトのタスクリスト（「マイタスク」）のIDを返す。
    タスクの追加先として使う。

    Args:
        tasks_service: Google Tasks API のサービスオブジェクト

    Returns:
        str: タスクリストID
    """
    result = tasks_service.tasklists().list().execute()
    tasklists = result.get("items", [])

    if not tasklists:
        raise RuntimeError("タスクリストが見つかりません。")

    # 最初のリスト（通常「マイタスク」）を返す
    return tasklists[0]["id"]


def tasks_to_text(all_tasks: dict[str, list[dict]]) -> str:
    """
    タスク辞書を Claude に渡すためのテキストに変換する。

    期限切れのタスクは「⚠️ 期限超過」と明示する。

    Args:
        all_tasks: get_all_tasks() の戻り値

    Returns:
        str: タスク一覧のテキスト
    """
    if not all_tasks:
        return "現在のタスクはありません。"

    lines = ["【現在のタスク一覧】"]

    for list_name, tasks in all_tasks.items():
        lines.append(f"\n■ {list_name}")

        # 期限切れ → 期限あり → 期限なし の順で並べる
        sorted_tasks = sorted(tasks, key=lambda t: (
            0 if t["is_overdue"] else (1 if t["due_raw"] else 2),
            t["due_raw"] or "9999",
        ))

        for task in sorted_tasks:
            # 期限切れの場合は警告マークを付ける
            overdue_mark = "【期限超過】" if task["is_overdue"] else ""
            due_text = f"期限: {task['due']}" if task["due"] else "期限: 未設定"

            line = f"  ・{overdue_mark}{task['title']}（{due_text}）"
            lines.append(line)

            # メモがあれば追記
            if task["notes"]:
                lines.append(f"    └ メモ: {task['notes'][:80]}")

    return "\n".join(lines)


def _format_due_date(due_str: str) -> str:
    """
    Google Tasks の期限文字列（RFC3339）を読みやすい形式に変換する。
    例: "2026-04-15T00:00:00.000Z" → "4月15日（水）"
    """
    if not due_str:
        return ""
    try:
        dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        dt_jst = dt.astimezone(JST)
        # 曜日を日本語で表示
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        weekday = weekdays[dt_jst.weekday()]
        return dt_jst.strftime(f"%m月%d日（{weekday}）")
    except Exception:
        return due_str


def _is_overdue(due_str: str) -> bool:
    """
    タスクの期限が過ぎているかチェックする。

    Args:
        due_str: 期限の文字列（RFC3339形式）

    Returns:
        bool: 期限切れなら True
    """
    if not due_str:
        return False
    try:
        dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return dt < now
    except Exception:
        return False


def _date_to_rfc3339(date_str: str) -> str:
    """
    "2026-04-15" のような日付文字列を Google Tasks が受け付ける RFC3339 形式に変換する。
    例: "2026-04-15" → "2026-04-15T00:00:00.000Z"
    """
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%dT00:00:00.000Z")
    except ValueError:
        return date_str
