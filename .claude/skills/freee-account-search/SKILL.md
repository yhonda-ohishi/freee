---
name: freee-account-search
description: This skill should be used when searching for freee account items (勘定科目), looking up account item IDs, finding tax codes for freee transactions, or when the freee account_items API response exceeds token limits. Trigger phrases include "勘定科目を探す", "科目ID", "account_items", "勘定科目検索".
---

# freee 勘定科目検索

freee会計の勘定科目（account_items）APIは198件以上の科目を返し、レスポンスが156K文字を超えてトークン制限に引っかかる。このスキルはその問題を解決し、効率的に科目を検索する。

## 検索手順

### Step 1: スクリプトで検索

`scripts/search_account_items.py` を使って科目を検索する。

```bash
PYTHONIOENCODING=utf-8 python "c:/freee/.claude/skills/freee-account-search/scripts/search_account_items.py" "<keyword>"
```

例:
```bash
PYTHONIOENCODING=utf-8 python "c:/freee/.claude/skills/freee-account-search/scripts/search_account_items.py" "租税"
```

company_idは `.env` の `FREEE_COMPANY_ID` から自動取得。

出力はJSON形式で、id, name, tax_code, shortcut, account_categoryなどを含む。

### Step 2: キャッシュがない場合

初回実行時、スクリプトは過去のfreee API tool-resultsファイルからデータを解析してキャッシュを作成する。tool-resultsファイルもない場合は、先にAPIを呼ぶ:

```
freee_api_get { "service": "accounting", "path": "/api/1/account_items", "query": { "company_id": <company_id> } }
```

APIを呼んだ後、再度スクリプトを実行すればキャッシュが生成される。

### Step 3: キャッシュの更新

科目が追加・変更された場合、キャッシュを削除して再生成する:

```bash
rm ~/.claude/projects/c--freee/freee-cache/account_items_<company_id>.json
```

## 検索のコツ

- 日本語名で検索: `"租税"`, `"旅費"`, `"消耗品"`
- ローマ字ショートカットで検索: `"SOZEI"`, `"RYOHI"`
- カテゴリで検索: `"販売管理費"`, `"流動資産"`
- 部分一致で検索される

## 取引登録への活用

検索結果のidとtax_codeを使って取引を登録する:

```
freee_api_post {
  "service": "accounting",
  "path": "/api/1/deals",
  "body": {
    "company_id": <company_id>,
    "issue_date": "YYYY-MM-DD",
    "type": "expense",
    "details": [{
      "account_item_id": <検索結果のid>,
      "tax_code": <検索結果のtax_code>,
      "amount": <金額>,
      "description": "<摘要>"
    }]
  }
}
```
