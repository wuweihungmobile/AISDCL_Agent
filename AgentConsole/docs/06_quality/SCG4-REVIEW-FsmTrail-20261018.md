# SCG-4 PR Review 報告 — FsmTrail（DEF-AC-023：決策軌跡 from 欄的顯示投影，DF-B）

**審查日期**: 2026-10-18　**審查者**: 整合輪 116 W3 QA（未參與規格撰寫與實作；規格作者＝W2 SA、實作者＝hooks-ON 的 headless Sonnet，三方不同）
**審查範圍**: `AgentConsole/engine-bridge/app/fsm_trail.py`（新，40 行）、`AgentConsole/engine-bridge/app/routers/sdd.py`（改，import 一行加 `_state_view` 一個運算式）、`AgentConsole/engine-bridge/tests/test_fsm_trail.py`（新，204 行）；commit `4c327ea0`
**基準規格**: `AgentConsole/docs/03_testing/contracts/TCS-FsmTrail-20261018.md`（Stage-2 凍結摘要 `sha256:409b2c5e…58e8e1`，當回合重算相符）　**FSM 鍵**: `agentconsole-fsm-trail`
**證據總檔**: `docs/06_quality/AutoSDD_ZeroTrust_Audit_116.md`（§2.2 本審查全表、§3 閘門、§1.3 hooks-ON 證據）

### A. FRD 功能規格一致性

| AC-ID | 驗收標準（摘要） | 實作座標 | 測試座標（`tests/test_fsm_trail.py`） | 結論 |
|-------|------------------|----------|--------------------------------------|------|
| AC-001-1 | 委派失敗那筆 `from`→`AUTOCLAUDE_DELEGATED`、`from_inferred is True`、其他鍵不變、輸入不被改、回傳新 list | `fsm_trail.py:28-40`（R2、R4） | AT-001-1-1 `:25-47`：`result is not trace`、`result[0] is trace[0]`、`result[1] is not trace[1]`、`is True`、五個鍵逐值、深拷貝快照比對 | Pass |
| AC-001-2 | 只改符合三條件的筆 | `:21-25、36-39`（R3、R5） | AT-001-2-1 `:50-82`：十筆混合（含小寫、`trigger` 缺鍵／錯字大小寫／`None`）只有 `[3]` 被改且其餘為同一物件；`trace2` 雙命中 | Pass |
| AC-001-3 | provenance 非 dict 或 source 不符則一筆不改 | `:32-33`（R3③） | AT-001-3-1 `:85-97`：八種不合格值，筆本身三條件合格 | Pass |
| AC-001-4 | 不良輸入不拋例外 | `:30-31`、`:21-25` 的 `isinstance`（R1、R6） | AT-001-4-1 `:100-107`（None／42／abc／dict／tuple／set 回同一物件）；AT-001-4-2 `:110-129`（十種不良元素＋一筆好元素仍被改寫） | Pass |
| AC-001-5 | `GET /sdd/fsm/{project}` 尾 5 筆經投影、磁碟檔位元組不變；非委派失敗檔逐值相等；直接呼叫 `_state_view` 結果相同 | `sdd.py:28`（import）、`:187-188`（R8 運算式） | AT-001-5-1 `:141-176`（七筆種子、`ts` 為 t3～t7、`before == after`、`_state_view` 直接呼叫逐值相等）；AT-001-5-2 `:179-204`（四個檔：other_source、無 provenance、殘留 provenance 加 retry_exhausted 自迴圈、IMPLEMENTATION 態） | Pass |

### B. Contract 一致性（API_Contract_P3-6 §3.1.3／§3.1.4、openapi-p3-6.yaml）
`GET /sdd/fsm/{project}` 鍵集合不變、`decisionTrace` 項目只可能多選填鍵 `from_inferred`（OpenAPI `additionalProperties: true`，schema 不變）；既有 `tests/test_sdd_fsm.py` 的鍵集合斷言在全套中續綠。**已知語意偏離（TCS 已誠實登記，非缺陷）**：契約與 OpenAPI 的「原樣」描述對委派失敗那一筆不再逐字為真（`from` 被還原、多一鍵）。文件措辭訂正屬文件變更，由主控在 SCG-5 或收尾補一句；RTM 備註已記（`RTM.md` §2.1）。

### C. Business Invariants
不適用。寫入面不變量：`fsm_trail.py` 零 import（只 `typing`）、不含 `FSM-STATE` 字串、無 I/O（NFR-001-1／-6 逐項人工核對）；`tests/test_sdd_integration_parity.py` 的 F-4 AST 鎖在全套中續綠。

### D. RTM 覆蓋率確認
AC 5／5、AT 7／7 皆有測試函式（`AgentConsole/docs/06_quality/RTM.md` §2.1 的 14 列）；R1～R9 皆被 AT 觸及（R7 純度與 R8 接線的 import 位置以人工讀碼＋diff 核對）。

### E. 審查證據
| 項目 | 結果（當回合親跑） |
|------|------------------|
| 整檔單跑與 engine-bridge 全套（cwd `AgentConsole/engine-bridge`，`-n 4`） | rc 0；全套 1003 通過、24 略過、137 秒。24 個略過逐筆列出理由＝7 個「此環境無法建立 symlink」＋17 個「未設定 BRIDGE_TEST_DSN」，零筆來自 `test_fsm_trail.py`（NFR-001-4 的「0 新增 skip」成立） |
| ruff（本專案視角 `ruff check .`、monorepo 根視角 `ruff check AgentConsole/engine-bridge`） | 兩次皆 All checks passed |
| 突變檢驗（記憶體內改寫，repo 零改動） | 19 個突變（核心 17＋探針 2）全數被殺；涵蓋拿掉 trigger 條件、拿掉 provenance 閘、沒改寫時回同一 list、就地改輸入、多動 `to`、接線略過 restore、`from_inferred` 用 1、不驗 dict、source 只看真值、from／to 不分大小寫、只看 from、tuple 轉 list、接線傳 None、視窗改 4、不符者被複製或加 `from_inferred: False` 等 |
| NFR-001-2（單次 < 1 ms，P99） | 1000 次呼叫：中位 0.70 微秒、P99 0.80 微秒、最大 2.10 微秒 |
| R8 接線 | `git show 4c327ea0 -- sdd.py` 恰為預期的 import 一行（位於 `fsm_phase` 與 `models` 之間）與 `_state_view` 一個運算式（折兩行）；其餘一字未動 |
| 範圍守衛（NFR-001-8） | `git show --stat 4c327ea0` 恰三檔；未動 RTM 與任何文件 |
| hooks-ON 證據 | 見 §1.3：SessionStart 成功注入 `project: agentconsole-fsm-trail`、`current_state: IMPLEMENTATION`；ledger 記入 Read 8、Write 3、Edit 2（與 hooks.log 的 router 觸發數逐項相等）；PowerShell 呼叫 2 次未入帳（G-116-17 暴露證據）；全程零 deny |

### 審查結論

| 項目 | 狀態 |
|------|------|
| FRD 功能規格 | Pass（0 項不符） |
| Contract 一致性 | Pass（附已知語意偏離，已登記） |
| Invariants 保護 | Pass |
| RTM 覆蓋率 | 100%（AC 5／5、AT 7／7） |
| 測試強度（突變） | Pass（19／19 被殺，無存活） |

**SCG-4 建議**: [通過]

### 必修項目
無（P≤2 為零）。非必修：`tests/test_fsm_trail.py` 沒有 AT 咬住 `_state_view` 的 `else []` 分支（`trace` 非 list 時回空 list）——那是既有行為、既有測試另行覆蓋，不屬本增量。
