---
name: freee-unmatched-check
description: freeeの銀行口座・クレジットカード・現金口座の未仕訳（消込待ち）明細を確認するスキル。「未仕訳」「消込待ち」「明細チェック」「unmatched」「自動で経理に残ってる明細」などのフレーズで起動。
---

# freee 未仕訳明細チェック

freee会計に登録された口座の未処理明細（消込待ち）を一括確認する。

## 手順

### Step 1: 事業所IDを取得

```
freee_get_current_company
```

### Step 2: 全口座を取得

銀行口座・クレジットカード・現金口座をそれぞれ取得:

```
freee_api_get { "service": "accounting", "path": "/api/1/walletables", "query": { "company_id": <company_id> } }
```

### Step 3: 各口座の消込待ち明細を確認

口座ごとに status=1（消込待ち）の明細を取得:

```
freee_api_get {
  "service": "accounting",
  "path": "/api/1/wallet_txns",
  "query": {
    "company_id": <company_id>,
    "walletable_type": "<type>",
    "walletable_id": <id>,
    "status": "1"
  }
}
```

typeは `bank_account`, `credit_card`, `wallet` のいずれか。

### Step 4: 結果をまとめて報告

以下の形式で報告する:

```
## 未仕訳明細チェック結果

| 口座 | 未仕訳件数 | 合計金額 |
|------|-----------|---------|
| ○○銀行 | N件 | ¥XX,XXX |
| ...  | ...       | ...     |

### 明細一覧
- [口座名] YYYY-MM-DD | 入金/出金 | ¥XX,XXX | 摘要
```

未仕訳がない場合は「全口座の明細は消込済みです」と報告。

### 注意

- freee APIには明細の消込機能がないため、未仕訳明細の処理はfreee Web画面「自動で経理」で行うようユーザーに案内する
- 明細が多い場合はlimit=100を指定し、件数だけ先に報告する
