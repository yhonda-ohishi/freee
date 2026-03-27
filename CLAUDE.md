# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

freee会計のMCPサーバー連携プロジェクト。法人設立後の会計処理をClaude Code + freee MCP経由で行う。

## freee MCP操作

freee APIはすべてMCPツール経由で呼び出す（`mcp__freee-mcp__freee_api_*`）。

### 勘定科目検索

APIレスポンスが156K文字（198科目）でトークン制限を超えるため、専用スクリプトを使う:

```bash
PYTHONIOENCODING=utf-8 python "c:/freee/.claude/skills/freee-account-search/scripts/search_account_items.py" "<keyword>"
```

`--broad` オプションでカテゴリも含めた広範囲検索。キャッシュは `~/.claude/projects/c--freee/freee-cache/` に保存。

勘定科目検索スキル (`freee-account-search`) も利用可。

### 環境変数

`.env` に機密情報を格納（gitignore済み）:

```
FREEE_COMPANY_ID=<company_id>
```

スクリプトは自動で `.env` を読み込む。freee MCP操作時は `freee_get_current_company` でも取得可。

## 自動ログ

PostToolUseフック（`.claude/settings.json`）が全freee API呼び出しを自動記録:

- `logs/accounting/` — 会計API
- `logs/hr/` — 人事労務API
- `logs/invoices/` — 請求書API
- `logs/time_tracking/` — 工数管理API
- `logs/sales/` — 販売API
- `logs/social_insurance/` — 社会保険手続き（年金機構・協会けんぽ）

ログは日付別JSON（例: `2026-03-26.json`）。認証系・情報取得系はスキップ。

## TODO管理

`logs/todo.json` でタスクを管理。status: pending / in_progress / blocked / done。`depends_on` で依存関係を表現。

## 書類管理

`docs/` に種類別フォルダで管理（gitignore済み、rcloneでGoogle Driveにバックアップ）:

- `docs/social_insurance/` — 社会保険関連（年金機構・協会けんぽ）
- `docs/tax/` — 税務関連（扶養控除申告書等）

## Windows環境

- Python出力のエンコーディング: `PYTHONIOENCODING=utf-8` を付ける
- bash シェル使用（Unix構文）
