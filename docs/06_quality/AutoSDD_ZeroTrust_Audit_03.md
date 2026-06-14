# AutoSDD Zero-Trust Audit 03 — 第三輪迭代審計與複審證據

> **日期**：2026-06-14
> **審計原則**：完全不信任文件宣稱（含 CLAUDE.md），一切以實際程式碼與實際執行結果為準。
> **範圍**：improving_03 W1（DEF-01-008 main.py brain flag-gated 注入，A 軌）/ W2（DEF-02-002 tlc_runner 計數修正 → Copy-on-Evolve v0.04，B 軌）/ 零退化矩陣 / Copy-on-Evolve 紅線 / 缺陷帳本誠實性。

---

## 1. 階段一 Zero-Trust 重偵察實測（2026-06-14，權威證據）

| 項 | 命令 | 實測結果 |
|----|------|---------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3060 passed / 122 skipped / 0 failed**（96.58s） |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken** |
| (c) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh`（AISDLC_SDD 根） | **全數通過**（exit 0；arch_fitness advisory warn 不阻擋） |
| — | `check_loc_budget` / `snapshot_sync --check` | violations=0（total 17508）/ 新鮮 |
| (d) 缺陷重現 | 開檔/實測 | DEF-01-008 ✓重現（main.py:97 無 brain=）、DEF-02-002 ✓重現（tlc_runner.py:73 re.search first-match）、DEF-01-009 ✓重現（plugin 250 行） |
| (e) 結構發現 | 開檔 | `ci-gate.sh:17` 寫死 `FW_DIR=v0.01` → 官方閘門只測 v0.01（記 **DEF-03-001**） |

**硬閘**：基線 0 failed 且 3060 = 上輪 floor → 通過，准進階段二。**本輪零退化 floor 錨定 = 3060**。

---

## 2. W1 執行紀錄 — DEF-01-008 main.py brain flag-gated 注入（A 軌）

### 2.1 影響評估（zero-trust 開檔實證）

`build_kernel(brain=...)` 把同一 brain **雙重**下發（`wiring.py:307→202` SddGovernancePlugin + `wiring.py:315` PlaybookKernel）。盲注入會：① 啟動 `kernel.py:198` correction 區塊（brain=None 時整段跳過）→ 改變 production 每步修正行為；② `kernel.py:216` `c is None → ESCALATE` 新增「Minimax API 故障」escalation 路徑。故修死碼與改 production 語意在現有 wiring **綁定**，必須以 flag 解耦。

### 2.2 落地決策與交付

採 **flag-gated**（使用者凍結方案 A 之「證明非退化才注入，否則 flag-gated」分支）：

| 步 | 交付 | 驗證（實跑） |
|----|------|------------|
| W1-a | `config.py` `MinimaxConfig.enable_kernel_brain: bool = False`（additive） | `py_compile` OK；`MinimaxConfig().enable_kernel_brain is False` 實證 |
| W1-b | `main.py` flag-gated `MinimaxBrainAdapter(minimax) if cfg.minimax.enable_kernel_brain else None` + import | `py_compile` OK |
| W1-c | `tests/integration/test_def_01_008_brain_injection.py` 9 case | **9 passed**（0.52s） |
| W1-d | 全套 pytest + lint | **3069 passed / 122 skipped / 0 failed**（98.01s）+ **8 kept / 0 broken** |

### 2.3 測試覆蓋意圖（Rule 9）

9 case 鎖定三契約：① **預設零退化**（flag 預設 False；brain=None → kernel._brain 與 sdd_governance._brain 皆 None＝現況）；② **flag-on 雙效耦合**（同一 brain 抵達 kernel + governance）；③ **死碼轉活 + 新語意**（correction 可達 / API 故障 ESCALATE / governance escalation 達 threshold 諮詢 / brain=None 不諮詢不崩潰）。每 case 檔頭 WHY。

---

## 3. W2 執行紀錄 — DEF-02-002 tlc_runner 計數修正（Copy-on-Evolve v0.04）

| 步 | 交付 | 驗證（實跑） |
|----|------|------------|
| W2-a | `robocopy v0.03 → v0.04`（v0.01/v0.02/v0.03 凍結） | **6115 == 6115 檔**；git：v0.01/v0.02/v0.03 改動=0 |
| W2-b | `tlc_runner.py` 抽 `parse_tlc_summary(out)`：`re.findall[-1]` last-match 取代 `re.search` first-match + fail-closed 斷言 `generated >= distinct` | `py_compile` OK |
| W2-c | `tools/fsm_runtime/tests/test_tlc_runner_parsing.py` 4 case | **4 passed**（0.13s） |
| W2-d | 五軌 TLC（驗證修正後 generated ≥ distinct + 0 violation） | 見 §3.1 |
| W2-e | EVOLUTION_LOG v0.03→v0.04 + CHANGELOG [v0.04] | 已寫入 |
| — | v0.04 not-chaos pytest | **1494 passed / 4 skipped**（40.80s；v0.03 1490 + 4 新解析測試） |

### 3.1 五軌 TLC 證據（2026-06-14 實跑，v0.04 目錄，exit 0 / No error found）

| Module | DISTINCT | GENERATED | DEPTH | generated≥distinct | 結果 |
|--------|----------|-----------|-------|--------------------|------|
| SDD_FSM | 855 | **4706** | 14 | ✅（舊 first-match 誤報 706）| ✅ No error found |
| META_FSM | 13 | 24 | 6 | ✅ | ✅ |
| FLEET_FSM | 7 | 8 | 7 | ✅ | ✅ |
| COMPOSITION_FSM | 21 | 28 | 7 | ✅ | ✅ |
| OPTIMIZATION_FSM | 12 | 21 | 5 | ✅ | ✅ |

> **DEF-02-002 修復實證**：修正後 `parse_tlc_summary` 取最終 summary，五軌 `generated >= distinct` 恆成立（舊 first-match 曾報 SDD_FSM distinct=855 > generated=706 的錯配已消除）。本輪 W2 **不觸發 Rule 9.18.1**（`_HAPPY_PATH`/`.tla` 零改動），五軌 TLC 為修正正確性之 real-output 加證、非形式化義務。

---

## 4. 階段四零退化矩陣收斂（2026-06-14 實測）

| 檢查 | 命令 | 結果 |
|------|------|------|
| AutoClaude 全套 | `pytest tests/ -q` | **3069 passed / 122 skipped / 0 failed**（98.01s；≥ floor 3060，+9 新 W1 測試，零退化） |
| 架構契約 | `lint-imports` | **8 kept / 0 broken** |
| LOC 分級 | `check_loc_budget` | violations=0（total 17511 ≤ cap 20438） |
| Snapshot | `snapshot_sync --check` | OK |
| AISDLC_SDD 閘門（v0.01 凍結） | `ci-gate.sh` | 全數通過（exit 0） |
| v0.04 not-chaos | `cd v0.04 && pytest -m "not chaos"` | **1494 passed / 4 skipped** |
| **五軌 TLC** | `tlc_runner --module ×5` | **五軌 0 violation**（SDD_FSM 4706/855/14、META 24/13/6、FLEET 8/7/7、COMP 28/21/7、OPT 21/12/5）；generated≥distinct 恆成立（DEF-02-002 修復實證） |

**Copy-on-Evolve 紅線**：v0.01/v0.02/v0.03 改動=0（git 確認）；所有改動落 v0.04（新）/ AutoClaude `main.py`+`config.py`+測試（W1）/ `docs/`（計畫+審計+缺陷帳本）。

---

## 5. 缺陷帳本本輪異動

| 缺陷 | 異動 |
|------|------|
| DEF-01-008（P1） | routed → **fixed@improving_03**（§2 flag-gated 落地，9 case 鎖定，3069/0 零退化） |
| DEF-02-002（P3） | routed → **fixed@v0.04**（§3 last-match + 斷言，4 case，五軌 TLC 加證） |
| **DEF-03-001（新，P2）** | B 軌 dogfooding 發現：`ci-gate.sh:17` 寫死 v0.01 → 官方閘門/CI/pre-push 不覆蓋演化版 v0.02+（與 DEF-02-001 同根）→ open（routed 候選下輪，RFC v0.0Y `FW_DIR` 參數化） |
| DEF-01-007 / 009 / DEF-02-001 | 本輪未涉，維持 open/watch（計畫 §7 載明 disposition） |

---

## 6. 多專家 Zero-Trust 審查閉環

> 主 agent 同時戴 Architect / SA-SD / QA 三頂帽子，唯讀 + 親自重跑命令 + 開檔複驗（本輪無 mutation/突變，無需 worktree 隔離；對齊 Audit_02 §6 體例）。

### 6.1 親自重跑實測（逐項，獨立確認）

| # | 命令 | 重跑實測 | 判定 |
|---|------|----------|------|
| 1 | AutoClaude `pytest tests/ -q`（**獨立第二次**） | **3069 passed / 122 skipped / 0 failed**（97.35s） | PASS（零退化 floor 3060 守住，逐項重現、零灌水）|
| 2 | `lint-imports`（**獨立第二次**） | **8 kept / 0 broken** | PASS |
| 3 | `check_loc_budget` | violations=0（total 17511） | PASS |
| 4 | `snapshot_sync --check` | OK | PASS |
| 5 | v0.04 `pytest -m "not chaos"` | 1494 passed / 4 skipped（含 test_tlc_runner_parsing 4） | PASS |
| 6 | 五軌 TLC（v0.04） | 五軌 0 violation；SDD_FSM generated=4706≥distinct=855 | PASS（DEF-02-002 修復實證，逐欄）|
| 7 | git status v0.01/v0.02/v0.03 | 0 / 0 / 0 | PASS（凍結本體零汙染）|
| 8 | W1 測試檔 | 9 passed | PASS |

### 6.2 開檔複驗（W1 雙效耦合 + W2 解析 + 凍結）

- **W1 PASS**：`config.py` enable_kernel_brain 預設 False；`main.py` flag-gated 構造 + 傳 `brain=`；`build_kernel` 簽名未改（早已收 brain=）；`sdd_governance_plugin.py`/`kernel.py`/`wiring.py` git diff = 0（守 D9 250 行紅線）。
- **W2 PASS**：v0.04 `tlc_runner.py:parse_tlc_summary` 用 `re.findall[-1]` + 斷言；`run_tlc` 改呼叫；4 case 測試含畸形 raise（不變量守護）。
- **凍結 PASS**：v0.01/v0.02/v0.03 git 改動=0；v0.04 為 6115 檔完整複製後施作。
- **誠實性 PASS**：DEF-03-001 為本輪誠實新發現（非掩蓋）；DEF-01-008 採 flag-gated 而非謊稱「已全注入」；DEF-02-002 五軌為 real-output 加證、非形式化義務（誠實標註）。

### 6.3 三頂帽子結論 + 總判定

| 帽子 | 結論 |
|------|------|
| Architect（架構紅線） | **PASS** — W1 純 entry-point + 1 config flag；`build_kernel` 簽名未改、`kernel.py`/`wiring.py`/`sdd_governance_plugin.py` git diff=0（守 D9 250 行紅線）；無 God-object；Thin Facade `playbook_runner.py` 未碰；lint 8/0 + LOC 0。W2 純框架工具重構落 v0.04 |
| SA-SD（RTM·同步保真） | **PASS** — improving_03 §5 RTM 九項皆有落點+驗證；EVOLUTION_LOG/CHANGELOG v0.04 段齊全；Copy-on-Evolve v0.01/v0.02/v0.03 git 零汙染；ID_REGISTRY 維持（純工具 bugfix 不取新 ACT，正確）|
| QA（零退化·TLC·誠實性） | **PASS** — 3060→3069/0 floor 守住（獨立第二跑吻合零灌水）；五軌 TLC 0 violation + SDD_FSM 4706/855 generated≥distinct（DEF-02-002 修復鐵證）；缺陷帳本三條異動誠實（DEF-01-008 flag-gated 非謊稱全注入 / DEF-02-002 五軌為 real-output 加證非義務 / DEF-03-001 誠實新發現）|

**總判定：✅ PASS**（無任何 P0/P1 紅旗）。零 P0/P1 → **全能修復輪無材料項**。

---

## 7. 本輪最終結論

W1（DEF-01-008 main.py brain flag-gated 注入，A 軌）+ W2（DEF-02-002 tlc_runner 計數修正 → Copy-on-Evolve v0.04，B 軌）全數交付，經「主 agent 三頂帽子 Zero-Trust 審查（獨立重跑 + 開檔複驗）→ 零 P0/P1 → 總判定 PASS」閉環收斂：

- **零退化**：3069 passed / 0 failed（≥ floor 3060，+9 新 W1 測試；獨立第二跑吻合）；lint 8 kept；LOC 0；v0.04 1494 passed。
- **形式化**：五軌 TLC 0 violation；SDD_FSM GENERATED 706（舊誤報）→ **4706**（真值），generated≥distinct 恆成立——DEF-02-002 修復於曾出 bug 的同一軌得到鐵證。
- **flag-gated 零退化保證**：`enable_kernel_brain` 預設 False，production 維持 brain=None 位元相同行為；死碼轉為 flag-gated 可選能力（9 case 鎖定 off/on 雙態 + 雙效耦合 + 新語意）。
- **Copy-on-Evolve**：v0.01/v0.02/v0.03 凍結本體 git 改動=0；改動落 v0.04（6115 檔完整複製）/ AutoClaude（W1）/ docs（四件套）。
- **缺陷帳本**：DEF-01-008 fixed@improving_03、DEF-02-002 fixed@v0.04、DEF-03-001 誠實新入帳（P2，routed 候選下輪）。

**本輪准予結案。** 建議後續 commit + tag（如 v2026.06.14-03）。

