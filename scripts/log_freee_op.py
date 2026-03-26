"""
freee MCP操作の自動ログスクリプト（PostToolUseフック用）

stdin からフックデータを受け取り、サービス別フォルダにJSON追記する。

ログ構造:
  c:/freee/logs/
    accounting/2026-03-26.json
    hr/2026-03-26.json
    invoices/2026-03-26.json
    ...
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

LOGS_DIR = Path("c:/freee/logs")

# freee APIパスからサービスを判定
SERVICE_MAP = {
    "/api/1/": "accounting",
    "/hr/api/v1/": "hr",
    "/api/1/invoices": "invoices",
    "/api/1/quotations": "invoices",
    "/api/1/time_clocks": "time_tracking",
    "/api/1/time_entries": "time_tracking",
    "/api/1/sales": "sales",
}


def detect_service(path: str, service_hint: str = "") -> str:
    """APIパスとサービスヒントからサービス種別を判定"""
    if service_hint:
        mapping = {
            "accounting": "accounting",
            "hr": "hr",
            "payroll": "hr",
            "invoice": "invoices",
            "time_tracking": "time_tracking",
            "sales": "sales",
        }
        if service_hint in mapping:
            return mapping[service_hint]

    for prefix, svc in SERVICE_MAP.items():
        if path.startswith(prefix):
            return svc
    return "other"


def detect_method(tool_name: str) -> str:
    """ツール名からHTTPメソッドを判定"""
    if "get" in tool_name:
        return "GET"
    elif "post" in tool_name:
        return "POST"
    elif "put" in tool_name:
        return "PUT"
    elif "patch" in tool_name:
        return "PATCH"
    elif "delete" in tool_name:
        return "DELETE"
    elif "upload" in tool_name:
        return "UPLOAD"
    return "UNKNOWN"


def main():
    sys.stdin.reconfigure(encoding="utf-8")

    try:
        hook_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    tool_name = hook_data.get("tool_name", "")

    # freee MCP ツール以外は無視
    if not tool_name.startswith("mcp__freee"):
        return

    tool_input = hook_data.get("tool_input", {})

    # 認証系・情報系はログ不要
    skip_tools = [
        "freee_auth_status", "freee_authenticate", "freee_clear_auth",
        "freee_server_info", "freee_current_user",
        "freee_list_companies", "freee_get_current_company", "freee_set_current_company",
        "freee_api_list_paths",
    ]
    for skip in skip_tools:
        if skip in tool_name:
            return

    path = tool_input.get("path", "")
    service_hint = tool_input.get("service", "")
    method = detect_method(tool_name)
    service = detect_service(path, service_hint)

    # ログエントリ作成
    entry = {
        "timestamp": datetime.now().isoformat(),
        "tool": tool_name,
        "method": method,
        "path": path,
        "service": service,
    }

    # GETはqueryパラメータを記録
    if method == "GET" and "query" in tool_input:
        entry["query"] = tool_input["query"]

    # POST/PUT/PATCHはbodyのキーのみ記録（データは大きいので）
    if method in ("POST", "PUT", "PATCH") and "body" in tool_input:
        body = tool_input["body"]
        if isinstance(body, dict):
            entry["body_keys"] = list(body.keys())
            # 金額と科目名は記録
            if "details" in body:
                details_summary = []
                for d in body["details"]:
                    summary = {}
                    for k in ["amount", "description", "account_item_id", "tax_code"]:
                        if k in d:
                            summary[k] = d[k]
                    details_summary.append(summary)
                entry["details"] = details_summary

    # ログファイルに追記
    log_dir = LOGS_DIR / service
    log_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"{today}.json"

    entries = []
    if log_file.exists():
        try:
            with open(log_file, encoding="utf-8") as f:
                entries = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            entries = []

    entries.append(entry)

    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
