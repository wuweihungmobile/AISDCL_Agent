# SDD_AUTOCLAUDE_BRIDGE — SDD 文件 → AutoClaude Playbook 標準作業（Phase Z / ACT-162；整合輪 115 增補 Console／Bridge 路徑）

> **版本**：v0.03（v0.02＝Phase Z：AutoClaude 執行引擎橋接，ACT-162~171；v0.03＝整合輪 115：Phase Z′ 落地更正、Console／Bridge 路徑單一 SOP、何時走 SDD 迴圈）
> **依據**：monorepo `docs/04_planning/Archive/AutoSDD_improving_01.md`（已凍結，2026-06-12）；Console／Bridge 路徑與 FSM CLI 契約＝`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`
> **配套 Agent**：`agent/specialized/sdd-playbook-compiler-zh.yaml`
> **配套規則**：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`
> **FSM 寫入指令**：[SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉

> 🔴 **訂正紀錄（整合輪 115／G-16、S-06；訂正協議：禁止靜默覆寫，被訂正的原文逐字保留於此）**
>
> | 站點 | 被訂正的原文（逐字） | 現況與依據 |
> |---|---|---|
> | 標頭「依據」 | 「`docs/04_planning/AutoSDD_improving_01.md`」 | 該檔已搬到 `docs/04_planning/Archive/`（現路徑已 `Test-Path` 確認存在） |
> | §2 exit code | 「exit 0=成功 / 2=規格未凍結 / 3=規格遭汙染(SPEC_TAINTED) / 4=缺檔或無契約」 | `sdd_compile` 另有 5＝規格格式版本不受支援（`SpecFormatVersionError`）；整合輪 115 再加 6＝規格出現卻未編成 step 的 AT（見 §2、§3） |
> | §3 evaluator 範本 | 「僅白名單模板 `python -m pytest {path} -k "{at}" -q`」 | adapter 實際範本是裸 `pytest {path} -k "{at}" -q`（R52 起；`_EVALUATOR_TEMPLATE`，adapter 的 prompt 還明寫「不是 python -m pytest」） |
> | §5 標題與內文 | 「`AUTOCLAUDE_DELEGATED` 觀察態（提案，未落地）」；「v0.02 **不新增** FSM 狀態（`_HAPPY_PATH` 零修改 → 五軌 TLC 維持有效，N/A）」 | Phase Z′ 已落地（`transition_rules.py` 的 `_HAPPY_PATH`／`OBSERVATION_STATES`、`formal/SDD_FSM.tla`、`FSMRuntime.enter_autoclaude_delegated`／`exit_autoclaude_delegated`、`releases/CHANGELOG.md` 的 Phase Z′ 條目）；原文完整引用見 §5 |
>
> 全文搜尋同一宣稱：`SDD_FSM_ENGINE.md` 的轉換表早已列出 AUTOCLAUDE_DELEGATED 兩個出口（與本檔舊 §5 互斥的是本檔，不是它）。

---

## 1. 目的與邊界

把已凍結的 SDD 規格（TEST-CONTRACT-SPEC，AC→AT 100% 映射）編譯為 AutoClaude
標準 playbook YAML，交由 AutoClaude 微核心引擎自動執行實作與雙重驗證，形成
「規格 → 執行 → 驗證 → 回饋」全自動閉環。

**邊界（不可越）**：
- 規格未達 `SPEC_FROZEN`（`fsm_state.frozen_stages` 為空且 `current_state`
  未達凍結後狀態）→ 編譯器 fail-closed 拒絕（Spec-First Gate）。
- **凍結綁內容（整合輪 115）**：`spec-frozen --digest` 對每份凍結文件記摘要
  （`frozen_stages[*].spec_doc_digests`）；adapter 在摘要存在時比對——規格檔不在任何階段的凍結清單、或內容與凍結時不同
  → fail-closed（`SpecNotFrozenError`／其子類 `SpecDigestMismatchError`）。舊狀態檔沒有摘要＝維持放行並出聲一次
  （事件 `sdd.frozen_digest_absent`）。
- **選檔依專案鍵（整合輪 115）**：FSM 狀態檔由 `fsm_project`（編譯 CLI 的 `--fsm-project`）或環境變數
  `SDD_PROJECT` 精確選定；同目錄有多個狀態檔而無法指認 → fail-closed（「狀態檔不唯一」），不再取字母序第一份。
- 編譯產物 = 待審工件：兩段之間必須人工 review（SCG-4 精神），凍結後才執行。
- 🔴 人工確認點不可由 AutoClaude 自動跳過（Rule 8 / R-9.5）。

## 2. 標準作業流程（compile-then-run 兩段式）

第一段：編譯（cwd＝monorepo 的 `AutoClaude/` 目錄）。`<monorepo 根>` 為本機 checkout 路徑。

PowerShell（Windows；不裸 `cd`，`Push-Location`／`Pop-Location` 同一次呼叫成對）：

```powershell
Push-Location "<monorepo 根>\AutoClaude" -ErrorAction Stop; python -m autoclaude.tools.sdd_compile --spec-dir "<SDD 專案 docs/ 路徑>" --out "playbooks/sdd_bridge.yaml" --project "<專案名>"; Pop-Location
```

bash／zsh（mac／Linux）：

```bash
cd "<monorepo 根>/AutoClaude" && python -m autoclaude.tools.sdd_compile \
    --spec-dir "<SDD 專案 docs/ 路徑>" \
    --out playbooks/sdd_bridge.yaml \
    --project "<專案名>"
```

選用旗標（兩種形態通用，附在上述指令之後）：`--test-path tests`（evaluator 的 pytest 目標路徑）；
`--spec-file <TCS 路徑>`（`--spec-dir` 內有多份 TCS 時必填；相對路徑以 `--spec-dir` 為基準，須是其下的 `.md` 檔）；
`--fsm-project <FSM 專案鍵>`（同目錄多個 FSM 狀態檔時必帶，或設 `SDD_PROJECT`）。

```
  exit 0=成功 / 2=規格未凍結（含凍結後內容已變更、摘要不符） / 3=規格遭汙染(SPEC_TAINTED)
       / 4=缺檔、無契約、參數不合法或規格有歧義 / 5=規格格式版本不受支援
       / 6=規格中出現卻未編成 step 的 AT（unmapped_at_ids；不寫輸出檔、無覆寫旗標）
```

[人工檢視點] review 生成的 YAML（step_id / expected_output_regex /
             evaluator_command 白名單模板 / weak_regex audit log）

第二段：執行（同樣在 `AutoClaude/` 下）：

```powershell
Push-Location "<monorepo 根>\AutoClaude" -ErrorAction Stop; python -m autoclaude "playbooks/sdd_bridge.yaml"; Pop-Location
```

```bash
cd "<monorepo 根>/AutoClaude" && python -m autoclaude playbooks/sdd_bridge.yaml
```

（要忽略舊 checkpoint 重跑，兩種形態皆在 `playbooks/sdd_bridge.yaml` 之後加 `--fresh`。）

→ SddGovernancePlugin（PRIORITY=45）自動啟用：
  SCG 閘門守門（越閘 deny）/ 契約違反記帳 / spec digest 防 drift /
  sdd_governance 掛入 checkpoint

## 3. 轉譯契約（AT↔step 100% 雙向映射，R-9.38）

| SDD 來源 | PlaybookTask 欄位 | 規則 |
|----------|------------------|------|
| AT-XXX-Y-Z | `step_id` | `sdd-{scenario}-{at_id}`（kebab-case 全 playbook 唯一；`at_id` 轉小寫） |
| Gherkin Given/When | `prompt` | 「依下列契約實作並使測試通過」模板 + 規格出處 digest |
| Gherkin Then | `expected_output_regex` | 引號字面值 / 狀態碼推導；不可推導 → `\bPASS(ED)?\b` 並標 weak_regex 入 audit log |
| AT 測試類型 | `evaluator_command` | 僅白名單模板 `pytest {path} -k "{at}" -q`（**裸 `pytest`，不是 `python -m pytest`**；R52：乾淨 PATH 的 macOS／Linux 沒有裸 `python` 別名，`python -m pytest` 經 shell 執行恆 rc=127） |
| Unit/Integration/Contract → SCG-4；E2E → SCG-5 | `max_retries` | SCG-4=5 / SCG-5=2（對齊 RETRY_LIMITS） |
| 同 AC 連續 AT | `maintain_context` | 同 AC=true / 跨 AC=false |

**保真驗收**：playbook steps 數 = 規格 AT 條數；雙向可追溯（step_id ↔ at_id）；
缺漏或多餘 → R-9.38 違反 → `SPEC_AUDIT`。

### 3.1 AT ID 文法、場景宣告與「出現卻未編成」的出聲（整合輪 115，D-115-16）

| 項 | 契約 |
|---|---|
| AT ID 文法 | `AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*`（整串全比對、區分大小寫、`AT-` 大寫）。**前兩段數字＝所屬 AC**：`AT-001-12-3-a` 屬 `AC-001-12`；第三段起的任意英數尾綴（`-1`、`-a`、`-E1`、`-E-1`）不影響歸屬。正向編譯與逆向 RTM 共用同一份 `AT_ID_PATTERN` |
| E 類（邊界／錯誤）AT | TCS 模板 §4 的 `AT-{NNN}-E-n` 第二段不是數字，**不可編譯**（只是文件內編號）。要讓邊界／錯誤 AT 由 AutoClaude 執行，命名成 `AT-{NNN}-{Y}-E-{n}`（掛在所屬 AC `AC-{NNN}-{Y}` 之下）並列入 §1 映射表 |
| 宣告位置（只掃這兩處） | ①§1 AC 映射表的列（第一欄形如 `AC-…`，取第三欄的 AT 字樣）；②標為 `gherkin` 的程式碼圍欄的第一個 `# AT-…` 標頭。§3 清單表、§4 邊界表與散文都不是宣告位置，照模板填 §3／§4 不會讓編譯失敗 |
| AC 一致性 | §1 該列的 AC id 必須等於 AT 前兩段推得的 `AC-<第一段>-<第二段>`；不一致的列視為未編成（避免正向與逆向悄悄歸到不同的 AC） |
| `unmapped_at_ids` | `出現 − 已編成`（保首見順序）。`sdd_compile`：stderr 列出 ID、**rc 6**、不寫輸出檔（fail-closed，修法只有補進 §1／改成合文法的 ID／刪掉）；adapter：不拋，只 `record_event("sdd.at_unmapped", …)`（引擎 PRE_RUN 也走它）；Bridge `/sdd/compile`：回應永遠帶 `unmapped_at_ids`，**不是錯誤、仍回 200**，Console 轉成匯入警告 `at_unmapped`，簽核前由人決定。未實例化的 TCS 模板本體會得 rc 6（§2 示例區塊的 `AT-001-1-1`／`AT-001-1-2` 無對應 §1 列），這是預期的大聲失敗——實例化時示例區塊要刪或改成真實 AC 的 AT |
| 場景宣告 | TCS 檔頭 `**scenario**: <10 場景之一>`（行首、半／全形冒號皆可）優先；值必須屬 10 個場景名，否則 rc 4／422 `spec_ambiguous`。沒宣告才沿用整份文字推斷（不改既有 step_id）並 `record_event("sdd.scenario_inferred", …)` 讓推斷可見 |
| 版本宣告 | `**spec-format-version**: 1.0` 容許裝飾與間隔變形；宣告卻解析不出版本值 → 拒絕（`SpecFormatVersionError`，rc 5／422 `spec_format_version_unsupported`） |
| 逆向 RTM 歸屬 | 還原後符合文法者以前兩段歸 AC；以 `AT-` 開頭卻不合文法者**仍計入** `summary.total_at`、依完成與否計入 `passed_at`／`failed_at_ids`，但**不進任何 AC 桶**，列入 `unmapped_at_ids`（逆向層的同名欄，與上列正向層是兩個不同的欄位）；`unmapped_at_ids` 非空時 `fully_covered` 為 False |

## 4. 治理回路（AutoClaude 側 ↔ SDD 側）

| AutoClaude 事件 | SDD 對應 |
|----------------|---------|
| `SDD-VIOLATION[at_id]`（ErrorClass.SDD_CONTRACT_VIOLATION） | 契約違反記入 `sdd_governance.contract_violations` |
| 同模式違反 ≥3 | `IBrain.decide_escalation` 諮詢（鏡像 SCG-4「3 次→SPEC_AUDIT」） |
| `sdd.spec_drift` 事件 | 規格在執行中被改 → SPEC_AUDIT 需求（advisory） |
| ESCALATION_FINAL 等價（演化亦失敗） | checkpoint 全量保存 → 人工接管（不自動恢復） |

## 5. `AUTOCLAUDE_DELEGATED` 觀察態（已落地 Phase Z′；由 Bridge 驅動）

**已落地**：`transition_rules.py` 的 `_HAPPY_PATH`（出邊 `{IMPLEMENTATION, ESCALATION}`）與 `OBSERVATION_STATES`、
`formal/SDD_FSM.tla`（`T_EnterAutoclaudeDelegated`／`T_AutoDelegToImpl`／`T_AutoDelegToEsc`，五軌 TLC 已證）、
`FSMRuntime.enter_autoclaude_delegated()`／`exit_autoclaude_delegated()`、[SDD_FSM_ENGINE.md](../sdd-fsm-engine/SDD_FSM_ENGINE.md)
轉換表的兩個出口列。入口只能從 IMPLEMENTATION（沒有走 `transition --to` 的邊；`transition` 對它回 TransitionError），
出口 `done`→IMPLEMENTATION、`failed`→ESCALATION。

**誰呼叫 enter／exit**（整合輪 115 之前零呼叫者；現由 CLI 動詞 `delegate-enter`／`delegate-exit` 驅動）：

| 路徑 | 呼叫者 | 動詞 |
|---|---|---|
| Console／Bridge 路徑 | **Bridge**（`AgentConsole/engine-bridge`；以固定環境起 FSM CLI 子行程，見 §6） | `delegate-enter`（spawn 前，`--playbook-ref run:<run_id>`）、`delegate-exit --decision done｜failed`（終態同步） |
| SDD session 人工路徑（人手動把實作交 AutoClaude 跑） | 人，在 SDD session 執行同一組 CLI（呼叫樣板見 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉） | 同上；`--playbook-ref` 不帶，或寫不以 `run:` 開頭的值（例如 `manual-note`）＝**外來委派**，Bridge 不會回收它（見 §6.7） |
| AutoClaude 引擎本身 | **不呼叫**（ADR-XPLAT-010 §2.1：兩子專案不互相 import；FSM 寫入只經 FSMRuntime CLI） | — |

🔴 **`delegate-exit --decision done` 的語意是「委派交還控制權、未升級」，不是「成功」**：run 是否成功由後續閘門判
（SCG-4 審查、RTM 面板），FSM 不替它背書。所以完成與使用者取消都是 `done`；只有引擎升級型失敗是 `failed`
（進 ESCALATION，只有人能解，見 §6.8）。`delegate-enter` 的 `autoclaude_delegated_tracking`（`entered_at`、`resume_state`、
`playbook_ref`）在 exit 後**不會被清除**——它是歷史殘留欄，不是現況旗標。

> **被訂正的原文逐字保留（訂正協議：禁止靜默覆寫；本節原標題為「`AUTOCLAUDE_DELEGATED` 觀察態（提案，未落地）」）**：
>
> v0.02 **不新增** FSM 狀態（`_HAPPY_PATH` 零修改 → 五軌 TLC 維持有效，N/A）。
> 落地前置條件（缺一不可，AutoSDD_improving_01.md §6）：
> (a) `SDD_FSM_ENGINE.md` delta（入邊自 IMPLEMENTATION / 出邊回 IMPLEMENTATION 或
> ESCALATION）+ 納入 `transition_rules.OBSERVATION_STATES`；(b) 同步
> `formal/SDD_FSM.tla`（Rule 9.18.1）；(c) 五軌 TLC 預跑全綠 + PR 附
> TLC_DISTINCT/GENERATED/DEPTH 輸出。
>
> 該三項前置條件已於 Phase Z′（ACT-172）全部完成；v0.02 的「零修改」在當時為真、現已過期。

## 6. Console／Bridge 路徑（單一 SOP；整合輪 115）

HTTP 欄位形狀與錯誤封包以 `AgentConsole/docs/02_architecture/API_Contract_P3-6.md` 為準；FSM CLI 動詞、reason 組字與
決策理由的唯一真相源是 `docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`。本節只寫 SDD 側語意
（FSM 動詞、狀態轉移、預檢、恢復指令），讓框架使用者不必翻兩份子專案的文件。

### 6.1 角色

| 角色 | 在這條路徑上做什麼 | 寫 FSM？ |
|---|---|---|
| 人（SDD session） | 在專案目錄的 SDD session 把閘門走到 HUMAN_PENDING（`SDD_STATE_DIR=<execution_path>/build/reports/fsm`；`SDD_PROJECT`＝專案名或其淨化鍵） | 是（經 CLI） |
| Console（前端＋Backend） | 專案綁定、核准凍結（人工閘）、匯入規格（路徑 A）、簽核、啟動批次、顯示 FSM 與 RTM（RTM 一律標「諮詢視圖」） | 否（人工閘只開「核准凍結」一個寫動詞，且由 Bridge 代為寫入；談判與委派同步是 Bridge 在批次內自行寫的） |
| Bridge（`AgentConsole/engine-bridge`） | 以 FSM CLI 子行程代為寫入（動詞白名單＋寫入權杖）、預檢、委派同步、回收 | 是（只經 CLI，不直接寫 yaml） |
| AutoClaude 引擎 | 執行 playbook；PRE_RUN 以 adapter 重驗凍結與摘要 | 否 |

綁定＝**Console 專案為錨**：`execution_path`（專案根；狀態目錄＝`<execution_path>/build/reports/fsm`）＋`sdd_project`
（FSM 專案鍵，預設＝專案名，由 Bridge 以 `AISDLC_SDD/scripts/component_sanitizer.py` 的規則淨化；傳原名與傳淨化鍵等價）。
一個 FSM 專案只綁一個 Console 專案。

### 6.2 逐步 SOP

| 步 | 誰 | 動作 | FSM 變化 |
|---|---|---|---|
| 1 | 人 | 建 Console 專案（`execution_path`＝專案根）；在該目錄的 SDD session 依 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md) 走閘門到 HUMAN_PENDING（TCS 已完成、SCG 已通過） | …→ HUMAN_PENDING |
| 2 | 人（Console，OPERATOR 以上） | **核准凍結**：Console `POST /api/v1/projects/{id}/sdd/freeze` → Bridge `POST /sdd/fsm/{project}:freeze`（帶 `X-Bridge-Token`）。Bridge 呼叫 `spec-frozen --digest …`；`docs[]` 必含 TCS；`--approver`＝Console 的 JWT subject | HUMAN_PENDING → SPEC_FROZEN |
| 3 | 人（Console） | **匯入**（路徑 A）：帶 `targetProjectId`＝同一專案，`POST /sdd/compile` 由 adapter 重驗凍結與摘要；回應若有 `unmapped_at_ids`，Console 顯示警告 `at_unmapped`，簽核前由人決定 | 無 |
| 4 | 人（Console） | **簽核**匯入草稿（談判閘對映見 §6.4） | 無（對映在第 5 步執行） |
| 5 | 人（Console）→ Bridge | **執行**：`POST /autoclaude/runs`（含 `sdd` 區塊）。Bridge 預檢三點（§6.3）後依序：`negotiate-enter` → `negotiate-exit --outcome agreed` → `delegate-enter` → spawn 引擎 | SPEC_FROZEN → TEST_CONTRACT_NEGOTIATED → IMPLEMENTATION → AUTOCLAUDE_DELEGATED |
| 6 | Bridge | **終態同步**（§6.5）：完成／取消 → `delegate-exit --decision done`；引擎升級型失敗 → `--decision failed` | → IMPLEMENTATION（或 ESCALATION） |
| 7 | 人 | 之後的閘門（SCG-4／5／6）照 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉走；RTM 面板是諮詢視圖，真正的閘仍是 SCG-4 的獨立審查 | IMPLEMENTATION → PR_REVIEW → … |

### 6.3 預檢三點與錯誤對映

| 點 | 時機 | 檢查 | 失敗 |
|---|---|---|---|
| ①凍結時 | `POST /sdd/fsm/{project}:freeze` | **Bridge** 依序：`docs[]` 皆存在、在根之下；至少一個 TCS 命名檔（`TEST-CONTRACT-SPEC-*`／`TCS-*`）；FSM 現況須是 HUMAN_PENDING；請求若帶 `expected_digests`（核准人當時看到的摘要）逐一與現檔比對。**Console Backend** 在送出前另擋：專案已綁定 `sdd_spec_file` 時它必須在 `docs` 內（綁定只存在 Console 的資料庫，Bridge 看不到；ADR-XPLAT-016 §6.3 ① 原把它列在 Bridge 欄，實作歸屬以 API 契約 v1.5 為準） | 422 `sanitization_failed`（`violations[].rule` 例：`missing_tcs`、`not_found`、`outside_root`）／409 `fsm_state_conflict`（FSM 不在 HUMAN_PENDING；帶 `expected_state`）／409 `spec_digest_changed`（`detail.pair=expected_vs_file`）：核准人看的版本不是現在要凍結的版本；Backend 擋下者為 400（`errors[0].field=docs`） |
| ②匯入時 | `POST /sdd/compile` | adapter 內建（凍結＋摘要）；回應帶 `fsm_project`、`frozen_digest`（`verified`／`absent`） | 422 `spec_not_frozen`（未凍結、狀態檔缺、規格檔不在凍結清單）／409 `spec_digest_changed`（有摘要但現檔不吻合）；AT 未編成不是錯誤（200＋`unmapped_at_ids`） |
| ③執行前 | `POST /autoclaude/runs`（含 `sdd`）、`:resume`、`/restore` | 重跑 adapter（凍結＝現檔）；playbook 各任務的 `spec_digest` 必須恰為現檔摘要 | 409 `spec_digest_changed`（`detail.pair=frozen_vs_file`／`import_vs_file`）；缺摘要 422 `sdd_block_invalid`；`frozen_digest_status="absent"` 放行並在 201 的 `warnings` 帶 `sdd_frozen_digest_absent` |

「內容與凍結時不同」在三個預檢點一律是 **409** `spec_digest_changed`，不是 422。

### 6.4 談判閘對映（R-9.20.2）

R-9.20.2 要求 SPEC_FROZEN 後先過 TEST_CONTRACT_NEGOTIATED 才進 IMPLEMENTATION（`enforcement_mechanism: manual`）。Console 路徑採
「Console 簽核匯入草稿＝談判 `agreed`」，附四個條件：

| # | 條件 | 做法 |
|---|---|---|
| C-1 | 權威與時機 | 只在 Bridge 收到**帶有效權杖**且含 `sdd` 區塊的 `POST /autoclaude/runs` 時執行（Backend 在簽核通過後才呼叫）；簽署人＝`sdd.approver`（Backend 永遠送具名人；Bridge 端省略時記 `console`，不假裝有人簽） |
| C-2 | 內容綁定 | `negotiate-exit` 的 `--reason` 固定格式：`console-signoff approver=<approver>; oracle=<TCS 相對路徑>@<sha256:…>; basis=import-draft-signoff; r9.20.3=not-satisfied`；`--contract-ref`＝TCS 相對路徑 |
| C-3 | 補償性控制 | 真正的閘仍是 SCG-4 的獨立審查（QA 鏡核 AI 寫的測試是否忠於 Gherkin）；RTM 面板一律標「諮詢視圖」 |
| C-4 | 兩步連發與自癒 | `negotiate-enter` 與 `negotiate-exit` 在同一個 Bridge 請求內背靠背；中間失敗留在 TEST_CONTRACT_NEGOTIATED，下次預檢以 `negotiate-exit agreed` ＋ `delegate-enter` 自癒，不需人工 |

**誠實條款**：R-9.20.3（oracle 對 Generator 不可見、Generator 與 Evaluator 獨立 context）在 AutoClaude 路徑**結構上不成立**
（adapter 把評估指令與驗收 regex 逐字寫進 prompt，且寫測試的就是同一個 AI）；憑證本身記 `r9.20.3=not-satisfied`，
本流程**不宣稱**它已滿足。Console 沒有「退回修改」，Bridge 也不呼叫 `negotiate-exit --outcome underspecified`。

### 6.5 委派同步：Bridge 觀察到的終態 → FSM 動作

| Bridge 觀察到 | FSM 動作（reason 組字） |
|---|---|
| COMPLETED（引擎 rc=0） | `delegate-exit --decision done`（`console-run run=<id> COMPLETED`） |
| CANCELLED（使用者取消） | `delegate-exit --decision done`（`console-run run=<id> CANCELLED`） |
| FAILED·引擎升級（引擎印出 `=== STATE: ESCALATION`） | `delegate-exit --decision failed`（`console-run run=<id> ENGINE-ESCALATION step=<step_id>: <detail ≤200 字>`）→ ESCALATION |
| FAILED·額度或 token 停機、引擎異常或被訊號終止、Bridge 關閉、孤兒 | **不動**（基礎設施故障不得映成阻塞態；留給 §6.7 的回收點） |
| spawn 失敗（`delegate-enter` 已做、引擎從未啟動） | 補償 `delegate-exit --decision done`（`console-run run=<id> SPAWN-FAILED delegation not started`） |
| PAUSED | **不動**（委派仍開著，可 `:resume`） |

建立順序：唯讀預檢 → advisory lock → **FSM 寫入** → 建工作區 → spawn（任何一步失敗都做補償）；終態事件先發布、之後才呼叫
`delegate-exit`。因此「終態事件」到「FSM 回到 IMPLEMENTATION」之間有約 0.1 秒（暖機）視窗：驗證時要**輪詢到 FSM 離開
AUTOCLAUDE_DELEGATED（上限 30 秒）再比對，不得單次讀取**。`delegate-exit` 回 rc 3（FSM 已不在 AUTOCLAUDE_DELEGATED，例如人工已處理）視為「已就位」，不當失敗。

### 6.6 預檢處置（建立批次時 FSM 的現況）

| FSM 現況 | 預檢處置 |
|---|---|
| IMPLEMENTATION | `delegate-enter`（常態） |
| AUTOCLAUDE_DELEGATED | 回收點（§6.7）；仍活著或外來委派 → 409 `fsm_state_conflict` |
| TEST_CONTRACT_NEGOTIATED | `negotiate-exit agreed` → `delegate-enter`（上次 enter 後 exit 前中斷的自癒） |
| SPEC_FROZEN | `negotiate-enter` → `negotiate-exit agreed` → `delegate-enter`（首次批次） |
| 其他（含 HUMAN_PENDING、ESCALATION） | 409 `fsm_state_conflict`（`detail.current_state` 帶回）；ESCALATION 的出路見 §6.8 |
| 狀態檔不存在 | 404 `fsm_not_found`（Bridge 不替專案建立狀態檔） |

### 6.7 回收點（新批次遇到陳舊的 AUTOCLAUDE_DELEGATED）

🔴 判斷只在 `current_state=AUTOCLAUDE_DELEGATED` 時才讀 `autoclaude_delegated_tracking.playbook_ref`；exit 後該欄不清除，
在 IMPLEMENTATION 上它是歷史殘留欄，**不得拿來判斷任何事**。判定依序：

| # | 條件 | 處置 |
|---|---|---|
| 1 | `playbook_ref` 缺，或不以 `run:` 開頭（外來委派：人在 SDD session 進入的） | 409 `fsm_state_conflict`（`reason:"foreign_delegation"`）；Bridge **不碰**——解卡由人在 SDD session `delegate-exit` |
| 2 | 解出 `run_id` 後，Bridge 的 run 登錄查無此 run | 視為「不存在」→ 回收 |
| 3 | 該 run 存在，但其狀態目錄或 FSM 專案與本次不同 | 視為外來，同第 1 項 409 |
| 4 | 該 run 為活躍（INITIALIZING／RUNNING／PAUSING／PAUSED／CANCELLING） | 409 `fsm_state_conflict`（`detail` 帶 `run_id`、`run_status`） |
| 5 | 該 run 為終態（COMPLETED／FAILED／CANCELLED） | 回收 |

**回收**＝在鎖內依序 `delegate-exit --decision done`（`console-run run=<舊 id> RECLAIMED old_status=<舊終態或 missing> by=<新 id>`）
→ `delegate-enter`（`--playbook-ref run:<新 id>`），FSM 軌跡因此留下完整的「舊委派被回收」一筆。兩步之間 `delegate-enter` 失敗
→ FSM 停在 IMPLEMENTATION（無委派），本次建立回 409／5xx 並不 spawn，下次建立從 IMPLEMENTATION 常態進入，不需人工。

### 6.8 `failed` 之後：人工恢復（只能在 SDD session）

引擎升級型失敗後 FSM＝ESCALATION（阻塞態：hooks 擋下一切工具呼叫），**只有人能解**（Rule 9.5、絕對禁令 #6），而且恢復**留在
SDD session**：Bridge 與 Console **不提供恢復動詞**（`resume-from-escalation` 不在 Bridge 的動詞白名單內；Bridge 的回收點也不能碰
ESCALATION，`delegate-exit` 在 ESCALATION 回 rc 3）。

- 「現在有沒有一個未解的委派失敗」的判斷式只能是：`current_state` 屬 ESCALATION／ESCALATION_FINAL，**且**
  `escalation_history[-1].resolved_at` 為空。`escalation_provenance`（辨識來源：`source="autoclaude_delegated_failed"`）與
  `autoclaude_delegated_tracking`（哪個 run：`playbook_ref=run:<run_id>`）在恢復後**都不會被清除**，只看它們在不在，會在
  IMPLEMENTATION 上顯示過期的失敗。
- 恢復指令模板（人工執行；PowerShell 不裸 `cd`，`Push-Location`／`Pop-Location` 同一句內成對；bash 的 `VAR=值 指令` 前綴只作用於該指令）：

```powershell
Push-Location "<SDD 版本目錄>" -ErrorAction Stop; $env:SDD_STATE_DIR = "<專案根>\build\reports\fsm"; & "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "<鍵>" --to IMPLEMENTATION --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR; Pop-Location
```

```bash
cd "<SDD 版本目錄>" && SDD_STATE_DIR="<專案根>/build/reports/fsm" "<python>" -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project "<鍵>" --to IMPLEMENTATION --reason "<人工原因>"
```

- 前置條件：FSM 在 ESCALATION 或 ESCALATION_FINAL（否則回 `{"noop":true,…}`）；`--to` 必須屬 SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW
  （委派失敗該回 IMPLEMENTATION，與 `autoclaude_delegated_tracking.resume_state` 一致）；`--reason` 非空——缺或不合法＝argparse 用法錯誤
  （rc 2），狀態與檔案不動。`ESCALATION_FINAL` 走同一路徑，目標可能不同：以 `GET /sdd/fsm/{project}` 回應的 `phase` 與
  `escalation_provenance` 為準，不得猜。
- 外部專案模式（`SDD_STATE_DIR` 有設）下該 CLI 不寫規則命中遙測，所以人工恢復不會弄髒框架樹。恢復後 FSM＝IMPLEMENTATION，
  歷史回填 `resolved_at`，**下一個 Console 批次可直接啟動**。

### 6.9 寫入面權杖與動詞白名單

- HTTP 寫入只有兩個入口：`POST /sdd/fsm/{project}:freeze` 與含 `sdd` 區塊的 `POST /autoclaude/runs`，都須帶 `X-Bridge-Token`
  （值＝環境變數 `BRIDGE_SDD_WRITE_TOKEN`，Backend 與 Bridge 同名；≥32 字元，repo 內不放真值）。Bridge 未設＝這兩種請求回 503
  `sdd_write_disabled`（fail-closed）；缺或錯＝403 `sdd_write_forbidden`。前端、引擎子行程、FSM CLI 子行程都不持有權杖。
- Bridge 對 FSM CLI 的動詞白名單：`spec-frozen`（僅經 `:freeze`）、`negotiate-enter`、`negotiate-exit --outcome agreed`、
  `delegate-enter`、`delegate-exit --decision done｜failed`；其餘動詞（`transition`、`gate`、`resume-from-escalation` 等）一律不呼叫。
- Bridge 以固定環境起 CLI 子行程（argv、cwd＝SDD 版本目錄、環境移除 `BRIDGE_*`／`SDD_*`／`PYTHONPATH` 後只設必要變數、
  `SDD_STATE_DIR=<專案根>/build/reports/fsm`、規則命中遙測旗標顯式 0、逾時 20 秒；細節與理由見 ADR-XPLAT-016 §3.5）。
  Bridge 原始碼不得直接寫 `FSM-STATE-*.yaml`（Rule 9 絕對禁令 #1）。
- **誠實劃界**：權杖只封住 Bridge 的 HTTP 寫入面。引擎子行程內的 AI 步驟仍可呼叫框架的 FSM CLI；縱深在於不注入
  `SDD_STATE_DIR` 給引擎、批次期間 FSM 在 IMPLEMENTATION／AUTOCLAUDE_DELEGATED（`spec-frozen` 轉態不合法）、
  以及凍結綁內容（竄改規格可偵測）。**不防禦主動對抗的 AI。**

### 6.10 已知邊界（未修）

狀態檔 load-modify-save 沒有跨行程鎖（SDD session 與 Bridge 同時寫＝競態；Bridge 只在 spawn 與終態各呼叫一次，預期近零）；
R-9.20.3 獨立性不滿足（§6.4）；外部專案模式下由人觸發的 SCAFFOLD_GC／LEARNING_COMMIT 等仍寫框架的 `build/reports/*`；
Console 沒有「退回修改」與「解除綁定」。完整清單與再開症狀見 ADR-XPLAT-016 §14.1。

## 7. 何時走 SDD 迴圈（判準；G-11）

**兩個條件都成立才走**（缺一就改走一般開發流程，仍受倉內 CI 閘門約束，不要為了套流程而硬寫佔位 AT）：

1. **有 Python 可測的 AT**：AC 能寫成以 `pytest -k "<at>"` 自動判定的 AT（Given-When-Then；evaluator 白名單只收裸 `pytest`）。
2. **規格可凍結**：FRD-lite／TCS 能在實作**之前**通過 SCG-0～3，並經人類確認、以 `spec-frozen --digest` 凍結。

補充：

- **不強制全面套用**：SDD 迴圈是選用的橋接（Console 路徑或 SDD session）。本 monorepo 自身的開發預設不受 SDD 治理（根層 SDD hook router
  在 `SDD_ACTIVE_VERSION` 未設時休眠）；一般 session 不要為了走這條迴圈而啟用 Rule 9 hooks——FSM 進入阻塞態（ESCALATION 等）時會
  擋下一切工具呼叫，把工具鎖死。
- **小功能走增量條款**：變更限於已凍結系統的單一 Feature 時，見 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈增量（delta）條款〉
  ——FRD-lite 併入 TCS 檔頭，加上 TCS，不必重寫全套 PRD／SRD／C4／OpenAPI。
- 整合輪 115 的 dogfood 是本迴圈第一個真實使用者；新發現的缺口請走缺陷帳本，不要在本檔補丁式追加。
