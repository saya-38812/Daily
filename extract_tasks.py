"""
extract_tasks.py
----------------
Claude API を使って、メールからタスクと期限を自動抽出し、Google Tasks に登録するモジュール。

【流れ】
1. メールテキストを Claude に渡す
2. Claude が「タスク名・期限・優先度・メモ」を JSON で返す
3. JSON を解析して Google Tasks にタスクを作成する
"""


import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

from tasks_client import create_task, get_default_tasklist_id

JST = ZoneInfo("Asia/Tokyo")
MODEL = "claude-sonnet-4-6"


def extract_and_register_tasks(
    gmail_service,
    tasks_service,
    emails_text: str,
    api_key: str = None,
    dry_run: bool = False,
) -> list[dict]:
    """
    メールテキストからタスクを抽出して Google Tasks に登録する。

    Args:
        gmail_service: Gmail API サービス（現在は未使用、将来の拡張用）
        tasks_service: Google Tasks API サービス
        emails_text: gmail_client.emails_to_text() で整形したテキスト
        api_key: Anthropic API キー（省略すると環境変数から取得）
        dry_run: True にすると実際には登録せず、抽出結果だけ返す（テスト用）

    Returns:
        list[dict]: 抽出されたタスクのリスト
        例: [{"title": "...", "due": "2026-04-15", "priority": "高", "notes": "..."}, ...]
    """
    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")

    client = anthropic.Anthropic(api_key=api_key)

    today_str = datetime.now(JST).strftime("%Y-%m-%d")

    # Claudeへのプロンプト（JSON形式で返すよう指示する）
    prompt = f"""以下のメール一覧を読んで、対応が必要なタスクと期限を抽出してください。

今日の日付: {today_str}

{emails_text}

---

【抽出ルール】
・自分（受信者）が対応すべきアクションだけを抽出する
・「確認してください」「送ってください」「回答ください」のような依頼を拾う
・期限が明記されていれば必ず記録する
・同じ内容の重複は1つにまとめる
・明らかに関係ないメール（広告・通知系）は無視する

【出力形式】
必ず以下のJSON形式で返してください。タスクが1つもない場合は空配列 [] を返してください。

```json
[
  {{
    "title": "タスクのタイトル（動詞で始める。例: 〇〇に返信する、〇〇を提出する）",
    "due": "期限（YYYY-MM-DD形式。不明な場合は null）",
    "priority": "高 or 中 or 低",
    "notes": "送信者・メールの件名・補足情報"
  }}
]
```
"""

    print("Claude API でメールからタスクを抽出中...")

    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = message.content[0].text

    # JSONを抽出・パースする
    extracted_tasks = _parse_json_response(response_text)

    if not extracted_tasks:
        print("メールから抽出できるタスクはありませんでした。")
        return []

    print(f"{len(extracted_tasks)} 件のタスクを抽出しました。")

    # dry_run モードでなければ Google Tasks に登録する
    if not dry_run:
        _register_tasks_to_google(tasks_service, extracted_tasks)
    else:
        print("[dry_run] タスクの登録はスキップしました。")
        for task in extracted_tasks:
            print(f"  ・{task['title']}（期限: {task.get('due') or '未設定'}）")

    return extracted_tasks


def _parse_json_response(response_text: str) -> list[dict]:
    """
    Claude のレスポンスから JSON 部分を抽出してパースする。

    Claude は JSON の前後に説明文を書くことがあるので、
    ```json ... ``` ブロックを正規表現で探して取り出す。

    Args:
        response_text: Claude のレスポンステキスト

    Returns:
        list[dict]: パースされたタスクリスト
    """
    # ```json ... ``` ブロックを探す
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", response_text)

    if json_match:
        json_str = json_match.group(1)
    else:
        # ブロックがない場合は全体を試す
        json_str = response_text.strip()

    try:
        parsed = json.loads(json_str)
        # リスト形式かチェック
        if isinstance(parsed, list):
            return parsed
        else:
            print(f"予期しないJSON形式: {type(parsed)}")
            return []
    except json.JSONDecodeError as e:
        print(f"JSONのパースに失敗しました: {e}")
        print(f"レスポンス内容:\n{response_text[:300]}")
        return []


def _register_tasks_to_google(tasks_service, tasks: list[dict]) -> None:
    """
    抽出されたタスクを Google Tasks に一括登録する。

    デフォルトのタスクリスト（「マイタスク」）に追加する。

    Args:
        tasks_service: Google Tasks API サービス
        tasks: extract_and_register_tasks() が返すタスクリスト
    """
    # デフォルトのタスクリストIDを取得
    tasklist_id = get_default_tasklist_id(tasks_service)

    print(f"{len(tasks)} 件のタスクを Google Tasks に登録中...")

    for task in tasks:
        title = task.get("title", "（タイトル不明）")
        due = task.get("due")          # "2026-04-15" or None
        notes = task.get("notes", "")
        priority = task.get("priority", "中")

        # メモに優先度も追記する
        full_notes = f"優先度: {priority}"
        if notes:
            full_notes += f"\n{notes}"
        full_notes += "\n※ メールから自動抽出"

        create_task(
            tasks_service=tasks_service,
            tasklist_id=tasklist_id,
            title=title,
            due_date=due,
            notes=full_notes,
        )


def extracted_tasks_to_text(extracted_tasks: list[dict]) -> str:
    """
    抽出されたタスクをレポート用テキストに変換する。

    Args:
        extracted_tasks: _parse_json_response() の戻り値

    Returns:
        str: タスク一覧のテキスト
    """
    if not extracted_tasks:
        return "メールから新たに抽出されたタスクはありません。"

    lines = [f"【メールから新規抽出されたタスク（{len(extracted_tasks)}件）】"]

    # 優先度でソート（高→中→低）
    priority_order = {"高": 0, "中": 1, "低": 2}
    sorted_tasks = sorted(extracted_tasks, key=lambda t: priority_order.get(t.get("priority", "中"), 1))

    for task in sorted_tasks:
        due = task.get("due") or "未設定"
        priority = task.get("priority", "中")
        lines.append(f"  [{priority}] {task['title']}（期限: {due}）")

    return "\n".join(lines)
