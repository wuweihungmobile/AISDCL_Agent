# 根層目錄地圖與模組落點規範（Root Layout and Module Placement）

**狀態**：SSOT（根 `CLAUDE.md`〈根層模組落點〉節只導航、不複寫本檔）。**立案**：掌舵者 2026-10-19 指令「請規劃日後有新模組產生時, 可以有系統, 有組織的規劃整體專案系統目錄, 不要到處散落, 請寫在CLAUDE.md及專案規格相關文件中落實」（sid f3ead132-29b1-418c-97d9-35868ab11c70；首例＝SelfImproving 自 `tools/lib/si_*.py` 搬成 `tools/lib/selfimproving/` 套件）。
**WHY**：SelfImproving P0 的每一個檔案都放在「合慣例」的位置（入口在 `tools/`、函式庫以 `si_` 前綴扁平放 `tools/lib/`、測試在 `tools/tests/`、文件依編號制分四個目錄），整體卻看不出「這是一個模組」；慣例只存在主控腦中、不在文件裡，下一個模組只會再散落一次。本檔把落點寫成規則，新模組開 PRD 時就得照表填。

---

## 1. 全 repo 目錄地圖（誰住哪裡；量測值不寫死，目錄職責才是契約）

| 目錄 | 職責 | 權威指引 |
|------|------|---------|
| `AutoClaude/`、`AISDLC_SDD/`、`AgentConsole/` | 三個子專案（各自 `CLAUDE.md`、`docs/01～08`、測試、CI 閘門） | 各子專案 `CLAUDE.md` |
| `docs/01_requirements` … `docs/06_quality`（根層） | 根整合層文件，依編號制：01 需求（PRD）、02 架構（ADR／RFC／本檔）、03 測試契約（TCS）、04 規劃（迭代計畫、交棒書、範本）、05 開發（SOP、附註檔）、06 品質（帳本、協定目錄、審查報告、RTM、證據檔） | 根 `CLAUDE.md`〈兩專案共通的工程紀律〉第 3 條 |
| `tools/` | 根層可執行工具：`check_*.py`（閘門）、`run_root_unittests.py`、`dev_start.*`、`session_resume_planner.py`、各模組的指令入口薄殼 `<module>.py` | 本檔 §2 |
| `tools/lib/` | 根層可 import 函式庫（`from lib import …`／`from lib.<module> import …`；`tools/` 在 `sys.path` 上、`lib/` 無 `__init__.py`）：單檔共用工具（`platform_utils.py`、`cpu_budget.py`…）＋**模組套件 `<module>/`** | 本檔 §2 |
| `tools/probe/` | 量測與探針（事後量測、不接任何閘門 rc）；模組專屬探針以 `<module>_*.py` 命名 | 各探針檔頭自述 |
| `tools/tests/` | 根層 unittest（`run_root_unittests.py` discover；護欄層行數棘輪 `test_adr_xplat001_c1c2_lock.py` 管轄） | `guard-ratchet-repin-ritual`（記憶）／該鎖檔檔頭 |
| `tools/git-hooks/`、`tools/act/` | git hook dispatcher、本機 act 載具 | `AutoClaude/tools/install_git_hooks.ps1`／`.sh`（安裝器住 AutoClaude，裝的是根層 dispatcher） |
| `.claude/`（hooks、settings、skills） | 守衛面；auto mode 受保護路徑，任何改動走〈權限姿態〉 | 根 `CLAUDE.md`〈機械守衛總表〉 |
| `.github/workflows/` | 全部 CI（含子專案）；根層消費檔必列入 compat-ci `paths` | `AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py` |
| `build/`、`logs/`、`checkpoints/`、`.act-runs/` | 執行期產物（FSM 狀態、日誌、快照）；不入庫或 ignore | `.gitignore` |

---

## 2. 根層模組落點表（新模組一律照填；每格的 `<module>`＝snake_case 模組鍵，`<Module>`＝PascalCase 文件名）

| 內容 | 落點 | 規則 |
|------|------|------|
| 函式庫（判準、解析、I/O） | `tools/lib/<module>/`（套件：`__init__.py` 寫一句用途；依職責分檔，例 `ledger.py`、`rows.py`、`check.py`） | 🔴 **兩支以上函式庫檔、或 PRD 已排定後續階段會長**的模組，第一天就成套件；單檔共用工具才准扁平放 `tools/lib/<name>.py`。套件內用相對 import；跨模組只准 import `tools/lib/` 的共用單檔，不得互相 import 對方套件（走資料檔／帳本） |
| 指令入口 | `tools/<module>.py`（薄殼：argparse、stdio UTF-8、輸出格式；**不含判準**） | 指令字面 `python tools/<module>.py <verb>` 是對外契約，寫進 PRD／TCS／SOP 後不得因搬遷改變 |
| 量測探針 | `tools/probe/<module>_*.py` | 不接閘門 rc；檔頭自述 |
| 測試 | `tools/tests/test_<module>_*.py` | 進根層全套；新增即撞護欄層棘輪（見記憶 `guard-ratchet-repin-ritual`） |
| 執行期協定資料（機器讀） | `docs/06_quality/<Module>_Protocol/`（`params.json`、指標副本 `metrics.md`…） | 先例：`FiveQuestion_Audit_Protocol/`、`SelfImproving_Protocol/` |
| 帳本（人寫、機器驗） | `docs/06_quality/<Module>_<Kind>_Ledger.md`；超長原文附註檔 `docs/05_development/<Module>_<Kind>_Ledger_notes.md` | 列 ≤700 bytes、只追加（各帳本自己的 TCS 定） |
| 事件帳本（機器寫、JSONL） | `docs/06_quality/<Module>_Event_Ledger.jsonl`（單一檔；寫入鎖與配號由該模組 TCS 定） | 先例：SelfImproving P1 的 ATT／PROP／DEC／APP／MEA／RUN 事件 |
| 提案／工件內容檔 | `docs/06_quality/<Module>_Proposals/<ID>/`（每提案一目錄，版本檔 `rN.*`） | 先例：SelfImproving `PROP-SI-NNN/rN.{md,patch}` |
| 需求／設計 | `docs/01_requirements/<Module>_PRD.md`（§9 元件表**必附本表的填寫版**＝「模組落點表」）；架構決策短編於 PRD §9 的 ADR 節，獨立 ADR 檔放 `docs/02_architecture/ADR-<MOD>-NNN-<slug>.md` | 動工前先查本檔；落點與本表不同＝先改本檔（含 WHY）再落檔 |
| 測試契約 | `docs/03_testing/contracts/TCS-<Module>-<Phase>-<YYYYMMDD>.md` | §5.6 檔案集合必與落點表一致 |
| 運作 SOP | `docs/05_development/<Module>_Operations_SOP.md`（研究方法類 SOP 同目錄 `<Module>_*_SOP.md`） | — |
| 審查／RTM | `docs/06_quality/SCG<n>-REVIEW-<Module>-<Phase>-<YYYYMMDD>.md`（PRD 層級的 SCG-0 無 `<Phase>`）、`docs/06_quality/RTM-<Module>-<Phase>-<YYYYMMDD>.md`、預審 `TCS-PREREVIEW-<Module>-<Phase>-<YYYYMMDD>.md` | 整合輪 116 D-116-09：SCG 產物一律 06_quality |
| CI 接線 | compat-ci 兩支 workflow 的 push／pull_request `paths` 各加 `tools/lib/<module>/**` 與 `tools/<module>.py` | 漏列即 `test_ci_paths_cover_root_consumers.py` 紅 |
| 不可進化面 | 迴圈／守衛類模組的自身檔案列入 `docs/06_quality/SelfImproving_Protocol/params.json` 的 `non_evolvable_globs`（PRD NFR-SI-02-1 實體 glob 同步） | 由 `python tools/selfimproving.py check` 的 `params.globs` 對表 |

**子專案內的模組不往根層放**：AutoClaude 照 `AutoClaude/CLAUDE.md`〈新增 Plugin 的 SOP〉（`autoclaude/plugins/<feature>_plugin.py`＋`tests/plugins/`）；AISDLC_SDD 照 `AISDLC_SDD/CLAUDE.md` Rule 2 的 LATEST 版本目錄表；AgentConsole 照 `AgentConsole/docs/02_architecture/Architecture.md`。根層只放跨專案治理工具（守衛、帳本、閘門、量測、自我進化）。

---

## 3. 根層既有模組登記表（搬遷只在「大幅觸及」時做；本表登記現況，不要求一次搬完存量）

| 模組 | 程式碼 | 入口／探針 | 測試 | 資料／文件 | 形態 |
|------|--------|-----------|------|-----------|------|
| SelfImproving（自我進化迴圈，P0＝`check`；P1＝運轉／研究／歸因／提案／卡面／體檢／匯出） | `tools/lib/selfimproving/`（P0：`ledger`、`rows`、`git`、`refs`、`history`、`params`、`check`；P1：`events`、`fold`、`evwrite`、`defs`、`sources`、`paths`、`props`、`propfiles`、`card`、`status`、`scan`、`export`、`evcheck`、`fetch`、`research`、`writeverbs`） | `tools/selfimproving.py`（13 個動詞）；P3 探針（PRD C11）預定落點 tools/probe/selfimproving_measure.py，尚未建檔、依 PRD §9.1〈C19 判準〉刻意不加反引號（原誤寫「P1 探針」，2026-10-19 依 PRD §9.7 #53 與 QA 複審 F-01 訂正） | `tools/tests/test_selfimproving_check.py`（P0）；`tools/tests/test_selfimproving_capability.py`、`tools/tests/test_selfimproving_events.py`、`tools/tests/test_selfimproving_props.py`、`tools/tests/test_selfimproving_research_scan.py`、`tools/tests/test_selfimproving_export_status.py`＋夾具 `tools/tests/_selfimproving_fixtures.py`（P1）；落點鎖 `tools/tests/test_root_module_layout.py`（FR-SI-34） | `docs/06_quality/SelfImproving_Protocol/`（`params.json`、`metrics.md`、`research_sources.json`）、`SelfImproving_Observation_Ledger.md`、事件帳本 `docs/06_quality/SelfImproving_Event_Ledger.jsonl` 與提案目錄 `docs/06_quality/SelfImproving_Proposals/`（皆於 2026-10-20 首次真實運轉 RUN-SI-001 建立、commit 8a0860d8；建立後依 PRD §9.1〈C19 判準〉加回反引號納入落點鎖，OBS-SI-220）、PRD／TCS／SOP 依編號制 | ✅ 套件（2026-10-19 自 `si_*.py` 搬入；P1 於 2026-10-20 擴充） |
| 五問協定（守衛面症狀閘） | — | `tools/probe/fivequestion_ledger.py`（函式庫形態的探針，不是 CLI） | 消費者 `tools/tests/test_claim_provenance_r86.py`（無專屬測試檔；現查 `git grep fivequestion_ledger -- tools/tests`） | `docs/06_quality/FiveQuestion_Audit_Protocol/`（`params.json`、`severity.md`、`README.md`） | 單檔探針＋協定目錄 |
| 額度／context 守衛與哨兵 | `tools/lib/quota_*.py`、`session_brief.py`、`harness_feed.py`、`sentinel_lifecycle*.py`、`endurance_env.py`、`pace_contract.py`、`resume_*.py`、`relay_machine.py`、`schedule_backend*.py` | `tools/session_resume_planner.py`；hooks `.claude/hooks/context_budget_guard.py` | `tools/tests/test_context_budget_guard.py`、`test_quota_*.py`… | `~/autosdd_quota.json`、`~/.autosdd/traces`（repo 外） | 存量扁平（前綴 `quota_`）；守衛面准入規則管，觸及時再議套件化 |
| 缺陷帳本家族 | `tools/lib/defect_ledger_index.py`、`ledger_*.py` | `tools/check_defect_log_crossref.py`、`archive_defect_log.py`、`check_handoff_carriers.py` | `tools/tests/test_defect_id_reference_integrity.py`、`test_check_defect_log_crossref.py`… | `docs/06_quality/AutoSDD_Defect_Log*.md`、`AutoSDD_External_Blocked_Log.md`、`AutoSDD_Structural_Debt_Log.md` | 存量扁平 |
| 護欄層棘輪與分桶 | `tools/lib/guard_bucket_policy.py`、`guard_line_taxonomy.py`、`oversize_repin.py` | `tools/probe/guard_layer_bucket_census.py` | `tools/tests/test_adr_xplat001_c1c2_lock.py` | 兩站點 guard-total（`docs/06_quality/CrossPlatform_R145_Scan_Findings.md`、`docs/04_planning/AutoSDD_improving_112.md`） | 存量扁平 |
| dev_start／bootstrap／本機閘門 | `tools/lib/bootstrap_lock.py`、`clean_venv_carrier.py`、`dev_platform_provenance.py`、`hook_carrier_symlink.py`… | `tools/dev_start.*`、`bootstrap.*`、`integration_gate.*`、`run_root_unittests.py` | `tools/tests/test_dev_start.py`… | `ONBOARDING.md` | 存量扁平 |
| 守衛 hooks | `.claude/hooks/*.py`（`_hook_launcher` 載具） | — | `tools/tests/test_check_hooks_liveness.py`、`test_block_destructive_git_r83.py`… | `.claude/settings.json` | 守衛面（受保護路徑） |

---

## 4. 新模組檢查表（PRD §9 與 SCG-0 一併檢）

1. PRD §9 元件表每一列的路徑都能對上 §2 的某一格；對不上＝先改本檔。
2. 程式碼成套件（§2 第一列的門檻）；入口薄殼不含判準。
3. compat-ci `paths` 兩支、`non_evolvable_globs`（若適用）、`tools/tests` 棘輪重釘、CI paths 覆蓋鎖同一個 commit 內收齊。
4. 搬遷既有模組：同步改 PRD／TCS 路徑並依 FSM 重凍或 SPEC_AUDIT 記錄；帳本以追加列記錄搬遷，舊列座標依「該列 commit 當時的路徑」解讀，不原地改。
5. 本檔 §3 登記表加一列。

## 5. 誠實劃界

- 本檔的機械鎖＝`tools/tests/test_root_module_layout.py`（SelfImproving P1 落地，FR-SI-34；§3 登記表 ↔ 磁碟存在性、`tools/lib/` 出現 ≥3 支同前綴未成套件的檔即紅、PRD 須引本檔）。鎖只守「登記的存在、未成套件的散落」兩件事；落點是否符合仍由 SCG-0／SCG-4 審查與本檢查表把關。
- 存量扁平模組不回溯搬遷：搬遷會撞護欄層棘輪與 CI paths，收益不足以付代價；只在該模組被大幅觸及（新階段、重寫）時依 §2 成套件。
