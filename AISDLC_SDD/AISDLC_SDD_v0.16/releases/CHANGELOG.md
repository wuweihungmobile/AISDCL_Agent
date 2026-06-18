# AISDLC-SDD Framework CHANGELOG

**維護者**: AISDLC-SDD Framework Team
**最後更新**: 2026-06-18

---

## [v0.16] - 2026-06-18（Copy-on-Evolve 自 v0.15；v0.15 凍結唯讀）

> AutoSDD_improving_38 — B 軌 dogfooding 缺陷漸進清償（無 A/C 軌新功能）。DEF-19-001 catch 歸因覆蓋 5/39 → 7/39（+2）。

### 新增（DEF-19-001 catch 覆蓋補強，沿用既有 R-9.3 / R-SELF-STRIDE，不取新 ACT/Rule）
- **W-38-1（R-SELF-STRIDE，5/39→6/39）** — `governance/rules/R-SELF-STRIDE.yaml` 補 `failure_mode`（SANDBOX_HARDENING_GATE policy_violation → ESCALATION structural，**唯一生產落點**；明文 verdict=pass 不歸因、與既有 5 條零交集）；`tools/fsm_runtime/fsm_runtime.py` `exit_sandbox_hardening_gate` 的 policy_violation 分支接 `_record_escalation_catches(["R-SELF-STRIDE"])`。
- **W-38-2（R-9.3，6/39→7/39）** — `governance/rules/R-9.3-logical-consistency-guard.yaml` 補 `failure_mode`（record_spec_audit 的 SPEC_AUDIT 耗盡 → ESCALATION；**明文排除** implementation-budget-exceeded 直接 escalate〔正交、無規則〕與 R-9.1 gate-retry 落點，杜絕雙重歸因）；`record_spec_audit` 的 escalate 分支接 `_record_escalation_catches(["R-9.3"])`。
- `tools/fsm_runtime/tests/test_w38_catch_wiring.py` — **+8 case**（R-SELF-STRIDE / R-9.3 各：flag ON catch+1、flag OFF 零退化、**非重疊守門**；真實規則具非空 failure_mode×2）。runtime `catch_attribution_coverage` 實測 **7/39**。

### 紅線守界（B 軌）
- **DEF-18-001 寧缺勿濫** — 只接「有唯一生產 escalation 落點 + 可定義 failure_mode + 無雙重歸因」的規則；R-9.3 的 failure_mode 明文排除正交落點（同 improving_37 R-9.7「僅 9.7.2」範式）。
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（catch 純記帳、不寫 FSM-STATE、不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.15 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.16 `pytest -m "not chaos"` = **1605 passed / 4 skipped / 0 failed**（v0.15 1597 + 8）。Copy-on-Evolve 以 `scripts/copy_on_evolve.sh` 匯出 856 tracked 檔（零 runtime cruft）。

---

## [v0.15] - 2026-06-18（Copy-on-Evolve 自 v0.14；v0.14 凍結唯讀）

> AutoSDD_improving_37 — B 軌 dogfooding 缺陷漸進清償（無 A/C 軌新功能）。DEF-19-001 catch 歸因覆蓋 4/39 → 5/39。

### 新增（W-37-1：DEF-19-001 catch 覆蓋補強，沿用既有 R-9.7，不取新 ACT/Rule）
- `governance/rules/R-9.7-precise-halt-m1.yaml` — 補 `failure_mode` 欄位（可參與 catch 自動歸因）。**明文僅涵蓋 9.7.2**（HUMAN_PENDING 逾時 ≥168h → 自動 ESCALATION），排除 9.7.3（AUTO_COMPACT per-stage 超限，歸 R-9.2 `trigger_auto_compact`），杜絕雙重歸因（DEF-18-001 寧缺勿濫）。
- `tools/fsm_runtime/fsm_runtime.py` — 新增 thin 方法 `escalate_human_pending_timeout(reason=...)`：record_escalation + flag-gated `_record_escalation_catches(["R-9.7"])` 同落點（與 R-9.1/R-9.2/R-9.21/R-9.22 四條既有接線同範式）。
- `.claude/hooks/session_start.py` — ACT-023 HUMAN_PENDING 逾時 ESCALATION 分支改委派 `rt.escalate_human_pending_timeout(reason=reason)`（catch 與 escalation 同落點才不漏記）。
- `tools/fsm_runtime/tests/test_w37_catch_wiring.py` — **+4 case**（flag ON catch+1 / flag OFF 零退化 / 非重疊守門：9.7.3 路徑只 R-9.2 catch+1、R-9.7 恆 0 / 真實 R-9.7 具非空 failure_mode）。

### 紅線守界（B 軌）
- **R-9.9 降級不接** — 親驗無唯一生產 escalation 落點（state_loader 損毀 `raise` 非 escalate；chaos_runner record_escalation 屬測試載具模擬其他規則失敗模式），依 DEF-18-001 不臆測歸因（掌舵者預授權 fallback）。
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（catch 純記帳、不寫 FSM-STATE、不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.14 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；flag `SDD_ENABLE_RULE_CATCH_TELEMETRY` 預設 OFF；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.15 `pytest -m "not chaos"` = **1597 passed / 4 skipped / 0 failed**（v0.14 1593 + 4）。Copy-on-Evolve 以 `git archive` 匯出 855 tracked 檔（零 runtime cruft）。

---

## [v0.14] - 2026-06-17（Copy-on-Evolve 自 v0.13；v0.13 凍結唯讀）

> AutoSDD_improving_23 — B 軌 XAI 深化（dogfooding，無 A/C 軌新功能）。補完 Phase Y 視覺化儀表板 `_26.md` 列入、§D 收官以 pagination 替代而靜默未交付的 Folding 降維子項。

### 新增（W-23-1：Folding 降維補完，隸屬既有 R-9.37 PY-3，不取新 ACT/Rule）
- `tools/fsm_runtime/recursion_topology_view.py` — fold env 旋鈕 `SDD_VIZ_FOLD`(預設 **OFF**＝v0.13 行為) / `SDD_VIZ_FOLD_MIN`(預設 3, clamp[2,64])；`RenderBudget` additive `fold_enabled`/`fold_min`；`TopoNode` additive `folded`/`folds`。新增純函式 `fold_topology(view)`：把窗內極大「內部簡單鏈」（連續 in==1∧out==1∧非 kept-node）塌縮為單一 `[+k more]` 折疊超節點（錨定鏈首 + 商圖重接邊）；**永不折疊 entry/critical/分支/匯聚/sink/未訪問節點**（結構要角恆可見）。`extract_topology` 末尾 flag-gated 套用。
- `render_mermaid` 折疊超節點專屬 `classDef fold` 渲染；`render_json` additive 輸出 `folded`/`folds`。
- **PY-2 fold-aware 誠實收縮稽核** — `verify_topology_consistency` 擴充：以 expanded（含折疊展開）窗格錨定（真實大小誠實 nothing dropped）+ 折疊合法性 f1（窗內成員 in==1∧out==1 + 連續真實呼叫邊）/ f2（鏈 rank 嚴格遞減）/ f3（不藏 entry）+ 商圖邊比對（折疊內部邊吸收、跨群邊保留，杜絕杜撰/漏畫）。**fold OFF 時 group=identity、expanded=shown，五道恆過 ⇒ 與 v0.13 逐位元行為相容**。
- `chaos_runner.py` — `VISUALIZATION_FOLD_DRIFT_FLAP` + `_visualization_fold_drift_flap_is_bounded`（偽造折疊吞 sink / 丟成員必被攔、忠實折疊放行，納入 100 輪 bounded）。
- `tools/fsm_runtime/tests/test_phase_y.py` — **+13 case**（fold OFF 零退化 / 鏈塌縮 / 不折要角 / 誠實 verify+guard / 4 道折疊偽造 fail-closed / env clamp / 10⁶ 有界 / fold_topology 零 while 零遞迴 / chaos fold-drift 註冊+bounded）。

### 流程修復
- **DEF-23-002** — `build/planning/active/SDD_improving_Automation_26.md`（Phase Y §D 已收官）、`_27.md`（closure §6 標 archive）兩份已完成 RFC `git mv` 入 `build/planning/archive/`（修「active=待決 / archive=已決」生命週期漂移；v0.13 凍結不回改）。
- **DEF-23-001**（文檔計數口徑釐清）— v0.13 CHANGELOG 上條稱 `test_cross_version_guard.py`「+2 case（25→27）」，**口徑釐清：27＝`scripts/tests/` 全套合計（跨檔），非單檔函式數**（該檔單檔實測為 10 個 test 函式 / 10 passed、無 parametrize；DEF-12-002/DEF-22-001 回歸鎖確在檔內）。

### 紅線守界（B 軌）
- **無 FSM 狀態/規則/`*.tla`/`.cfg` 變更**（Folding 為 `recursion_topology_view` 內 read-only 純投影轉換、不寫 FSM-STATE/不 churn；`transition_rules.py` + 5 `*.tla`/`.cfg` 對 v0.13 **逐位元零差異** → **免五軌 TLC**，Rule 9.18.1 不啟動）；`VisualizationBounded==churn<=MAX_CHURN` 不受影響；不碰 meta⁹/meta-oracle；不提 Token 上限；ID_REGISTRY 不取新 ACT/rule（沿用 _27/DEF-20-001 前例 + Rule 2）。
- 驗證：v0.14 `pytest -m "not chaos"` = **1593 passed / 4 skipped / 0 failed**（v0.13 1580 + 13）；chaos **34 passed**（100 輪 bounded_ratio==1.0 含新 FOLD_DRIFT）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept。Copy-on-Evolve 以 `git archive` 匯出 853 tracked 檔（零 runtime cruft）。

---

## [v0.13] - 2026-06-17（Copy-on-Evolve 自 v0.12；v0.12 凍結唯讀）

> AutoSDD_improving_22 缺陷清償輪（B 軌 dogfooding，無 A/C 軌新功能）。

### 重構（W-22-2：DEF-15-001 深層 — FSM 種子模板移出 runtime 輸出目錄，本版觸發者）
- `tools/fsm_runtime/state_loader.py` — `TEMPLATE_PATH` 由 `REPO_ROOT/build/reports/fsm/FSM-STATE-TEMPLATE.yaml` 改為與 loader 同層的 tracked 源碼位 `Path(__file__).resolve().parent/"templates"/"FSM-STATE-TEMPLATE.yaml"`（docstring 同步）。`DEFAULT_STATE_DIR`（runtime 狀態檔輸出 = build/reports/fsm/）**不變** → **輸入（種子模板）/ 輸出（runtime 狀態檔）分離**。
- 物理移檔 `build/reports/fsm/FSM-STATE-TEMPLATE.yaml` → `tools/fsm_runtime/templates/FSM-STATE-TEMPLATE.yaml`（內容逐位元零變更）；同步 3 處文件連結（`SDD_FSM_ENGINE.md` / `AISDLC_SDD_UPGRADE_SOP.md` / `test-failure-analyzer/SKILL.md`）。
- `AISDLC_SDD/.gitignore` v0.13 區塊：模板移出後 build/reports/ **整樹排除、不再需 negate idiom**（消除 DEF-11-001/15-001 反覆打補丁的結構異味根因）；`copy_on_evolve.sh` 補回模板特例對 v0.13+ 自然成 no-op（保留供 ≤v0.12 舊佈局相容）。
- `tools/fsm_runtime/tests/test_template_location.py` — **3 case**（TEMPLATE_PATH 在 templates/ 非 build/reports / 模板 is_file 且 `_load_template` 載入非空 dict / DEFAULT_STATE_DIR 仍 build/reports/fsm）。

### 修復（W-22-1：shared infra `AISDLC_SDD/scripts/`，免 Copy-on-Evolve）
- **DEF-12-002** — `cross_version_guard._is_path_arg` 在 `os.path.exists` 前剝 `token.split("::",1)[0]`，修 pytest nodeid（`path::test`）含 `::` 被誤判非路徑 → bare 分支誤展全版 false fire。
- **DEF-22-001**（dogfooding 當場揭露，P2 真 bug）— `VERSION_RE=AISDLC_SDD_v0\.0\d+` 僅匹配 v0.00–v0.09，對現役 v0.10~v0.13 失效（DEF-19-002 同根十位數跨越，當時漏修此處）→ 放寬 `v0\.\d+` 通則化。`scripts/tests/test_cross_version_guard.py` +2 case（25→27）。

### 紅線守界（B 軌）
- **無 FSM 狀態/規則/`*.tla` 變更**（模板移位純屬檔案位置 + 路徑常數；`transition_rules.py` + 5 `*.tla` 對 v0.12 **逐位元零差異**，`diff -q` 實測全 IDENTICAL → **免五軌 TLC**，Rule 9.18.1 不啟動）；ID_REGISTRY 不取新 ACT/rule。
- 驗證：v0.13 `pytest -m "not chaos"` = **1580 passed / 0 failed**（v0.12 1577 + 3）；ci-gate 雙軌 exit 0 v0.01:1478 / **v0.13:1580** / scripts/tests:27（FF-17 自證 v0.13 入閘）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept；LOC 0；snapshot 新鮮；潔淨度 `git add -A -n` 853 無 runtime 殘留（模板正常 tracked、build/reports 整樹忽略）。

---

## [v0.12] - 2026-06-16（Copy-on-Evolve 自 v0.11；v0.11 凍結唯讀）

### 新增（B 軌 DEF-20-001 反幻覺機械閘門 — 結案證據強制重推導；AutoSDD_improving_21 W-21-1/W-21-2）
- `tools/fsm_runtime/closure_evidence.py` — 純函式邏輯模組（同 `drift_monitor.py` 慣例）。**廉價層** `verify_git_facts`：對 improving_NN.md 末尾 `closure-evidence` 契約宣稱的 `claimed_commits`/`claimed_tag`，以 `git cat-file -e`+`merge-base --is-ancestor`+`rev-parse --verify` 就 monorepo 根真實狀態重推導（白名單正則消毒、list-form argv shell=False），任一無法重推導 → **FAIL**（直擊「編造 commit/push/tag」幻覺事故核心）。**昂貴層** `verify_expensive_claims`：pytest passed / ci-gate floors **不重跑**，改驗綁定當前 HEAD 的 rederive 證書（`write_rederive_cert` stamp HEAD），契約 base_sha≠HEAD 或證書缺失/數字不符 → **INCONCLUSIVE**（fail-closed 不綠勾，比照 embodied_grounding 零觀測語意，絕不假綠）。`synthesize_verdict` 三分支優先序 FAIL>INCONCLUSIVE>VERIFIED。
- `.claude/hooks/closure_evidence_verify.py` — thin git post-commit hook（同 `post_commit_drift.py`）：`repo_root_from()` 以 git toplevel 定位 monorepo 根、**永遠 exit 0 / <2s budget / fail-soft / 不阻擋 commit**，verdict 寫 `.git/CLOSURE_EVIDENCE_VERDICT` + `build/reports/closure/VERDICT-<sha>.yaml`。**把反幻覺紀律由「agent 跨 session 自律」升級為框架機械可驗閘門**。
- `tools/install_hooks/install_post_commit.{sh,ps1}` — 擴充串接 drift（指 v0.01）+ closure（指 v0.12），opt-in 不經 settings.json deny 層。
- CLI 入口 `_main(argv, repo_root=None)` + `__main__`（`--rederive --observed '<json>'` stamp HEAD 落盤證書 / 無參數 evaluate 印 verdict）。**DEF-21-003**（dogfooding 揭露 → fixed@v0.12）：hook INCONCLUSIVE 訊息承諾的 `python -m ... --rederive` 原無 CLI 入口、指令無動作，本輪補完。
- `tools/fsm_runtime/tests/test_closure_evidence.py` — **22 case**（tmp 真實 git repo 驗 cat-file/merge-base/rev-parse 真實行為：真 commit PASS/編造 FAIL/非祖先 FAIL/注入拒絕/真 tag PASS/缺 tag FAIL；昂貴層 stale base_sha + 缺證書 INCONCLUSIVE、證書符 VERIFIED、不符 FAIL；verdict 三分支；last-match 解析；端到端+持久化；CLI rederive 寫證書/bad-json/無參數 evaluate）。
- 結案契約 schema＝`docs/04_planning/AutoSDD_improving_NN.md` 末尾 ```yaml ``closure-evidence`` 區塊（機器可讀宣稱來源）。RFC：`build/planning/active/SDD_improving_Automation_27.md`。

### 修復（DEF-21-001 dogfooding 衍生 → fixed@v0.12）
- `tools/fsm_runtime/closure_evidence.py:parse_closure_evidence` — improving_NN.md 多 `closure-evidence` yaml 區塊（§4 schema 範例 + 末尾真實契約）致解析歧義，改 **last-match**（對齊 DEF-02-002 `tlc_runner.parse_tlc_summary` findall[-1] 紀律）；計畫書 §4 schema fence 改 ```text 雙保險。

### 紅線守界（B 軌）
- **決策不新增 R-9.x**（advisory hook 不需規則承載即可運作，避免牽動 RULES_INDEX/ID_REGISTRY 取號與五軌 reachable，同 DEF-10-002 前例 + Rule 2）。治理規則承載 + catch 覆蓋面推進 + closure 接入 SCG-4/5 機械閘門 → routed 未來輪。
- **無 FSM 狀態/規則/`*.tla` 變更**（hook 不新增狀態/轉換、不寫 FSM-STATE；`transition_rules.py` + 5 `*.tla` 對 v0.11 逐位元零差異 → **免五軌 TLC**，Rule 9.18.1 不啟動）。closure hook advisory 不阻擋 commit、零觸碰 FSM/規則/既有測試。驗證：v0.12 `pytest -m "not chaos"` = **1577 passed / 0 failed**（v0.11 1555 + 22 新測試〔19 核心 + 3 CLI〕）；ci-gate 雙軌 exit 0 v0.01:1478 / v0.12:1574 / scripts:25（FF-17 自證 v0.12 入閘；ci-gate 跑於 CLI 補完前）；AutoClaude **3112 passed / 0 failed** 持平；lint 8 kept；LOC 0；snapshot 新鮮；潔淨度無 runtime 殘留（closure runtime 產物根 gitignore，DEF-21-002）。**dogfooding 自驗**：commit A `5f8b633` 後回填真實契約 + rederive 證書 → hook VERIFIED（反幻覺迴圈閉合）。

---

## [v0.11] - 2026-06-16（Copy-on-Evolve 自 v0.10；v0.10 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 catch 覆蓋補強；AutoSDD_improving_20 W-20-1）
- `governance/rules/R-9.2-context-budget.yaml` — 補 `failure_mode`：per-stage `auto_compact` 超限 → ESCALATION（R-9.2 守望的失敗模式）。
- `governance/rules/R-9.22-adversarial-self-improving-phase-j.yaml` — 補 `failure_mode`：`spec_patch` per-AC 上限耗盡 → 直升 ESCALATION（R-9.22 守望的失敗模式）。
- `tools/fsm_runtime/fsm_runtime.py` — 在兩個既有 `record_escalation` 呼叫點接 v0.10 既有 `_record_escalation_catches()`：`trigger_auto_compact` per-stage 超限分支歸因 `["R-9.2"]`、`enter_spec_patch_proposal` per-AC 超限分支歸因 `["R-9.22"]`。**catch 自動歸因覆蓋 2/39 → 4/39**（沿用 v0.10 catch 三要件契約：failure_mode 自描述 ∧ 攔截事件真實發生 ∧ 結構化歸因 rule_id，顯式可歸因非時序猜測）。**預設 OFF＝v0.10 行為（零退化）**；fail-closed；只增 catch_count 永不 set_maturity（R-9.20 #11）。**閉合 DEF-19-001 兩條確定路徑**。
- `tools/fsm_runtime/tests/test_w20_catch_wiring.py` — 6 新測試（R-9.2/R-9.22 各 flag ON 真記+1 + flag OFF 零退化 + 真實凍結規則具非空 failure_mode）。

### 修復（W-20-2 / DEF-19-002 通則化 → fixed@v0.11）
- `tools/arch_fitness/arch_fitness.py` — FF-17 驗證正則 `_CI_GATE_LATEST_GLOB_RE` 由寫死 `AISDLC_SDD_v0\.0\*` 放寬為通則 `AISDLC_SDD_v0\.[0-9\[*]`（接受 `v0.0*` / `v0.[0-9]*` / `v0.[1-9]*` / `v0.*`），**解除 improving_19 雙 glob 修復被迫保留 `v0.0*` 子串的結構耦合異味**（ci-gate.sh 此後可清掉子串改純通則化仍過 FF-17）；同步更新兩處顯示字串。
- `tools/fsm_runtime/tests/test_arch_fitness.py` — 4 新測試（FF-17 接受 4 種通則 glob 形式）。

### 紅線守界（B 軌）
- W-20-1 沿用 v0.10 既有 catch helper，零新增方法、零 FSM 拓樸變更。**無 FSM 狀態/規則/`*.tla` 變更**（`transition_rules.py` + 5 `*.tla` 對 v0.10 逐位元零差異 → 免五軌 TLC）。catch 記帳只增 `catch_count`、永不 `set_maturity`（退役維持 🔴 人工，R-9.20 #11）；R-9.2/R-9.22 之外 35 規則 failure_mode 未定義者 fail-closed 不記（DEF-19-001 漸進補強）。驗證：v0.11 `pytest -m "not chaos"` = **1555 passed / 0 failed**；ci-gate v0.01:1478 / v0.11:1555 / scripts:25；AutoClaude 3112 持平；lint 8 kept；LOC 0；snapshot 新鮮。

---

## [v0.10] - 2026-06-16（Copy-on-Evolve 自 v0.09；v0.09 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — catch 側契約定義並接入 FSM 主迴圈；AutoSDD_improving_19 W-19-1/W-19-2/W-19-3）
- `tools/fsm_runtime/rule_loader.py` — `Rule` 新增 optional `failure_mode`（規則自描述守望的失敗模式）；`_write_rule` **條件寫回 failure_mode**（非空才寫，解決 fire/catch round-trip 抹欄之持久化潔淨度陷阱）；新增 `record_state_catches(attributed_rule_ids)`（對「歸因∩failure_mode非空∩非deprecated」子集各記 catch+1，fail-closed）。
- `tools/fsm_runtime/fsm_runtime.py` — 把 catch 記帳**接入主迴圈**：新增 `_RULE_CATCH_TELEMETRY_ENV="SDD_ENABLE_RULE_CATCH_TELEMETRY"` 開關 + `_rule_catch_telemetry_enabled()` + `_record_escalation_catches()`；接在兩個 `record_escalation` 呼叫點（`record_attempt` escalate→`["R-9.1"]`、`exit_monitor_violation`→`["R-9.21"]`）。`rule_fire_telemetry_stats()` 證書 **翻 `catch_side_wired=True`** + 新增 `total_catches` + `catch_attribution_coverage`（誠實揭露覆蓋率）。**預設 OFF＝v0.09 行為（零退化）**；fail-closed：catch 記帳失敗絕不阻塞已落定的 escalation。**閉合 DEF-18-001「catch 側語意未定義」**——catch 契約三要件（failure_mode 自描述 ∧ 攔截事件真實發生 ∧ 結構化歸因 rule_id），**顯式可歸因、非時序鄰近猜測**。
- `governance/rules/R-9.1` / `R-9.21` — 補 `failure_mode` 欄（兩條確定可歸因規則）。
- `tools/fsm_runtime/tests/test_rule_catch_telemetry_wiring.py` — 11 新測試（含持久化陷阱回歸鎖 + monitor violation 整合真接 + 要件①無 failure_mode 不歸因 + 空歸因寧缺勿濫）；fire 測試 Case 7 同步斷言。

### 紅線守界（B 軌）
- `record_state_catches` 只增 `catch_count` 計數、**永不自動退役 active 規則**；退役維持 🔴 人工 `set_maturity(reviewed_by=...)`（R-9.20 #11 不弱化）。catch_count>0 是 `propose_graduation` 保護有用規則不被誤退役的依據，補實 arch_fitness FF-16 GAP-X2 的真實資料缺口。**未歸因 escalation / 無 failure_mode 規則 fail-closed 不記、不污染 ROI**（DEF-18-001 寧缺勿濫）。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.09 逐位元零差異 → 免五軌 TLC）。**新記 DEF-19-001**（P3, routed）：catch 歸因目前覆蓋 2/39 規則，餘漸進補強（coverage 誠實揭露）。

---

## [v0.09] - 2026-06-16（Copy-on-Evolve 自 v0.08；v0.08 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — 規則命中遙測接入 FSM 主迴圈；AutoSDD_improving_18 W-18-1/W-18-2）
- `tools/fsm_runtime/rule_loader.py` — 新增批次 helper `record_state_fires(state, *, caught=False)`：單次 `load_all`、對 `load_for_state(state)` 命中規則一次性增 `scaffold_roi.fire_count` 各寫一次（避 per-rule O(N²) 重載；deprecated 不記）。
- `tools/fsm_runtime/fsm_runtime.py` — 把 `record_fire` on-watch 記帳**接入主迴圈**：新增 `_RULE_FIRE_TELEMETRY_ENV="SDD_ENABLE_RULE_FIRE_TELEMETRY"` 開關 + `_rule_fire_telemetry_enabled()` + `rule_fire_telemetry_stats()`（L5 可量測信號：fire_ladder 降冪 / `retirement_eligible` + XAI 安全證書）；`transition()` 於 `save_state` 後 flag-gated 呼 `record_state_fires(dst)`。**預設 OFF＝v0.08 行為（零退化）**；fail-closed：記帳失敗絕不阻塞已落定的轉態。**閉合 DEF-17-001 點名的「`fire_count=0` 根因」**——使 GC 有非零資料可驅動退役提議（上輪只接決策側 run_gc，本輪接遙測側）。
- `tools/fsm_runtime/tests/test_rule_fire_telemetry_wiring.py` — 8 新測試（flag off 零退化 ×2 / flag on 命中記 on-watch fire + 選擇性 / fire_count 累積持久化 / 記帳失敗 fail-closed / 遙測零 set_maturity 呼叫〔R-9.20 #11〕/ stats 度量穩健+證書誠實揭露 / fire_ladder 降冪+retirement_eligible）。

### 紅線守界（B 軌）
- `record_state_fires` 只增 `fire_count` 計數、**永不自動退役 active 規則**；退役維持 🔴 人工 `rule_loader.set_maturity(reviewed_by=...)`（R-9.20 絕對禁令 #11 不弱化）＝rubric「L5 在環上守界」之守界；`rule_fire_telemetry_stats` 純讀不碰 meta-oracle。**誠實揭露**：`safety_certificate.catch_side_wired=False`——本輪只接 fire 側，catch 側語意未定義（**DEF-18-001**，routed），ROI 為單側信號。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.08 逐位元零差異 → 免五軌 TLC）。

---

## [v0.08] - 2026-06-16（Copy-on-Evolve 自 v0.07；v0.07 凍結唯讀）

### 新增（B 軌「鷹架代謝」L4→L5 信號 — GC 自動提議退役接入 FSM 主迴圈；AutoSDD_improving_17 W-17-1/W-17-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `scaffold_gc.run_gc()`（產 `RetirementProposal` proposed 退役提議，原測試-only / 手動）**接入主迴圈**：新增 `_SCAFFOLD_GC_AUTO_PROPOSE_ENV` 開關 + `_scaffold_gc_auto_propose_enabled()` + `scaffold_gc_stats()`（L5 可量測信號 + XAI 安全證書）；`enter_scaffold_gc()` 進態 SCAFFOLD_GC 後 flag-gated 自動跑 `run_gc` 算 ROI 落 `SCAFFOLD-ROI-{date}.md` + 填 `scaffold_gc_tracking`。**預設 OFF＝v0.07 行為（零退化）**；fail-closed：run_gc 任何失敗進態仍成功、不偽造報告。行使 arch_fitness FF-16 GAP-X2「代謝肌肉從未收縮」之 Rule 9.20.5。
- `tools/fsm_runtime/tests/test_scaffold_gc_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 run_gc+tracking / 報告真實落盤 / run_gc 失敗 fail-closed / GC 零 set_maturity 呼叫〔R-9.20 #11〕/ 非 RELEASE 源仍 raise / 零提議度量穩健 / roi_ladder 升冪+by_transition）。

### 紅線守界（B 軌）
- `run_gc` 只產退役提議、**永不自動退役 active 規則**；退役維持 🔴 人工 `rule_loader.set_maturity(reviewed_by=...)`（R-9.20 絕對禁令 #11 不弱化）＝rubric「L5 在環上守界」之守界；`scaffold_gc_stats` 純讀不碰 meta-oracle（GC 是 ROI 統計層非生成器）。**無 FSM 狀態/規則/`*.tla` 變更**（diff v0.07 逐位元零差異 → 免五軌 TLC）。

---

## [v0.07] - 2026-06-15（Copy-on-Evolve 自 v0.06；v0.06 凍結唯讀）

### 新增（B 軌「規則自演化」L4→L5 信號 — SLV 自動提議接入 FSM 主迴圈；AutoSDD_improving_16 W-16-1/W-16-2）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `slv_generator.propose_slv_from_fpl()`（`trust_level:proposed` 草案合成，原 proposal-only / 手動 CLI）**接入主迴圈**：新增 `_SLV_AUTO_PROPOSE_ENV` 開關 + `_slv_auto_propose_enabled()` + staticmethod `_auto_draft_slv(fpl_id)`（純合成 fail-closed）+ `learning_loop_stats()`（L5 可量測信號 + XAI 良基終止證書）；`exit_production_behavioral_signal()` 加 optional `fpl_id`，**learn 分支**轉態到 LEARNING_COMMIT 後 flag-gated 自動 draft proposed 草案 + 填 `learning_commit_tracking`。**預設 OFF＝v0.06 行為（零退化）**；附帶修 **DEF-16-001**（learn 採納鏈結構性斷裂）。
- `tools/fsm_runtime/tests/test_slv_auto_propose_wiring.py` — 9 新測試（flag off 零退化 ×2 / flag on 自走 draft+tracking / learn→人 verify→approve 鏈閉合 / 未 verify approve→raise〔R-9.11〕/ FPL 不存在 fail-closed / 合成失敗 fail-closed / 零事件度量穩健 / 計數+churn_max 一致）。

### 紅線守界（B 軌）
- 草案恆 `trust_level:proposed`（R-9.11，永不自動升 verified）；`trust_level→verified` 維持 🔴 人工（`exit_learning_commit` verified 強制檢查不動）＝rubric「L5 在環上守界」之守界；採納經 `meta_halt_monitor` ChurnBounded/GraduationRatchet（R-9.24 不弱化）；`learning_loop_stats` 純讀不碰 meta-oracle（R-9.37）。

### 不變
- **無 FSM 狀態/規則變更**：`LEARNING_COMMIT` 既有 state、`PRODUCTION_BEHAVIORAL_SIGNAL→LEARNING_COMMIT`（learn）既有邊，`transition_rules.py` + 全 5 `*.tla` 對 v0.06 **逐位元零差異**（diff 實測全 ZERO DIFF），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 不取新 ACT/rule。

### 驗證
- v0.07 `pytest -m "not chaos"` = 1517 passed / 4 skipped（v0.06 1508 + 9，只增不減）；新 wiring 9 passed；flag OFF 既有 37 相關 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.07 最新演化版」（FF-17 自證入閘）。

---

## [v0.06] - 2026-06-15（Copy-on-Evolve 自 v0.05；v0.05 凍結唯讀）

### 新增（B 軌「流程自治」L3→L4 升級 — auto_recovery 接入 FSM 主迴圈；AutoSDD_improving_15 W-15-1）
- `tools/fsm_runtime/fsm_runtime.py` — 把既有 `auto_recovery.py`（Rule 9.14 有界 1-shot 自癒，原 proposal-only / 需 orchestrator 手動觸發）**接入主迴圈**：新增 `_AUTO_RECOVERY_ENV` 開關常數 + `_auto_recovery_enabled()` + `_gate_is_resumable()` 預檢 + `auto_recovery_stats()`（L4 可量測信號）；`record_gate_result()` escalate 分支 **flag-gated 自動嘗試** `enter_auto_recovery`，把既有 `ESCALATION→AUTO_RECOVERY_ATTEMPT` 邊（TLA `T_EnterAutoRecover` 已模型化）由手動改自動觸發。**預設 OFF＝v0.05 行為（零退化）**；fail-closed（structural/bounds→ESCALATION_FINAL、例外停 ESCALATION）。
- `tools/fsm_runtime/tests/test_auto_recovery_wiring.py` — 9 新測試（flag off 零退化 / flag on 自走進 recovery / 完整閉環 success 回 gate / structural→FINAL / bounds→FINAL / fail→FINAL / resumable 預檢 / 空 session 零率）。

### 不變
- **無 FSM 狀態/規則變更**：`AUTO_RECOVERY_ATTEMPT` 為既有合法 state、`ESCALATION→AUTO_RECOVERY_ATTEMPT` 為既有合法邊，`_HAPPY_PATH` 與全部 `*.tla` 零改動（僅改 Python 觸發者、非狀態宇宙），Rule 9.18.1 不啟動、五軌 TLC 既有證明維持有效；ID_REGISTRY 維持 act=173 / rule="9.39"（接線既有能力，不取新 ACT/rule）。

### 驗證
- v0.06 `pytest -m "not chaos"` = 1508 passed / 4 skipped（v0.05 1499 + 9，只增不減）；flag OFF 既有 86 passed 零退化；雙軌 ci-gate exit 0「v0.01 凍結基線 + v0.06 最新演化版」（FF-17 自證 v0.06 自動入閘）。

### 共享 infra 同輪修（DEF-15-001，免 Copy-on-Evolve）
- `scripts/copy_on_evolve.sh` — 修 `tar --exclude build/reports` 誤殺 FSM 種子模板 `build/reports/fsm/FSM-STATE-TEMPLATE.yaml`（state_loader 必需真輸入）：排除後補回該模板；`scripts/tests/test_copy_on_evolve.py` 加回歸鎖 case。首次真實 v0.06 演化當場揭露（46+ FSM 測試全紅）。

---

## [v0.05] - 2026-06-15（Copy-on-Evolve 自 v0.04；v0.04 凍結唯讀）

### 新增（DEF-10-002b 回流 — Copy-on-Evolve 演化版必納官方閘門固化；AutoSDD_improving_11 W-11-2）
- `tools/arch_fitness/arch_fitness.py` — 新增 **FF-17「Copy-on-Evolve 演化版必納官方閘門」** 結構守門：把 improving_04 對 DEF-03-001 的雙軌**點修**固化為**結構不變量**。新增常數 `CI_GATE_PATH`、純函式 `_latest_version_dir()`、`check_ff17_evolution_version_gate_coverage()`（靜態讀 `scripts/ci-gate.sh`，斷言四錨點動態最新版偵測；退回靜態寫死＝`structural fail`），註冊進 `ALL_CHECKS`；docstring 16→17、exit-code 清單補 FF-17。與 FF-14 同源（靜態讀 CI 腳本、純讀、跨平台不執行 shell）。
- `tools/fsm_runtime/tests/test_arch_fitness.py` — 5 新測試（真 repo 涵蓋最新版 / 合成雙軌 PASS / 寫死單版 fail / 漏 append-latest fail / 腳本缺 INFO 略過）。
- **設計決策**：不另開 R-9.x 規則（會連鎖 FF-8/10/12 且屬自演化 meta-loop 異類關注點）；arch_fitness 本即治理層 fitness-function 套件，FF-17 即最小正確固化（Rule 2/3）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"（純 fitness-function 新增，不取新 ACT/rule）。

### 驗證
- v0.05 `pytest -m "not chaos"` = 1499 passed / 4 skipped（v0.04 1494 + 5，只增不減）；arch_fitness 87 passed；雙軌 ci-gate exit 0「v0.01:1478 v0.05:1499」——v0.05 作為最新演化版自動納入官方閘門，自證 FF-17 不變量。

---

## [v0.04] - 2026-06-14（Copy-on-Evolve 自 v0.03；v0.03 凍結唯讀）

### 修正（DEF-02-002 回流 — tlc_runner 計數標籤接反；AutoSDD_improving_03 W2）
- `tools/fsm_runtime/tlc_runner.py` — 抽出 module-level `parse_tlc_summary(out)`：以 **last-match**（`re.findall[-1]`）取最終 summary，取代舊 **first-match**（`re.search`）誤抓中途 progress 行；加 fail-closed 斷言 `generated >= distinct`（違反即 `raise RuntimeError`）。
- `tools/fsm_runtime/tests/test_tlc_runner_parsing.py` — 4 新測試（last-match / 正常不誤報 / 畸形 raise / 無匹配回 0；純字串、不需 Java）。

### 不變
- **無 FSM 狀態/規則變更**（`_HAPPY_PATH` 與 `*.tla` 零改動，Rule 9.18.1 不啟動）；ID_REGISTRY 維持 next_free act=173 / rule="9.39"。

### 形式化驗證
- 五軌 TLC 重跑驗證修正本身（last-match 取對 + generated ≥ distinct + 0 violation）；數據見 `EVOLUTION_LOG.md` v0.03→v0.04 段。

---

## [v0.03] - 2026-06-13（Copy-on-Evolve 自 v0.02；v0.02 凍結唯讀）

### 新增（Phase Z′ — AUTOCLAUDE_DELEGATED 觀察態落地，ACT-172；AutoSDD_improving_02 W1）
- `tools/fsm_runtime/transition_rules.py` — `_HAPPY_PATH` 新增 `AUTOCLAUDE_DELEGATED`（出邊 `{IMPLEMENTATION, ESCALATION}`）+ `OBSERVATION_STATES` 新增成員
- `tools/fsm_runtime/fsm_runtime.py` — 新增 `enter_autoclaude_delegated()` / `exit_autoclaude_delegated()`（forced-transition，比照 `enter_memory_consolidation`）
- `tools/fsm_runtime/formal/SDD_FSM.tla` — `ObservationStates` + 入/出邊 action（`T_EnterAutoclaudeDelegated` / `T_AutoDelegToImpl` / `T_AutoDelegToEsc`）+ `Next` + Fairness `SF_vars(T_AutoDelegToImpl)`（Rule 9.18.1 雙源同步）
- `workflow/sdd-fsm-engine/SDD_FSM_ENGINE.md` — 狀態轉換表新增 AUTOCLAUDE_DELEGATED 兩出口列
- `tools/fsm_runtime/tests/test_phase_z.py` — 8 新測試（enter/exit/邊界/不變量）
- `governance/ID_REGISTRY.yaml` — 登記 ACT-172、next_free 推進 act=173

### 形式化驗證
- **五軌 TLC 重跑全綠**（SDD_FSM/META_FSM/FLEET_FSM/COMPOSITION_FSM/OPTIMIZATION_FSM）：`_HAPPY_PATH` + `SDD_FSM.tla` 變更觸發 Rule 9.18.1 義務，TLC_DISTINCT/GENERATED/DEPTH 見 EVOLUTION_LOG。

---

## [v0.02] - 2026-06-12（Copy-on-Evolve 自 v0.01；v0.01 凍結唯讀）

### 新增（Phase Z — AutoClaude 執行引擎橋接，ACT-162~171）
- `workflow/sdd-autoclaude-bridge/SDD_AUTOCLAUDE_BRIDGE.md` — SDD 文件 → AutoClaude playbook 標準作業（compile-then-run 兩段式）
- `agent/specialized/sdd-playbook-compiler-zh.yaml` — SDD Playbook 編譯專家角色
- `governance/rules/R-9.38-playbook-translation-fidelity.yaml` — AT↔step 100% 雙向映射保真規則（違反→SPEC_AUDIT）
- 10 場景 SOP 各加「AutoClaude 自動化執行」小節（QuickRef 同步）
- `EVOLUTION_LOG.md` — 版本演化紀錄（含 TLC 證據與回退指引）

### 修正（AutoSDD_Defect_Log 分流項）
- DEF-01-001：`governance/RULES_INDEX.md` 計數過期（35→39 檔）+ next-act/next-rule 前緣同步
- DEF-01-002：`tools/fsm_runtime/formal/run_tlc.sh` 補「五軌請走 tlc_runner.py」legacy 註記
- DEF-01-003：補 `tools/__init__.py` 顯式 package 宣告

### 形式化驗證
- `_HAPPY_PATH` / `*.tla` 零修改 → 五軌 TLC 既有證明維持有效（N/A）；
  `AUTOCLAUDE_DELEGATED` 觀察態維持提案（落地前置條件見 SDD_AUTOCLAUDE_BRIDGE.md §5）

---

## [v0.01] - 2026-04-17

### 新增（SDD 轉型）

#### SDD 核心機制
- 整合 SDD Spec-First Gate（SCG-0~SCG-6）機制，建立 7 道規格品質閘門
- 新增 SDD Core Principles（`guides/system/sdd/SDD_Core_Principles.md`）— 三大支柱定義
- 新增 SDD Guide（`guides/system/sdd/SDD_GUIDE.md`）— SDD 快速指引

#### SDD Skills（6 個新增）
- `sdd-gate` — 執行 SCG 閘門驗證（所有情境通用）
- `sdd-review` — SCG-4 PR Review 輔助，驗證實作與規格一致性
- `spec-compliance-check` — SDD 文件格式與完整性驗證
- `rtm-generate` — 生成/更新需求追溯矩陣（RTM），確保 SCG-5 100% 覆蓋
- `contract-generate` — 生成 API Contract（OpenAPI 3.1）或 Consumer-Driven Contract
- `adr-generate` — 生成 Architecture Decision Record（ADR）

#### SDD 文檔模板（51+ 個）
- 新增 `docs_template/sdd/` 目錄，含 51+ 個 SDD 專屬文檔模板
- 涵蓋：需求（PRD/FRD/Invariant Spec）、架構（SRD/C4/ADR/As-Is/Trust Boundary）、測試（RTM/Contract Test Spec/Invariant Test Contract）、規劃（Gap Analysis/PBS/Refactor Plan）、品質（Tech Debt Spec/Code Quality Baseline）、安全（SAD/STRIDE/Compliance Matrix）、部署（Pipeline Spec/IaC Spec/Runbook）等

#### SDD CI/CD 規格（9 個）
- `cicd/SDD_CICD_BASE_LAYER.md` — 基礎層（全場景通用）
- `cicd/SDD_GREENFIELD_CICD.md` — Greenfield 場景
- `cicd/SDD_BROWNFIELD_CICD.md` — Brownfield 場景
- `cicd/SDD_REFACTORING_CICD.md` — Refactoring 場景
- `cicd/SDD_TESTING_CICD.md` — Testing 場景
- `cicd/SDD_PERFORMANCE_CICD.md` — Performance 場景
- `cicd/SDD_SECURITY_CICD.md` — Security 場景
- `cicd/SDD_MIGRATION_CICD.md` — Migration 場景
- `cicd/SDD_INTEGRATION_CICD.md` — Integration 場景

#### SDD 場景增強文件（10 個）
- 新增各情境 `SDD_{SCENARIO}_ENHANCEMENT.md`，定義 SDD Spec-First 流程補強
- 涵蓋全部 10 大情境：greenfield / brownfield / refactoring / documentation / devops / integration / migration / performance / security / testing

#### 文檔目錄結構（SDD 8 層）
- `docs/01_requirements/` — PRD / FRD / Invariant Spec / Third-Party API Research
- `docs/02_architecture/` — SRD / C4 / ADR / As-Is / Trust Boundary Map
- `docs/02_architecture/adr/` — ADR-{NNN} 架構決策記錄
- `docs/02_architecture/api/` — OpenAPI 3.1 Contract / Consumer Contract
- `docs/03_testing/` — RTM / Test Plan / Test Strategy / Defect Classification
- `docs/03_testing/contracts/` — Invariant Test Contract / Contract Test Spec / Chaos Contract
- `docs/04_planning/` — Gap Analysis / Refactor Plan
- `docs/04_planning/performance/` — Performance Baseline Spec（PBS）
- `docs/05_development/` — Living Doc Strategy
- `docs/06_quality/` — Code Quality Baseline / Tech Debt Spec
- `docs/06_quality/security/` — SAD / STRIDE / Compliance Matrix / Asset Inventory
- `docs/07_design/` — UI/UX / Database Design
- `docs/08_deployment/` — CI/CD Pipeline Spec / Monitoring Alert Spec / Release Notes / Runbook / Cutover Plan
- `docs/08_deployment/iac/` — IaC Specifications

---

### 修改（v0.09 → v0.01 升級）

#### Agents（21 個全部更新）
- 21 個 Agents 版本更新至 v0.01（7 core + 14 specialized）
- 核心 Agents 新增 SDD 技能：
  - `sa-analyst`：逆向規格工程（As-Is SRD）、Gap Analysis、Business Invariants 提取（INV-XXX）
  - `sd-architect`：As-Is C4 Model、ADR Archaeology、Before/After 架構對比、Migration Contract Map
  - `qa-tester`：As-Is 測試規格基線、Invariant Test Contract、Consumer Contract 測試
  - `dev-developer`：Strangler Fig 模式、Branch by Abstraction、Contract-First 開發
  - `code-analyzer`：Tech Debt 規格化（TD-XXX）、Code Quality Baseline Spec
  - `technical-writer`：Living Documentation 策略、ADR 維護、API 文件從 Contract 生成

#### Workflows（23 個全部更新）
- 所有 23 個 Workflows 整合 SCG 閘門驗證點
- 新增 SDD Spec-First Gate Workflow（`workflow/sdd-spec-first-gate/`）
- 核心 8 個 Workflow + 13 個場景特定 Workflow + 1 個 ADR Workflow

#### 場景 SOP（10 個全部更新）
- 所有 10 個場景 SOP 反映 SDD Spec-First 流程
- 每個場景新增強制 SCG 閘門步驟說明
- Brownfield / Refactoring / Migration 場景新增逆向規格工程步驟

#### 工具與腳本
- `tools/init_project.sh` 新增 `--sdd` 模式（v3.3-SDD），自動建立 SDD 8 層 docs/ 目錄結構

#### 指南文件更新
- `guides/user/onboarding/QUICK_START_GUIDE.md` — 新增 SDD 三大支柱說明與 SCG 閘門引導
- `guides/user/onboarding/SCENARIO_DECISION_TREE.md` — 各情境新增對應 SCG 閘門說明
- `guides/user/standards/PROJECT_DOCUMENTATION_STANDARDS.md` — 目錄結構更新為 SDD 8 層，FILE_DIRECTORY_RULES.md 引用
- `agent/AGENT_COLLABORATION_PATTERNS.md` — 新增「SDD SCG 閘門協作模式」章節
- `agent/AGENT_PHASE2_UPDATE_GUIDE.md` — 更新為 v0.09 → v0.01 升級指南
- `scenarios/SCENARIO_TRANSITION_GUIDE.md` — 新增「場景切換前的 SCG 驗證」強制章節
- `scenarios/SCENARIO_AGENT_MAPPING.md` — 新增各情境 SCG 對照說明與特殊情境說明

---

### 歸檔

- AISDLC v0.09 保留於 `AISDLC_v0.09/` 目錄（僅供參考，不修改）
- v0.09 版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`

---

## [v0.09] - 2026-04-14（歸檔）

> 此版本為 AISDLC 開發專注版（Development-Focused Edition），版本歷史已歸檔至 `build/planning/archive/SDD_VERSION_HISTORY.md`。
>
> v0.09 定義了 10 大情境、21 個 Agents、23 個 Workflows 的基礎框架，v0.01 在此基礎上加入 SDD Spec-First Gate 機制完成框架轉型。

### 主要特性（v0.09 歸檔記錄）
- 10 大開發情境（含 migration）
- 21 個 Agents（7 core + 14 specialized）
- 23 個 Workflows
- 雙層 guides 架構（system + user）
- 中文優先 Agents（-zh.yaml）
- 開發專注版 docs/ 目錄結構（8 個目錄）
