# Evidence Matrix — 證據矩陣與證據項契約模板
# 使用說明：研究者依第 2 節產出 `00_research/evidence_items.json`；`00_research/evidence_matrix.md` 依第 4 節版式由執行層（Bridge）確定性渲染（無執行層時由研究者以同一版式手寫）

**文件類型**: Evidence Matrix（`evidence_items.json` 契約＋`evidence_matrix.md` 版式）
**契約版本**: `schema_rev` = 1
**存放位置**: `<研究工作區>/00_research/evidence_items.json`（研究者寫）、`<研究工作區>/00_research/evidence_matrix.md`（執行層渲染）
**作者分工**: `evidence_items.json`＝`research-analyst`；`evidence_matrix.md`＝執行層渲染（檔案可由 JSON 與抓取紀錄重生）；PRD 只引用矩陣，不改矩陣
**下游**: `spec-engineer`（以 `[E-NNN]` 引用）、審查四角（核對引用與授權）、`spec-frozen --doc`（Gate 0 凍結集合含 `evidence_matrix.md`）
**立案**: 掌舵者 2026-11-02 ResearchSOPtoPRD；主控裁決 D-21

> 設計原則：長表格由 LLM 直寫容易漏欄，所以 agent 只寫**可機驗的 JSON**，Markdown 版式由程式渲染；
> JSON 能被 schema 驗證、渲染後的檔案摘要穩定，Gate 0 才有可凍結的內容。

---

## 1. 檔案、作者與流向

| 檔案（相對研究工作區） | 作者 | 流向 | 說明 |
|----------------------|------|------|------|
| `00_research/issue_scope.json` | 執行層（人手流程為人） | 輸入 | 契約見 `ISSUE-SCOPE-TEMPLATE.md`；研究者唯讀 |
| `00_research/raw/` | 執行層（預取）／研究者（Web 層節錄） | 輸入／輸出 | 抓回的第三方原文或節錄，內容定址；**只存工作區、不入版控與備份**（版權與再散布風險），證據靠 URL／DOI／commit 錨定，不靠保存原文 |
| `00_research/evidence_items.json` | `research-analyst` | 檔→驗證→入庫 | 本檔第 2 節契約；驗證不過即該步失敗重試 |
| `00_research/evidence_matrix.md` | 執行層渲染 | 庫→渲染→檔 | 第 4 節版式；供人讀與 Gate 0 凍結 |
| `00_research/notes/E-NNN.md` | `research-analyst`（選用） | 輸出 | 欄位超過 600 字元時的附註；只是閱讀輔助，**沒有證據效力**，欄位本身仍須獨立成句 |

---

## 2. `evidence_items.json` 契約

### 2.1 有效範例（虛構來源，勿引用）

> 來源網域一律用保留網域 `example.org`、DOI 前綴用 `10.0000`、commit 用 `0123456789abcdef…`：讓任何人一眼看出這是範例，避免範例被誤當成真實證據。
> 範例同時滿足 2.3 的全部規則（機器對拍的有效夾具；區塊前一行的 `r2p:contract` 註解是定位標記，勿刪）。

<!-- r2p:contract=evidence_items -->
```json
{
  "schema_rev": 1,
  "issue_scope_sha256": "0000000000000000000000000000000000000000000000000000000000000001",
  "scope_rev": 1,
  "search_log": [
    {"id": "Q-001", "layer": "INDUSTRY", "tool": "WebSearch", "query": "example render engine production blog", "at": "2026-11-02T10:05:00+08:00", "result_urls": ["https://example.org/blog/example-post"]},
    {"id": "Q-002", "layer": "COMMUNITY", "tool": "WebSearch", "query": "example render engine pitfalls forum", "at": "2026-11-02T10:07:00+08:00", "result_urls": ["https://example.org/forum/thread-123"]},
    {"id": "Q-003", "layer": "ACADEMIC", "tool": "WebSearch", "query": "example render engine survey", "at": "2026-11-02T10:09:00+08:00", "result_urls": ["https://example.org/papers/example-survey", "https://example.org/papers/example-limits"]},
    {"id": "Q-004", "layer": "ACADEMIC", "tool": "WebSearch", "query": "example render engine limitations fails negative result", "at": "2026-11-02T10:12:00+08:00", "result_urls": ["https://example.org/papers/example-limits"]},
    {"id": "Q-005", "layer": "OSS", "tool": "WebSearch", "query": "example-lib license incompatibility known issue", "at": "2026-11-02T10:15:00+08:00", "result_urls": []},
    {"id": "Q-006", "layer": "INDUSTRY", "tool": "WebSearch", "query": "example post claims does not generalize", "at": "2026-11-02T10:18:00+08:00", "result_urls": ["https://example.org/papers/example-limits"]}
  ],
  "sources": [
    {"source_no": "S-001", "layer": "ACADEMIC", "tier": "T1", "verification": "V3", "anchor_kind": "DOI", "url": "https://example.org/papers/example-001", "doi": "10.0000/EXAMPLE.001", "git_commit": null, "title": "Example Paper A", "authors_org": "Example Lab", "published_at": "2025-03-01", "source_type": "PAPER", "license_spdx": null, "license_note": "論文頁面未載授權條款", "clue_only": false, "fetch_refs": ["F-0001"]},
    {"source_no": "S-002", "layer": "OSS", "tier": "T1", "verification": "V3", "anchor_kind": "COMMIT", "url": "https://example.org/repos/example-lib", "doi": null, "git_commit": "0123456789abcdef0123456789abcdef01234567", "title": "example-lib", "authors_org": "Example Org", "published_at": "2025-09-12", "source_type": "REPO", "license_spdx": "Apache-2.0", "license_note": "取自 repo 授權檔", "clue_only": false, "fetch_refs": ["F-0002"]},
    {"source_no": "S-003", "layer": "INDUSTRY", "tier": "T1", "verification": "V2", "anchor_kind": "URL", "url": "https://example.org/blog/example-post", "doi": null, "git_commit": null, "title": "Example Engineering Post", "authors_org": "Example Inc.", "published_at": "2025-06-30", "source_type": "ENG_BLOG", "license_spdx": null, "license_note": "部落格頁面未載授權條款", "clue_only": false, "fetch_refs": []},
    {"source_no": "S-004", "layer": "COMMUNITY", "tier": "T3", "verification": "V1", "anchor_kind": "URL", "url": "https://example.org/forum/thread-123", "doi": null, "git_commit": null, "title": "Forum thread about example engine", "authors_org": "未見", "published_at": null, "source_type": "FORUM", "license_spdx": null, "license_note": "未見", "clue_only": true, "fetch_refs": []},
    {"source_no": "S-005", "layer": "ACADEMIC", "tier": "T2", "verification": "V2", "anchor_kind": "URL", "url": "https://example.org/papers/example-survey", "doi": null, "git_commit": null, "title": "Example Survey of Render Engines", "authors_org": "Example Survey Group", "published_at": "2025-11-20", "source_type": "PREPRINT", "license_spdx": null, "license_note": "預印本頁面未載授權條款", "clue_only": false, "fetch_refs": []},
    {"source_no": "S-006", "layer": "ACADEMIC", "tier": "T1", "verification": "V2", "anchor_kind": "URL", "url": "https://example.org/papers/example-limits", "doi": null, "git_commit": null, "title": "Limits of Template Caching", "authors_org": "Example Lab B", "published_at": "2025-08-15", "source_type": "PREPRINT", "license_spdx": null, "license_note": "預印本頁面未載授權條款", "clue_only": false, "fetch_refs": []}
  ],
  "items": [
    {"evidence_no": "E-001", "source_no": "S-001", "scope_rev": 1, "candidate": "候選方案甲",
     "claim": "候選方案甲在固定樣板的批次渲染中吞吐量明顯高於基準實作",
     "f1": "以預先編譯的樣板快取取代逐頁解析；由渲染器觸發，以基準測試驗證",
     "f2": "基準 X、單機 8 核、1000 頁文件：1200 頁每分鐘，對照組 450 頁每分鐘",
     "f3": "作者自述僅在樣板固定時成立，樣板每頁不同時優勢消失",
     "f4": [],
     "f5": {"technical": {"grade": "A", "reason": "可由 Python 直接呼叫，無額外執行環境"}, "license": {"grade": "M", "reason": "論文未載授權，需另查實作授權"}, "maintenance": {"grade": "M", "reason": "作者實作的維護狀態未見"}, "performance": {"grade": "A", "reason": "吞吐量優勢直接對應效能邊界需求"}, "security": {"grade": "M", "reason": "未見資安評估，需另行檢核"}, "cost": {"grade": "A", "reason": "無額外授權費用"}},
     "f6": "單一基準、單一硬體；未見獨立重現",
     "f7": "V3", "strength": "STRONG"},
    {"evidence_no": "E-002", "source_no": "S-002", "scope_rev": 1, "candidate": "候選方案乙",
     "claim": "候選方案乙以 Apache-2.0 釋出且近一年有持續提交",
     "f1": "開源函式庫，授權與提交紀錄取自 repo 頁面與授權檔",
     "f2": "授權識別碼 Apache-2.0；最近提交日期 2025-09-12",
     "f3": "未見",
     "f4": ["DEP"],
     "f5": {"technical": {"grade": "A", "reason": "提供 Python 綁定"}, "license": {"grade": "A", "reason": "Apache-2.0 與目標授權限制相容"}, "maintenance": {"grade": "M", "reason": "維護者人數少，需評估停更風險"}, "performance": {"grade": "M", "reason": "未見效能數據，需自行量測"}, "security": {"grade": "M", "reason": "未見安全公告紀錄，需掃描相依"}, "cost": {"grade": "A", "reason": "無授權費用"}},
     "f6": "只讀 repo 頁面與授權檔；未讀原始碼",
     "f7": "V3", "strength": "MEDIUM"},
    {"evidence_no": "E-003", "source_no": "S-003", "scope_rev": 1, "candidate": "候選方案甲",
     "claim": "業界團隊在生產環境採用候選方案甲並回報延遲下降",
     "f1": "工程部落格描述以樣板快取降低渲染延遲",
     "f2": "文中自述 P95 延遲由 900 ms 降到 300 ms，未列基準與對照組細節",
     "f3": "文中未說明量測環境與樣本數",
     "f4": ["SELF"],
     "f5": {"technical": {"grade": "A", "reason": "做法與候選方案甲一致"}, "license": {"grade": "M", "reason": "部落格未載授權，需另查"}, "maintenance": {"grade": "M", "reason": "未見後續維護說明"}, "performance": {"grade": "M", "reason": "自述數字未見獨立重現"}, "security": {"grade": "M", "reason": "未見資安討論"}, "cost": {"grade": "A", "reason": "無額外授權費用"}},
     "f6": "官方部落格自述成果；只讀轉述，未開原文逐字核對",
     "f7": "V2", "strength": "MEDIUM"},
    {"evidence_no": "E-004", "source_no": "S-005", "scope_rev": 1, "candidate": null,
     "claim": "渲染方案的選型文獻多數把樣板是否固定列為首要分流條件",
     "f1": "綜述整理既有渲染方案並以樣板固定程度分類",
     "f2": "綜述納入 24 個方案，其中 17 個以樣板固定為前提",
     "f3": "綜述自述分類依作者判斷，未做獨立標註一致性檢查",
     "f4": ["IMM"],
     "f5": {"technical": {"grade": "M", "reason": "分類可轉為本案的選型條件"}, "license": {"grade": "N", "reason": "綜述不涉及授權比較"}, "maintenance": {"grade": "N", "reason": "綜述不涉及維護狀態"}, "performance": {"grade": "M", "reason": "僅質性描述，需自行量測"}, "security": {"grade": "N", "reason": "綜述不涉及資安"}, "cost": {"grade": "N", "reason": "綜述不涉及成本"}},
     "f6": "預印本、頁面未顯示 venue；只讀摘要頁",
     "f7": "V2", "strength": "WEAK"}
  ],
  "counter_evidence": [
    {"evidence_no": "E-001", "search_id": "Q-004", "conclusion": "LIMIT", "source_no": "S-006", "note": "S-006 指出樣板每頁不同時優勢消失；已併入 E-001 的 f3"},
    {"evidence_no": "E-002", "search_id": "Q-005", "conclusion": "NOT_FOUND", "source_no": null, "note": "以反證字串搜尋無相關結果；不代表不存在"},
    {"evidence_no": "E-003", "search_id": "Q-006", "conclusion": "IRRELEVANT", "source_no": "S-006", "note": "S-006 討論離線批次，與本案的生產情境無關"},
    {"evidence_no": "E-004", "search_id": null, "conclusion": "NOT_SEARCHED", "source_no": null, "note": "本輪未做專門反證搜尋"}
  ],
  "honest_bounds": {
    "not_found": [
      {"query": "example-lib license incompatibility known issue", "date": "2026-11-02", "result": "無相關結果"}
    ],
    "summary_only": ["S-003", "S-004", "S-005", "S-006"],
    "not_read_fully": ["S-001", "S-002", "S-003", "S-004", "S-005", "S-006"]
  }
}
```

### 2.2 欄位定義與列舉

**頂層**

| 欄位 | 型別 | 規則 |
|------|------|------|
| `schema_rev` | integer | 固定 `1` |
| `issue_scope_sha256` | string | 64 位小寫 hex；**由任務書提供，原樣抄寫**（研究者沒有雜湊工具，不得自行計算）；演算法＝換行正規化後 UTF-8 的 SHA-256（與 `spec-frozen --digest` 同，不含 `sha256:` 前綴） |
| `scope_rev` | integer ≥1 | 本次檢索所依的 `issue_scope.json` 的 `scope_rev` |
| `search_log` | object[] | 研究者**自己發出**的 WebSearch／WebFetch 紀錄；執行層預取的來源以 `fetch_refs` 為出處，不在此重列 |
| `sources` | object[] | 來源實體（含 T3 線索） |
| `items` | object[] | 證據項（只含 T1／T2 來源） |
| `counter_evidence` | object[] | 每個證據項恰一筆反證結論（研究方法 S5） |
| `honest_bounds` | object | 誠實劃界三桶（研究方法 S8） |

**`search_log[]`**：`id`（`Q-NNN`）、`layer`、`tool`（`WebSearch`｜`WebFetch`）、`query`（原樣字串；`WebFetch` 時為被開啟的 URL）、`at`（ISO-8601 帶 offset）、`result_urls`（https 字串陣列，可空）。

**`sources[]`**：`source_no`（`S-NNN`）、`layer`、`tier`、`verification`、`anchor_kind`、`url`、`doi`（`anchor_kind=DOI` 必填，否則 `null`）、`git_commit`（`anchor_kind=COMMIT` 必填 40 位小寫 hex，否則 `null`）、`title`、`authors_org`（缺寫 `未見`）、`published_at`（`YYYY-MM-DD` 或 `null`；`null` 於渲染時顯示「未見」）、`source_type`、`license_spdx`（SPDX 識別碼；**開源 repo 必填**，查不到寫 `UNKNOWN`；其他來源可 `null`；`null` 與 `UNKNOWN` 渲染時皆顯示「未見」）、`license_note`、`clue_only`、`fetch_refs`（執行層抓取紀錄 id 陣列 `F-NNNN`，由執行層提供，研究者原樣抄寫；Web 層來源為空陣列）。

**`items[]`**：`evidence_no`（`E-NNN`）、`source_no`、`scope_rev`（該列首次出現時的 scope_rev，之後不改）、`candidate`（候選技術名或 `null`，供「技術優缺點矩陣」分組）、`claim`（PRD 引用的論點，一句話）、`f1`～`f3`、`f4`（風險標籤陣列，取自 3.2，可空）、`f5`（適用性物件，鍵＝`issue_scope.applicability_axes` 對映的軸 id）、`f6`、`f7`（查證層級）、`strength`。

**`counter_evidence[]`**：`evidence_no`、`search_id`（反證搜尋的 `Q-NNN` 或 `null`）、`conclusion`、`source_no`（反證來源或 `null`）、`note`。

**`honest_bounds`**：`not_found`（`{query, date, result}` 陣列）、`summary_only`（來源編號陣列）、`not_read_fully`（來源編號陣列）。

**列舉值**

| 欄位 | 值 |
|------|----|
| `layer` | `ACADEMIC`｜`INDUSTRY`｜`OSS`｜`COMMUNITY` |
| `tier` | `T1` 一手（arXiv 或會議頁、官方文件與官方工程部落格、官方 repo）｜`T2` 二手（survey、基準報告；畫地圖用，不單獨支撐論點）｜`T3` 線索（個人貼文、論壇、社群討論；只當搜尋線索） |
| `verification` | `V1` 只見搜尋結果的標題與 URL（未開啟）｜`V2` 已開啟頁面（WebFetch 轉述，或執行層抓回原文但尚未針對章節專項抽取）｜`V3` 原文位元組已落地，且針對方法／限制／安全章節做過專項抽取。`V0`（只憑記憶）**不得列入**。WebFetch 的轉述最高 `V2` |
| `anchor_kind` | `URL`｜`DOI`｜`COMMIT` |
| `source_type` | `PAPER`｜`PREPRINT`｜`ENG_BLOG`｜`WHITEPAPER`｜`PATENT`｜`REPO`｜`ISSUE_PR`｜`FORUM`｜`DOC`｜`OTHER` |
| `grade`（`f5`） | `A` 直接適用｜`M` 需改造｜`N` 不適用（皆附一句理由） |
| `strength` | `STRONG`｜`MEDIUM`｜`WEAK`｜`CANDIDATE`（函式見 3.3） |
| `conclusion`（反證） | `WEAKEN` 削弱｜`LIMIT` 限定（補適用範圍條件）｜`IRRELEVANT` 無關（寫理由）｜`NOT_FOUND` 未找到反證（附搜尋字串與日期）｜`NOT_SEARCHED` 未做專門反證搜尋 |

### 2.3 驗證規則（執行層以確定性程式檢查；不過即該步失敗並重試；人手流程由研究者逐條自檢）

1. **結構**：欄位齊全、型別正確、無多餘欄位；UTF-8、LF、無 BOM。
2. **編號**：`Q-`、`S-`、`E-` 各自 ≥3 位數字（上限 4 位）、不重複、不重用。
3. **錨定**：每個 `sources[].url` 必須是 `https://`；`anchor_kind=DOI` 時 `doi` 非空；`COMMIT` 時 `git_commit` 為 40 位小寫 hex。
4. **URL 出處**：每個 `sources[].url` 必須出現在某筆 `search_log[*].result_urls`，或該來源的 `fetch_refs` 非空。憑記憶的來源一律不列；憑記憶猜出的網址若要驗證，先以 `WebFetch` 開啟並在 `search_log` 記一筆（`query`＝該 URL），頁面內容核對到標題才算數，核對不上就移除。
5. **分級**：`tier=T3` ⇒ `clue_only=true`，且不得被任何 `items[].source_no` 引用；`tier` 為 `T1`／`T2` ⇒ `clue_only=false`；`verification` 只能是 `V1`～`V3`。
6. **V3 條件**：`verification=V3` ⇒ `fetch_refs` 非空。
7. **證據項綁定**：`items[].source_no` 必須存在於 `sources` 且非 `clue_only`；`f7` 不得高於其來源的 `verification`（V1＜V2＜V3）。
8. **欄位完整**：`claim`、`f1`、`f2`、`f3`、`f6` 非空字串，缺資訊寫「未見」，不留空；`f4` 的值必須在 3.2 登錄表內；`f5` 的鍵集合必須恰等於 `issue_scope.applicability_axes` 對映的軸 id 集合，每軸 `{grade, reason}`，`reason` 非空。
9. **儲存格紀律**：所有文字欄位不得含管線字元 `|` 與換行；每欄 ≤600 字元，超長改以 `見 notes/E-NNN.md` 指向附註檔。
10. **數字登錄**：`f2` 的數字原樣抄自來源（含單位、基準、對照組），不四捨五入、不換算；兩個數字要比較時必須出自同一來源同一基準；搜尋工具轉述的數字只能放 V1 並註明「須核對」。執行層對 V2／V3 的列做字面或數值正規化比對，比對不到的標 `UNANCHORED`（**由執行層計算並標示，研究者不寫**）。
11. **反證**：每個證據項恰有一筆 `counter_evidence`；`NOT_FOUND` 必附 `search_id`，且該搜尋的 `query` 必須同時出現在 `honest_bounds.not_found`；`NOT_SEARCHED` 不得附 `search_id`；`WEAKEN`／`LIMIT`／`IRRELEVANT` 必附 `source_no`。
12. **強度**：`strength` 必須等於 3.3 函式值，不等＝JSON 無效。
13. **無孤兒來源**：每個非 `clue_only` 的來源至少被一個證據項或一筆反證引用。
14. **誠實劃界**：`summary_only` 必須包含所有 `V1`／`V2` 來源；`not_read_fully` 必須包含所有非 `V3` 來源（`V3` 只代表讀過關鍵章節，通讀全文者另行在 `f6` 宣告）。
15. **增補只增不改**：已有前一版 `evidence_items.json` 時，新版必須逐位元保留其全部 `sources`、`items`、`search_log`，編號延續；只准新增。
16. **雜湊與抓取 id 原樣抄寫**：`issue_scope_sha256`、`fetch_refs` 一律由任務書或執行層提供，不得自行編造。

---

## 3. 登錄表

### 3.1 適用性軸登錄表（`f5` 的鍵與 `applicability_axes` 的標籤）

<!-- r2p:contract=axis_registry -->
```json
{
  "technical": "技術可行",
  "license": "授權相容",
  "maintenance": "維護風險",
  "performance": "效能邊界",
  "security": "資安",
  "cost": "成本"
}
```

`f5` 是研究者「對本專案」的判斷，必須與 `f2`（來源說了什麼）分開寫，**不得把判斷寫成來源所說**。軸集合封閉為六個；`issue_scope.applicability_axes` 只能取其子集（預設全六軸）。

### 3.2 風險標籤登錄表（`f4`）

<!-- r2p:contract=risk_tag_registry -->
```json
{
  "LOCK": "供應商或生態鎖定",
  "IMM": "不成熟（預印本、單一作者、無 venue、進行中）",
  "SELF": "自述成果、未見獨立重現",
  "SCOPE": "外推風險（單一基準、小模型、構造資料）",
  "DEP": "相依與維護風險（維護者少、停更、重大 issue 長期未決）",
  "LIC": "授權風險（強 copyleft、授權未見、限制商用）",
  "SEC": "安全風險（已知漏洞、供應鏈）",
  "COMP": "合規或資料保護風險"
}
```

表外的風險寫進 `f3` 或 `f6`，**不自創標籤**。

### 3.3 `strength` 函式

先依來源分級與查證層級取基準，再依反證結論與風險標籤調整：

| 步驟 | 規則 |
|------|------|
| 基準 | `f7=V1` → `CANDIDATE`；`tier=T1` 且 `f7=V3` → `STRONG`；（`tier=T1` 且 `f7=V2`）或（`tier=T2` 且 `f7=V3`）→ `MEDIUM`；`tier=T2` 且 `f7=V2` → `WEAK` |
| 反證 `WEAKEN` | 降一級（`STRONG`→`MEDIUM`→`WEAK`→`CANDIDATE`；`CANDIDATE` 不再降） |
| 反證 `NOT_FOUND` 或 `NOT_SEARCHED` | 上限 `MEDIUM`（`STRONG` 降為 `MEDIUM`，其餘不變）：沒找到反證不等於已證無反例 |
| 反證 `LIMIT`／`IRRELEVANT` | 不變（`LIMIT` 須已把限定條件寫進 `f3` 或 `f6`） |
| 封頂 | `f4` 含 `IMM`、`SELF` 或 `SCOPE` 其一 → 上限 `MEDIUM` |

`CANDIDATE` 的列只能當候選線索，**PRD 不得引用**。範例四列的推導：E-001＝T1／V3、反證 `LIMIT`、無封頂標籤 → `STRONG`；E-002＝T1／V3、`NOT_FOUND` → 上限 `MEDIUM`；E-003＝T1／V2、`SELF` → `MEDIUM`；E-004＝T2／V2 → `WEAK`。

---

## 4. `evidence_matrix.md` 渲染版式（執行層確定性渲染；人手流程照同一版式手寫）

### 4.1 結構

1. **檔頭註解**：第 1 行 `<!-- r2p:evidence_matrix schema_rev=1 version=N -->`（N＝矩陣版本，只增不改）。
2. **標題與兩行統計**：`# 證據矩陣（version N；scope_rev M）`；其下兩行引言：`授權待查：<n> 筆`（授權條款為 GPL／AGPL 系或「未見」的證據列數，資安審查的輸入）、`UNANCHORED：<n> 筆`（F2 數字在抓取原文中比對不到者）。
3. **A 來源表**（研究方法 S2）。
4. **B 證據表**（研究方法 S3 七欄；欄位與順序固定如下）。
5. **C 反證**（研究方法 S5）。
6. **D 線索區**（T3；只當搜尋線索，不得當證據）。
7. **E 誠實劃界**（研究方法 S8 三桶）。

### 4.2 A 來源表欄位（固定順序）

`S-NNN`｜`標題`｜`作者機構`｜`年份`｜`URL 或 DOI`｜`類型`｜`查證層級`｜`授權條款`｜`層`｜`來源分級`｜`被引證據`

`URL 或 DOI` 儲存 `url`；`anchor_kind=DOI` 時追加 `；doi:<doi>`，`COMMIT` 時追加 `；commit:<前 12 碼>`。`被引證據`＝引用該來源的 `E-NNN`（含反證引用，以 `（反證）` 標示）；T3 來源不進本表，改列 D 區。

### 4.3 B 證據表欄位（固定順序；共 17 欄，與 Console PRD §5.1.3 一致）

| # | 欄位名 | 取自 JSON | 渲染規則 |
|---|--------|-----------|----------|
| 1 | `ID` | `items[].evidence_no` | `E-NNN`；PRD 以 `[E-NNN]` 引用 |
| 2 | `層` | 來源的 `layer` | `ACADEMIC`→`academic`、`INDUSTRY`→`industry`、`OSS`→`oss`、`COMMUNITY`→`community`（小寫，與議題檔 `layers` 的鍵同名） |
| 3 | `候選技術` | `candidate` | `null` 顯示 `—` |
| 4 | `標題` | 來源 `title` | 缺＝`未見` |
| 5 | `出處機構或作者` | 來源 `authors_org` | 缺＝`未見` |
| 6 | `年份` | 來源 `published_at` 的前 4 碼 | `null` 顯示 `未見` |
| 7 | `定位符` | 來源 `url`＋（DOI／commit） | URL、DOI、git commit 三者至少一個，皆空＝拒收 |
| 8 | `來源分級` | 來源 `tier` | `T1`／`T2`（T3 不進本表） |
| 9 | `查證層級` | `f7` | `V1`／`V2`／`V3`；PRD 只能引 ≥V2 的列 |
| 10 | `授權條款` | 來源 `license_spdx` | `null` 或 `UNKNOWN` 顯示 `未見` |
| 11 | `F1 機制` | `f1` | 原文 |
| 12 | `F2 證據` | `f2` | 原文；數字原樣 |
| 13 | `F3 失敗與批評` | `f3` | 原文 |
| 14 | `F4 風險標籤` | `f4` | 以 `、` 連接；空陣列顯示 `無` |
| 15 | `F5 適用性` | `f5` | `<軸標籤>:<A｜M｜N>（<reason>）`，各軸以 `；` 連接，順序依 `issue_scope.applicability_axes` |
| 16 | `F6 限制` | `f6` | 原文 |
| 17 | `抓取紀錄` | 來源 `fetch_refs` 與抓取紀錄的內容雜湊 | `F-NNNN@<sha 前 12 碼>`，多筆以 `、` 連接；無抓取紀錄顯示 `無（宣告型）`；F2 數字錨定失敗者在末尾加 ` ⚠UNANCHORED` |

儲存格規則：**不得含管線字元 `|`**（含者寫入被拒）；每格 ≤600 字元；`缺＝未見` 不留空白（`候選技術`、`F4` 例外，分別顯示 `—`、`無`）。`UNANCHORED` 與抓取紀錄欄由執行層填，**研究者不寫**。

### 4.4 C 反證、D 線索區、E 誠實劃界

- **C 反證表**：`證據`｜`反證搜尋`｜`結論`｜`反證來源`｜`說明`（`NOT_SEARCHED` 的搜尋欄顯示 `—`）。
- **D 線索區表**：`S-NNN`｜`標題`｜`URL`｜`層`｜`用途`，用途固定寫「只作搜尋線索，不得當證據」。
- **E 誠實劃界**：三個小節，不得合併——①沒查到（`not_found`：搜尋字串＋日期＋結果）；②只讀摘要或搜尋結果（`summary_only`，逐篇列出）；③沒讀全文（`not_read_fully`）。小節後固定三句：「WebFetch 是小模型依提問轉述，所有 V2 的數字與陳述都是轉述，PRD 引用前須核對原頁面。」「來源表以外的文獻一律視為『未納入』，不是『不存在』。」「搜尋引擎找得到的不等於全集，本矩陣不聲稱窮盡。」

### 4.5 渲染範例（由 2.1 的 JSON 渲染；欄寬已省略，僅示範版式）

````markdown
<!-- r2p:evidence_matrix schema_rev=1 version=1 -->
# 證據矩陣（version 1；scope_rev 1）

> 授權待查：3 筆（授權條款為 GPL／AGPL 系或「未見」；範例中 E-001、E-003、E-004）
> UNANCHORED：0 筆

## A 來源表

| S-NNN | 標題 | 作者機構 | 年份 | URL 或 DOI | 類型 | 查證層級 | 授權條款 | 層 | 來源分級 | 被引證據 |
|-------|------|----------|------|-----------|------|----------|----------|----|----------|----------|
| S-001 | Example Paper A | Example Lab | 2025 | https://example.org/papers/example-001；doi:10.0000/EXAMPLE.001 | PAPER | V3 | 未見 | academic | T1 | E-001 |
| S-002 | example-lib | Example Org | 2025 | https://example.org/repos/example-lib；commit:0123456789ab | REPO | V3 | Apache-2.0 | oss | T1 | E-002 |

## B 證據表

| ID | 層 | 候選技術 | 標題 | 出處機構或作者 | 年份 | 定位符 | 來源分級 | 查證層級 | 授權條款 | F1 機制 | F2 證據 | F3 失敗與批評 | F4 風險標籤 | F5 適用性 | F6 限制 | 抓取紀錄 |
|----|----|----------|------|----------------|------|--------|----------|----------|----------|---------|---------|---------------|-------------|-----------|---------|----------|
| E-001 | academic | 候選方案甲 | Example Paper A | Example Lab | 2025 | https://example.org/papers/example-001；doi:10.0000/EXAMPLE.001 | T1 | V3 | 未見 | 以預先編譯的樣板快取取代逐頁解析；由渲染器觸發，以基準測試驗證 | 基準 X、單機 8 核、1000 頁文件：1200 頁每分鐘，對照組 450 頁每分鐘 | 作者自述僅在樣板固定時成立，樣板每頁不同時優勢消失 | 無 | 技術可行:A（可由 Python 直接呼叫，無額外執行環境）；授權相容:M（論文未載授權，需另查實作授權）；維護風險:M（作者實作的維護狀態未見）；效能邊界:A（吞吐量優勢直接對應效能邊界需求）；資安:M（未見資安評估，需另行檢核）；成本:A（無額外授權費用） | 單一基準、單一硬體；未見獨立重現 | F-0001@3fa9c1d20b7e |
````

> 渲染範例中的雜湊前 12 碼為示意值。`E-002`～`E-004` 的列同形，不逐列重複。

---

## 5. 自檢清單（研究者交卷前逐條勾；QA 與審查四角抽查時同用）

- [ ] 第 2.3 節 16 條規則逐條自檢過；驗證器（有執行層時）rc 0
- [ ] 每個來源的 URL 都有出處（搜尋結果或抓取紀錄），沒有憑記憶的來源
- [ ] T3 只在線索區，沒有任何證據項引用它；V0 沒有出現
- [ ] 每個數字原樣抄自來源；沒有跨來源或跨基準的比較
- [ ] `f5` 的判斷與 `f2` 的來源陳述分開寫；每軸有一句理由
- [ ] 每個證據項有反證結論；`NOT_FOUND` 的搜尋字串也出現在 `not_found`
- [ ] `strength` 逐列用 3.3 函式重算過
- [ ] `honest_bounds` 三桶齊全；`summary_only`、`not_read_fully` 已涵蓋所有應列來源
- [ ] 沒有任何欄位含 `|` 或換行；超長欄位已改指向附註檔
- [ ] 範例中的虛構來源已全部移除

---

## 6. 與研究方法論 SOP 的差異（規範性清單見 `workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md` 第 3.7 節）

本模板的方法源自 monorepo 的 `docs/05_development/SelfImproving_Research_Methodology_SOP.md` Part I（S1～S8），以下四項是**有意的差異**，不是遺漏：

1. `F5` 適用性改為「對本專案」的六軸（技術可行｜授權相容｜維護風險｜效能邊界｜資安｜成本），不沿用 SelfImproving 專屬的六格。
2. T3（個人貼文、論壇、社群）收進來源表但強制 `clue_only`、不得當正式證據；SOP 是把 T3 排除在來源表之外。
3. `F4` 風險標籤改用通用登錄表（3.2）；SOP 的標籤集合是自我進化主題專屬。
4. `V3` 要求原文位元組已落地並針對章節專項抽取，WebFetch 的轉述最高 `V2`；SOP 允許以 WebFetch 追問章節升到 `V3`。

**相關文件**:
- 研究到規格工作流：`workflow/sdd-research-to-prd/SDD_RESEARCH_TO_PRD.md`
- 議題契約：`docs_template/sdd/requirements/ISSUE-SCOPE-TEMPLATE.md`
- 研究者設定：`agent/specialized/research-analyst-zh.yaml`
- 憑證紀律：`agent/EVIDENCE_DISCIPLINE.md`

**最後更新**: 2026-11-02
