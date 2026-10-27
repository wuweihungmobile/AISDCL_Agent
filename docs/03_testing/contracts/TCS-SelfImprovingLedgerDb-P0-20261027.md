# Test Contract Specification — SelfImproving 帳本改 DB（Ledger → PostgreSQL）P0：規格階段交付與出口（ADR、Root_Layout 先修、上位規格勘誤備案、A.4 普查、棘輪預演、P0 基準）
# 測試契約規格文件（計畫型 PRD 的 P0 階段；FRD-lite 併入檔頭；一份 TCS 涵蓋一把 SDD 鍵、只涵蓋 P0）

> **上位 PRD digest**：`sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4`（`docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` v0.3＋〈勘誤一〉1-1～1-13；87,682 bytes；2026-10-28 由主控追加勘誤節後重算，與本檔同於 Stage-2 凍結記入鍵 `monorepo-si-ledgerdb-p0` 的 FSM `frozen_stages`；Stage-1 凍結值為 `sha256:a2231270c55b6facac034d65bf62e791af6f110c4b08fc904f47f103141ee898`（82,499 bytes，commit `000a217b`））。`<base>`＝開發棒開工時的 HEAD；本檔所有「現查」於 `000a217b` 與 `99c9a868` 皆成立（其間只動缺陷帳本一列與一支測試夾具，不影響本檔引用的座標）。本檔不改 PRD 正文；PRD 的勘誤表在 §7.2（由主控貼入 PRD 檔尾〈勘誤〉節，PRD digest 因此改變，主控於 Stage-2 凍結時更新本檔檔頭與增量追溯表的 digest 欄）、其餘建議在 §7.3；後續階段鍵各自以當時 digest 凍結，勘誤走各鍵〈勘誤〉節。
> **範圍**：只涵蓋 P0（PRD §8 階段表 P0 列、§11 P0 出口列）。PRD 共 13 條 FR、58 條 AC；P0 範圍內只有 5 條（AC-LD-02-6 與 AC-LD-11-1 的「基準建立」半、AC-LD-11-4、AC-LD-13-5、AC-LD-13-7），其餘 53 條列於 §1.2〈不在本鍵〉並註明所屬階段。PRD 對 P0 的 ADR、Architecture 草稿、上位規格勘誤案三件交付沒有對應的 AC，本檔以 TCS 自訂的 `FR-LD-00`（交付項 D1～D10）承載，編號見 §1.1，並於 §7.3 建議 PRD 補條文。
> **命名紀律（解決三處 M 編號撞名）**：PRD 的 §8.1 機器閘 M1～M7、SelfImproving 量測窗 M1～M5、skip 政策 M6 三處同用 M 編號。本檔與 P0 全部交付文件一律改稱：§8.1 機器閘＝`G-SIDB-1`～`G-SIDB-7`（人工閘仍稱 H1～H5）；量測窗＝`MEAS-M1`～`MEAS-M5`；skip 政策的「全世界沒跑過」判準＝`SKIP-M6`。對照見 §5.1.1；改名已列入 §7.2 勘誤 1-5～1-7。

## 文件資訊

| 項目 | 內容 |
|---|---|
| 檔案 | `docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md`（新；SDD 規格階段 Stage-2 契約，置於 03_testing/contracts） |
| 版本與狀態 | **v0.3**（v0.2 抽驗 PASS 後補審查鏡 N-1～N-6 與 PRD 勘誤表；待 Stage-2 凍結。前版：v0.2 為一審 FAIL〔P2 4／P3 7／P4 數則〕後修訂）；2026-10-27 起草；作者角色＝QA Engineer（Sonnet 5.5，依主控任務書）；〈勘誤〉節凍結前留空 |
| 上位規格 | `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` v0.3（digest 見檔頭）；先例 TCS：`TCS-IssueCenter-20261027.md`（節體例、§5.7 允許變更集合、〈凍結後修訂路由〉）、`TCS-SelfImproving-P0-20261019.md`（P0 驗收測試先例） |
| SDD 鍵（BRIDGE §8，一功能一鍵） | `monorepo-si-ledgerdb-p0`（根層；P0 沒有 Console 半，後續階段才有 `agentconsole-si-ledgerdb-p2`、`-p3a`、`-p3b`、`-p4`） |
| 規模 | R 條文 32 條；AT 37 個（單元測試載具 DT 14、審查閘載具 GT 23）；P0 範圍 PRD AC 5／5 全覆蓋、交付項 D1～D10 全覆蓋（§1、§6）；新測試檔 1 支；檔案集合表 1 張（§5.7）；閘門指令 G-P0-1～G-P0-13（SCG-4 通過標準） |
| 載具與判定指令 | `DT`＝根層 unittest（`python -m unittest discover -s tools/tests -p "test_selfimproving_ledgerdb_p0.py" -k <AT 底線形>_`）；`GT`＝審查閘（SCG-4 通過標準的 G-P0 編號指令，輸出貼進審查報告）。PG 專屬檢查只有 G-P0-7 一道（一次性容器，不進 CI）。細節見 §2、§3 |
| 讀法 | 實作棒只需讀：〈P0 交付表〉（FRD-lite）→ 契約節 C1～C7 → R 條文 → §5.2（ADR 內容契約）→ §5.7（允許變更集合與棒切分）→ §5.9（新測試檔會撞的鎖）。QA 審查另讀 §5.3～§5.6（普查、預演、基準的現查值）與 SCG-4 通過標準 |

### 凍結後修訂路由（凍結後任何修訂走哪把鍵）

1. **只動本檔**：鍵 `monorepo-si-ledgerdb-p0` 狀態合法時（`spec-refreeze` 合法狀態只有 `SPEC_AUDIT`／`RELEASE_READY`／`RELEASE`，其餘 rc 3）追加〈勘誤〉節並更新檔頭 digest，再 `spec-refreeze --project monorepo-si-ledgerdb-p0 --doc docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md --root <monorepo 根> --reason … --approver …`；hooks-ON 時 Rule 9.6 在 `RELEASE_READY`／`RELEASE` 擋 `docs/01～03` 的寫入，文字勘誤要在 hooks-OFF 視窗改檔（`spec-refreeze` 本身是 CLI，不受此擋）。
2. **PRD 本身有誤**：PRD 已凍結、正文不可改。P0 不修 PRD 正文；§7.2 的勘誤表由主控貼入 PRD 檔尾〈勘誤〉節並於 Stage-2 凍結時記新 digest；其餘問題寫 §7.3，由後續階段鍵各自以當時 digest 凍結並走其〈勘誤〉節。
3. **上位規格（非本 PRD）的勘誤＝全備案**（PRD §3.3 九列衝突；主控代決 Q-LD0-3）：P0 **零凍結文件變動**——E-1～E-7 只備妥於案文證據檔，各於案文的「套用階段」（E-1、E-5→P1；E-2、E-6→P2；E-3、E-4→P3a；E-7→P3b）由該階段鍵於 hooks-OFF 視窗改上位檔並 `spec-refreeze`（`--reason` 引「勘誤 LD-0」並寫明修訂發生在哪個狀態、哪個 commit）。SI PRD 側六把鍵之間沒有主副關係、各自 refreeze 一次；議題中心側沿 `TCS-IssueCenter-20261027.md` 第 3、4 點（`monorepo-issue-center` 先、`agentconsole-issue-center` 隨後，兩鍵最終 digest 必須相同）。讀端（AutoClaude `check_digest`、Bridge）取 `frozen_stages` 全部條目 `spec_doc_digests` 的聯集、同鍵後者勝出，不可只讀 `frozen_stages[-1]`。
4. **本檔載明的「P0 基準」被改動**（協定目錄、`params.fingerprint()`、`CHECK_RULES_REV`、skip 摘要）：任何一項變動即 P0 基準失效，必須先走本條：基準證據檔 `docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md` 追加一列變動原因與新值（不得原地覆寫舊列），再於本檔〈勘誤〉登記；後續階段 TCS 以最新基準列為準。
5. 凍結審批依根 `CLAUDE.md`〈凍結常態規則〉（獨立審查 PASS 且主控親驗無 P1、P2 才代執行）。

**上位規格現況與 P0 處置**（2026-10-27 於 `<base>` 以 FSM 狀態檔現查）：

| 目標文件（現行 digest 前 8 碼） | 載有它的 FSM 鍵（狀態） | 現況 | P0 的處置 |
|---|---|---|---|
| `docs/01_requirements/SelfImproving_PRD.md`（`a341259c`；586,722 bytes） | `monorepo-si-p0-ledger`、`monorepo-si-p1-propose`、`monorepo-si-p2-gate-apply`、`monorepo-si-p3-measure-retire`、`agentconsole-si-decide`、`agentconsole-si-mirror`（皆 `RELEASE`） | 六鍵聯集的 PRD 摘要皆等於現檔 | **不動**（備案 E-1～E-5：P1／P2／P3a 套用） |
| 同上 | `monorepo-selfimproving`（`SPEC_FROZEN`） | 聯集摘要 `1d26dbf8…` **已與現檔不符**（2026-10-25、10-26 兩輪勘誤皆未涵蓋它） | **不入路由**：`SPEC_FROZEN` 不是 `spec-refreeze` 的合法狀態；既有不符不因 P0 加重（Q-LD0-4 結案：知悉、另案） |
| `docs/01_requirements/Issue_Center_PRD.md`（`9765a825`；98,208 bytes） | `monorepo-issue-center`、`agentconsole-issue-center`（皆 `RELEASE_READY`） | 聯集摘要等於現檔 | **不動**（備案 E-6、E-7：P2、P3b 套用） |
| `AgentConsole/docs/02_architecture/Architecture.md`（`dbdbd5f9`） | `agentconsole-si-decide`、`agentconsole-si-mirror` | 聯集摘要等於現檔 | **不改**（Architecture 草稿只備案；補丁隨 P1、P2、P3 套用） |
| 根 `CLAUDE.md:44,48`（軌道表以缺陷帳本未結列為驅動器） | 非凍結規格 | — | 屬 P4（PRD §3.3 #8、OQ-4），P0 不動 |

## 增量變更專用：FRD-lite 與〈增量追溯表〉

### FRD-lite

**Before／After（現值皆於 `<base>` 實查）**

| 面 | Before | After（P0 出口） |
|---|---|---|
| `docs/02_architecture/Root_Layout_and_Module_Placement.md` §1 目錄地圖 | 10 列，無 `tools/tests_pg/` | 11 列（加 `tools/tests_pg/`） |
| 同檔 §2 落點表 | 14 列（`:29-42`），無 PG 專屬測試、無套件內 SQL 資料目錄 | 16 列（加兩格，各含 WHY；契約節 C1.1） |
| 同檔 §3 登記表 SelfImproving 列（`:52`） | 登記議題中心三支與既有測試，無 ADR、無本案證據檔 | 加 `docs/02_architecture/ADR-SIDB-*.md` 等已存在路徑；**不得**加尚不存在的 `tools/tests_pg/`、`sql/`（落點鎖 `registry_problems` 會紅，見 R-LD0-04） |
| `docs/02_architecture/ADR-SIDB-*.md` | 0 檔（根層 `docs/02_architecture/` 現只有 3 檔，無任何根層 ADR 檔） | 8 檔（`ADR-SIDB-001`～`008`） |
| `docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md` | 無 | 新（三塊補丁草稿，P0 不套用） |
| `docs/01_requirements/SelfImproving_PRD.md`、`Issue_Center_PRD.md` | 無 `## 勘誤` 節（既有訂正為行內〔訂正…〕） | **不變**（E-n 全備案，不在 P0 追加勘誤節；digest 仍 `a341259c…`、`9765a825…`） |
| 證據檔 `docs/06_quality/SelfImproving_LedgerDb_*` | 無 | 3 檔：`_P0_Errata.md`（勘誤案案文，備案）、`_P0_Baseline.md`（P0 基準）、`_P0_Ratchet_PreRun.md`（棘輪預演＋腳本） |
| `tools/tests/` 測試檔 | 112 支 `test_*.py`；`_TREE_FILE_FLOORS['tools/tests']`＝89 | 113 支（加 `test_selfimproving_ledgerdb_p0.py`）；下限須重釘為 90（`int(113×0.8)`，§5.9） |
| `tools/`、`.claude/`、`params.json`、協定目錄、三本帳、事件帳本、提案目錄、凍結上位文件 | — | **位元組不變**（P0 不寫生產碼；§5.7「不得變更」） |

### P0 交付表（先列「要交付哪些檔、改哪些檔」，每項引 PRD 座標、對應 AT）

「類」欄：N＝新增、M＝修改、E＝只讀驗證（不改檔）。

| 項 | 交付 | 檔案（類） | PRD 座標 | 對應 AT |
|---|---|---|---|---|
| D1 | Root_Layout 先修：§2 加兩格（PG 專屬契約測試 `tools/tests_pg/`；套件內 SQL 遷移資料目錄 `sql/`）、§1 加一列、§3 SelfImproving 列補登記 | `docs/02_architecture/Root_Layout_and_Module_Placement.md`（M） | §8 P0 列「Root_Layout §2 修訂」；§9.4 `:223` 括號；AC-LD-11-4；§11 P0 機械可驗欄；D-18 | AT-LD-11-4-1、-2、-3、-E-1、-E-2 |
| D2 | 以 `tools/tests` 為根的掃描器普查與 `tools/tests_pg/` 管轄判定（結果入本檔 §5.3） | 本檔 §5.3（N）；乾跑置位實驗為 QA 審查閘 | AC-LD-11-4 後半；§9.4 `:229`；ADR-SIDB-02 | AT-LD-11-4-4、-5、-E-3 |
| D3 | ADR-SIDB-001～008 成檔（各含選項、代價、決定、再開症狀；ADR-003 附 SQL 草稿） | `docs/02_architecture/ADR-SIDB-001-…md`～`ADR-SIDB-008-…md`（N，8 檔） | §8 P0 列；§9.5 六條；§9.3 `:221`（SQL 草稿隨 ADR-SIDB-03）；§11 P0 機械可驗欄 | AT-LD-00-D3-1～-5、-E-1 |
| D4 | Architecture 草稿（§7.2、§9.4、§10.3 三塊補丁；B、C 兩變體；P0 不套用） | `docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md`（N）；`AgentConsole/docs/02_architecture/Architecture.md`、`AgentConsole/docker/README.md`（E，位元組不變） | §8 P0 列「Architecture 草稿」；§9.4 `:234`（`Architecture :612-618,854-870,944-956`；B 方案另含 `docker/README.md` 〈4.3〉）；§11 P0 機械可驗欄 | AT-LD-00-D4-1、-2、-E-1 |
| D5 | 上位規格勘誤案（PRD §3.3 九列；**全備案**）：案文證據檔；P0 零凍結文件變動 | `docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md`（N）；`SelfImproving_PRD.md`、`Issue_Center_PRD.md`（E，位元組不變） | §3.3；§8 P0 列「§3.3 勘誤案」；§11 P0 機械可驗欄 | AT-LD-00-D5-1～-4 |
| D6 | A.4 普查定稿（附錄 A.4 逐列於 `<base>` 重核座標、補其餘 20 檔〔15 檔僅名稱提及、2 檔存在性依賴、3 檔 `fx.ROOT` 讀非帳本檔〕、三項「TCS 逐斷言判」已判、落地階段） | 本檔 §5.4（N） | 附錄 A.4；AC-LD-13-5；§8 P0 列「A.4 普查定稿」；R-3 | AT-LD-13-5-1、-2、-3 |
| D7 | 棘輪預演表（`repin_growth_problems()` 與款(12) 唯讀預演；需入名冊的階段與上修量） | 本檔 §5.5（N）；`docs/06_quality/SelfImproving_LedgerDb_P0_Ratchet_PreRun.md`（N，含腳本與輸出） | AC-LD-13-7；§8.3；§8 P0 列「棘輪預演」 | AT-LD-13-7-1、-2 |
| D8 | P0 基準記錄（協定目錄、指紋、`CHECK_RULES_REV`、`items=33` 十處釘、skip 摘要） | `docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md`（N） | AC-LD-02-6；AC-LD-11-1；§8.1 `G-SIDB-5`；§11 P1 列「P0 基準」 | AT-LD-02-6-1、-2、-E-1、-E-2；AT-LD-11-1-1 |
| D9 | 流程件：本 TCS、1 支新測試檔、SCG-4 審查報告與 RTM、收尾單人窗口重釘 | 本檔（N）；`tools/tests/test_selfimproving_ledgerdb_p0.py`（N）；`docs/06_quality/SCG4-REVIEW-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md`、`RTM-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md`（N，主控／QA）；重釘面見 §5.9（M，收尾單人窗口） | §8.3「每階段新增 `tools/tests` 測試檔 ≤3」；AC-LD-11-4；根 `CLAUDE.md` 鐵律七 | AT-LD-00-D9-1～-3 |
| D10 | 命名紀律：三處 M 編號撞名改稱 | 全部 P0 交付文件（約束，不單獨成檔） | 本檔檔頭；§8.1；AC-LD-13-6；AC-LD-11-1 | AT-LD-00-D10-1 |

**不在 P0 交付的 PRD 項（避免誤做）**：SOP 新節（P1 的 psql 範本、P3b 改寫）、`Frozen_Manifest`（P3b）、`tools/tests_pg/` 與 `sql/` 目錄本身及其內容（P1）、任何 `tools/lib/selfimproving/dal_*.py`（P1）、`SelfImproving_Snapshots/` 目錄（P3a）、上位 PRD 的任何修改與 refreeze（備案，各階段套用）、compat-ci `paths` 中與 `tools/tests_pg/**` 有關的項（本檔結論＝不入，§5.3.1 末段；P0 只為新 DT 消費的 docs 路徑加 `paths`，見 §5.7.1、§5.9 第 9 列）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根；鍵 `monorepo-si-ledgerdb-p0`）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | PRD v0.3 全文（SCG-0 獨立審查：一審 FAIL〔P2 7〕→二審 FAIL〔P2 1〕→三審抽驗 PASS；掌舵者 2026-10-27 對 OQ-1～OQ-6 全部採建議值，PRD §13.2 裁決段）；Stage-1 依常態規則由主控執行 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | FR-LD-01～13（PRD §5）；P0 範圍＝AC-LD-02-6、11-1（基準半）、11-4、13-5、13-7 ＋ TCS 自訂 FR-LD-00 的 D1～D10；其餘見 §1.2 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-0／NFR 已量化定義 | PRD §6（安全、誠實劃界、效能、跨平台、零侵入）；P0 只承擔「零侵入」（不動守衛面、`params.json`、協定目錄、`tools/`、凍結上位文件）與「跨平台」（Root_Layout 新格的 `sql/` 行尾規則）；本檔 R-LD0-02、R-LD0-28 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-0／User Story 已完成 INVEST 檢查 | 不適用（計畫型 PRD；場景見 PRD §2）；P0 的使用者是後續階段的實作棒與審查者，其需求寫成 D1～D10 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-0／利害關係人已確認簽核 | PRD §13.2〈掌舵者裁決〉（2026-10-27，本窗互動選項；Stage-1 凍結依據）；本檔 §7.1 裁決（含主控代決 Q-LD0-1～10）由主控回報掌舵者，掌舵者可隨時以 T1 推翻 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-0／RTM 初版已建立 | 本檔 §1、§6；P0 收尾由主控產 `RTM-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md`（Root_Layout §2 審查／RTM 列） | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review | 不適用（計畫型 PRD 的 P0 無程式面設計）；最近依據 PRD §8、§9（模式矩陣、資料模型、落點表、ADR 候選） | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-1／API Spec 草稿完成 | 不適用（P0 無 HTTP 端點、無 CLI 動詞）；P1 起的 CLI 動詞見 PRD §9.4 與後續階段 TCS | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-1／資料模型設計完成 | PRD §9.3（`si` schema 14 張表、三角色）；P0 的交付＝ADR-SIDB-003 的 SQL 草稿與逐表守衛矩陣（本檔 §5.2.2）；欄位於 P1 TCS 定稿 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-1／NFR 設計對應完成 | PRD §6 對應本檔 R-LD0-26～R-LD0-29（零侵入、基準不變） | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-1／整合架構說明完整 | 依賴＝PG18（影子期任何可達的 PG18；P3 前定案，ADR-SIDB-001）；P0 無執行期依賴；Architecture 草稿（D4）備妥補丁 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-2／C4 Context 圖完成 | 不適用（brownfield 計畫型）；PRD §8.2（DB 在哪、怎麼連）與 ADR-SIDB-001 的拓撲 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-2／C4 Container 圖完成 | PRD §9.4 模組落點表；本檔〈契約節〉C1（Root_Layout 兩新格）與 §5.7 檔案集合 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-2／所有架構決策有對應 ADR | **本階段的主交付**：PRD §9.5 六條 ADR 候選（SIDB-01～08）成 8 個正式 ADR 檔（D3），見 R-LD0-09～R-LD0-13 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-2／Trust Boundary Map 完成 | 不適用；P0 要點＝憑證只走 `SI_DB_DSN`＋`PGPASSFILE`、角色三分（ADR-SIDB-007、ADR-SIDB-003）；P0 文件不得含 DSN 或密碼字面（R-LD0-13） | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-2／Before／After 架構對比 | 本檔 FRD-lite〈Before／After〉；PRD §9.2 模式矩陣 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-3／OpenAPI 3.1 規格完整 | 不適用（P0 無 API） | （本檔；自引） | n/a（自引） |
| SCG-3／Request／Response Schema 定義完整 | 不適用；P0 的「契約」是交付文件的必要結構（本檔〈契約節〉C1～C7） | （本檔〈契約節〉；隨 Stage-2 凍結，自引） | n/a（自引） |
| SCG-3／錯誤碼定義 | 不適用（P0 無執行期錯誤碼）；PRD 的 `MIGRATION-CHECKSUM`、`SCHEMA-BEHIND`、`MODE-MISMATCH` 等於 P1 TCS 定稿 | docs/01_requirements/SelfImproving_Ledger_DB_PRD.md | sha256:d66d0e59cab5823a39a58c2dd6b948f3a0eb7713fdda49de761c147b764baaf4 |
| SCG-3／Consumer Contract 完成 | 消費者＝P1 實作棒（Root_Layout 兩新格、ADR、P0 基準）、後續各階段 TCS（普查、預演、基準、勘誤案）、掌舵者（OQ 答覆）；契約即〈契約節〉C1～C7 | （本檔〈契約節〉；自引） | n/a（自引） |
| SCG-3／API ID 與 RTM 已對應 | 不適用；AT 到 RTM 見本檔 §1 與 §6 | （本檔；自引） | n/a（自引） |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（含突變重放） | （本檔；自引） | n/a（自引） |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值。PRD 的值是 Stage-1 凍結的 digest；本檔作者於 2026-10-27 以 SHA-256 對工作樹現況重算一致（82,499 bytes）。凍結後的實際 digest 以該鍵 `show --json` 為準，與本表不符時以 `show` 為準並更正本表。

### R 條文（把 PRD §3.3、§8、§9.4、§9.5、§11、AC-LD-02-6／11-1／11-4／13-5／13-7 逐條化；每條可判定）

**突變語言**（「突變」欄與 QA 重放共用；QA 在**保留歷史的 clone** 上逐一套用——`git clone --no-local <repo> <短路徑>` 後 `git checkout <tip>`（含 ADR、DT、證據檔、Root_Layout 新格與 `<base>..<tip>` 歷史；`git archive <base>` 沒有這些交付物也沒有 `.git`，**不可用於突變**），套用突變後**提交**才跑所列 AT 與 G 閘〔GT 的座標、關鍵字與 `<base>..<tip>` 檢查讀 git 樹與歷史，未提交的改動看不見；DT 突變不需提交；突變提交取代 `<tip>`〕；不動工作樹、不用 `git checkout --` 還原；「killed」＝所列 AT **或 G 閘**任一轉紅（定義見 §2），回報「突變 MU-LD0-nn：killed／survived」，倖存者＝該 R 條文缺鑑別力，須補 AT 並勘誤）：

| 操作 | 語意 |
|---|---|
| `DEL /re/ <檔>` | 刪除 `<檔>` 內所有符合 `re`（多行模式、`^` `$` 為行界）的整行 |
| `SUB /re/→x/ <檔>` | 把第一個符合 `re` 的文字替換為 `x`（`x` 可空；`re` 可帶 `(?s)` 與反向參照 `\1`）；**只換首處，字樣若在檔內重複，其餘會倖存——故只用於字樣唯一或首處即足以致命者** |
| `SUBALL /re/→x/ <檔>` | 把**全部**符合 `re` 的文字替換為 `x` |
| `SUBALL@row /anchor/ /re/→x/ <檔>` | 只在含 `anchor` 的表格列內，把全部符合 `re` 的文字替換為 `x` |
| `SUBALL@sec /heading/ /re/→x/ <檔>` | 只在標題符合 `heading` 的節內（至下一個同級或更高階標題之前），把全部符合 `re` 的文字替換為 `x` |
| `SUB-AFTER /anchor/ /re/→x/ <檔>` | 先找第一個符合 `anchor` 的行，自該行起把第一個符合 `re` 的文字替換為 `x` |
| `HEAD- /re/ <檔>` | 刪除標題行符合 `re` 的整個節（至下一個同級或更高階標題之前） |
| `WEAKEN <函式> <檔>` | 把 `<檔>` 內 `<函式>` 的主體整個換成 `return []`（回傳 `str` 者換成 `return ""`）；**自證 AT 必須因此轉紅，否則該自證是空的** |
| `BYTE <檔> @mid` | 翻轉檔案正中央一個位元組（只用於 digest 類 AT） |
| `RM <檔>`／`REN <舊>→<新>` | 刪檔／改名 |

「AT」欄為 AT 簡碼（例 `11-4-1`＝`AT-LD-11-4-1`；`D3-2`＝`AT-LD-00-D3-2`）。`RL`＝`docs/02_architecture/Root_Layout_and_Module_Placement.md`；`A3`＝`docs/02_architecture/ADR-SIDB-003-*.md`（`*` 取唯一符合的檔）；`<新測試檔>`＝`tools/tests/test_selfimproving_ledgerdb_p0.py`。

#### A Root_Layout 先修（D1；PRD AC-LD-11-4、§9.4 `:223`、D-18）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-01 | `RL` 的 `## 2.` 節有一列，首格含「PG 專屬契約測試」、落點格含反引號 `tools/tests_pg/`、規則格含 C1.1 列出的**全部 13 個**必要字樣（含 AC-LD-11-4 要求的「行數棘輪」「skip 政策」管轄否定） | MU-LD0-01：`DEL /^\|[^\n]*PG 專屬契約測試/ RL`；MU-LD0-02：`SUBALL@row /PG 專屬契約測試/ /SI_TEST_PG_REQUIRED/→X/ RL`；MU-LD0-03：`SUBALL@row /PG 專屬契約測試/ /guardrail_cli/→X/ RL`；MU-LD0-51：`SUBALL@row /PG 專屬契約測試/ /行數棘輪/→X/ RL`；MU-LD0-52：`WEAKEN layout_cell_problems <新測試檔>`（AT-LD-11-4-E-1 自證須紅） | 11-4-1、11-4-E-1 |
| R-LD0-02 | `RL` 的 `## 2.` 節有一列，首格含「套件內 SQL 遷移資料目錄」、落點格含反引號 `tools/lib/<module>/sql/`、規則格含 C1.1 列出的**全部 10 個**必要字樣 | MU-LD0-04：`DEL /^\|[^\n]*套件內 SQL 遷移資料目錄/ RL`；MU-LD0-05：`SUBALL@row /套件內 SQL 遷移資料目錄/ /只追加/→X/ RL` | 11-4-2、11-4-E-1 |
| R-LD0-03 | `RL` 的 `## 1.` 地圖有一列首格含 `tools/tests_pg/`；`## 3.` SelfImproving 列的「測試」或「資料／文件」欄登記本案已存在的新檔（`test_selfimproving_ledgerdb_p0.py`、`ADR-SIDB-*.md` glob、Architecture 草稿、三份證據檔） | MU-LD0-06：`DEL /^\|[^\n]*`tools\/tests_pg\/`/ RL`（刪所有含該路徑的表列，§1 與 §2 的列都中）；MU-LD0-07：`SUBALL@row /^\| SelfImproving/ /`tools\/tests\/test_selfimproving_ledgerdb_p0\.py`/→/ RL` | 11-4-3 |
| R-LD0-04 | `RL` 的 `## 3.` 登記表**不得先登記尚不存在的路徑**：P0 結束時 `tools/tests_pg/`、`tools/lib/selfimproving/sql/` 皆不存在，登記它們＝`registry_problems` 紅（落點鎖只解析 `## 3.` 節；`## 2.` 的格不被解析，所以兩新格可先寫）。這條由落點鎖本身（G-P0-3）與合成自證承載，**不入永久 DT 斷言**（P1 落地後登記才是對的） | MU-LD0-08：在 `RL` 的 SelfImproving 列「測試」欄追加 `` `tools/tests_pg/` ``（`SUB /(\| `tools\/tests\/test_selfimproving_issuemap\.py`)/→\1、`tools/tests_pg/`/ RL` 類）→ G-P0-3 的 `test_root_module_layout` 紅 | 11-4-E-2、G-P0-3 |

#### B 掃描器普查與 `tools/tests_pg/` 管轄（D2；PRD AC-LD-11-4 後半）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-05 | 本檔 §5.3 普查表覆蓋四類掃描器——(a) 只看 `tools/tests` 的（runner discover、skip 政策、行數棘輪、檔數下限、分桶、MIN_TESTS）；(b) 遞迴看 `tools/` 全樹的（LOC 分級、ruff、py_compile、`.ps1`／`.sh` 掃描面）；(c) 僅在註解或字串提及 `tools/tests` 的；(d) 以路徑前綴字串分類的（`tools/lib/selfimproving/scan.py` 的 `bucket_of`，PRD §9.4 沒列）——每列給「對 `tools/tests_pg/` 的判定」（四值之一，補充只寫在依據欄）與可重現的座標（檔:行＋關鍵字） | MU-LD0-09（模擬座標失真）：`SUBALL /_EXTRA_SCAN_TREES/→_XTRA_TREES/ tools/lib/skip_tag_policy.py`（全檔不再含該關鍵字；副本須提交）→ §5.3.1 A2 列的座標檢查紅 | 11-4-5 |
| R-LD0-06 | 乾跑置位實驗（§5.3.2）：於 `git archive <base>` 副本加入 probe 檔 `tools/tests_pg/test_selfimproving_dal_pg_probe.py` 與 `tools/lib/selfimproving/sql/V000__probe.sql`，選檔規則所得各檔與無 probe 的對照副本**結果相同**（rc、收集數、失敗集合皆同；基線紅者以同樣紅法計）；第二輪（副本皆 `git init`＋提交，讓依 git 索引的掃描器有輸入）重跑第一輪基線紅者與棘輪類 8 檔（起草時 25＋8＝33 檔），同樣逐檔相同 | MU-LD0-10：在 probe 副本 `SUB /frozenset\(\{"tests"\}\)/→frozenset({"tests", "tests_pg"})/ AutoClaude/tools/check_loc_budget.py`，LOC 報表不再含 probe → AT-LD-11-4-4 的「LOC 判定」子檢查紅 | 11-4-4 |
| R-LD0-07 | `tools/tests_pg/*.py` 受 LOC 分級（`guardrail_cli`，單檔 ≤750 斷言行；`check_loc_budget.py:279-282,296,551`）與 ruff 全規則（`tools/ruff.toml` 的 `"tests/*.py"=["E501"]` 只涵蓋目錄名 `tests`，不涵蓋 `tests_pg`）；故 PG 測試須每檔 ≤750 斷言行、每行顯示寬度 ≤100（CJK 算 2）、`py_compile` 通過 | MU-LD0-11：probe 檔加一行 152 寬註解 → ruff 回 E501（預期紅，作為「確實不被豁免」的正向證據；若不紅＝本條不成立） | 11-4-4 |
| R-LD0-08 | 對照組（反向）：同一支 probe 放進 `tools/tests/`（非兄弟目錄）時，只看 `tools/tests` 的棘輪**會反應**（行數棘輪的 `[新增]`／`[成長]` 款、E501 存量棘輪），證明「兄弟目錄不被棘輪計入」是目錄選擇造成、不是掃描器壞了 | MU-LD0-50（實驗輸入突變）：把 ctrl 的放置改為 `tools/tests_pg/`（ctrl≡probe）→ ctrl 相對 base 零新增失敗，AT-LD-11-4-E-3 判準紅（證明對照組確實有牙） | 11-4-E-3 |

#### C ADR（D3；PRD §9.5、§9.3 `:221`、§11 P0 機械可驗欄）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-09 | `docs/02_architecture/` 有 `ADR-SIDB-001`～`008` 各恰一個 `ADR-SIDB-00N-<slug>.md`（`<slug>`＝小寫 ASCII 與連字號；日後增補 009 以上不紅）；檔內標題行為 `# ADR-SIDB-00N：<中文標題>（PRD 簡稱 SIDB-0N）` | MU-LD0-12：`RM ADR-SIDB-005-*.md`；MU-LD0-13：`REN ADR-SIDB-003-*.md→ADR-SIDB-009-integrity.md` | D3-1 |
| R-LD0-10 | 每個 ADR 依序含六節標題：`## 狀態`、`## 脈絡`、`## 選項與代價`、`## 決定`、`## 再開症狀`、`## 連動面`；「選項與代價」依 §5.1.2 選項計數規則有 ≥2 個選項，**每個選項**各有一行 `- 代價：`；「再開症狀」≥1 條，且每條至少含一個反引號 token（指令、環境變數、錯誤碼、檔名、門檻之一——可觀測事件，不是感想）；「狀態」值以 `Accepted` 或 `Superseded` 起頭（階段性決定寫 `Accepted（階段性：<條件>）`） | MU-LD0-14：`HEAD- /^## 再開症狀/ ADR-SIDB-004-*.md`；MU-LD0-15：`DEL /^\s*- 代價：/ ADR-SIDB-002-*.md`（刪該檔全部代價行）；MU-LD0-16：`SUB /^## 狀態\n+Accepted/→## 狀態\n\nDraft/ ADR-SIDB-006-*.md`；MU-LD0-53：`WEAKEN adr_problems <新測試檔>`（AT-LD-00-D3-E-1 自證須紅） | D3-2、D3-E-1 |
| R-LD0-11 | 選項與決定逐檔對 PRD §9.5（§5.2.1 表）：選項標籤齊全且「決定」節含該表指定的決定字樣（例：001 含 `C` 與「B 在同樣隔離下可接受」；002 含 `B` 與 `tools/tests_pg/`；008 含「舊檔永遠保留」與 `AUTOSDD_SNAPSHOT_GATE_OFF`） | MU-LD0-17：`SUBALL@sec /^## 決定/ /tools\/tests_pg\//→tools\/tests_x\// ADR-SIDB-002-*.md`；MU-LD0-18：`SUBALL /AUTOSDD_SNAPSHOT_GATE_OFF/→AUTOSDD_X/ ADR-SIDB-008-*.md` | D3-3 |
| R-LD0-12 | ADR-SIDB-001 的「狀態」節含 `階段性`、`H2`、`H3`（P3 進場條件＝PRD §8.1 的 H2〔DB 生命週期隔離〕與 H3〔拓撲決議與他機匯入演練〕）；「決定」節記 OQ-2 的掌舵者裁決（`單一主力機為真相`，他機唯讀） | MU-LD0-19：`SUB /階段性：[^）]*/→階段性：/ ADR-SIDB-001-*.md`（清空狀態節的條件）；MU-LD0-20：`SUBALL /H3/→H9/ ADR-SIDB-001-*.md` | D3-3 |
| R-LD0-13 | ADR-SIDB-003 附 SQL 草稿（` ```sql ` 區塊，合計含 §5.2.2 列的全部物件字樣）與逐表守衛矩陣（覆蓋 PRD §9.3 的 14 張表，每表恰屬一類：追加專用／可變且逐列 audit／讀模型／自舉例外），並明寫 `audit_chain_guard` 只驗 `seq` 連續、`prev_hash` 銜接與 `txid`、**不重算 `row_hash`**；八個 ADR 與其餘 P0 文件不得含 DSN、密碼、金鑰字面（`<YOUR_…>` 佔位符除外） | MU-LD0-21：`DEL /audit_chain_guard/ ADR-SIDB-003-*.md`；MU-LD0-22：`DEL /^\|[^\n]*\bdefects\b[^\n]*\|$/ ADR-SIDB-003-*.md`（刪矩陣中 defects 那列；表名寫 `si.defects` 或 `defects` 皆可被匹配）；MU-LD0-23：在任一 ADR 追加一行 libpq URI（`postgresql` 協定名、userinfo 帶密碼段，密碼值取 `FAKEPW`；字面由 QA 在副本現組，不寫進任何文件，B-15）→ D3-4 的字面掃描紅 | D3-4、D3-5 |

#### D Architecture 草稿（D4；PRD §8 P0 列、§9.4 `:234`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-14 | `SelfImproving_LedgerDb_Architecture_Draft.md` 含三塊補丁，標題各含 `§7.2`、`§9.4`、`§10.3`；每塊都有四欄字樣：`目標檔：`（路徑＋行號座標，於 `<base>` 重核）、`插入文：`（逐字、可直接貼入）、`生效階段：`（P1／P2／P3 之一）、`路由：`（哪兩把 FSM 鍵 refreeze）；§7.2 與 `docker/README.md` 〈4.3〉兩塊另含 `B 方案` 與 `C 方案` 兩個變體標示 | MU-LD0-24：`DEL /^生效階段：/ <草稿>`（刪全部）；MU-LD0-25：`HEAD- /§10\.3/ <草稿>`；MU-LD0-54：`WEAKEN draft_problems <新測試檔>`（AT-LD-00-D4-E-1 自證須紅） | D4-1、D4-E-1 |
| R-LD0-15 | P0 不改 `AgentConsole/docs/02_architecture/Architecture.md`（digest `dbdbd5f9…`）與 `AgentConsole/docker/README.md`：與 base 位元組相同（避免對 `agentconsole-si-decide`／`-mirror` 兩鍵造成未 refreeze 的漂移） | MU-LD0-26：`BYTE AgentConsole/docs/02_architecture/Architecture.md @mid`（G-P0-2 紅） | D4-2 |

#### E 上位規格勘誤案（D5；PRD §3.3 九列、§11 P0 機械可驗欄；**全備案**）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-16 | `SelfImproving_LedgerDb_P0_Errata.md` 逐條記 E-1～E-7（對應 PRD §3.3 列 #1～#5、#7 與其拆分；#6、#8、#9 在表尾「不勘誤」節各給處置與理由），每條含欄位：`目標文件`、`原文座標`（檔:行，`<base>` 重核）、`原文`（`<base>` 版逐字截取）、`訂正文`、`生效階段`、`套用階段`（P1／P2／P3a／P3b）、`理由`；E-4 含核准座標欄（佔位或已填）；`原文`與目標文件該行**逐字相同** | MU-LD0-27：`SUB /原文座標：[^\n]*/→原文座標：/ <案文檔>`；MU-LD0-29：`SUB-AFTER /^### E-1/ /^- 原文：./→- 原文：X/ <案文檔>`（改 E-1 `原文` 的首字，使其不再是 base 的子字串） | D5-1、D5-2 |
| R-LD0-17 | **P0 不改上位 PRD**：`SelfImproving_PRD.md` 與 `Issue_Center_PRD.md` 與 `<base>` 位元組相同（E-1～E-7 全備案，各於「套用階段」由該階段鍵套用並 refreeze；不在 P0 追加 `## 勘誤` 節） | MU-LD0-28：改 `SelfImproving_PRD.md:791` 一個字；MU-LD0-30：改 `SelfImproving_PRD.md:100` 一個字（正文漂移）→ AT-LD-00-D5-3 的 `git diff --quiet` 紅 | D5-2、D5-3 |
| R-LD0-18 | 六鍵（`monorepo-si-p0-ledger`、`-p1-propose`、`-p2-gate-apply`、`-p3-measure-retire`、`agentconsole-si-decide`、`agentconsole-si-mirror`）的聯集 PRD 摘要＝現檔（P0 不改檔，故仍全部相符）；`monorepo-selfimproving` 不入路由並在案文載明原因（`SPEC_FROZEN`、既有不符） | MU-LD0-31：在 FSM 狀態檔的副本（`AgentConsole/build/reports/fsm/FSM-STATE-agentconsole-si-mirror.yaml`）`SUBALL /sha256:a341259c/→sha256:00000000/`（模擬該鍵摘要漂移）→ G-P0-8 對該鍵 PRD 列回 DIFF 而紅 | D5-3 |
| R-LD0-19 | `Issue_Center_PRD.md` 位元組不變（digest `9765a825…`）、`monorepo-issue-center`／`agentconsole-issue-center` 的 FSM 狀態檔位元組不變；E-6、E-7 只存在於案文 | MU-LD0-32：`BYTE docs/01_requirements/Issue_Center_PRD.md @mid` | D5-4 |

#### F A.4 普查定稿（D6；PRD 附錄 A.4、AC-LD-13-5）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-20 | 本檔 §5.4 的 A.4 表：每列含測試座標（`<base>` 行號）、讀什麼、P3b 後影響、處置（`維持`／`改讀 export`／`改讀快照`／`隨被測碼退役` 四值之一）、處置落地階段；PRD 三項「TCS 逐斷言判」已逐斷言判定；其餘 20 檔另表列出（15 檔僅名稱提及、不需處置；2 檔存在性依賴、維持並加不得變更約束；3 檔 `fx.ROOT` 讀非帳本檔） | MU-LD0-33：`SUBALL /REAL_DEFECT_LOG/→REAL_X/ tools/tests/test_selfimproving_issuemap.py`（關鍵字自全檔消失；副本須提交）→ 座標重核（G-P0-5 的逐列檢查）紅 | 13-5-1、13-5-3 |
| R-LD0-21 | 普查重跑：PRD `[C-17]` 兩條 Grep 命中檔案集合 ⊆「A.4 表」∪「§5.4.1b」∪「§5.4.2a／b」；`fx.ROOT`／`REAL_ROOT` 型根讀取普查（§5.4.4(b)）命中檔 ⊆「A.4 表」∪「§5.4.2a／b／c」；漏列＝紅 | MU-LD0-34：在副本新增 `tools/tests/test_zz_new_reader.py`（內含 `REAL_LEDGER = ...`）並提交 → G-P0-5 的集合包含檢查紅 | 13-5-1 |
| R-LD0-22 | 帳本盲實驗（§5.4.3）：副本移除六類帳本路徑後，28 個測試檔（A.4 的 10 檔＋§5.4.2a 的 13 支＋§5.4.2b 的 2 檔＋§5.4.2c 的 3 檔）中，因移除而新增的失敗所屬測試檔 ⊆ A.4「讀真實內容」的 10 檔 ∪ 5.4.2b「存在性依賴」的 2 檔；5.4.2a 與 5.4.2c 的 16 檔結果與對照副本相同；且實驗**非空轉**——至少一支 A.4 測試因移除而轉紅（本次 9 檔共 158 項） | MU-LD0-35：從 A.4 表刪去 `test_defect_id_reference_integrity.py` 一列 → 實驗回「失敗不在表內」紅；MU-LD0-36：實驗時不移除帳本（對照）→ 零失敗，空轉判準紅 | 13-5-2、13-5-E-1 |

#### G 棘輪預演（D7；PRD AC-LD-13-7、§8.3）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-23 | 預演表（§5.5）與證據檔 `SelfImproving_LedgerDb_P0_Ratchet_PreRun.md` 覆蓋 P0（新測試檔）、P1～P4 × 兩種標籤情境（S-A 同標籤續列、S-B 輪號前進）× 低高兩個增量，每格填 `repin_growth_problems()` 的**真實回傳標籤集合**；S-B 另逐輪計入款(12) 到期義務（`_REPIN_NET_CAP_DUE_ROUND`／`DUE_TARGET`，`repin_cost_ratchet_problems()`）與「該輪上限」；標出需入名冊的階段、名冊上限上修量、上限表須追加的階段與「R214 精確淨額」須重登的次數 | MU-LD0-37：把證據檔表內 `[超出每輪上限]` 改成 `NONE`（任一格）→ 重跑比對紅 | 13-7-1、13-7-2 |
| R-LD0-24 | 預演是唯讀的：腳本只 import 鎖檔、不寫檔、不呼叫 git；於 `git archive <base>` 副本重跑輸出與證據檔逐列相同；「名冊未更新」態必回 `[超出每輪上限]`（有鑑別力），「名冊已更新」態回空；款(12) 未兌現態必回 `[到期未下修]`，兌現後回空 | MU-LD0-38：在副本把 `test_adr_xplat001_c1c2_lock.py` 的 `_REPIN_NET_CAP_SCHEDULE` 末列 `(214, 515)` 改 `(214, 5150)` → 腳本輸出與證據檔不同（紅） | 13-7-1、13-7-E-1 |
| R-LD0-25 | 證據檔載明標籤規則：重釘標籤不得超前帳本當前輪（`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`；當前輪＝`python tools/check_handoff_carriers.py` 首行）⇒ 產品輪沒有自己的 R 系列證據檔時走 S-A；S-B 僅在當前輪因其他工作前進後才可用 | MU-LD0-39：`DEL /TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound/ <證據檔>` | 13-7-2 |

#### H P0 基準與零侵入（D8；PRD AC-LD-02-6、AC-LD-11-1、§8.1 `G-SIDB-5`）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-26 | `SelfImproving_LedgerDb_P0_Baseline.md` 記（C5 的必有列）：基準 commit（含程序）、`SelfImproving_Protocol/` 三檔各自的位元組數與 sha256、`params.fingerprint()`、`CHECK_RULES_REV`、`items=33` 十處釘的逐行座標、`si check`（file 模式）的取證程序與期望（rc 0、`items=33`、尾行含基準指紋）、skip 摘要基準（`[skip census]` 行原文，加 id 集合行去掉方括號標籤後的原文〔標籤帶裸 M 編號，不抄，免撞 D10-1〕，標平台剖面；他平台剖面標 NE 待補） | MU-LD0-40：`DEL /^\|[^\n]*指紋/ <基準檔>`（刪所有含「指紋」的列；`` `指紋` `` 帶反引號者亦中） | 02-6-1、11-1-1 |
| R-LD0-27 | 活值＝基準值（DT，各項取最後一列）：`params.fingerprint()`、協定目錄逐檔 sha256、`CHECK_RULES_REV`＝4；`items=33` 釘逐座標核（GT，AT-LD-02-6-2）；負控：合成副本改 `params.json` 任一鍵→指紋變，還原→相等 | MU-LD0-41：`BYTE docs/06_quality/SelfImproving_Protocol/params.json @mid`；MU-LD0-42：`SUB /^CHECK_RULES_REV = 4/→CHECK_RULES_REV = 5/ tools/lib/selfimproving/params.py`；MU-LD0-43：`SUBALL@row /指紋/ /sha256:[0-9a-f]/→sha256:x/ <基準檔>`（改基準檔指紋列的值）；MU-LD0-55：`WEAKEN fingerprint_of <新測試檔>`（AT-LD-02-6-E-1 自證須紅） | 02-6-1、02-6-E-1 |
| R-LD0-28 | P0 不改：`tools/lib/**`（唯二例外＝收尾單人窗口重釘 `skip_tag_policy.py` 的 `_TREE_FILE_FLOORS` 與 `guard_bucket_policy.py` 的 shrink-only 常數，§5.9 #5、#6；兩者皆非守衛面）、`tools/selfimproving.py`、`tools/probe/**`、`docs/06_quality/SelfImproving_Protocol/**`（含 `params.json`）、三本帳與事件帳本與提案目錄、`.claude/**`、`settings*.json`、守衛面清單檔、`AutoClaude/**`、`AISDLC_SDD/**`、凍結上位文件；`git diff --name-only <base>..<tip>` 對這些路徑零輸出 | MU-LD0-44：副本在 `tools/lib/selfimproving/params.py` 加一行註解並提交 → G-P0-1 的「不得變更」子檢查紅 | 02-6-E-2、D9-1 |
| R-LD0-29 | file 模式 `python tools/selfimproving.py check`：rc 0、首行 `si-check rows=<N> items=33`、尾行 `overall=PASS rc=0 fingerprint=<基準指紋>`；`items=33` 十處釘與 `CHECK_RULES_REV`＝4 釘（`test_selfimproving_p3_meta.py:292`）於 P0 **零變動**（鎖檔位元組同 base） | MU-LD0-45：clone 副本 `SUB /"params\.coupling", //→/ tools/lib/selfimproving/check.py`（刪項目清單一項；乾跑實測首行變 `items=32`）→ G-P0-9 紅 | 02-6-2 |

#### I 命名紀律與流程件（D9、D10）

| R | 條文 | 突變（轉紅） | AT |
|---|---|---|---|
| R-LD0-30 | P0 全部交付文件（8 個 ADR、Architecture 草稿、三份證據檔、`RL` 的兩新格列）不含**裸** `M1`～`M7` 字樣（判準 `(?<![-\w])M[1-7](?!\d)`，反引號內也算）；§8.1 機器閘稱 `G-SIDB-n`、量測窗稱 `MEAS-Mn`、skip 政策稱 `SKIP-M6`；本檔自身不在掃描集內（檔頭與 §5.1.1 需引用 PRD 原稱） | MU-LD0-46：在任一 ADR 追加一行「進場須過 M2」→ D10-1 紅；MU-LD0-57：`WEAKEN bare_m_hits <新測試檔>`（D10-1 的合成正反例自證須紅） | D10-1 |
| R-LD0-31 | P0 新增 `tools/tests` 測試檔恰 1 支 `test_selfimproving_ledgerdb_p0.py`（≤3 的上限內）；純標準庫（AST 檢查 import ⊆ 標準庫 ∪ `lib.selfimproving.params` ∪ `test_root_module_layout` ∪ `_selfimproving_fixtures` ∪ `_stdio_utf8`；後者只供 `__main__` 區塊的獨立執行保護，先例 `test_archive_defect_log.py:4067`）；測試函式以 AT 底線形命名；類別 docstring 第一句指名受測檔路徑；每行顯示寬度 ≤100；`ruff check --no-cache` 全規則清零；`__main__` 守衛為最後一個頂層敘述；註解與 docstring 不含超前輪號（> 帳本當前輪） | MU-LD0-47：副本該檔加 `import yaml` → G-P0-11 的 AST 檢查紅；MU-LD0-48：加一行 130 寬註解 → ruff E501 紅；MU-LD0-56：把該檔兩行 import 對調成未排序（I001）→ `ruff check --no-cache` 紅 | D9-2 |
| R-LD0-32 | 重釘由收尾單人窗口一次做完 §5.9 表所列各鎖，最後一次 `--print-guard-lines` 為 `+0`、`逐檔漂移 0 支`；`ruff check tools/ .claude/hooks/`、`compileall`、`run_root_unittests` 全綠；`git diff --name-only` 不含守衛面 | MU-LD0-49：副本新增測試檔但不重釘 → `test_adr_xplat001_c1c2_lock` 的 `[新增]`／`[成長]` 款紅（G-P0-12 預期此紅，作為「重釘前必紅」的證據） | D9-3 |

## 契約節（P0 的「契約」＝七份交付物的必要結構；本節為真相，交付文件不得與它不同）

P0 沒有 API 或 CLI 輸出 schema；它交付的是文件與基準，後續階段的實作棒與審查者「消費」它們。故契約寫成「必要結構」：下列每一格的字樣是 AT 的判準，交付文件可以寫得更多，不可以缺。**字樣清單只在本節（單一家）；R 條文與 AT 一律引用本節，不另列。**

### C1 Root_Layout 的兩格、一列、一組登記（R-LD0-01～04）

**C1.1 `## 2.` 落點表加兩列**（欄＝`內容｜落點｜規則`，沿既有三欄；下為「必要字樣」骨架，實作棒可潤飾措辭、不可缺字樣）：

| 內容（首格必含） | 落點（必含） | 規則欄必含字樣（13 個，逐項各至少出現一次） |
|---|---|---|
| `PG 專屬契約測試` | `` `tools/tests_pg/` ``（兄弟目錄；檔名 `test_<module>_<topic>.py`） | `WHY`、`SKIP-M6`、`guardrail_cli`、`750`、`≤4`、`≤3`、`不計入`（句意：每階段 ≤4 檔，不計入 `tools/tests` 的每階段 ≤3 檔）、`行數棘輪`（句意：不受其管轄，只數 `tools/tests/*.py`）、`skip 政策`（句意：不受其管轄）、`run_root_unittests`（句意：不在 discover 根內）、`ruff`（句意：E501 豁免只涵蓋目錄名 `tests`）、`SI_TEST_PG_DSN`、`SI_TEST_PG_REQUIRED` |
| `套件內 SQL 遷移資料目錄` | `` `tools/lib/<module>/sql/` ``（`V<NNN>__<slug>.sql`；資料目錄，非子套件） | `WHY`、`V<NNN>__`、`UTF-8`、`LF`、`只追加`、`MIGRATION-CHECKSUM`、`不含密碼`、`PGPASSFILE`、`non_evolvable_globs`、`*.py`（句意：能力登記只掃套件根層 `*.py`，故資料目錄不造成鎖的盲區）——共 10 個 |

**C1.2 `## 1.` 目錄地圖加一列**：首格含 `` `tools/tests_pg/` ``，職責欄含「PG 專屬」與「不進 runner discover 根」，權威指引欄指向本檔 §2。

**C1.3 `## 3.` SelfImproving 登記列補登記**：只登**已存在**的檔：`tools/tests/test_selfimproving_ledgerdb_p0.py`、`docs/02_architecture/ADR-SIDB-*.md`（glob，落點鎖支援 `*`）、`docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md`、`docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md`、`…_P0_Baseline.md`、`…_P0_Ratchet_PreRun.md`。**禁止**在 P0 登記 `tools/tests_pg/`、`tools/lib/selfimproving/sql/`、任何 `dal_*.py`（磁碟上尚無；`registry_problems` 會對每個找不到的路徑紅，見 R-LD0-04）。⚠ 陷阱：`test_root_module_layout.py` 只解析 `## 3.` 節的六欄資料列；`## 2.` 的格不被它檢查——C1.1 的字樣由本檔 DT 的 AT-LD-11-4-1、-2 承載，不是由落點鎖承載。

### C2 ADR 檔（R-LD0-09～13；內容細表見 §5.2）

**檔名**：`docs/02_architecture/ADR-SIDB-00N-<slug>.md`，`N`＝1～8，`<slug>` 取 §5.2.1 表的「slug」欄（小寫 ASCII 與連字號）。PRD 文內的「ADR-SIDB-01」是簡稱；檔案採三位數（沿 Root_Layout §2 的 `ADR-<MOD>-NNN-<slug>.md` 與 `ADR-AGT-001` 先例）。

**檔內結構（依序；標題文字逐字）**：

```
# ADR-SIDB-00N：<中文標題>（PRD 簡稱 SIDB-0N）
## 狀態            （`Accepted` ｜ `Accepted（階段性：<條件>）` ｜ `Superseded…`；日期；決定者＝掌舵者裁決座標或「主控依 PRD §9.5 轉正式」）
## 脈絡            （PRD 座標、現況事實與其座標）
## 選項與代價      （每選項一行 `- 選項 <標籤>：…`，其後一行 `- 代價：…`；計數規則見 §5.1.2）
## 決定            （採用的選項、理由、被否決選項為何否決）
## 再開症狀        （≥1 條；每條含 ≥1 個反引號 token＝可觀測事件）
## 連動面          （被取代的既有規格／被連動的文件與階段；refreeze 鍵）
```

### C3 Architecture 草稿（R-LD0-14、15）

`docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md` 含：檔頭（性質＝草稿、P0 不套用、套用路由）、三塊補丁（`## 補丁 §7.2 資料所有權`、`## 補丁 §9.4 環境變數`、`## 補丁 §10.3 SelfImproving 鏡像與寫入載體`），每塊含行首字樣 `目標檔：`、`插入文：`、`生效階段：`、`路由：`；§7.2 與 `AgentConsole/docker/README.md`〈4.3〉兩塊另含小標 `### B 方案（Console PG 加 si schema）` 與 `### C 方案（專屬 PG 容器）`。座標於 `<base>` 重核：`Architecture.md:612-618`（§7.2 表，末列為 `issue_priority`）、`:854-870`（§9.4 環境變數表）、`:944-956`（§10.3）。

### C4 勘誤案（全備案；R-LD0-16～19；案文內容契約見 §5.1.3）

**案文檔** `docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md`：檔頭（性質＝備案、P0 不套用；路由指向本檔〈凍結後修訂路由〉）＋ E-1～E-7 逐條 ＋ `## 不勘誤` 節（`#6`、`#8`、`#9` 各一段）。**逐條格式（機器可解析，〈附錄 A〉的腳本依此）**：每條以 `### E-<n>` 為小標，其下欄位各占一行、格式 `- <欄位>：<內容>`（內容單行、不含換行）；七個欄位標籤逐字為 `目標文件`、`原文座標`、`原文`、`訂正文`、`生效階段`、`套用階段`、`理由`；`原文` 取 `<base>` 版目標文件該行的逐字子字串（§5.1.3）。**P0 零凍結文件變動**：`SelfImproving_PRD.md`、`Issue_Center_PRD.md` 不改；各條於「套用階段」由該階段鍵套用並 `spec-refreeze`。

### C5 P0 基準檔（R-LD0-26～29；值見 §5.6）

`docs/06_quality/SelfImproving_LedgerDb_P0_Baseline.md`：一張「基準列」表，欄＝`項｜值｜取得指令｜取得時 HEAD`；必有列：`基準 commit`、`協定目錄 metrics.md`、`協定目錄 params.json`、`協定目錄 research_sources.json（排除於指紋）`、`指紋`、`CHECK_RULES_REV`、`items=33 釘（10 處）`、`si check 取證程序`、`skip 摘要（win32）`、`SKIP-M6（win32）`（記該 id 集合行**去掉方括號標籤後**的文字）；變動只准追加新列（C 欄「取代」前列，不覆寫）；同一項多列時，DT 取檔內最後一列。

### C6 棘輪預演檔（R-LD0-23～25；值見 §5.5）

`docs/06_quality/SelfImproving_LedgerDb_P0_Ratchet_PreRun.md`：①檔頭（HEAD、唯讀聲明）②預演腳本全文（一個 ` ```python ` 區塊；只 import 鎖檔、不寫檔、不呼叫 git；入口為 `python <腳本> ` 於 repo 根）③輸出表（S-A 表；S-B 表含「該輪上限」「款(12)」欄）④〈標籤規則〉節（R-LD0-25）⑤〈結論〉節（需入名冊的階段、上限上修量、款(12) 兌現動作）⑥〈乾跑選檔名單〉節（D2 證據：§5.3.2 選檔規則所得名單，起草時實跑並驗過的 50 檔；重跑時 QA 可擴充、不可縮減）。

### C7 新測試檔（R-LD0-31）

`tools/tests/test_selfimproving_ledgerdb_p0.py`：標準庫 only（外加 `lib.selfimproving.params`、同目錄 `test_root_module_layout` 與 `_selfimproving_fixtures` 的唯讀 import；`tools/_stdio_utf8.py` 只准出現在 `__main__` 區塊，供獨立執行時的 UTF-8 stdio 保護）；類別與載具對照見 §3.1；每個 DT 的 AT 一個測試函式；被測目標（Root_Layout 文件、ADR 檔、基準檔）以 `ROOT = Path(__file__).resolve().parents[2]` 取得，**不依賴 git、不依賴 `build/`、不依賴 PG、不依賴網路**。**瘦身原則**：只寫時間穩定謂詞（見 §2 規則 6）；一次性驗收只以 `p0_acceptance_problems` 函式形態存在、由 G-P0-13 呼叫。

## 1. AC → AT 映射表

### 1.1 P0 範圍的 AC 與交付項（FR-LD-00 為 TCS 自訂）

每個 AC 或交付項各有至少一個正向 AT（`AT-LD-<FR>-<AC>-<n>`），並盡量有一個反向 AT（`AT-LD-<FR>-<AC>-E-<n>`；負控、邊界或錯誤路徑）。**例外（無獨立反向 AT）**：AC-LD-11-1（借 AT-LD-02-6-E-2 的「不得變更」子檢查作負控）、D5（反向由突變 MU-LD0-27～32 承載）、D9（MU-LD0-47～49、56）、D10（D10-1 自帶合成正反例；MU-LD0-57）。「載具」欄為 §3.1 的載具代碼。

#### FR-LD-02　儲存層（Store）與模式解析 — 本鍵只涵蓋 AC-LD-02-6 的「P0 基準」半

| AC | 重點（P0 範圍） | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-LD-02-6 | 建立並凍結 P0 基準：協定目錄位元組、`params.fingerprint()`、`CHECK_RULES_REV`＝4、`items=33` 十處釘；file 模式 `si check` 不變。（P1～P4 出口的比對半不在本鍵，見 §1.2） | AT-LD-02-6-1、AT-LD-02-6-2 | AT-LD-02-6-E-1、AT-LD-02-6-E-2 | DT、GT |

#### FR-LD-11　離線、CI 與測試替身 — AC-LD-11-1 的「P0 基準」半與 AC-LD-11-4 全條

| AC | 重點（P0 範圍） | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-LD-11-1 | 記錄 skip 摘要基準（win32 剖面；`skip_id_ledger.json` 位元組不動）；P1 出口比對半不在本鍵 | AT-LD-11-1-1 | （負控由 AT-LD-02-6-E-2 的「不得變更」子檢查承載：`skip_id_ledger.json` 在不得變更集合內） | GT |
| AC-LD-11-4 | Root_Layout §2 先修（兩格＋WHY）、以 `tools/tests` 為根的掃描器普查、`tools/tests_pg/` 管轄（LOC 分級／不受行數棘輪、SKIP-M6、skip 政策）、每階段檔數上限 | AT-LD-11-4-1、AT-LD-11-4-2、AT-LD-11-4-3、AT-LD-11-4-4、AT-LD-11-4-5 | AT-LD-11-4-E-1、AT-LD-11-4-E-2、AT-LD-11-4-E-3 | DT、GT |

#### FR-LD-13　閘門、驅動器與文件連動 — AC-LD-13-5（P0 半）、AC-LD-13-7

| AC | 重點（P0 範圍） | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| AC-LD-13-5 | A.4 普查定稿：逐列座標重核、處置、三項逐斷言判、重跑普查無遺漏、帳本盲實驗。（P3a 出口處置落地、P3b 前後同組測試綠不在本鍵） | AT-LD-13-5-1、AT-LD-13-5-2、AT-LD-13-5-3 | AT-LD-13-5-E-1 | GT |
| AC-LD-13-7 | 棘輪預演（唯讀）：預演表入檔、重跑相同、需入名冊階段與上修量標出 | AT-LD-13-7-1、AT-LD-13-7-2 | AT-LD-13-7-E-1 | GT、DT |

#### FR-LD-00　P0 交付項（TCS 自訂；PRD §8 P0 列、§11 P0 機械可驗欄；PRD 無對應 AC，見 §7.3）

| 項 | 重點 | 正向 AT | 反向 AT | 載具 |
|---|---|---|---|---|
| D3 | ADR-SIDB-001～008 成檔：命名連號、六節結構、選項與代價、決定對 PRD §9.5、ADR-003 的 SQL 草稿與逐表守衛矩陣、SQL 於 PG18 烟測 | AT-LD-00-D3-1、AT-LD-00-D3-2、AT-LD-00-D3-3、AT-LD-00-D3-4、AT-LD-00-D3-5 | AT-LD-00-D3-E-1 | DT、GT |
| D4 | Architecture 草稿三塊補丁；Architecture.md 與 docker README 位元組不變 | AT-LD-00-D4-1、AT-LD-00-D4-2 | AT-LD-00-D4-E-1 | DT、GT |
| D5 | 勘誤案（全備案）：案文結構、`原文` 為 base 版逐字子字串、凍結上位文件零變動、六鍵與議題中心兩鍵聯集摘要等於現檔 | AT-LD-00-D5-1、AT-LD-00-D5-2、AT-LD-00-D5-3、AT-LD-00-D5-4 | （見上方例外：D5-3、D5-4 的「位元組不變」即負向判準；MU-LD0-27～32） | DT、GT |
| D9 | 流程件：允許變更集合、新測試檔屬性、重釘儀式 | AT-LD-00-D9-1、AT-LD-00-D9-2、AT-LD-00-D9-3 | （見上方例外：MU-LD0-47～49） | GT |
| D10 | 三處 M 編號撞名的命名紀律 | AT-LD-00-D10-1 | （見上方例外：MU-LD0-46） | DT |

D1、D2 的 AT 掛在 AC-LD-11-4；D6 掛在 AC-LD-13-5；D7 掛在 AC-LD-13-7；D8 掛在 AC-LD-02-6 與 AC-LD-11-1（見 §3.2 各列「項」欄）。

### 1.2 不在本鍵的 PRD AC（53 條；階段歸屬依 PRD §8 階段表與 §11 出口列）

| 階段 | AC | 條數 | 備註 |
|---|---|---|---|
| P1（影子） | AC-LD-01-1～01-4；02-1～02-4；03-1～03-5；04-1～04-3；05-1～05-6；11-2、11-3 | 4＋4＋5＋3＋6＋2＝24 | §11 P1 列：「AC-LD-01～05 綠」。另：AC-LD-02-6 與 AC-LD-11-1 的**比對半**（P1～P4 每個出口與 P0 基準相比；11-1 為 P1 出口的 skip 摘要比對）不重複計入下列條數；AC-LD-06-5 的能力登記實質守衛自 P1 起（新 `dal_*.py` 一出現即受既有能力登記鎖管），驗收列 P3a |
| P2（讀） | AC-LD-02-5；07-1、07-2；08-1～08-6 | 1＋2＋6＝9 | §11 P2 列：「AC-LD-07、08 綠」；02-5 於「P2 出口」驗（AC 本文） |
| P3a（寫） | AC-LD-06-1～06-5；09-1～09-4；12-1～12-3；13-1、13-2、13-3、13-6 | 5＋4＋3＋4＝16 | §11 P3a 列：「AC-LD-06、09、12、13-1～13-6 綠」；13-4 本文為 P4 出口（見 §7.2 勘誤 1-9）；13-5 的 P3a 半（處置落地）亦屬 P3a、不重複計入 |
| P3b（切換） | AC-LD-10-1～10-3 | 3 | §11 P3b 列 |
| P4（清理） | AC-LD-13-4 | 1 | §11 P4 列 |
| **合計** | | 24＋9＋16＋3＋1＝**53** | PRD 58 條＝本鍵 5 條（02-6、11-1、11-4、13-5、13-7）＋不在本鍵 53 條；機械核對見 §6.1 |

## 2. 可自動化 AT 格式規範

**編號與命名**：AT 編號 `AT-LD-<FR>-<AC>-<n>`（正向）、`AT-LD-<FR>-<AC>-E-<n>`（反向）；FR-LD-00 的交付項以 `D<k>` 代替 `<AC>`（`AT-LD-00-D3-1`）。測試函式名一律以 AT 編號的底線形開頭：

| 載具 | 命名 | 例 |
|---|---|---|
| DT 根層 unittest | `test_AT_LD_<FR>_<AC>_<n>_<slug>`、`test_AT_LD_<FR>_<AC>_E_<n>_<slug>`（slug 為 ASCII 蛇形；**不得以 `test_AT_3`、`test_AT_2` 開頭**——`test_selfimproving_p3_meta.py` 與 `p2_meta` 的錨定鎖會把數字前綴當自己的） | `test_AT_LD_11_4_1_root_layout_has_the_pg_contract_test_cell` |
| GT 審查閘 | 無測試函式；由 SCG-4 通過標準的 `G-P0-n` 指令承載，AT 的 Then 欄指名 G 編號與期望輸出 | `AT-LD-11-4-4`→G-P0-4 |

**判定指令樣板**（`<id>` 為 AT 編號的底線形，例 `AT_LD_11_4_1`；一律在 repo 根執行；rc 先存變數再讀）：

- DT：`python -m unittest discover -s tools/tests -p "test_selfimproving_ledgerdb_p0.py" -k <id>_`
- GT：見 SCG-4 通過標準的 G-P0 表。

**零測試視為失敗**：`Ran 0 tests` 一律 FAIL（`-k` 無命中＝該 AT 未實作）；跳過（skip）不算通過；DT 不得含任何 `skipUnless`／`skipIf`（P0 文件與基準檢查沒有「環境缺件」可言）。

**AT 區塊樣式（壓縮成表列；三項後設資料由載具代碼與樣板推得）**

```
# AT-LD-11-4-1                         # 對應 AC: AC-LD-11-4（PRD §9.4 :223；R-LD0-01）
# 測試類型: Doc-structure              # 自動化工具: unittest（標準庫；讀 Root_Layout 文字）
# 判定指令: python -m unittest discover -s tools/tests -p "test_selfimproving_ledgerdb_p0.py" -k AT_LD_11_4_1_
Given Root_Layout 的 ## 2. 節
When  以 §5.1.2 的解析函式取出首格含「PG 專屬契約測試」的列
Then  恰一列；落點格含 `tools/tests_pg/`；規則格含 C1.1 的全部必要字樣；rc 0
```

**測試檔規則**（單一新檔 `test_selfimproving_ledgerdb_p0.py`）：

1. 每個 `TestCase` 類別的 docstring **第一句**指名受測檔路徑（受測物若確為文件，分桶棘輪歸 `prose` 是正確分類；但 `prose` 桶 shrink-only，成長須帶四方複審裁決，見 §5.9 #5，故本檔必須瘦身）。
2. 每行顯示寬度 ≤ 100（CJK 算 2）；ruff 全規則（`tools/ruff.toml`：E,F,I,UP,W,S102）與 `--isolated --select E501` 皆清零（G-P0-11）。
3. 假 DEF 編號一律 `DEF-999-nnn` 或中性字串；不得寫 `OBS-SI-` 接數字的片段；不得出現未登記的 `DEF-…` 字面（`test_defect_id_reference_integrity` 掃全 repo）。
4. 不得出現「測試摘要字樣＋4 位數字」同行（基線站點鎖：`passed`、`skipped` 字樣與 4 位數字不得同行）；註解與 docstring 不得含超前輪號（> 帳本當前輪，`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`），合成語料用 `round-label-ok`。
5. 不新增守衛碼、不改 `.claude/**`、不改 `settings*.json`；不讀 `build/`、不呼叫 git（DT 必須在 `git archive` 副本與 CI 內同樣可跑）。
6. **只寫時間穩定謂詞**：P1 起任何會隨階段合法改變的斷言都是必誤紅，不得入 DT。可入 DT：格結構（Root_Layout 兩格的字樣）、ADR 六節結構與命名、基準等式（取各項最後一列）、案文結構、合成自證（紅綠兩側）。不可入 DT（一律 GT）：「恰 N 檔」「不得存在某路徑」、ADR 與草稿的內容字樣、`items=33` 釘的處數、對 `<base>` 的逐字比對。

**突變規格**：見 R 條文節的突變語言。每個 R 條文有至少一個會使所列 AT 或 G 閘轉紅的最小改動：「killed」＝所列 AT **或**所列 G 閘任一轉紅（R 條文表的 AT 欄可直接列 `G-P0-n`，表示該條只被閘門承載，如 R-LD0-04 的 MU-LD0-08 只會被 G-P0-3 的 `test_root_module_layout` 殺）；倖存者補 AT 並勘誤。

## 3. AT 完整清單

### 3.1 載具代碼與判定指令

| 代碼 | 載具 | 檔案／指令 | 判定指令樣板 | 持有面 | AT 數 |
|---|---|---|---|---|---|
| DT | 根層 unittest（標準庫） | `tools/tests/test_selfimproving_ledgerdb_p0.py`（新；類別：`TestRootLayoutCells`、`TestAdrFiles`、`TestAdrNegativeControls`、`TestArchitectureDraft`、`TestErrataCase`、`TestBaselineAndFingerprint`、`TestNamingDiscipline`、`TestPreRunEvidence`） | `python -m unittest discover -s tools/tests -p "test_selfimproving_ledgerdb_p0.py" -k {id}_` | 根層 | 14 |
| GT | 審查閘（指令型 AT，不入單元測試） | SCG-4 通過標準的 G-P0-1～G-P0-13 | 見該 AT 的 Then 欄所指 G 編號 | 共同 | 23 |

DT 的 14 個 AT 預估收集數 14～18（`subTest` 不增收集數；每個 AT 至多一個輔助自證測試）。

### 3.2 AT 清單（依 FR；每列＝一個 AT）

Given（夾具）與 Then（判定）；R 條文對應見 R 條文表的 AT 欄與 §6 RTM。夾具名詞（RL、A3、基準檔…）定義於 §5。「項」欄＝所屬交付項（D1～D10）。

#### FR-LD-02　AC-LD-02-6（P0 基準半）

| AT | 項 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-LD-02-6-1 | D8 | DT | 真樹：基準檔 `SelfImproving_LedgerDb_P0_Baseline.md`、`docs/06_quality/SelfImproving_Protocol/` 三檔、`tools/lib/selfimproving/params.py` | 基準檔各項（同項多列取最後一列，C5）的值與活值相等：三檔 sha256 與位元組數、`params.fingerprint(ROOT, params)` 的字串、`CHECK_RULES_REV`；任一不等回報哪一列（R-LD0-26、27）。`items=33` 釘不在此（時間不穩，歸 AT-LD-02-6-2 的 GT） |
| AT-LD-02-6-2 | D8 | GT | `git clone --no-local <repo> <short>` 後 `git checkout <base>`（含歷史；🔴 不可用 `git archive` 副本：無 `.git` 時依 git 歷史的 `history.migration`、`row.fixed_sha` 等 7 項會 FAIL，乾跑實測副本上 `si check` rc 1），清除 `SI_*`、`AUTOSDD_*` 環境變數，工作目錄＝副本根 | G-P0-9：(a) `python tools/selfimproving.py check` rc 0；首行 `si-check rows=<N> items=33`；尾行含 `overall=PASS rc=0 fingerprint=<基準指紋>`；輸出（去除 `rows=` 數字與時間戳行後）sha256 記入基準檔「si check 取證程序」列；(b) `items=33` 釘逐座標核（基準檔記的座標，其檔仍含關鍵字，行號僅提示；排除本案測試檔自身）（R-LD0-27、29） |
| AT-LD-02-6-E-1 | D8 | DT | 合成樹（暫存目錄）：複製真樹的 `SelfImproving_Protocol/` 三檔 | 對合成樹呼叫 `params.fingerprint(tmp, params)`：與真樹相等；改 `params.json` 任一位元組→不等；還原→相等；改 `research_sources.json`→**仍相等**（排除於指紋）；改 `metrics.md`→不等（R-LD0-27） |
| AT-LD-02-6-E-2 | D8 | GT | `git diff --name-only <base>..<tip>`（本鍵 commit 範圍） | G-P0-1 的「不得變更」子檢查：對 §5.7.2 的路徑清單零輸出（R-LD0-28） |

#### FR-LD-11　AC-LD-11-1（P0 基準半）與 AC-LD-11-4

| AT | 項 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-LD-11-1-1 | D8 | GT | 於本機（win32 剖面）跑 `python tools/run_root_unittests.py` 全套一次（收尾單人窗口；不接管線，rc 先存） | G-P0-10：基準檔「skip 摘要（win32）」列含 `[skip census] tools/tests@win32 共 <N> 支：…` 原文；「`SKIP-M6`（win32）」列含該 id 集合行**去掉方括號標籤後**的原文（形如 `tools/tests@win32：✅ 集合關係成立（本次 skip <N> 支）`）——標籤字樣本身不抄，因它帶裸 M 編號，會撞 AT-LD-00-D10-1 對基準檔的掃描；`docs/06_quality/skip_id_ledger.json` 位元組數與 sha256 記入；他平台剖面（darwin、linux）標 `NE（P1 前由該平台補錄）`，不得填猜測值（R-LD0-26） |
| AT-LD-11-4-1 | D1 | DT | `RL` | `## 2.` 節恰一列首格含「PG 專屬契約測試」；落點格含 `` `tools/tests_pg/` ``；規則格含 C1.1 PG 列的全部 13 個必要字樣（R-LD0-01） |
| AT-LD-11-4-2 | D1 | DT | `RL` | `## 2.` 節恰一列首格含「套件內 SQL 遷移資料目錄」；落點格含 `` `tools/lib/<module>/sql/` ``；規則格含 C1.1 SQL 列的全部 10 個必要字樣（R-LD0-02） |
| AT-LD-11-4-3 | D1 | DT | `RL` | `## 1.` 有 `` `tools/tests_pg/` `` 列；`## 3.` 的 SelfImproving 列於「測試」或「資料／文件」欄登記 C1.3 的各已存在路徑。（「登記路徑必存在」由 `registry_problems` 自己守，本 AT 不重複；亦不寫「不得登記某路徑」，那是 P1 起必誤紅的斷言。Architecture 草稿日後若被移除〔P1 起才可能〕，其 `## 3.` 登記須同批取消，本 AT 只對磁碟上仍存在的草稿要求登記）（R-LD0-03） |
| AT-LD-11-4-4 | D2 | GT | §5.3.2 乾跑置位實驗：`git archive <base>` 三副本 base／probe／ctrl（§5.3.2 實驗副本規則：展開後 `git init`＋提交；兩輪）；probe 加 `tools/tests_pg/test_selfimproving_dal_pg_probe.py` 與 `tools/lib/selfimproving/sql/V000__probe.sql`；選檔規則見該節 | G-P0-4：選檔規則所得各檔的 base 與 probe 結果逐檔相同（rc、收集數、失敗集合；起草時驗過 50 檔）；第二輪（基線紅者＋棘輪類 8 檔；起草時 33 檔）同樣逐檔相同；`check_loc_budget.py --json` 在 probe 副本的根層報表含該 probe 檔且 tier＝`guardrail_cli`（budget 750）；`ruff check tools/` 在 probe 副本對 probe 的 152 寬行回 E501、base 副本回 `All checks passed!`；`compileall` 兩副本 rc 0（R-LD0-06、07） |
| AT-LD-11-4-5 | D2 | GT | §5.3.1 普查表（每列含座標）；被測副本已提交（突變副本規則，SCG-4 通過條件 3） | G-P0-4 的子步驟：逐列以 `git grep -n -F <關鍵字> <HEAD> -- <檔>` 驗座標與關鍵字於當前 HEAD 仍成立；表內「判定」欄值只能是 `不涵蓋`、`涵蓋（受管）`、`涵蓋（無反應）`、`需 P1 處置` 四者**之一**，補充說明只准寫在「依據」欄；`需 P1 處置` 的列須在 §7.3 有對應輸入；缺列或關鍵字自全檔消失＝紅（R-LD0-05） |
| AT-LD-11-4-E-1 | D1 | DT | 合成 SSOT（暫存目錄）：`## 2.` 缺 PG 列、缺 SQL 列、兩列都有、規則格缺 `SI_TEST_PG_REQUIRED` 四種變體 | §5.1.2 的解析函式對四變體各回報「缺格」或「缺字樣」並點名；對兩列俱全的對照組回空（紅綠自證，沿 `test_root_module_layout` 的合成樹體例） |
| AT-LD-11-4-E-2 | D1 | DT | 合成樹：磁碟無 `tools/tests_pg/`，`## 3.` 登記列卻含 `` `tools/tests_pg/` `` | `registry_problems(synth)` 回非空並點名該路徑（把「P0 不得先登記」陷阱鎖成紅綠自證）；對照組（登記一個真存在的路徑）回空 |
| AT-LD-11-4-E-3 | D2 | GT | 第三副本 `ctrl`：base＋同一支 probe 放進 `tools/tests/`（非兄弟）；`git init` 並提交 | G-P0-4 的對照步驟：`test_adr_xplat001_c1c2_lock.py` 在 `ctrl` 副本出現新增失敗（行數棘輪款）、`test_subprocess_encoding_hygiene` 的 E501 存量棘輪新增失敗；與 base／probe 的結果不同（證明兄弟目錄的「不反應」是目錄選擇造成，非掃描器失明）（R-LD0-08） |

#### FR-LD-13　AC-LD-13-5（P0 半）與 AC-LD-13-7

| AT | 項 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-LD-13-5-1 | D6 | GT | `<base>`；§5.4.1 的 A.4 表與 §5.4.2a、§5.4.2b、§5.4.2c 三表 | G-P0-5：(a) PRD `[C-17]` 兩條 Grep 重跑，命中檔案集合 ⊆ A.4 ∪ §5.4.1b ∪ §5.4.2a／b（起草時：`tools/tests` 9 檔 156 處、`AutoClaude/tests` 2 檔 9 處）；(b) `fx.ROOT` 型根讀取普查（§5.4.4(b)；起草時 22 行／11 檔）命中檔 ⊆ A.4 ∪ §5.4.2a／b／c；(c) A.4 表每列的座標與關鍵字於 `<base>` 成立（R-LD0-20、21） |
| AT-LD-13-5-2 | D6 | GT | `git archive <base>` 兩副本（對照 B、帳本盲 K；皆 `git init`＋提交）；K 移除六類帳本路徑（§5.4.3） | G-P0-5：兩副本各跑 28 個測試檔（§5.4.1 的 10 檔＋§5.4.2a 的 13 支測試檔＋§5.4.2b 的 2 檔＋§5.4.2c 的 3 檔）：K 相對 B 新增的失敗所屬測試檔 ⊆ A.4「讀真實內容」的 10 檔 ∪ §5.4.2b 的 2 檔；§5.4.2a 與 §5.4.2c 的 16 檔在 K 與 B 結果相同（R-LD0-22） |
| AT-LD-13-5-3 | D6 | GT | A.4 表 | G-P0-5：每列「處置」∈ 四值、「落地階段」∈ {P1、P2、P3a、P3b、P4、不需}；PRD 三項「TCS 逐斷言判」（`issuemap:21,145`、`measure_probe:450`）各有逐斷言判定且與 §5.4.1 一致；表內無「待查」「TBD」字樣（R-LD0-20） |
| AT-LD-13-5-E-1 | D6 | GT | 同 -2 的副本；對照：不移除帳本的副本 | G-P0-5：移除帳本的副本至少一支 A.4「讀真實內容」測試轉紅（非空轉）；不移除的對照副本零失敗（兩者皆須成立，否則實驗無鑑別力，R-LD0-22） |
| AT-LD-13-7-1 | D7 | GT | `git archive <base>` 副本（含 `.git`）；預演腳本（取自證據檔的 ` ```python ` 區塊） | G-P0-6：腳本於副本跑 rc 0，輸出與證據檔輸出表逐列相同；`repin_growth_problems(real_log)` 與 `repin_cost_ratchet_problems()` 回空（基準）（R-LD0-23、24） |
| AT-LD-13-7-2 | D7 | DT | 證據檔 `SelfImproving_LedgerDb_P0_Ratchet_PreRun.md` | 檔存在；含 C6 的六個部分標題字樣；含 `S-A`、`S-B` 兩情境與 P0、P1、P2、P3a、P3b、P4 六階段名；含字樣 `repin_growth_problems`、`repin_cost_ratchet_problems`、`TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`、`_REPIN_APPROVED_ROUND_OVERAGE`；含 ` ```python ` 區塊且區塊內無 `write_text`、`open(`、`subprocess`（唯讀的機械面，R-LD0-23、25） |
| AT-LD-13-7-E-1 | D7 | GT | 同 -1 | G-P0-6：S-A「名冊未重登」每格回傳含 `[超出每輪上限]`、重登後每格回空；S-B 的「無名冊項」於 P1、P2、P3a、P3b 含 `[超出每輪上限]`、加名冊項後回空，款(12) 未兌現態於 P1、P3a、P4 含 `[到期未下修]`、兌現後回空（函式有鑑別力；R-LD0-24） |

#### FR-LD-00　D3 ADR、D4 Architecture 草稿、D5 勘誤案、D9 流程件、D10 命名

| AT | 項 | 載具 | Given／夾具 | Then／判定 |
|---|---|---|---|---|
| AT-LD-00-D3-1 | D3 | DT | `docs/02_architecture/` | `ADR-SIDB-001`～`008` 各恰一檔；檔名符合 `ADR-SIDB-00[1-8]-[a-z0-9-]+\.md`；檔內首個 `# ` 標題符合 C2 格式且其 `00N` 與檔名一致（日後增補 009 以上不紅）（R-LD0-09） |
| AT-LD-00-D3-2 | D3 | DT | 8 個 ADR | 每檔依序含 C2 的六個 `## ` 標題；「選項與代價」依 §5.1.2 選項計數規則 ≥2 個選項、每個選項各有一行 `- 代價：`；「再開症狀」≥1 條、每條含反引號 token；「狀態」值以 `Accepted` 或 `Superseded` 起頭（R-LD0-10） |
| AT-LD-00-D3-3 | D3 | GT | 8 個 ADR；§5.2.1 表 | G-P0-13：`adr_decision_problems` 對 001～008 皆回空——每檔「選項與代價」含該表「必含選項標籤」、「決定」節含該表「決定字樣」；001 的「狀態」節含 `階段性`、`H2`、`H3`，「決定」節含 `單一主力機為真相`（OQ-2 裁決）（R-LD0-11、12） |
| AT-LD-00-D3-4 | D3 | GT | `A3`；§5.2.2 | G-P0-13：`sql_draft_problems(A3)` 回空——含 ≥1 個 ` ```sql ` 區塊；區塊合計含 §5.2.2 列的全部物件字樣；逐表守衛矩陣含 PRD §9.3 的 14 張表名各至少一列、每列分類值 ∈ 四類；含「不重算 `row_hash`」句意字樣；8 個 ADR、Architecture 草稿與三份證據檔不含連線字串字面（`postgres(ql)?://[^<\s]*:[^<\s@]+@` 命中 0，`<YOUR_…>` 佔位符除外）（R-LD0-13） |
| AT-LD-00-D3-5 | D3 | GT | 一次性 PG18 容器（`docker run --rm`，`pgvector/pgvector:pg18`；不碰長駐 `autoclaude_pg`） | G-P0-7：把 A3 的 SQL 區塊依序餵 `psql -v ON_ERROR_STOP=1`：rc 0；再三個負控各 rc≠0 且訊息含對應物件名：(i) 對追加專用表 UPDATE；(ii) 對可變表於無同交易 audit 列時 COMMIT；(iii) 以非擁有者角色 `ALTER TABLE … DISABLE TRIGGER`；另一個正控：經「同交易寫 audit 列」的 INSERT 成功。腳本與輸出摘要存審查報告；容器結束時 `docker rm -f` 並驗不存在（備援改用 `autoclaude_pg` 時須 `DROP ROLE IF EXISTS` 並驗 `pg_roles` 無 `si_%`）（R-LD0-13） |
| AT-LD-00-D3-E-1 | D3 | DT | 合成 ADR 文字（記憶體字串）六種變體：缺 `## 再開症狀`、再開症狀條目無反引號、選項缺「代價：」行、狀態值為 Draft、標題編號與檔名不符、決定節缺指定字樣 | §5.1.2 的 `adr_problems`、`adr_decision_problems` 對六變體各回報對應問題；對合規字串回空（紅綠自證；R-LD0-10、11） |
| AT-LD-00-D4-1 | D4 | GT | Architecture 草稿檔 | G-P0-13：`draft_problems` 回空——含 C3 的三塊補丁標題與每塊四個行首字樣；§7.2 與 docker README 兩塊含 `B 方案`、`C 方案` 小標；§7.2 補丁的目標檔座標字樣含 `Architecture.md:612`、§9.4 含 `:854`、§10.3 含 `:944`（落檔時對 `<base>` 為真；P2、P3 套用後草稿不再受檢，故非 DT）（R-LD0-14） |
| AT-LD-00-D4-2 | D4 | GT | `git diff --exit-code <base> <tip> -- AgentConsole/docs/02_architecture/Architecture.md AgentConsole/docker/README.md` | G-P0-2：rc 0 無輸出；`agentconsole-si-decide`／`-mirror` 的聯集 Architecture 摘要仍等於現檔（R-LD0-15） |
| AT-LD-00-D4-E-1 | D4 | DT | 合成草稿文字五種變體：缺一塊補丁、缺 `生效階段：`、缺 `B 方案`、座標字樣被改、整檔空 | `draft_problems` 各回報對應問題；合規文字回空（紅綠自證） |
| AT-LD-00-D5-1 | D5 | DT | 案文檔 `SelfImproving_LedgerDb_P0_Errata.md` | `errata_problems` 回空：含 E-1～E-7 各一節；每節含七個欄位標籤且各欄值非空；`套用階段` 值以 `P1`、`P2`、`P3a`、`P3b` 之一起頭；E-4 含核准座標欄（佔位 `〈sid／line 由主控填〉` 或已填）；E-6、E-7 的 `目標文件` 為 `Issue_Center_PRD.md`；`## 不勘誤` 節含 `#6`、`#8`、`#9` 三段（R-LD0-16） |
| AT-LD-00-D5-2 | D5 | GT | 案文檔；`git show <base>:<目標文件>` | G-P0-8：案文每條 `原文` 為 `<base>` 版目標文件的逐字子字串（20～200 字元、不含 `\|`、不含裸 M 編號）；E-4 核准座標欄＝佔位或 `sid <uuid> line <n>`（R-LD0-16、17） |
| AT-LD-00-D5-3 | D5 | GT | `SelfImproving_PRD.md`；六鍵 FSM 狀態檔（唯讀；`build/reports/fsm`、`AgentConsole/build/reports/fsm`） | G-P0-8：`git diff --quiet <base> -- docs/01_requirements/SelfImproving_PRD.md` rc 0（零凍結文件變動）；六鍵各取 `frozen_stages` 全部條目 `spec_doc_digests` 的聯集（同鍵後者勝出），PRD 摘要＝現檔 SHA-256；`monorepo-selfimproving` 不在檢查清單且案文載明原因（R-LD0-17、18） |
| AT-LD-00-D5-4 | D5 | GT | `Issue_Center_PRD.md` 與 `monorepo-issue-center`／`agentconsole-issue-center` 狀態檔 | G-P0-8：PRD digest＝`sha256:9765a825973f75722b79268dd827047a712a6db6a694f62f31e9fb90655a9eba`；兩鍵聯集 PRD 摘要仍等於現檔；`git diff --quiet <base> -- docs/01_requirements/Issue_Center_PRD.md` rc 0（E-6、E-7 全備案，R-LD0-19） |
| AT-LD-00-D9-1 | D9 | GT | `git diff --name-only <base>..<tip>`（本鍵 commit 範圍） | G-P0-1：每個路徑 ⊆ §5.7.1 的允許集合；`<tip>` 只含本鍵路徑（R-LD0-28、31） |
| AT-LD-00-D9-2 | D9 | GT | 新測試檔 `tools/tests/test_selfimproving_ledgerdb_p0.py` | G-P0-11：`ruff check --isolated --select E501 --line-length 100 --output-format concise` 與 `ruff check --no-cache`（全規則）皆 rc 0（輸出僅 `All checks passed!`）；AST 走訪 import 集合 ⊆ 標準庫 ∪ {`lib.selfimproving.params`、`test_root_module_layout`、`_selfimproving_fixtures`、`_stdio_utf8`（僅 `__main__` 區塊）}；`tools/tests/` 本輪新增的測試檔恰 1 支；`__main__` 守衛為最後一個頂層敘述；檔內無 `skip`、無超前輪號、無 `OBS-SI-` 接數字、無未登記 `DEF-` 字面（R-LD0-31） |
| AT-LD-00-D9-3 | D9 | GT | 收尾單人窗口重釘完成後 | G-P0-12：§5.9 表的每一道鎖逐項綠；最後一次 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 尾段為 `+0`、`逐檔漂移 0 支`；`ruff check tools/ .claude/hooks/ --no-cache` 與 `compileall` rc 0；`python tools/run_root_unittests.py` rc 0；`<tip>` 的變更不含守衛面（R-LD0-32） |
| AT-LD-00-D10-1 | D10 | DT | 掃描集：8 個 ADR、Architecture 草稿、三份證據檔、`RL` 中首格含「PG 專屬契約測試」與「套件內 SQL 遷移資料目錄」的兩列（本檔自身不在掃描集內；Architecture 草稿若日後被移除〔P1 起才可能〕，自掃描集剔除，其餘檔必須存在） | 以 `(?<![-\w])M[1-7](?!\d)` 掃描全集合，命中 0；對含 `MEAS-M1`、`SKIP-M6`、`G-SIDB-3`、`HM1` 的合成字串命中 0；對含裸 `M2` 的合成字串命中 1（紅綠自證；R-LD0-30） |

## 4. 邊界與錯誤測試規格

下列邊界各自由所列 AT（含反向 AT）覆蓋；實作棒不得因「看起來不會發生」而省略夾具。「覆蓋」欄為 AT 簡碼。

| B | 邊界或錯誤路徑 | 規格（可判定） | 覆蓋 |
|---|---|---|---|
| B-01 | BOM 與行尾 | P0 新增與修改的每份 Markdown：UTF-8 無 BOM、LF only（根 `.gitattributes` 的 `* text=auto eol=lf` 與 `*.md text eol=lf`）。DT 一律經 `read_doc()` 讀檔，該函式先斷言「無 BOM、無 `\r`」再解碼——文件被 CRLF 化時所有讀它的 DT 一起紅，且訊息指名檔 | 全部 DT |
| B-02 | 表格切欄 | 新格與新增登記不得在儲存格內寫 `\|`（`registry_rows` 與 `read_doc` 系解析皆以 `\|` 切欄；需要「或」時用 `／`）；反引號內的 `<module>`、`<NNN>` 不含 `\|` | 11-4-1、-2、-3 |
| B-03 | 標題比對 | `## ` 標題以**逐字**比對（全形與半形、「與」與「及」皆分）；比對前只 `strip()` 行尾空白；巢狀 `### ` 不終止 `## ` 節 | D3-2、D5-1 |
| B-04 | 圍欄內文字 | 以 ` ``` ` 圍起的區塊內的 `## ` 行不是標題、不計入節邊界；` ```sql ` 區塊的內容才計入 SQL 字樣；圍欄外的敘述不算 SQL 字樣 | D3-2、D3-4 |
| B-05 | 反引號 token | 「再開症狀」條目的「可觀測 token」＝該條內至少一對反引號包住的非空字串；空反引號對 ` `` ` 不算；token 內不得只有空白 | D3-2、D3-E-1 |
| B-06 | 絕對缺席斷言的寫法 | 「不含某字樣」一律逐行判定（list comprehension 取命中行→`assertEqual([], hits)`），**不得**寫 `assertNotIn(文字, 整份文件.read_text())`，也不得對讀入的文字用寫死數字切片（`test_archive_defect_log` 的 `TestNoAssertionSamplesALiveDocumentWholesale` 掃全部根層測試檔，會紅） | D10-1、D3-4、11-4-3 |
| B-07 | 檔名大小寫與連號 | ADR 檔名全小寫 slug；N 連號無洞；`ADR-SIDB-*` glob 結果排序後逐一比對 N（NTFS 大小寫不敏感：`ADR-SIDB-001-…` 與 `adr-sidb-001-…` 視為碰撞，`check_ntfs_paths.py` 會紅） | D3-1 |
| B-08 | 行號座標漂移 | 本檔所有「檔:行」座標於 `<base>` 重核；後續 commit 使行號漂移時，座標檢查（G-P0-4、G-P0-5）以**關鍵字**為準、行號僅作提示（先 `git grep -n -F <關鍵字>`，行號與表差 ≠0 則報「座標漂移」但不紅；關鍵字**自全檔消失**才紅）。座標檢查讀 git 樹，被測副本須已提交（SCG-4 通過條件 3 的突變副本規則） | 11-4-5、13-5-1 |
| B-09 | 長路徑 | 副本根路徑須短（≤60 字元）；展開失敗而未記數＝實驗無效（細節見 §5.3.2「副本規則與注意」） | 11-4-4、13-5-2 |
| B-10 | 基線紅 | 副本無 `.git` 時依 git 的測試恆紅，故乾跑跑兩輪、以兩副本逐檔比較判定（見 §5.3.2） | 11-4-4 |
| B-11 | 時間與環境 | DT 不呼叫 `datetime.now`、不讀環境變數（`SI_*`、`AUTOSDD_*` 皆不影響）、不讀 `build/`（FSM 狀態檔未追蹤，CI 看不到）、不連 PG、不連網；GT 的 FSM 檢查只在開發機跑 | 全部 DT |
| B-12 | 重跑決定性 | GT 腳本輸出一律排序、不含時間戳與絕對路徑；`rows=<N>` 與 `generated_at` 先去除再比對 | 02-6-2、13-7-1 |
| B-13 | 零測試與假綠 | 判定指令收集 0 個測試＝FAIL；DT 不含 `skip*`；GT 的 rc 必須先存變數再讀（不接管線），輸出尾段貼進審查報告 | 全部 |
| B-14 | 東亞寬度 | 新測試檔每行顯示寬度 ≤100（CJK 算 2，ruff E501 口徑）；ADR 等 Markdown 不受此限，但表格列不得因折行而破壞單行表格語法 | D9-2 |
| B-15 | 憑證字面 | 全部 P0 文件（**含本 TCS**）不得含連線字串、密碼、金鑰；示例一律 `<YOUR_…>` 佔位符；掃描判準＝`postgres(ql)?://[^<\s]*:[^<\s@]+@`（有 userinfo 密碼段者）命中 0；突變用的假 DSN 由 QA 在副本現組，不寫進任何文件 | D3-4 |
| B-16 | 並行偽差異 | 乾跑兩副本並行時，使用全域具名資源的測試會互撞；任何 base／probe 的 DIFF 先單跑兩副本各至少 2 次複核（見 §5.3.2） | 11-4-4 |
| B-17 | 帳本盲實驗的索引一致性 | K 副本只刪工作樹而索引仍列檔，會有人為不一致的雜訊（見 §5.4.3 步驟 2） | 13-5-2 |

## 5. 測試資料規格

### 5.1 命名對照、解析函式與夾具

#### 5.1.1 M 編號撞名對照（本檔與全部 P0 文件一律用右欄）

| PRD 稱呼 | PRD 座標 | 本檔與 P0 文件的稱呼 |
|---|---|---|
| M1 對帳恆等式（彩排庫與真庫） | §8.1 | `G-SIDB-1` |
| M2 `si check` 全綠（含 `db.consistency`、`chain.intact`、`state.replay`、`readmodel.fresh`） | §8.1 | `G-SIDB-2` |
| M3 `console_pending=0` 且載體旗標為 `db` | §8.1 | `G-SIDB-3` |
| M4 快照在場且鏈頭等於 DB 鏈頭 | §8.1 | `G-SIDB-4` |
| M5 `params.fingerprint()` 等於 P0 基準 | §8.1 | `G-SIDB-5` |
| M6 `docs/06_quality/` 無未提交的帳本編輯 | §8.1 | `G-SIDB-6` |
| M7 寫入動詞與閘門在彩排庫以 `db` 模式全綠 | §8.1 | `G-SIDB-7` |
| M1～M5（SelfImproving 的兩個 measuring 窗指標） | AC-LD-13-6；R-10；`SelfImproving_Protocol/metrics.md` | `MEAS-M1`～`MEAS-M5` |
| M6（skip 政策「全世界沒跑過」判準） | AC-LD-11-1；`tools/lib/skip_runtime_report.py:311-318` | `SKIP-M6` |
| H1～H5（人工項） | §8.1 | 不變（H1～H5；與其他編號不撞） |

> 本檔自身不在 AT-LD-00-D10-1 的掃描集內（檔頭與本表需引用 PRD 原稱）；本表是 P0 交付文件之外唯一對照處。skip 摘要引文**去掉**方括號標籤再記入基準檔（標籤帶裸 M 編號，G-P0-10）。

#### 5.1.2 DT 的解析函式（純函式；檔內自帶，不新增輔助檔）

| 函式 | 契約 |
|---|---|
| `read_doc(rel) -> str` | 以位元組讀 `ROOT/rel`；斷言無 UTF-8 BOM、無 `\r`（B-01）；回傳 UTF-8 解碼文字 |
| `sections(text, level=2) -> dict[str, str]` | 以行首 `## `（level 2）切節；鍵＝標題行 `strip()` 後全文；圍欄（` ``` `）內的行不算標題（B-04） |
| `table_rows(section_text) -> list[list[str]]` | 取節內以 `\|` 起頭的行，逐行以 `\|` 切欄並 `strip()`；排除分隔列（只含 `-: ` 字元）；欄數由列自己決定 |
| `layout_cell_problems(text) -> list[str]` | 對 Root_Layout 文字檢 C1.1 兩列：缺列、列重複、缺必要字樣（C1.1 的全部字樣，含 AC-LD-11-4 要求的「行數棘輪」「skip 政策」）各回一筆含「列名＋缺的字樣」；對真樹應回空 |
| `adr_problems(filename, text) -> list[str]` | 檢 C2：標題格式與編號一致、六節順序、**選項計數規則**（見下）、再開症狀≥1 且各有 token、狀態值以 `Accepted` 或 `Superseded` 起頭；回問題清單 |
| `adr_decision_problems(n, text) -> list[str]` | 檢 §5.2.1 該 N 的「必含選項標籤」與「決定字樣」 |
| `sql_draft_problems(text) -> list[str]` | 檢 ADR-003：` ```sql ` 區塊存在、§5.2.2 物件字樣齊全、14 表矩陣逐表分類與 §5.2.2 預期相同、連線字串字面為 0 |
| `draft_problems(text) -> list[str]` | 檢 C3 |
| `errata_problems(text) -> list[str]` | 檢 C4 案文檔：E-1～E-7 七節、七欄標籤、`套用階段` 值域、E-4 核准座標欄、`## 不勘誤` 三段 |
| `p0_acceptance_problems(root) -> list[str]` | **一次性驗收**（GT 的 G-P0-13 呼叫，**DT 不跑**）：對真樹串接 `adr_decision_problems`（001～008）、`sql_draft_problems`（ADR-003）、`draft_problems`（Architecture 草稿），並對 8 個 ADR、草稿、三份證據檔跑連線字串判準（B-15）；空清單＝通過 |
| `bare_m_hits(text) -> list[str]` | `(?<![-\w])M[1-7](?!\d)` 的逐行命中（行號＋行文）；不含 §5.1.1 |
| `fingerprint_of(tree)` | `lib.selfimproving.params.fingerprint(tree, params_dict)` 的第一個回傳值（`tree` 下的 `docs/06_quality/SelfImproving_Protocol/`） |

**選項計數規則**（`adr_problems` 的判準）：「選項與代價」節內，以 `- 選項 <標籤>：` 起頭的行＝一個選項（`<標籤>` 逐字取自 §5.2.1 的「必含選項標籤」，如 `A`、`B′`、`(a)`）；選項數＝這類行數，須 ≥2 且標籤集合包含 §5.2.1 所列；每個選項行之後、下一個選項行之前，**有且僅有一行**以 `- 代價：` 起頭（可縮排）；節內其他敘述行不計入選項。

**夾具**：`tempfile.mkdtemp` 合成樹（不動真樹）：`synth_layout(cells)`（建只含 `## 1.`、`## 2.`、`## 3.` 的 SSOT 文字）、`synth_protocol(tmp)`（複製真樹協定目錄三檔）。DT 無注入縫（沒有 `mock.patch`）：全部判準函式都是文字進、問題清單出。

#### 5.1.3 勘誤案內容契約（案文檔 E-1～E-7；座標皆於 `<base>` 重核）

**全備案**（§7.1 第 3 條）：P0 不套用、不 `spec-refreeze`；案文只是「備妥」。欄位「原文」必須是 **`<base>` 版**目標文件該行的逐字截取（≥20 個字元、≤200 字元的連續子字串），不含 `|`（PRD `:904`、`:905`、`:491` 等行本身含 `|`，請避開；案文儲存格不得有 `|`），也不得含裸 `M1`～`M7`（AT-LD-00-D10-1 掃案文，引文不豁免；SI PRD `:491` 第 856 字元附近有「M1 窗序」、`:988` 第 316～320 字元附近有「M1～M5」，取子字串時避開）。七個欄位標籤逐字為 `目標文件`、`原文座標`、`原文`、`訂正文`、`生效階段`、`套用階段`、`理由`；`套用階段`＝該條最早生效階段，值以 `P1`、`P2`、`P3a`、`P3b` 之一起頭（日後套用時可在其後括註已套用的 commit）。「訂正要點」是**必含字樣**，措辭由實作棒定。

| 條 | 目標文件 | 原文座標 | 訂正要點（必含字樣） | 生效階段 | 套用階段 |
|---|---|---|---|---|---|
| E-1 | `SelfImproving_PRD.md` | `:791`（「入 git…單一真相＝git」）、`:793`（「不用 PG」） | 改述為模式矩陣（PRD §9.2）：`LEDGER_TRUTH`、`file`、`shadow`、`db`；「單一真相＝git」自 P3b 切換 commit 起不成立；「不用 PG」改為 P1 起影子、P3b 起真相源；仍不用 `build/`；引 `ADR-SIDB-001` | P1（影子）；P3b（真相） | P1 |
| E-2 | 同上 | `:811`（ADR-SI-10 多寫入者與配號）、`:987`（ADR-SI-01）、`:988`（ADR-SI-02）、`:997`（ADR-SI-10）、`:999`（ADR-SI-12） | 逐項加「被取代關係」：ADR-SI-01→`ADR-SIDB-001`（P3b）；ADR-SI-02→JSONL 與內容檔於 P3b 起降為匯出格式；ADR-SI-10→`ADR-SIDB-005`（P3a，`pg_advisory_xact_lock`）；ADR-SI-12→`ADR-SIDB-004`（P2，僅 `console.si.read-source=db` 時；預設 `bridge` 不變；Bridge 仍只經 CLI 子行程取數，AC-LD-08-4） | P2／P3a／P3b | P2 |
| E-3 | 同上 | `:990`（ADR-SI-03′ Console 載體＝稽核檔、`audit_sha256`）、`:792`（家目錄表 `console_audit/`「不可丟棄」） | 加「P3a 起載荷落 DB 並保存原始位元組（`raw`）；`console.si.write-carrier`＝`file`／`dual`／`db`；稽核檔『不可丟棄』性質改由 DB 備份承擔；選項 E 的『第二個真相』因 DB 成唯一真相而失效」；引 `ADR-SIDB-006` | P3a | P3a |
| E-4 | 同上 | `:491`（AC-SI-35-1 ⑤「本 PRD 不新增非 Console 的 obs-add」）、`:904`、`:905`（`obs-add`／`obs-close` 列：`--carrier` 目前只收 `console`） | 加「掌舵者 2026-10-27 核准（OQ-3）：P3a 起於 `db` 模式新增 `--carrier operator`、`def-*`、`debt-*`；`AUTOSDD_UNATTENDED` 與手寫同級；不核准則 P3b 不得進（H4）」；生效前沿用原文；**含核准座標欄**：未填時字面 `〈sid／line 由主控填〉`，主控於 Stage-2 凍結時填為 `sid <36 位 uuid> line <n>` | P3a | P3a |
| E-5 | 同上 | `:527`（NFR-SI-02-4「外聯只在 `fetch.py` 一個模組」） | 增列「DB 連線只在 `dal_pg_conn.py`」；能力測試明列該檔為唯一可 import `psycopg` 者；新增 `dbr`、`dbw` 能力類 | P1 | P1 |
| E-6 | `Issue_Center_PRD.md` | `:415`（「不快取：每請求重算，帳本是唯一真相源」）、`:4`（「帳本…一個字不動」） | 加「`console.si.read-source=db`（P2 起；非預設）時讀模型是寫入時刷新、帶 `ledger_head` 的衍生值，過期由 `READ-MODEL-STALE` 偵測；退路＝ADR-SIDB-004 選項 C；預設 `bridge` 仍每請求重算」 | P2 | P2 |
| E-7 | 同上 | `:204`（游標：缺陷＝主檔資料列行號）、`:419`（`schema_rev` 維持 1） | 加「P3b：游標改插入序、`schema_rev` 升 2（D-10）；Bridge、backend、黃金檔、前端同批」 | P3b | P3b |

**不勘誤（案文 `## 不勘誤` 節三段）**：#6（`SelfImproving_PRD.md:370,422` 的 `params` 指紋判準）——以設計避開（不新增 params 鍵、不改協定目錄任何檔），由 AT-LD-02-6-1、-E-1 持續守；#8（根 `CLAUDE.md:44,48`）——屬 P4（OQ-4）；#9（`.claude/hooks/block_destructive_git.py:1445-1464` 的 `_GOV_EXACT`）——無需改（不含任何帳本檔，PRD `[C-8]`）。

### 5.2 ADR 內容契約

#### 5.2.1 逐檔必含（對應 PRD §9.5；「必含選項標籤」＝「選項與代價」節 `- 選項 <標籤>：` 行的標籤，計數規則見 §5.1.2）

| N | slug（檔名） | 中文標題 | 必含選項標籤 | 「決定」節必含字樣 | 「再開症狀」須對應（PRD §9.5 原文要點） |
|---|---|---|---|---|---|
| 001 | `truth-source-and-db-location` | 真相源與 DB 位置 | A 維持檔、B Console PG 加 `si` schema、C 專屬 PG 容器、D 用 `autoclaude_pg` | 「決定」節：`C`、`B 在同樣隔離下可接受`、`影子期任何可達的 PG18`、`單一主力機為真相`（OQ-2 裁決）；「狀態」節：`Accepted（階段性：…）` 且含 `H2`、`H3`（P3 進場條件） | `down -v` 清掉 `si`；埠衝突 |
| 002 | `dal-and-modes` | DAL 與模式 | A 只做 Pg、B Mem＋File＋Pg＋影子、C 另加 SQLite | `B`、`tools/tests_pg/`、`LEDGER_TRUTH`、`SI_LEDGER_STORE`、`file`、`shadow`、`db`；寫明 C 否（雙 SQL 方言、保真度差） | PG 契約測試在 CI 長期跑不起來（`si-pg-contract`）；棘輪收緊到涵蓋兄弟目錄 |
| 003 | `integrity-append-only-chain-replay` | 完整性：追加專用、鏈與重放 | A 無、B 追加專用＋全表延遲約束＋鏈＋重放、C B＋外部錨點 | `B`、`錨點`、`快照內鏈頭`（OQ-1）、`audit_chain_guard`、`row_hash` | 出現超級權限竄改的暴露證據（`chain.intact` 紅且非測試語料） |
| 004 | `read-model` | 讀模型 | A Java 重實作 fold 與對照表、B Python 算 DB 存 Java 只讀、C 保留 Bridge 子行程讀 DB | `B`、`READ-MODEL-STALE`、`ledger_head`；寫明 C 為 P2 退路 | 刷新使寫入 >1 s 或鏈頭常落後（`readmodel.fresh`） |
| 005 | `write-serialization` | 寫入序列化與配號 | A 沿用檔案鎖（`evwrite.py` 獨佔建檔）、B `pg_advisory_xact_lock`＋鎖內 `max+1`、C identity／sequence | `B`、`pg_advisory_xact_lock`、`max+1`、`lock_timeout`；寫明 C 否（回滾留洞） | 取鎖逾時成常態（`lock_timeout`） |
| 006 | `console-carrier` | Console 載體 | A 稽核檔＋Bridge、B 載荷列放 `console.si_console_writes`（加 `raw`）、B′ 專屬容器時 `si.console_requests` | `B`、`B′`、`console.si.write-carrier`、`file`、`dual`、`db`、`audit_sha256` | Console 表被清而尚有未入帳列（`console_pending`） |
| 007 | `credentials-and-tls` | 憑證與 TLS | A 讀 `AgentConsole/.env`、B 只認 `SI_DB_DSN`＋`PGPASSFILE`、C 放 `params.json` 或 config | `B`、`SI_DB_DSN`、`PGPASSFILE`、`sslmode`、`D-5`；寫明 A、C 否的理由 | 無人值守窗口缺 env 成常態（`si-db-unavailable`） |
| 008 | `snapshot-and-offsite-backup` | 快照與離機備份 | (a) 輪收尾手動匯出、(b) 固定單一目錄覆寫＋pre-commit 快照閘、(c) (b)＋每日 `pg_dump -n si`、(d) 不要快照 | `舊檔永遠保留`、`(b)`、`(c)`、`AUTOSDD_SNAPSHOT_GATE_OFF`、`docs/06_quality/SelfImproving_Snapshots/`、`pg_dump -n si`（OQ-1 裁決） | 快照鏈頭長期落後 DB 鏈頭；快照匯出長期失敗 |

#### 5.2.2 ADR-SIDB-003 的 SQL 草稿與逐表守衛矩陣

**SQL 草稿必含字樣**（合計於 ` ```sql ` 區塊內；每項至少一次）：`CREATE SCHEMA`、`si_owner`、`si_writer`、`si_reader`、`RETURNS trigger`、`BEFORE UPDATE OR DELETE`、`integrity_constraint_violation`、`CREATE CONSTRAINT TRIGGER`、`DEFERRABLE INITIALLY DEFERRED`、`audit_chain_guard`、`pg_advisory_xact_lock`、`sha256(`、`txid`、`prev_hash`、`row_hash`、`after_sha`、`row_sha256`、`REVOKE`、`GRANT`。草稿沿 `V13__si_console_writes.sql:28-51` 的形態（`RETURNS trigger`＋`BEFORE UPDATE`＋`ERRCODE = 'integrity_constraint_violation'`，已於 `<base>` 重核）；`audit_chain_guard` 只驗 `seq` 連續、`prev_hash` 銜接與 `txid`，**不重算 `row_hash`**（canonical JSON 只由 Python 定義）。

**逐表守衛矩陣**（預期分類；依 PRD §9.3 與 AC-LD-05-4 推得，ADR-003 的矩陣必須逐表相同）：

| 類 | 表（`si.` 前綴省略） | 守衛 |
|---|---|---|
| 追加專用（UPDATE／DELETE 一律被觸發器拒；after_sha＝PG 核心 `sha256()` 重算值；要求同交易 audit 列，`audit` 本身除外） | `events`、`artifacts`、`audit`、`legacy_rows`、`console_audit_files` | `BEFORE UPDATE OR DELETE` 觸發器＋（`audit` 以外）延遲約束觸發器 |
| 可變且逐列 audit（audit 存改前改後完整列影像；`observations` 只准處置欄 `open`→終值一次） | `observations`、`defects`、`debt_tracks` | 延遲約束觸發器要求同 `txid` 有同 `tbl`、`row_id` 的 audit 列，且 `after_sha` 等於 `NEW.row_sha256` |
| 讀模型（只准 `si_writer` 於同一交易刷新；不逐列 audit，由 `readmodel.fresh` 重算比對） | `issues`、`export_items`、`export_meta` | 權限（`si_reader` 只 SELECT）；無觸發器 |
| 自舉例外（首次遷移的自舉順序：`audit` 與觸發器先於任何受約束表的首筆寫入；這三表不受「同交易 audit 列」約束） | `schema_migrations`、`meta`、`import_runs` | `meta` 僅 `si_owner` 與 `db flip` 可改；其餘追加 |

共 14 表（5＋3＋3＋3）。`si.console_requests`（專屬容器的 B′ 變體）不在 14 表內，於 ADR-006 另述。

### 5.3 以 `tools/tests` 為根的掃描器普查與 `tools/tests_pg/` 管轄（AC-LD-11-4；D2）

PRD 要求「Grep `tools/tests` 於 `tools/lib`、`tools/tests`，逐一核對」。現查：`tools/lib` 47 檔 217 處命中（`git grep` 口徑；`tools/*.py` 的 pathspec 是超集——含 `tools/lib` 與 `tools/tests` 自身，共 138 檔 605 處，扣 `tests` 後 72 檔 308 處）；其中**多數只是註解、docstring、訊息字串或對具名測試檔的引用**。本檔用兩道互補的方法定案，不只靠 Grep：(1) §5.3.1 以 AST 把「非 docstring 的字串常數」與註解分開，逐族判定；(2) §5.3.2 的**乾跑置位實驗**直接量行為——這才是 AT-LD-11-4-4 的判準，因為靜態普查看不到「由 `rglob("*.py")` 一路掃下來、並不字面寫出 `tools/tests`」的掃描器。

#### 5.3.1 掃描器族別與對 `tools/tests_pg/` 的判定（座標於 `<base>` 重核）

判定值**只填四值之一**，補充說明一律寫在「依據」欄（AT-LD-11-4-5 的判準）：`不涵蓋`（掃描器的根或鍵就是 `tools/tests`，兄弟目錄在射程外）、`涵蓋（受管）`（`tools/tests_pg` 在射程內且有明確規則）、`涵蓋（無反應）`（在射程內但合規檔不觸發）、`需 P1 處置`（射程內且需 P1 改碼或登記）。

| 族 | 掃描器（座標） | 對 `tools/tests` 的依附 | 判定 | 依據與乾跑結果 |
|---|---|---|---|---|
| A1 runner | `tools/run_root_unittests.py:301`（`census_profile("tools/tests", …)`）、`:333-336`（`start_dir.resolve()==_TESTS_DIR` 才評 `SKIP-M6`）、`:424`、`:44`（`MIN_TESTS`） | discover 根＝`tools/tests`；`SKIP-M6` 只在該根評 | 不涵蓋 | `tools/tests_pg` 不在 discover 根內（PRD AC-LD-11-1）；乾跑：`test_run_root_unittests` 255 項在 base／probe／ctrl 三副本逐項相同 |
| A2 skip 政策 | `tools/lib/skip_group_policy.py:575,622,701`（三張剖面表，共 17 處 `tools/tests@<剖面>` 鍵）、`skip_tag_policy.py:310-314`（`_EXTRA_SCAN_TREES` 不含 `tools/tests_pg`）、`:336,424`（`_TREE_FILE_FLOORS`）、`:569,593`（POSIX 標籤棘輪）、`skip_profile_key.py:60`、`skip_runtime_report.py:201,311-318`、`windows_skip_tags.py`、`skip_static_scan.py`、`skip_source_io.py`、`pytest_skip_census.py` | 以 `tools/tests` 為鍵的上限表、落款、掃描面 | 不涵蓋 | 乾跑：`test_skip_ceiling_ratchet_direction`、`test_skip_discoverability_r83` 逐項相同；PG 測試因不進 runner 而不計 skip（AC-LD-11-1） |
| A3 行數棘輪與分桶 | `tools/tests/test_adr_xplat001_c1c2_lock.py:554`（`_GUARD_DIR_REL="tools/tests"`）、`:595`（`_GUARD_LINE_PATTERN="*.py"`，非遞迴）、`:4491-4496`（子目錄內 `.py`＝`[逃逸]`，只看 `tools/tests` 的子目錄）；`tools/lib/guard_bucket_policy.py:57,65,92`（`GUARD_SURFACE_REL`、`("tools/tests", True)`、`guard_self` 前綴）；`tools/probe/guard_layer_bucket_census.py`、`guard_layer_dedup_census.py` | 掃描面＝`tools/tests/*.py` | 不涵蓋 | **對照組成立**（ctrl）：同一 probe 放進 `tools/tests/` 時，`TestGuardLayerRatchet.test_a_net_zero_swap_is_red`、`TestGuardLayerRatchet.test_the_line_ratchet_took_over_and_has_teeth`、`TestShrinkOnlyRatchet.test_ratchet_is_independent_of_git_state` 三項新增失敗；放進 `tools/tests_pg/` 則 `test_adr_xplat001_c1c2_lock` 187 項全過 |
| A4 檔數下限與 `MIN_TESTS` | `skip_tag_policy.py:424`（`"tools/tests": 89`）；`tools/lib/min_tests_margin.py`＋`run_root_unittests.py:44`（`MIN_TESTS`）；`tools/lib/parallel_shard.py:251`（分片只吃 discover 根） | 計數取自 discover 根 | 不涵蓋 | PG 測試不增加 `tools/tests` 檔數、不增加零相依收集數；P1 因此**不付**這兩道稅（P0 的新測試檔則要付，§5.9） |
| A5 具名檔引用 | `check_pytest_baseline_sites.py:85`、`tools/lib/defect_ledger_index.py:358`、`test_pre_push_dispatcher.py:1051`（`_CARRIER_REF_RE`）、`test_windows_smoke_heartbeat_doc_sync.py:63`、`test_schedule_capability_parity.py:55`（`_SKIP_TREE_FLOORS["tools/tests"]`） | 對**具名** `tools/tests/<檔>` 的引用，不是掃描 | 不涵蓋 | 未列名的 `tools/tests_pg/<檔>` 不被這些引用誤收。`test_schedule_capability_parity.py:49-55` 的 `_SCAN_FLOOR` 直接取 `skip_tag_policy._TREE_FILE_FLOORS['tools/tests']`（SSOT 消費端，與 A4 同源，§5.9 #6 一次重釘涵蓋），不是獨立下限 |
| B1 LOC 分級 | `AutoClaude/tools/check_loc_budget.py:276-283`（`ROOT_TOOLS_TIERS`：`guardrail_cli` 預算＝絕對紅線 750、patterns 含 `tools/`）、`:296`（`ROOT_TOOLS_EXCLUDED_DIRS={"tests"}`）、`:538-553`（`iter_root_tools_files` 以路徑**片段名**＝`tests` 排除）、`:318-340`（`count_loc` 只計斷言行） | 排除目錄名 `tests` | 涵蓋（受管） | 乾跑 probe：`check_loc_budget.py --json` 的 `narrative_total` 由 25747 增為 25749（probe 檔的敘事行入帳），檔入根層報表；`tests_pg` ≠ `tests` 故不被排除，單檔 ≤750 斷言行 |
| B2 ruff | `tools/ruff.toml:33-50`（`E,F,I,UP,W,S102`、line-length 100）、`:82`（`"tests/*.py" = ["E501"]`）；執行者＝`root-infra-ci.yml:486` 第 16 道（`ruff check tools/ .claude/hooks/`）與 `tools/git-hooks/pre-push` 第 ④ 段 | E501 豁免只涵蓋 `tools/tests/*.py` | 涵蓋（受管） | **無 E501 豁免**：乾跑 probe 的 `ruff check tools/` 對 152 寬行回 `E501 Line too long (152 > 100)`，base 回 `All checks passed!`；PG 測試每行顯示寬度須 ≤100（CJK 算 2） |
| B3 語法 | `root-infra-ci.yml:330-337`（`compileall -q -j0 tools`，遞迴） | 全樹 | 涵蓋（無反應） | 乾跑：`compileall` 兩副本 rc 0 |
| B4 平台中立 | `tools/tests/test_platform_neutral_paths.py`（`:55` 逐檔登記表、`:2143`、`:4215` 等；文字 I/O 編碼、`os.replace` 等原語、單平台 API 詞彙表的 AST 判準；掃描面含 `tools/**`） | 全樹（排除 `tests` 目錄與否依各類判準） | 涵蓋（無反應） | 乾跑 probe 與 base 逐項相同（兩輪皆然）；P1 實作須自守：PG 測試若用 `open()`／`read_text()` 須帶 `encoding=`，用 `os.replace` 等須包 `try/except OSError` |
| B5 編碼衛生 | `test_subprocess_encoding_hygiene.py:892`（具名登記）、`:1442`（`_E501_DEBT_CEILING` 只針對 `tools/tests/`）；`subprocess` 無 `encoding=` 的掃描涵蓋 `tools/**` | E501 債棘輪＝`tools/tests`；`subprocess` 掃描＝全樹 | 涵蓋（無反應） | 乾跑 probe rc 0、39 項逐項相同；ctrl（放進 `tools/tests/`）則 `test_e501_debt_only_shrinks` 新增失敗 |
| B6 腳本掃描面 | `tools/_script_scan_surface.py:66`（`SCRIPT_SCAN_ROOTS=("tools","AutoClaude/tools","AISDLC_SDD/scripts")`，遞迴 `*.sh`／`*.ps1`）；`test_ps51_compat`、`test_ps1_bom`、`test_bash32_compat` | 全樹，只看 `.sh`／`.ps1` | 涵蓋（無反應） | P1 的 `tests_pg/`、`sql/` 只含 `.py`、`.sql`；若日後加 `.ps1` 則落入 BOM、CRLF、PS5.1 語法判準 |
| B7 NTFS 與衛星檢查 | `tools/check_ntfs_paths.py`（所有追蹤路徑的大小寫碰撞）；`check_script_parity.py`、`check_wrapper_thinness.py`（只看具名檔，不涵蓋） | 全樹或具名薄殼 | 涵蓋（無反應） | 檔名全小寫 ASCII（§5.2.1 的 slug 規則同理）即無反應 |
| C 提及 | `tools/lib/console_orphan_census.py:93`、`tools/check_hooks_liveness.py:280`（訊息字串）；其餘 `tools/lib`、`tools/probe` 命中檔（`hook_wiring.py`、`governance_docs.py`、`git_paths.py`、`quota_*.py`、`sentinel_lifecycle.py`、`session_brief.py`、`bootstrap_lock.py`、`dispatch_imbalance.py`、`nightly_heartbeat.py`、`ci_liveness.py`、`schedule_backend*.py`、`platform_utils.py`、`pace_contract.py` 等） | 註解、docstring、訊息、或指向被測腳本的路徑 | 不涵蓋 | AST 普查：這些檔的非 docstring 字串常數不是掃描根或表鍵，無一以 `tools/tests` 為掃描根 |
| D 路徑前綴分類（PRD §9.4 沒列） | `tools/lib/selfimproving/scan.py:33-48`（`bucket_of`：前綴 `tools/tests/test_selfimproving_` 才歸 `SelfImproving` 桶） | 前綴字串 | 需 P1 處置 | `tools/tests_pg/test_selfimproving_dal_pg_*.py` 不以該前綴起頭⇒ `si scan` 的模組桶會把 PG 測試歸「根層」而非「SelfImproving」（統計歸屬偏差，不影響閘門）。P1 須擴前綴加 `tools/tests_pg/test_selfimproving_`（改 `ro` 檔 `scan.py`，屬 `non_evolvable_globs` 範圍）並補桶歸屬測試（§7.3）；`ADR-SIDB-*.md` 檔名不含 `SelfImproving` 亦歸「根層」，同屬統計歸屬，不處置 |

**`tests_pg` 與 compat-ci `paths`**（PRD §9.4 `:232` 留給 TCS 核）：不入。理由：compat CI 不起服務容器、不跑 PG 測試（AC-LD-11-3）；`root-infra-ci.yml` 以 `on: push／pull_request` 觸發、無 `paths` 過濾，且其 `py_compile`（B3）與 `ruff check tools/`（B2）本就遞迴涵蓋 `tools/tests_pg/`。新 CI 工作 `si-pg-contract` 的觸發範圍由 P1 TCS 定。

#### 5.3.2 乾跑置位實驗（AT-LD-11-4-4、-E-3；2026-10-27 實跑）

**目的**：用行為取代靜態推測，量「新增 `tools/tests_pg/` 與 `tools/lib/selfimproving/sql/` 之後，既有掃描器有沒有反應」，並以對照組證明量測有鑑別力。

**副本規則與注意**（原 B-09、B-10、B-16）：①副本根路徑要短（≤60 字元；Windows 260 字元限制下 `AgentConsole/backend` 深層 Java 路徑會使展開失敗。本次因 scratchpad 路徑太深，三副本一致略過 127～164 個超長路徑檔；略過數須記入報告，展開失敗而未記數＝實驗無效，不得當成「無反應」）；②副本無 `.git` 時依 git 的測試恆紅（起草時 25 檔），故跑兩輪：第一輪無 `.git`，第二輪三副本皆 `git init`＋`git add -A`＋提交；判定以「兩副本逐檔比較」而非「絕對綠」；③並行偽差異：兩副本並行時，使用全域具名資源（Windows mutex、固定埠、家目錄固定檔）的測試會互撞，任何 base／probe 的 DIFF 先**單跑兩副本各至少 2 次**複核再下結論（本次 `test_dev_start::TestOrphanChildLockRegression.test_nightly_running_true_branch_on_windows_mutex` 即是：並行時只在 probe 紅，單跑皆 OK）。

**程序**：`git archive <base>` 展開三副本：`base`（原樣）、`probe`（加 `tools/tests_pg/test_selfimproving_dal_pg_probe.py`〔含一行 152 寬註解〕與 `tools/lib/selfimproving/sql/V000__probe.sql`）、`ctrl`（base＋同一支測試放進 `tools/tests/`，對照組）。逐檔 `python -m unittest discover -s tools/tests -p <檔>`（工作目錄＝副本根），比對 `rc`、收集數、失敗集合。

**選檔規則**（名單入 D7 證據檔〈乾跑選檔名單〉節，契約節 C6 ⑥；G-P0-4 引用）：(1) 第一輪＝`git grep -l -E 'tools/tests|_TESTS_DIR|rglob\(|ls_files|iterdir\(|\.glob\(|os\.walk' <base> -- 'tools/tests/test_*.py'`（`<base>` 現查 90 檔）加 `test_ntfs_trailing_space_device_name`（B7）、`test_root_infra_parity`（CI／pre-push 對等）；**起草時實跑並驗過的是其中涵蓋 §5.3.1 每一族的 50 檔子集**（名單入 D7 證據檔），其餘檔未驗，由 QA 重跑補全。(2) 第二輪＝第一輪 `rc≠0` 者（起草時 25 檔）加棘輪類 8 檔（`test_adr_xplat001_c1c2_lock`、`test_root_module_layout`、`test_subprocess_encoding_hygiene`、`test_skip_ceiling_ratchet_direction`、`test_run_root_unittests`、`test_selfimproving_capability`、`test_selfimproving_p2_meta`、`test_selfimproving_p3_meta`；後 8 檔三副本皆跑），起草時共 33 檔。

**實測結果**：

| 項 | 結果 |
|---|---|
| 第一輪：base vs probe | 50 檔逐檔 `rc`、收集數、失敗集合**完全相同**（收集共 4,321 項；其中 25 檔因副本無 `.git` 等因素基線紅，兩副本紅法一致） |
| 第二輪：base vs probe | 33 檔中 32 檔逐項相同；唯一差異 `test_dev_start…windows_mutex` 只在 probe 紅——**並行偽差異**，兩副本單跑（各 2 次）皆 OK |
| 第二輪：ctrl vs base | `test_adr_xplat001_c1c2_lock` 由 0 項失敗變 3 項（上列三項）；`test_subprocess_encoding_hygiene` 由 0 變 1 項（`TestRootToolsLintPolicy.test_e501_debt_only_shrinks`）；其餘根掃描器（`test_run_root_unittests`、`test_skip_ceiling_ratchet_direction`、`test_root_module_layout`、能力登記、p2／p3 meta、`test_platform_neutral_paths`、`test_doc_loc_baseline_freshness_r60`）無新增失敗 |
| LOC 報表 | `AutoClaude/tools/check_loc_budget.py --json`：probe 副本 `narrative_total` 25747→25749，probe 檔入根層報表（`guardrail_cli`）；兩副本 rc 0 |
| ruff | probe：`tools\tests_pg\test_selfimproving_dal_pg_probe.py:13:101: E501 Line too long (152 > 100)`；base：`All checks passed!` |
| `compileall -q tools` | 兩副本 rc 0 |

**結論**：(1) `tools/tests_pg/`＋`sql/` 對 50 檔掃描器測試**零新增反應**；(2) 對照組證明量測有牙：同一檔放進 `tools/tests/` 立即讓行數棘輪（3 項）與 E501 存量棘輪（1 項）轉紅，故兄弟目錄的「不被計入」是目錄選擇造成；(3) 兩個真實管轄＝LOC 分級與 ruff 全規則（含 E501）；(4) 盲區（誠實劃界）：第二輪仍有 6 檔因副本與真樹的差異而基線紅（`test_check_defect_log_crossref` 2 項、`test_check_script_parity` 2 項、`test_dev_platform_provenance` 2 項、`test_dev_start` 2 項、`test_doc_loc_baseline_freshness_r60` 5 項、`test_platform_neutral_paths` 2 項），它們的失敗集合兩副本相同，但被遮蔽的測試無法證明「有無反應」；以靜態普查補看：`test_platform_neutral_paths` 的遮蔽項是 git 索引模式類，與路徑目錄無關。

> **AT-LD-11-4-4 的判定程序**：依本節副本規則與選檔規則重跑，條件＝(a) base 與 probe 逐檔相同（並行偽差異須單跑複核）；(b) ctrl 相對 base 至少出現行數棘輪或 E501 存量棘輪的新增失敗；(c) LOC、ruff、compileall 三項如上。與本節數字不同時，以重跑結果為準並勘誤本節。

### 5.4 A.4 普查定稿（AC-LD-13-5；D6）——「讀真實帳本內容」的測試

#### 5.4.1 A.4 定稿表（座標於 `<base>` 逐列重核；PRD 附錄 A.4 的 7 列拆為 10 列，補「逐斷言判」與落地階段；另有 §5.4.2b 的 2 檔存在性依賴、§5.4.2c 的 3 檔非帳本讀取與 §5.4.1b 的路徑常數依附）

處置四值：`維持`、`改讀 export`、`改讀快照`、`隨被測碼退役`。OQ-1 已裁決採 (b)（快照固定單一目錄入 git），故 PRD A.4 第一列所稱「快照不入 git（OQ-1 選 d）則 CI 內 NE」的分支不成立，一律「改讀快照」。

| # | 測試（座標） | 讀什麼 → P3b 後影響 | 處置 | 落地階段 | 逐斷言判／備註 |
|---|---|---|---|---|---|
| 1 | `tools/tests/test_defect_id_reference_integrity.py:171-186`（`ledger_primary_ids()` 於 `:173`） | 真實缺陷帳本家族，全 repo 的 `DEF-…` 引用必須存在 → 新 DEF 只在 DB，引用新 DEF 的 commit 紅 | 改讀快照 | P3a | ID 全集改取「凍結檔∪最新快照」（快照入 git，CI 可驗）；快照缺席時 fail-loud 而非放行 |
| 2 | `tools/tests/test_adr_xplat001_c1c2_lock.py:102`（`_LEDGER`）、`:314-321`（`audit()`）、`:458-464`（`read_ledger()`／`read_family()`） | 讀主檔＋歸檔取 C1／C2 判準與輪次落款 → **P0 查明判準語意**：本鎖對 ID＞`_BASELINE_ID_CEILING` 的新列做家族全檔硬擋（ADR-XPLAT-001 §4.3：落入 §4.3.1 的列須有 C1 追溯、C2 觸發條件字樣）。P3b 後新 DEF 只在 DB，鎖只看得到凍結檔⇒**新列零命中、靜默 fail-open** | 改讀快照 | P3a | 讀快照目錄（或 `si export --kind defects`）的家族全列；輸入為空或缺新列時須 fail-loud。屬 `_GOV_EXACT`（根 `CLAUDE.md` 機械守衛總表），只能互動 session 改（PRD §8.3） |
| 3 | `tools/tests/test_check_defect_log_crossref.py:380`、`:388`、`:544` | 真實主檔做跨文件狀態一致（ONBOARDING 對 DEF 狀態宣稱 vs 帳本實況）→ 凍結檔不再更新、新宣稱無對照 | 改讀 export | P3a | 差分（AC-LD-13-1）：同輸入兩路徑（檔／`export --kind defects`）輸出逐位元相同；`--unresolved-count` 輸出契約不變 |
| 4 | `tools/tests/test_archive_defect_log.py`（全檔 72 處命中；真實家族讀取多處）、`tools/tests/test_check_archive_required.py`（3 處） | 歸檔輪替與強制觸發 → 輪替退役 | 隨被測碼退役 | P4 | 隨 `archive_defect_log.py` 等六檔（PRD §4 觀察 3）一併退役；其間（P3a～P3b）凍結檔不長、不觸發輪替，測試維持綠 |
| 5 | `tools/tests/test_selfimproving_issuemap.py:21`（`REAL_DEFECT_LOG`）、`:144-150`（`test_AT_IC_01_4_2_…`） | 真實缺陷主檔（PRD 記 271 列，隨帳本成長）→ 凍結檔仍在、位元組不變 | 維持 | 不需 | 逐斷言：(i)`len(rows) > 100`、(ii) 每列嚴重度欄首碼 ∈ P0～P4、(iii) `severity_of("def", …)` 皆有值——三者對**凍結內容**恆成立，不含「最大 ID／最新輪」語意。殘留：新缺陷的嚴重度不再被本測試看到⇒P3a 的 `def-add` 須以同一函式 `issuemap.severity_of("def", raw)` 驗證（寫入面守門），列入 P3a TCS 輸入 |
| 6 | `tools/tests/test_selfimproving_measure_probe.py:450-456`（`real = fx.ROOT / … / AutoSDD_Defect_Log.md`） | 真實主檔與合成檔各比對 `si_defs.load_ledger_status(path)` 與 `cdl._load_ledger_status()`（`mock.patch.object(cdl, "_DEFECT_LOG", path)`）→ 凍結檔上兩實作差分仍成立 | 維持 | P3a（隨改寫） | 逐斷言：差分斷言對凍結檔成立⇒維持；但 `check_defect_log_crossref` 於 P3a 改讀 export 時，`cdl._DEFECT_LOG` 與 `_load_ledger_status` 的補丁面改變⇒本測試隨該模組的改寫同批改為「FileStore 讀凍結檔 vs export defects」兩路徑差分 |
| 7 | `tools/tests/test_selfimproving_events.py:1696`（`res = self.check(fx.ROOT)`） | 對真實 repo 根跑 `check`；`db` 模式無 PG 即 fail-loud | 維持 | P1 | 靠夾具：`SiTestCase.setUp` 自 P1 起清 `SI_DB_DSN`、設 `SI_LEDGER_STORE=file`（AC-LD-02-2）；真實根在 file 模式讀的是凍結檔（P3b 後亦然） |
| 8 | `tools/tests/test_selfimproving_issues.py:1859-1864`（`run_raw(fx.ROOT, "check", "--json")` 於 `:1860`）、`:1923`（`timed_export(fx.ROOT)`） | 對真實根跑 `check` 與 `export`（含 ≤2 s 計時）→ 同 7 | 維持 | P1（夾具）；計時 AC 於 P3a 重判 | 計時斷言（AC-IC-12-1 的 ≤2 s）讀凍結檔，不受 `db` 影響；若 P3a 另設 PG 專屬計時，另案 |
| 9 | `tools/tests/test_selfimproving_events_p2.py:1119-1127`（子行程 `selfimproving.py check --json`，`cwd=fx.ROOT`，`env={**os.environ, "PYTHONUTF8": "1"}`） | 子行程對真實根跑 `check` → 繼承呼叫端環境 | 維持 | P1（驗證） | 該測試所在類別 `TestP2Checks(P2TestCase)`、`P2TestCase(SiTestCase)`（`_selfimproving_p2_fixtures.py:118`），子行程的 `env={**os.environ,…}` 取自 `SiTestCase.setUp` 已 patch 的環境⇒P1 在 `setUp` 清 `SI_DB_DSN` 即自動涵蓋；P1 TCS 仍須驗證（開發機設有 `SI_DB_DSN` 時此子行程不連庫），並逐支核實其餘跑 CLI 的 SI 測試（AC-LD-02-2「TCS 核實」） |
| 10 | `AutoClaude/tests/contract/test_ac_matrix_scaffolding.py:433-438`、`AutoClaude/tests/test_conftest_windows_native_skip_report.py:136-143` | `crossref.current_round()` ＋ `ledger.is_file()`（R210 起 `current_round` 讀 R 系列文件檔名最大號，**不讀帳本內容**） | 維持 | P4（退役審查時保留） | 約束：凍結檔不得刪、`check_defect_log_crossref.current_round` 不得退役（寫入 P3a／P4 TCS 的不得變更項）。盲實驗（§5.4.3）：缺帳本時 `test_conftest_windows_native_skip_report` 由通過轉 `[TOOL-ABSENCE]` skip（靜默降級，不是失敗），故「凍結檔不得刪」要靠約束與 §5.4.2b 兩檔報警，不能靠這兩支 |

**5.4.1b 另需處置的「路徑常數依附」（PRD AC-LD-02-5：「測試碼 17 處依附錄 A.4」，但 A.4 表沒有逐檔列出這 6 檔——本表補上）**：`LEDGER_REL`、`PROPOSALS_REL` 於 `tools/tests` 的 17 處／6 檔（`test_adr_xplat001_c1c2_lock.py`〔1，字串〕、`test_defect_id_reference_integrity.py`〔4，`_SISTER_LEDGER_RELS` 等〕、`test_selfimproving_events_p2.py`〔7，`OBS_LEDGER_REL` 夾具路徑〕、`test_selfimproving_events.py`〔2，`PROPOSALS_REL`〕、`_selfimproving_p3_fixtures.py`〔1，`si_events.LEDGER_REL`〕、`test_selfimproving_issues.py`〔2，`si_events.LEDGER_REL`〕）全部對**夾具 repo** 構造路徑，不讀真實內容。處置＝`維持`：`events.LEDGER_REL`、`events.PROPOSALS_REL` 保留為 FileStore 的路徑真相（P2 出口前不得刪、不得改名；AC-LD-02-5 只約束非測試碼）。

#### 5.4.2 其餘 20 檔：僅名稱提及 15 檔（a）、存在性依賴 2 檔（b）、`fx.ROOT` 讀非帳本檔 3 檔（c）

PRD `[C-7]`：`tools/` 四個主帳本名測試 26 檔，扣 5.4.1 內同屬這 26 檔的 9 檔，餘 17 檔＝(a)＋(b)（`test_selfimproving_events.py` 屬 5.4.1 第 7 列，以 `fx.ROOT` 讀真實根而非提及帳本名，不在這 26 檔內）；(c) 由 §5.4.4(b) 的 `fx.ROOT` 型根讀取普查另行找出。靜態普查把 17 檔都看成「只提及名稱」；**帳本盲實驗（§5.4.3）改判其中 2 檔為存在性依賴**——這正是補做動態實驗的價值。

**5.4.2a 僅名稱提及 15 檔（13 支測試檔＋2 支夾具模組；只在路徑字面、註解、夾具 repo 內提及帳本名，不讀真實內容，移除帳本後結果與對照相同；不需處置）**

| 檔 | 提及處（座標） | 性質 |
|---|---|---|
| `test_claim_provenance_r86.py` | `:1793` | 寫入暫存目錄的合成 `AutoSDD_Defect_Log.md` |
| `test_extras_quoting_zsh_safety.py` | `:114` | 豁免名單字面 |
| `test_sanitize_component_frozen_sdd_versions_lock.py` | `:12` | docstring 引缺陷座標 |
| `test_selfimproving_console_obs.py` | `:30`、`:815`、`:842` | 夾具 repo 路徑常數 `OBS_REL` |
| `test_selfimproving_check.py` | `:97`、`:99`、`:353`、`:354`、`:362` | 夾具路徑常數 |
| `test_selfimproving_capacity_retire.py` | `:222` | 夾具 `porcelain` 集合 |
| `test_selfimproving_research_scan.py` | `:1881`、`:1892`、`:2046` | 夾具複本內的路徑 |
| `test_selfimproving_props.py` | `:300`～`:302` | 情境路徑字串 |
| `test_selfimproving_p2_meta.py` | `:439`～`:441` | `non_evolvable_globs` 鏡像字面 |
| `test_selfimproving_measure.py` | `:36` | `EVL_REL` 常數 |
| `test_windows_smoke_heartbeat_doc_sync.py` | `:30`、`:75` | 排除清單 |
| `test_windowsapps_guard_cross_consistency.py` | `:583` | 註解 |
| `test_selfimproving_sandbox.py` | `:513`、`:514` | 過濾字串 |
| `_selfimproving_fixtures.py`（夾具模組，無測試） | 13 處 | 夾具常數（所有 SI 測試的建構基礎） |
| `_platform_helpers.py`（夾具模組，無測試） | `:15` | docstring |

**5.4.2b 存在性依賴 2 檔（不讀帳本內容，但斷言「文件宣稱的帳本路徑必須存在」；移除帳本檔即紅）**

| 檔與測試 | 提及處 | 處置 | 約束 |
|---|---|---|---|
| `test_doc_loc_baseline_freshness_r60.py`：`TestR81GhostPathClaims.test_no_ghost_path_claims` | `:3619` 註解；測試對文件內的路徑宣稱逐一驗存在 | 維持 | 凍結檔（含 `AutoSDD_Defect_Log_archive_*.md`、`_INDEX.md`）不得刪、不得改名 |
| `test_ntfs_trailing_space_device_name.py`：`TestRootDocsPathRefsAreCaseExact.test_the_three_r67_a15_citation_sites_resolve_exactly` | `:225`、`:529`、`:649`、`:666` | 維持 | 同上（引用的帳本路徑大小寫須精確且檔須存在） |

這兩項是 OQ-1「舊檔永遠保留」裁決的**機械承載**：P3b、P4 任何「刪檔／改名／搬目錄」的動作都會讓它們轉紅，應寫入 P3b、P4 TCS 的「不得變更」項。

**5.4.2c `fx.ROOT` 讀非帳本檔 3 檔（§5.4.4(b) 命中，不在 A.4、5.4.2a、5.4.2b；讀的標的都不是帳本，K 與 B 補跑結果相同；不需處置）**

| 檔 | 座標 | 讀取標的（非帳本） |
|---|---|---|
| `test_selfimproving_capability.py` | `:616`、`:669` | `fx.ROOT/.claude/settings.json`（斷言不含 selfimproving）；`fx.ROOT/tools/probe/selfimproving_measure.py`（量 import 時載入的模組） |
| `test_selfimproving_measure_verb.py` | `:29`、`:61` | 同一支探針（`PROBE`，以子行程執行） |
| `test_selfimproving_p3_meta.py` | `:37`～`:39`、`:212`、`:220`、`:285`、`:379` | `ROOT=fx.ROOT`：Operations SOP、真實 `params.json`（協定目錄，屬 P0 基準保護面）、AutoClaude 測試檔、測試節點收集 |

#### 5.4.3 帳本盲實驗（AT-LD-13-5-2、-E-1；補足純 Grep 普查看不到的「以路徑運算讀真實內容」與「存在性依賴」；2026-10-27 實跑）

純 Grep 只看得到「寫了帳本檔名或常數」的測試；實驗直接量**依賴**：

1. `git archive <base>` 展開兩個副本（B 對照、K 帳本盲），兩者皆 `git init`＋提交（實驗副本規則，§5.3.2）。
2. 在 K 副本刪除「六類帳本路徑」的工作樹檔案（本次共 75 檔＋提案目錄）：`docs/06_quality/SelfImproving_Observation_Ledger*.md` 與 `docs/05_development/SelfImproving_Observation_Ledger_notes.md`、`docs/06_quality/AutoSDD_Defect_Log*.md`（含 `_archive_*`、`_INDEX.md`）、`docs/06_quality/AutoSDD_External_Blocked_Log.md`、`docs/06_quality/AutoSDD_Structural_Debt_Log.md`、`docs/06_quality/SelfImproving_Event_Ledger.jsonl`、`docs/06_quality/SelfImproving_Proposals/`。（本次 K 只刪工作樹、索引仍列檔：對「枚舉追蹤檔再逐一讀」的測試會有人為不一致的雜訊，判讀以 5.4.2b 為準；重跑時應連同索引一併提交刪除。）
3. 兩副本各跑 §5.4.1 的 10 個 `tools/tests` 測試檔、§5.4.2a 的 13 支測試檔、§5.4.2b 的 2 檔、§5.4.2c 的 3 檔，共 28 檔（`python -m unittest discover -s tools/tests -p <檔>`，工作目錄＝副本根；**逐檔序列跑**——並行會有全域資源偽差異）；AutoClaude 兩支在 `AutoClaude/` 下以 `python -m pytest <檔> -q -p no:xdist -o addopts=` 另跑。
4. 判定：(a) K 相對 B 新增的失敗所屬測試檔 ⊆ §5.4.1 的 10 檔 ∪ §5.4.2b 的 2 檔；(b) §5.4.2a 的 13 支與 §5.4.2c 的 3 檔在 K 與 B 的 `rc`、收集數、失敗集合逐檔相同；(c) **非空轉**：新增失敗至少含一個 §5.4.1 的測試（否則實驗無鑑別力，AT-LD-13-5-E-1）。

**實測摘要**（逐檔明細不入本檔，審查者重跑取得）：(a)(b)(c) 皆成立。K 新增失敗全落在 A.4 的 9 檔（共 158 項：`test_archive_defect_log` 97、`test_check_defect_log_crossref` 42、`test_adr_xplat001_c1c2_lock` 10〔6 個類別 `setUpClass` 失敗，收集 187→152〕、`test_check_archive_required` 3、`test_defect_id_reference_integrity` 2、`events`／`events_p2`／`issuemap`／`measure_probe` 各 1）與 5.4.2b 的 2 檔（各 1 項）；A.4 第 8 列 `test_selfimproving_issues` 新增 0（副本上 `test_AT_IC_06_4_1_…_all_33_items` 本就基線紅而被遮蔽，依賴由 `:1860` 靜態可見）；5.4.2a 的 13 支與 5.4.2c 的 3 檔（8／18／10 項皆過）K 與 B 逐檔相同；AutoClaude `test_ac_matrix_scaffolding` 32 項皆過，`test_conftest_windows_native_skip_report` 缺帳本時由通過轉 `[TOOL-ABSENCE]` skip（靜默降級，不是失敗；故「凍結檔不得刪」要靠約束與 5.4.2b 兩檔報警）。A.4 因此補一類：5.4.2b 的存在性依賴，處置為維持並把「凍結檔不得刪、不得改名」寫入後續階段的不得變更項。

#### 5.4.4 重跑普查指令（G-P0-5）

```powershell
# (a) PRD [C-17] 兩條（Grep 工具或 rg；計數口徑＝命中行數）
#   tools/tests：ledger_primary_ids|_LEDGER\b|read_text.*Defect_Log|Defect_Log.*read_text|REAL_DEFECT_LOG|REAL_LEDGER|Observation_Ledger.*read_|LEDGER_REL
#   AutoClaude/tests：SelfImproving_Observation_Ledger|AutoSDD_Defect_Log|SelfImproving_Event_Ledger|SelfImproving_Proposals|current_round\(
# (b) 根讀取型（SI 測試）：
git -C <repo> -c core.quotepath=false grep -n -P '\bfx\.ROOT\b|REAL_ROOT|run_issues\(ROOT' -- 'tools/tests/*selfimproving*.py'
# (c) 四個主帳本名在 tools/tests 的檔案集合（應為 26 檔）：
git -C <repo> -c core.quotepath=false grep -l -P 'SelfImproving_Observation_Ledger|AutoSDD_Defect_Log|SelfImproving_Event_Ledger|SelfImproving_Proposals' -- 'tools/tests/*.py'
```

`<base>` 現查值：(a) `tools/tests` 156 處／9 檔、`AutoClaude/tests` 9 處／2 檔（與 PRD `[C-17]` 逐數字相同）；(b) **22 行／11 檔**＝A.4 的 `events`、`events_p2`、`issuemap`、`issues`、`measure_probe`（5 檔）＋5.4.2a 的 `capacity_retire`、`console_obs`、`p2_meta`（3 檔）＋5.4.2c 的 `capability`、`measure_verb`、`p3_meta`（3 檔）；(c) 26 檔 120 處。判定：(a) 命中檔 ⊆ A.4 ∪ 5.4.1b ∪ 5.4.2a／b（9 檔中 `_selfimproving_p3_fixtures.py` 只在 5.4.1b）；(b) 命中檔 ⊆ A.4 ∪ 5.4.2a／b／c；(c) 集合＝A.4 的 9 檔 ∪ 5.4.2a／b 的 17 檔。

### 5.5 棘輪預演（AC-LD-13-7；D7）——`repin_growth_problems()`／`repin_cost_ratchet_problems()` 唯讀預演

**方法**：不改任何檔；import `tools/tests/test_adr_xplat001_c1c2_lock.py`，取真實 `_GUARD_LINES_REPIN_LOG`（358 列）、`_REGRESSION_LANE_LOG`、`_REPIN_APPROVED_ROUND_OVERAGE`，於記憶體附加各階段預估增量列後呼叫 `repin_growth_problems(log, regression_lane=…, approved_overage=…)`；S-B 另在記憶體模擬款(12) 到期義務（追加上限表一列、重新武裝到期常數）並呼叫 `repin_cost_ratchet_problems(latest_round=…, current_cap=…, due_round=…, due_target=…)`。增量取 PRD §8.3 量級（無實測）：低＝P0 +420、P1 +1,500、P2 +515、P3a +1,500、P3b +515、P4 −4,228；高＝+515、+2,500、+515、+3,000、+515、−4,228。預演腳本全文與完整輸出表入 `docs/06_quality/SelfImproving_LedgerDb_P0_Ratchet_PreRun.md`（D7；契約節 C6 ②③）；下表是該腳本於 `<base>` 的輸出（2026-10-27 實跑，rc 0）。

**基準**：log 358 列；當前輪 R214；名冊 6／6（R101、R129、R145、R171、R213、R214）；R214 名冊精確淨額 15,220（＝逐列淨額合計 15,529 減回歸鎖軌 309）；每輪上限 515（`:2872`）；到期輪 R216／目標 514（`:3539-3540`）；連續上升上限 2；回歸鎖軌上限 309；`repin_growth_problems()` 與 `repin_cost_ratchet_problems()` 的基準回傳皆為空。

**S-A　同標籤續列**（標籤＝當前輪 R214；本鎖「重釘標籤不得超前帳本當前輪」使它成為預設路徑；到期輪 R216 未到，款(12) 不觸發）：每階段名冊「未重登」回傳 `[超出每輪上限]`（R214 淨額本已超限）；「重登」＝R214 名冊精確淨額改為 `15,220＋Σ 各階段增量`，重登後回空、名冊筆數不動（6／6）。公式與三例（完整 12 列入證據檔）：

| 方案 | 階段（累計增量） | 精確淨額須改為 | 重登後回傳 |
|---|---|---|---|
| 低 | P0（+420） | 15,640 | 空 |
| 高 | P3a（+515＋2,500＋515＋3,000） | 21,750 | 空 |
| 低 | P4（累計淨減至 −4,228 後） | 15,442 | 空（仍遠高於每輪上限：名冊項不能退場，只能改值） |

**S-B　輪號前進**（僅在帳本當前輪因他事前進後可用；每階段新標籤 R215～R220）：稽核痕跡一走到 R216，款(12) 即要求往上限表追加更小的一列並重新武裝（到期輪＝兌現輪＋2、目標＝新上限−1），所以**該輪上限逐輪遞減**；低、高兩方案的旗標相同：

| 階段（標籤） | 該輪上限 | 款(12)（未兌現→兌現後） | 無名冊項的回傳 | 名冊累計＝上限須上修為 |
|---|---|---|---|---|
| P0（R215） | 515 | 空→空（到期輪 R216 未到） | 空（低 +420、高 +515 皆 ≤515） | 6 |
| P1（R216） | 514 | `[到期未下修]`→空：追加 (R216, 514)，重新武裝 R218／513 | `[超出每輪上限]` | 7 |
| P2（R217） | 514 | 空→空 | `[超出每輪上限]`（+515 > 514） | 8 |
| P3a（R218） | 513 | `[到期未下修]`→空：追加 (R218, 513)，重新武裝 R220／512 | `[超出每輪上限]` | 9 |
| P3b（R219） | 513 | 空→空 | `[超出每輪上限]`（+515 > 513） | 10 |
| P4（R220，−4,228） | 512 | `[到期未下修]`→空：追加 (R220, 512)，重新武裝 R222／511 | 空（淨減） | 10 |

**結論（入證據檔〈結論〉節）**：

1. **預設路徑是 S-A**：重釘標籤不得超前帳本當前輪（`test_check_defect_log_crossref.py::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`；當前輪＝`python tools/check_handoff_carriers.py` 首行）；本案各階段沒有自己的 R 系列證據檔，故同標籤續列。名冊筆數不動，但 **R214 精確淨額須在每一個有測試行變動的階段（P0、P1、P2、P3a、P3b、P4）各重登一次**——含 P0 的 +420、P2／P3b 的 +515，以及 **P4 的淨減**（淨額減到 15,442 仍遠高於上限，名冊項不能退場）。PRD §8.3 的「P2、P3b 各 ≤+515」在 S-A 下不是約束。
2. **S-B 的代價遠高於 S-A**：每階段多付一次鎖檔改動（P1、P3a、P4 各追加上限表列並重新武裝到期常數），名冊要四次可見上修（`_REPIN_APPROVED_ROUND_OVERAGE_MAX_ENTRIES` 6→7→8→9→10，P1、P2、P3a、P3b 各入一列）；P2、P3b 須壓到 ≤+514／≤+513 才免入名冊。S-B 只在當前輪已因他事前進時才需評估。
3. 名冊內「已核准」輪次不計入 `[只升不降]` 的連續上升計數；不入名冊又 >0 的相鄰輪（例如 S-B 的 P0 之後緊接未核准的正淨額輪）須確保連續不超過 2 輪或其間有淨減輪。
4. 預演表的「低／高」是 PRD §8.3 量級（無實測）；P0 欄的 +420／+515 是 DT 瘦身前的估量，瘦身後預期更小，但任何增量下 S-A 結論不變（R214 本已超限，須重登精確淨額）。實作棒收尾時以 `--print-guard-lines` 的真實淨額為準，重跑腳本核對。

### 5.6 P0 基準值（AC-LD-02-6、AC-LD-11-1；D8；`<base>` 現查，值於 `000a217b` 與 `99c9a868` 相同）

| 項 | 值 | 取得指令 |
|---|---|---|
| 基準 commit | P0 起點 `<base>`（P0 不改 `tools/`、協定目錄、守衛面，故程式面基準＝該 commit）；**P0 出口基準 commit** 由主控於收尾以 `git rev-parse HEAD` 現取，寫入基準檔（基準檔由緊接其後的獨立 commit 入庫，故不含自身） | `git rev-parse HEAD` |
| `SelfImproving_Protocol/metrics.md` | 8,022 bytes；sha256 `d4762244fc21cde5c3b617c2c8372e33dab2dfe4770841d08b7a829e9375581b`；CR 0 | `Get-FileHash -Algorithm SHA256` |
| `SelfImproving_Protocol/params.json` | 1,994 bytes；sha256 `fc48653bfa0107012d2b5316a64bb5ec6d2bac3cdb373b967e7f10ddca1bf197`；CR 0 | 同上 |
| `SelfImproving_Protocol/research_sources.json`（排除於指紋） | 4,721 bytes；sha256 `6a3993e985a6fd530c99641414423c2befb67aa83999af39185642804706ef0a` | 同上；`FINGERPRINT_EXCLUDED`（`params.py:15`） |
| `params.fingerprint()` | `sha256:1d14bfdbd15e1f6832f45832177b9f3278f7d3caf3b415cb5cdbfc7777d625fd`；分量：`manifest`＝`695b70352f5ba6bcb775f9ab77adc5d5c33c2e1591ddf213ce6266cec59afddc`、`metrics_rev`＝1、`check_rules_rev`＝4 | `python tools/selfimproving.py check` 尾行，或 `lib.selfimproving.params.fingerprint(repo, params_dict)` |
| `CHECK_RULES_REV` | 4（`tools/lib/selfimproving/params.py:13,139`；釘於 `tools/tests/test_selfimproving_p3_meta.py:292`） | `git grep -n CHECK_RULES_REV -- tools` |
| `items=33` 釘（10 處；**GT 判定，不入 DT**） | `test_selfimproving_capability.py:624`、`test_selfimproving_check.py:722`（`(ITEMS21, 33)`）與 `:736`、`test_selfimproving_events.py:1200`、`:1490`、`:1907`、`:2273`、`test_selfimproving_events_p2.py:874`、`test_selfimproving_issues.py:1864`、`test_selfimproving_measure_verb.py:80` | `git grep -n -P -e 'items=33' -e 'all_33_items' -e '\b33\b.{0,30}items' -e 'items.{0,30}\b33\b' <base> -- 'tools/tests/*selfimproving*.py'` 得 10 行，扣 `test_selfimproving_issues.py:1859`（測試名）、加 `test_selfimproving_check.py:722`（該行不被正則涵蓋）＝10 處（Grep 工具的引擎少列 `:1864`，須用 `git grep -P`） |
| `si check`（file 模式，真實 repo 或含歷史的 `git clone --no-local` 副本；`git archive` 副本不可用） | rc 0；首行 `si-check rows=332 items=33`；尾行 `overall=PASS rc=0 fingerprint=sha256:1d14bfdb…d625fd`；含 `CONSOLE-KEY-MISSING` 警示行（金鑰環未設；與環境有關，取證程序須清除 `SI_*`、`AUTOSDD_*`） | `python tools/selfimproving.py check` |
| skip 摘要（win32 剖面） | 開發機 2026-10-27 全套實跑（主控同日全套實跑的日誌，非契約依據）：`[skip census] tools/tests@win32 共 46 支：platform=42／tool-absence=0／env-disabled=4／structural-pair=0／debt=0／untagged=0／欠債型 4 支（目標 0）` 與 `SKIP-M6` 行「集合關係成立（本次 46 支）」；**基準以 P0 收尾實跑為準**（env-disabled 4 支＝本機無建立 symlink 權限，屬環境、非缺件） | `python tools/run_root_unittests.py`（不接管線） |
| `docs/06_quality/skip_id_ledger.json` | 23,705 bytes；sha256 `212c15925ae286e630ba23373706a57e048fa292815bb8f597d8bf62782dc909`（AC-LD-11-1：落款不需變動） | `Get-FileHash` |
| 不納入（OQ-5 裁決） | `FiveQuestion_Round_Ledger.jsonl`（38,974 bytes；sha256 `2069507abd4b8852db4d2e3b049f1b2ebcba216db386b0ba11c3bcb92c0372b3`）與 `skip_id_ledger.json` 另案；此處只作「P0 不動」的雜湊記錄 | 同上 |

### 5.7 允許變更的檔案集合（G-P0-1：`git diff --name-only <base>..<tip>` 必須 ⊆ 5.7.1，且 5.7.2 的路徑必須零輸出）

「同步鎖」＝PRD §9.4 的〈需同步改的既有鎖〉逐項重核（§5.8）。P0 只碰其中與「新測試檔」「Root_Layout」「compat-ci paths」「重釘」相關者；其餘為 P1 以後。

#### 5.7.1 允許集合

| 路徑 | 類別 | 內容 |
|---|---|---|
| `docs/02_architecture/ADR-SIDB-001-truth-source-and-db-location.md`、`-002-dal-and-modes.md`、`-003-integrity-append-only-chain-replay.md`、`-004-read-model.md`、`-005-write-serialization.md`、`-006-console-carrier.md`、`-007-credentials-and-tls.md`、`-008-snapshot-and-offsite-backup.md` | 新增 | D3（slug 見 §5.2.1） |
| `docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md` | 新增 | D4 |
| `docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md`、`…_P0_Baseline.md`、`…_P0_Ratchet_PreRun.md` | 新增 | D5、D8、D7 |
| `docs/03_testing/contracts/TCS-SelfImprovingLedgerDb-P0-20261027.md` | 新增 | 本檔 |
| `tools/tests/test_selfimproving_ledgerdb_p0.py` | 新增 | 唯一新測試檔（上限 3，實用 1） |
| `docs/06_quality/SCG4-REVIEW-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md`、`docs/06_quality/RTM-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md` | 新增 | 主控／QA 收尾（Root_Layout §2 審查／RTM 列） |
| `docs/02_architecture/Root_Layout_and_Module_Placement.md` | 修改 | §1 一列、§2 兩列、§3 SelfImproving 列補登記（C1） |
| `.github/workflows/windows-compat-ci.yml`、`macos-compat-ci.yml` | 同步鎖 | `paths`（push 與 pull_request 各處）加 `docs/02_architecture/ADR-SIDB-*.md`、`docs/02_architecture/SelfImproving_LedgerDb_Architecture_Draft.md`、`docs/06_quality/SelfImproving_LedgerDb_P0_*.md`（Root_Layout、`SelfImproving_Protocol/**`、`SelfImproving_PRD.md` 已在 paths 內）；精確清單以 `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` 為準（G-P0-12；先例：`windows-compat-ci.yml:246-247`、`:734-735`） |
| 收尾單人窗口重釘面（鐵律七；開發棒不碰）：`tools/tests/test_adr_xplat001_c1c2_lock.py`、`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`（尾端 R214 標記行與附記）、`docs/04_planning/AutoSDD_improving_112.md`（尾端一行）、`tools/lib/skip_tag_policy.py`（`_TREE_FILE_FLOORS['tools/tests']` 89→90）、`tools/lib/guard_bucket_policy.py`（`_FROZEN_SHRINK_ONLY_BUCKET_LINES` 的 `prose`，須帶四方複審裁決，§5.9 #5）、`tools/run_root_unittests.py`（`MIN_TESTS`，若 `min_tests_margin` 判準說話才改） | 同步鎖（收尾） | §5.9 逐項；不得出現未列於 §5.9 的重釘面 |

#### 5.7.2 不得變更（全部零輸出）

`tools/lib/**`（含 `tools/lib/selfimproving/**`）除上表 `skip_tag_policy.py`、`guard_bucket_policy.py` 兩支重釘常數外一概不動；`tools/selfimproving.py`、`tools/probe/**`、`docs/06_quality/SelfImproving_Protocol/**`（含 `params.json`）、`docs/06_quality/SelfImproving_Observation_Ledger*.md`、`docs/05_development/SelfImproving_Observation_Ledger_notes.md`、`docs/06_quality/AutoSDD_Defect_Log*.md`、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md`、`SelfImproving_Event_Ledger.jsonl`、`SelfImproving_Proposals/`、`docs/06_quality/skip_id_ledger.json`、`docs/06_quality/FiveQuestion_Round_Ledger.jsonl`、`.claude/**`、`settings*.json`、守衛面清單檔（根 `CLAUDE.md`〈守衛面准入〉）、`AutoClaude/**`、`AISDLC_SDD/**`、`AgentConsole/**`（含 `Architecture.md`、`docker/README.md`）、**凍結上位文件 `docs/01_requirements/SelfImproving_PRD.md`、`docs/01_requirements/Issue_Center_PRD.md`、`docs/01_requirements/SelfImproving_Ledger_DB_PRD.md`**（P0 零凍結文件變動：E-n 全備案；本案 PRD 的 §7.2 勘誤一由主控於 Stage-2 凍結前貼入，早於 `<base>`）、`tools/tests/` 內除新測試檔與 `test_adr_xplat001_c1c2_lock.py` 外的一切既有檔。

> 開發階段（未 commit）`docs/06_quality/` 的新增只准 5.7.1 列的三份 `SelfImproving_LedgerDb_P0_*.md`（與收尾的 SCG4／RTM）；其餘 `docs/06_quality/` 路徑零差異。

#### 5.7.3 棒切分與依賴順序（鐵律七：並行包的持有面不得相交）

依賴：①文件（ADR、Architecture 草稿、案文、基準檔、預演檔；彼此不依賴）→ ②Root_Layout 的 §3 登記（路徑須已存在，否則 `registry_problems` 紅）→ ③新測試檔 DT（讀①②）→ ④收尾單人窗口重釘（所有 `tools/tests` 改動定稿之後；鎖檔屬 `_GOV_EXACT`，只能互動 session）。建議切棒：甲＝ADR-001、002、004～008；乙＝ADR-003（SQL 草稿與 14 表矩陣；另做 G-P0-7 烟測）；丙＝Architecture 草稿＋案文證據檔；丁＝基準檔＋預演檔；戊＝Root_Layout 修訂＋新測試檔（C1.1 字樣的常數面與消費端不可拆給兩棒）；己＝主控收尾窗口。甲～丁可並行；戊的 DT 以①完成為綠燈條件；己最後。

### 5.8 PRD §9.4 的「需同步改的既有鎖」於 `<base>` 重核（只列 P0 動到或引用者）

重核方法＝逐座標讀檔比對；「吻合」＝行號與內容與 PRD 敘述一致。P1 以後才動的鎖（能力登記 `test_selfimproving_capability.py`、`tools/selfimproving.py` 動詞表、`check.py`、`skip_group_policy`／`skip_runtime_report`、pre-commit／pre-push／root-infra-ci 的帳本閘、Console 各列）座標由該階段 TCS 於當時 HEAD 重核，P0 不核。

| 座標 | 結果 |
|---|---|
| `Root_Layout_and_Module_Placement.md:29-42`（§2 落點表 14 列）、`:52`（SelfImproving 登記列） | 吻合 |
| `tools/tests/test_adr_xplat001_c1c2_lock.py:554,595`（只數 `tools/tests/*.py`）、`:2872`（`(214, 515)`）、`:2856,2877`（連續上升 2）、`:2888`、`:2979`（名冊上限 6）、`:2946-2970`（R214 名冊列）、`:3539-3540`（到期輪 216／目標 514）、`:3878`（`repin_growth_problems`）、`:3967`（`repin_cost_ratchet_problems`）、`:4491-4496`（子目錄＝繞道）、`:8718`（`_REPIN_REASON_MAX_CHARS`） | 吻合（名冊 6 列＝R101、R129、R145、R171、R213、R214） |
| `tools/lib/skip_tag_policy.py:310-314`（`_EXTRA_SCAN_TREES` 不含 `tools/tests_pg`）、`:424`（`"tools/tests": 89`）；`tools/run_root_unittests.py:44`（`MIN_TESTS`）、`:333-336`（`start_dir` 為 `tools/tests` 才評 `SKIP-M6`） | 吻合 |
| `tools/lib/guard_bucket_policy.py:277`（`measure_shrink_only`）、`:290`（`_FROZEN_SHRINK_ONLY_BUCKET_LINES`）、`:385-391`（先例註解與 `"prose": 5060`）、`:436-441`（`[分桶成長]`）、`:409`（`BUCKET_STALE_SLACK`） | 吻合 |
| `tools/lib/selfimproving/params.py:13`（`CHECK_RULES_REV = 4`）、`:15`（`FINGERPRINT_EXCLUDED`）、`:128-141`（`fingerprint`）；`test_selfimproving_p3_meta.py:292` | 吻合 |
| `AutoClaude/tools/check_loc_budget.py:276-283`（`ROOT_TOOLS_TIERS`）、`:296`（`ROOT_TOOLS_EXCLUDED_DIRS={"tests"}`）、`:551`、`:318-340`（`count_loc`） | 吻合 |
| `.github/workflows/windows-compat-ci.yml:241-250,729-738`、`macos-compat-ci.yml:104-112,600-608`（compat-ci `paths`；`Root_Layout` 已在 `:250`／`:738`） | 區段存在；先例行 `:246-247`、`:734-735` |
| `AgentConsole/docs/02_architecture/Architecture.md:612-618`（§7.2 表，末列 `issue_priority`）、`:854-870`（§9.4）、`:944-956`（§10.3）；`Issue_Center_PRD.md:4,204,415,419`；`SelfImproving_PRD.md:491,527,791-793,811,904-905,987-990,997,999` | 吻合（§5.1.3 逐條引用） |

### 5.9 新測試檔 `test_selfimproving_ledgerdb_p0.py` 會撞的鎖與出口（實作棒與收尾窗口的清單；順序＝建議）

| # | 鎖（座標） | 觸發與預期 | 出口 |
|---|---|---|---|
| 1 | 行數棘輪（`test_adr_xplat001_c1c2_lock.py` 的 `_FROZEN_GUARD_LINES` 逐檔表、`guard_line_problems` 的 `[新增]`／`[成長]`／`[基準過時]`） | 新檔必入逐檔表；淨額上升＝紅，直到重釘 | 收尾窗口：先把所有 `tools/tests` 改動定稿，再 `python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；逐檔表加本檔、`_GUARD_LINES_REPIN_LOG` 追加一列（標籤＝當前輪 R214；理由含 `[非淨減法輪]`、指名一份 `CrossPlatform_R\d+_\w+\.md`、**≤700 字元**〔`_REPIN_REASON_MAX_CHARS`，`:8718`〕、不得寫死「N 支／N 列」、tuple 行加 `# round-label-ok`）、`_REPIN_LOG_FROZEN_PREFIX_LEN` +1、`_FROZEN_PREFIX_REWRITE_LEDGER` 追加、`_REPIN_LOG_HISTORY_SHA256`；最後一次 print 為 `+0`、`逐檔漂移 0 支`。🔴 該檔在 `.claude/hooks/block_destructive_git.py:1459` 的 `_GOV_EXACT`（治理檔禁寫面）內：`AUTOSDD_UNATTENDED` 下唯讀，重釘只能在互動 session 由主控做 |
| 2 | 單輪淨額上限 515、連續上升 2、名冊（`repin_growth_problems`；§5.5） | S-A：R214 名冊精確淨額由 15220 改為 15220＋本檔淨額（預演：+420 → 15640；+515 → 15735）；名冊筆數不動 | 改 `_REPIN_APPROVED_ROUND_OVERAGE['R214']` 的第一個元素並在理由末尾追加一段（沿 `:2946-2970` 的續列體例） |
| 3 | 回歸鎖軌（`_REGRESSION_LANE_LOG`；R214 已申報至軌上限 309） | 本檔 AT 不屬「結案回歸鎖」性質，P0 不申報；全額歸主軌 | 不動 |
| 4 | doc-total 兩站點（`<!-- guard-total:R214 -->`） | 兩份不同檔各追加（append 在最後） | `CrossPlatform_R145_Scan_Findings.md` 尾端附記＋`AutoSDD_improving_112.md` 尾端一行 |
| 5 | 分桶棘輪（`guard_bucket_policy.py`：函式 `measure_shrink_only` `:277` 量；凍結基準在常數 `_FROZEN_SHRINK_ONLY_BUCKET_LINES` `:290`，`"prose"`＝`:391`；`prose`、`guard_self` 兩桶 shrink-only） | 本檔是文件結構測試，類別 chunk 多只參照 `docs/` 字樣⇒歸 `prose` 桶（瘦身後預估 +200～+300 行，收尾實測為準）：**成長即紅**（`[分桶成長]`，`:436-441`）；`BUCKET_STALE_SLACK`（`:409`）只管「縮小後未重釘」的過時判（`[分桶基準過時]`），不是成長的餘裕 | 先瘦身（一審 F-04：DT 只留時間穩定謂詞、一次性驗收移 GT）；仍成長則由收尾窗口帶**四方複審裁決**重釘常數（`:439-440`；本鍵依據＝SCG-4 審查 PASS＋主控依凍結常態規則裁定），**理由寫在常數的註解**（先例 `:385-390`；不登缺陷帳本——§5.7.2 禁動帳本）；取實測：`python tools/probe/guard_layer_bucket_census.py --grain chunk --jsonl <輸出檔>`（🔴 `--jsonl` 是**輸出路徑**，會覆寫該檔：先 commit 成品、輸出檔放 scratchpad） |
| 6 | 檔數下限（`tools/lib/skip_tag_policy.py::_TREE_FILE_FLOORS['tools/tests']`＝89；`TREE_FLOOR_RATIO`＝0.8） | 112→113 支 `test_*.py`：`int(113×0.8)=90 > 89`⇒「下限已過期」判紅，且根層 runner 在前置早退、**一支測試都沒跑**（rc=1 但零 FAIL 行） | 重釘為 90；🔴 早退＝閘門未過，不得改跑 pytest 子集替代 |
| 7 | ruff 全規則（`tools/ruff.toml:50` `select = [E,F,I,UP,W,S102]`；只有 E501 對 `tests/*.py` 豁免〔`:82`〕；執行者＝`root-infra-ci.yml:486` 第 16 道與 `tools/git-hooks/pre-push` 第 ④ 段）＋E501 存量棘輪（`test_subprocess_encoding_hygiene.py::TestRootToolsLintPolicy::test_e501_debt_only_shrinks`） | DT 在 `sys.path` 插入後才 import 同目錄模組，最易踩 I001（排序）、F401（未用 import）、UP；本檔每行 ≤100 寬⇒不新增 E501 債 | 先 `ruff check --no-cache <檔>` 與 `ruff check --isolated --select E501 --line-length 100 --output-format concise <檔>` 清零，不得上修棘輪（G-P0-11）；收尾再跑 `ruff check tools/ .claude/hooks/ --no-cache`（G-P0-12） |
| 8 | 整檔缺席斷言鎖（`test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale`，掃全部根層 `test_*.py`） | 本檔不得 `assertNotIn(文字, 整份文件)`、不得對讀入文字做寫死數字切片 | 一律逐行判定（B-06） |
| 9 | compat-ci `paths`（`AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py`） | 新 DT 消費 ADR、Architecture 草稿、三份證據檔⇒兩支 compat-ci 的 `paths`（push／pull_request 各一）須含這些路徑，否則 SDD ci-gate 紅（本機根層與 AutoClaude 全套抓不到） | 加 `paths`；新增檔**之後**重跑 `AISDLC_SDD/scripts/ci-gate.ps1`（2026-09-22 先例：漏此步使雲端兩支 smoke 翻紅） |
| 10 | `MIN_TESTS` 零相依餘裕（`tools/lib/min_tests_margin.py`；`run_root_unittests.MIN_TESTS`＝5996） | 本檔純標準庫，+14～+18 收集⇒零相依餘裕 −14～−18；餘裕門檻帶（滿格的 50%／25%，另有實跑數 5% 的絕對軸）說話才重釘 | 以 `min_tests_margin` 的 `headroom_message` 現查；說話才改 `MIN_TESTS`（只准上修） |
| 11 | 超前輪號鎖（`test_check_defect_log_crossref.py::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound`，掃 `git ls-files` 的程式碼檔） | 本檔註解與 docstring 不得含 > R214 的輪號；合成語料同行加 `round-label-ok` | 寫作時避開 |
| 12 | 全 repo 引用完整性（`test_defect_id_reference_integrity.py` 掃 `DEF-…` 字面；R18 掃 `OBS-SI-` 接數字） | 本檔與全部 P0 文件不得含未登記的 `DEF-`／`OBS-SI-` 字面 | 只引已登記者（本檔只引缺陷帳本主檔已有列的 `DEF-200-570`、`DEF-200-572`）或中性字串 |
| 13 | 文字 I/O 編碼（`test_platform_neutral_paths.py::TestTextIoDeclaresEncoding`，`:2143`，AST；掃描面 1,167 檔，+1 不越界） | 新檔每個 `open`／`read_text`／`write_text` 須帶 `encoding=`（B-01 的 `read_doc()` 以位元組讀再解碼，不觸發） | 寫作時避開 |
| 14 | 雜湊排序鍵（`test_platform_neutral_paths.py::TestDigestSortKeyIsPlatformNeutral`，`:5693`） | DT 若以 `hashlib` 逐檔算基準 sha256，`for … in sorted(<glob／rglob／iterdir>)` 餵 digest 時須帶 `key=` | 檔名寫死逐檔算，或 `sorted(…, key=…)` |
| 15 | 腳本入口守衛（`test_doc_loc_baseline_freshness_r60.py::TestMainGuardIsTheLastTopLevelStatement`，`:7138`） | `if __name__ == "__main__":` 須為檔內最後一個頂層敘述（`_stdio_utf8` 的 import 放其內） | 檔尾即守衛 |
| 16 | 無反應項 | skip 靜態標籤掃描（本檔無 skip 裝飾器）；AT 錨定鎖（`test_selfimproving_p2_meta.py:88`／`p3_meta.py:281` 只解析 `TCS-SelfImproving-P<n>-*.md`，本檔 `TCS-SelfImprovingLedgerDb-…` 不符該 glob） | 不動 |

## 6. RTM 連結確認

### 6.1 AC／交付項 → AT（數字由 §1、§3 機械計算）

| 項 | AC／交付項數 | 正向 AT | 反向 AT | 載具 | R 條文 |
|---|---|---|---|---|---|
| FR-LD-02（AC-LD-02-6，P0 基準半） | 1 | 2 | 2 | DT、GT | R-LD0-26、27、28、29 |
| FR-LD-11（AC-LD-11-1 基準半＋AC-LD-11-4） | 2 | 6 | 3 | DT、GT | R-LD0-01～08、26 |
| FR-LD-13（AC-LD-13-5、AC-LD-13-7） | 2 | 5 | 2 | GT、DT | R-LD0-20～25 |
| FR-LD-00（D3、D4、D5、D9、D10） | 5 | 15 | 2 | DT、GT | R-LD0-09～19、30、31、32 |
| 合計 | PRD AC 5／5；交付項 D1～D10 全覆蓋 | 28 | 9 | DT 14、GT 23 | R-LD0-01～R-LD0-32（32 條） |

D1、D2（掛 AC-LD-11-4）、D6（掛 AC-LD-13-5）、D7（掛 AC-LD-13-7）、D8（掛 AC-LD-02-6 與 AC-LD-11-1）不另佔列。**機械核對**：QA 對 §1.1、§1.2、§3.2、R 條文表自備腳本（計數腳本已移出本檔），輸出貼進審查報告；期望：AT 37（正 28、反 9；DT 14、GT 23）、映射表與清單互無缺漏、P0 範圍 PRD AC 覆蓋 5／5、R 條文 AT 欄無懸空、無未被 R 引用的 AT、PRD 58 條＝本鍵 5＋§1.2 展開 53。

### 6.2 NFR（PRD §6）→ AT

| NFR | 條文 | 覆蓋 AT |
|---|---|---|
| 零侵入 | 不動守衛面、`params.json`、協定目錄、`tools/`、兩引擎、Console 檔、凍結上位文件 | 02-6-E-2、D9-1、D4-2、D5-3、D5-4 |
| 跨平台 | 文件 LF、無 BOM；`sql/` 遷移檔 LF 與 sha256 口徑；Windows 長路徑展開 | 全部 DT（B-01）、11-4-2、11-4-4（B-09） |
| 安全 | P0 文件不含連線字串、密碼；SQL 草稿角色三分與非擁有者不能停用觸發器 | D3-4、D3-5 |
| 可逆 | P0 回退點＝丟棄文件（PRD §8）：交付全為文件與一支測試檔，`git revert` 即回 | D9-1（允許集合）；無執行期面可回退 |
| 誠實劃界 | 乾跑實驗的盲區（基線紅被遮蔽者以 git 索引第二輪補看）、帳本盲實驗的盲區（只看得到「以路徑運算」的依賴，看不到網路或家目錄依賴） | 11-4-4、13-5-2（B-10） |

### 6.3 R→AC 與 AC→R 連結

R 條文表每條 R 的 AT 欄皆指向存在的 AT 或 G 閘；P0 範圍 PRD 的 5 條 AC 每條至少被一條 R 引用、每個 AT 至少被一條 R 引用（§6.1 的自備腳本檢查）。RTM 回填：`docs/06_quality/RTM-SelfImprovingLedgerDb-P0-<YYYYMMDD>.md` 由主控於收尾產出（Root_Layout §2 審查／RTM 列）。

## 7. 本檔採用的預設裁決（Q-LD0-1～10 已結案；掌舵者可隨時以 T1 推翻）

### 7.1 裁決表（QA 預設＋主控代決 2026-10-27；本節無開放問題）

| # | 裁決 | 內容（出處／理由） |
|---|---|---|
| 1 | ADR 檔名與編號 | `ADR-SIDB-00N-<slug>.md`（三位數）；PRD 文內 `ADR-SIDB-01` 視為簡稱。WHY：Root_Layout §2 的 `ADR-<MOD>-NNN-<slug>.md` 與 `ADR-AGT-001` 先例；PRD §9.4 與 §9.5 自相不一（§7.2 勘誤 1-8） |
| 2 | Architecture 草稿 | 獨立檔、P0 不改 `Architecture.md`／`docker/README.md`：其 digest 凍結在 `agentconsole-si-decide`／`-mirror`，`si.*` 表建好前寫進去是不實陳述；補丁隨 P1（§9.4）、P2（§10.3）、P3（§7.2、docker README〈4.3〉）套用 |
| 3 | 勘誤案＝**全備案**（Q-LD0-3 結案） | E-1～E-7 在 P0 只備妥於案文證據檔，**P0 零凍結文件變動**；各條於案文的「套用階段」（E-1、E-5→P1；E-2、E-6→P2；E-3、E-4→P3a；E-7→P3b）由該階段鍵於 hooks-OFF 視窗改上位檔並 `spec-refreeze`（SI PRD 側六鍵各一次；議題中心側 `monorepo-issue-center` 先、`agentconsole-issue-center` 隨後並同步 `TCS-IssueCenter` 檔頭 digest）。WHY：E-1～E-5 的原則已獲裁決，但文字要到 PG 影子（P1）起才為真；今天改凍結 PRD 要動八把鍵（兩把 `RELEASE_READY`）。E-4 引用的掌舵者核准座標由主控於 Stage-2 凍結時填（佔位 `〈sid／line 由主控填〉`） |
| 4 | Root_Layout 兩格 WHY | `tools/tests_pg/`：真 PG 測試不能住 `tools/tests`（runner discover 根、skip 政策、行數棘輪、第三方相依鎖皆以它為根）；代價＝仍受 LOC 分級與 ruff 全規則（乾跑實測 E501 不被 `tests/*.py` 豁免涵蓋）。`sql/`：遷移檔是資料不是程式，能力登記只掃套件根層 `*.py`；根 `.gitattributes` 使 sha256 跨平台一致 |
| 5 | 測試載具（Q-LD0-1 結案） | DT 14／GT 23；**新測試檔恰 1 支、純標準庫、瘦身**：DT 只留時間穩定謂詞（格結構、ADR 六節結構、基準等式、案文結構、合成自證）；一次性驗收（內容字樣、乾跑、盲實驗、預演、勘誤逐字）一律 GT。WHY：P1 起任何會隨階段合法改變的斷言都是必誤紅（一審 F-04）；prose 桶 shrink-only，成長須帶四方複審裁決（`guard_bucket_policy.py:439-440`），瘦身即省稅 |
| 6 | 重釘標籤（Q-LD0-5 結案） | S-A：R214 同標籤續列（標籤鎖禁超前）；名冊筆數不動，每個有測試行變動的階段（含 P4 淨減）重登精確淨額。S-B 只在當前輪前進後可用，且逐輪遞減上限、名冊 6→10（§5.5） |
| 7 | A.4 處置 | OQ-1 採 (b)：讀真實內容的測試一律「改讀快照／維持」，不採 NE；補 §5.4.1b、§5.4.2c |
| 8 | 基準 commit | 出口基準 commit 於收尾現取、記入基準檔（由後續獨立 commit 入庫）；程式面基準＝`<base>`（P0 不改 `tools/`） |
| 9 | 命名紀律 | `G-SIDB-n`／`MEAS-Mn`／`SKIP-M6`（§5.1.1） |
| 10 | SQL 烟測（Q-LD0-2 結案） | **必做**；用**一次性容器**（`docker run --rm`，`pgvector/pgvector:pg18`；一審 F-11：叢集全域角色不隨 `DROP DATABASE` 消失），不碰長駐 `autoclaude_pg`；GT、不進 CI |
| 11 | `monorepo-selfimproving`（Q-LD0-4 結案） | 不入路由（`SPEC_FROZEN`、摘要已不符、非 P0 引入）；主控知悉、另案 |
| 12 | probe 檔名 | `test_selfimproving_dal_pg_probe.py`、`V000__probe.sql`；P1 實作檔不得同名 |
| 13 | `tools/tests_pg/**` 與 compat-ci `paths` | **不入**（AC-LD-11-3 compat CI 不跑 PG；`root-infra-ci.yml` 無 `paths` 過濾，`compileall`／`ruff check tools/` 本就遞迴涵蓋）；PRD §9.4 `:232` 於此定案（§5.3.1 末段） |
| 14 | 其餘問題結案 | Q-LD0-6 skip 基準只記 win32、他平台標 NE：可；Q-LD0-7 ADR 狀態允許 `Accepted（階段性：…）`：允許；Q-LD0-8 PRD 對 SIDB-05／07 只給決定、本檔補選項：可（選項取自 PRD 他處明文）；Q-LD0-9 帳本盲實驗不另跑全套；Q-LD0-10 檔名 `test_selfimproving_ledgerdb_p0.py`：可 |
| 15 | 棒切分與依賴順序 | 見 §5.7.3 |
| 16 | G-P0-1 判定口徑 | 以「本鍵 commit 範圍」（`<base>..<tip>`）判定，不用工作樹快照相減：工作樹另有他鍵未追蹤 TCS，相減會被污染 |

### 7.2 PRD 勘誤表（勘誤一；可直接貼進 `docs/01_requirements/SelfImproving_Ledger_DB_PRD.md` 檔尾 `## 勘誤` 節的 `### 勘誤一` 之下）

只收 (i) P0 範圍的實作棒會撞到的、(ii) 純事實錯誤；其餘見 §7.3。「原文」逐字取自現行 PRD（座標為 PRD 行號；已以字串包含複核）；貼入後 PRD digest 改變，由主控於 Stage-2 凍結時記新 digest，並更新本檔檔頭與增量追溯表的 digest 欄（本檔其餘內容不依賴 PRD 檔尾；勘誤一貼在 `<base>` 之前，不入 §5.7.2 的零變動判定）。

| 條 | 位置 | 原文（逐字） | 訂正 | 理由 |
|---|---|---|---|---|
| 1-1 | AC-LD-02-6（`:86`） | **file 模式 `si check` 位元組同 P0（items=33）** | file 模式 `si check` 的 rc、`items=33`、尾行指紋同 P0 基準；首行 `rows=<N>` 隨帳本成長、`CONSOLE-KEY-MISSING` 警示隨環境而變，兩者不釘；比對在含歷史的 clone 並清除 `SI_*`／`AUTOSDD_*` 後進行 | 對真 repo「位元組同 P0」不可達；`git archive` 副本無 `.git`，`si check` 有 7 項依 git 歷史而 FAIL（P0 乾跑實測 rc 1） |
| 1-2 | §11 P1 列（`:264`） | （P0 基準取自 `git archive` 匯出的 P0 commit） | （夾具 repo 的差分取自 `git archive` 匯出的 P0 commit，夾具 repo 自帶 `git init`；真 repo 的 `si check` 比對取含歷史的 `git clone --no-local` 副本）；同列「file 模式 `si check` 位元組同 P0」依 1-1 | 同 1-1 |
| 1-3 | AC-LD-11-4（`:133`） | **不受**行數棘輪（只數 `tools/tests/*.py`，`test_adr_xplat001_c1c2_lock.py:554,595`）、M6、skip 政策管轄 | 句末補：但 `tools/tests_pg/*.py` **受** ruff 全規則管轄（`tools/ruff.toml`：E,F,I,UP,W,S102；`"tests/*.py"` 的 E501 豁免只涵蓋目錄名 `tests`、不涵蓋 `tests_pg`），每行顯示寬度須 ≤100（CJK 算 2），`ruff check tools/ .claude/hooks/`（root-infra-ci 第 16 道、pre-push）照常判紅 | P0 乾跑實測：152 寬行在 `tests_pg` 回 E501、在 `tests` 不回 |
| 1-4 | §8.3（`:191`） | P2、P3b 各 ≤ +515 | 此上限只在輪號前進（S-B）時適用且逐輪遞減：款(12) 到期義務使 R216 起單輪上限為 514、513、512，故 P2 須 ≤ +514、P3b 須 ≤ +513，否則各入名冊（名冊上限 6→10）；同標籤續列（S-A，預設）下 R214 淨額本已超限，每個有測試行變動的階段（含 P4 淨減）都重登 R214 名冊精確淨額，515 不是約束 | P0 棘輪預演（P0 TCS §5.5；`repin_growth_problems()`、`repin_cost_ratchet_problems()` 實跑） |
| 1-5 | §8.1（`:187`） | **M 類**——M1 對帳恆等式（彩排庫與真庫） | §8.1 機器閘 M1～M7 改稱 G-SIDB-1～G-SIDB-7（AC-LD-10-1 的「§8.1 M1～M7」同；H 類不變） | PRD 內 M 編號三處撞名：§8.1 的 M1～M7、AC-LD-13-6 與 R-10 的 M1～M5、AC-LD-11-1 的 M6 |
| 1-6 | AC-LD-13-6（`:144`） | 與 M1～M5 的兩個 measuring 窗 | M1～M5（SelfImproving 的量測窗）改稱 MEAS-M1～MEAS-M5；R-10（`:257`）同 | 同 1-5 |
| 1-7 | AC-LD-11-1（`:130`） | 故**不進 M6「全世界沒跑過」判準** | M6 改稱 SKIP-M6（同列「M6 只在 `start_dir` 為 `tools/tests` 時評」、AC-LD-11-4 的「M6」、D-18 的「避開 M6」同） | 同 1-5 |
| 1-8 | §9.4（`:234`）、§9.5（`:237`） | `docs/02_architecture/ADR-SIDB-NNN-*.md` | ADR 檔名一律三位數 `ADR-SIDB-00N-<slug>.md`（N＝1～8；沿 Root_Layout §2 的 `ADR-<MOD>-NNN-<slug>.md`）；全文的「ADR-SIDB-01」「ADR-SIDB-01～08」為簡稱，指 `ADR-SIDB-001`～`008` | §9.5 與全文用二位數、§9.4 寫三位數，自相不一 |
| 1-9 | §11 P3a 列（`:266`） | AC-LD-06、09、12、13-1～13-6 綠 | AC-LD-06、09、12、13-1、13-2、13-3、13-5（處置落地）、13-6 綠（13-4 於 P4 出口驗） | 13-4 本文為「Given P4 出口」，與 P4 列重複歸屬 |
| 1-10 | A.4 第 1 列（`:326`） | 快照不入 git（OQ-1 選 d）則 CI 內 NE、本機以 DB 驗 | OQ-1 已裁決採 (b)（快照固定單一目錄入 git）：一律「改讀快照」，不採 NE；快照缺席時 fail-loud 而非放行 | 掌舵者 2026-10-27 對 OQ-1 採建議值（PRD §13.2） |
| 1-11 | §3.3 #5（`:40`） | 能力測試明列該檔為唯一可 import `psycopg` 者 | 現況 `test_selfimproving_capability.py:195-201` 是「不得 import 第三方」判準，尚無例外清單；P1 於該判準新增分支把 `psycopg` 限於 `dal_pg_conn.py` 並加紅綠自證；AC-LD-06-5（`:109`）與 §9.4（`:229`）的「明列例外，`:195-201`」同此訂正 | P0 重核座標（P0 TCS §5.8） |
| 1-12 | AC-LD-02-5（`:85`） | 測試碼 17 處依附錄 A.4 | 測試碼 17 處／6 檔為路徑常數依附，逐檔列於 P0 TCS §5.4.1b；附錄 A.4 只列「讀真實內容」的測試 | A.4 沒逐檔列出 `LEDGER_REL`／`PROPOSALS_REL` 的 6 檔 |
| 1-13 | A.4 第 2 列（`:327`） | 凍結檔不再長新輪次，「最新輪」判準失去輸入 | 該鎖對 ID＞`_BASELINE_ID_CEILING` 的新列做家族全檔硬擋；P3b 後新 DEF 只在 DB、鎖只看得到凍結檔，新列零命中＝**靜默 fail-open**（不只是失去最新輪判準）；改讀快照時輸入缺新列或為空須 fail-loud | P0 查明判準語意（P0 TCS §5.4.1 第 2 列） |

### 7.3 後續階段修訂建議與給後續階段 TCS 的輸入（不入勘誤一；P0 現查發現，各階段 TCS 逐項承接）

**後續階段 PRD 修訂建議**：(a) P0 三項交付（ADR、Architecture 草稿、§3.3 勘誤案）沒有對應 AC，本檔以自訂 `FR-LD-00` 承載，建議補 `AC-LD-14-n`；(b) AC-LD-11-1「skip 摘要同 P0 基準」未說明跨平台基準來源（skip 摘要有 win32／darwin／linux 三張剖面表，本檔只記 win32），建議寫明「逐剖面比對；無基準的剖面 advisory」。

| 階段 | 項 | 出處 |
|---|---|---|
| P1 | `scan.py:33-48` 的 `bucket_of` 前綴表加 `tools/tests_pg/test_selfimproving_`（否則 PG 測試被歸「根層」桶）並補桶歸屬測試；PG 測試每行 ≤100 寬、`open()`／`read_text()` 帶 `encoding=`、單檔 ≤750 斷言行、每階段 ≤4 檔 | §5.3.1 B1、B2、B4、D |
| P1 | AC-LD-02-2「每支跑 CLI 的 SI 測試皆經 `SiTestCase.setUp` 的環境 patch」逐支核實（預查：`test_selfimproving_issuemap.py` 是唯一不經 `SiTestCase` 者且不跑 CLI；`test_selfimproving_events_p2.py:1119-1127` 的子行程屬 `P2TestCase(SiTestCase)`、繼承已 patch 的 `os.environ`）；`psycopg` 唯一 import 例外要寫進 `test_selfimproving_capability.py:195-201` 判準的新分支並加紅綠自證（勘誤 1-11）；`sql/` 遷移檔 sha256 對 LF 位元組；skip 比對先以 win32 | §5.4.1 第 9 列、契約節 C1.1 |
| P1／P2／P3a／P3b | 依案文「套用階段」套用 E-n 並 refreeze（E-1、E-5→P1；E-2、E-6→P2；E-3、E-4→P3a；E-7→P3b）；Architecture 草稿三塊補丁依序 P1（§9.4）、P2（§10.3）、P3（§7.2、docker README〈4.3〉） | §5.1.3、C3 |
| P3a | `def-add` 以 `issuemap.severity_of("def", raw)` 驗證嚴重度；`test_adr_xplat001_c1c2_lock.py` 的「新列硬擋」改讀快照並在輸入缺新列／為空時 fail-loud（屬 `_GOV_EXACT`，只能互動 session 改；勘誤 1-13）；`check_defect_log_crossref.py` 改讀 export 時，`test_selfimproving_measure_probe.py:450-456` 與 `test_check_defect_log_crossref.py:380,388,544` 同批改為兩路徑差分 | §5.4.1 第 2、3、5、6 列 |
| P3b／P4 | 凍結檔不得刪、`check_defect_log_crossref.current_round` 不得退役（AutoClaude 兩支測試依賴；§5.4.2b 兩檔報警） | §5.4.1 第 10 列 |

## SCG-4 通過標準

**通過條件**（全部成立才算過；審查報告逐字貼各 G 指令的 rc 與輸出尾段）：

1. **AT 37／37**：每個 DT 的判定指令 rc 0 且收集 ≥1 個測試；每個 GT 以所指 G 編號指令的輸出為證。
2. **閘門全綠**：G-P0-1～G-P0-13。
3. **突變**：R-LD0-01～R-LD0-32 每條至少一個突變轉紅（killed）；倖存者補 AT 並勘誤。**突變副本規則**：突變一律在保留歷史的 clone 上做——`git clone --no-local <repo> <短路徑>` 後 `git checkout <tip>`（短路徑；`AgentConsole/` 深層路徑超過 260 字元時以 `git sparse-checkout` 只展開所需子樹），套用突變並**提交**後才跑所列 AT 與 G 閘（GT 的座標、關鍵字與 `<base>..<tip>` 檢查讀 git 樹與歷史，未提交的改動看不見；`git archive <base>` 沒有 ADR、DT、證據檔與 Root_Layout 新格，也沒有 `.git`，不可用於突變）；DT 突變不需提交。乾跑置位實驗與帳本盲實驗另用 `git archive <base>` 展開、`git init`＋提交的**實驗副本**（§5.3.2、§5.4.3）。
4. **兩個負控成立**：AT-LD-11-4-E-3（`tools/tests` 放置會反應）與 AT-LD-13-5-E-1（帳本盲實驗非空轉）——不成立＝對應實驗無鑑別力，不得以其「無反應」結論過關。
5. **出口判準（PRD §11 P0 列）**：ADR-SIDB-01～08 成檔（D3）；§3.3 勘誤案（全備案，D5）與 Architecture 草稿備妥（D4）；Root_Layout §2 已修（D1）；A.4 普查定稿與棘輪預演表入 TCS 與證據檔（D6、D7）；掌舵者答覆 OQ-1、OQ-2、OQ-3、OQ-6（**已於 2026-10-27 全部作答**，PRD §13.2）。
6. 無 P1、P2 未結；凍結與放行依根 `CLAUDE.md`〈凍結常態規則〉與 BRIDGE §8。

**閘門指令**（`<repo>`＝monorepo 根，現查 `git rev-parse --show-toplevel`；`<base>`＝開發棒開工時的 HEAD；`<tip>`＝本鍵最後一個 commit；`<short>`＝QA 展開副本的**短**根目錄（B-09）；PowerShell 形態、rc 先存變數再讀；不得裸 `cd`；Python 閘門的 venv 啟動與指令在同一呼叫內）：

```powershell
Push-Location <repo>; & <repo>\.venv\Scripts\Activate.ps1; $o = & <指令與參數> 2>&1; $rc = $LASTEXITCODE; Pop-Location; "rc=$rc"; $o | Select-Object -Last 20
```

| G | 目錄 | 指令／程序 | 期望 |
|---|---|---|---|
| G-P0-1 | `<repo>` | (a) `git diff --name-only <base>..<tip>`；(b) 同範圍對 §5.7.2 的路徑清單 `-- <路徑…>`；(c) `<tip>` 只含本鍵路徑：提交時精確 `git add <路徑>`，禁 `git add -A`（工作樹另有他鍵未追蹤檔） | (a) 每個路徑 ⊆ §5.7.1；(b) 零輸出（AT-LD-00-D9-1、AT-LD-02-6-E-2） |
| G-P0-2 | `<repo>` | `git diff --exit-code <base> <tip> -- AgentConsole/docs/02_architecture/Architecture.md AgentConsole/docker/README.md`；再讀 G-P0-8 輸出中 `agentconsole-si-decide`／`-mirror` 的 `Architecture.md` 列 | rc 0、無輸出；兩列 MATCH（AT-LD-00-D4-2） |
| G-P0-3 | `<repo>` | `python -m unittest discover -s tools/tests -p "test_root_module_layout.py"` | rc 0（落點鎖對新登記為綠；AT-LD-11-4-3 的互補） |
| G-P0-4 | `<short>` | 乾跑置位實驗（§5.3.2）：三副本 base／probe／ctrl 兩輪、選檔規則、逐檔比對指令與 LOC、ruff、`compileall` 三項如該節 | base 與 probe 逐檔相同；ctrl 在 §5.3.2 所列鎖出現新增失敗；LOC 報表含 probe 檔且 tier＝`guardrail_cli`；ruff 對 probe 回 E501、對 base 回通過；`compileall` rc 0（AT-LD-11-4-4、-5、-E-3） |
| G-P0-5 | `<short>` | §5.4.4 三條普查指令；§5.4.3 帳本盲實驗（B 對照、K 帳本盲；28 檔；AutoClaude 兩支另跑） | 集合包含成立（(a) 命中檔 ⊆ A.4 ∪ 5.4.1b ∪ 5.4.2a／b；(b) 命中檔 ⊆ A.4 ∪ 5.4.2a／b／c）；K 相對 B 新增失敗所屬檔 ⊆ A.4 的 10 檔 ∪ 5.4.2b 的 2 檔；5.4.2a 的 13 支與 5.4.2c 的 3 檔 K 與 B 相同；至少一支 A.4 測試因移除而轉紅（AT-LD-13-5-1、-2、-3、-E-1） |
| G-P0-6 | `<short>` | 把證據檔 `SelfImproving_LedgerDb_P0_Ratchet_PreRun.md` 的 ` ```python ` 區塊存成腳本，於含 `.git` 的 `git archive <base>` 副本根執行，輸出與證據檔的兩張表逐列比對 | rc 0；逐列相同；S-A「名冊未重登」每格含 `[超出每輪上限]`、「重登後」每格為空；S-B 的「款(12) 未兌現」於 P1、P3a、P4 格含 `[到期未下修]`、兌現後為空，「無名冊項」於 P1、P2、P3a、P3b 含 `[超出每輪上限]`、加名冊項後為空（AT-LD-13-7-1、-E-1） |
| G-P0-7 | `<repo>`（Docker） | (1) 一次性容器：`docker run --rm -d --name si_p0_smoke_<隨機> -e POSTGRES_PASSWORD=<QA 現場隨機值> -p 127.0.0.1::5432 pgvector/pgvector:pg18`（同映像見 `AutoClaude/docker-compose.yml:30`；不碰長駐 `autoclaude_pg`），`pg_isready` 等就緒；(2) `psql -v ON_ERROR_STOP=1 -f <ADR-003 sql 區塊存檔>` 套 SQL 草稿；(3) 三個負控（追加專用表 UPDATE；可變表無同交易 audit 列 COMMIT；非擁有者 `ALTER TABLE … DISABLE TRIGGER`）與一個正控；(4) `docker rm -f` 並驗容器已不存在。備援（映像取不到）才用 `autoclaude_pg` 建拋棄式庫：結束先 `DROP DATABASE`，再 `DROP ROLE IF EXISTS si_owner, si_writer, si_reader`（角色是叢集全域物件，`DROP DATABASE` 不會帶走；有依賴物件時先 `DROP OWNED BY`），並驗 `SELECT count(*) FROM pg_roles WHERE rolname LIKE 'si\_%'` 回 0 | 套用 rc 0；三負控各 rc≠0 且訊息含物件名；正控成功；容器（或庫與角色）零殘留（AT-LD-00-D3-5） |
| G-P0-8 | `<repo>` | 勘誤案一致性腳本（〈附錄 A〉；唯讀；`python <short>\errata_check.py <base>`）：案文結構與 `原文` 逐字、凍結文件與 base 位元組相同、六鍵與議題中心兩鍵與 Architecture 兩鍵的聯集摘要對現檔 | 全 OK；各鍵的 PRD／Architecture 列全為 MATCH；`monorepo-selfimproving` 為已知 DIFF（AT-LD-00-D5-2、-D5-3、-D5-4）。FSM 狀態檔在 `build/`（未追蹤），在 clone 或 `git archive` 副本跑時須先複製兩個 `build/reports/fsm` 目錄；DT 不得依賴它們（B-11） |
| G-P0-9 | `<short>` | `git clone --no-local <repo> <short>` 後 `git checkout <base>`（含歷史；🔴 不可用 `git archive`：無 `.git`，`si check` 有 7 項依 git 歷史而 FAIL），可用 `git sparse-checkout set --no-cone /tools/ /docs/06_quality/ /docs/05_development/ /docs/01_requirements/SelfImproving_PRD.md /.gitattributes` 只展開所需子樹（避開 260 字元限制）；清除 `SI_*`、`AUTOSDD_*` 後 (a) `python tools/selfimproving.py check`；(b) `git grep -n -P -e 'items=33' -e 'all_33_items' -e '\b33\b.{0,30}items' -e 'items.{0,30}\b33\b' <base> -- 'tools/tests/*selfimproving*.py'`，排除 `test_selfimproving_ledgerdb_p0.py` 自身 | (a) rc 0；首行 `si-check rows=<N> items=33`；尾行含 `overall=PASS rc=0 fingerprint=<基準指紋>`；(b) 基準檔「`items=33` 釘」列所記的每個座標，其檔仍含該關鍵字（行號僅提示，B-08；逐座標核，不比總數）；基準後新增的命中須在審查報告歸類，確屬新釘者基準檔追加一列（AT-LD-02-6-2） |
| G-P0-10 | `<repo>` | `python tools/run_root_unittests.py`（收尾單人窗口；不接管線，rc 先存；摘要行貼審查報告） | rc 0；基準檔 skip 摘要列與本次 `[skip census]` 行相符、`SKIP-M6` 列與本次 id 集合行（去掉方括號標籤後的文字）相符；`skip_id_ledger.json` sha256 不變（AT-LD-11-1-1） |
| G-P0-11 | `<repo>` | 對新測試檔：(1) `ruff check --isolated --select E501 --line-length 100 --output-format concise <檔>`；(2) `ruff check --no-cache <檔>`（吃 `tools/ruff.toml`：E,F,I,UP,W,S102；只有 E501 對 `tests/*.py` 豁免）；(3) AST 走訪 import（`ast.parse`＋`Import`／`ImportFrom`）；(4) `git diff --name-only --diff-filter=A <base>..<tip> -- tools/tests` 數新增 `test_*.py`；(5) `__main__` 守衛為檔內最後一個頂層敘述 | (1)(2) rc 0（輸出僅 `All checks passed!`）；(3) import ⊆ 標準庫 ∪ {`lib.selfimproving.params`、`test_root_module_layout`、`_selfimproving_fixtures`、`_stdio_utf8`（僅 `__main__` 區塊）}；(4) 恰 1 支；(5) 成立（AT-LD-00-D9-2） |
| G-P0-12 | `<repo>` | 收尾單人窗口重釘後依序：`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines`；`python -m unittest discover -s tools/tests -p` 逐個跑 `test_adr_xplat001_c1c2_lock.py`、`test_root_module_layout.py`、`test_subprocess_encoding_hygiene.py`、`test_check_defect_log_crossref.py`、`test_archive_defect_log.py`、`test_defect_id_reference_integrity.py`、`test_platform_neutral_paths.py`、`test_doc_loc_baseline_freshness_r60.py`、`test_selfimproving_p2_meta.py`、`test_selfimproving_p3_meta.py`；`ruff check tools/ .claude/hooks/ --no-cache`；`python -m compileall -q tools`；`python -m pytest AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py -q -p no:xdist -o addopts=`；`python tools/check_pytest_baseline_sites.py`；`python tools/check_ntfs_paths.py`；`python AutoClaude/tools/check_loc_budget.py --json`；最後 `python tools/run_root_unittests.py` | 每條 rc 0；`--print-guard-lines` 尾段 `+0`、`逐檔漂移 0 支`；LOC 無新違規；全套 rc 0 且 skip 摘要同基準（AT-LD-00-D9-3） |
| G-P0-13 | `<repo>` | 內容一次性驗收（不入 CI）：`python -c "import sys; sys.path[:0]=['tools','tools/tests']; import pathlib, test_selfimproving_ledgerdb_p0 as t; print(t.p0_acceptance_problems(pathlib.Path('.')))"` | rc 0 且印 `[]`（AT-LD-00-D3-3、-D3-4、-D4-1；函式契約見 §5.1.2） |

## 附錄 A　勘誤案一致性檢查腳本（G-P0-8；唯讀）

存成 `<short>\errata_check.py`，於 repo 根、根 venv 內執行：`python <short>\errata_check.py <base> [<案文檔>]`。輸出 `OK`／`NOT-OK` 行與各鍵逐列 `MATCH`／`DIFF`；任一 `NOT-OK`、或六鍵的 PRD 列或兩鍵的議題中心 PRD 列有 `DIFF`，rc 1。AT 數與 AC 覆蓋的機械核對（原附錄 A 計數腳本）已移出本檔：QA 以 §1.1、§1.2、§3.2、R 條文表自備對照，數字見交卷報告。

```python
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT, BASE = Path.cwd(), sys.argv[1]
ERR = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "docs/06_quality/SelfImproving_LedgerDb_P0_Errata.md"
PRD, ICP = "docs/01_requirements/SelfImproving_PRD.md", "docs/01_requirements/Issue_Center_PRD.md"
ARCH, DOCKER = "AgentConsole/docs/02_architecture/Architecture.md", "AgentConsole/docker/README.md"
ML, AC = "build/reports/fsm", "AgentConsole/build/reports/fsm"
SI = [(ML, "monorepo-si-p0-ledger"), (ML, "monorepo-si-p1-propose"), (ML, "monorepo-si-p2-gate-apply"),
      (ML, "monorepo-si-p3-measure-retire"), (AC, "agentconsole-si-decide"), (AC, "agentconsole-si-mirror")]
IC = [(ML, "monorepo-issue-center"), (AC, "agentconsole-issue-center")]
ROUTE = {PRD: SI, ICP: IC, ARCH: SI[4:]}
EXTRA = [(ML, "monorepo-selfimproving")]
FIELDS = ("目標文件", "原文座標", "原文", "訂正文", "生效階段", "套用階段", "理由")
bad = 0

def say(ok, msg):
    global bad
    bad += not ok
    print(("OK     " if ok else "NOT-OK ") + msg)

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True)

def base_text(rel):
    return git("show", f"{BASE}:{rel}").stdout.decode("utf-8")

entries = {}
for m in re.finditer(r"^### (E-\d+)\n((?:- .*\n?)+)", ERR.read_text(encoding="utf-8"), flags=re.M):
    entries[m.group(1)] = dict(re.findall(r"^- ([^：\n]+)：(.*)$", m.group(2), flags=re.M))
say(sorted(entries) == [f"E-{i}" for i in range(1, 8)], f"案文含 E-1～E-7（實得 {sorted(entries)}）")
for n, f in sorted(entries.items()):
    say(all(f.get(k, "").strip() for k in FIELDS), f"{n} 七欄位標籤齊全且非空")
    say(re.match(r"P(1|2|3a|3b)", f.get("套用階段", "")) is not None, f"{n} 套用階段值域")
    src = f.get("原文", "")
    target = f.get("目標文件", "")
    rel = ICP if "Issue_Center_PRD" in target else PRD
    say(20 <= len(src) <= 200 and "|" not in src and src in base_text(rel), f"{n} 原文為 base 版 {Path(rel).name} 的逐字子字串")
    say(re.search(r"(?<![-\w])M[1-7](?!\d)", src + f.get("訂正文", "")) is None, f"{n} 不含裸 M 編號")
e4 = entries.get("E-4", {}).get("訂正文", "")
say("〈sid／line 由主控填〉" in e4 or re.search(r"sid [0-9a-f-]{36} line \d+", e4) is not None, "E-4 核准座標＝佔位或已填")

for rel in (PRD, ICP, ARCH, DOCKER):
    say(git("diff", "--quiet", BASE, "--", rel).returncode == 0, f"凍結文件與 base 位元組相同：{rel}")

def sha(p):
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()

for rel, keys in ROUTE.items():
    for d, key in keys + (EXTRA if rel == PRD else []):
        st = yaml.safe_load((ROOT / d / f"FSM-STATE-{key}.yaml").read_text(encoding="utf-8"))["fsm_state"]
        union = {}
        for s in st.get("frozen_stages") or []:
            union.update(s.get("spec_doc_digests") or {})
        dg = next((v for k, v in union.items() if k.endswith(Path(rel).name)), None)
        status = "MISSING" if dg is None else ("MATCH" if sha(ROOT / rel) == dg else "DIFF")
        known = (d, key) in EXTRA and status == "DIFF"
        if status != "MATCH" and not known:
            bad += 1
        print(f"{status:7s} {key:32s} {st['current_state']:13s} {Path(rel).name}" + ("  （已知：SPEC_FROZEN 不入路由）" if known else ""))
sys.exit(1 if bad else 0)
```

## 勘誤（本檔凍結之後的訂正；凍結前留空）

（凍結前留空；凍結後依〈凍結後修訂路由〉走 `monorepo-si-ledgerdb-p0` 的 `spec-refreeze`，並於此逐條附新 digest。）
