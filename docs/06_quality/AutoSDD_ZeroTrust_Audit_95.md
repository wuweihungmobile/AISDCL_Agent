# AutoSDD_improving_95 — Zero-Trust 審查報告（A 軌：PRD→playbook 橋接端到端真跑）

> 日期 2026-06-29｜柱 A 軌｜審查對象＝improving_95 三 W 項 + 端到端真跑證據 + 缺陷帳本誠實性。
> 三鏡（Architect / SA-SD / QA）主樹派發（本輪新檔皆 untracked，依 DEF-24-001 禁 worktree）。

## 1. 階段一基線（Zero-Trust Re-Audit 實測，Explore agent）

| 項目 | 實測 | 通過 |
|------|------|------|
| AutoClaude pytest | 3593 passed / 0 failed / 122 skipped（75.93s） | ✅（= improving_94 floor） |
| lint-imports | 8 kept / 0 broken | ✅ |
| LOC budget | violations=0（19895/20438） | ✅ |
| snapshot | OK | ✅ |
| claude CLI（真跑前置） | 2.1.144 認證 OK | ✅ |

硬閘：無 failed、不低於上輪 → 准進階段二。

## 2. 階段四零退化矩陣（結案實測）

| 檢查 | 實測 | 判定 |
|------|------|------|
| AutoClaude 全套 | **3600 passed / 0 failed / 122 skipped**（78.08s，+7 harness 測） | ✅ |
| lint-imports | 8 kept / 0 broken | ✅ |
| LOC 分級 | violations=0（19895/20438） | ✅ |
| snapshot | OK | ✅ |
| AISDLC_SDD ci-gate | **N/A 第一種**（git 證零碰 `AISDLC_SDD/`、無 Copy-on-Evolve） | ✅ |
| DAL 等價 | **N/A 第二種**（`tests/equivalence/` 隨全套通過、零 DAL/checkpoint 改動） | ✅ |
| 五軌 TLC | **N/A 第一種**（git 證零碰 `*.tla`/FSM） | ✅ |

git diff 範圍：只 `AutoClaude/tools/run_bridge_e2e.py`、`AutoClaude/scripts/bridge_e2e/`、`AutoClaude/tests/tools/test_run_bridge_e2e.py`、`docs/` 新檔；零碰 `autoclaude/` 生產碼與 `AISDLC_SDD/` 框架本體。

## 3. 端到端真跑證據（W-95-3，核心成果）

| 後端 | 步成功 | pass_rate | kernel_success | escalated | peak token% |
|------|--------|-----------|----------------|-----------|-------------|
| **sdk** | **5/5** | **1.0** | **True** | False | 3.0 |
| pty | 0/5 | 0.0 | False | True | 0.0 |

- **北極星第 3 點首證**：PRD→Archy 真跑→compiler→AutoClaude 真跑整鏈在 sdk 後端跑通，5 步（1 規格 + 4 TDD）全過、evaluator pytest 閉環真綠。
- **非空殼鐵證**：parent 獨立複跑 Claude 真建的 `strutils.py`+`test_strutils.py`＝**13 passed**。
- 證據檔：`docs/03_testing/AutoSDD_improving_95_bridge_e2e_evidence.json`（sdk）/ `..._evidence_pty.json`（pty 對照）。

## 4. 本輪缺陷（zero-trust 自揪）

- **DEF-95-001（P2，harness 解析 bug，fixed@improving_95）**：per-step `✓` regex 誤匹配 log 等級標籤 `[INFO]` → sdk 真跑誤報 4/5；比對 kernel 權威 `completed_step_ids` 揪出 → gap 改 `[^\[\n]*?` + 改用 completed_step_ids（fallback ✓）+ 回歸鎖測。
- **DEF-95-002（P3，pty 後端真實摩擦，routed improving_96）**：pty `--output-format json` 對寫檔步驟擷取不可靠 → keyword 未擷到致 escalated（Claude 實際已正確寫 SPEC.md）→ 建議 Archy doc 步改 artifact-existence evaluator（v0.29）。

## 5. 三鏡 Zero-Trust 複審

### 5.1 Architect 鏡 — **OVERALL PASS（P0=0/P1=0）**
- 架構純潔：`run_bridge_e2e.py` 三純函式（compile_plan/parse_e2e_log/build_evidence）+ 真跑副作用（run_autoclaude subprocess）切開；對引擎唯一耦合為唯讀 `import Playbook` + 複用同層 compiler，無業務邏輯滲入 core。
- 落點：`check_loc_budget.SCAN_ROOT="autoclaude"`，tools/ 不掃描；import-linter 199 檔 8 kept/0 broken 不觸發。
- 安全：evaluator 唯一生成關仍 `sanitize_evaluator`（三層 fail-closed），harness 未繞過；subprocess 走 list 形式無 `shell=True`、無 eval/exec/os.system，無注入面。
- additive：對 Checkpoint/DAL grep 零命中，完全 additive。零碰生產碼/框架本體/`*.tla`（git status 證）。

### 5.2 SA-SD 鏡 — **OVERALL PASS（P0=0/P1=0；1 P3 已 moot）**
- 6 構件實存；evidence JSON 與 §4.3 表逐欄一致（sdk 5/5/1.0/True/False/3.0；pty 0/5/True）。
- 缺陷帳本誠實：DEF-95-001 三項修復（gap 不跨 `[` + 用權威 completed_ids + `[INFO]` 回歸測）經原始碼+測試碼坐實；DEF-95-002 與 pty evidence note 一致；無漏記/虛報。
- RTM-95-1~6 皆有對應證據；N/A 第一/二種標註有 git 鐵證。
- **F-95-A1（P3）**：審查當時 `AutoSDD_ZeroTrust_Audit_95.md` 尚未生成（前向引用）→ **本檔即是、現已落地，moot**。

### 5.3 QA 鏡（對抗）— **OVERALL PASS（P0=0/P1=0）**
- 7 單測 passed；**對抗驗證回歸鎖非恆真**：把 `_RE_STEP_OK` gap 改回弱版 `[^\n]*?` → `test_parse_e2e_log_*` 確實轉紅（`ok_steps` 出現 `{'INFO':1}`、E-SPEC-1 被吃掉），證回歸鎖真能擋 bug 回潮；Edit 還原乾淨（git diff 空）。
- RTM-95-5 真驗 fail-closed（`&&` 注入被 CompileError 拒、合法 pytest 放行，非無腦全拒）。
- 真跑非空殼：sdk workdir Claude 真建 strutils.py+test，parent 複跑 13 passed；sdk log `completed_step_ids` 五步齊全與 evidence 一致。
- 誠實性：pty 0/5 誠實標 DEF-95-002（Claude 已寫 SPEC.md 4151 bytes）、sdk 5/5 經 harness bug 修正後與 kernel 權威一致，無「失敗講成成功」。

### 5.4 綜合判定 — **全三鏡 OVERALL PASS，P0=0 / P1=0**
- parent 對鏡子結論複核（紀律 #17 雙向 zero-trust）：①QA 突變還原後 parent 親驗 `_RE_STEP_OK` 確為 `[^\[\n]*?`、harness 7 passed、檔完整 untracked（QA 還原乾淨、無殘留）；②SA-SD 之 F-95-A1（Audit_95.md 缺）已由本檔落地解決；③三鏡並行於主樹（untracked 新檔禁 worktree，DEF-24-001）無假陰性，QA 瞬時突變未與 Architect/SA-SD 讀檔互踩（SA-SD 讀到的 regex 為修後態）。
- 結論：**准予結案**。本輪零退化（3600/0/122）、三軌紅線守住、兩缺陷（DEF-95-001 fixed / DEF-95-002 routed_96）誠實入帳。
