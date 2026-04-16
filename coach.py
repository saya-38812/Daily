"""
coach.py
--------
Claude API を使って、予定ごとの準備事項を生成するモジュール。
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import anthropic

JST = ZoneInfo("Asia/Tokyo")
WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]
MODEL = "claude-sonnet-4-6"


def generate_preparation_advice(
    today_events_text: str,
    tomorrow_events_text: str,
    this_week_events_text: str,
    target_date: datetime = None,
    api_key: str = None,
) -> str:
    """
    今日・明日・今週の予定に対して、予定ごとの具体的な準備事項を生成する。

    Args:
        today_events_text:     今日の予定テキスト（events_to_text の出力）
        tomorrow_events_text:  明日の予定テキスト
        this_week_events_text: 今週の残り（明後日〜日曜）の予定テキスト
        target_date: 対象日（省略すると今日）
        api_key: Anthropic API キー（省略すると環境変数から取得）

    Returns:
        str: 予定ごとの準備アドバイステキスト
    """
    if target_date is None:
        target_date = datetime.now(JST)

    wd = WEEKDAYS[target_date.weekday()]
    date_display = target_date.strftime(f"%Y年%m月%d日（{wd}）")

    if api_key is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY が設定されていません。.env を確認してください。")

    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = """あなたは優秀な秘書です。
ユーザーの予定を見て、各予定に必要な準備事項を具体的に提示してください。

ルール：
・準備が不要な予定（ランチ、移動、休憩など）はスキップする
・準備事項は「何を・いつまでに」の形で書く
・抽象的な表現禁止（「確認する」ではなく「〇〇の資料をメールで送付する」のように）
・1つの予定につき最大3つまで
・予定のタイトルや参加者から、必要な準備を推測して補う"""

    user_prompt = f"""以下の予定に対して、準備事項を教えてください。

対象日: {date_display}

【今日の予定】
{today_events_text}

【明日の予定】
{tomorrow_events_text}

【今週の残りの予定（明後日以降）】
{this_week_events_text}

---

以下の形式で出力してください：

【今日の準備】

▼ （予定名・時刻）
・（準備事項1）
・（準備事項2）

※ 準備不要な予定は省略する
※ すべて準備不要なら「準備が必要な予定はありません」と書く

【明日の準備】

▼ （予定名・時刻）
・（準備事項）

※ 同上

【今週の準備】

▼ （日付・予定名）
・（準備事項）― いつまでに着手すべきか目安も添える

※ 同上
"""

    print("Claude API で準備アドバイスを生成中...")
    message = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return message.content[0].text

