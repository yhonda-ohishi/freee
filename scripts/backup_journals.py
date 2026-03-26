"""
freee仕訳帳の全件バックアップスクリプト（SessionStartフック用）

freee APIから仕訳帳を取得し、ローカル保存 → Google Driveに同期。
トークンはfreee MCPの tokens.json から取得。期限切れ時は自動リフレッシュ。
"""

import json
import sys
import os
import time
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime

FREEE_CONFIG_DIR = Path(os.path.expanduser("~/.config/freee-mcp"))
BACKUP_DIR = Path("c:/freee/logs/backup")
RCLONE = os.path.expanduser("~/bin/rclone.exe")
API_BASE = "https://api.freee.co.jp"


def load_config():
    with open(FREEE_CONFIG_DIR / "config.json", encoding="utf-8") as f:
        return json.load(f)


def load_tokens():
    with open(FREEE_CONFIG_DIR / "tokens.json", encoding="utf-8") as f:
        return json.load(f)


def save_tokens(tokens):
    with open(FREEE_CONFIG_DIR / "tokens.json", "w", encoding="utf-8") as f:
        json.dump(tokens, f, ensure_ascii=False, indent=2)


def refresh_token(config, tokens):
    """期限切れトークンをリフレッシュ"""
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": config["clientId"],
        "client_secret": config["clientSecret"],
    }).encode()

    req = urllib.request.Request(
        "https://accounts.secure.freee.co.jp/public_api/token",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())

    new_tokens = {
        "access_token": result["access_token"],
        "refresh_token": result["refresh_token"],
        "expires_at": int(time.time() * 1000) + result["expires_in"] * 1000,
        "token_type": result["token_type"],
        "scope": tokens.get("scope", ""),
    }
    save_tokens(new_tokens)
    return new_tokens


def get_access_token():
    """有効なアクセストークンを取得（必要ならリフレッシュ）"""
    config = load_config()
    tokens = load_tokens()

    # 期限切れチェック（5分前にリフレッシュ）
    if tokens.get("expires_at", 0) < int(time.time() * 1000) + 300000:
        tokens = refresh_token(config, tokens)

    return tokens["access_token"], config


def api_get(path, params, access_token):
    """freee API GET"""
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}{path}?{query}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    req.add_header("Accept", "application/json")

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def fetch_all_journals(access_token, company_id):
    """仕訳帳を全件取得（ページネーション対応）"""
    all_deals = []
    offset = 0
    limit = 100

    while True:
        data = api_get("/api/1/deals", {
            "company_id": company_id,
            "limit": limit,
            "offset": offset,
        }, access_token)

        deals = data.get("deals", [])
        if not deals:
            break

        all_deals.extend(deals)
        offset += limit

        # 全件取得完了
        if len(deals) < limit:
            break

    return all_deals


def backup_to_gdrive():
    """Google Driveに同期"""
    if Path(RCLONE).exists():
        import subprocess
        try:
            subprocess.run(
                [RCLONE, "sync", str(BACKUP_DIR), "gdrive:freee-logs/backup", "--quiet"],
                timeout=30,
                capture_output=True,
            )
        except Exception:
            pass


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    try:
        access_token, config = get_access_token()
        company_id = config.get("currentCompanyId") or config.get("defaultCompanyId")

        deals = fetch_all_journals(access_token, company_id)

        # ローカル保存
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        backup_file = BACKUP_DIR / f"journals_{today}.json"

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump({
                "backup_at": datetime.now().isoformat(),
                "company_id": company_id,
                "count": len(deals),
                "deals": deals,
            }, f, ensure_ascii=False, indent=2)

        # Google Driveに同期
        backup_to_gdrive()

        print(f"✓ 仕訳帳バックアップ完了: {len(deals)}件 → {backup_file.name}")

    except urllib.error.HTTPError as e:
        print(f"⚠ 仕訳帳バックアップ失敗: HTTP {e.code}")
    except Exception as e:
        print(f"⚠ 仕訳帳バックアップ失敗: {e}")


if __name__ == "__main__":
    main()
