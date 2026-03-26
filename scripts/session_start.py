"""
セッション開始時の初期化スクリプト（SessionStartフック用）

1. .env の存在チェック
2. freee認証状態の確認
3. todo.json の未完了タスク表示
4. 前回作業ログのサマリ表示
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE = Path("c:/freee")


def check_env():
    env_path = BASE / ".env"
    if not env_path.exists():
        print("⚠ .env ファイルが見つかりません。FREEE_COMPANY_ID を設定してください。")
        return

    with open(env_path, encoding="utf-8") as f:
        content = f.read()

    if "FREEE_COMPANY_ID" not in content:
        print("⚠ .env に FREEE_COMPANY_ID が未設定です。")
    else:
        print("✓ .env OK")


def check_freee_auth():
    try:
        result = subprocess.run(
            ["claude", "mcp", "call", "freee-mcp", "freee_auth_status", "{}"],
            capture_output=True, text=True, timeout=10, encoding="utf-8"
        )
        if "authenticated" in result.stdout.lower() or "true" in result.stdout.lower():
            print("✓ freee認証 OK")
        else:
            print("⚠ freee未認証 — freee_authenticate を実行してください")
    except Exception:
        print("⚠ freee認証状態の確認に失敗（MCP未接続の可能性）")


def show_todos():
    todo_path = BASE / "logs" / "todo.json"
    if not todo_path.exists():
        return

    try:
        with open(todo_path, encoding="utf-8") as f:
            todos = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    pending = [t for t in todos if t.get("status") in ("pending", "in_progress", "blocked")]
    if not pending:
        print("✓ 未完了タスクなし")
        return

    print(f"\n📋 未完了タスク ({len(pending)}件):")
    for t in pending:
        status_icon = {"pending": "○", "in_progress": "◐", "blocked": "✗"}
        icon = status_icon.get(t["status"], "?")
        dep = f" (#{t['depends_on']}待ち)" if t.get("depends_on") else ""
        print(f"  {icon} [{t['id']}] {t['task']}{dep}")


def show_last_log():
    logs_dir = BASE / "logs"

    # 全サービスフォルダから最新のログファイルを探す
    latest_file = None
    latest_mtime = 0

    for service_dir in logs_dir.iterdir():
        if not service_dir.is_dir():
            continue
        for log_file in service_dir.glob("*.json"):
            mtime = log_file.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_file = log_file

    if not latest_file:
        return

    try:
        with open(latest_file, encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return

    if not entries:
        return

    service = latest_file.parent.name
    date = latest_file.stem

    print(f"\n📝 前回作業 ({date} / {service}): {len(entries)}件")
    for entry in entries[-5:]:  # 最新5件
        ts = entry.get("timestamp", "")[:16]
        if entry.get("type") == "memo":
            print(f"  {ts} memo: {entry.get('description', '')}")
        elif entry.get("type") == "setup":
            print(f"  {ts} setup: {entry.get('description', '')}")
        else:
            method = entry.get("method", "")
            path = entry.get("path", "")
            print(f"  {ts} {method} {path}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("=== freee session start ===\n")
    check_env()
    check_freee_auth()
    show_todos()
    show_last_log()
    print("\n===========================")


if __name__ == "__main__":
    main()
