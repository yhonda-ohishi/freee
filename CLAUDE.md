# CLAUDE.md

freee会計のMCPサーバー連携プロジェクト。法人設立後の会計処理をClaude Code + freee MCP経由で行う。

## freee MCP操作

freee APIはすべてMCPツール経由で呼び出す（`mcp__*__freee_api_*`）。
tool prefix は起動環境で変わる — 詳細は freee-map skill を参照。

## 規範 (hard constraint)

- **銀行同期済み明細**: `POST /api/1/deals` に payments を付けて取引を作らない（別明細が生成され二重計上になる）。明細の処理は **`/api/1/wallet_txns/{id}/...` 系API** で行う — 既存取引への消込は `reconcile`（body: `{"company_id", "deals": [{"deal_id", "amount"}]}`）、新規取引は `create_deal`。給与計算・freee請求書から作られた既存取引がある明細は、新規作成せず必ず `reconcile` で消し込む。請求書から取引を作るAPIは無いため、請求書の入金はWeb画面で「取引を登録」してもらってから消込する。
- **freee-invoice-review**: 読み取り専用。自動で登録・修正は行わない。
- **機密情報**: `.env` に格納（`FREEE_COMPANY_ID` 等、gitignore済み）。秘密情報をLLMコンテキストや会話に出さない。

## 主要スキル

- `freee-account-search` — 勘定科目検索（APIは156K文字超過のためscript経由）
- `freee-invoice-check` — 発行請求書ステータス一括チェック
- `freee-invoice-review` — 請求書1件の事前確認・事後反映確認（読み取り専用）
- `freee-unmatched-check` — 銀行/CC/現金口座の未仕訳明細確認

詳細 (MCP tool prefix 環境差・勘定科目検索手順・gotcha・自動ログ・書類管理) は freee-map skill を参照。
