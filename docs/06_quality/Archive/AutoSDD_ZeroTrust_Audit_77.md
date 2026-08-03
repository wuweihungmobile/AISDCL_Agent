# AutoSDD_ZeroTrust_Audit_77 — improving_77 多專家 zero-trust 審查 + 複審證據

> **本輪**：A 軌載具加固——修 DEF-77-001（`AutoClaude/tools/ab_compare_backends.py` real-run 模式相對路徑靜默 0/0 + fail-loud 違反）+ 輕量真跑取真實非-token 指標。零 `autoclaude/` 生產碼、零 `AISDLC_SDD/` 觸碰。
> **結論**：三鏡（Architect / SA-SD / QA）**全 OVERALL PASS，P0=0 / P1=0**。

---

## §1 階段一零信任重偵察（parent 親跑，2026-06-26）

| 項目 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 pytest（硬閘基線） | `python -m pytest tests/ -q` | **3402 passed / 122 skipped / 0 failed**（69.89s，bg bgm5p8mbs） |
| 真跑可行性 | `claude -p "回覆兩個字：可以"` | headless exit 0、真回應；本機 `claude` CLI 即 pty/sdk 載具後端 |
| 端到端真跑（絕對路徑） | `ab_compare_backends.py --run <abs> --workdir <tmp> --n 1` | pty/sdk 皆 100% 一次通過、2/2、run 成功 True；log 證真起 `claude -p`、真建檔、pytest 評估 exit=0 |
| **DEF-77-001 揪出**（相對路徑） | `--run scripts/sdd_bridge_smoke.yaml ...` | pty/sdk 皆 0/0、run 成功 False、全 0、exit=0、workdir 子目錄全空 |

硬閘 PASS（基線無退化、無 failed）→ 准進階段二。

---

## §2 缺陷與修復（DEF-77-001）

**根因**（`tools/ab_compare_backends.py`，修復前）：
1. real-run 以子目錄為 subprocess cwd（`run_backend`），但 playbook（`args.run`）以相對路徑傳入未 resolve；N=1 分支連 config 亦未 resolve（只 N>1 `run_backend_n` resolve config，兩路徑皆未 resolve playbook）→ autoclaude 子目錄找不到 playbook → 啟動即失敗未建 log。
2. `subprocess.run(...)` returncode/stderr 丟棄；log 不存在回空字串 → `parse_run_metrics("")` 全 0 → `format_comparison` 印「成功的平淡 A/B」+ `main` 回 exit 0（**fail-loud 違反，工程紀律第 12 條**）。

**修復**（W-77-1）：`_resolve_invocation_path`（main 解析 args 後即把 playbook+config 轉絕對）+ `_load_log_or_raise`（log 不存在即 raise RuntimeError 含 backend/returncode/stderr 尾，不再靜默回空字串）。

**修復驗證**（parent 親跑）：
- 同一**相對路徑**呼叫 → pty/sdk 皆 100% 一次通過、2/2、run 成功 True（修復前 0/0/False）。
- fail-loud 端到端：指向不存在 playbook → `RuntimeError: [pty] real-run 未產生引擎 log…（returncode=1）…stderr 尾段：❌ 找不到 Playbook 檔案`、exit=1。
- 受控突變：MUT-77-1（resolve 退化 `return path`）→ resolve 測轉紅；MUT-77-2（raise 退化 `return ""`）→ fail-loud 測轉紅；Edit 還原（禁 git checkout）復綠、grep MUT-77 無殘留。

---

## §3 三鏡 zero-trust 審查結論（皆主樹派發——本輪有 untracked 新檔，依 DEF-24-001 禁 worktree）

### Architect 鏡 — OVERALL PASS（P0=0 / P1=0）
- 架構純潔性 PASS：改動全在 `tools/` 載具層、未碰 `autoclaude/` 生產碼；兩 helper 為小純函式、無 God-object。
- 零生產碼鐵證 PASS：`git status --short` 恰 4 檔（載具 + 測試 + Defect_Log + improving_77.md），無 `autoclaude/`、無 `AISDLC_SDD/`。
- 修復設計正確性 PASS：resolve 時機（main 在 subprocess 啟動前、cwd 仍使用者 cwd）正確；fail-loud 只在「log 不存在＝啟動即失敗」raise，escalated/halted 輪有 log 不誤 raise；resolve 冪等。
- §3/§5 N/A 標註 PASS：ci-gate / 五軌 TLC N/A 有 git diff 鐵證。
- **P3 觀察**：`_resolve_invocation_path` 對 `args.run` resolve 之語意契約已在 docstring 明示（real-run playbook/config 本應相對使用者 cwd），設計正確。

### SA-SD 鏡 — OVERALL PASS（P0=0 / P1=0 / P2=0；P3×1；無 overclaim）
- 根因分析正確 PASS：DEF-77-001 兩缺陷描述與程式碼一致無誇大；獨立 grep 佐證 `autoclaude/` 全域 `TOKEN_COMPACT` 僅棄用 `_impl.py:233`、`TOKEN_HALT` log marker 僅 `_token_halt.py:46`、`main.py:123` 載「Kernel 為唯一正式路徑」→ production blind 屬實。
- 修復無殘留漏洞 PASS：real-run 兩路徑 playbook+config 皆經 resolve、`--pty-log/--sdk-log` 解析模式不經 subprocess cwd 切換無此問題；fail-loud 切點正確分離「啟動失敗」vs「業務失敗」。
- 測試驗證意圖（Rule 9）PASS：5 新測非空殼、斷言能在退化時轉紅；MUT-77-1/2 突變點↔斷言精確對應。
- 文件誠實性 PASS：token 0% 誠實標「非真值」、DEF-76-001 誠實標「本輪未做續 routed」、無 phantom fix。
- **P3 觀察**：`_resolve_invocation_path("")` 與 `None` 行為不對稱（空字串轉 cwd、None 透傳），無實際觸發向量，可不修。

### QA 鏡 — OVERALL PASS（無退化 / 無虛報）
- 載具測試獨立重跑：**43 passed**（38→43）。
- 架構契約/LOC/snapshot 獨立重跑：**8 kept / 0 broken、violations=0、snapshot OK**。
- MUT 證據：`grep MUT-77` 無殘留；直讀兩生產函式核對 MUT-77-1/2 轉紅宣稱合理（含 Rule 9 意圖）。
- 全套 pytest 收集數核對：`--co -q` → **3529 collected** = 3407 passed + 122 skipped（§4.4 數字吻合）。
- 缺陷帳本誠實性：DEF-77-001 fixed@improving_77、DEF-76-001 續 routed improving_78，無漏記虛報。

---

## §4 P3 觀察處置（by-design 不修，justified）

兩鏡共同記的 P3（`_resolve_invocation_path("")` 轉 cwd 絕對、`None` 透傳之不對稱）**by-design 不修**，理由：argparse 對未給定的 `--run/--*-config` 回 `None`（無 default），**絕無傳入空字串的觸發向量**；即便傳入空 playbook 路徑，下游 autoclaude 啟動失敗會觸發本輪新增的 fail-loud（不再靜默）。補一個針對不可達輸入的 `""` 特例分支將新增 dead defensive code，違反 Rule 2 簡潔原則。屬 [[no-defer-unless-justified]] 的「不做有優點」類，明說不修而非延後。

---

## §5 零退化驗證矩陣（階段四實測）

| 檢查 | 實測 |
|------|------|
| AutoClaude 全套 pytest | **3407 passed / 122 skipped / 0 failed**（70.20s，bg bd9onzdhv，exit 0）= 3402 floor + 5 新 |
| 架構契約 lint-imports | **8 kept / 0 broken** |
| LOC 分級 | **violations=0**（absolute=0 tier=0 special=0） |
| Snapshot | **OK — 對齊一致** |
| 載具測試 | **43 passed**（38 + 5 新） |
| AISDLC_SDD ci-gate | **N/A**（git status 零 `AISDLC_SDD/` 檔，鐵證） |
| 五軌 TLC | **N/A**（零碰 `*.tla`/FSM，鐵證） |
| DAL 等價 | 隨全套通過、零碰 DAL/checkpoint、無新 round-trip 契約 |

---

## §6 結論

三鏡全 **OVERALL PASS、P0=0 / P1=0**；2 條 P3 觀察（同一語意不對稱）by-design 不修並說明。零退化（3402→3407）、零生產碼、零框架觸碰。DEF-77-001 fixed@improving_77；DEF-76-001 production marker 續 routed improving_78。本輪結案四件套齊備。
