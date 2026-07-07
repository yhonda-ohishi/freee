---
name: freee-map
generated-from: freee:b80e90ad0acbf5bcf7fbf0fa3dfc2c1087328ea0
paths: [.claude/skills/, scripts/, CLAUDE.md]
description: ippoan/freee (法人会計を Claude Code + freee MCP 経由で行う薄い運用 repo。CLAUDE.md + hook scripts + .claude/skills/freee-* の skill 群) の構造ナビゲーション。MCP tool prefix の環境差 / 自動ログ hook / 勘定科目検索 / 銀行同期明細の消込制約 / 発行請求書ステータスチェックの gotcha を 1 枚にまとめる。トリガー:「freee」「freee MCP」「勘定科目検索」「未仕訳」「消込」「自動で経理」「freee_api」「会計処理」「仕訳登録」「freee ログ」「FREEE_COMPANY_ID」「請求書チェック」「請求書ステータス」等。
---

# freee-map — ippoan/freee 構造ナビゲーション

法人設立後の会計処理を **Claude Code + freee MCP** で回す薄い運用 repo。アプリ code は
無く、`CLAUDE.md` (運用ルール) + `scripts/` (hook) + `.claude/skills/freee-*` (freee 操作
skill 群) で構成される。freee API は全て MCP tool (`mcp__*__freee_api_*`) 経由で叩く。

> ここは索引 (pointer)。細部は repo 側が正。frontmatter の `generated-from` が現在の
> repo tree-sha とズレたら session-start hook が再生成を促す → その時 tree-sha を更新する。

## 区画

| 区画 | パス | 役割 |
|---|---|---|
| **運用ルール** | `CLAUDE.md` | MCP tool prefix の環境差 / 勘定科目検索 / 銀行同期明細の消込制約 / 自動ログ / TODO / 書類管理 / Windows 注意 |
| **hook scripts** | `scripts/*.py` | SessionStart / PostToolUse hook 実体 (下表)。`.claude/settings.json` から起動 |
| **hook 設定** | `.claude/settings.json` | SessionStart 3 本 + PostToolUse (matcher `mcp__freee-mcp__freee_api_*`) 2 本 |
| **freee skill 群** | `.claude/skills/freee-*/SKILL.md` | freee 操作の詳細 skill (下表) |

### scripts/ (hook 実体)

| script | hook | 役割 |
|---|---|---|
| `session_start.py` | SessionStart | `.env` 存在 + freee 認証状態 + todo.json + 前回ログサマリ |
| `backup_journals.py` | SessionStart | 仕訳帳を freee API から全件取得 → ローカル + Google Drive 同期 (token は freee MCP の tokens.json から、期限切れ自動 refresh) |
| `backup_logs.py` | SessionStart / PostToolUse | rclone で `logs/` → `gdrive:freee-logs/` 同期 |
| `log_freee_op.py` | PostToolUse | stdin の hook data を service 別フォルダに日付別 JSON 追記 (認証/取得系は skip) |

### .claude/skills/ (freee 操作 skill)

| skill | 役割 |
|---|---|
| `freee-api-skill` | freee-mcp / freee-sign-mcp の詳細 API リファレンス + recipes/ + references/ + sign-references/ (会計・人事労務・請求書・工数・販売・電子契約)。freee_jp 公式 (Apache-2.0) |
| `freee-account-search` | 勘定科目 (account_items) 検索。198 件で 156K 文字 → token 超過するため専用 python script + cache 経由 |
| `freee-unmatched-check` | 銀行/CC/現金口座の未仕訳 (消込待ち) 明細の一括確認 |
| `freee-invoice-check` | 発行請求書 (売上請求書) のステータス一括チェック。送付漏れ・入金期限超過/間近・仕訳未登録を `service: "invoice"` API で検出 (会計API旧 `/api/1/invoices` とは別物) |
| `freee-invoice-review` | 請求書1件ごとの事前確認（画像レビュー＋重複懸念チェック）＋送信後の反映確認（2フェーズ、読み取り専用）。`freee-invoice-check` の一括監査とは異なり、今まさに送ろうとしている1件のピンポイント確認用 |

## entrypoint / 起動フロー

- code の entrypoint は無い。**SessionStart hook (`.claude/settings.json`)** が repo を開いた時に session_start / backup_journals / backup_logs を走らせるのが実質の起点。
- 以降の freee 操作は MCP tool 呼び出し → PostToolUse hook (`log_freee_op` + `backup_logs`) で自動記録。
- log は service 別: `logs/{accounting,hr,invoices,time_tracking,sales,social_insurance}/<date>.json`。

## gotcha (CLAUDE.md 由来)

- **MCP tool prefix は起動環境で変わる**: local (CLI/Desktop) = `mcp__freee-mcp__freee_api_*` / CCoW = `mcp__<connector-uuid>__freee_api_*` (例 `ac8e39b2-...`)。doc では `mcp__*__freee_api_*` とワイルドカード表記。**`.claude/settings.json` の PostToolUse matcher は `mcp__freee-mcp__freee_api_*` 固定なので、CCoW (UUID prefix) では自動ログ hook が match せず発火しない点に注意**。
- **勘定科目は直接 API を叩かず `freee-account-search` script を使う** (156K 文字で token 超過)。`--broad` でカテゴリ含む広域検索。cache は `~/.claude/projects/c--freee/freee-cache/`。
- **銀行同期済み明細は API で取引を作らない**: freee API に消込機能が無く、deals 作成時の payments が別明細を生成して重複する。銀行同期口座の仕訳は **freee Web 画面の「自動で経理」から登録**するよう user に案内する。
- **発行請求書は `service: "invoice"` を使う**: 会計API旧 `/api/1/invoices` (`service: "accounting"`) とは別の独立API (ベースURL `https://api.freee.co.jp/iv`)。`freee-invoice-check` は送付漏れ・入金期限超過/間近・仕訳未登録をサーバー側フィルタ (`sending_status`/`payment_status`/`deal_status`/`cancel_status`) で検出し、全件取得してのクライアント側フィルタは行わない。
- 機密は `.env` (`FREEE_COMPANY_ID`、gitignore 済)。MCP では `freee_get_current_company` でも取得可。
- 書類 `docs/` (social_insurance / tax) は gitignore 済 + rclone で Google Drive backup。
- Windows 環境: python 出力は `PYTHONIOENCODING=utf-8` を付ける。bash シェル (Unix 構文)。パスは `c:/freee/...` 前提で settings.json に hard-code。

## CCoW / CI から見た立ち位置

- CI / build は無い (運用 repo)。freee MCP server への疎通は `freee_auth_status` / `freee_server_info` で確認 (参考 yhonda-ohishi/freee#1)。
- CCoW では claude.ai の custom connector 経由で `mcp.freee.co.jp/mcp` に接続 (connector UUID が tool prefix)。

## 関連 skill

- `freee-api-skill` / `freee-account-search` / `freee-unmatched-check` — repo 同梱の freee 操作 skill (上表)。本 map はそれらの索引であって個々の使い方は各 SKILL.md が正
- `repo-map` / `cross-repo-symbol-index` — この per-repo map の運用方針 (generated-from 鮮度 hook)

## CLAUDE.md から移設 (2026-07-07)

## freee MCP操作

freee APIはすべてMCPツール経由で呼び出す（`mcp__*__freee_api_*`）。

### ツール名 prefix について

freee MCP の tool prefix は **起動環境によって異なる**:

- **local (Claude Code CLI / Desktop)**: `mcp__freee-mcp__freee_api_*`
  - `~/.claude.json` 等で stdio 起動した `freee-mcp` server name がそのまま prefix
- **CCoW (Claude Code on the Web)**: `mcp__<connector-uuid>__freee_api_*`
  - claude.ai の custom connector 経由で `mcp.freee.co.jp/mcp` に接続するため、connector UUID（例: `ac8e39b2-6f6c-4ef8-9878-294530f4bb34`）が prefix になる
  - UUID はワークスペース/コネクタごとに異なる

本ドキュメントでは UUID 部をワイルドカードで `mcp__*__freee_api_*` と表記する。実呼び出し時は Claude が自動でツール名解決するため、両環境で同じ意図のコードが動く。

CCoW での疎通確認は `mcp__*__freee_auth_status` / `mcp__*__freee_server_info` で行える（参考: yhonda-ohishi/freee#1）。

### 勘定科目検索

APIレスポンスが156K文字（198科目）でトークン制限を超えるため、専用スクリプトを使う:

```bash
PYTHONIOENCODING=utf-8 python "c:/freee/.claude/skills/freee-account-search/scripts/search_account_items.py" "<keyword>"
```

`--broad` オプションでカテゴリも含めた広範囲検索。キャッシュは `~/.claude/projects/c--freee/freee-cache/` に保存。

勘定科目検索スキル (`freee-account-search`) も利用可。

### 銀行同期済み明細の仕訳登録

freee APIには銀行同期で取り込まれた明細と取引を紐づける消込機能がない（deals作成時のpaymentsは別の明細を生成し、既存明細と重複する）。銀行同期済みの口座で仕訳を登録する場合は、APIで取引を作らず**freee Web画面の「自動で経理」から登録**するようユーザーに案内する。

### 発行請求書のステータスチェック

freee請求書API (`service: "invoice"`、会計APIの旧 `/api/1/invoices` とは別物) で、送付漏れ・
入金期限超過・入金期限間近・仕訳未登録の請求書を一括検出できる。詳細は
`freee-invoice-check` スキル (`.claude/skills/freee-invoice-check/SKILL.md`) を参照。

### 請求書1件ごとの事前確認・事後反映確認

ユーザーが請求書のスクリーンショットを送ってきた時（送信前の内容確認）、および「送信した」
「登録した」と報告してきた時（送信後の反映確認）は `freee-invoice-review` スキル
(`.claude/skills/freee-invoice-review/SKILL.md`) を使う。読み取り専用（自動で登録・修正は
行わない）。

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
