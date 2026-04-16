"""
google_auth.py
--------------
Google API への OAuth 2.0 認証を担当するモジュール。

【仕組み】
1. 初回実行: ブラウザが開いてGoogleアカウントでログインを求められる
2. 認証後: token.json にトークンが保存される
3. 次回以降: token.json を読み込んで自動ログイン（期限切れなら自動更新）
"""


import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 使用する Google API のスコープ（必要最小限のみ）
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",  # カレンダー読み取り
    "https://www.googleapis.com/auth/gmail.readonly",     # プロフィール取得（送信先メアド用）
    "https://www.googleapis.com/auth/gmail.send",         # メール送信
]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"


def get_credentials() -> Credentials:
    """
    有効な Google API 認証情報を取得する。
    token.json がなければブラウザでログインを求める。
    """
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("トークンを更新しています...")
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} が見つかりません。\n"
                    "Google Cloud Console から OAuth 2.0 クライアントIDをダウンロードして、"
                    "このフォルダに置いてください。"
                )
            print("ブラウザでGoogleアカウントにログインしてください...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"認証情報を {TOKEN_FILE} に保存しました。")

    return creds


def build_services() -> dict:
    """
    使用する Google API のサービスオブジェクトをまとめて作成して返す。

    Returns:
        dict: {"calendar": ..., "gmail": ...}
    """
    creds = get_credentials()
    services = {
        "calendar": build("calendar", "v3", credentials=creds),
        "gmail":    build("gmail",    "v1", credentials=creds),
    }
    print("Google API への接続が完了しました。")
    return services
