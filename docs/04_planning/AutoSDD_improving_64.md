# AutoSDD_improving_64 — C 軌指揮官自精進：perf 載具去環境依賴化（decide_correction 基線確定性修復）

> **軌道**：① 整合迭代｜**本輪柱位**：**C 軌（指揮官 AutoClaude 自身能力 / SD_09 觀察期工程）**｜**下一份**：`AutoSDD_improving_65.md`
> **日期**：2026-06-25｜**驅動器**：`AutoSDD_Iteration_Prompt_Template.md`｜**成熟度量表 SSOT**：`AutoSDD_Maturity_Rubric.md`
> **本輪定位**：C 軌 **perf 取證載具修復**（非升級）——維持 `L_合體=L5`。修復 `decide_correction` perf baseline 的環境依賴缺陷（DEF-64-001）：基線量到的 99.7% 是 `git diff` 子行程 I/O 而非邏輯，隨 monorepo 成長假退化、且對真正邏輯退化失明。
> **框架版本**：n/a（純 AutoClaude C 軌；零 AISDLC_SDD 凍結本體變更，無 Copy-on-Evolve）。
> **🔴 人工 signoff 軌跡**：本輪方向經掌舵者 4 次 AskUserQuestion 逐步定錨——①「先做階段一全偵察再決定」→②（偵察後）「查觀察期→達標則走 W1 launch」→③（觀察期未成熟、撞見 perf 信號）「查 perf 單調爬升根因」→ 修載具。

---

## §1 上輪繼承（improving_63 結案 + 缺陷帳本）

- **improving_63**（B 軌 L5 加固：scaffold_gc 自動提議退役翻預設 ON）已 commit（`2bc6f43`），RTM R-63-1~9 全 ✅；Copy-on-Evolve v0.25。**B 軸 opt-in→default-ON 翻環家族至此收齊**（AUTO_RECOVERY/SLV/fire/catch/scaffold_gc 五支全翻）——improving_63 §8 明載「下輪 B 軌須另尋實質 delta（或 C 軌 SD_09）」。
- **缺陷帳本 open/routed 項**（本輪處置）：DEF-01-007（cc-switch GUI，本輪不涉多後端）、DEF-01-009（sdd_governance LOC watch，本輪零擴充該檔）、DEF-19-001/23-005/30-001/32-002/35-001/62-001（皆非本輪 scope，維持 routed/open）。本輪新增 **DEF-64-001**（perf 載具環境依賴，本輪即修）。

## §2 階段一零信任重偵察（實測事實，全錨定本輪 tool 輸出）

| 項目 | 實測命令 | 結果 | 硬閘 |
|------|---------|------|------|
| (a) AutoClaude 全套 | `python -m pytest tests/ -q` | **3315 passed / 122 skipped / 0 failed**（126s 初測） | ✅ ＝上輪 floor 3315 |
| (b) 架構契約 | `PYTHONUTF8=1 lint-imports` | **8 kept / 0 broken**（195 檔/489 依賴） | ✅ |
| (c) LOC / snapshot / git | `check_loc_budget` / `snapshot_sync --check` / `git status` | **violations=0 / 新鮮 / 工作樹乾淨** | ✅ |
| (d) AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | **exit 0**；v0.01:1478 / v0.25:1656 / scripts:129 | ✅ |
| (e) 三軸待辦盤點 | Explore + 親讀碼複核 | A 軌 adapter 已 GA 無缺口；B 軌翻環家族收齊、active RFC 空、僅 FF-5 doc 瑣碎 + FF-16 advisory；C 軌 SD_09 為唯一線索 | ✅ |
| (f) 外部工具依賴 | — | 本輪純 AutoClaude 內部碼，無新外部 CLI/服務依賴 | n/a |

**硬閘結論**：基線零退化、零 failed、不低於上輪（3315 ≥ floor 3315）→ 准予進入後續階段。

### §2.1 🔴 關鍵零信任發現（推翻 Explore 初步線索 — zero-trust 雙向紀律）

階段一 Explore 盤點指 C 軌 SD_09「有 X/Y/Z 三組可寫缺檔 delta」。**親查碼/檔證實此線索錯誤——SD_09 W0 的 X/Y/Z 三組早已完成**（2026-05-20，22/22 task CLOSED、5 方終審 APPROVED）：

| 組 | 內容 | 實測證據 | 真實狀態 |
|----|------|---------|---------|
| **Z1** | 移除 11 處 nightly continue-on-error | `ci.yml` 12 行 `# ...continue-on-error` 全是「2026-05-20 B-09 已移除」註解；真正 active 僅 3 處（`ci.yml:138` SD_10 PG-track + `pg-e2e-on-label.yml:21,64`），全為刻意保留之延後項，移除反而錯 | ✅ 已完成 |
| **X1** | seed_kb.py + pgvector fixture | `tools/seed_kb.py`（13.7KB）、`tests/fixtures/pgvector_real_queries.json`（2.9MB）皆存在 | ✅ 已完成 |
| **Y1** | F-01~F-09 + ADR-SD09-006 | `ADR-SD09-006` 存在、ADR-SD09 001~010 齊全、F-0x 落 `SD09_Pre_W0_Audit_Findings.md` | ✅ 已完成 |

**SD_09 真正卡的不是寫碼，是觀察期累積**（依 forensic 紀律引 raw store，nightly 06-24 END 行為 SSOT）：

| 觀察期 | 真實值 | 達標？ | 證據 |
|--------|--------|--------|------|
| #2 AC4 14 天 p95<60ms | **25/14**，p95 48~51ms | ✅ 達標 | `.ac4_history.jsonl` 末筆 06-23 p95=50.97ms/recall 0.999 |
| #1 mutation unique-sha | 25/7 計數達、unique-sha 為源碼演進閘需 W1 本身 | ⏳ 自指閘 | — |
| #3 drift_log 30 天零事件 | **23/30** | ❌ 未達標（差 7 天） | `.drift_log_history.jsonl` 末筆 06-22 count=0 |
| observability 30 天 | **25/30** | ❌ 未達標（差 5 天） | nightly END 行 obs=25/30 |

**結論**：觀察期 #3/observability 未滿 30 天（預估 ~2026-06-29~07-01 成熟），**W1 launch 本輪無法啟動**。依掌舵者規則「未達標→轉認實等待輪」。

### §2.2 本輪實質 delta 的浮現（驗證觀察期時撞見的具體信號）

查 perf 取證時發現 nightly 06-24 **perf-baseline stage FAIL（exit=1）**：`decide_correction` p95 **+42.2% BLOCK**，`.perf_history.jsonl` 軌跡**單調爬升** 1604→2602→2848→3086→3145→3218→3711→3701ms。單調（非隨機噪音）→ 有累積性根因 → 值得查。此即本輪 C 軌實質 delta。

## §3 三軸成熟度現況 + 本輪定位

| 軸 | 現級 | 證據 |
|----|------|------|
| **A 協作自治** | **L5** | improving_60/61 轉譯策略元學習活體化 + weak_regex 第二信號。adapter 已 GA、無未竟整合缺口。 |
| **B 流程自治** | **L5** | 翻環家族（AUTO_RECOVERY/SLV/fire/catch/scaffold_gc）收齊。本輪無可寫 delta。 |
| **C 引擎自治** | **L5** | 自演化 wire 進 ESCALATION + 跨 session DAL 元學習。**本輪修復**：perf 取證載具去環境依賴化。 |

`L_合體 = min(A=L5, B=L5, C=L5) = **L5**`（本輪**維持**，非升級——取證載具修復不改成熟度）。

---

## §4 <Architecture_Design_Review>（寫任何實質 Python 前必出）

### 4.1 架構純潔性
- **不創 God-object**：改動僅 `tests/perf/test_decide_correction.py` 一支測試檔——加 1 個 import、workload 多 1 層 `patch.object`、test 多 1 條守衛 assert + docstring。無新類別/職責。
- **Thin Facade 維持**：n/a（純測試載具，零 production 程式變更；`playbook_runner.py`/kernel/plugins/ports 全未觸碰）。
- **邊界**：stub 目標 `prompt_builder.build_file_state_snapshot` 為既有 module-global，patch 點與既有 `_call_with_retry` HTTP 層 stub 同精神（皆「隔離環境依賴使基線量純邏輯」）。

### 4.2 持久化相容
- **無新持久化**。`.perf_baseline.toml`（auto-generated SSOT）**本輪不手改**——`should_lock`（`perf_baseline_lock.py:160-163`）已證對 2602→~2ms 巨幅下修在容忍內、連續 7 次 nightly 後 auto-relock 至 `max(p95s)`≈2ms。DAL 三後端無涉。

### 4.3 安全防護網
- **無新 shell 指令生成路徑**。本輪反而**移除**測試對 `git` 子行程的依賴（stub 之）。CONDITIONAL 三層消毒不需擴充（零新增攻擊面）。

### 4.4 對外 I/O 安全
- 本輪**無新增 `ToolInvocationPort` 外呼路徑**（純測試載具 stub）→ allowlist/SSRF 攻防 n/a。

### 4.5 設計抉擇記錄（為何 stub 而非他法 / 為何不手改 baseline）
- **為何 stub `build_file_state_snapshot` 而非「在空 git dir 跑測試」**：stub 最 surgical、與既有 `_call_with_retry` HTTP 層 stub 慣例一致；docstring 本即宣稱該測試量「prompt build + Pydantic + Hallucination Guard 完整流程」，git snapshot 屬偶然 I/O 非待測邏輯。
- **為何不改 production `build_file_state_snapshot`**：production correction 非熱路徑、working_dir 為使用者專案小 repo、git diff 快，Gap-007-C 提供 Brain 變更檔上下文之設計意圖正確 → Rule 3 surgical 不擴張 scope。
- **為何不手改 `.perf_baseline.toml`**：它是 auto-generated（檔頭自述），手改會被 lock 工具覆寫且屬壞習慣；且近亞毫秒基線手設過緊會觸 jitter 偽 WARN（token_halt_roundtrip 前例）。交由系統既有 auto-relock（取 7 輪保守 max）最穩。

---

## §5 增量設計（W 項 / 介面 delta / 驗證）

### W-64-1 — perf 測試 stub git 層 + Rule-9 上界守衛
`tests/perf/test_decide_correction.py`：
1. workload 的 `with` 併入 `patch.object(prompt_builder, "build_file_state_snapshot", return_value="")`（鏡像既有 `_call_with_retry` stub），使基線量純 CPU-bound 邏輯、確定性。
2. test 末加 **Rule-9 守衛** `assert baseline.p95_ms < 500`：純邏輯 100 次呼叫實測 p95 ~2ms（5 輪 1.9~2.2ms），<500ms 給 ~250x headroom；若 `build_file_state_snapshot` 等子行程 I/O 被重新計入，p95 躍至數千 ms（monorepo git diff ~2900ms）即 fail loud，防環境依賴假退化回歸。
3. docstring 補 DEF-64-001 根因與修法。

### W-64-2 — baseline auto-relock（不手改 toml）
依 §4.2/§4.5：W-64-1 落地後 nightly 量 ~2ms < 2602×1.15=2992ms → 立即 PASS（假 BLOCK 消失）；`should_lock` 連續 7 輪後 auto-relock 至 ~2ms。本輪**零手改 SSOT**。

### 不需動的部分（scope 收斂證據）
- production 程式零變更（`git status` 僅 `tests/perf/test_decide_correction.py` + 缺陷帳本）。
- 無 FSM/`_HAPPY_PATH`/`*.tla` 變更 → **無五軌 TLC**。無 AISDLC_SDD 凍結本體變更 → 無 Copy-on-Evolve。無新 plugin/port/sink/alembic。

---

## §6 RTM（需求→設計→測試 追溯）

| RTM | 需求 | 設計落點 | 驗證 | 狀態 |
|-----|------|---------|------|------|
| R-64-1 | decide_correction perf baseline 量純邏輯（去 git I/O 環境依賴） | W-64-1 | cProfile+stub 對照證 git I/O 占 99.7%；修後 `pytest tests/perf/test_decide_correction.py` 0.32s（原 58.5s） | ✅ |
| R-64-2 | 假 BLOCK 消除、真退化可被捕 | W-64-1 | `perf_regression_check.py perf_results.json .perf_baseline.toml`：[PASS] decide_correction 2602.1→2.1ms / green=3 warn=0 block=0 / EXIT=0 | ✅ |
| R-64-3 | Rule-9 守衛防環境依賴回歸 | W-64-1 | `assert p95<500`；git I/O 潛回則 p95~2900ms 觸發 fail loud | ✅ |
| R-64-4 | baseline 確定性穩定 | W-64-1/2 | 5 輪重量 p95 1.9~2.2ms（max 2.17）；auto-relock 由 should_lock 接手（已證容忍下修） | ✅ |
| R-64-5 | 零退化基線 | §7 矩陣 | full pytest **3315/0 failed**（68s，原 126s）；lint 8 kept；LOC 0 | ✅ |
| R-64-6 | surgical / production 零影響 | §4 | `git status` 僅測試檔 + 帳本；production `build_file_state_snapshot` 未動 | ✅ |
| R-64-7 | maturity 不變（L5 維持，取證載具修復非升級）誠實 | §3 | 三鏡 audit OVERALL PASS，見 `AutoSDD_ZeroTrust_Audit_64.md` | ✅ |

## §7 零退化驗證矩陣（floor = improving_63 §2 實測；通過條件每輪實測，禁寫死）

| 檢查 | 命令 | 通過條件 | 結案實測 |
|------|------|---------|---------|
| AutoClaude 全套 | `python -m pytest tests/ -q` | ≥ **3315** passed / 0 failed | **3315 / 0 failed**（68s）|
| 架構契約 | `PYTHONUTF8=1 lint-imports` | 全部 kept / 0 broken | **8 kept / 0 broken** |
| LOC 分級 | `python tools/check_loc_budget.py` | 全部過 | **violations=0**（total=18999 純測試變更不計入）|
| perf 閘門 | `python tools/perf_regression_check.py perf_results.json .perf_baseline.toml` | block=0 / EXIT=0 | **green=3 warn=0 block=0 / EXIT=0**（decide_correction 2602.1→2.1ms PASS）|
| AISDLC_SDD 閘門 | `bash scripts/ci-gate.sh` | exit 0 | **exit 0**（本輪零 SDD 變更，階段一已驗）|
| 五軌 TLC | （僅 FSM 變更時）| **n/a（本輪零 FSM/`*.tla` 變更）** | n/a |

## §8 缺陷 / 延後

- **DEF-64-001**（P2，perf 載具環境依賴）本輪即修 fixed@improving_64（見缺陷帳本）。
- **SD_09 W1 launch**：觀察期 #3（drift 23/30）/observability（25/30）未滿 30 天，預估 ~2026-06-29~07-01 自然成熟 + W0 G0 人工預檢後可啟。本輪非延後技術債，是**等待時間閘門**（不可純寫碼）。下輪可於觀察期成熟後接 SD_09 W1（含改 token_guard 源碼解 unique-sha 閘）。
- **production `build_file_state_snapshot` 每次 Brain correction spawn git**：誠實記為觀察項（非缺陷——小 repo 快、設計意圖正確）；若未來 production 用於超大 repo 再評估快取/節流。
