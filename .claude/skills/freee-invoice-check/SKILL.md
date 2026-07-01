---
name: freee-invoice-check
description: freeeで発行した請求書（売上請求書）のステータスを一括チェックするスキル。送付漏れ・入金期限超過・入金期限間近・仕訳（取引）未登録の請求書を検出する。「請求書チェック」「請求書ステータス確認」「未入金請求書」「入金期限超過」「送付漏れ」「仕訳未登録の請求書」「invoice status check」などのフレーズで起動。
---

# freee 発行請求書ステータスチェック

freee請求書API (`service: "invoice"`) で発行済みの請求書一覧を取得し、対応が必要な請求書を
カテゴリ別に抽出する。会計API旧エンドポイント (`/api/1/invoices`) ではなく、必ず
`service: "invoice"` (ベースURL `https://api.freee.co.jp/iv`) を使うこと
(`freee-api-skill/recipes/invoice-operations.md` 参照)。

## 前提

- 事業所IDが未取得なら `freee_get_current_company` を先に呼ぶ
- 実行日 (今日の日付) を基準に期限判定を行う

## チェック対象カテゴリ

freee請求書APIの `sending_status` / `payment_status` / `deal_status` / `cancel_status`
クエリパラメータでサーバー側フィルタし、該当件数だけ取得する（全件取得してクライアント側で
絞り込まない）。`cancel_status: "canceled"` の請求書は全カテゴリで対象外。

### Step 1: 送付漏れ（未送付）

```
freee_api_get {
  "service": "invoice",
  "path": "/invoices",
  "query": {
    "company_id": <company_id>,
    "sending_status": "unsent",
    "cancel_status": "uncanceled",
    "limit": 100
  }
}
```

### Step 2: 入金期限超過（未入金）

`end_payment_date` に実行日を指定すると、入金期日がその日以前の請求書に絞り込める
（= 今日時点で期限超過しているのに未入金のもの）。

```
freee_api_get {
  "service": "invoice",
  "path": "/invoices",
  "query": {
    "company_id": <company_id>,
    "payment_status": "unsettled",
    "cancel_status": "uncanceled",
    "end_payment_date": "<今日 YYYY-MM-DD>",
    "limit": 100
  }
}
```

### Step 3: 入金期限間近（7日以内・未入金）

```
freee_api_get {
  "service": "invoice",
  "path": "/invoices",
  "query": {
    "company_id": <company_id>,
    "payment_status": "unsettled",
    "cancel_status": "uncanceled",
    "start_payment_date": "<今日+1日 YYYY-MM-DD>",
    "end_payment_date": "<今日+7日 YYYY-MM-DD>",
    "limit": 100
  }
}
```

Step 2 と期間が重複しないよう `start_payment_date` は今日の翌日にする。

### Step 4: 仕訳（取引）未登録

請求書が取引として記帳されていない = 会計帳簿に反映されていない状態。

```
freee_api_get {
  "service": "invoice",
  "path": "/invoices",
  "query": {
    "company_id": <company_id>,
    "deal_status": "unregistered",
    "cancel_status": "uncanceled",
    "limit": 100
  }
}
```

### ページング

各カテゴリのレスポンス件数が `limit` (100) に達した場合、`offset` を増やして追加取得する
（未取得分がある可能性）。

## 結果の報告形式

```
## 請求書ステータスチェック結果 (事業所: <会社名 or company_id>, 実行日: YYYY-MM-DD)

| チェック項目 | 該当件数 | 対応 |
|---|---|---|
| 送付漏れ（未送付） | N件 | 送付が必要 |
| 入金期限超過（未入金） | N件 | 督促が必要 |
| 入金期限間近（7日以内・未入金） | N件 | フォロー推奨 |
| 仕訳未登録 | N件 | 記帳が必要 |

### 送付漏れ
- [請求書番号] 取引先名 | 請求日 YYYY-MM-DD | ¥XX,XXX | report_url

### 入金期限超過
- [請求書番号] 取引先名 | 入金期日 YYYY-MM-DD（X日超過） | ¥XX,XXX | report_url

### 入金期限間近
- [請求書番号] 取引先名 | 入金期日 YYYY-MM-DD（あとX日） | ¥XX,XXX | report_url

### 仕訳未登録
- [請求書番号] 取引先名 | 請求日 YYYY-MM-DD | ¥XX,XXX | report_url
```

該当が1件もないカテゴリは表の件数を「0件」とし、詳細見出しごと省略してよい。
全カテゴリ0件の場合は「発行済み請求書はすべて正常な状態です」とだけ報告する。

## 注意

- **`service: "invoice"` を必ず使う** — `service: "accounting"` の `/api/1/invoices` は旧APIで
  現在の請求書データと一致しない場合がある
- `cancel_status: "canceled"`（取消済み）の請求書はどのカテゴリにも含めない
- `payment_status` の `canceled`（決済キャンセル）は `cancel_status` とは別概念。決済ステータス
  側の `canceled` は入金取消のことなので、これも通常の督促対象からは除外して考える
- 入金期限判定は freee 側の `payment_date`（振込/振替/カード支払期日）を基準にする。実際の
  入金消込はfreee Web画面またはfreee請求書サービス側で行われ、本スキルはAPI越しの状態確認に
  留まる（消込自体は行わない）
- 件数が多い場合は各カテゴリ0件確認だけ先に報告し、詳細は必要な分だけ取得してもよい
