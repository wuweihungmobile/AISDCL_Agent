# AutoSDD_improving_01 — AISDLC-SDD × AutoClaude 深度整合執行計畫

> **版本**：01（首輪迭代）
> **日期**：2026-06-12
> **作者**：Dr. Alan（L5 自治系統與微核心架構總監）
> **狀態**：✅ **已凍結**（2026-06-12 🔴 人工確認：使用者於本日 session 明示「確認 AutoSDD_improving_01.md 凍結」，W1 准予啟動）
> **絕對前提**：零退化（Zero-Regression）— AutoClaude 基線 **2,732 passed / 122 skipped**（2026-06-12 實測 107.61s，非引用文件數字）；AISDLC_SDD `ci-gate.sh`（pytest not-chaos + arch_fitness --strict）必須全綠。

---

## 0. 現況事實基線（Zero-Trust 實測，非文件宣稱）

本計畫所有設計皆錨定下列**已驗證事實**（出處：2026-06-12 三路偵察 + 親自實測）：

| # | 事實 | 證據位置 | 對設計的影響 |
|---|------|---------|------------|
| F1 | AutoClaude 全套 pytest = **2732 passed / 122 skipped** | 本機實測 `python -m pytest tests/ -q` | 零退化基線數字 |
| F2 | `GoalSynthesisPlugin` **既存**（PRIORITY=50，POST_RUN GOAL_SYNTHESIS 驗證） | `autoclaude/plugins/goal_synthesis_plugin.py:29` | Stage 1 改為「擴展事件、不動既有 plugin」 |
| F3 | `ErrorClass` enum 既存 7 類（syntax/import/assertion/type/environment/timeout/unknown），**無 SDD_CONTRACT_VIOLATION** | enum：`autoclaude/execution/error_classifier.py:13-20`；`ErrorClassifier` 類：`error_classifier.py:35-42` | Stage 3 需新增枚舉值 + 分類規則 |
| F4 | `workflow_type` 已支援 `auto \| aisdlc \| aisdlc_sdd`，偵測器既存，但**無任何 SDD→Playbook 轉譯器** | `autoclaude/models/playbook.py:64`、`execution/workflow_detector.py:14-44` | `SddToPlaybookAdapter` 是真缺口，為 Stage 2 主體 |
| F5 | `PlaybookTask` 欄位：`step_id/name/prompt/command/expected_output_regex/evaluator_command/max_retries/maintain_context/evaluator_timeout_seconds/token_guard` | `models/playbook.py:16-50` | 轉譯器輸出 schema 的目標格式 |
| F6 | `PlaybookCheckpoint` 已有 additive 欄位先例（Gap-007-A/041/042/048、SD_06 W5 run_id/goal_task_id） | `utils/checkpoint_manager.py:27-56` | SDD 狀態以同模式 additive 掛入 |
| F7 | DAL 三後端 `yaml_only/both/db_only`，ID 策略 stem vs sha256 | `infra/repositories/factory.py:38-61` | 新欄位不得破壞三後端 round-trip |
| F8 | CONDITIONAL 三層防禦：`_SAFE_COND_PATTERN` 白名單 + `{!,`,>,<,~,$}` 黑名單 + `shell=False`/`shlex`，遞迴 ≤4 | `core/services/mutation/_conditional_evaluator.py` | 防護網不動；adapter 生成物需等強度過濾 |
| F9 | `.importlinter` 7 contract（plugin 隔離 / core 純度 / Brain↮Executor / runner-no-checkpoint…）；core-purity 的 forbidden_modules 僅 `autoclaude.execution` / `autoclaude.infra`，**不含** `autoclaude.models` | `.importlinter:1-213`（全檔 213 行，2026-06-12 複驗；core-purity 於 L43-59） | 架構紅線，新構件選址依此決定 |
| F10 | AISDLC_SDD：10 場景（各 SOP/DeepDive/QuickRef；`scenarios/` 另有 6 個跨場景 .md——ERROR_RECOVERY_GUIDE / FRONTEND_SPECIFIC_GUIDE / SCALING_GUIDE / SCENARIO_AGENT_MAPPING / SCENARIO_TRANSITION_GUIDE 5 指引 + README，**非場景本體**）、25 Agents（7 core + 18 specialized）、R-9 規則 **37 條**（R-9.1~9.37）+ R-SELF-STRIDE 共 **38 檔**（`ls governance/rules/` 實數；`RULES_INDEX.md:9` 表頭「共 35 檔」為過期數字）、SCG-0~6 全標 🔴 | `scenarios/`、`agent/`、`governance/rules/`、`governance/RULES_INDEX.md` | Stage 1 映射來源 |
| F11 | Contract Test Spec 模板族：`TEST-CONTRACT-SPEC-TEMPLATE.md`（AC→AT 100% 映射 + Gherkin）等 7 式 | `docs_template/sdd/testing/` | Stage 2 解析目標格式 |
| F12 | `ci-gate.sh` 位於 `AISDLC_SDD/scripts/`（v0.01 目錄**外**一層）；五軌 TLC 由 Python `tlc_runner.py --module` 跑（已驗證支援五軌）；shell 版 `run_tlc.sh` 僅 2 軌屬 legacy | `AISDLC_SDD/scripts/ci-gate.sh:44-47`、`tools/fsm_runtime/tlc_runner.py:93-94` | Stage 4 單一真相源錨點 |
| F13 | FSM `_HAPPY_PATH` **42** 狀態（`len(_HAPPY_PATH)` 實測 = 42，2026-06-12）；Rule 9.18.1：改 `_HAPPY_PATH` 必同步 `SDD_FSM.tla` 重跑 TLC | `tools/fsm_runtime/transition_rules.py:12` | v0.02 若加狀態必走形式化同步 |
| F14 | AISDLC_SDD 僅 v0.01 存在，**無 v0.02**；INIT.md 記 Phase D~Y（ACT-010~159）但無版本演化規劃 | `AISDLC_SDD_INIT.md:16-61` | §6 版本演化規則為本計畫新訂 |

---

## 1. <Architecture_Design_Review>（程式碼設計前強制自我檢核）

### 1.1 架構純潔性 — 是否創造 God-object？Thin Facade 是否維持？

**否，且維持。** 整合面拆為三個正交構件，`playbook_runner.py` 一行不改：

- **Port（契約層）**：`autoclaude/core/ports/spec_source.py` — `ISpecSource` 抽象介面（contract tier ≤400 LOC）。core 只認識此介面，不知 SDD 文件格式。
- **Adapter（實作層）**：`autoclaude/infra/adapters/sdd_to_playbook_adapter.py` — 實作 `ISpecSource`（adapter tier ≤400 LOC）。
- **Plugin（橫切層）**：`autoclaude/plugins/sdd_governance_plugin.py` — 訂閱 EventBus，constructor 注入 ports（plugin_entry tier ≤250 LOC）。

既存 `GoalSynthesisPlugin`（F2）**不修改**；SDD 治理 plugin 與其透過 EventBus 事件協作（plugin-isolation contract #1 保證互不 import）。`.importlinter` 7 條契約逐條核對：新 plugin 不 import 其他 plugin（#1）、新 port 在 core 內無 infra 依賴（#2）、不觸碰 Brain/Executor 邊界（#4/#5）、runner 不 import checkpoint 內部（#6，本設計 runner 零改動天然滿足）、plugin 經 Port 用 observability（#7）。

另：`ISpecSource` 引用 `PlaybookTask` 採與既有 `IEvaluator` **完全相同的引用模式**——runtime 相對 import（`from ...models.playbook import PlaybookTask`，`core/ports/evaluator.py:17` 既有先例；`core/hookspec.py:18` 同模式）。core-purity contract（`.importlinter:43-59`）的 forbidden_modules 僅含 `autoclaude.execution` / `autoclaude.infra`，**不含** `autoclaude.models`，故此模式經 core/ports 既有先例複驗、不破壞 core-purity。

### 1.2 持久化相容 — 新狀態是否寫入 PlaybookCheckpoint？DAL 三後端零停機是否維持？

**是，且維持。** 新增**單一 additive 欄位**：

```python
# PlaybookCheckpoint 新增（比照 Gap-007-A / SD_06 W5 既有 additive 模式，F6）
sdd_governance: dict = field(default_factory=dict)
# 內容契約（dict 內 schema，由 plugin 維護）：
# { "scg_gate": "SCG-3", "fsm_state": "IMPLEMENTATION",
#   "contract_violations": [{"step_id": ..., "at_id": "AT-001-2-1", "ts": ...}],
#   "spec_digest": "sha256:..." }   # 規格凍結指紋，防 drift
```

- 舊 checkpoint 反序列化 → `default_factory` 補空 dict，**零遷移破壞**。
- 三後端（F7）checkpoint 走整體序列化（YAML / JSONB blob），additive dict 欄位**不需 alembic schema 變更**，`yaml_only → both → db_only` 零停機切換路徑不變。
- **證明義務**：新增契約測試「含 `sdd_governance` 之 checkpoint 在三後端 round-trip 等價 + 舊格式（無此欄位）載入相容」，掛入既有 equivalence CI job。

### 1.3 安全防護網 — CONDITIONAL 白名單能否攔截鏈式攻擊向量？

**能，且新增來源點防禦。** CONDITIONAL 三層縱深（F8）**零修改**——SDD 生成的 playbook 與手寫 playbook 走完全相同的驗證管線。新風險點是 adapter「從 SDD 文件生成 `evaluator_command`」：若規格文件被汙染即成注入向量。對策（三點截斷鏈式攻擊）：

1. **模板白名單**：adapter 只允許兩種 evaluator 模板 — `python -m pytest <path> -k "<at_id>" -q` 與 `python -m tools.<module> <args>`；任何自由字串指令一律拒絕並標記 `SPEC_TAINTED`。
2. **參數消毒**：`<path>/<at_id>/<args>` 經 `shlex.quote` + 套用與 CONDITIONAL 同款黑名單字元集 `{!,`,>,<,~,$}` + 白名單 regex。
3. **末端複驗**：生成的 playbook 仍經 `pre_run_validator` plugin（PRIORITY=5 最早執行）整體驗證。

**結論：三項檢核全數自洽，無架構衝突，准予實作。**

---

## 2. 階段一：實體映射與介面設計（Mapping & Interfaces）

### 2.1 分析 — `global_goal` 如何驅動 `sa-analyst` / `sd-architect`

AutoClaude 的 `global_goal`（playbook 頂層欄位，由 `global_goal_anchor` plugin PRIORITY=35 注入每步驟）在語意上等價於 AISDLC-SDD 的「SCG-0 需求凍結輸入」。映射鏈：

```
global_goal ──(SddGovernancePlugin 偵測 workflow_type ∈ {aisdlc, aisdlc_sdd})──▶
  Step[SPEC]: prompt 套用 AISDLC_SDD_v0.01/agent/core/04.sa-analyst-zh.yaml 角色 → 產出 FRD/US/AC（SCG-0 素材）
  Step[DESIGN]: prompt 套用 AISDLC_SDD_v0.01/agent/core/05.sd-architect-zh.yaml 角色 → 產出 SRD/C4/ADR（SCG-1~2 素材）
  Step[CONTRACT]: 產出 TEST-CONTRACT-SPEC（AC→AT 映射，SCG-3 素材）
──(ISpecSource.compile)──▶ 後續 PlaybookTask 序列（實作 + 雙重驗證）
```

驅動方向是**單向**的：`global_goal` 是因，SDD 文件是果，PlaybookTask 是果的果。GOAL_SYNTHESIS 階段由既存 `GoalSynthesisPlugin` 驗證「果的果」是否回到「因」（全局目標達成），形成閉環。

### 2.2 實作策略 — Port 依賴清單

| 構件 | 依賴 Port | 用途 |
|------|----------|------|
| `SddGovernancePlugin` | `IBrain`（`decide_correction` / `decide_escalation`） | 契約違反時請 Minimax 決策修正 vs 升級 |
| 〃 | `IObservabilityPort`（contract #7 強制） | `sdd.scg_gate_pass/fail` counter、違反事件 span |
| 〃 | `IStateRepository`（經 checkpoint plugin 事件，**不直接 import** checkpoint 內部，守 contract #6） | `sdd_governance` 欄位持久化 |
| `SddToPlaybookAdapter` | 實作 `ISpecSource`（新 Port） | SDD 文件 → PlaybookTask |
| 〃 | `IEvaluator`（組裝雙重驗證，不重新發明） | 沿用 regex + evaluator_command 既有契約 |

**新 Port 介面定義**（`core/ports/spec_source.py`）：

```python
"""ISpecSource — SDD 規格來源契約（contract tier ≤400 LOC）。

core 僅依賴本介面；SDD 文件格式知識封裝於 infra adapter。
PlaybookTask 引用模式與既有 IEvaluator（core/ports/evaluator.py:13-17）完全相同：
Protocol + runtime 相對 import models（core-purity 不禁 autoclaude.models，
.importlinter:43-59 複驗）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ...models.playbook import PlaybookTask


@dataclass(frozen=True)
class SpecContract:
    """單條 AC→AT 契約（自 TEST-CONTRACT-SPEC 解析）。"""
    ac_id: str                    # AC-XXX
    at_id: str                    # AT-XXX-Y-Z
    gherkin: str                  # Given-When-Then 全文
    expected_regex: str           # 轉譯後的 expected_output_regex
    evaluator_cmd: str            # 白名單模板生成的 evaluator_command
    scg_gate: str                 # 所屬閘門（SCG-3/4/5）


@dataclass(frozen=True)
class SddSpec:
    """凍結後的規格快照。digest 寫入 checkpoint 防 drift。"""
    spec_path: str
    digest: str                   # sha256(規格全文)
    scenario: str                 # 10 場景之一
    contracts: tuple[SpecContract, ...] = field(default=())


class ISpecSource(Protocol):
    def load_spec(self, spec_dir: str) -> SddSpec:
        """解析 docs/ 下已凍結的 SDD 文件。

        凍結判定（複驗 fsm_runtime.py / state_loader.py 實際機制）：讀取
        state_loader 管理的 FSM 狀態檔 build/reports/fsm/FSM-STATE-{project}.yaml，
        確認 fsm_state.frozen_stages 含對應 stage（record_spec_frozen 寫入
        {stage, frozen_at, spec_docs}，fsm_runtime.py:280-287 同步 transition 至
        SPEC_FROZEN）或 fsm_state.current_state 已達 SPEC_FROZEN 之後狀態；
        否則 raise SpecNotFrozenError。
        """
        ...

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        """SddSpec → PlaybookTask 序列（含雙重驗證綁定）。純函數、無 IO。"""
        ...
```

---

## 3. 階段二：動態路由與任務轉換（SddToPlaybookAdapter）

### 3.1 分析 — SDD（MD/YAML）→ `PlaybookTask` 的轉譯規則

解析目標是 F11 的 `TEST-CONTRACT-SPEC-TEMPLATE.md` 結構（Section 1 AC→AT 映射表 + Section 2 Gherkin）。轉譯規則表：

| SDD 來源欄位 | PlaybookTask 目標欄位（F5 實名） | 轉譯規則 |
|-------------|--------------------------------|---------|
| AT-XXX-Y-Z 條目 | `step_id` | `sdd-{scenario}-{at_id}`（kebab-case，全 playbook 唯一） |
| Gherkin `Given/When` | `prompt` | 模板：「依下列契約實作並使測試通過：\n{gherkin}\n規格出處：{spec_path}（digest {digest[:8]}）」 |
| Gherkin `Then` 斷言 | `expected_output_regex` | 斷言關鍵詞 → escape 後的 regex（如 `Then 回傳 201` → `(?i)201\|created`）；不可推導時 fallback `\bPASS(ED)?\b` 並標 `weak_regex=true` 供審查 |
| AT 自動化分類（Unit/Integration/E2E/Contract） | `evaluator_command` | 白名單模板 `python -m pytest {test_path} -k "{at_id_sanitized}" -q`（§1.3 消毒） |
| 場景 SOP 的 retry 政策（SCG-4 max 5 / SCG-5 max 2，對齊 `transition_rules.py:246` RETRY_LIMITS 的 PR_REVIEW=5 / RTM_VERIFY=2） | `max_retries` | SCG-4 類步驟=5、SCG-5 類=2、其餘 None（用 global_invariants） |
| — | `maintain_context` | 同一 AC 內的 AT 連續步驟 = true；跨 AC = false（隔離污染） |

**Gherkin `Then` → `expected_output_regex` 轉譯實例**（`test_gherkin_to_regex` 必覆蓋，見 §7 測試清單）：

| Gherkin `Then` 斷言 | 轉譯產出 regex | 規則 |
|---------------------|---------------|------|
| `Then 回傳 201 Created` | `(?i)(201\|created)` | 狀態碼 + 字面詞抽取，case-insensitive 並聯 |
| `Then 顯示錯誤訊息「餘額不足」` | `餘額不足` | 引號內字面值 `re.escape` 後直出 |
| `Then 回應時間 < 200ms` | `\bPASS(ED)?\b`（fallback） | 量化 NFR 斷言不可由文字推導 → fallback 並標 `weak_regex=true` |

凡標 `weak_regex=true` 的 AT，adapter **必須**經 `IObservabilityPort` 寫入 observability audit log（事件 `sdd.weak_regex`，含 at_id 與原始 Gherkin），供人工審查雙重驗證強度；不可 silent fallback。

### 3.2 實作策略 — `SddToPlaybookAdapter` 骨架

```python
"""infra/adapters/sdd_to_playbook_adapter.py — adapter tier ≤400 LOC。"""
import hashlib, re, shlex
import yaml
from autoclaude.core.ports.spec_source import ISpecSource, SddSpec, SpecContract
from autoclaude.models.playbook import PlaybookTask

_AT_ROW = re.compile(r"^\|\s*(AC-\d+)\s*\|\s*(AT-[\d\-]+)\s*\|", re.M)
_DENY = set("!`><~$&;")                      # ⊇ CONDITIONAL 黑名單（F8），再加 &;
_EVALUATOR_TEMPLATES = (
    'python -m pytest {path} -k "{at}" -q',
    "python -m tools.{module} {args}",
)

class SpecNotFrozenError(RuntimeError): ...
class SpecTaintedError(RuntimeError): ...

# current_state 已達 SPEC_FROZEN 之後即視為凍結（happy path 上 SPEC_FROZEN 的
# 後繼狀態，如 TEST_CONTRACT_NEGOTIATED / IMPLEMENTATION；fsm_runtime.py:1245）
_POST_FROZEN_STATES = frozenset({"SPEC_FROZEN", "TEST_CONTRACT_NEGOTIATED",
                                 "IMPLEMENTATION", ...})

class SddToPlaybookAdapter(ISpecSource):
    def load_spec(self, spec_dir: str) -> SddSpec:
        text = self._read_contract_spec(spec_dir)        # 找 *CONTRACT*SPEC*.md
        self._assert_frozen(spec_dir)                    # 凍結硬閘（規格先行）
        digest = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
        return SddSpec(spec_dir, digest, self._scenario_of(text),
                       tuple(self._parse_contracts(text)))

    def _assert_frozen(self, spec_dir: str) -> None:
        # 凍結偵測（複驗實際機制；「SCG-3: PASS」文字戳記不存在於任何文件，
        # 不可作為凍結依據——閘門 PASS 只以 decision_trace（trigger="gate_pass"、
        # reason="{gate} PASS"，fsm_runtime.py:183-195）+ retry reset 留痕）：
        # 讀 state_loader 管理的 build/reports/fsm/FSM-STATE-{project}.yaml
        # （state_loader.py:44-45），確認下列任一成立，否則 raise：
        #   (a) fsm_state.frozen_stages 含對應 stage —— record_spec_frozen 寫入
        #       {stage, frozen_at, compaction_report, spec_docs}
        #       （state_loader.py:204-219），且 fsm_runtime.record_spec_frozen
        #       同步 transition 至 SPEC_FROZEN（fsm_runtime.py:280-287）；
        #   (b) fsm_state.current_state ∈ _POST_FROZEN_STATES（state_loader.py:83）。
        doc = yaml.safe_load(self._read_fsm_state(spec_dir))
        root = (doc or {}).get("fsm_state", {})
        frozen_stages = root.get("frozen_stages") or []
        if not frozen_stages and root.get("current_state") not in _POST_FROZEN_STATES:
            raise SpecNotFrozenError(spec_dir)

    def compile_tasks(self, spec: SddSpec) -> list[PlaybookTask]:
        return [self._to_task(spec, c) for c in spec.contracts]

    def _sanitize(self, fragment: str) -> str:
        if any(ch in _DENY for ch in fragment):
            raise SpecTaintedError(fragment)             # §1.3 鏈式攻擊截斷點 2
        return shlex.quote(fragment)
    # _parse_contracts / _to_task / _scenario_of：純函數，
    # 每條 AT 產出 SpecContract → PlaybookTask（evaluator_command 僅由
    # _EVALUATOR_TEMPLATES 內插生成 — 截斷點 1；最終仍過 pre_run_validator — 截斷點 3）
```

**接線**（`core/wiring.py`）：`ISpecSource` 由 wiring 在 `workflow_type ∈ {aisdlc, aisdlc_sdd}` 時組裝注入——wiring 是 core-purity contract（#2）唯一豁免點，合法。

### 3.3 入口整合設計（compile-then-run 兩段式）

**問題（zero-trust 複驗）**：runner 的載入鏈是 `playbook_runner._load_playbook`（`execution/playbook_runner.py:253-255`）→ `boot_helper.load_playbook_impl`（`execution/boot_helper.py:78-85`）→ 直接 `yaml.safe_load` + `Playbook.model_validate`，**純函式、無任何注入點**。若要在 runner 內掛 SDD 編譯，必然修改 Thin Facade——違反 §1.1 紅線。

**決策：不掛 runner，採兩段式 compile-then-run。**

- **第一段（編譯）**：新增 CLI 編譯工具 `autoclaude/tools/sdd_compile.py`（新建 `autoclaude.tools` 子套件；經複驗 `autoclaude/` 下**現無** `tools/` 子套件、無命名衝突。不選 repo 根層 `AutoClaude/tools/`，因該處腳本群為純 stdlib 維運工具、不 import autoclaude 套件本體）：

  ```
  python -m autoclaude.tools.sdd_compile --spec-dir <docs path> --out <playbook.yaml>
  ```

  內部呼叫 `SddToPlaybookAdapter.load_spec` + `compile_tasks`，輸出**標準 playbook YAML**（schema 與手寫 playbook 完全一致）。

- **第二段（執行）**：走既有入口 `python -m autoclaude <playbook.yaml>`，runner 路徑零修改。

**優點**：

1. **runner 零修改**：`playbook_runner.py` / `boot_helper.py` 一行不動，Thin Facade 絕對維持（§1.1 檢核自動成立）。
2. **生成物自然經過既有防護網**：編譯產物是標準 YAML，執行時照常通過 `pre_run_validator` plugin 與 CONDITIONAL 三層防禦（F8）——§1.3 截斷點 3 無需任何特判。
3. **可人工 review 生成的 YAML**：兩段之間留有人工檢視點，符合 SCG-4（PR Review）精神——SDD 生成的 playbook 等同一份待審工件，凍結後才執行。

**LOC / 契約落點**：`sdd_compile.py` 屬 CLI 薄殼（plugin_entry 級 ≤250 LOC）；`autoclaude.tools` 不在 core-purity source_modules 內，import infra adapter 合法；不觸碰 `.importlinter` 任何既有 contract。

---

## 4. 階段三：雙重防護網整合（Governance & Escapement）

### 4.1 分析 — 違反 SDD 契約時的安全停機 / 自演化路徑

AISDLC-SDD 的 Rule 9 防護是 **hook 時間軸**（SessionStart / PreToolUse / PostToolUse / post-commit），AutoClaude 的防護是 **EventBus phase 時間軸**（PRE_RUN / PRE_ATTEMPT / POST_EVALUATE / ON_ESCALATION / POST_RUN）。語意映射（phase 欄全數對照 `core/hookspec.py:25-70` 的 `KernelPhase` 枚舉複驗；**不存在** `PRE_RUN_VALIDATE` / `ON_EVALUATE` / `ON_CHECKPOINT` 等枚舉值）：

| AISDLC-SDD hook | 語意時點 | 實際 KernelPhase 枚舉名（hookspec.py:25-70 複驗） | 移植後行為 |
|----------------|---------|------------------------------------------------|-----------|
| `session_start.py`（reconcile + 規則 lazy-load） | 執行前驗證 | `PRE_RUN` | plugin 載入 spec digest、依 `scg_gate` 以 rule_loader 同款邏輯選規則注入 prompt |
| `context_ledger_pre.py`（FSM guardrail + 95% 拒絕） | 嘗試前守門 | `PRE_ATTEMPT` | 檢查當前步驟是否越過未 PASS 的 SCG 閘門 → deny（拋 `SDD_CONTRACT_VIOLATION`）；token 防護**沿用既有 token_guard plugin（F8 前置 PRIORITY=30），不重複造** |
| `context_ledger_post.py`（記帳 + 警告） | 評估後記帳 | `POST_EVALUATE` | evaluator 結果含契約違反標記 → 計入 `sdd_governance.contract_violations` |
| `post_commit_drift.py`（drift ≥0.3 advisory） | 評估後 advisory | `POST_EVALUATE`（advisory 分支） | spec digest 不符（規格被改）→ 標記 SPEC_AUDIT 需求，**非阻塞** |
| FSM ESCALATION（不自動退出，等人工） | 升級決策 | `ON_ESCALATION` → MinimaxEvolver | 違反 N 次（預設 3，鏡像 SCG-4「同模式 3 次→SPEC_AUDIT」）→ 交 `IBrain.decide_escalation`；Minimax 失敗 fallback `PlaybookEvolver`（既有路徑 F3 觸發鏈不變） |
| （checkpoint 掛載，無對應 hook） | 持久化快照 | `ON_CHECKPOINT_SAVE_REQUEST` / `ON_CHECKPOINT_RESTORE` | `sdd_governance` dict 掛入/還原 checkpoint——沿用 `GotoCounterPlugin` 既有先例（`goto_counter_plugin.py:50-51` 訂閱、`:61-65` 回傳 snapshot IHookResult）；`CheckpointPlugin` 本身訂閱 7 phase 含 `ON_PERSISTENCE_REQUEST`（`plugins/checkpoint/plugin.py:90-100`） |

**安全停機**：`ESCALATION_FINAL` 等價物 = 演化提議也失敗 → plugin 發 checkpoint 事件（含 `sdd_governance` 全量狀態）→ runner 既有 halt 機制停機，狀態可由 `--fresh` 以外的正常 resume 恢復。**絕不 silent-skip 失敗測試**（兩專案共同紀律）。

### 4.2 實作策略 — `ErrorClassifier` 擴充 + plugin

```python
# execution/error_classifier.py — 既有 7 類（F3）追加第 8 類（additive，零破壞）
class ErrorClass(str, Enum):
    ...                                   # 既有 7 類不動
    SDD_CONTRACT_VIOLATION = "sdd_contract_violation"

# 分類規則（classify() 追加，置於 ASSERTION 之前以免被吃掉）：
#   1. evaluator stderr/stdout 含 "SDD-VIOLATION[" 結構化標記（adapter 生成的
#      evaluator 包裝層在 AT 失敗時輸出 "SDD-VIOLATION[{at_id}]"）
#   2. 或 PRE_ATTEMPT 階段 SCG 閘門 deny 拋出之例外型別
```

```python
"""plugins/sdd_governance_plugin.py — plugin_entry ≤250 LOC。"""
class SddGovernancePlugin(HookSpec):
    PRIORITY = 45        # token_guard(30)/anchor(35)/persistence(40) 之後、
                         # PRE_ATTEMPT tie-breaker 群(50) 之前 → 閘門先於快速路徑

    def __init__(self, brain: IBrain, observability: IObservabilityPort,
                 spec_source: ISpecSource): ...     # constructor 注入，禁 import infra

    # subscribed_phases（全為 hookspec.py:25-70 實際枚舉名）：
    # PRE_RUN:                    load_spec → digest 入 kernel_state；未凍結 → fail-fast
    # PRE_ATTEMPT:                步驟 scg_gate 序檢查；越閘 → SDD_CONTRACT_VIOLATION
    # POST_EVALUATE:              violation 記帳；digest drift → advisory 標記
    # ON_ESCALATION:              同模式 ≥3 → decide_escalation → (修正|演化|停機)
    # ON_CHECKPOINT_SAVE_REQUEST: 回傳 sdd_governance snapshot（GotoCounterPlugin
    #                             同款 IHookResult 模式，goto_counter_plugin.py:51,61-65）
    # ON_CHECKPOINT_RESTORE:      自 checkpoint 還原 sdd_governance dict
```

**註冊**：`wiring._REGISTER_ORDER` 於 `playbook_persistence`(40) 與 `fast_path`(50) 之間插入 `sdd_governance`(45)；不與既有 tie-breaker 群同優先級，迴避順序耦合。

---

## 5. 階段四：CI 平價與形式化驗證（Verification）

### 5.1 分析 — 「地端綠 ⇒ 雲端綠」與 TLA+ 雙源一致性

兩專案已各有單一真相源（F12）：AutoClaude = `tools/local_ci_gate.ps1` ↔ `ci.yml`（審計確認逐項鏡像）；AISDLC_SDD = `scripts/ci-gate.sh`（pytest not-chaos + arch_fitness --strict + 選配五軌 TLC）。整合層**不另立第三真相源**，只加一層薄聚合：

```
AISDCL_Agent/tools/integration_gate.ps1   （新增，薄聚合，無自有檢查邏輯）
  ├─ [1/3] AutoClaude:  powershell tools/local_ci_gate.ps1        # 既有真相源
  ├─ [2/3] AISDLC_SDD:  bash scripts/ci-gate.sh                   # 既有真相源（Git Bash / WSL / Docker）
  └─ [3/3] 整合測試:    cd AutoClaude && python -m pytest tests/integration/test_sdd_bridge/ -q
```

**TLA+ 雙源紀律**：本整合 v0.01 階段**不改 `_HAPPY_PATH`**（SDD 治理以 AutoClaude plugin 落地，不新增 SDD FSM 狀態），故五軌 TLC 不需重跑即維持有效。v0.02 若引入 `AUTOCLAUDE_DELEGATED` 觀察態（§6），依 Rule 9.18.1 必須同步 `SDD_FSM.tla` 並以 `tlc_runner.py` 五軌重驗，PR 必附 `TLC_DISTINCT/GENERATED/DEPTH` 輸出。

### 5.2 驗收工具 — `cc-switch` 多模型後端對比

整合驗收時以 `cc-switch` 快速切換 Claude Code CLI 後端（本地 Qwen / 外部 API），對同一 SDD playbook 跑 A/B：

```
cc-switch use <profile-A> && autoclaude sdd_bridge_smoke.yaml --fresh   # 記錄 pass率/演化次數
cc-switch use <profile-B> && autoclaude sdd_bridge_smoke.yaml --fresh
# 對比指標：步驟一次通過率、CORRECTION 次數、SDD_CONTRACT_VIOLATION 次數、token 峰值
```

### 5.3 零退化驗證矩陣（每一輪迭代的 DoD）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥2732 passed / 0 failed（新測試只增不減） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 7+ kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過（port≤400 / adapter≤400 / plugin≤250） |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | pytest not-chaos 全綠 + arch_fitness exit<2 |
| DAL 等價 | equivalence job（含新 round-trip 契約測試） | 三後端等價 |
| 五軌 TLC（僅 FSM 變更時） | `bash scripts/ci-gate.sh --full-tlc` | 五軌 0 violation |

---

## 6. AISDLC_SDD 版本演化設計（v0.01 → v0.02 → …）

> 本專案開發本身**立即採用 v0.01 流程**：本文件即 SCG-0/1 規格載體；§2-4 的介面/設計 = SRD+ADR 素材（SCG-1~2）；§3.1 轉譯表 = Contract（SCG-3）；實作 PR 過 SCG-4；§5.3 矩陣 = RTM（SCG-5）。

**版本演化規則（本計畫新訂，補 F14 缺口）**：

1. **Copy-on-Evolve**：`AISDLC_SDD_v0.01/` 凍結為唯讀基線；演化時複製為 `AISDLC_SDD_v0.0(N+1)/`，於新目錄修改。模板「不可直接改」紀律推廣到版本層。
2. **每版必附** `EVOLUTION_LOG.md`，最小模板（五欄）：

   | 欄位 | 內容 |
   |------|------|
   | 版本 | `v0.0(N) → v0.0(N+1)` |
   | 日期 | 凍結/發布日期 |
   | delta 清單 | 新增 ACT 編號（自 `ID_REGISTRY.yaml` next_free 起算）、新增/修改 R-* 規則、新增 FSM 狀態 |
   | TLC 證據 | 五軌 TLC 輸出（TLC_DISTINCT/GENERATED/DEPTH；無 FSM 變更則註明 N/A） |
   | 回退指引 | AutoClaude config 指回舊版目錄的步驟 + 已知不相容點 |

3. **FSM 變更 = 形式化義務**：任何 `_HAPPY_PATH` / `*.tla` delta 必附五軌 TLC 全綠輸出（Rule 9.18.1）。
4. **回退保證**：AutoClaude 端以 config 指定 SDD 版本目錄，可隨時指回 v0.01。回退路徑由 CI gate 守護：integration_gate（§5.1）增加一項「以 config 指回 v0.01 跑 `test_sdd_bridge` 煙霧」的回退驗證，確保回退不是僅存在於文件上的承諾。
5. **遷移相容性檢查（v0.01→v0.02 必跑）**：(a) `.claude/hooks/`（session_start / context_ledger_pre/post / post_commit_drift）在新目錄路徑下仍可載入；(b) AutoClaude config 的 SDD 版本目錄切換後 `sdd_compile` 可重編譯既有 spec；(c) 既有 checkpoint（含 `sdd_governance` 欄位）在切版後 resume 相容（digest 指向舊版 spec 時觸發 advisory 而非 hard fail）。

**v0.02 規劃內容（Phase Z：AutoClaude 執行引擎橋接，ACT-162~171）**：

> 編號複驗：`governance/ID_REGISTRY.yaml:23-25` 記 `next_free: act: 162 / rule: "9.38"`；`AISDLC_SDD_INIT.md` 尾部同記 next_free **ACT-162 / R-9.38**（Phase Y 已持有 ACT-159~161 / R-9.37）。依「monotonic-from-next-free」分配原則，本計畫自 ACT-162 起取 10 個號（162~171），R-9.38 確為下一可用規則號。

| 項目 | 內容 |
|------|------|
| 新 workflow | `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` — SDD 文件 → playbook 的標準作業 |
| 新 agent | `agent/specialized/sdd-playbook-compiler-zh.yaml` — 駕馭 `SddToPlaybookAdapter` 的編譯者角色 |
| 新規則 | `governance/rules/R-9.38-playbook-translation-fidelity.yaml`（R-9.38 = `ID_REGISTRY.yaml:25` next_free）— AT↔step 100% 雙向映射，違反→SPEC_AUDIT |
| 新觀察態 | `AUTOCLAUDE_DELEGATED` —— **v0.02 提案，現況不存在**（已複驗 transition_rules.py 無此狀態）。落地前置條件見下方設計義務 |
| 場景擴充 | 10 場景 SOP 各加「§AutoClaude 自動化執行」小節（QuickRef 同步） |

**`AUTOCLAUDE_DELEGATED` 設計義務（合併前置條件，缺一不可）**：

- (a) 提交 `SDD_FSM_ENGINE.md` delta：定義入邊（自 `IMPLEMENTATION` 進入）與出邊（返回 `IMPLEMENTATION` / 升級 `ESCALATION`），並把該狀態納入 `transition_rules.py` 的 `OBSERVATION_STATES` frozenset（`transition_rules.py:214`；經複驗實際集合名為 `OBSERVATION_STATES`、**無底線前綴**，現有成員均為「非阻塞觀測狀態」並逐一附 ACT 編號註解——新狀態照此模式登記，且不得進入 `_EMERGENCY_TARGETS` deny 清單，`transition_rules.py:200-206`）。
- (b) 同步 `formal/SDD_FSM.tla`（Rule 9.18.1 雙源紀律）。
- (c) 五軌 TLC（SDD_FSM / META_FSM / COMPOSITION_FSM / OPTIMIZATION_FSM / FLEET_FSM）**預跑全綠才准合併**，PR 附 TLC_DISTINCT/GENERATED/DEPTH 輸出。

**v0.03+ 方向**（僅列待證假設，不在本輪範圍）：契約違反知識回流 `knowledge_base` plugin → Hub Sync 跨專案學習；`MinimaxEvolver` 演化提議反向生成 SDD 規格修訂草案（spec 與 playbook 雙向同步）。

---

## 7. 重構後目錄結構（delta only）

```
AISDCL_Agent/
├── docs/                                      # 整合層文件（本計畫起新增，依 01-08 編號制）
│   ├── 04_planning/
│   │   ├── AutoSDD_improving_01.md            # 本文件
│   │   └── AutoSDD_Iteration_Prompt_Template.md
│   └── 06_quality/
│       └── AutoSDD_ZeroTrust_Audit_01.md
├── tools/
│   └── integration_gate.ps1                   # §5.1 薄聚合閘門（新增）
├── AutoClaude/
│   ├── autoclaude/
│   │   ├── core/ports/spec_source.py          # 新增（contract ≤400）
│   │   ├── core/wiring.py                     # 修改：註冊 sdd_governance + ISpecSource 組裝
│   │   ├── tools/sdd_compile.py               # 新增：compile-then-run CLI（§3.3；新建 autoclaude.tools 子套件）
│   │   ├── infra/adapters/sdd_to_playbook_adapter.py   # 新增（adapter ≤400）
│   │   ├── plugins/sdd_governance_plugin.py   # 新增（plugin_entry ≤250；PRIORITY=45）
│   │   ├── execution/error_classifier.py      # 修改：+SDD_CONTRACT_VIOLATION（additive）
│   │   └── utils/checkpoint_manager.py        # 修改：+sdd_governance dict（additive）
│   └── tests/
│       ├── plugins/test_sdd_governance.py     # coverage ≥90%（plugin SOP）
│       ├── infra/test_sdd_to_playbook_adapter.py
│       ├── infra/test_gherkin_to_regex.py     # §3.1 轉譯實例 + weak_regex audit 路徑
│       ├── tools/test_sdd_compile_cli.py      # §3.3 編譯產物 schema + pre_run_validator 煙霧
│       ├── contract/test_checkpoint_sdd_roundtrip.py    # 三後端等價
│       └── integration/test_sdd_bridge/       # 端到端煙霧測試
└── AISDLC_SDD/
    ├── AISDLC_SDD_v0.01/                      # 凍結唯讀（規則 1）
    └── AISDLC_SDD_v0.02/                      # v0.02 落地時自 v0.01 複製演化（§6）
```

**實作順序（每支完成立即編譯+測試，絕不累積）**：
W1 `spec_source.py`（port+單測）→ W2 `error_classifier` 擴充（單測）→ W3 `sdd_to_playbook_adapter.py`（單測+消毒攻防測試+`test_gherkin_to_regex`）→ W4 `sdd_compile.py` CLI（§3.3；單測 + 生成 YAML 過 pre_run_validator 煙霧）→ W5 `checkpoint` additive 欄位（三後端 round-trip 契約測試）→ W6 `sdd_governance_plugin.py`（plugin 測試 ≥90%）→ W7 wiring 註冊 + 整合煙霧 → W8 `integration_gate.ps1` + cc-switch A/B 驗收 → W9 AISDLC_SDD_v0.02 目錄演化（含 TLC 重驗）。每個 W 結束跑 §5.3 矩陣，任一紅 → 停機修復。

---

## 8. RTM（本計畫自身的需求追溯矩陣）

| 需求 | 落點 | 驗證 |
|------|------|------|
| global_goal 驅動 SA/SD agent | §2 映射鏈 + SddGovernancePlugin PRE_RUN | test_sdd_bridge 煙霧 |
| SDD→PlaybookTask 自動綁定雙重驗證 | §3 SddToPlaybookAdapter | test_sdd_to_playbook_adapter + test_gherkin_to_regex |
| 入口零侵入（compile-then-run，runner 不改） | §3.3 sdd_compile CLI | test_sdd_compile_cli（產物過 pre_run_validator） |
| Rule 9 → EventBus 攔截 + SDD_CONTRACT_VIOLATION | §4 plugin + classifier | test_sdd_governance |
| Minimax 自演化修正路徑 | §4.1 ON_ESCALATION 映射（既有鏈不改） | 既有 evolution 測試 + 新煙霧 |
| 地端綠⇒雲端綠 | §5.1 integration_gate.ps1 | 矩陣 §5.3 |
| TLA+ 雙源一致 | §5.1/§6 規則 3 | tlc_runner 五軌輸出 |
| 零退化 | 全篇 additive 設計 | 2732+ passed 基線 |
| v0.02 演化 | §6 | EVOLUTION_LOG.md + TLC 證據 |

---

*本文件為 SCG-0/1 規格載體。🔴 人工確認點：實作（W1）啟動前，須由人類確認本計畫凍結。*
