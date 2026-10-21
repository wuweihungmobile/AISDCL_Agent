# SDD_AUTOCLAUDE_BRIDGE — SDD 文件 → AutoClaude Playbook 標準作業（Phase Z / ACT-162；整合輪 115 增補 Console／Bridge 路徑；整合輪 116 增補子專案 SDD session SOP）

> **版本**：v0.04（v0.02＝Phase Z：AutoClaude 執行引擎橋接，ACT-162~171；v0.03＝整合輪 115：Phase Z′ 落地更正、Console／Bridge 路徑單一 SOP、何時走 SDD 迴圈；v0.04＝整合輪 116：§7 改三徑、新增 §8 子專案 SDD session〔根 session、外部專案模式〕單一 SOP）
> **依據**：monorepo `docs/04_planning/Archive/AutoSDD_improving_01.md`（已凍結，2026-06-12）；Console／Bridge 路徑與 FSM CLI 契約＝`docs/04_planning/ADR/ADR-XPLAT-016-sdd-integration-loop-minimal-intrusion.md`；子專案 SDD session 的裁決與探針事實＝`docs/04_planning/AutoSDD_improving_116.md`（§1.1 探針 P1～P10、§6 裁決 D-116-01～18）
> **配套 Agent**：`agent/specialized/sdd-playbook-compiler-zh.yaml`
> **配套規則**：`governance/rules/R-9.38-playbook-translation-fidelity.yaml`
> **FSM 寫入指令**：[SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉

> 🔴 **訂正紀錄（整合輪 115／G-16、S-06；整合輪 116／G-116-04、G-116-11；訂正協議：禁止靜默覆寫，被訂正的原文逐字保留於此）**
>
> | 站點 | 被訂正的原文（逐字） | 現況與依據 |
> |---|---|---|
> | 標頭「依據」 | 「`docs/04_planning/AutoSDD_improving_01.md`」 | 該檔已搬到 `docs/04_planning/Archive/`（現路徑已 `Test-Path` 確認存在） |
> | §2 exit code | 「exit 0=成功 / 2=規格未凍結 / 3=規格遭汙染(SPEC_TAINTED) / 4=缺檔或無契約」 | `sdd_compile` 另有 5＝規格格式版本不受支援（`SpecFormatVersionError`）；整合輪 115 再加 6＝規格出現卻未編成 step 的 AT（見 §2、§3） |
> | §3 evaluator 範本 | 「僅白名單模板 `python -m pytest {path} -k "{at}" -q`」 | adapter 實際範本是裸 `pytest {path} -k "{at}" -q`（R52 起；`_EVALUATOR_TEMPLATE`，adapter 的 prompt 還明寫「不是 python -m pytest」） |
> | §5 標題與內文 | 「`AUTOCLAUDE_DELEGATED` 觀察態（提案，未落地）」；「v0.02 **不新增** FSM 狀態（`_HAPPY_PATH` 零修改 → 五軌 TLC 維持有效，N/A）」 | Phase Z′ 已落地（`transition_rules.py` 的 `_HAPPY_PATH`／`OBSERVATION_STATES`、`formal/SDD_FSM.tla`、`FSMRuntime.enter_autoclaude_delegated`／`exit_autoclaude_delegated`、`releases/CHANGELOG.md` 的 Phase Z′ 條目）；原文完整引用見 §5 |
> | §7 判準（整合輪 116） | 「**兩個條件都成立才走**（缺一就改走一般開發流程，仍受倉內 CI 閘門約束，不要為了套流程而硬寫佔位 AT）：1. **有 Python 可測的 AT**：AC 能寫成以 `pytest -k "<at>"` 自動判定的 AT（Given-When-Then；evaluator 白名單只收裸 `pytest`）。2. **規格可凍結**：FRD-lite／TCS 能在實作**之前**通過 SCG-0～3，並經人類確認、以 `spec-frozen --digest` 凍結。」 | 改為三徑（§7）。原判準把 Java／TypeScript 子專案連規格、閘門、RTM 一併排除；事實上它們的規格仍可凍結、SCG 閘門仍可走，不能的只有「AT 交給 evaluator 自動判定」，所以只該把徑①（委派迴圈）限定在 pytest 可評的 AT，另開徑②（SDD session-only） |
> | §7 補充（hooks；整合輪 116） | 「本 monorepo 自身的開發預設不受 SDD 治理（根層 SDD hook router 在 `SDD_ACTIVE_VERSION` 未設時休眠）；一般 session 不要為了走這條迴圈而啟用 Rule 9 hooks——FSM 進入阻塞態（ESCALATION 等）時會擋下一切工具呼叫，把工具鎖死。」 | 「預設 hooks-OFF」仍成立；「不要啟用」的反向語氣過時。走徑①②就是要開 hooks-ON 視窗，§8 給出單一 SOP（三件組、一視窗一功能、阻塞態三層處置），不是叫人不要開 |
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

## 7. 何時走 SDD 迴圈（判準；G-11；整合輪 116 改為三徑）

三徑共同的入場券是「**規格能在實作之前凍結**」：FRD-lite／TCS 能在實作**之前**通過 SCG-0～3，並經人類確認、以
`spec-frozen --digest` 凍結。這條不成立就走徑③。成立之後，再看 **AT 能不能被 evaluator 自動判定**，決定走徑①還是徑②：

| 徑 | 判準 | 做法 | 目前適用 |
|---|---|---|---|
| ① 委派迴圈 | 規格可凍結，**且**每個 AC 能寫成以 `pytest -k "<at>"` 自動判定的 AT（Given-When-Then；evaluator 白名單只收裸 `pytest`，見 §3） | 走 §6（Console／Bridge）或 §5 的人工委派：AutoClaude 依編譯出的 playbook 實作並雙重驗證；SDD 側的閘門在 §8 的 hooks-ON 視窗走 | Python 標的：AutoClaude、AgentConsole 的 `engine-bridge`、AISDLC_SDD 自身 |
| ② SDD session-only | 規格可凍結；AT **不是** pytest 可評（Java、TypeScript） | 全程走 §8：hooks-ON 的 SDD session 內依凍結規格實作；AT 由 session 內自跑 `gradlew test --tests …`／`vitest run -t …`／pytest，**輸出逐字貼進證據檔與 RTM 欄**（沒貼＝未驗證） | AgentConsole 的 `backend`（Java）、`frontend`（TypeScript） |
| ③ 一般流程 | 規格無法在實作前凍結，或功能小到不值得走閘門 | 一般開發流程，仍受倉內 CI 閘門約束；不要為了套流程而硬寫佔位 AT | 其餘 |

補充：

- **不強制全面套用**：SDD 迴圈是選用的橋接（Console 路徑或 SDD session）。**預設 hooks-OFF**——根層 SDD hook router 在
  `SDD_ACTIVE_VERSION` 未設時休眠，一般 session 零污染；要走徑①②時，依 §8 開 hooks-ON 視窗。hooks-ON 視窗是把 SDD 守門裝上去的
  專用視窗（一次綁一個功能、收工即關），不是把整個 monorepo 的開發預設改成受治理；阻塞態（ESCALATION 等）會擋下被 matcher 命中的
  工具呼叫，§8.8 給了三層處置，風險是被管理的，不是迴避的理由。
- **不擴 evaluator 白名單**：evaluator 命令必須是單一模板內插（Gap-046 資安過濾器），Java／TS 的 AT 不會被「放寬白名單」救進徑①；
  以 pytest 殼代跑 Java／TS 也不做。再開症狀：掌舵者要求 Java／TS 功能走 Console 委派。
- **小功能走增量條款**：變更限於已凍結系統的單一 Feature 時，見 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈增量（delta）條款〉
  ——FRD-lite 併入 TCS 檔頭，加上 TCS，不必重寫全套 PRD／SRD／C4／OpenAPI。
- 整合輪 115 的 dogfood 是本迴圈第一個真實使用者；新發現的缺口請走缺陷帳本，不要在本檔補丁式追加。

## 8. 子專案 SDD session（根 session、外部專案模式；單一 SOP；整合輪 116）

本節是「在 monorepo 根開一個 hooks-ON 的 SDD session，把 AutoClaude、AgentConsole、monorepo 根層或 AISDLC_SDD 自身任一個當成 SDD
外部專案來開發」的**唯一** SOP。§6 是 Console／Bridge 的 HTTP 路徑，本節是人在終端的路徑，兩者在**狀態目錄**相會（§8.11）。機制本身
（外部專案模式＝ADR-XPLAT-016 §3 的 `SDD_STATE_DIR`／`SDD_PROJECT`）早已就位，缺的是 SOP 與幾條守門，整合輪 116 補上。事實依據是
2026-10-18 的探針實測（編號 P1～P10、P3x 見 `docs/04_planning/AutoSDD_improving_116.md` §1.1）。

### 8.0 適用與不做

| 項 | 規定 |
|---|---|
| 何時走本節 | 依 §7：徑①（委派迴圈）與徑②（SDD session-only）走本節；徑③（一般流程）不開 hooks-ON 視窗 |
| FSM 的單位 | **一個功能週期一個 FSM 專案鍵**（D-116-03）。原因：`transition_rules.py` 的 `RELEASE` 是終態（出邊集合為空），IMPLEMENTATION／PR_REVIEW／RTM_VERIFY 也沒有回 SPEC_DRAFTING 的邊——一個鍵只走得完一個功能，下一個功能用新鍵 |
| 鍵的格式 | `<sub>-<slug>`：`sub` ∈ `autoclaude`／`agentconsole`／`monorepo`／`sdd`；`slug` 小寫 kebab、≤30 字。**鍵一律小寫**：Windows 檔名不分大小寫、POSIX 分，混用大小寫會在兩個平台各得一份 `FSM-STATE-*.yaml`（G-116-19） |
| 狀態目錄 | 每個子專案一個目錄（§8.1），目錄內多個鍵的狀態檔共處；同目錄多檔而無法指認鍵＝adapter／Bridge fail-closed（§1） |
| RELEASE 語意 | 週期終點是 RELEASE_READY；功能合併進 main 且雲端 CI 綠之後，由收尾者記一次 `RELEASE`（終態，不重開；§8.7） |
| Console | 一個功能一個 Console 專案（`execution_path`＝子專案根；§8.11） |
| 本節不做 | 不改 hook 判準（規格檔 deny 仍看路徑子字串，§8.3）、不擴 evaluator 白名單（§7）、不新增 CLI 動詞、不碰 `_HAPPY_PATH`／`formal/` |

### 8.1 三件組標準值與啟動區塊

三件組＝`SDD_ACTIVE_VERSION`（hooks 版本）＋`SDD_STATE_DIR`（狀態目錄，**絕對路徑**）＋`SDD_PROJECT`（FSM 專案鍵）；**缺一不可**（§8.3）。
標準值（路徑相對 monorepo 根；LATEST 現查 `python AISDLC_SDD/scripts/sdd_version.py`，`SDD_ACTIVE_VERSION`＝其輸出去掉 `AISDLC_SDD_v`
前綴，例 `0.30`）：

| `sub` | `SDD_STATE_DIR` | 鍵 | 專案文件根（`docs/`） | Console `execution_path` | `spec-frozen --root` |
|---|---|---|---|---|---|
| `autoclaude` | `AutoClaude\build\reports\fsm` | `autoclaude-<slug>` | `AutoClaude/docs/` | `<根>\AutoClaude` | `<根>\AutoClaude`（凍結文件都在其下；省略 `--root` 也會推導到這裡） |
| `agentconsole` | `AgentConsole\build\reports\fsm` | `agentconsole-<slug>` | `AgentConsole/docs/`（PRD 在根層 `docs/01_requirements/`） | `<根>\AgentConsole` | 凍結文件含根層 PRD 時取 monorepo 根（`--doc` 寫相對根的路徑，如 `AgentConsole/docs/…`、`docs/01_requirements/…`）；只含子專案內文件時取 `<根>\AgentConsole` |
| `monorepo` | `build\reports\fsm` | `monorepo-<slug>` | 根 `docs/` | `<根>` | monorepo 根 |
| `sdd` | `AISDLC_SDD\AISDLC_SDD_v<LATEST>\build\reports\sdd-dogfood` | `sdd-<slug>` | 版本目錄 `docs/` | 不走 Console：Bridge 固定讀 `<execution_path>\build\reports\fsm`，`sdd-dogfood` 不在慣例內 | 版本目錄（凍結文件含 `AISDLC_SDD/CLAUDE.md` 時取 `AISDLC_SDD/`） |

`--root` 規則：取「含全部凍結文件的最小目錄」（絕對路徑、須為存在的目錄）。省略時：狀態目錄以 `build/reports/fsm` 結尾 ⇒ 取其上三層（子專案根），
否則退回框架版本目錄；自訂目錄落在慣例之外又不給 `--root`＝rc 4 `doc_not_found`，大聲失敗而不是靜默算錯檔（P7）。摘要的鍵是相對 `--root` 的
POSIX 路徑；adapter 與 Bridge 以「鍵為路徑尾段」比對、不依賴 `--root` 的絕對路徑，所以以根層為基準的鍵也對得上子專案內的規格檔。

四個狀態目錄都已被 `.gitignore` 忽略（根 `.gitignore` 的 `/build/reports/fsm/`、`AutoClaude/.gitignore`、`AgentConsole/.gitignore`、
`AISDLC_SDD/.gitignore` 的各版 `build/reports/`；`git check-ignore` 實測）——狀態不入庫，所以每個功能收尾要把證據引進證據檔（§8.12）。

啟動區塊（**hooks-ON 視窗專用**，收工關視窗即清環境；一律從 monorepo 根啟動，§8.3）。PowerShell：

```powershell
# 在 monorepo 根的 PowerShell 視窗啟動（子目錄啟動則根 router 不載入）；hooks-ON 視窗專用，收工關視窗即清環境
$root = (Get-Location).Path
$ver  = ((python AISDLC_SDD/scripts/sdd_version.py) -replace '^AISDLC_SDD_v', '').Trim()
$sub  = 'autoclaude'   # autoclaude｜agentconsole｜monorepo｜sdd
$slug = 'webhook'      # 小寫 kebab、≤30 字；一個功能週期一個鍵
$rel  = @{ autoclaude = 'AutoClaude\build\reports\fsm'; agentconsole = 'AgentConsole\build\reports\fsm'; monorepo = 'build\reports\fsm'; sdd = "AISDLC_SDD\AISDLC_SDD_v$ver\build\reports\sdd-dogfood" }
$env:SDD_ACTIVE_VERSION = $ver
$env:SDD_PROJECT        = "$sub-$slug"
$env:SDD_STATE_DIR      = Join-Path $root $rel[$sub]
$env:SDD_ENABLE_RULE_FIRE_TELEMETRY = '0'; $env:SDD_ENABLE_RULE_CATCH_TELEMETRY = '0'
# 日常視窗可加：$env:SDD_HOOKS_DRY_RUN = '1'（deny 降為警告）；證明守門的場次不要設
claude
```

bash／zsh（mac／Linux）：

```bash
# 在 monorepo 根的 bash／zsh 視窗啟動；hooks-ON 視窗專用
root="$(git rev-parse --show-toplevel)"; ver="$(python AISDLC_SDD/scripts/sdd_version.py | sed 's/^AISDLC_SDD_v//')"
sub=autoclaude; slug=webhook   # sub：autoclaude｜agentconsole｜monorepo｜sdd
case "$sub" in autoclaude) rel=AutoClaude/build/reports/fsm;; agentconsole) rel=AgentConsole/build/reports/fsm;; monorepo) rel=build/reports/fsm;; sdd) rel="AISDLC_SDD/AISDLC_SDD_v$ver/build/reports/sdd-dogfood";; esac
export SDD_ACTIVE_VERSION="$ver" SDD_PROJECT="$sub-$slug" SDD_STATE_DIR="$root/$rel" SDD_ENABLE_RULE_FIRE_TELEMETRY=0 SDD_ENABLE_RULE_CATCH_TELEMETRY=0
claude
```

貼到最後一行 `claude` 之前停手：先做 §8.2 的 (a)(c)，通過後才執行 `claude`。環境變數在 `claude` 啟動那一刻就定案（hooks 子行程繼承的是這一份），
之後在視窗內改環境影響不到已在跑的 session；要換功能＝關視窗、改 `$sub`／`$slug` 重新貼（§8.3 一視窗一功能）。

### 8.2 開場三步

**(a) 驗三件組同址**——在已設三件組的同一個視窗、`claude` 還沒啟動時。`<版本目錄>`＝`$root\AISDLC_SDD\AISDLC_SDD_v$ver`。

PowerShell（不裸 `cd`；`Push-Location`／`Pop-Location` 成對；先接到變數再讀 rc）：

```powershell
$vd = Join-Path $root "AISDLC_SDD\AISDLC_SDD_v$ver"; $py = Join-Path $root '.venv\Scripts\python.exe'
Push-Location $vd -ErrorAction Stop
# 新功能（這個鍵第一次出現）才跑下一行：整個週期唯一允許「缺檔自動建立 INIT 狀態檔」的一次；續做既有功能跳過
$null = & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project $env:SDD_PROJECT
# 之後（以及續做既有功能時）一律帶 --must-exist
$out = & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project $env:SDD_PROJECT --must-exist
$rc = $LASTEXITCODE
Pop-Location
"rc=$rc"   # 0＝三件組同址；5＝state_not_found＝鍵或目錄錯：改三件組，不要拿掉 --must-exist 硬過
"current_state=" + (($out -join "`n" | ConvertFrom-Json).fsm_state.current_state)   # 新功能＝INIT
Test-Path (Join-Path $env:SDD_STATE_DIR "FSM-STATE-$($env:SDD_PROJECT).yaml")   # 必須 True
```

bash／zsh：

```bash
vd="$root/AISDLC_SDD/AISDLC_SDD_v$ver"; py="$root/.venv/bin/python"
( cd "$vd" && "$py" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project "$SDD_PROJECT" >/dev/null )   # 新功能第一次才跑；續做跳過
( cd "$vd" && "$py" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime show --project "$SDD_PROJECT" --must-exist >/dev/null ); echo "rc=$?"   # 0＝同址；5＝鍵或目錄錯
test -f "$SDD_STATE_DIR/FSM-STATE-$SDD_PROJECT.yaml" && echo "狀態檔在三件組指定的目錄"
```

**(b) 第二終端備妥恢復指令**——另開一個終端（同一 monorepo 根、**不設**三件組、已啟用 `.venv`），先把恢復指令填好存著。ESCALATION 時 hooks 印出的恢復行
（`recovery_hint.py`；外部專案模式下自帶 `SDD_STATE_DIR`／`SDD_PROJECT`／`--project`／`--must-exist`／`-W ignore::RuntimeWarning`，G-116-01）與下列樣板等價；
自己填時 `--to` 只能是 SPEC_DRAFTING／IMPLEMENTATION／PR_REVIEW 之一，選「要回到的工作階段」（委派失敗＝IMPLEMENTATION，與 §6.8 一致）。

```powershell
Push-Location "<根>\AISDLC_SDD\AISDLC_SDD_v<LATEST>" -ErrorAction Stop; $env:SDD_STATE_DIR = '<狀態目錄>'; $env:SDD_PROJECT = '<鍵>'; & "<根>\.venv\Scripts\python.exe" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project '<鍵>' --to IMPLEMENTATION --must-exist --reason "<人工原因>"; Remove-Item Env:SDD_STATE_DIR, Env:SDD_PROJECT; Pop-Location
```

```bash
cd "<根>/AISDLC_SDD/AISDLC_SDD_v<LATEST>" ; SDD_STATE_DIR='<狀態目錄>' SDD_PROJECT='<鍵>' "<根>/.venv/bin/python" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime resume-from-escalation --project '<鍵>' --to IMPLEMENTATION --must-exist --reason "<人工原因>"
```

**(c) 活性正負兩面驗收**（配方出自根 `CLAUDE.md`〈hook 載具〉；同樣在已設三件組的視窗）。「不閃窗了」「沒報錯」都不算驗收通過：載具解析不到時 Claude Code
fail-open（只記 ERROR、工具照跑），表徵與「修好了」完全相同，所以正負兩面都要看。

```powershell
$log = Join-Path $env:TEMP 'sdd_hooks_probe.log'
claude -p --model haiku --debug hooks --debug-file $log "ok"
Select-String -Path $log -Pattern 'Hook SessionStart.*success'        # 正面①：hooks 活著（要有 success）
Select-String -Path $log -Pattern "project: $($env:SDD_PROJECT)"      # 正面②：注入的是你的鍵與狀態
Select-String -Path $log -Pattern 'project: AISDLC_SDD'               # 負面①：不得有輸出（有＝鍵退回目錄名，缺 SDD_PROJECT）
Test-Path (Join-Path $vd ('build\reports\fsm\FSM-STATE-{0}.yaml' -f $env:SDD_PROJECT))   # 負面②：必須 False（True＝狀態寫進框架預設目錄）
Remove-Item -LiteralPath $log
```

```bash
log="$(mktemp)"; claude -p --model haiku --debug hooks --debug-file "$log" "ok"
grep 'Hook SessionStart.*success' "$log"; grep "project: $SDD_PROJECT" "$log"
grep 'project: AISDLC_SDD' "$log" && echo "負面①失敗" || echo "負面①通過（無命中）"
test -e "$vd/build/reports/fsm/FSM-STATE-$SDD_PROJECT.yaml" && echo "負面②失敗" || echo "負面②通過"
rm -f "$log"
```

### 8.3 硬規則

1. **一律從 monorepo 根啟動 `claude`**（P3x）：`CLAUDE_PROJECT_DIR` 指向子專案時，根層啟動器找不到 router ⇒ rc=0 空輸出，hooks **靜默 fail-open**；直接跑 router
   只會 WARN＋放行。從子專案目錄啟動只會載入該目錄自己的 `.claude/settings.json`（§8.12）。
2. **三件組缺一不可**：缺 `SDD_STATE_DIR` ⇒ 狀態寫進框架預設目錄 `AISDLC_SDD/<LATEST>/build/reports/fsm/`，且 hook 對不存在的專案名會自動建檔（P3）；缺
   `SDD_PROJECT` ⇒ 鍵退回版本目錄上一層的目錄名 `AISDLC_SDD`，缺檔即建一份 `FSM-STATE-AISDLC_SDD.yaml`（INIT）（P1）；缺 `SDD_ACTIVE_VERSION` ⇒ 根 router 休眠，
   所有 hooks 不動（等於沒開）。
3. **一個 hooks-ON 視窗同時只綁一個功能**（P4）：規格檔 deny 看**路徑字串**含 `docs/01_requirements/`｜`docs/02_architecture/`｜`docs/03_testing/`，與該檔屬於哪個專案
   無關——在非草擬態，任何子專案（含根層）的這三個目錄都被擋（Write／Edit；deny 走 stdout JSON `permissionDecision=deny`、rc=0）。**允許寫規格檔的態**（
   `fsm_runtime._STATES_ALLOWING_SPEC_WRITE`）：INIT、SCENARIO_DETECT、AGENT_LOAD、SPEC_DRAFTING、SPEC_AUDIT、SPEC_REGRESSION_CHECK、RESUME_VERIFICATION。程式碼與
   `docs/04_planning/`、`docs/06_quality/` 放行。跨專案的文件編修走 hooks-OFF 視窗。
4. **CLI 形態**一律 `python -m tools.fsm_runtime.fsm_runtime …`，且 cwd 或 `PYTHONPATH`＝版本目錄（P1：直接跑 `.py`＝ImportError，rc=1）。每次呼叫 stderr 會多一行 runpy 的
   `RuntimeWarning`，與成敗無關，加 `-W ignore::RuntimeWarning` 消音；成敗只看 rc 與 stdout。
5. **兩個遙測旗標顯式 0**：`SDD_ENABLE_RULE_FIRE_TELEMETRY=0`、`SDD_ENABLE_RULE_CATCH_TELEMETRY=0`（P6：兩者為 0 時整套探針後 `git status --short` 空、governance `diff --stat` 空；
   外部專案模式的預設雖已關回寫，仍不靠預設）。

### 8.4 棕地 Stage-1 基線採納程序（G-116-08／D-116-10）

**何時做**：該子專案的上位文件（PRD／SRD／ADR／契約）從未走過 SCG、FSM 裡沒有凍結紀錄——也就是每個**新功能鍵的開頭**做一次（鍵是新檔，基準文件不變、摘要相同，做起來是幾行指令）。
採納**不是**重跑 SCG：它只把「人類確認過這批文件的現況」記進 FSM，讓後續的凍結綁內容有基準，也讓 §8.5 的增量追溯表有可引用的已凍結文件。

**鏈**：五次 `transition`（INIT→SCENARIO_DETECT→AGENT_LOAD→SPEC_DRAFTING→SCG_VALIDATION→HUMAN_PENDING）＋一次 `spec-frozen --stage Stage-1 --doc …（上位文件）--digest --root <根> --approver <人> --json`。
用 `transition` 而不是 `gate … PASS`：後者會把這一步記成 SCG 通過；採納沒有重跑 SCG，不得留下通過紀錄。reason 一律寫「baseline adoption；SCG 未重跑」。

PowerShell（前置：§8.1 已設三件組、§8.2(a) 已建檔；`$vd`、`$py` 同 §8.2；`--doc` 路徑相對 `--root`、用正斜線）：

```powershell
function sdd { & $py -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime @args }
Push-Location $vd -ErrorAction Stop
foreach ($to in 'SCENARIO_DETECT', 'AGENT_LOAD', 'SPEC_DRAFTING', 'SCG_VALIDATION', 'HUMAN_PENDING') {
    sdd transition --project $env:SDD_PROJECT --must-exist --to $to --reason 'baseline adoption；SCG 未重跑'
}
$docs = 'CLAUDE.md', 'docs/02_architecture/SRD_AGT_Phase1_Memory.md'   # 依下表填；此例＝autoclaude（--root 取 AutoClaude）
$docArgs = $docs | ForEach-Object { '--doc'; $_ }
sdd spec-frozen --project $env:SDD_PROJECT --must-exist --stage Stage-1 @docArgs --digest --root (Join-Path $root 'AutoClaude') --reason 'baseline adoption；SCG 未重跑；授權依據：<…>' --approver '<人類確認者>' --json
Pop-Location
```

bash／zsh：

```bash
sdd() { ( cd "$vd" && "$py" -W ignore::RuntimeWarning -m tools.fsm_runtime.fsm_runtime "$@" ); }
for to in SCENARIO_DETECT AGENT_LOAD SPEC_DRAFTING SCG_VALIDATION HUMAN_PENDING; do
  sdd transition --project "$SDD_PROJECT" --must-exist --to "$to" --reason 'baseline adoption；SCG 未重跑'
done
sdd spec-frozen --project "$SDD_PROJECT" --must-exist --stage Stage-1 --doc CLAUDE.md --doc docs/02_architecture/SRD_AGT_Phase1_Memory.md --digest --root "$root/AutoClaude" --reason 'baseline adoption；SCG 未重跑；授權依據：<…>' --approver '<人類確認者>' --json
```

| `sub` | Stage-1 上位文件（`--doc`；相對 `--root`） | `--root` |
|---|---|---|
| `autoclaude` | `CLAUDE.md`、`docs/02_architecture/SRD_AGT_Phase1_Memory.md`、`docs/02_architecture/SRD_AGT_Phase2_Closedloop.md`、`docs/02_architecture/SRD_AGT_Phase3_Autonomy.md`（本功能涉及的既有 FRD 另加，如 `docs/01_requirements/FRD_*.md`） | `<根>\AutoClaude` |
| `agentconsole` | `docs/01_requirements/Agent_ConsoleUI_PRD.md`、`AgentConsole/docs/02_architecture/Architecture.md`、`AgentConsole/docs/02_architecture/ADR-001-TechStack-Lock.md`、`AgentConsole/docs/02_architecture/ADR-002-Frontend-Design-System.md`、`AgentConsole/docs/02_architecture/API_Contract_P3-6.md`、`AgentConsole/docs/02_architecture/openapi-p3-6.yaml`（SCG-3 契約） | `<根>`（含根層 PRD） |
| `monorepo` | `CLAUDE.md`、`docs/04_planning/AutoSDD_Iteration_Prompt_Template.md` | `<根>` |
| `sdd` | `CLAUDE.md`、`AISDLC_SDD_v<LATEST>/AISDLC_SDD_INIT.md`、`AISDLC_SDD_v<LATEST>/workflow/sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md`（`--root` 取 `AISDLC_SDD/`，所以 `CLAUDE.md` 即 `AISDLC_SDD/CLAUDE.md`） | `<根>\AISDLC_SDD` |

**慣例**：

- 追溯表（TCS 檔頭〈增量追溯表〉，見 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈增量（delta）條款〉）裡，指向採納文件的列在「追溯 ID」欄標
  `ADOPTED`（例：`ADOPTED SRD-AGT-Phase2 §3`）；「凍結摘要」欄照填 Stage-1 記下的 `sha256:…`（`show` 的 `frozen_stages[0].spec_doc_digests` 可查）。
- `--approver` 必須是**人類確認者**（非空、≤100 字、不含控制字元；Bridge 路徑另禁 `;`）。掌舵者授權主控代決時填 `掌舵者代理（主控）`，並把授權依據（日期＋授權原話的出處）寫進 `--reason`。
  agent 不得自行判定「已確認」（Rule 8／R-9.5）。
- 採納後 `show --must-exist` 看 `frozen_stages[-1]`：`spec_docs` 與 `spec_doc_digests` 應列出全部 `--doc`；把這段逐字引進證據檔（§8.12）。

### 8.5 Stage-2 增量規格

- **文件集**：FRD-lite（US／AC 併入 TCS 檔頭）＋TCS，寫進**被治理專案自己的** `docs/03_testing/contracts/TCS-<Feature>-<date>.md`（模板
  `docs_template/sdd/testing/TEST-CONTRACT-SPEC-TEMPLATE.md`，複製後填寫、不改模板）；目前 AutoClaude、AgentConsole、monorepo 根層都還沒有 `docs/03_testing/contracts/`，隨第一份 TCS 新建（G-116-14）。
  僅新架構決策才另立 ADR，僅對外 API／事件契約變更才另附 OpenAPI delta。
- **增量追溯表**：照 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈增量（delta）條款〉逐項列出，追溯到 §8.4 採納的已凍結上位文件（路徑＋摘要）；沒列進表＝未滿足。
- **走法**：SPEC_FROZEN 之後 `transition --to SPEC_DRAFTING --reason "進入 Stage-2"` → 寫規格 → `transition --to SCG_VALIDATION --reason "SCG-0～3 驗證開始"` →
  `gate --gate SCG_VALIDATION --result PASS／FAIL`（指令全表見 [SDD_SPEC_FIRST_GATE.md](../sdd-spec-first-gate/SDD_SPEC_FIRST_GATE.md)〈FSM 寫入指令〉）→ HUMAN_PENDING → 人確認 → `spec-frozen --stage Stage-2 …`（`--doc` 必含 TCS）。
- **報告與 RTM 落 `docs/06_quality/`**（D-116-09）：SCG_VALIDATION 起 `docs/03_testing/` 被擋寫（§8.3 第 3 點），SCG 驗證報告、SCG-4 審查報告、RTM 與 RTM 驗證報告一律放 `docs/06_quality/`；
  `docs/03_testing/` 只放凍結前的測試規格（TCS、測試策略、測試計畫）。
- **增量專案的機械半段會空轉**（G-116-15；整合輪 115 的 DEF-AC-015／016／017）：SLV 的檔名樣式與 `score_frd` 在表格形 AC 上不會產生判斷，**由 QA 人讀補位**——逐條讀 AC 與追溯表，
  不要把「機械半段沒報錯」當成通過。再開症狀：QA 發現機械半段放行了有缺陷的 AC（屆時修碼）。

### 8.6 人工閘與實作

1. **人工閘**：`spec-frozen` 是人類動作，`--approver` 填人（§8.4 慣例）；確認前 agent 不得執行（Rule 8）。**凍結常態規則（掌舵者 2026-10-20 直接指令，sid `d6dfce97-92bd-4d34-b7d3-73cf5feaa23d` line 13，原文「若SelfImproving.prd各方驗證都沒問題, 即可凍結實作! ==> 改成常態規則」）**：該階段的 SCG／QA 獨立審查 PASS、且主控親驗無 P1／P2 未結時，`spec-frozen` 由主控代執行，`--approver` 填「掌舵者（常態規則 2026-10-20，sid d6dfce97-92bd-4d34-b7d3-73cf5feaa23d line 13；主控執行）」、`--reason` 引該審查報告座標；掌舵者可隨時以 T1 推翻或要求回問。不適用面（仍只准人解）：ESCALATION／ESCALATION_FINAL 的恢復（R-9.5）、守衛面准入、SelfImproving 的 K=1 PROP 決定（DEC 只認掌舵者真人發言）。細則住根 `CLAUDE.md`〈派工模型與凍結常態規則〉。**人工閘退回修訂**（整合輪 116 實證）：`HUMAN_PENDING → SPEC_DRAFTING` **不是合法邊**（CLI 回 `TransitionError`），審查者要求改規格時走 `transition --to SPEC_REGRESSION_CHECK --reason "<預審結論>"`（該態允許寫規格檔）→ 修訂 → `transition --to HUMAN_PENDING --reason "<重核依據>"` → 再 `spec-frozen`；先前的 `gate SCG_VALIDATION PASS` 紀錄仍在軌跡裡，修訂依據寫進兩次 transition 的 reason（不重跑 gate、不捏造第二次通過）。
2. **談判閘**：SPEC_FROZEN 之後 `negotiate-enter --reason "<原因>" --contract-ref "<TCS 相對路徑>"` → Dev／QA 對 oracle 達成共識後 `negotiate-exit --outcome agreed --reason "<共識依據>"` →
   IMPLEMENTATION（R-9.20.2；全表見 GATE〈FSM 寫入指令〉第 8 列）。Console 路徑由 Bridge 代為（§6.4）。
3. **徑①（委派）**：Console 路徑走 §6，由 Bridge 同步 FSM。🔴 **真實樹的委派批次**（`execution_path`＝子專案根，不是 TEMP 專案）：被委派的 claude 會讀到根層與子專案的 CLAUDE.md——Windows 上鐵律一會讓它正確地拒用 Bash，所以 `--allowedTools` 必須含 `PowerShell`（整合輪 116 DF-A 實證：沿 115 的 `Read,Edit,Write,Bash` 會讓評估指令跑不了）；每回合會載入約 86k token 的規則文件，context 量測以最後一次 API 呼叫為準（DEF-200-550）。**CLI-only**：人在 session 內 `delegate-enter --reason "<原因>"`（`--playbook-ref` 不帶，或寫不以 `run:` 開頭的值＝外來委派，Bridge 不會回收，見 §5、§6.7）→ 依 §2 編譯並執行
   playbook → 完成或使用者取消 `delegate-exit --decision done`，引擎升級型失敗 `--decision failed`（進 ESCALATION，只有人能解，§8.8）。CLI-only 路徑的 FSM 委派**不自動同步**：
   延後，再開症狀＝掌舵者在純 CLI 路徑要求 FSM 反映 AutoClaude 執行狀態。
4. **徑②（session-only）**：session 內依凍結規格實作，Rule 4（每支程式立即編譯＋跑單元測試）；AT 由 session 內自跑——Java：`gradlew test --tests …`；TypeScript：`vitest run -t …`；Python：`pytest -k …`——
   **輸出逐字貼進證據檔與 RTM 的「自動測試」欄**，沒貼＝未驗證。

### 8.7 SCG-4 獨立審查 → RELEASE

1. `transition --to PR_REVIEW --reason "SCG-4 PR 審查開始"`；審查者必須是**未參與規格撰寫與實作**的角色（AI 自寫自驗的補償控制，§6.4 C-3），以 `AISDLC_SDD:sdd-review` 產報告 → `docs/06_quality/SCG4-REVIEW-<Feature>-<日期>.md`。
2. `gate --gate PR_REVIEW --result PASS --reason "SCG-4 PASS"` → RTM_VERIFY；`AISDLC_SDD:rtm-generate verify` 產 `docs/06_quality/RTM-<System>.md`／`RTM-VERIFY-<System>.md`；`gate --gate RTM_VERIFY --result PASS --reason "SCG-5 PASS"` → RELEASE_READY。
   失敗與重試上限照 GATE〈FSM 寫入指令〉第 11、12 列（PR 5 次、同模式 3 次 → SPEC_AUDIT；RTM 2 次）。
3. **RELEASE**：功能合併進 main 且雲端 CI 綠之後，由**收尾者**執行一次 `transition --to RELEASE --reason "SCG-6 PASS；已合併 <commit>，雲端 CI 綠"`（終態；`RELEASE: set()`，不重開）。下一個功能用新鍵、新視窗。雲端 CI 紅時**不要**直接記 `RELEASE`：`gate --gate RELEASE_READY --result FAIL --reason "<CI 失敗摘要>"`（理由必填；上限 2——第 1 次失敗退回 IMPLEMENTATION 修，修好照步驟 1～2 再走 PR_REVIEW → RTM_VERIFY → RELEASE_READY，第 2 次失敗進 ESCALATION、不自動恢復；OBS-SI-117，GATE〈FSM 寫入指令〉第 14 列）。
4. 收尾時把 `show --must-exist` 的逐字輸出與 `frozen_stages[*].spec_doc_digests` 引進證據檔（狀態在被忽略的 `build/` 下，不入庫；§8.12）。

### 8.8 阻塞態三層處置（D-116-08；不改任何 hook）

FSM 進入 ESCALATION／ESCALATION_FINAL（或 TERMINATED、TOKEN_BUDGET_CRITICAL）後，根 router 轉發的 PreToolUse 對**被 matcher 命中的工具**（Write／Edit／Read／Bash／NotebookEdit／Task／Agent／Workflow）
一律 deny，deny 訊息附恢復指令（P5）；**只有人能解**（Rule 9.5、絕對禁令 #6）。ESCALATION 是**專案級黏著**：關視窗再用同一組三件組重開，仍然被擋。三層：

| 層 | 做什麼 | 誰 |
|---|---|---|
| ① 預防 | 一個視窗只綁一個功能（§8.3，不讓別的功能的態擋住這個視窗）；日常視窗可設 `SDD_HOOKS_DRY_RUN=1`（deny 降為警告；**證明守門的場次不要設**）；開場先備妥恢復指令（§8.2 b）。**不**把 `SDD_HOOKS_DRY_RUN` 寫進 `$PROFILE`／`~/.zshrc`：那會讓所有視窗的守門靜默降級 | 人 |
| ② 解除 | 在**第二終端**執行 hook 印出的恢復行（外部專案模式下自帶 `SDD_STATE_DIR`／`SDD_PROJECT`／`--project`；舊版不帶，照貼會打到框架預設 INIT 檔、回 noop rc=0 的假成功，子專案仍鎖死——G-116-01 已修）。**agent 不得代跑**（Rule 9.5）。跑完用 `show --must-exist` 確認 `current_state` 已離開 ESCALATION | 人 |
| ③ 全關 | 關視窗，重啟前清 `SDD_ACTIVE_VERSION`（PowerShell `Remove-Item Env:SDD_ACTIVE_VERSION`；bash `unset SDD_ACTIVE_VERSION`）——router 休眠、全部放行（P5：拿掉 `SDD_ACTIVE_VERSION` 即全放行）；或重啟前設 `SDD_HOOKS_DISABLE=1`（全關，保留子代理注入）。環境在 `claude` 啟動時就定案，視窗內改不動 | 人 |

③ 只關守門、**不解 FSM**：狀態檔仍是 ESCALATION，下一個 hooks-ON 視窗照樣被擋；要續做該功能就得走②。

### 8.9 閘門對映（D-116-05）

SCG 是**單一功能**的閘；AutoClaude 的 G0～G6 與 AgentConsole 的 W 波次是 **Sprint／波次層級**的交付里程碑簽核。兩套並存，不改名、不互相取代：

| 層 | 閘 | FSM 驗證 | 三子專案共同點 |
|---|---|---|---|
| 規格閘 | SCG-0～3 | `gate --gate SCG_VALIDATION`（共用一個重試預算，上限 3）→ HUMAN_PENDING → `spec-frozen` | 一個功能一份 FRD-lite＋TCS，三子專案同一套（FSM 可驗） |
| 品質閘 | SCG-4 | `PR_REVIEW`（上限 5；同模式 3 次 → SPEC_AUDIT） | 獨立審查：審查者未參與規格與實作 |
| 品質閘 | SCG-5 | `RTM_VERIFY`（上限 2） | RTM 100% 覆蓋；RTM 與報告落 `docs/06_quality/` |
| 發布閘 | SCG-6 | `RELEASE_READY`（上限 2）→ `RELEASE`（合併＋雲端 CI 綠後，§8.7）；CI 紅 → `gate --gate RELEASE_READY --result FAIL --reason "<CI 失敗摘要>"` 有界退回 IMPLEMENTATION（第 2 次 → ESCALATION，不自動恢復；OBS-SI-117） | 以倉內 CI 為憑 |
| 交付里程碑 | G0～G6（AutoClaude；見 `AutoClaude/docs/05_development/gate_audit.md`）／W1～W5 入口與出口閘（AgentConsole；見 `AgentConsole/docs/04_planning/Implementation_Plan.md` §2） | 不在 FSM 內，人工簽核 | 範圍比單一功能大：一個 G／W 之內可以有多個功能週期（多個鍵）；SCG 的通過紀錄與報告可作為簽核證據引用 |

### 8.10 skills 與路徑語意（G-116-13）

- **一律以 `AISDLC_SDD:<skill>` 前綴叫起**（來源＝`AISDLC_SDD/.claude/skills`，LATEST 的機械鏡像）。根層與 AgentConsole 不另建鏡像：每份鏡像都會進每個 session 的技能清單，既有前綴已可達。
- **AutoClaude 自己的 `.claude/skills` 也是 LATEST 的機械鏡像**，由 `AISDLC_SDD/scripts/sync_exposed_skills.py` 守：`--check` 預設同時守父層與 AutoClaude 兩個目標，stale 時訊息指出修法
  `--write --target autoclaude`（AutoClaude 專案目錄不存在的獨立 checkout，該目標略過、不紅）。原因：Claude Code 對 skills 採「最具體者優先」，在 `AutoClaude/` 的檔案上它會壓過 `AISDLC_SDD:` 前綴；
  它曾是 33 支 AISDLC v0.09 舊版（缺 sdd-gate 等 SDD 專屬 skill），於是在 AutoClaude 的檔案上叫到的是非 SDD 版。
- **skill 內相對路徑的語意**（外部專案模式下兩個根不同）：`docs/`、`build/reports/` 以**專案根**（被治理專案的根）為準；`workflow/`、`governance/`、`docs_template/`、`agent/` 以**版本目錄**
  （`AISDLC_SDD/AISDLC_SDD_v<LATEST>/`）為準。

### 8.11 Bridge 綁定一致性（探針 P8）

| 項 | 事實／規定 |
|---|---|
| 狀態目錄 | Bridge 固定讀寫 `<sdd.root 或 execution_path>/build/reports/fsm`。Console 專案的 `execution_path`＝子專案根 ⇒ 與 §8.1 的標準值（autoclaude／agentconsole／monorepo）**同址**，session 與 Bridge 看到同一份狀態；`sdd` 鍵的 `sdd-dogfood` 目錄不在此慣例內，不走 Console |
| 專案鍵 | 由請求的 `sdd.fsm_project`（compile 為 `--fsm-project`）指定；Bridge 的 `fsm_component` 與 SDD 的 `sanitize_component` 對 13 個樣本逐筆相同，傳原名與傳淨化鍵等價 |
| 寫入 | Bridge 對 FSM CLI 恆帶 `--must-exist`：狀態檔須先由 §8.2(a) 建好，Bridge 不替專案建檔（404 `fsm_not_found`） |
| compile | 一律帶 `--fsm-project <鍵>`：adapter 與 Bridge 會向上找祖先的狀態目錄，而根層 `build/reports/fsm` 是所有子專案的祖先，不帶鍵時可能選到錯的 FSM（G-116-18）。再開症狀：子專案 compile 回應的 `fsm_project` 不是該子專案的鍵 |
| 一功能一專案 | 一個 Console 專案綁一個 FSM 鍵（§6.1）；下一個功能建新的 Console 專案與新鍵。「改綁新鍵」的 UI 延後，再開症狀：同一 Console 專案要跑第二個 SDD 功能時 `PUT sdd-binding` 不夠用 |

### 8.12 已知邊界

| 邊界 | 事實 | 處置與再開症狀 |
|---|---|---|
| 子專案 hooks 的載入射程（G-116-16） | `AutoClaude/.claude/settings.json` 的 hooks（`enforce_docs_path`、`loc_budget_check`、`check_lang`、`claude_md_freshness`）只在**以該目錄為根**的 session 載入；根 session 一行都不跑，反之在 `AutoClaude/` 啟動的 session 沒有根層 SDD router | SDD session 一律從根啟動（§8.3）；AutoClaude 的守衛改由收尾前手動兜底：`python AutoClaude/tools/check_loc_budget.py --json`、`ruff check <改到的檔>`、`pytest tests/contract/test_claude_md_*.py`（cwd `AutoClaude/`）與雲端 CI |
| 根 router 的 PowerShell matcher 缺口（G-116-17，已修） | 根 `.claude/settings.json` 的 router PreToolUse／PostToolUse matcher 原不含 `PowerShell`（Windows 上唯一的 shell 載具）⇒ PowerShell 不經 context-ledger 守門與計量，阻塞態下也不被擋（hook 邏輯本身遇到工具名 PowerShell 是會 deny 的，探針 P5；缺的只是 matcher）。D-115-09 登理論洞；整合輪 116 QA 一審兩場 hooks-ON session 命中再開症狀 | 已修（根層帳本 DEF-200-551：PostToolUse 半 `d75a38a0`、PreToolUse 半 `a8504ba1`）；真機驗收＝從根啟動的三件組 headless 視窗，ESCALATION 下 PowerShell 回 JSON deny（§8.3 第 3 點形態）、INIT 下 pre／post 入帳 |
| 規格檔 deny 看路徑子字串（G-116-03） | 見 §8.3 第 3 點：一個視窗綁一個功能是唯一的處置 | 判準改動延後，再開症狀：合法寫入被他專案狀態誤擋 |
| 缺三件組的自動建檔（G-116-12） | 缺 `SDD_PROJECT`／缺檔即建（§8.3 第 2 點）；SOP 以三件組＋開場 `show --must-exist` 守 | 碼的收緊延後，再開症狀：子專案狀態目錄出現 `FSM-STATE-AISDLC_SDD.yaml` |
| 狀態不入庫（G-116-20） | 狀態檔在被忽略的 `build/` 下，凍結證據 clone 後就沒了 | 每功能收尾把 `show --must-exist` 的逐字輸出與 `spec_doc_digests` 引進證據檔（整合輪 115 §1.3 的做法） |
| 鍵的大小寫（G-116-19） | 檔案系統大小寫差異 | 標準鍵一律小寫 kebab（§8.0） |
| 機械半段空轉（G-116-15） | 見 §8.5 | 由 QA 人讀補位；碼延後，再開症狀見 §8.5 |
| Java／TS 的 AT（G-116-11） | 不入 evaluator（§7） | pytest 殼代跑延後，再開症狀：掌舵者要求 Java／TS 功能走 Console 委派 |
