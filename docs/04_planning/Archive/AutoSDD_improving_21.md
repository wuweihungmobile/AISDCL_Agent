# AutoSDD_improving_21 — 結案證據強制重推導 hook（DEF-20-001 反幻覺機械閘門）

> **軌道**：① 整合迭代｜**本輪柱別**：**B 軌（手腳 AISLDC_SDD dogfooding）**
> **下一份**：improving_22（按需）
> **driver instance**：DEF-20-001（治理閉環誠信缺口 → `closure_evidence_verify` hook）
> **建立日期**：2026-06-16｜**舵手 signoff scope**：框架本體 v0.12（`.claude/hooks/`）+ git 事實層 + 證據契約（兩項 W）
> **前置基線**：見 §1 階段一實測（zero-trust，禁文件宣稱當事實）

---

## §1 階段一：Zero-Trust 現況重偵察（本輪錨定事實）

三路 agent 親跑真實工具實測（非引用文件宣稱值）。**硬閘通過**（基線 = 上輪 floor，無 failed、無低於上輪 passed）。

| 檢查 | 命令 | 實測 | 退出碼 | 判定 |
|------|------|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | **3112 passed / 122 skipped / 0 failed**（107s） | 0 | ✅ = floor 3112 |
| 架構契約 | `lint-imports` | **8 kept / 0 broken**（184 files/466 deps） | 0 | ✅ |
| LOC 分級 | `check_loc_budget.py` | violations=0（total=17794/cap=20438） | 0 | ✅ |
| Snapshot | `snapshot_sync.py --check` | OK 對齊一致 | 0 | ✅ |
| AISDLC_SDD 閘門 | `ci-gate.sh` | v0.01:**1478** + v0.11:**1555** + scripts/tests:**25**，0 failed；arch_fitness 0 fail/3 warn(advisory) | 0 | ✅ |

**improving_20 構件複核（無造假）**：HEAD=`38de1e7`；`test_w20_catch_wiring.py` 6 passed、FF-17 相關 9 passed；R-9.2/R-9.22 failure_mode 與 `fsm_runtime.py:571/:2335` 兩接點真實存在；catch 覆蓋 4/39 與宣稱吻合。

**本輪零退化 floor（禁寫死，本輪實測值）**：
- AutoClaude pytest passed **≥ 3112**（本輪不動 AutoClaude，預期持平 3112）。
- lint-imports **8 kept / 0 broken**。
- ci-gate 雙軌：v0.01:1478（凍結基線不動）+ **v0.12:≥1555+N**（v0.12 = v0.11 複製 + 本輪新測試 N）+ scripts/tests:25。

---

## §2 本輪輸入（自上輪繼承）

### 2.1 上輪（improving_20）狀態
- 已完成 W 項：W-20-1（catch 覆蓋 2/39→4/39，R-9.2/R-9.22）、W-20-2（arch_fitness FF-17 glob 通則化，解 DEF-19-002 子串耦合）。Copy-on-Evolve v0.10→v0.11。結案 commit `0366bd1`，封存 `cb9a342`，複核 tag `v2026.06.16-17`。
- 未完成 W 項：無（improving_20 已結案）。
- 審計遺留：improving_20 結案後 zero-trust 複核登錄 **DEF-20-001（P2, open, routed 下輪 B 軌）**＝本輪 driver。

### 2.2 缺陷帳本 open/routed 與本輪處置
| DEF | 嚴重度 | 狀態 | 本輪處置 |
|-----|--------|------|---------|
| **DEF-20-001** | P2 | open/routed | **本輪實作**（W-21-1/2 閉合核心）|
| DEF-19-001 | P3 | routed | 不動（catch 覆蓋面漸進，本輪不開 R-9.39 故不推進；續 routed）|
| DEF-15-001(深層) | P2 | routed | 不動（FSM 種子模板結構異味，待真實大版重構）|
| DEF-12-002 | P3 | open | 不動（cross_version_guard nodeid 小修，非本輪 scope）|
| DEF-01-007/-009 | P3 | open/watch | 不動（環境工具/LOC watch，本輪零觸發）|

---

## §3 <Architecture_Design_Review>（寫實質 Python 前必先輸出）

### 3.1 架構純潔性：是否創造 God-object？Thin Facade 是否維持？
- **不創造 God-object**。沿用框架既有 **hook-thin + 純函式邏輯模組** 慣例（`post_commit_drift.py` thin → import `tools/fsm_runtime/drift_monitor.py` 純函式）。
  - 新增 `tools/fsm_runtime/closure_evidence.py`：純函式（解析契約 / 廉價層 git 事實重推導 / 昂貴層 log 佐證 / verdict 合成），無狀態、可單測。
  - 新增 `.claude/hooks/closure_evidence_verify.py`：thin 包裝（≤ post_commit_drift 規模），呼叫純函式、寫 advisory flag、永遠 exit 0。
- **不碰 FSMRuntime 狀態機**：hook 為 opt-in git native post-commit（同 post_commit_drift，**不走 settings.json deny 層**），不新增 FSM 狀態/轉換，不寫 FSM-STATE.yaml → **不觸 `_HAPPY_PATH`/`*.tla` → 免五軌 TLC**（Rule 9.18.1 不啟動）。

### 3.2 持久化相容：新狀態是否 additive？DAL 三後端零停機？
- **不涉 AutoClaude DAL / PlaybookCheckpoint**（本輪純 AISLDC_SDD 框架本體，AutoClaude 零變更）。
- closure verdict 落 `build/reports/`（runtime 取證輸出，additive，gitignore 涵蓋同 drift 報告），不污染源碼、不入 Copy-on-Evolve commit。

### 3.3 安全防護網：CONDITIONAL 白名單能否攔本輪新增路徑？
- 本輪**不新增「從文件生成 shell 指令」路徑**。closure hook 對 improving_NN.md 的解析僅讀取（yaml 區塊 → 結構化資料），git 重推導用**固定參數化命令**（`git cat-file -e <hash>^{commit}`、`git merge-base --is-ancestor`、`git rev-parse --verify`），claimed hash/tag 經正則白名單（`^[0-9a-f]{7,40}$` / tag 字元集）消毒後才入 `subprocess`（`shell=False`、list-form argv），不可注入。

### 3.4 對外 I/O 安全：是否新增 ToolInvocationPort 外呼？
- **無**。closure hook 全程本機 git/檔案讀取，零網路 I/O，不涉 `ToolInvocationPort`/allowlist。

---

## §4 本輪增量設計（W 項 ≤ 2，對齊舵手「兩項」signoff）

### W-21-1 — Copy-on-Evolve v0.12 + closure hook git 事實層（廉價層 fail-closed 硬核）

**Copy-on-Evolve**：`bash scripts/copy_on_evolve.sh AISDLC_SDD/AISDLC_SDD_v0.11 AISDLC_SDD/AISDLC_SDD_v0.12`（tar 排除 runtime 產物 + 補回 FSM 種子模板）。v0.11 凍結唯讀。`.gitignore` 比照 v0.11 補 v0.12 區塊（`build/reports/*` 排除 + `!FSM-STATE-TEMPLATE.yaml` negate，DEF-15-001 紀律）。

**新增 `AISDLC_SDD_v0.12/tools/fsm_runtime/closure_evidence.py`**（純函式，data/strategy 級 LOC ≤300）：
- `parse_closure_evidence(md_text) -> dict | None`：抽取 improving_NN.md 內的 ```yaml ``closure-evidence`` 區塊（無區塊回 None）。
- `verify_git_facts(evidence, repo_root) -> list[FactResult]`：對 `claimed_commits`/`claimed_tag` 廉價層真重推導：
  - commit：`git cat-file -e <hash>^{commit}`（存在）∧ `git merge-base --is-ancestor <hash> HEAD`（在當前歷史）。
  - tag：`git rev-parse --verify refs/tags/<tag>`（存在）。
  - 任一無法重推導 → `FAIL`（直擊「編造 commit/push/tag」幻覺事故核心）。
- 輸入消毒：hash/tag 經白名單正則，不合法即 `FAIL`（拒絕，非靜默放行）。

**新增 `AISDLC_SDD_v0.12/.claude/hooks/closure_evidence_verify.py`**（thin，plugin_entry 級 ≤250）：
- 定位 monorepo 根：`git rev-parse --show-toplevel`（**非** `parents[2]`——本輪陷阱：hook 在版本目錄但結案 commit 在 monorepo 根）。
- 找最新 `docs/04_planning/AutoSDD_improving_*.md` → 解析契約 → 跑 `verify_git_facts` → 寫 `.git/CLOSURE_EVIDENCE_VERDICT`（advisory flag）。
- **永遠 exit 0、<2s budget、fail-soft**（同 post_commit_drift，不阻擋 commit；fail-closed 體現在 verdict=FAIL 的 flag 標記與 CI 消費，非 block commit）。

**安裝**：擴充 `tools/install_hooks/install_post_commit.{sh,ps1}`，opt-in 串接 closure verify（git post-commit 串 drift + closure 兩 hook，皆 `|| true` advisory）。

**測試** `tools/fsm_runtime/tests/test_closure_evidence.py`（≥6 case）：契約解析（有/無區塊）、真 commit PASS、編造 commit FAIL、非祖先 commit FAIL、不存在 tag FAIL、注入字元 hash 拒絕。

### W-21-2 — 結案證據結構化契約 + 昂貴項 HEAD 綁定驗證（inconclusive fail-closed）

**契約 schema**（嵌入 improving_NN.md **末尾**真實 ```yaml ``closure-evidence`` 區塊，既是宣稱來源又機器可讀；下為 schema 說明，**刻意用 `text` fence 避免被 parser 當真契約**——DEF-21-001：解析取 last-match，真實契約放文件末尾）：
```text
closure-evidence:
  iteration: 21
  base_sha: <結案點 HEAD 全長 hash>
  claimed_commits: [<hash>, ...]
  claimed_tag: <tag 或 null>
  autoclaude_pytest_passed: 3112
  ci_gate_floors: { AISDLC_SDD_v0.01: 1478, AISDLC_SDD_v0.12: <floor>, scripts/tests: 25 }
  lint_imports: "8 kept / 0 broken"
  # ci_gate_log_ref: 保留欄位（落地實作改以 _rederive_cert_path(repo_root, HEAD) 自動推導
  #   build/reports/closure/REDERIVE-<sha>.yaml，天然綁定 HEAD；本欄 verify 不讀取）
```

**`closure_evidence.py` 增**：
- `verify_expensive_claims(evidence, repo_root) -> list[ClaimResult]`：昂貴項（pytest passed / ci_gate_floors）**不重跑**，改驗綁定：
  - `evidence.base_sha == git rev-parse HEAD`？不符 → 全昂貴項 `INCONCLUSIVE`（證據過期，提示需重新 rederive）。
  - `_rederive_cert_path(repo_root, HEAD)` 推導之 rederive 證書（`build/reports/closure/REDERIVE-<sha>.yaml`，由 `--rederive` 模式 stamp HEAD 產生）存在 ∧ 證書 base_sha == HEAD ∧ 證書 observed 數字 == 契約宣稱 → `VERIFIED`；證書缺失/base_sha 不符 → `INCONCLUSIVE`（fail-closed 不綠勾，**比照框架 embodied_grounding 零觀測 inconclusive 語意**，絕不假綠）；數字不符 → `FAIL`。
- `synthesize_verdict(fact_results, claim_results) -> ClosureVerdict`：任一 git 事實 FAIL → 整體 `FAIL`；git 全 PASS 但昂貴項有 INCONCLUSIVE → `INCONCLUSIVE`；全 VERIFIED → `VERIFIED`。
- `--rederive` CLI 模式（顯式由人/CI 跑）：廉價層永遠真重推導；昂貴層真重推導 = 由呼叫者先跑 ci-gate 產生綁定 base_sha 的 log，工具負責比對（工具自身不在 hook budget 內跑 pytest）。

**測試**（併入 test_closure_evidence.py，+≥5 case）：base_sha 符/不符、log 存在且數字符 VERIFIED、log 缺失 INCONCLUSIVE、log floor 不符 INCONCLUSIVE、verdict 合成三分支（FAIL 優先 / INCONCLUSIVE / VERIFIED）。

### 不納入本輪（明確 routed，避免 scope 蔓延 — Rule 2/3）
- **R-9.39 治理規則承載**：舵手選「兩項」；hook 為 advisory 不需規則承載即可運作；開 R-9.39 牽動 RULES_INDEX/ID_REGISTRY 取號與五軌 reachable（同 DEF-10-002「不另開 R-9.x 而用既有機制」前例）→ **routed 未來輪**（連同 DEF-19-001 catch 覆蓋面）。
- closure verdict 接入 SCG-4/5 機械閘門（FSM 整合）→ 需動 FSM，routed 未來輪。

---

## §5 LOC 預算 / importlinter 影響 / Copy-on-Evolve 範圍

| 構件 | 路徑（v0.12） | LOC 分級落點 |
|------|--------------|-------------|
| `closure_evidence.py` | `tools/fsm_runtime/` | strategy ≤300（純函式邏輯）|
| `closure_evidence_verify.py` | `.claude/hooks/` | plugin_entry ≤250（thin hook）|
| `test_closure_evidence.py` | `tools/fsm_runtime/tests/` | 測試（不計分級）|

- **importlinter**：AISLDC_SDD 框架的 arch 約束由 `arch_fitness`（非 AutoClaude `.importlinter`）守。本輪不動 AutoClaude → AutoClaude `lint-imports` 8 kept/0 broken 不受影響。v0.12 arch_fitness 沿用 v0.11（複製），FF-17 動態涵蓋 v0.12（最新版自動入閘）。
- **Copy-on-Evolve 範圍**：僅 v0.11→v0.12 整碗複製 + v0.12 內新增 3 檔 + `.gitignore` v0.12 區塊。潔淨度：結案前必跑 `git add -A -n AISDLC_SDD/AISDLC_SDD_v0.12/` dry-run 審 would-add 無 runtime/stale（DEF-11-002 紀律）。

---

## §6 B 軌 SCG-0~3（Brownfield dogfooding）

本輪以 `SDD_PROJECT=AutoSDD_iter_21`、場景 = Brownfield（既有框架改進）執行。

| SCG | 載體 | 狀態 |
|-----|------|------|
| SCG-0 需求凍結 | 本計畫書 §2/§4（DEF-20-001 閉合需求：反幻覺紀律落為機械閘門）| 本文件即凍結 |
| SCG-1 設計凍結 | §3 <Architecture_Design_Review> + §4 介面 delta | 本文件即凍結 |
| SCG-2 架構凍結 | §3.1（hook-thin + 純函式，不碰 FSM/TLA）| 本文件即凍結 |
| SCG-3 契約凍結 | §4 W-21-2 closure-evidence yaml schema | 本文件即凍結 |
| SCG-4 PR Review | 實作後三鏡 zero-trust 審查 | 階段三後 |
| SCG-5 RTM | §7 RTM | 階段四 |

---

## §7 RTM（需求追溯矩陣）

| 需求 | 設計 | 實作 | 驗證 (TC) |
|------|------|------|----------|
| R-21-1 編造 commit/tag 可被機械抓出 | W-21-1 `verify_git_facts` 廉價層真重推導 | `closure_evidence.py` + hook | 編造 commit FAIL / 非祖先 FAIL / 不存在 tag FAIL / 注入拒絕 |
| R-21-2 結案宣稱數字機器可讀 | W-21-2 closure-evidence yaml 契約 | `parse_closure_evidence` | 契約解析（有/無區塊）|
| R-21-3 昂貴項不重跑但 fail-closed | W-21-2 HEAD 綁定 + inconclusive | `verify_expensive_claims` | base_sha 符/不符 / log 缺失 INCONCLUSIVE / floor 不符 INCONCLUSIVE |
| R-21-4 hook 不阻擋 commit、不碰 FSM | W-21-1 thin hook、exit 0、git native | hook 檔 | exit 0 / 不寫 FSM-STATE / 免五軌 TLC |
| R-21-5 零退化 | §1 floor | 階段四矩陣 | AutoClaude≥3112 / lint 8kept / ci-gate 雙軌 exit 0 含 v0.12 |

---

## §8 零退化驗證矩陣（階段四全項，floor 本輪實測、禁寫死）

| 檢查 | 命令 | 通過條件 |
|------|------|---------|
| AutoClaude 全套 | `pytest tests/ -q` | ≥ 3112 passed / 0 failed |
| 架構契約 | `lint-imports` | 8 kept / 0 broken |
| LOC 分級 | `check_loc_budget.py` | 全過 |
| Snapshot | `snapshot_sync.py --check` | 新鮮 |
| AISDLC_SDD 閘門 | `ci-gate.sh` | 雙軌 exit 0，v0.01:1478 + v0.12:≥1555+N + scripts/tests:25 |
| 五軌 TLC | （僅 FSM 變更時）| **本輪不觸發**（無 `_HAPPY_PATH`/`*.tla` 變更）|
| 潔淨度 | `git add -A -n AISDLC_SDD/AISDLC_SDD_v0.12/` | would-add 無 runtime/stale（DEF-11-002）|

---

## §9 回流分流

- **框架程式/hook 缺陷類**（DEF-20-001）→ RFC：`AISDLC_SDD_v0.12/build/planning/active/SDD_improving_Automation_27.md`（軌道② 帳本，最新 26→27）記錄提案 → 修改落 v0.12 + EVOLUTION_LOG + CHANGELOG。
- 本輪行進中新發現框架摩擦 → 即記 `docs/06_quality/AutoSDD_Defect_Log.md`（DEF-21-xxx）。

---

## §10 結案證據契約（closure-evidence，dogfooding 自驗 — 本輪新 hook 驗本輪自身結案）

> 本輪以新落地的 closure_evidence hook 驗證自身結案宣稱（DEF-20-001 閉合精神之下游採用）。
> 契約指向結案主體 commit A（`5f8b633`）。dogfooding 自驗：`base_sha == HEAD == A` 時跑
> `python -m tools.fsm_runtime.closure_evidence --rederive --observed '<實測>'` 產綁定 HEAD 證書 →
> hook 得 **VERIFIED**（git 事實 A 存在且為 HEAD 祖先 + 昂貴項證書數字符）。
> 本契約區塊為文件中唯一真實 ```yaml ``closure-evidence`` 區塊（§4 schema 為 ```text fence 不被解析，
> 解析取 last-match，DEF-21-001）。

```yaml
closure-evidence:
  iteration: 21
  base_sha: 5f8b6334d543772692238b004f27bd19c6f87160
  claimed_commits:
    - 5f8b6334d543772692238b004f27bd19c6f87160
  claimed_tag: null
  autoclaude_pytest_passed: 3112
  ci_gate_floors:
    AISDLC_SDD_v0.01: 1478
    AISDLC_SDD_v0.12: 1574
    scripts/tests: 25
  lint_imports: "8 kept / 0 broken"
```
