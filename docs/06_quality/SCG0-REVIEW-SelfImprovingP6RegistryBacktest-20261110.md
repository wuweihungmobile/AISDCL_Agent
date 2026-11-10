# SCG-0～3 獨立審查報告：研究來源單一化＋歷史缺陷反事實回測（兩把鍵）

- 鍵：根層 `monorepo-si-p6-registry-backtest`（SelfImproving PRD v0.15、SOP、Root_Layout、TCS-SelfImproving-P6-20261110）；Console `agentconsole-research-registry`（ResearchToPRD PRD FR-R2P-24、API_Contract_ResearchToPRD §5A、TCS-ResearchRegistry-20261110）。
- 授權：掌舵者 T1，sid `58ce5ccd-13fb-47fc-8a46-b04fa73257d7` line 14（研究來源用研發工作流同一來源、授權主控決策、AISDLC 程序最小文件）與 line 500（議題中心三個待解問題；本輪處理 OBS-SI-377）。
- 角色：規格棒兩支（根層、Console；Sonnet，兼 Architect／SA／SD）；QA 一支（Sonnet，未參與撰寫，全程唯讀）；主控 Opus 5.5 裁決並親修 P2／P3。
- 結論：**一審 FAIL → 主控裁決 D-EQA-1～18 → 兩棒修正 → 二審 FAIL（新引入 P2 一條）→ 主控親修 → 聚焦複核 PASS（P1 0、P2 0）**。殘留 P3 三條已由主控當場編修（見〈四〉）。

## 一、一審（P1 0／P2 6／P3 10／P4 2）

QA 的機械檢查（scratchpad `qa\` 臨時副本）：附錄 A 公網位址表逐列對 Bridge `allowlist.py::is_public_ip` 求值零不符；附錄 B golden 依正規化規則重新序列化位元組相等；三種事件最壞行長實算與規格一致；兩份 TCS 的 AT 計數與對照表無缺漏；17 列種子推導一致。

| 編號 | 嚴重度 | 摘要 |
|---|---|---|
| QA-X-01 | P2 | Console 追蹤來源網址輸入閘（DB CHECK、punycode 原樣通過）比 SI 驗證寬，一列被 SI 拒收的網址會使登記永遠同步不了 |
| QA-X-02 | P2 | G-S1 黃金檔產生責任兩邊衝突（根層 Python 與 Console Java 各自產、輸入不同） |
| QA-X-03 | P2 | 根層宣稱共享附錄兩份 TCS 逐字相同，Console 實際沒有附錄 A／B 與 Bridge 側 parity 測試 |
| QA-X-04 | P2 | Console 規格仍寫「根層刪除舊表」，與 D-RR-20（凍結、不刪）矛盾 |
| QA-X-05 | P2 | D-RR-25 未落實：SI status 新三鍵在 Console 狀態橫幅的處理無規格、無 AT |
| QA-BT-01 | P2 | D-BT-07「池子小於 K 以明確碼拒收」未落實，PRD 反寫「如實用盡」 |
| QA-X-06 | P3 | 同步冪等邊角（待入帳 E 後登記改回已入帳 D） |
| QA-RR-01～05 | P3 | 失敗文章不補抓；牆鐘定義前後不一；暫停鉤子位置未定義；§9.4 舊敘述；XML spy 目標不明 |
| QA-BT-02～04 | P3 | 允許集合未列舉；472 bytes 無法由參數重現；平台條件案例與零 skip 紀律 |
| QA-X-07、08 | P3 | Console §7.2(4) 過時；入帳沒有單調性 |
| QA-X-09、10 | P4 | 種子表與 golden 的 `added_by` 字面不一 |

## 二、主控裁決（D-EQA-1～18，全文存 session scratchpad `rr\QA1_RULINGS.md`）

- D-EQA-1：原則「Console 的接受集合 ⊆ SI 的接受集合」；根層 TCS 新增附錄 D（URL parity 表，42 列含 17 列種子，位元組 sha256 為常數），兩側逐列斷言。主控另定 Console 輸入原樣判定：大寫 host 與任何顯式埠（含 `:443`）由 Console 拒（附錄 D 兩列 CON 改 F，sha256 `25fd334dc97b8d135393849851962abfb54a621f11f9f0b1ba80eb27f4de1e89`）。
- D-EQA-2、3：G-S1 由根層依附錄 C 先產；共享附錄 A～D 以根層 TCS 為唯一本文，Console 以「路徑＋位元組＋sha256」引用並加 Bridge 側 AT。
- D-EQA-4、5：Console 改「舊表凍結」；狀態橫幅三鍵具名呈現（null 顯示「尚無」、缺鍵或型別不符顯示「量不到」）。
- D-EQA-6：新碼 `BT-POOL-TOO-SMALL`（輸出 `pool=<m> k=<K>`）。
- D-EQA-7：冪等與 synced 判定加「無更新的未入帳寫入」條件；D→E→D 情境 AT。
- D-EQA-8～15：文章展開每次掃描都做；牆鐘＝每條請求鏈；三個模組的暫停鉤子；§9.4 重寫；允許集合表；位數參數；平台案例以注入路徑模組確定化；spy 收斂到 `expand._parse_xml`。
- D-EQA-16～18：入帳動詞 `registry-ingest`；入帳單調性 `REG-STALE`（事件加 `audit_time`）；golden 與種子表 `added_by` 逐字一致。

修正後 AT：根層 89→95、Console 68→72。

## 三、二審（P1 0／P2 1／P3 4／P4 2）與聚焦複核

- 一審 18 條：17 條已解、QA-X-02 部分（修正引入新問題）。
- **QA2-01（P2）**：根層 AT-645-1-8 讀 Console 路徑的副本，但提交順序是根層先、Console 後，根層實作 commit 時該檔不存在，必紅。主控親修：AT-645-1-8 只驗根層檔對附錄 C 重新產生，不讀 `AgentConsole/**`；副本一致性由 Console AT-965-6-7 負責（兩側同綁附錄 C）。
- QA2-02（P3）：`backtest` 物件鍵名定稿為固定鍵集合（`cases_sha256` 存全值，顯示才截 12 碼）。
- QA2-03／05（P3）：`REG-STALE` 拒收檔與 `unchanged` 的出口寫進 Console TCS §7.3 已知邊界（不設 force 端點）。
- QA2-06（P4）：Console PRD D-169 的 WHY 殘句改寫。QA2-07（P4）：不改。
- **聚焦複核：PASS**（P1／P2 殘留與新引入皆 0）。

## 四、主控當場編修的殘留 P3（複核後）

1. 根層 AT-645-1-8：判定以重新產生比對為準，附錄 C 的 G-S1 sha256 回填是文件紀錄、不是測試常數（實作 commit 單獨看也可綠）。
2. Console AT-965-9-5：`cases_sha256` 夾具給全值，橫幅才取前 12 碼；鍵清單補 `hit5_trend`（本 AT 不顯示）。
3. Console TCS〈共用物〉一句改為「根層 AT-645-1-8 只驗根層檔對附錄 C、不讀本路徑」。

## 五、主控親驗（落地當回合）

- 七份規格檔由 scratchpad 鏡像原樣落地；逐檔檢查無 BOM、無 CR、結尾換行。
- `tools/tests/test_root_module_layout.py`：9 條 OK（Root_Layout 新列不撞落點鎖）。
- 已知且已列入 TCS-P6 §2 的實作輪同步項：SOP〈研究者〉節改版使 `_selfimproving_p5_fixtures.py::RESEARCHER_SHA` 與 `_selfimproving_fixtures.py::FRAGMENTS` 兩支既有判準在實作輪重算前會紅（D-RR-24）。
