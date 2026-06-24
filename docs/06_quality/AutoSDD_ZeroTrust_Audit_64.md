# AutoSDD_ZeroTrust_Audit_64 — improving_64 審計 + 複審證據

> **輪次**：improving_64（C 軌 perf 取證載具去環境依賴化）｜**日期**：2026-06-25
> **零退化基線（floor）**：improving_63 §2 實測 AutoClaude pytest **3315 passed**｜**結案**：OVERALL PASS

---

## §1 階段一基線實測（全錨定本回合 tool 輸出）

| 項目 | 命令 | 實測輸出 |
|------|------|---------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | `3315 passed, 122 skipped in 126.06s`（初測）|
| (b) lint-imports | `PYTHONUTF8=1 lint-imports` | `Contracts: 8 kept, 0 broken.` |
| (c) LOC | `python tools/check_loc_budget.py` | `total=18999 baseline=17032 cap=20438 violations=0` |
| (c) snapshot | `python tools/snapshot_sync.py --check` | `OK — Snapshot 區段 + sprint 骨架對齊一致` |
| (c) git | `git status --short` | （初測乾淨）|
| (d) AISDLC_SDD | `bash scripts/ci-gate.sh` | `exit 0`；逐軌計數 `AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.25:1656 scripts/tests:129` |

**硬閘**：3315 ≥ floor 3315、0 failed → 通過，准進後續階段。

## §2 零信任雙向複核（推翻 Explore 線索）

Explore 盤點稱「C 軌 SD_09 有 X/Y/Z 可寫 delta」。主 agent 親查證實**已完成**（zero-trust 雙向，對 subagent 結論複核——同 Nightly 紀律 #17）：

- **Z1**：`grep -rnE "^[[:space:]]*continue-on-error:" .github/workflows/` → 真正 active 僅 3 處（`ci.yml:138`、`pg-e2e-on-label.yml:21,64`），全為刻意保留延後項；`ci.yml` 12 行 `# ...continue-on-error` 皆「2026-05-20 B-09 已移除」註解。
- **X1**：`ls tools/seed_kb.py tests/fixtures/pgvector_real_queries.json` → 皆存在（13.7KB / 2.9MB）。
- **Y1**：`ls docs/04_planning/ADR/ | grep sd09` → ADR-SD09-001~010 齊全（含 006）。
- **觀察期**（forensic 引 raw store）：nightly 06-24 END 行 `mutation=25/7 ac4=25/14 obs=25/30 drift=23/30`；`.ac4_history.jsonl` 末筆 p95=50.97ms；`.drift_log_history.jsonl` 末筆 count=0。→ #3/obs 未滿 30 天，**W1 本輪不能啟**。

## §3 根因取證（DEF-64-001 — perf 單調爬升）

| 證據 | 命令/輸出 |
|------|----------|
| 軌跡單調爬升 | `.perf_history.jsonl` decide_correction p95：1604→2602→2848→3086→3145→3218→3711→3701ms |
| cProfile（100 呼叫）| `build_file_state_snapshot` cumtime **2.954s**；`_winapi.CreateProcess` ncalls=**100**；`thread.lock.acquire` tottime 2.552s |
| 呼叫點 | `prompt_builder.py:135` `subprocess.run(["git","diff","--name-only","HEAD"], cwd=working_dir)`；`prompt_builder.py:223` `build_file_state_snapshot()` |
| stub 對照 | 含 snapshot p95=**2943ms** / stub 後 p95=**9.8ms**（p50 1.6ms）→ **git I/O 占 99.7%** |
| 單次 git diff | AutoClaude cwd `git diff --name-only HEAD` = **29.4ms**（×100≈2900ms 吻合）|

**根因判定**：B-07（2026-05-20）改「100 次真實呼叫」時無意納入 git 子行程；單一 monorepo + Copy-on-Evolve 凍結版累積使 git diff 逐輪變慢 → 基線非確定性、假退化、對邏輯退化失明（邏輯僅 0.3%）。**非 decide_correction 邏輯退化**（improving_57~63 零接觸 AutoClaude，git log 證）。

## §4 修復驗證（雙重）

| 檢查 | 命令 | 結案輸出 |
|------|------|---------|
| 單測（修後）| `pytest tests/perf/test_decide_correction.py -m perf` | `1 passed in 0.32s`（原 58.5s）|
| perf 全套 | `pytest tests/perf/ -m perf -q` | `3 passed, 1 skipped in 0.65s` |
| **perf 閘門** | `perf_regression_check.py perf_results.json .perf_baseline.toml` | `[PASS] decide_correction: 2602.1ms → 2.1ms` / `green=3 warn=0 block=0` / `EXIT=0` |
| 確定性 | 5 輪重量純邏輯 | p95 = `2.2, 2.0, 1.9, 1.9, 2.0` ms（max 2.17）|
| **零退化全套** | `python -m pytest tests/ -q` | `3315 passed, 122 skipped in 68.05s`（0 failed）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | `8 kept, 0 broken` |
| LOC | `check_loc_budget.py` | `violations=0` |
| surgical | `git status --short` | 僅 `AutoClaude/tests/perf/test_decide_correction.py` + `docs/06_quality/AutoSDD_Defect_Log.md` |

## §5 多專家 Zero-Trust 審查閉環

> **派發隔離判準**：本輪變更為**未 commit 的 tracked 檔就地修改**（`test_decide_correction.py`）+ 新增 root docs。依 DEF-24-001 判準「審查 untracked/未 commit 改動 → 主樹派發」（worktree 由 HEAD 建樹看不到未 commit 改動會假陰性），審查 agent 一律**主樹派發**，**禁 `isolation: worktree`**。

（審查結論見 §6；複審證據逐項回填。）

## §6 審查結論（三鏡親跑複核，主樹派發、禁 worktree）

### §6.1 Architect + SA-SD 雙鏡 — **5/5 PASS**
獨立親讀/親跑回報：
1. **根因屬實**：`prompt_builder.py:135` 確 spawn `git diff`，呼叫鏈 `decide_correction → build_correction_message(:223) → build_file_state_snapshot → git diff 子行程` 成立、無快取。
2. **獨立重現 stub 對照**：自寫 probe 量得 含 snapshot p95=3154ms / stub p95=5.6ms → **git I/O 占 99.8%**（與宣稱 99.7% 同量級）；單次 git diff（AutoClaude cwd 掃全 monorepo）median≈30.4ms×100≈3044ms 精準對應。
3. **surgical/純潔**：`git diff autoclaude/` 為空（零 production 變更）、僅測試檔 +25 行 + 帳本 1 行；patch 點與既有 `_call_with_retry` stub 同精神。
4. **Rule-9 守衛有效**：500ms 門檻位於純邏輯 5.6ms（~90x 下方餘裕）與 git 版 3154ms（~6x 上方分離）之間，git I/O 潛回即 fail loud。
5. **production 未改動合理**：correction 非熱路徑、timeout=10 有上限、使用者專案多為小 repo；真要優化另立 RFC。

### §6.2 QA 鏡 — **5/5 PASS / OVERALL PASS**
親跑真實輸出：
1. 零退化全套 `pytest tests/ -q` → **3315 passed / 122 skipped / 0 failed**（81.54s）＝floor。
2. perf 閘門 → `[PASS] decide_correction 2602.1→2.3ms`、**green=3 warn=0 block=0 / EXIT=0**。
3. `lint-imports` → **8 kept / 0 broken**（195 files / 489 deps）。
4. 確定性重跑 ×3 → 皆 PASS、**0.36/0.35/0.35s**（原含 git I/O ~58s）。
5. 缺陷帳本誠實性 → DEF-64-001 P2/根因/修法/nuance/狀態齊全；釐清「2.1/2.3/2.69ms」為執行抖動帶、「99.7%（stub 占比）vs 99.9%（對 toml 下修）」為不同指標，**無虛報/漏記/數字對不上**；`.perf_baseline.toml` 仍 2602.147（SSOT 未手改，符合 auto-relock 宣稱）。

### §6.3 衍生檔潔淨度（兩鏡共同提醒，已處置）
審查跑 perf 套件會使載具寫回 `.perf_baseline.toml`/`.drift_log_history.jsonl`（auto-generated 衍生檔），`perf_results.json` 已 gitignored。已還原；結案 `git status` 僅本輪 4 預期檔（`tests/perf/test_decide_correction.py` M + `AutoSDD_Defect_Log.md` M + `improving_64.md`/`ZeroTrust_Audit_64.md` 新增），無衍生檔污染。

**OVERALL：PASS**（三鏡全 PASS、零退化 3315/0、perf block=0、根因獨立重現、缺陷帳本誠實、工作樹潔淨）。
