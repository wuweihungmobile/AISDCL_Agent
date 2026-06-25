# AutoSDD improving_72 — 多專家 Zero-Trust 審查報告

> **對應計畫**：[AutoSDD_improving_72.md](../04_planning/AutoSDD_improving_72.md)（A 軌：pty-vs-sdk 完整統計 A/B + 真跑、揪修 DEF-72-001）。
> **日期**：2026-06-26 ｜ **派發**：三鏡（Architect / SA-SD / QA）**主樹並行**——本輪含 untracked 新檔（2 config + 計畫/審計文件）→ 依 **DEF-24-001** 主樹派發、**禁 worktree**（worktree 不攜帶 untracked 檔會回報假陰性）；突變已全數還原、無並行突變鏡。
> **結論**：**三鏡全 OVERALL PASS、P0=0、P1=0**。

---

## 1. 主 agent 親跑收斂矩陣（zero-trust 基準）

| 檢查 | 命令 | 實測 |
|------|------|------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | **3374 passed / 122 skipped / 0 failed** |
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 8 kept / 0 broken |
| LOC 分級 | `python tools/check_loc_budget.py` | violations=0（total 19391 / cap 20438） |
| Snapshot | `python tools/snapshot_sync.py --check` | FRESH |
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0（v0.01:1478 / v0.26:1665 / scripts:129） |
| 真跑 A/B（N=3，真 token） | `run_backend_n` × pty/sdk | 兩後端 3/3 success、100%/0/0/0（§計畫 §4.2） |

---

## 2. 三鏡獨立審查結論

### 2.1 Architect 鏡 — OVERALL PASS（P0=0 / P1=0）

- **架構純潔性**：`git diff --stat` 證改動侷限於 `tools/ab_compare_backends.py` / `pty_wrapper.py` / 2 測試檔 / `scripts/ab_configs/` / docs；`playbook_runner.py` **零改**（Thin Facade 未碰）；無 God-object（`AggregateMetrics` 純 dataclass、`aggregate_runs`/`format_aggregate_comparison` 純函式、`run_backend_n` 僅編排複用 `run_backend`）。
- **DEF-72-001 修復**：確認 `_start_wexpect` 改 `wexpect.spawn(command, args=list(args), encoding=...)`；逐行比對判定為**參數傳遞訂正、非執行語意改寫**（控制流分支、`_raw_logger` 掛載、subprocess argv 路徑皆未變），風險低。
- **import-linter** 8 kept / 0 broken；**LOC** violations=0。
- **安全面**：`run_backend(_n)` 固定 argv list、無 `shell=True`；`bypassPermissions` 限 A/B 臨時工作目錄、無新外呼路徑；arg list 不經 shell parsing → **降低**注入面（移除反引號/分號被 shell 解析的非預期路徑）。
- **零退化親跑複核**：3374/122/0、lint 8 kept、LOC 0、snapshot FRESH，與宣稱一致。

### 2.2 SA-SD 鏡 — OVERALL PASS（P0=0 / P1=0）

- **DEF-72-001 根因親跑探針重現（核心）**：以 wexpect spawn 印 `sys.argv` 的 python，傳含反引號+換行+分號的 prompt——
  - `" ".join` 路徑：prompt 被 shell 切碎 → 子程序 `SyntaxError`、**prompt 完全未抵達**；
  - `args=list` 路徑：prompt 原樣完整抵達（`['hello \`echo INJECTED\`\nsecond line; rm -rf nothing']`）。
  根因宣稱成立、修法正確。
- **聚合驗算**：`aggregate_runs([1.0, 0.5])` → mean 0.75 / 母體 stdev 0.25 / min 0.5 / max 1.0 全命中；空 list → n=0 不崩。
- **回歸測有效性**：18 passed；**親自突變**還原 join 版確認回歸測 FAIL（非假綠），再還原乾淨。
- **config 公平性**：兩後端 dummy key 非空、`enable_kernel_brain=false`、權限旁路各自正確（pty extra_args / sdk permission_mode）、`goal_synthesis_enabled=false` 對稱；唯一非對稱的旁路注入位置係「各後端 API 形態使然」、執行效果相同、對四指標無系統性偏頗。
- **config 移子目錄**：`test_yaml_import.py` 112 passed；確認該測非遞迴 glob `scripts/*.yaml`、子目錄避開為正解。

### 2.3 QA 鏡 — OVERALL PASS（P0=0 / P1=0）

- **零退化全套親跑**：`3374 passed / 122 skipped / 0 failed`（215.94s）≥ floor 3367。
- **新測非空殼**：6 個 `test_aggregate_*`/`test_format_aggregate_*` + 1 個 `test_wexpect_spawn_passes_args_as_list_not_shell_joined`，斷言實質（mean/stdev/min-max/計數/spawn 形態），非 `assert True`。
- **誠實性**：`git diff` 無 `@pytest.mark.skip`/`xfail`/`pytest.skip`/註解規避、floor 無偷改、`aggregate_runs` 用真 `statistics` 非 stub；「修復前 pty 0%/sdk 100% 巨大差異」**有誠實揭露**（教訓②、DEF-72-001 條目）、「smoke 短→四指標收斂」邊界亦誠實標註。
- **DEF-72-001 帳本誠實**：已入帳、P1 標註合理（預設後端對真實 prompt 默默失效、workaround=sdk），非虛報 P0 亦非低報。
- **runtime 副作用**：`git status` 待提交清單乾淨，未見 `.drift_log_history.jsonl`/`.perf_baseline.toml`/`.mutmut-cache` 混入。

---

## 3. 非阻斷觀察（不擋本輪結案）

| # | 來源鏡 | 觀察 | 處置 |
|---|--------|------|------|
| O-1 | Architect | 計畫書原寫 pty_wrapper「179 行」，實測 **177** | **已修**（計畫書 §3.2/§5 校正為 177） |
| O-2 | SA-SD | 探針用 `python -c` 放大破壞、非真 claude；「真 claude 收完整 prompt 行為正常」屬活體驗證 | 已由 W-72-3 真跑 N=3（pty 修後 3/3 真建檔）覆蓋——非缺陷 |
| O-3 | SA-SD | `git diff` 報 pty_wrapper.py CRLF→LF（與紀律 #8 同精神） | 行尾轉換不影響功能；commit 前確認，非缺陷 |
| O-4 | Architect | 計畫書 §7 連結之本審計文件原不存在 | **已修**（本文件即落地，連結不再懸空） |
| O-5 | Architect/QA | smoke 過短 → token 峰值皆 0%、四指標收斂相同 | 已誠實標註為遞延候選（更長 playbook 分出差異），非虛報 |

---

## 4. 結案判定

三鏡 zero-trust 全 **OVERALL PASS、P0=0、P1=0**；非阻斷觀察 O-1/O-4 已當場修、其餘為誠實邊界或活體覆蓋。本輪四件套（improving_72 / 本審計 / Defect_Log〔DEF-72-001 + recap〕/ scripts+程式產出）達結案條件。`L_合體=L5` 維持（非成熟度推進，A 軌執行器後端 A/B 驗收 + 揪修潛伏 P1）。
