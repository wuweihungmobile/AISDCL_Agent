# SCG-4 獨立驗收報告：SelfImproving P6 研究來源單一化與歷史缺陷反事實回測（2026-11-10）

受審對象＝`914e0adc`（研究來源登記與抓取，RR）、`0bea20e4`（回測 BT 與範圍守衛）、`11067dd1`（重釘）；SCG-4 修正＝`12c93c65`、`8bf9b648`（重釘二十三列）、`0f65773a`（AT 改編號為 AT-630-8-E-3）；勘誤＝`0638fdd5`。QA＝獨立審查棒。oracle＝TCS-SelfImproving-P6-20261110（含〈勘誤〉E-1～E-7）。

## 結論

- **一審 FAIL**（P2 2、P3 1、P4 1）。
- 主控修正後**聚焦二審 PASS**（P1 0／P2 0／P3 0／P4 0 未結）。

## 一審發現

| 編號 | 級別 | 內容 | 處置 |
|------|------|------|------|
| QA4R-01 | P2 | `expand._checked_root` 的 DOCTYPE／ENTITY 防護只搜 UTF-8 位元組，UTF-16 可繞過。實測 `sitemap_entries` 回 `[('https://www.x.org/AAAA', None)]`。本機 expat 2.6.0 有放大保護，故非可利用的 DoS，但規格意圖未達 | 新增 `_is_utf8_family`（UTF-16／UTF-32 BOM、前 4096 位元組含 NUL、宣告 encoding 非 utf-8／us-ascii ⇒ 解析前 `ExpandRefused`）與新 AT-630-8-E-3；`12c93c65` |
| QA4R-02 | P2 | 範圍守衛逐 commit：`0bea20e4` 因 `test_selfimproving_sandbox.py` 不在允許集合而紅；`11067dd1` 的重釘三檔不在集合而紅 | 允許集合補 sandbox 與重釘三檔；`12c93c65`、勘誤寫入 TCS 〈§4〉 |
| QA4R-03 | P3 | 重釘 commit 為分桶分類補一行 fixtures docstring | 寫入 TCS-P6 勘誤（`0638fdd5`） |
| QA4R-04 | P4 | `fetch.py` 空白行 | 清空白行 |

## 一審驗收重點

- **AT 全跑**：95 條 AT 全有同名測試函式；逐條讀約 55 條，無恆真斷言。
- **突變 22 組**：21 組被殺、1 組存活（M22，UTF-16 繞過，即 QA4R-01）。M13（`fetch_chain` 不判 host 白名單）只由 registry 檔 AT-630-2-E-3 殺，鑑別力集中於單一測試，列為資訊（不降級、不加修）。
- **全套**：`run_root_unittests.py` rc=0，發現 6295 個測試、下限 6207。
- **零退化**：`si check` overall=PASS，指紋 `sha256:519d800f4d3f9af37d9aed2b31319cd63247a9ac2aa0e186a0a4f9cc0d310b4f`。
- **安全面與防 Goodhart**：各項皆在碼與測試內（外聯隔離、釘 IP、DNS 全公網、重導逐跳重驗、`proof` 不得引用回測分數、回測不入指標與指紋）。

## 主控裁決與修正

- QA4R-01：`_is_utf8_family` 於解析前拒收非 UTF-8 系 XML；新增 AT-630-8-E-3，測試函式 `test_AT_630_8_E_3_non_utf8_xml_is_refused_before_parse`。
- QA4R-02：範圍守衛 `ALLOWED` 補入 sandbox 與重釘三檔（`test_adr_xplat001_c1c2_lock.py`、`AutoSDD_improving_112.md`、`CrossPlatform_R145_Scan_Findings.md`）。
- QA4R-03：寫入 TCS-P6 勘誤（E-6），`0638fdd5`。
- QA4R-04：清空白行。
- 重釘：`8bf9b648` 為護欄層行數棘輪補第二十三列（新 AT 與允許集合）。
- 編號：`0f65773a` 把非 UTF-8 XML 拒收 AT 改為 AT-630-8-E-3，避免與既有 research.scan 驗證撞號（函式名同長、行數不變）。

## 聚焦二審（PASS）

- 六個變體皆 `ExpandRefused` 且 `_parse_xml` 呼叫 0 次：utf16-bom、utf32-bom、utf16le-nobom、utf16be-nobom-nodecl、UTF-8 宣告 UTF-16、UTF-8 宣告 ISO-8859-1；乾淨 UTF-8 正常解析。
- 兩組新突變（拿掉 NUL 判定、拿掉宣告判定）皆被新 AT 殺。
- 五個 commit（`914e0adc`、`0bea20e4`、`11067dd1`、`12c93c65`、`8bf9b648`）以 `SI_SCOPE_BASE=<c>^`、`SI_SCOPE_TIP=<c>` 跑 AT-690-4-1 全綠。
- netfetch 單檔 27 條綠；`si check` 指紋不變。

## 未驗與待辦

- 真機 V-P6-1（登記、入帳、實抓）與 V-P6-2（K=5 回測）尚未執行，見 `docs/06_quality/RTM-SelfImproving-P6-20261110.md`，標「真機待驗」。
- Console 半（登記 UI、同步端點、種子遷移）由 `agentconsole-research-registry` 鍵交付，審查報告見 `AgentConsole/docs/06_quality/SCG4-REVIEW-ResearchRegistry-20261110.md`。
