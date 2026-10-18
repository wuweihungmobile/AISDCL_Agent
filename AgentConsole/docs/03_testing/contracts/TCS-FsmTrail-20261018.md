# Test Contract Specification — FsmTrail（DEF-AC-023：決策軌跡 from 欄的顯示投影）
# 測試契約規格文件（增量變更；FRD-lite 併入檔頭）

**文件類型**: Test Contract Specification (TCS)
**SDD Gate**: SCG-4 PR Review Gate（RG-TEST 為補充閘）
**使用時機**: 已凍結系統的單一 Feature（增量條款）；FRD-lite 與 TCS 同檔
**存放位置**: `AgentConsole/docs/03_testing/contracts/TCS-FsmTrail-20261018.md`（相對 monorepo 根；`spec-frozen --root` 取 monorepo 根，因 Stage-1 含根層 PRD）
**spec-format-version**: 1.0
**scenario**: brownfield

---

## 文件資訊

| 欄位 | 說明 |
|------|------|
| **Feature ID** | F-001 |
| **Feature 名稱** | FsmTrail：把委派失敗那筆 decision_trace 的 from 還原為真實來源狀態（純函式 restore_trail，僅顯示投影） |
| **User Story** | US-001 |
| **建立日期** | 2026-10-18 |
| **QA 負責人** | 整合輪 116 W3 QA（獨立審查者；規格作者＝W2 SA、實作者＝hooks-ON 的 headless Sonnet，三方不同） |
| **SCG Gate** | SCG-4 □ 待審 |

---

## 增量變更專用：FRD-lite 與〈增量追溯表〉

> 適用 `workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`〈增量（delta）條款〉：變更限於已凍結系統（AgentConsole；上位文件已於 Stage-1 採納凍結，採納程序見 `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` §8.4）的單一 Feature。
> 未列入追溯表視為未滿足；引用不得指向未凍結文件（必須列在 FSM 狀態檔 `frozen_stages[*].spec_docs`）。

### FRD-lite

**現況與變更（Before／After；棕地）**

- Before：`AgentConsole/engine-bridge/app/routers/sdd.py` 的 `_state_view()` 以 `trace[-FSM_TRAIL:]` 原樣輸出 `decision_trace`（`FSM_TRAIL` 即 `sdd_state.TRAIL`，現為 5）。委派失敗進 ESCALATION 時，SDD 的 `record_escalation` 先把 `current_state` 寫成 `ESCALATION` 再轉態，於是 `decision_trace` 那一筆是 `from=ESCALATION`、`to=ESCALATION`、`trigger=autoclaude_delegated_exit`；Console 監控頁「最近決策」因此顯示「ESCALATION → ESCALATION」，真實來源 `AUTOCLAUDE_DELEGATED → ESCALATION` 那一跳讀不出來（DEF-AC-023；證據在 `docs/06_quality/AutoSDD_ZeroTrust_Audit_115.md` 第 247 行，稽核檔、非凍結上位文件，僅供追溯）。
- After：Bridge 輸出前以純函式 `restore_trail(trace, provenance)` 做**顯示投影**：對符合條件的筆把 `from` 還原為 `AUTOCLAUDE_DELEGATED` 並加 `from_inferred: true`（標明這是推斷值）。**FSM 狀態檔、SDD runtime、Backend、Frontend 都不動**；Backend 與 Frontend 是否透傳 `from_inferred` 由它們自行決定，顯示字串因 `from` 已修正而正確。

**F-001 `restore_trail`**（新模組 `AgentConsole/engine-bridge/app/fsm_trail.py`；同型先例是 T-G 的 `app/fsm_phase.py`）

```python
def restore_trail(trace, provenance) -> list[dict]: ...
```

**〈F-001 行為規則〉**（R1～R9）

- **R1 非 list 輸入**：`trace` 不是 `list`（`None`、數字、字串、dict、tuple、set 等）→ 原樣回傳該物件（同一個物件，不複製）。呼叫端 `_state_view()` 已先以 `isinstance(trace, list)` 把關，此分支只防禦直接呼叫。
- **R2 list 輸入**：回傳**新 list**（`result is not trace`，即使沒有任何元素被改寫），長度與順序不變；輸入的 list 與其中任何元素都不被改動。
- **R3 改寫條件**（逐元素，三條同時成立；一律精確字串比對、區分大小寫）：① 元素是 `dict` 且 `elem.get("from") == "ESCALATION"` 且 `elem.get("to") == "ESCALATION"`；② `elem.get("trigger") == "autoclaude_delegated_exit"`（SDD 的 `exit_autoclaude_delegated` 在委派失敗時寫下的 trigger，實查 LATEST 的 `tools/fsm_runtime/fsm_runtime.py`；缺鍵、`None`、其他值、大小寫不同皆不成立）；③ `provenance` 是 `dict` 且 `provenance.get("source") == "autoclaude_delegated_failed"`。第 ② 條是 QA 預審採納的收窄：原判準（D-116-15）只看 from、to 與 provenance，provenance 殘留時，視窗內更早的、非委派失敗的 ESCALATION 自迴圈筆會被誤改；加上 trigger 後，只有委派失敗那條路徑寫下的筆才會被還原。
- **R4 改寫結果**：符合 R3 的元素 → 放入一個**新 dict**：複製原元素全部鍵值，把 `from` 改為 `AUTOCLAUDE_DELEGATED`，再加 `from_inferred: True`（布林）；其餘鍵（`ts`、`to`、`reason`、`spec_refs`、`agents_consulted`、`trigger` 等）原值保留。
- **R5 不符者原樣**：不符合 R3 的元素（含非 dict 元素、缺 `from` 或 `to` 鍵、值不是字串、`trigger` 缺鍵或不是 `autoclaude_delegated_exit`）→ 以**同一個元素物件**放入新 list，不加任何鍵。
- **R6 不拋例外**：任何輸入都不拋例外（含 `provenance` 為 `None` 或非 dict、元素為 `None`、字串、數字、list）。
- **R7 純函式**：只用標準庫；無 I/O、無全域可變狀態；不 import `app.*` 內任何模組。
- **R8 接線**：`app/routers/sdd.py` 的 `_state_view()` 把 `"decision_trace"` 那一行改為 `restore_trail(trace[-FSM_TRAIL:], provenance) if isinstance(trace, list) else []`（`provenance` 是該函式內既有的區域變數）；以 `from ..fsm_trail import restore_trail` 匯入，放在既有 `from ..fsm_phase import phase_of` 與 `from ..models import SddCompileIn, SddFreezeIn` 之間（ruff 啟用 isort 規則 I，相對匯入依模組名排序：`fsm_phase` 在 `fsm_trail` 前、`fsm_trail` 在 `models` 前）；其餘欄位、鍵順序與註解一字不動。
- **R9 影響面**：`GET /sdd/fsm/{project}` 與 `POST /sdd/fsm/{project}:freeze` 的成功回應共用 `_state_view()`（實查 `sdd.py`：`fsm_state()` 與 `_freeze()` 兩處都以它組回應），兩者的 `decision_trace` 都經投影；`:freeze` 端點本身要走 CLI 凍結流程、整合成本高，所以由 AT-001-5-1 直接呼叫 `_state_view` 涵蓋這個共用函式；`GET /sdd/fsm`（清單）不含 `decision_trace`，不受影響；磁碟上的 FSM 狀態檔不被改動。

| US ID | User Story | AC ID | AC（Given／When／Then） |
|-------|------------|-------|-----------------------|
| US-001 | 作為 Console 監控頁的「最近決策」使用者，我要委派失敗進 ESCALATION 那一筆顯示成「AUTOCLAUDE_DELEGATED → ESCALATION」而不是「ESCALATION → ESCALATION」，以便讀得出失敗是從委派來的（DEF-AC-023） | AC-001-1 | Given 軌跡含一筆 from 與 to 皆為 ESCALATION 且 trigger 為 autoclaude_delegated_exit 的筆，且 provenance 的 source 為 autoclaude_delegated_failed When 呼叫 restore_trail Then 該筆的 from 為 AUTOCLAUDE_DELEGATED、from_inferred 為 True、其他鍵值不變；輸入未被改動；回傳是新 list |
| US-001 | 同上 | AC-001-2 | Given 軌跡中混有不符條件的筆（from 與 to 不同、from 與 to 皆為其他狀態、to 為 ESCALATION 但 from 是別的狀態、大小寫不符、from 與 to 皆為 ESCALATION 但 trigger 缺鍵或不是 autoclaude_delegated_exit） When 呼叫 restore_trail（provenance 為委派失敗） Then 只有符合條件的筆被改寫，其餘筆是原物件、不含 from_inferred，長度與順序不變 |
| US-001 | 同上 | AC-001-3 | Given provenance 不是 dict，或 source 不是 autoclaude_delegated_failed（缺鍵、其他字串、大小寫不同、非字串） When 呼叫 restore_trail Then 沒有任何筆被改寫，即使該筆 from 與 to 皆為 ESCALATION 且 trigger 為 autoclaude_delegated_exit |
| US-001 | 同上 | AC-001-4 | Given 輸入形態不良（trace 不是 list；list 內含非 dict 元素、缺 from 或 to、值不是字串） When 呼叫 restore_trail Then 不拋例外；非 list 原樣回傳同一物件；list 內不良元素原樣保留，同一 list 內符合條件的好元素仍被改寫 |
| US-001 | 同上 | AC-001-5 | Given Bridge 讀到一份委派失敗的 FSM 狀態檔 When 呼叫 GET /sdd/fsm/{project} Then decision_trace 尾 5 筆經 restore_trail 投影（失敗那筆的 from 還原），回應其餘欄位不變，磁碟上的 FSM 檔位元組不變；非委派失敗的狀態檔（provenance 缺或 source 不符，或 provenance 殘留但筆的 trigger 不符）其 decision_trace 與檔內尾 5 筆逐值相等；直接呼叫 _state_view（GET 與 :freeze 共用）結果相同 |

> 編譯相容提醒：FRD-lite 表的第一欄用 US ID，不把 AC ID 放第一欄（`sdd_compile` 會把「第一欄形如 AC-…」的表格列當成 AC→AT 映射列掃描）。

**INVEST 自檢（US-001）**：獨立（純函式加單一接線點）、可協商（改寫條件與標記鍵由本檔定義）、有價值（修正監控頁的誤導顯示，關閉 DEF-AC-023）、可估計（1 個模組、1 行接線、1 個測試檔）、小（模組約 30 行）、可測（7 個 AT：5 個純函式 Unit、2 個經端點的 Integration，皆不需外部服務）。

**非功能需求（量化）**

| NFR ID | 內容 | 驗證方式 |
|--------|------|----------|
| NFR-001-1 | 純函式：無 I/O、無全域可變狀態、只用標準庫，不 import app.* 任何模組（葉節點） | SCG-4 人工審查（程式碼與 import 檢視） |
| NFR-001-2 | 單次呼叫耗時 < 1 ms（對 5 筆 trace、其中 1 筆被改寫，量測 1000 次，P99） | SCG-4 審查時以 timeit 量測，不列 AT |
| NFR-001-3 | 回應相容：GET /sdd/fsm/{project} 與 :freeze 回應的鍵集合不變；decisionTrace 項目只可能多一個選填鍵 from_inferred（布林 true）；OpenAPI 的 SddFsmState.decisionTrace.items 為 additionalProperties: true，schema 不變，不需 OpenAPI 形狀變更；但契約與 OpenAPI 的「原樣」描述對委派失敗那一筆不再逐字為真，語意偏離見已知邊界 3 | AT-001-5-1、AT-001-5-2；既有 tests/test_sdd_fsm.py 的鍵集合斷言續綠 |
| NFR-001-4 | 零退化：engine-bridge 全套測試（cwd 為 AgentConsole/engine-bridge，python -m pytest -q）0 失敗、0 新增 skip；通過數以實跑為準，本檔不寫數字 | SCG-4 實跑 |
| NFR-001-5 | 靜態檢查：ruff check 0 錯，本專案視角與 monorepo 根視角各跑一次（AgentConsole/CLAUDE.md 閘門表） | SCG-4 實跑 |
| NFR-001-6 | 寫入面不變：不新增任何寫 FSM 檔的程式；fsm_trail.py 不含 FSM-STATE 字串；tests/test_sdd_integration_parity.py 的 F-4 AST 鎖續綠 | SCG-4 實跑與人工審查 |
| NFR-001-7 | AgentConsole 鐵律 6：新 Python 的 open、read_text、write_text 一律帶 encoding="utf-8"（本功能預期零檔案 I/O）；時間戳帶 tz；不使用單平台 API | SCG-4 審查 |
| NFR-001-8 | 範圍守衛：git diff --name-only 只准出現三個檔（新增 AgentConsole/engine-bridge/app/fsm_trail.py、改 AgentConsole/engine-bridge/app/routers/sdd.py、新增 AgentConsole/engine-bridge/tests/test_fsm_trail.py）；不改 RTM 與任何文件（RTM 回填屬 SCG-5 階段，落 docs/06_quality） | 主控以 git diff 機械核對 |

**追溯矩陣**：F-001 ← 整合輪 115 缺陷 DEF-AC-023（`docs/06_quality/AutoSDD_ZeroTrust_Audit_115.md` 第 247 行；稽核檔、非凍結上位文件，僅供追溯）；整合輪 116 裁決 D-116-15（DF-B）；US-001 → AC-001-1～AC-001-5 → AT-001-1-1～AT-001-5-2（本檔 §1）。

**〈增量追溯表〉**（SCG-0～3 每個清單項一列；清單取自 `/sdd-gate` 的 SCG-0～3 檢查表；「已凍結上位文件」均相對 `spec-frozen --root`＝monorepo 根）

| 清單項（閘門／項目） | 追溯 ID | 已凍結上位文件（路徑） | 凍結摘要 |
|---------------------|---------|----------------------|---------|
| SCG-0／PRD 版本已鎖定（Status: Approved） | ADOPTED PRD v1.1.0 §0.3（概念對映：監控遙測＝FSM decision_trace）、§0.2.2（狀態真相單一，Console 對引擎遙測唯讀投影）；PRD 檔頭的文件狀態仍標 Draft，以 Stage-1 採納凍結（摘要綁定）代替 Status: Approved | docs/01_requirements/Agent_ConsoleUI_PRD.md | sha256:1629cc2a67ba3e2b8df569c3349da89b8c8804b796744bf3b0df8fd3990d246c |
| SCG-0／FRD 覆蓋所有 PRD 功能項目（F-XXX 追溯） | F-001（本檔 FRD-lite）；ADOPTED 契約 §1.7（引擎狀態）、§3.1.3 與 §3.1.4（GET /sdd/fsm/{project}）；API-ENG-01、BR-13、BR-14 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-0／NFR 已量化定義 | NFR-001-1～8（本檔）；ADOPTED PRD NFR-OBS-01（FSM 檔、引擎、Console 渲染、PG 四源一致；投影造成的刻意差異見 §4） | docs/01_requirements/Agent_ConsoleUI_PRD.md | sha256:1629cc2a67ba3e2b8df569c3349da89b8c8804b796744bf3b0df8fd3990d246c |
| SCG-0／User Story 已完成 INVEST 檢查 | US-001（本檔 INVEST 自檢）；ADOPTED 契約 §4.3（監控頁）、§4.7（SDD 治理介面） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-0／利害關係人已確認簽核 | 掌舵者授權代決（整合輪 116 D-116-15；決策出處為規劃檔 AutoSDD_improving_116.md，僅作 ID 追溯，非上位文件） | docs/01_requirements/Agent_ConsoleUI_PRD.md | sha256:1629cc2a67ba3e2b8df569c3349da89b8c8804b796744bf3b0df8fd3990d246c |
| SCG-0／RTM 初版已建立 | 本增量自帶：本檔 §1 與 §6（AC→AT 映射）；全域 RTM 回填屬 SCG-5 階段 | （本檔；隨 Stage-2 凍結，非上位文件） | n/a（自引） |
| SCG-1／SRD 完成並通過 Review（Status: Approved） | ADOPTED Architecture §10（Bridge API 契約）、§6(d)（監控資料流） | AgentConsole/docs/02_architecture/Architecture.md | sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3 |
| SCG-1／API Spec 草稿完成（所有端點清單） | ADOPTED 契約 §3.1.3（GET /sdd/fsm/{project} 既有欄位一個都不動、只增不減）與 §3.1.4 (c)（回應新欄位只增不減）；本增量不新增端點 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-1／資料模型設計完成 | ADOPTED OpenAPI SddFsmState.decisionTrace.items（additionalProperties: true；每筆 ts、from、to、reason、spec_refs、agents_consulted、trigger） | AgentConsole/docs/02_architecture/openapi-p3-6.yaml | sha256:e51d8c298fbe46d668ee2f6b6e38f6ef832e20ce4b0e71505ed8e5e4253ca141 |
| SCG-1／NFR 設計對應完成（架構選型對應 NFR 指標） | NFR-001-3 對應 Architecture §10.1「補充約定（不改上列契約的形狀）」與契約 §3.1.3、§3.1.4 (c) 的只增不減；「原樣」語意的偏離見已知邊界 3 | AgentConsole/docs/02_architecture/Architecture.md | sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3 |
| SCG-1／整合架構說明完整（第三方服務已識別） | 無第三方服務；消費鏈＝Bridge GET /sdd/fsm/{project} → console-api GET /api/v1/engines/sdd → 前端監控頁（ADR-001 D22） | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38 |
| SCG-2／C4 Context 圖完成（系統邊界清晰） | ADOPTED Architecture §1（C4 L1）；本增量不改系統邊界 | AgentConsole/docs/02_architecture/Architecture.md | sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3 |
| SCG-2／C4 Container 圖完成（主要組件識別） | ADOPTED Architecture §2（C4 L2）；只動 engine-bridge 容器內一個模組與一行接線 | AgentConsole/docs/02_architecture/Architecture.md | sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3 |
| SCG-2／所有架構決策有對應 ADR（Status: Accepted） | ADOPTED ADR-001 D22（AISDLC_SDD 接入：唯讀接入、監控頁最近 5 筆決策）；本增量無新架構決策 | AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md | sha256:ff0bcd0038b77e80885240d287cfc68fb55c02200dc59f62f7e59c7691094e38 |
| SCG-2／Trust Boundary Map 完成（Security 情境） | 不適用（scenario 為 brownfield，非 security）；純函式、無 I/O、不跨信任邊界；最近依據 ADOPTED Architecture §8（安全） | AgentConsole/docs/02_architecture/Architecture.md | sha256:ffc13220a4d8a11008f6178087b237c5a1b3b2ddf95da63deb40e26b526c3cd3 |
| SCG-2／Before／After 架構對比（Brownfield 情境） | 本檔 FRD-lite〈現況與變更〉；Frontend 不改，設計系統決策（ADR-002）不受影響，因 from 字串已在 Bridge 還原 | AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md | sha256:d67e450b48f9ace170ec5873c81bca74d915ac1bd15ab496cbbfdea8efffbf36 |
| SCG-3／OpenAPI 3.1 規格完整（所有端點含完整 Schema） | ADOPTED OpenAPI（openapi 3.1.0、info.version 1.5.0）；本增量不改 OpenAPI 檔（schema 不變：additionalProperties: true；「原樣」描述的語意偏離見已知邊界 3） | AgentConsole/docs/02_architecture/openapi-p3-6.yaml | sha256:e51d8c298fbe46d668ee2f6b6e38f6ef832e20ce4b0e71505ed8e5e4253ca141 |
| SCG-3／Request／Response Schema 定義完整 | SddFsmState.decisionTrace.items 為 additionalProperties: true；新增選填鍵 from_inferred（布林）在其容許範圍內，schema 不變；「原樣」描述的語意偏離見已知邊界 3 | AgentConsole/docs/02_architecture/openapi-p3-6.yaml | sha256:e51d8c298fbe46d668ee2f6b6e38f6ef832e20ce4b0e71505ed8e5e4253ca141 |
| SCG-3／錯誤碼定義（400／401／403／404／500） | 不適用：restore_trail 不拋例外、不新增端點錯誤碼；端點錯誤沿用契約 §0.3 與 §3.1.4（404 fsm_not_found、422 fsm_state_unreadable） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-3／Consumer Contract 完成（整合情境） | 消費者＝console-api GET /api/v1/engines/sdd（透傳 decisionTrace）與監控頁；Backend DTO 與 Frontend 本增量不改（契約 §3.1.4 與 §4.7） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-3／API ID 與 RTM 已對應 | API-ENG-01、BR-13、BR-14（契約 §1.0 總表）；AT 到 RTM 見本檔 §1 與 §6；RTM 回填屬 SCG-5（docs/06_quality） | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |
| SCG-3／Contract 已 Review 通過 | 由未參與規格與實作的 QA 於 SCG-4 獨立審查（W3）；裁決 D-116-15 | AgentConsole/docs/02_architecture/API_Contract_P3-6.md | sha256:42db0d8ecad61b2fe50d59caaff3a12bebe3d551eb09d6c7868cd7d567bf82d2 |

> 凍結摘要＝該文件在 `frozen_stages[*].spec_doc_digests` 的值（`fsm_runtime show` 可查）。本表各值取自 Stage-1 凍結（2026-10-18T10:35:20+08:00，approver 為掌舵者代理（主控），reason 為「baseline adoption；SCG 未重跑」）後 `show` 的逐字輸出，並已用檔案現況獨立重算複驗一致；Stage-1 的六份上位文件與 HEAD（81faa59a）逐字相同（棕地基線採納）。

---

## 1. AC → AT 映射表

> **AT ID 文法**：`AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`，前兩段數字＝所屬 AC。

| AC ID | AC 描述 | AT ID | AT 描述 | 自動化 | 測試類型 | 狀態 |
|-------|---------|-------|---------|-------|---------|------|
| AC-001-1 | 委派失敗那筆的 from 還原且標記推斷 | AT-001-1-1 | 符合條件的筆改為 AUTOCLAUDE_DELEGATED 並加 from_inferred，輸入不被改動 | ✅ | Unit | □ |
| AC-001-2 | 只改符合條件的筆 | AT-001-2-1 | 混合十筆（含 trigger 缺鍵與不符）與雙命中：只有符合者被改，其餘為原物件，長度順序不變 | ✅ | Unit | □ |
| AC-001-3 | provenance 閘 | AT-001-3-1 | provenance 非 dict 或 source 不符時，即使筆的 trigger 合格也一筆都不改 | ✅ | Unit | □ |
| AC-001-4 | 不良輸入不拋例外 | AT-001-4-1 | 非 list 的 trace 原樣回傳同一物件 | ✅ | Unit | □ |
| AC-001-4 | 不良輸入不拋例外 | AT-001-4-2 | list 內不良元素原樣保留，好元素仍被改寫 | ✅ | Unit | □ |
| AC-001-5 | 端點接線且磁碟檔不變 | AT-001-5-1 | GET /sdd/fsm/{project} 對委派失敗檔還原最後一筆，磁碟檔位元組不變；直接呼叫共用的 _state_view 結果相同 | ✅ | Integration | □ |
| AC-001-5 | 端點接線且磁碟檔不變 | AT-001-5-2 | 非委派失敗、無 provenance、provenance 殘留但 trigger 不符的檔，decision_trace 與檔內尾 5 筆逐值相等 | ✅ | Integration | □ |

**覆蓋率統計**:
- 總 AC 數: 5
- 已映射 AT 數: 7
- 映射覆蓋率: 100% （目標: 100%）

---

## 2. 可自動化 AT 格式規範

> **驗收字樣**：每個 AT 的最後一個 `And` 行帶一個以雙引號包住的驗收字樣（例 `[AT_OK_001_1_1]`），本節 Then、And 行**只有驗收字樣一組引號**，其餘程式碼字面值一律用反引號（與同輪 DF-A 同型，編譯時引擎會把第一個引號字面值轉成最後回覆的 regex）。本 Feature 走 SDD session-only 路徑：實作者在 session 內自跑 `python -m pytest tests/test_fsm_trail.py -k "<AT 底線形>" -q`（cwd 為 `AgentConsole/engine-bridge`），**把輸出逐字貼進證據**（沒貼＝未驗證），並在最終回覆逐 AT 列出驗收字樣。

```gherkin
# AT-001-1-1
# 對應 AC: AC-001-1 委派失敗那筆的 from 還原為 AUTOCLAUDE_DELEGATED
# 測試類型: Unit
# 自動化工具: pytest

Feature: restore_trail 還原委派失敗那筆的 from

Scenario: 符合條件的筆被改寫成新 dict，其餘鍵不變，輸入不被改動
  Given 在 `AgentConsole/engine-bridge/` 下，新模組 `app/fsm_trail.py` 提供純函式 `restore_trail(trace, provenance) -> list[dict]`（只用標準庫；完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9，唯讀）
  And 測試放在 `tests/test_fsm_trail.py`（新檔；以 `from app.fsm_trail import restore_trail` 匯入；cwd 為 `AgentConsole/engine-bridge`），本 AT 的測試函式名稱須含 `AT_001_1_1`，例如 `test_AT_001_1_1_restores_from_of_the_delegated_failure_entry`
  When 造 `trace` 兩筆：第一筆 `{"ts": "t1", "from": "IMPLEMENTATION", "to": "AUTOCLAUDE_DELEGATED", "reason": "console-run run=r1 start", "spec_refs": [], "agents_consulted": [], "trigger": "autoclaude_delegated_enter"}`；第二筆 `{"ts": "t2", "from": "ESCALATION", "to": "ESCALATION", "reason": "console-run run=r1 ENGINE-ESCALATION step=s1: x", "spec_refs": ["docs/a.md"], "agents_consulted": ["dev"], "trigger": "autoclaude_delegated_exit"}`；`provenance` 為 `{"source": "autoclaude_delegated_failed", "reason": "r", "rule_id": "unknown", "session_id": "unknown", "at": "2026-10-18T00:00:00+00:00"}`；先對 `(trace, provenance)` 做 `copy.deepcopy` 存成快照，再呼叫 `restore_trail(trace, provenance)`
  Then 回傳值是 list 且 `result is not trace`，長度為 2
  And `result[0]` 與 `trace[0]` 是同一個物件（沒被改），且不含 `from_inferred` 鍵
  And `result[1]` 是新 dict（不是 `trace[1]` 同一個物件）：`from` 為 `AUTOCLAUDE_DELEGATED`、`from_inferred` 的值 `is True`（用 `is` 判定，排除 `1` 等其他真值）、`to` 仍為 `ESCALATION`，其餘鍵（`ts`、`reason`、`spec_refs`、`agents_consulted`、`trigger`）與 `trace[1]` 逐值相等
  And 呼叫之後 `(trace, provenance)` 與快照逐值相等（`trace[1]` 的 `from` 仍是 `ESCALATION`，沒有 `from_inferred` 鍵）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_1_1]"
```

```gherkin
# AT-001-2-1
# 對應 AC: AC-001-2 只改符合條件的筆
# 測試類型: Unit
# 自動化工具: pytest

Feature: restore_trail 只改符合條件的筆

Scenario: 混合軌跡中只有 from 與 to 皆為精確字串 ESCALATION 的筆被改寫
  Given 在 `AgentConsole/engine-bridge/` 下，`app/fsm_trail.py` 已提供純函式 `restore_trail(trace, provenance) -> list[dict]`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9，唯讀；本 AT 只要求 R3（含 `trigger` 條件）、R4、R5 成立）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_2_1`，例如 `test_AT_001_2_1_only_matching_entries_are_rewritten`
  When 造 `trace` 十筆（每筆含 `ts`、`from`、`to`、`reason` 四鍵，`reason` 各不相同；另含 `trigger` 鍵，其值除下列特別註明者外一律為 `autoclaude_delegated_exit`，第 7 筆則整個不含 `trigger` 鍵）：第 0 筆 `from` 為 `SPEC_DRAFTING`、`to` 為 `SCG_VALIDATION`；第 1 筆 `from` 與 `to` 皆為 `IMPLEMENTATION`；第 2 筆 `from` 為 `SPEC_AUDIT`、`to` 為 `ESCALATION`；第 3 筆 `from` 與 `to` 皆為 `ESCALATION`；第 4 筆 `from` 為 `ESCALATION`、`to` 為 `IMPLEMENTATION`；第 5 筆 `from` 與 `to` 皆為小寫字串 `escalation`；第 6 到第 9 筆 `from` 與 `to` 皆為 `ESCALATION`，但 `trigger` 依序是字串 `retry_exhausted`、（第 7 筆沒有 `trigger` 鍵）、大小寫不同的 `AUTOCLAUDE_DELEGATED_EXIT`、`None`；`provenance` 為 `{"source": "autoclaude_delegated_failed"}`；呼叫 `restore_trail(trace, provenance)`
  And 另造 `trace2` 三筆（`trigger` 皆為 `autoclaude_delegated_exit`）：第 0 筆與第 2 筆符合條件（`from` 與 `to` 皆為 `ESCALATION`），第 1 筆 `from` 為 `ESCALATION`、`to` 為 `IMPLEMENTATION`；以同一個 `provenance` 呼叫一次
  Then 第一次回傳的 list 長度為 10、順序不變，且只有 `result[3]` 被改寫（`from` 為 `AUTOCLAUDE_DELEGATED`、`from_inferred` 的值 `is True`）
  And `result[0]`、`result[1]`、`result[2]`，以及 `result[4]` 到 `result[9]`，都是 `trace` 對應位置的同一個物件，且都不含 `from_inferred` 鍵（`from` 與 `to` 不同、不是精確字串 `ESCALATION`，或 `trigger` 不是精確字串 `autoclaude_delegated_exit` 者一律不改）
  And 第二次回傳的 list 長度為 3，第 0 筆與第 2 筆都被改寫（`from_inferred` 的值 `is True`），第 1 筆是 `trace2[1]` 的同一個物件
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_2_1]"
```

```gherkin
# AT-001-3-1
# 對應 AC: AC-001-3 provenance 閘（非 dict 或 source 不符則一筆都不改）
# 測試類型: Unit
# 自動化工具: pytest

Feature: restore_trail 的 provenance 閘

Scenario: provenance 不是 dict 或 source 不是 autoclaude_delegated_failed 時，即使 from 與 to 皆為 ESCALATION 也不改寫
  Given 在 `AgentConsole/engine-bridge/` 下，`app/fsm_trail.py` 已提供純函式 `restore_trail(trace, provenance) -> list[dict]`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9，唯讀；本 AT 只要求 R2、R3 成立）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_3_1`，例如 `test_AT_001_3_1_provenance_gate_blocks_every_rewrite`
  When 造 `trace` 為只含一筆 `{"ts": "t1", "from": "ESCALATION", "to": "ESCALATION", "reason": "x", "trigger": "autoclaude_delegated_exit"}` 的 list（這一筆的 `from`、`to`、`trigger` 都合格，所以改寫與否只取決於 provenance）；對下列每個 `provenance` 各呼叫一次 `restore_trail(trace, provenance)`：`None`、空 dict、`{"source": "other"}`、`{"source": "AUTOCLAUDE_DELEGATED_FAILED"}`（大小寫不同）、`{"source": None}`、字串 `autoclaude_delegated_failed`、列表 `["autoclaude_delegated_failed"]`、整數 `123`
  Then 每次回傳的都是 list 且 `result is not trace`，長度為 1
  And 每次的 `result[0]` 都是 `trace[0]` 的同一個物件，`from` 仍為 `ESCALATION`，且不含 `from_inferred` 鍵
  And 全程沒有拋出任何例外，`trace` 呼叫前後逐值相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_3_1]"
```

```gherkin
# AT-001-4-1
# 對應 AC: AC-001-4 不良輸入不拋例外（非 list 的 trace）
# 測試類型: Unit
# 自動化工具: pytest

Feature: restore_trail 容錯（一）

Scenario: trace 不是 list 時原樣回傳同一個物件
  Given 在 `AgentConsole/engine-bridge/` 下，`app/fsm_trail.py` 已提供純函式 `restore_trail(trace, provenance) -> list[dict]`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9，唯讀；本 AT 只要求 R1、R6 成立）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_4_1`，例如 `test_AT_001_4_1_non_list_trace_is_returned_as_is`
  When 對下列每個 `trace` 值各呼叫一次 `restore_trail(value, provenance)`，`provenance` 為 `{"source": "autoclaude_delegated_failed"}`：`None`、整數 `42`、字串 `abc`、dict `{"from": "ESCALATION", "to": "ESCALATION"}`、tuple `({"from": "ESCALATION", "to": "ESCALATION"},)`、空 set
  Then 每次回傳的都是傳入的同一個物件（`result is value`）
  And 傳入的 dict 與 tuple 內容沒有被改動，且全程沒有拋出任何例外
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_4_1]"
```

```gherkin
# AT-001-4-2
# 對應 AC: AC-001-4 不良輸入不拋例外（list 內不良元素）
# 測試類型: Unit
# 自動化工具: pytest

Feature: restore_trail 容錯（二）

Scenario: list 內的不良元素原樣保留，同一 list 內的好元素仍被改寫
  Given 在 `AgentConsole/engine-bridge/` 下，`app/fsm_trail.py` 已提供純函式 `restore_trail(trace, provenance) -> list[dict]`（完整行為規則見規格出處檔 FRD-lite 的〈F-001 行為規則〉R1～R9，唯讀；本 AT 只要求 R3、R5、R6 成立）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_4_2`，例如 `test_AT_001_4_2_malformed_elements_pass_through`
  When 造 `trace` 十一筆：前十筆依序為 `None`、字串 `x`、整數 `7`、列表 `["ESCALATION"]`、空 dict、只有 `from` 為 `ESCALATION` 的 dict、只有 `to` 為 `ESCALATION` 的 dict、`from` 與 `to` 皆為 `None` 的 dict、`from` 與 `to` 皆為列表 `["ESCALATION"]` 的 dict、`from` 與 `to` 皆為整數 `1` 的 dict（其中第六到第十筆，即空 dict 之後的五個 dict，都另帶 `trigger` 為 `autoclaude_delegated_exit`，使缺鍵或非字串的 `from`、`to` 成為唯一擋下改寫的原因）；第十一筆是 `from` 與 `to` 皆為 `ESCALATION`、`trigger` 為 `autoclaude_delegated_exit` 的正常 dict（含 `ts` 與 `reason`）；`provenance` 為 `{"source": "autoclaude_delegated_failed"}`；呼叫 `restore_trail(trace, provenance)`
  Then 全程沒有拋出任何例外，回傳 list 長度為 11
  And 前十筆各自是 `trace` 對應位置的同一個物件（`is` 為真），沒有被改動
  And 第十一筆被改寫：`from` 為 `AUTOCLAUDE_DELEGATED`、`from_inferred` 的值 `is True`，其餘鍵與原筆逐值相等
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_4_2]"
```

```gherkin
# AT-001-5-1
# 對應 AC: AC-001-5 端點接線：委派失敗檔的最後一筆被還原，磁碟檔不變
# 測試類型: Integration
# 自動化工具: pytest + FastAPI TestClient（既有夾具）

Feature: GET /sdd/fsm/{project} 的決策軌跡投影（委派失敗）

Scenario: 委派失敗的 FSM 檔經端點讀出時，最後一筆的 from 被還原，其餘欄位與磁碟檔不變
  Given 在 `AgentConsole/engine-bridge/` 下，`app/routers/sdd.py` 的 `_state_view()` 已依規格出處檔 FRD-lite 的〈F-001 行為規則〉R8 改用 `restore_trail(trace[-FSM_TRAIL:], provenance) if isinstance(trace, list) else []` 輸出 `decision_trace`（只改這一行與匯入，其餘一字不動）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_5_1`，例如 `test_AT_001_5_1_view_restores_the_delegated_failure_and_leaves_the_file_untouched`；使用既有夾具 `sdd_live` 與 `sdd_proj`（`tests/conftest.py`）、`from tests.fake_sdd import seed_state`、`from tests.sdd_run_support import FSM_REL`
  When 以 `seed_state(sdd_proj / FSM_REL, "alpha", "ESCALATION", decision_trace=<七筆>, escalation_provenance=<provenance>)` 造狀態檔：七筆 `decision_trace` 的前六筆各為一般轉態（`ts` 為 `t1` 到 `t6`，`from` 與 `to` 不同，`reason` 各不相同，另含 `spec_refs`、`agents_consulted`、`trigger` 三鍵），第七筆 `ts` 為 `t7`、`from` 與 `to` 皆為 `ESCALATION`、`trigger` 為 `autoclaude_delegated_exit`；`provenance` 為 `{"session_id": "unknown", "at": "2026-10-18T00:00:00+00:00", "reason": "r", "rule_id": "unknown", "source": "autoclaude_delegated_failed"}`；先讀回該檔的位元組（`read_bytes()`）存成 `before`，再 `sdd_live.client.get("/sdd/fsm/alpha", params={"root": str(sdd_proj)})`，最後再讀一次位元組存成 `after`
  And 再直接呼叫 `app.routers.sdd._state_view(state, source="alpha.yaml", key="alpha", sdd_root=tmp_path, fsm_dir=tmp_path)`（`tmp_path` 是 pytest 內建夾具），其中 `state` 是 `{"project": "alpha", "current_state": "ESCALATION", "decision_trace": <同一份七筆種子>, "escalation_provenance": <同一份 provenance>}`；`GET` 與 `:freeze` 的成功回應都經由 `_state_view` 組成，直接呼叫它即涵蓋兩者（`recovery_commands` 只組字串、不做 I/O，所以傳假路徑安全）
  Then 回應狀態碼為 200，`decision_trace` 恰有 5 筆，依序對應原七筆的第 3 到第 7 筆（`ts` 為 `t3` 到 `t7`）
  And 前 4 筆與對應的種子筆逐值相等且不含 `from_inferred` 鍵；最後一筆的 `from` 為 `AUTOCLAUDE_DELEGATED`、`from_inferred` 的值 `is True`、`to` 為 `ESCALATION`、`trigger` 為 `autoclaude_delegated_exit`，其餘鍵與種子筆逐值相等
  And 回應的 `current_state` 為 `ESCALATION`，`escalation_provenance` 逐值等於種子 provenance，`fsm_project` 為 `alpha`，`phase` 的 `name` 為 `BLOCKED`
  And `after` 與 `before` 逐位元組相等（磁碟上的 FSM 檔沒有被改動）
  And 直接呼叫 `_state_view` 回傳的 `decision_trace` 與端點回應的 `decision_trace` 逐值相等（最後一筆的 `from` 為 `AUTOCLAUDE_DELEGATED`、`from_inferred` 的值 `is True`）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_5_1]"
```

```gherkin
# AT-001-5-2
# 對應 AC: AC-001-5 端點接線：非委派失敗、無 provenance、provenance 殘留但 trigger 不符的檔不受投影影響
# 測試類型: Integration
# 自動化工具: pytest + FastAPI TestClient（既有夾具）

Feature: GET /sdd/fsm/{project} 的決策軌跡投影（非委派失敗）

Scenario: 非委派失敗的檔，端點回的 decision_trace 與檔內尾 5 筆逐值相等
  Given 在 `AgentConsole/engine-bridge/` 下，`app/routers/sdd.py` 的 `_state_view()` 已依規格出處檔 FRD-lite 的〈F-001 行為規則〉R8 接上 `restore_trail`（先讀既有檔案再修改；不得破壞既有測試）
  And 測試追加到 `tests/test_fsm_trail.py`，本 AT 的測試函式名稱須含 `AT_001_5_2`，例如 `test_AT_001_5_2_non_delegated_files_are_not_projected`；使用既有夾具 `sdd_live` 與 `sdd_proj`、`from tests.fake_sdd import seed_state`、`from tests.sdd_run_support import FSM_REL`
  When 以 `seed_state` 造四個狀態檔，各自的 `decision_trace` 都至少 6 筆：`alpha` 為 `ESCALATION` 態，provenance 的 `source` 為 `other_source`，軌跡最後一筆 `from` 與 `to` 皆為 `ESCALATION`、`trigger` 為 `autoclaude_delegated_exit`；`beta` 為 `ESCALATION` 態，不給 `escalation_provenance`（用 `seed_state` 的預設，檔內沒有該鍵），軌跡最後一筆同樣 `from` 與 `to` 皆為 `ESCALATION`、`trigger` 為 `autoclaude_delegated_exit`；`delta` 為 `ESCALATION` 態，provenance 的 `source` 為 `autoclaude_delegated_failed`（人工恢復後殘留的委派失敗痕跡），但軌跡最後一筆是非委派的自迴圈：`from` 與 `to` 皆為 `ESCALATION`、`trigger` 為 `retry_exhausted`，其餘各筆是 `from` 與 `to` 不同的一般轉態（沒有任何一筆同時符合 R3 的 from、to 與 trigger 條件）；`gamma` 為 `IMPLEMENTATION` 態，軌跡全是 `from` 與 `to` 不同的一般轉態；對四者各 `sdd_live.client.get("/sdd/fsm/<名稱>", params={"root": str(sdd_proj)})` 一次
  Then 四次回應的狀態碼皆為 200
  And 四次回應的 `decision_trace` 都等於各自種子軌跡的最後 5 筆（逐值相等），且沒有任何一筆含 `from_inferred` 鍵
  And `alpha`、`beta` 與 `delta` 回應的最後一筆 `from` 仍為 `ESCALATION`（沒有誤改；`delta` 證明 provenance 殘留時，非委派的自迴圈筆因 `trigger` 不符而不被誤改）
  And 完成後在最後一則回覆逐字輸出驗收字樣 "[AT_OK_001_5_2]"
```

---

## 3. AT 完整清單

### 3.1 Unit Tests

| AT ID | 對應 AC | 描述 | 測試方法 | 預期結果 |
|-------|---------|------|---------|---------|
| AT-001-1-1 | AC-001-1 | 符合條件的筆被還原且標記推斷，輸入不被改動 | tests/test_fsm_trail.py::test_AT_001_1_1_* | from 為 AUTOCLAUDE_DELEGATED、from_inferred 為 True、新 list |
| AT-001-2-1 | AC-001-2 | 混合十筆（含 trigger 缺鍵與不符）與雙命中 | test_AT_001_2_1_* | 只有符合者被改，其餘為原物件 |
| AT-001-3-1 | AC-001-3 | provenance 閘的八種不合格值（筆的 trigger 合格） | test_AT_001_3_1_* | 一筆都不改 |
| AT-001-4-1 | AC-001-4 | 非 list 的 trace | test_AT_001_4_1_* | 原樣回傳同一物件 |
| AT-001-4-2 | AC-001-4 | list 內不良元素 | test_AT_001_4_2_* | 不良者原物件、好元素被改寫、不拋例外 |

### 3.2 Integration Tests

| AT ID | 對應 AC | 描述 | API/Service | 預期結果 |
|-------|---------|------|-------------|---------|
| AT-001-5-1 | AC-001-5 | 委派失敗檔經端點讀出，最後一筆 from 還原，磁碟檔不變；直接呼叫共用的 _state_view 結果相同 | GET /sdd/fsm/{project}?root=；app.routers.sdd._state_view | HTTP 200，最後一筆還原，檔案位元組不變，兩條路徑的 decision_trace 相等 |
| AT-001-5-2 | AC-001-5 | 非委派失敗、無 provenance、provenance 殘留但 trigger 不符的檔不受影響 | GET /sdd/fsm/{project}?root= | HTTP 200，decision_trace 與檔內尾 5 筆逐值相等 |

### 3.3 Contract Tests

（無；回應形狀的相容性由既有 `tests/test_sdd_fsm.py` 的鍵集合斷言與 NFR-001-3 承擔。）

### 3.4 E2E Tests

（無；Console 畫面不在本增量範圍。）

---

## 4. 邊界與錯誤測試規格

容錯與邊界情境已併入 AC-001-2、AC-001-3、AC-001-4（以 `AT-001-<AC>-<n>` 命名，列於 §1）；本節不另列文件內編號的 `AT-001-E-n`。

| 場景類型 | AT ID | 描述 | 輸入 | 預期結果 |
|---------|-------|------|------|---------|
| 非法輸入（provenance） | AT-001-3-1 | provenance 為 None、空 dict、其他 source、大小寫不同、非字串型別 | 見 AT 內清單 | 一筆都不改 |
| 非法輸入（trace 型別） | AT-001-4-1 | trace 為 None、數字、字串、dict、tuple、set | 見 AT 內清單 | 原樣回傳同一物件 |
| 非法輸入（元素） | AT-001-4-2 | 元素為 None、字串、數字、list、缺鍵、非字串值 | 見 AT 內清單 | 原物件保留 |
| 非法輸入（trigger） | AT-001-2-1 | from 與 to 皆為 ESCALATION 但 trigger 為 retry_exhausted、缺鍵、大小寫不同、None | 第 6 到第 9 筆 | 不改 |
| 邊界值（大小寫與精確比對） | AT-001-2-1 | from 與 to 為小寫 escalation | 第 5 筆 | 不改 |
| 邊界值（視窗） | AT-001-5-1 | 軌跡 7 筆只回尾 5 筆（FSM_TRAIL） | 七筆種子 | 5 筆，ts 為 t3 到 t7 |
| 邊界值（provenance 殘留） | AT-001-5-2 | provenance 殘留為委派失敗，但最後一筆是 trigger 為 retry_exhausted 的自迴圈 | delta 檔 | 不改 |

**刻意不做（附再開症狀）**

| 項目 | 為什麼不做 | 再開症狀 |
|------|-----------|----------|
| 改 SDD 的 record_escalation 讓軌跡記到真實 from | 屬 AISDLC_SDD 側（state_loader.py 註解稱此為既有行為），且會動 FSM runtime；本輪只做顯示投影 | 其他讀 FSM 檔的消費者（非 Console）也被這一跳誤導 |
| 改 Backend DTO 與 Frontend 以透傳或顯示 from_inferred | 顯示字串因 from 已還原而正確；是否透傳由它們自行決定 | 畫面需要區分「推斷的 from」與「檔內原值」 |
| 處理 ESCALATION_FINAL | 委派失敗只會落到 ESCALATION；ESCALATION_FINAL 的來源不在本增量 | Console 對 ESCALATION_FINAL 顯示自迴圈 |
| 拿掉 provenance 這道閘、只靠 trigger 判斷 | 沿用 D-116-15 的 provenance 閘並加上 trigger 條件（兩道都要過）；provenance 閘讓「最近一次升級不是委派失敗」時一律不改，方向是安全的（寧可漏還原、不誤改） | 視窗內較早的委派失敗筆因 provenance 已被後來的非委派升級覆寫而一直還原不了，使用者回報畫面仍顯示 ESCALATION → ESCALATION |

**已知邊界（誠實登記）**

1. **provenance 閘的漏還原（安全方向）**：`escalation_provenance` 只記最近一次升級，且在人工恢復後不會被清除（契約 §3.1.4 已載明）。R3 要求 provenance 的 `source` 為委派失敗，所以視窗（尾 5 筆）內若有較早的委派失敗筆，而最近一次升級已是別的來源（provenance 被覆寫），那一筆不會被還原，畫面仍顯示 ESCALATION → ESCALATION；這是漏還原、不是誤改，方向安全，AT-001-3-1 把它釘成現行行為。反過來，視窗內有多筆委派失敗筆（`trigger` 都是 `autoclaude_delegated_exit`）而 provenance 記的是委派失敗時，符合者全部還原，改得都對，AT-001-2-1 的 `trace2` 釘住這點。原先（D-116-15 初版判準）「provenance 殘留會把更早的非委派自迴圈筆誤改」的邊界，已由 R3 第 ② 條的 `trigger` 條件消除，回歸鎖是 AT-001-2-1 的 `trigger` 不符各例與 AT-001-5-2 的 `delta` 檔。再開症狀見上表最後一列。
2. **與 NFR-OBS-01（四源一致）的刻意差異**：投影後 API 與畫面在那一筆的 `from` 欄與 FSM 檔不相等，並以 `from_inferred: true` 標示為推斷值。既有的 E2E-15 對拍（契約 §5）用的 e2e-alpha 夾具是 IMPLEMENTATION 態，夾具說明未列 `escalation_provenance`，依 R3 不會有任何筆被改寫，所以不衝突；日後若對拍擴及委派失敗情境，須把 `from_inferred` 筆列為已知例外。
3. **與契約「原樣」描述的語意偏離（文件誠實登記）**：契約 §1.7.1 的 `SddFsmState` 表（凍結版第 1184 行「最外層鍵轉 camelCase，巢狀內容原樣＝FSM 檔寫什麼就是什麼」與第 1194 行 `decisionTrace` 列的「原樣」）、OpenAPI 的 `SddFsmState` description（第 4312 行）與 `decisionTrace` description（第 4350 行），都承諾 decision_trace 原樣帶出；本增量讓委派失敗那一筆的 `from` 不再等於檔內值（另多一個 `from_inferred`），所以對那一筆而言上述描述不再逐字為真。schema 不變（`additionalProperties: true`，兩個鍵都在容許範圍內），偏離的是「逐值相等」的語意承諾，不是形狀；契約 §3.1.3 的「既有欄位一個都不動」在欄位名稱層仍成立。文件措辭的訂正是文件變更：實作者不動（NFR-001-8），由主控在 SCG-5 或收尾補一句，並在 RTM 備註（RTM 落 docs/06_quality）。再開症狀：E2E-15，或任何「檔案 ↔ API 逐值比對」擴及委派失敗情境而轉紅。

**需同步的既有測試**：無（實查 `AgentConsole/engine-bridge/tests` 與 `AgentConsole/frontend`：沒有測試斷言端點回應的 `decision_trace[].from` 為 `ESCALATION`；`tests/test_sdd_dogfood_fixture.py` 第 346～349 行與 `tests/test_sdd_run_lifecycle.py` 第 190 行讀的是磁碟檔、不經 `_state_view()`，不受影響）。

---

## 5. 測試資料規格

| 資料項目 | 類型 | 說明 | 來源 |
|---------|------|------|------|
| 軌跡筆（一般轉態） | 靜態字面值 | 七鍵形狀 ts、from、to、reason、spec_refs、agents_consulted、trigger（與 SDD 的 append_decision_trace 一致） | 各 AT 內聯 |
| 委派失敗筆 | 靜態字面值 | from 與 to 皆為 ESCALATION、trigger 為 autoclaude_delegated_exit（所有要被改寫、或要證明被 provenance 擋下的筆都帶這個 trigger） | AT-001-1-1、AT-001-2-1、AT-001-3-1、AT-001-4-2、AT-001-5-1、AT-001-5-2 |
| 非委派的自迴圈筆 | 靜態字面值 | from 與 to 皆為 ESCALATION，但 trigger 為 retry_exhausted、缺鍵、AUTOCLAUDE_DELEGATED_EXIT（大小寫不同）或 None | AT-001-2-1、AT-001-5-2（delta 檔） |
| provenance | 靜態字面值 | source 為 autoclaude_delegated_failed 的正例，與八種不合格值 | AT-001-1-1、AT-001-3-1、AT-001-5-1 |
| 狀態檔夾具 | 動態生成 | tests.fake_sdd.seed_state 造的 FSM 狀態檔（形狀照真檔）；sdd_live 與 sdd_proj 夾具；AT-001-5-1 另以 tmp_path 夾具直接餵 _state_view | AT-001-5-1、AT-001-5-2 |

---

## 6. RTM 連結確認

| 追溯項目 | 覆蓋狀態 |
|---------|---------|
| DEF-AC-023 → F-001 | ☑ 已映射（FRD-lite 追溯矩陣） |
| F-001 → US-001 | ☑ 已映射 |
| US-001 → AC-001-1～AC-001-5 | ☑ 已映射 |
| AC-001-1～AC-001-5 → AT-001-1-1～AT-001-5-2 | ☑ 已映射（本文件 §1） |
| AT → CI Pipeline | □ 未整合（測試檔入庫後由雲端 agentconsole-ci 的 engine-bridge pytest 一併執行） |

---

## 📋 SCG-4 通過標準

| 驗證項目 | 判斷標準 | 狀態 |
|---------|---------|------|
| AC → AT 100% 映射 | 無未映射 AC | □ |
| AT 格式可自動化 | 使用 Given-When-Then 格式 | □ |
| 負向測試覆蓋 | 每個 AC 有至少一個負向 AT（AC-001-1 的負向由 AC-001-2、AC-001-3、AC-001-4 承擔） | □ |
| 邊界值測試 | 關鍵欄位有邊界值測試 | □ |
| 測試資料規格完整 | 資料來源明確定義 | □ |

**確認人**: ____________  **確認日期**: ____________  **狀態**: □ 通過 / □ 待修訂
