# AutoSDD_improving_77 — A 軌：pty-vs-sdk A/B 載具 real-run 模式 fail-loud 修復（DEF-77-001）+ 輕量真跑取真實非-token 指標

> **本輪柱位**：**A 軌（整合 / 載具加固）**。下一份＝`AutoSDD_improving_78.md`。
> **定位**：A 軌 A/B 載具 real-run 路徑缺陷修復 + 首次成功落地「輕量真跑」（本機 `claude` CLI 即後端，零外部憑證）。**零 `autoclaude/` 生產碼、零 `AISDLC_SDD/` 觸碰**——純 `AutoClaude/tools/` 載具 + 測試。免 Copy-on-Evolve、免五軌 TLC。
> **成熟度**：`L_合體 = min(A=L5, B=L5, C=L5) = L5` 維持（載具量測加固，非成熟度推進）。
> **掌舵者拍板（2026-06-26）**：候選 (a) 真跑——選「輕量真跑（本機/local LLM）」。階段一實證本機 `claude` CLI 即為 pty/sdk 載具的真實後端（兩 A/B config 皆 `enable_kernel_brain: false`，Minimax dummy key 永不被呼叫），真跑可行、無需外部 LLM。

---

## §1 本輪輸入（自 improving_76 繼承）

1. **上輪（improving_76）已完成 W 項**：W-76-1 逐步驟（per-step）指標歸因、W-76-2 載具納入 TOKEN_HALT 解析（DEF-76-001 載具側）、W-76-3 有界渲染（`format_step_comparison` max_steps 截斷）。載具 38 passed。commit 249f10a 已 push origin/main。
2. **上輪遞延 / routed**：
   - **DEF-76-001（P2，partially-fixed 載具側 + production marker routed improving_77）**：production Kernel 唯一正式路徑**不發 TOKEN_COMPACT**，致 peak/compact 在真跑恆 0；載具側已補認 TOKEN_HALT，但 **production 端 Kernel observability marker 補強需動 `autoclaude/` 生產碼**，原 routed 本輪。
   - improving_76 §8 遞延候選：**(a) 真跑**（真 token 跑長 playbook 取逐步驟差異）／per-step 多輪聚合／(b) SD_09 W1 source-sha 閘門（~06-29）／(c) W-67-2 producer 端 spec-format-version（需 v0.27）。
3. **缺陷帳本 open / routed**：DEF-01-007（cc-switch GUI 環境工具缺裝 P3 open）／DEF-01-009（sdd_governance_plugin LOC watch P3 open watch）／DEF-62-001（auto_recovery 註解滯後 P3 open）／DEF-17-001・DEF-42-001・DEF-35-001（P2 routed C 軌 SD_09 W1）／DEF-76-001（P2 partially-fixed + routed）。本輪處置見 §6。

> **🔴 本輪 scope 對齊掌舵者選擇的誠實切分**：掌舵者選「輕量真跑」。階段一啟動真跑時**意外揪出 DEF-77-001**（real-run 模式相對路徑 + fail-loud 違反）——這是「真跑」這個動作直接挖出的載具層真缺陷，**屬本輪 A 軌載具加固範圍、零生產碼**，優先於 DEF-76-001 的 production marker（後者仍需生產碼、本輪不做、維持 routed）。本輪因此**不**推進 DEF-76-001 production 端，而是先讓「真跑載具本身可信、不再靜默吞錯」——這是真跑能產出可信指標的前置。

---

## §2 階段一實測（Zero-Trust Re-Audit，2026-06-26，parent 親跑）

| 項目 | 命令 | 實測結果 | 證據 |
|------|------|---------|------|
| AutoClaude 全套 pytest（硬閘基線） | `python -m pytest tests/ -q` | **3402 passed / 122 skipped / 0 failed**（69.89s） | parent 親跑 bg task bgm5p8mbs；= improving_76 結案值，零退化 |
| 上輪構件存在性 | 開檔核對 | improving_76 載具碼（per-step / TOKEN_HALT / 有界渲染）+ 38 測試存在無虛報 | `tools/ab_compare_backends.py`、`tests/tools/test_ab_compare_backends.py` |
| 真跑可行性（本輪重點） | `claude -p "回覆兩個字：可以"` | **headless 可用 exit 0、真回應** | `/c/Users/wuwei/.local/bin/claude`；本機 claude CLI 即 pty/sdk 載具後端 |
| 端到端真跑（絕對路徑） | `ab_compare_backends.py --run <abs> --workdir <tmp> --n 1` | **pty/sdk 皆 100% 一次通過、2/2 步驟、run 成功 True**；token 峰值 0%/compact 0（DEF-76-001 實證） | log 證載具真起 `claude -p`（wexpect 模式）、真建檔、`pytest smoke_add_test.py` 評估通過 exit=0 |
| **DEF-77-001 揪出**（相對路徑真跑） | `ab_compare_backends.py --run scripts/sdd_bridge_smoke.yaml --workdir <tmp> --n 1` | **pty/sdk 皆 0/0 步驟、run 成功 False、全 0 指標、exit=0**；workdir 子目錄全空 | 見 §3 根因 |

> **lint-imports / ci-gate / 五軌 TLC**：本輪零碰 `autoclaude/` 生產碼與 `AISDLC_SDD/`，故 lint-imports/LOC/snapshot 於階段四回填（預期持平 8 kept / 0 / FRESH）；**AISDLC_SDD ci-gate 與五軌 TLC＝N/A（git diff 鐵證零碰觸發路徑，階段四附）**。

---

## §3 本輪增量設計（W-77-1 / W-77-2）

### DEF-77-001 根因（real-run 模式靜默 0/0 + fail-loud 違反）

`tools/ab_compare_backends.py` real-run 模式以子目錄為 cwd 起 autoclaude subprocess：

```python
# run_backend (L343-356)
def run_backend(playbook, backend, workdir, config_path=None):
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "autoclaude", playbook, "--fresh"]   # ← playbook 原樣（可能相對）
    if config_path: cmd += ["--config", config_path]
    subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True, timeout=900)  # ← returncode/stderr 丟棄
    log_file = workdir / "logs" / "autoclaude.log"
    log_text = log_file.read_text(...) if log_file.exists() else ""   # ← log 不存在 → 空字串 → 解析成全 0
    return log_text, parse_run_metrics(log_text, backend=backend)
```

**兩個缺陷**：
1. **路徑未 resolve**：`playbook`（`args.run`）以**相對路徑**傳入，但 subprocess `cwd=workdir`（子目錄）→ autoclaude 在子目錄找不到 playbook → 啟動即失敗、未建 log。N=1 分支連 `args.pty_config`/`args.sdk_config` 也未 resolve（`main():405-406` 原樣傳；只有 N>1 的 `run_backend_n:367` resolve config，但**兩條路徑皆未 resolve playbook**）。
2. **fail-loud 違反**：`subprocess.run(...)` 的 returncode/stderr 被整個丟棄；log 不存在時回空字串 → `parse_run_metrics("")` → 全 0 → `format_comparison` 印出「成功的平淡 A/B」+ `main` 回 **exit 0**。使用者拿到**假的全 0 報告**而不知真跑根本沒跑（典型「completed 是錯的若有東西被靜默跳過」，違反工程紀律第 12 條 Fail Loud）。

### `<Architecture_Design_Review>`

1. **架構純潔性**：本輪只動 `tools/` 載具（非 `autoclaude/` 微核心），不創 God-object、不碰 Thin Facade、不碰 ports/plugins/EventBus。新增邏輯抽為**純 helper** 以利離網單測。
2. **持久化相容**：零碰 PlaybookCheckpoint / DAL 三後端，N/A。
3. **安全防護網**：零新增 CONDITIONAL 指令生成路徑；subprocess cmd 為固定 argv（無 shell），不引入注入面。
4. **對外 I/O 安全**：零新增 `ToolInvocationPort` 外呼路徑；真跑起的是本機 `claude` CLI（既有 PtyExecutor / SdkExecutor 路徑），非新外呼。N/A。

### W-77-1：修 DEF-77-001（real-run 路徑 resolve + fail-loud）

| 修點 | 介面 delta | 設計 |
|------|-----------|------|
| 路徑 resolve | 新純 helper `_resolve_invocation_path(p: str \| None) -> str \| None`（相對 → 對「原始 cwd」絕對；None 透傳） | `main()` 解析 args 後（cwd 仍為使用者 cwd）即 resolve `args.run` + 兩 config，再下傳。`run_backend_n` 既有 config resolve 改走同 helper（去重）。 |
| fail-loud | 新純 helper `_load_log_or_raise(log_file: Path, backend: str, returncode: int, stderr: str) -> str` | `run_backend` 捕獲 `result = subprocess.run(...)`；log **不存在** → `raise RuntimeError`（含 backend / returncode / stderr 尾段），不再回空字串假裝 0/0。log 存在 → 正常讀（含 escalated 輪亦有 log，照常解析）。 |

- **語意保證**：log **存在**時行為與舊版**完全一致**（escalated/halted 真跑照常解析，不誤 raise）；只在「autoclaude 連 log 都沒產生＝啟動即失敗」這個唯一新路徑 fail loud。
- **LOC 落點**：`tools/ab_compare_backends.py` 預估 +約 20 行（兩 helper + 接線）；tools/ 非 LOC 分級強制標的，但仍維持精簡。

### W-77-2：用修好的載具實跑輕量真跑、取真實非-token 指標

- 修復後重跑 N=1（絕對路徑、smoke playbook），確認真跑成功且**相對路徑亦能正確 resolve 成功**（不再 0/0）。
- 取真實非-token 指標：一次通過率 / CORRECTION 次數 / SDD_CONTRACT_VIOLATION 次數 / 完成步驟 / run 成功・escalated・halted。
- **🔴 誠實邊界**：token 峰值 / compact 維度因 **DEF-76-001（production Kernel 不發 TOKEN_COMPACT）** 在真跑恆 0，**非真值**——報告明確標「token 維度待 DEF-76-001 production marker 補強（routed，需生產碼）後方可信」，**不虛報** 0 為實測差異。smoke playbook 過短本就不觸發 token 壓力，雙重原因下 token 差異本輪不可得。

### RTM 需求列（階段三/四回填實測欄）

| RTM-ID | 需求 | 驗證 | 階段 |
|--------|------|------|------|
| RTM-77-1 | real-run 相對路徑 playbook 不再靜默 0/0 | 單測 `_resolve_invocation_path` 相對→絕對；真跑相對路徑成功 2/2 | 三 |
| RTM-77-2 | autoclaude 啟動即失敗（無 log）時 fail loud | 單測 `_load_log_or_raise` 缺 log + rc≠0 → raise；log 存在 → 正常回 | 三 |
| RTM-77-3 | 修復不破壞既有 log-存在解析語意（含 escalated） | 既有 38 測全綠 + 真跑 escalated/halted log 照常解析（受控突變實證） | 三/四 |
| RTM-77-4 | 輕量真跑取得真實非-token 指標、token 維度誠實標記 | 真跑輸出 + §4.2 誠實標記 | 四 |

---

## §4 實作與雙重驗證

### §4.1 實作（2026-06-26 完成）

- **W-77-1 兩 helper 落地**（`tools/ab_compare_backends.py`）：
  - `_resolve_invocation_path(path)`（`:344-355`）：相對 → 對呼叫端 cwd 絕對；None 透傳；冪等。
  - `_load_log_or_raise(log_file, backend, returncode, stderr)`（`:358-371`）：log 不存在 → `raise RuntimeError`（含 backend/returncode/stderr 尾）；存在 → 照常讀（語意不變）。
  - 接線：`run_backend`（`:374-389`）捕獲 `proc` 並改走 `_load_log_or_raise`；`main`（`:441-446`）解析 args 後即 resolve playbook + 兩 config；`run_backend_n`（`:367-368`）改走 `_resolve_invocation_path` 並補 resolve playbook（防直呼）。
- **新增 5 離網單測**（`tests/tools/test_ab_compare_backends.py`）：`test_resolve_invocation_path_relative_becomes_absolute` / `_none_passes_through` / `_absolute_is_idempotent` / `test_load_log_missing_raises_fail_loud` / `test_load_log_existing_returns_content_unchanged`。**載具 38 → 43 passed**（0.17s）。

### §4.2 真跑與受控突變結果（2026-06-26 parent 親跑）

- **修復後真跑（相對路徑 = DEF-77-001 原始觸發向量）**：pty/sdk 皆 **一次通過率 100% / CORRECTION 0 / SDD_CONTRACT_VIOLATION 0 / 完成步驟 2/2 / run 成功 True（未 escalate、未 halt）**。與修復前同一相對路徑呼叫的 0/0/False 對比，**DEF-77-001 確認修復**。
  - **🔴 token 維度誠實標**：token 峰值 0% / compact 0 — **非真值**，係 DEF-76-001（production Kernel 不發 TOKEN_COMPACT）+ smoke playbook 過短不觸發 token 壓力**雙因**所致，**不充當 pty/sdk token 差異實測**。
  - **非-token 結論**：此 smoke 載具上 pty 與 sdk 後端**等價**（皆零修正、零違反、一次過）。
- **fail-loud 端到端實證**：`--run scripts/__NOPE_does_not_exist__.yaml` → `RuntimeError: [pty] real-run 未產生引擎 log…（returncode=1）…stderr 尾段：❌ 找不到 Playbook 檔案`、process **exit=1**（舊版會回 0/0 + exit 0）。
- **受控突變（序列化單線、Edit 還原禁 git checkout）**：
  - **MUT-77-1**〔`_resolve_invocation_path` 末行 `return str(Path(path).resolve())` → `return path`〕→ `test_resolve_invocation_path_relative_becomes_absolute` 轉紅（`is_absolute()==False`），Edit 還原復綠。
  - **MUT-77-2**〔`_load_log_or_raise` 的 `raise` → `return ""`（退化回 DEF-77-001 原貌）〕→ `test_load_log_missing_raises_fail_loud` 轉紅（`DID NOT RAISE`），Edit 還原復綠。
  - 還原後 `grep MUT-77` 無殘留、載具 43 passed 復綠。

---

## §5 零退化驗證矩陣（RTM / SCG-5，階段四回填實測）

| 檢查 | 命令 | 通過條件（floor = improving_76 實測 3402） | 實測 |
|------|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ 3402 passed / 0 failed（新測只增不減） | **3407 passed / 122 skipped / 0 failed**（= 3402 + 5 新；見 §4.4） |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** ✓ |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（absolute=0 tier=0 special=0）✓ |
| Snapshot | `python tools/snapshot_sync.py --check` | 新鮮 | **OK — 對齊一致** ✓ |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **N/A — 本輪零碰 AISDLC_SDD/**（git diff 鐵證） | **N/A**：`git status --short` 僅 `AutoClaude/tools/ab_compare_backends.py` + 其測試 + 本輪 docs/，無 `AISDLC_SDD/` 任一檔 |
| DAL 等價 | equivalence job | 隨全套通過、本輪無新 round-trip 契約（非 N/A 空白：引測試數/路徑） | 隨全套通過、零碰 DAL/checkpoint，無新 round-trip 契約（`tests/equivalence/`） |
| 五軌 TLC | `bash scripts/ci-gate.sh --full-tlc` | **N/A — 零碰 `*.tla`/FSM**（git diff 鐵證） | **N/A**：git status 無 `*.tla`/FSM 變更 |

### §4.4 全套 pytest 實測（階段四，parent 親跑回填）

`python -m pytest tests/ -q` → **3407 passed / 122 skipped / 0 failed**（70.20s，bg task bd9onzdhv，exit 0）。= improving_76 floor 3402 + 5 新載具測試，零退化、零 failed。

---

## §6 缺陷帳本本輪處置（詳見 AutoSDD_Defect_Log.md）

- **新增 DEF-77-001（P2，real-run 靜默 0/0 + fail-loud 違反）** → 本輪 W-77-1 即修，狀態 fixed@improving_77。
- **DEF-76-001（P2）**：本輪**不**推進 production marker（需生產碼）；維持 **partially-fixed 載具側 + routed**。但本輪真跑**再次實證** token 峰值/compact 恆 0，補強其證據鏈。下輪候選續列。
- open/routed 其餘缺陷（DEF-01-007 / DEF-01-009 / DEF-62-001 / DEF-17-001 / DEF-42-001 / DEF-35-001）：本輪只動 `tools/ab_compare_backends.py` + 測試，未觸碰標的，複驗維持原狀態。

---

## §7 多專家 Zero-Trust 審查（2026-06-26 完成）

三鏡皆**主樹派發**（本輪有 untracked 新檔 improving_77.md + 主樹就地改的載具/測試，依 DEF-24-001 禁 worktree；MUT 突變已序列化於實作後單線完成並 Edit 還原，無並行就地突變）：

- **Architect** — OVERALL PASS（P0=0/P1=0）：架構純潔（tools/ only、零生產碼、無 God-object）、修復設計正確（resolve 時機 + fail-loud 切點 + 冪等）、N/A 有鐵證。
- **SA-SD** — OVERALL PASS（P0=0/P1=0/P2=0；無 overclaim）：根因正確（grep 佐證 production blind）、無殘留漏洞、測試驗證意圖（Rule 9）、文件誠實（token 0% 標非真值、DEF-76-001 續 routed、無 phantom fix）。
- **QA** — OVERALL PASS（無退化/虛報）：獨立重跑 43 載具測 + 8 kept/0 broken + violations=0 + snapshot OK + 收集數 3529=3407+122 + MUT 無殘留 + 帳本誠實。

**2 條 P3 觀察**（同一語意：`_resolve_invocation_path("")` 轉 cwd 絕對 vs `None` 透傳之不對稱）**by-design 不修**（argparse 無空字串觸發向量 + 空路徑下游觸發 fail-loud；補特例＝dead defensive code 違反 Rule 2）——詳見 AutoSDD_ZeroTrust_Audit_77.md §4。

全閉環 PASS，准結案。

---

## §8 誠實標記

- **規格先行**：本檔 §1-§3（含 `<Architecture_Design_Review>` / 介面 delta / RTM 需求列）於**階段二先落地**，§4.2 真跑/突變與 §5 實測欄階段三/四回填——非事後結案報告。
- **token 維度誠實**：本輪真跑 token 峰值/compact 恆 0 為 **DEF-76-001 production blind + smoke 過短**雙重原因，**非真值**，不充當 pty/sdk token 差異實測。
- **DEF-77-001 來源誠實**：此缺陷是掌舵者選的「輕量真跑」動作直接揪出，非預先規劃；本輪如實記為「真跑使能過程意外發現並就地清償的載具缺陷」。
- **N/A 精確**：AISDLC_SDD ci-gate / 五軌 TLC ＝「條件未觸發、本輪確實未跑」附 git diff 鐵證；DAL 等價＝「隨全套已跑通過、無新契約」引測試數，非空白 N/A。
