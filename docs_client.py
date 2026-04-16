"""
docs_client.py
--------------
Google Docs API を使って、コーチングレポートを新しいドキュメントとして書き出すモジュール。

【出力されるドキュメントの構成】
- ファイル名: 「2026-04-11_コーチングレポート」のような日付付きの名前
- 内容: コーチングレポートのテキストをセクションごとに整形して貼り付ける
"""


import os
from datetime import datetime
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")


def create_coaching_doc(
    docs_service,
    drive_service,
    report_text: str,
    target_date: datetime = None,
    folder_id: str = None,
) -> str:
    """
    コーチングレポートを Google Docs に書き出す。

    Args:
        docs_service: Google Docs API のサービスオブジェクト
        drive_service: Google Drive API のサービスオブジェクト（フォルダ移動に使用）
        report_text: coach.py が生成したレポートのテキスト
        target_date: 対象日（省略すると今日）
        folder_id: 保存先フォルダのID（省略するとマイドライブ直下）

    Returns:
        str: 作成されたドキュメントのURL
    """
    if target_date is None:
        target_date = datetime.now(JST)

    # ドキュメントのタイトル（日付付き）
    doc_title = target_date.strftime("%Y-%m-%d") + "_コーチングレポート"

    print(f"Google Docs にドキュメントを作成中: 「{doc_title}」")

    # ① 空のドキュメントを作成する
    doc = docs_service.documents().create(
        body={"title": doc_title}
    ).execute()

    doc_id = doc["documentId"]

    # ② ドキュメントにテキストを書き込む
    _write_report_to_doc(docs_service, doc_id, report_text, target_date)

    # ③ フォルダIDが指定されている場合、そのフォルダに移動する
    if folder_id:
        _move_to_folder(drive_service, doc_id, folder_id)

    # ④ ドキュメントのURLを組み立てて返す
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"ドキュメントを作成しました: {doc_url}")

    return doc_url


def _write_report_to_doc(docs_service, doc_id: str, report_text: str, target_date: datetime) -> None:
    """
    Google Docs のドキュメントにレポートテキストを書き込む。

    Google Docs API は「batchUpdate」という仕組みでテキストを追加する。
    insertText リクエストをまとめて送ることで、見出しや本文を整形して書き込む。

    Args:
        docs_service: Google Docs API のサービスオブジェクト
        doc_id: 書き込み先のドキュメントID
        report_text: 書き込むレポートテキスト
        target_date: 対象日
    """
    date_display = target_date.strftime("%Y年%m月%d日")

    # タイトルと本文を合体させた最終テキストを作成する
    full_text = f"コーチングレポート - {date_display}\n\n{report_text}"

    # Google Docs API の batchUpdate でテキストを挿入する
    # インデックス 1 = ドキュメントの先頭（0はドキュメント自体を指すので1から始まる）
    requests = [
        {
            "insertText": {
                "location": {"index": 1},
                "text": full_text,
            }
        }
    ]

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()

    # タイトル行をヘッディングスタイルに設定する
    _apply_title_style(docs_service, doc_id, full_text)


def _apply_title_style(docs_service, doc_id: str, full_text: str) -> None:
    """
    ドキュメントの最初の行（タイトル）を「見出し1」スタイルに変更する。

    Args:
        docs_service: Google Docs API のサービスオブジェクト
        doc_id: ドキュメントID
        full_text: 書き込んだテキスト全文（タイトル行の長さを計算するため）
    """
    # タイトル行の文字数を取得（改行文字も1文字として数える）
    first_line = full_text.split("\n")[0]
    title_end_index = len(first_line) + 1  # +1 は index が 1 始まりのため

    requests = [
        {
            # 段落スタイルを「見出し1」に変更
            "updateParagraphStyle": {
                "range": {
                    "startIndex": 1,
                    "endIndex": title_end_index,
                },
                "paragraphStyle": {
                    "namedStyleType": "HEADING_1"
                },
                "fields": "namedStyleType",
            }
        }
    ]

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()


def _move_to_folder(drive_service, file_id: str, folder_id: str) -> None:
    """
    Google Drive上のファイルを指定フォルダに移動する。

    Drive API では「移動」= 既存の親フォルダを外して新しい親フォルダを設定する操作。

    Args:
        drive_service: Google Drive API のサービスオブジェクト
        file_id: 移動するファイルのID
        folder_id: 移動先フォルダのID
    """
    # まず現在の親フォルダを取得する
    file_info = drive_service.files().get(
        fileId=file_id,
        fields="parents",
    ).execute()

    current_parents = ",".join(file_info.get("parents", []))

    # 親フォルダを入れ替える
    drive_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=current_parents,
        fields="id, parents",
    ).execute()

    print(f"ドキュメントを指定フォルダに移動しました。")
