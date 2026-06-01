# 請求 — 定期請求の運用 spec（合同会社一歩庵）

freee 請求書での定期請求（毎月の業務委託料請求）の運用メモ。CCoW / Claude が
freee MCP 経由で請求まわりを扱うときの前提・gotcha をまとめる。

## 事業所 / プロダクト

- 事業所: 合同会社一歩庵 (`company_id = 12534560`)
- 適格請求書 登録番号: `T7290003018211`
- 請求書は **freee請求書 API**（`service: "invoice"`, base `https://api.freee.co.jp/iv`）を使う。
  会計の `/api/1/invoices` は旧 API なので使わない（参照のみ）。

### gotcha: company_id は必須（自動付与されない）

freee請求書 API は会計 API と違い `company_id` を自動付与しない。GET/POST いずれも
query / body に `company_id` を入れないと `401 company_not_found` になる
（freee/freee-mcp #169）。

## 定期請求の条件（大石運輸倉庫㈱）

| 項目 | 値 |
|---|---|
| 取引先 | 大石運輸倉庫株式会社 (`partner_id = 116451908`, 御中, 担当 大庭安子) |
| 金額 | ¥110,000（業務委託料 税抜 ¥100,000 + 消費税10% ¥10,000）|
| サイクル | 毎月 / 月末締め |
| 請求日(発行) | 翌月初日（例: 5月分 → 2026-06-01）|
| 支払期日 | 発行月の15日（例: 2026-06-15）/ 振込 |
| テンプレート | `template_id = 4506007`（レイアウト１/クラシック）|
| 税処理 | tax_entry_method=out / tax_fraction=omit / withholding=out |
| 振込先 | 三井住友銀行 トランクNORTH支店 普通 0622339 ﾄﾞ)ｲﾂﾎﾟｱﾝ |

## 運用フロー

1. **定期生成は freee UI の「作成予約」**で設定（API では作成・取得とも不可）。
   - その他設定 → 作成予約 → 新規作成、または既存請求書から「この内容で作成予約する」。
   - 作成サイクル=毎月 / 作成日=毎月1日 / 請求日=作成日 / 支払期日=発行月15日。
2. 毎月1日に請求書が自動生成（下書き: sending_status=unsent, issue_date=null）。
3. **送付も UI 操作**。API に送付/発行エンドポイントは無く、`sending_status` は
   レスポンス専用で POST/PUT 不可。UI で「送付」→ sending_status=sent。
   - 宛先メールは body 未指定でも取引先マスタの担当者メールにフォールバックする。

## API でできること（Claude 側の確認・補助）

- 一覧/詳細: `GET /invoices?company_id=12534560` / `GET /invoices/{id}?company_id=...`
- 作成: `POST /invoices`（下記 body）。※下書き作成のみ。送付はされない。
- テンプレ一覧: `GET /invoices/templates?company_id=...`（id/name のみ返る）
- 送付確認: `GET /invoices/{id}` → `sending_status: sent` / `email_url_file_downloaded_status`
- 会計連携(deal)確認: `GET /api/1/deals/{deal_id}?company_id=...`

### POST /invoices body テンプレ

    {
      "company_id": 12534560,
      "template_id": 4506007,
      "partner_id": 116451908,
      "partner_title": "御中",
      "billing_date": "<翌月初日 YYYY-MM-01>",
      "payment_date": "<同月15日 YYYY-MM-15>",
      "payment_type": "transfer",
      "tax_entry_method": "out",
      "tax_fraction": "omit",
      "line_amount_fraction": "omit",
      "withholding_tax_entry_method": "out",
      "lines": [
        { "type": "item", "description": "業務委託料", "quantity": 1,
          "unit_price": "100000", "tax_rate": 10 }
      ]
    }

## 会計仕訳（請求書から自動生成される deal）

- 売上計上日(発生日) = **当月末**（月末締め。例: 5月分は 2026-05-31）。請求書の
  billing_date(翌月初) とズレるが、これが正しい（売上は当月、請求発行は翌月）。
- 勘定科目 `account_item_id = 1028600188`、税区分 `tax_code = 129`（課税売上10%）、貸方。
- 入金は **三井住友 (`walletable_id = 4712555`)** に着金 → freee「自動で経理」で消込
  （wallet_txn status 1→2）。
- 実績: INV-0000000001(5月分) は 2026-05-11 入金で settled。
  INV-0000000002(6月分) は 2026-06-15 期日・入金待ち。

## 参考

- freee請求書 API: https://developer.freee.co.jp/reference/iv
- 作成予約(定期請求): https://support.freee.co.jp/hc/ja/articles/19290676111257
- skill: `freee-api-skill`（repo `.claude/skills/`）, `freee-unmatched-check`
