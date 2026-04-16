"""
setup_spreadsheet.py
--------------------
振り返りログ用のGoogleスプレッドシートを自動で作成するセットアップスクリプト。

【実行すると以下が作られる】
- 「ライフコーチ振り返りログ」というスプレッドシート
- 「振り返りログ」シート（毎日の記録用）
- 「コーチングサマリー」シート（レポート出力用）
- ヘッダー行と使い方のサンプルデータ

【実行方法】
    python setup_spreadsheet.py
"""

import os
import sys
from dotenv import load_dotenv
from google_auth import build_services



def main():
    """スプレッドシートを作成してIDを表示する"""

    load_dotenv()

    print("Google API に接続中...")
    services = build_services()
    sheets = services["sheets"]
    drive = services["drive"]

    # ① スプレッドシートを新規作成する
    print("\nスプレッドシートを作成中...")

    spreadsheet_body = {
        "properties": {
            "title": "ライフコーチ振り返りログ",
            "locale": "ja_JP",           # 日本語ロケール
            "timeZone": "Asia/Tokyo",    # 日本時間
        },
        "sheets": [
            # シート1: 毎日の振り返りログ
            {
                "properties": {
                    "title": "振り返りログ",
                    "gridProperties": {
                        "rowCount": 1000,
                        "columnCount": 10,
                    },
                }
            },
            # シート2: コーチングレポートのサマリー（main.py が自動追記する）
            {
                "properties": {
                    "title": "コーチングサマリー",
                    "gridProperties": {
                        "rowCount": 1000,
                        "columnCount": 6,
                    },
                }
            },
        ],
    }

    spreadsheet = sheets.spreadsheets().create(body=spreadsheet_body).execute()
    spreadsheet_id = spreadsheet["spreadsheetId"]
    sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    print(f"スプレッドシートを作成しました！")

    # ② 各シートのIDを取得する（スタイル設定に必要）
    sheet_ids = {}
    for sheet in spreadsheet["sheets"]:
        title = sheet["properties"]["title"]
        sheet_ids[title] = sheet["properties"]["sheetId"]

    # ③ 「振り返りログ」シートにヘッダーとサンプルデータを入力する
    print("振り返りログシートを設定中...")
    _setup_reflection_sheet(sheets, spreadsheet_id, sheet_ids["振り返りログ"])

    # ④ 「コーチングサマリー」シートにヘッダーを入力する
    print("コーチングサマリーシートを設定中...")
    _setup_summary_sheet(sheets, spreadsheet_id, sheet_ids["コーチングサマリー"])

    # ⑤ 結果を表示する
    print("\n" + "=" * 50)
    print("✅ セットアップ完了！")
    print("=" * 50)
    print(f"\n📊 スプレッドシートURL:\n   {sheet_url}")
    print(f"\n🔑 SPREADSHEET_ID:\n   {spreadsheet_id}")
    print("\n【次にやること】")
    print("1. 上記の SPREADSHEET_ID をコピーする")
    print("2. .env ファイルを開く")
    print("3. SPREADSHEET_ID=your_spreadsheet_id_here の行を以下に書き換える")
    print(f"   SPREADSHEET_ID={spreadsheet_id}")
    print("\n4. スプレッドシートを開いて、振り返りログの入力を始めてください。")
    print(f"   {sheet_url}")


def _setup_reflection_sheet(sheets, spreadsheet_id: str, sheet_id: int) -> None:
    """
    「振り返りログ」シートにヘッダーとサンプルデータを書き込み、
    ヘッダー行のスタイルを設定する。

    【列の構成】
    A: 日付
    B: よかったこと（今日うまくいったこと）
    C: 改善点（次回直したいこと）
    D: 感情スコア（1〜10）
    E: 完了タスク
    F: 未完了タスク
    G: 明日の目標
    H: メモ・気づき
    """

    # ヘッダー行
    headers = [
        "日付",
        "よかったこと",
        "改善点",
        "感情スコア(1-10)",
        "完了タスク",
        "未完了タスク",
        "明日の目標",
        "メモ・気づき",
    ]

    # サンプルデータ（入力例として2行分）
    sample_rows = [
        [
            "2026/04/09",
            "朝のルーティンを守れた。MTGの準備を前日にできた。",
            "夕方に集中力が落ちた。メールの返信が遅れた。",
            "7",
            "企画書作成・チームMTG・メール整理",
            "週次レポート",
            "週次レポートを午前中に完成させる",
            "昼食後の眠気が強い。15分仮眠が効果的だった。",
        ],
        [
            "2026/04/10",
            "週次レポートを期限前に提出できた。",
            "朝の準備に時間がかかりすぎた。タスクの優先順位付けが甘かった。",
            "6",
            "週次レポート・クライアント対応",
            "来週の計画作成",
            "朝の準備を30分短縮する・来週の計画を今日中に作る",
            "タスクが多いと判断が鈍る。重要度×緊急度マトリクスを使ってみる。",
        ],
    ]

    # データをまとめてシートに書き込む
    all_values = [headers] + sample_rows
    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="振り返りログ!A1",
        valueInputOption="USER_ENTERED",
        body={"values": all_values},
    ).execute()

    # ヘッダー行のスタイルを設定する（太字・背景色）
    requests = [
        # ヘッダー行を太字にする
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {
                            "red": 0.27,
                            "green": 0.51,
                            "blue": 0.71,
                        },
                        "foregroundColor": {
                            "red": 1.0,
                            "green": 1.0,
                            "blue": 1.0,
                        },
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor,foregroundColor,horizontalAlignment)",
            }
        },
        # 列幅を自動調整する
        {
            "autoResizeDimensions": {
                "dimensions": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 8,
                }
            }
        },
        # ヘッダー行を固定する（スクロールしてもヘッダーが見える）
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


def _setup_summary_sheet(sheets, spreadsheet_id: str, sheet_id: int) -> None:
    """
    「コーチングサマリー」シートにヘッダーを書き込み、スタイルを設定する。
    このシートには main.py が自動でサマリーを追記していく。
    """

    headers = [
        "日付",
        "今日の戦略",
        "行動アドバイス",
        "レポート生成",
    ]

    sheets.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range="コーチングサマリー!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [headers]},
    ).execute()

    # ヘッダーのスタイル設定
    requests = [
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {"bold": True},
                        "backgroundColor": {
                            "red": 0.20,
                            "green": 0.66,
                            "blue": 0.33,
                        },
                        "foregroundColor": {
                            "red": 1.0,
                            "green": 1.0,
                            "blue": 1.0,
                        },
                        "horizontalAlignment": "CENTER",
                    }
                },
                "fields": "userEnteredFormat(textFormat,backgroundColor,foregroundColor,horizontalAlignment)",
            }
        },
        {
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sheet_id,
                    "gridProperties": {"frozenRowCount": 1},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        },
    ]

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


if __name__ == "__main__":
    main()
