"""
sheets_client.py
----------------
Google Sheets API を使って、振り返りログの読み込みとサマリーの追記を行うモジュール。

【スプレッドシートの想定フォーマット】
1行目: ヘッダー行（例: 日付 | よかったこと | 改善点 | 感情スコア | メモ）
2行目以降: データ行（1行 = 1日分の振り返り）
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")



def get_reflection_logs(sheets_service, spreadsheet_id: str, sheet_name: str = "振り返りログ", max_rows: int = 30) -> list[dict]:
    """
    スプレッドシートから振り返りログを読み込む。

    Args:
        sheets_service: Google Sheets API のサービスオブジェクト
        spreadsheet_id: スプレッドシートのID（URLから取得）
        sheet_name: シート名
        max_rows: 取得する最大行数（最新のデータから遡って取得）

    Returns:
        list[dict]: 各行を辞書にしたリスト（ヘッダーをキーとして使う）
    """
    print(f"スプレッドシートから振り返りログを取得中...")

    # 読み込む範囲を指定（A列からZ列、最大行数分）
    range_notation = f"{sheet_name}!A1:Z{max_rows + 1}"

    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=range_notation,
    ).execute()

    rows = result.get("values", [])

    if not rows or len(rows) < 2:
        print("振り返りログが見つかりませんでした（ヘッダーのみ or 空）。")
        return []

    # 1行目をヘッダーとして扱う
    headers = rows[0]
    data_rows = rows[1:]  # 2行目以降がデータ

    # 各行を {ヘッダー: 値} の辞書に変換する
    logs = []
    for row in data_rows:
        # 行の列数がヘッダーより少ない場合は空文字で埋める
        padded_row = row + [""] * (len(headers) - len(row))
        log_entry = dict(zip(headers, padded_row))
        logs.append(log_entry)

    print(f"{len(logs)} 件の振り返りログを取得しました。")
    return logs


def logs_to_text(logs: list[dict], recent_count: int = 14) -> str:
    """
    振り返りログを Claude に渡すためのテキストに変換する。

    Args:
        logs: get_reflection_logs() の戻り値
        recent_count: 渡す直近のログ件数（多すぎるとトークンが増えるので制限）

    Returns:
        str: ログをまとめたテキスト
    """
    if not logs:
        return "振り返りログのデータがありません。"

    # 直近のデータだけを使う（リストの末尾 = 最新）
    recent_logs = logs[-recent_count:]

    lines = ["【過去の振り返りログ】"]
    for log in recent_logs:
        # 辞書のキーと値を「キー: 値」形式で並べる
        entry_parts = [f"{key}: {value}" for key, value in log.items() if value.strip()]
        if entry_parts:
            lines.append("---")
            lines.append("\n".join(entry_parts))

    return "\n".join(lines)


def append_summary(sheets_service, spreadsheet_id: str, sheet_name: str, summary_data: dict) -> None:
    """
    コーチングレポートのサマリーをスプレッドシートに1行追記する。

    Args:
        sheets_service: Google Sheets API のサービスオブジェクト
        spreadsheet_id: スプレッドシートのID
        sheet_name: 追記先のシート名
        summary_data: 追記するデータの辞書（キーがヘッダー名と一致している必要がある）
    """
    print(f"スプレッドシートにサマリーを追記中...")

    # 追記する値のリスト（順番はスプレッドシートのヘッダーに合わせる）
    # ここでは summary_data の値を順番に並べて追記する
    row_values = list(summary_data.values())

    # append メソッドで末尾に行を追加する
    range_notation = f"{sheet_name}!A1"
    body = {"values": [row_values]}

    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_notation,
        valueInputOption="USER_ENTERED",  # 日付などをGoogleが自動解釈する
        insertDataOption="INSERT_ROWS",   # 既存データの下に追加
        body=body,
    ).execute()

    print("スプレッドシートへの追記が完了しました。")


def build_summary_row(report_text: str, target_date: datetime = None) -> dict:
    """
    コーチングレポートから、スプレッドシートに追記するサマリー行を作成する。

    Args:
        report_text: coach.py が生成したレポートのテキスト
        target_date: 対象日（省略すると今日）

    Returns:
        dict: シートに追記するデータ
    """
    if target_date is None:
        target_date = datetime.now(JST)

    date_str = target_date.strftime("%Y/%m/%d")

    # レポートから【④ 今日の戦略】セクションだけを抜き出す（簡易パース）
    strategy_section = _extract_section(report_text, "④ 今日の戦略")
    advice_section = _extract_section(report_text, "⑤ 行動アドバイス")

    return {
        "日付": date_str,
        "今日の戦略": strategy_section[:200] if strategy_section else "",  # 長すぎる場合は200文字で切る
        "行動アドバイス": advice_section[:200] if advice_section else "",
        "レポート生成": "済",
    }


def _extract_section(text: str, section_name: str) -> str:
    """
    レポートテキストから指定セクションの内容を抽出するヘルパー関数。

    Args:
        text: レポート全文
        section_name: 抽出したいセクション名（例: "④ 今日の戦略"）

    Returns:
        str: そのセクションの内容（次のセクションが始まるまで）
    """
    marker = f"【{section_name}】"
    start_idx = text.find(marker)
    if start_idx == -1:
        return ""

    # セクション開始位置からテキストを切り出す
    content_start = start_idx + len(marker)
    remaining = text[content_start:]

    # 次の【...】が出てくるまでを取得
    next_section_idx = remaining.find("【")
    if next_section_idx != -1:
        return remaining[:next_section_idx].strip()
    else:
        return remaining.strip()
