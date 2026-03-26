"""
freee勘定科目検索スクリプト

Usage:
    python search_account_items.py <keyword> [--broad]

環境変数 FREEE_COMPANY_ID または引数でcompany_idを指定。

APIレスポンスが大きすぎてトークン制限を超える問題を解決する。
1. キャッシュがあればキャッシュから検索
2. なければfreee APIのtool-resultsファイルから解析してキャッシュ作成
3. キーワードで勘定科目を検索してJSON出力
"""

import json
import sys
import os
import glob
from pathlib import Path

# .envファイルから環境変数を読み込み
def load_dotenv(env_path: str = "c:/freee/.env"):
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())

load_dotenv()

CACHE_DIR = Path(os.environ.get("FREEE_CACHE_DIR", os.path.expanduser("~/.claude/projects/c--freee/freee-cache")))


def load_cache(company_id: str) -> list | None:
    cache_file = CACHE_DIR / f"account_items_{company_id}.json"
    if cache_file.exists():
        with open(cache_file, encoding="utf-8") as f:
            return json.load(f)
    return None


def save_cache(company_id: str, items: list):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / f"account_items_{company_id}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def find_tool_results_file() -> str | None:
    """最新のaccount_items APIレスポンスファイルを探す"""
    base = Path(os.path.expanduser("~/.claude/projects/c--freee"))
    patterns = [
        str(base / "*/tool-results/mcp-freee-mcp-freee_api_get-*.txt"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    # 最新ファイルから探す
    candidates.sort(key=os.path.getmtime, reverse=True)

    for filepath in candidates:
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read(200)
            if "account_items" in content:
                return filepath
        except Exception:
            continue
    return None


def parse_tool_results(filepath: str) -> list:
    """MCP tool-resultsファイルからaccount_itemsを抽出"""
    with open(filepath, encoding="utf-8") as f:
        raw = json.load(f)

    # 構造: [{"type": "text", "text": "{\"account_items\": [...]}"}]
    inner = json.loads(raw[0]["text"])
    return inner["account_items"]


def search_items(items: list, keyword: str, broad: bool = False) -> list:
    """キーワードで勘定科目を検索

    デフォルト: 名前・ショートカットのみ検索
    broad=True: カテゴリも含めて検索
    """
    keyword_lower = keyword.lower()
    results = []
    for item in items:
        name = item.get("name", "")
        shortcut = item.get("shortcut", "")
        category = item.get("account_category", "")

        if broad:
            searchable = f"{name} {shortcut} {category}".lower()
        else:
            searchable = f"{name} {shortcut}".lower()

        if keyword_lower in searchable:
            results.append({
                "id": item["id"],
                "name": name,
                "tax_code": item.get("tax_code"),
                "default_tax_code": item.get("default_tax_code"),
                "shortcut": shortcut,
                "shortcut_num": item.get("shortcut_num"),
                "account_category": category,
                "available": item.get("available"),
            })
    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python search_account_items.py <keyword> [--broad]", file=sys.stderr)
        print("  環境変数 FREEE_COMPANY_ID を設定するか .env に記載", file=sys.stderr)
        sys.exit(1)

    keyword = sys.argv[1]
    broad = "--broad" in sys.argv
    company_id = os.environ.get("FREEE_COMPANY_ID", "")
    if not company_id:
        print(json.dumps({"error": "FREEE_COMPANY_ID が未設定。.env に記載してください"}, ensure_ascii=False))
        sys.exit(1)

    # Ensure UTF-8 output
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. キャッシュから読み込み
    items = load_cache(company_id)

    # 2. キャッシュなければtool-resultsから解析
    if items is None:
        filepath = find_tool_results_file()
        if filepath:
            items = parse_tool_results(filepath)
            save_cache(company_id, items)
        else:
            print(json.dumps({"error": "account_itemsのキャッシュもtool-resultsファイルも見つかりません。先にfreee_api_getで/api/1/account_itemsを呼んでください。"}, ensure_ascii=False))
            sys.exit(1)

    # 3. 検索
    results = search_items(items, keyword, broad=broad)

    print(json.dumps({
        "keyword": keyword,
        "count": len(results),
        "items": results
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
