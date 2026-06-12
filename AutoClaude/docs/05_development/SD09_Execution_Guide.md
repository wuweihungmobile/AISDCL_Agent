# SD_Improving_09 嚴格執行大綱（Opus 4.7 操作指南）

| 項目 | 內容 |
|------|------|
| 目標文件 | [SD_Improving_09.md](../04_planning/SD_Improving_09.md) **v1.0（W0 task list 22/22 CLOSED + 五方終審 APPROVED 2026-05-20）** |
| 執行基線 | **2,094 passed / 122 skipped**（SD_08 W6 G6 末，2026-05-18 確認）→ **W3 Round 4 audit P0-AUDIT-R3-2 修復後實測 2,505 passed / 122 skipped（超 SD_08 W6 基線 +411；含 ADR-SD09-008 ac4 雙軌 +10 + Round 4 mutation_baseline_lock sha 強化 +3 case）** |
| 預估終線 | W6 末 **≥ 2,523 passed（軟目標） / ≥ 2,513 passed（硬底線）**（依 W3 Round 4 實測 2,505 為新基線 +18；W0/W3 補測落地後重新校準）|
| 執行模型 | Claude Opus 4.7（標準模式，**不要用 /fast**） |
| 總範圍 | 7 議題群（A→B→C→D→E→F→G）/ 7 Wave |
| G0 啟動日 | **2026-06-18 或之後**（最晚觀察期結束日 2026-06-17 + ≥ 1 工作日提前期；最遲 **2026-06-26**，對齊主規劃 §6 PM #6 (b) 拍板）|
| 建立日期 | 2026-05-19 |
| 文件版本 | **v1.0（與主規劃 SD_Improving_09.md v1.0 同步升版 2026-05-20 — W0 T0-F4 trace_id 路徑 (b) finalized + T0-7 6 ADR PM 形式核准 + T0-1 §7.1~§7.4 13 bullet 填實 + T0-C3/E1/10 全 CLOSED）** |
| 對應 ADR | [ADR-SD09-001](../04_planning/ADR/ADR-SD09-001-pg-db-only-cutover.md) ~ [005](../04_planning/ADR/ADR-SD09-005-pg-canary-stage-thresholds.md) 共 **5 條 W0 必過硬條件** + [ADR-SD09-006](../04_planning/ADR/ADR-SD09-006-kb-metric-port.md) **v1.0 ACCEPTED**（W0 PM 形式核准）+ [ADR-SD09-007](../04_planning/ADR/ADR-SD09-007-hook-governance.md) v1.0 ACCEPTED（W0 補修 Hook Governance）|

---

## 0. G0 啟動前置 DoD（啟動日前必完成）

### 0.1 三觀察期一覽表（QA M3/M4 + SA C4/C5 修復）

| # | 觀察期 | 起算日 | 結束日 | 失敗回退 |
|---|--------|--------|--------|---------|
| **#1** | mutation pilot TokenGuardPlugin 連續 7 次達 ≥ 70% **+ 紀律 #12 tail 7 筆 unique source_sha256 ≥ 7**。**✅ kill_rate 條件已達標**（R37 kill_rate=76.51% > 68% effective threshold，streak 7/7；[ADR-SD09-009 §11 R38 拍板](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)）；**唯一剩餘為 unique sha 源碼演進閘門**（需 W1 active 改 token_guard 源碼；idle 期凍結不達標，R47 audit 訂正見 §11.6）；80% 為長期非 G0 硬目標（等價變異天花板，非 G0 阻塞）| 2026-05-19 | 2026-06-01（W3 末判定） | < 60% → SD_10 接續 pilot（不阻塞 SD_09 W0；R-SD08-PM-#3）|
| **#2** | AC4 14 天 nightly 全綠（pg-e2e-nightly artifact 累計）— **升級門檻 p95 < 60ms tolerant**（[ADR-SD09-008 v0.4 ACCEPTED](../04_planning/ADR/ADR-SD09-008-ac4-tolerant-track.md#34-pm-拍板決定書2026-05-25) 軸 C 拍板 2026-05-25；v0.4 為 Round 12 取證更正版，60ms 拍板實質不變）；strict 50ms 降為觀察指標 `strict_streak` 持續採集 | **2026-05-26**（新口徑首筆 jsonl）| **~2026-06-16**（R55 forensic 訂正：原 06-08 投影過樂觀；`filter_recent` 為過去 14 日曆天滾動窗口需 14 連續筆，對 schtasks 漏跑日高度敏感；最後缺口 06-02 → 需 06-03~06-16 連續無缺口，任一漏跑即順延）| 黃線 3 / 紅線 5 告警；未達 → W0 T0-C2 延期或議題 C 延 SD_10 |
| **#3** | drift_log 30 天零事件（SD_08 W5 落地起算）| 2026-05-18 | 2026-06-17 | 任一 drift > 0 → W5 雙條件未達 → fall-back R-SD09-A-4 |

> **觀察期未達標處理矩陣**：達標 → 啟動 ≥ 2026-06-18；抖動 → 延長至下次連續達標；未達 → 議題群降級 / 延 SD_10。

> **觀察期 #1 雙重達標條件（SD_09 W3 Round 11 audit P2-R11-1 文件化修復；R38 PM 拍板更新；R39 audit P2-R39-1 輪次標記 SSOT 訂正）**：
> 1. **kill_rate 條件 — ✅ 已達標**：連續 7 次 ≥ 70%（target 75% - tolerance 5% - ±2pp = **68% effective threshold**，[ADR-SD09-009 §5.5](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)）。最新 R39 kill_rate=**76.51%**（114/35/susp 0）遠超 68%，streak **7/7**。演進：Round 9 69.80% → R10 71.81% → R11 74.50%（suspicious 7→4→0 bounce flake 證實 mutmut 半確定性）→ R35 73.83% → R36/R37/R39 76.51%（suspicious=0）→ R38 76.17%（suspicious=1）。
> **⚠️ 輪次數字 SSOT（P2-R39-1）**：自 2026-05-27 起 source_sha256=20940e1b 維持不變，同 sha 上 mutmut suspicious 半確定性使 kill_rate 在 **73.83%~76.51%** 區間 bounce（皆 >68% effective，結論不變）；`append_history` M-05 每 UTC 日僅留最後一筆。因此**各 Round 標註的 kill_rate 為該輪當下取證快照**（非單調），「R37=76.51% vs R38=76.17%」非矛盾而是 bounce flake；歷史對照**以 [.mutation_history.jsonl](../../.mutation_history.jsonl) 的 timestamp+source_sha256 為單一真相**，勿以輪次號反推 jsonl 內容。
> 2. **紀律 #12 sha unique 條件 — ⏳ 唯一剩餘瓶頸（源碼演進閘門，非時間閘門；R47 audit 訂正）**：tail 7 筆 `source_sha256` ≥ 7 unique（plugin 目錄 .py 檔合併 sha256 截 16 chars）— 由 [tools/mutation_baseline_lock.py:297-366 should_lock](../../tools/mutation_baseline_lock.py#L297) 實作。**達標需 token_guard plugin 源碼產生 ≥ 7 個相異 UTC 日版本**（M-05 每日上限 1 unique sha），唯有 **W1 active 開發合法改動 token_guard 源碼**時發生；**idle 觀察期源碼凍結（自 2026-05-27 sha=20940e1b）→ 重跑只追加相同 sha → unique 數不增（log `reason=sha_partial_duplicate`）**；若 W1 不觸碰 token_guard 則依 R-SD08-PM-#3 延 SD_10（[ADR-SD09-009 §11.6](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)）。**絕不可人工 churn 源碼衝 sha**（紀律 #12 反作弊）。
>
> **80% 目標降級（R38 PM 拍板 — 等價變異天花板）**：先前軸 B 追逐的「80% kill_rate」**已下修為長期非 G0 硬目標**。[thresholds.py:36 `should_compact_decision`](../../autoclaude/plugins/token_guard/thresholds.py#L36) 恆等於 `return token_pct >= threshold`，correction-loop 分支（#125/126/127）為**等價變異任何測試殺不掉** → kill_rate ~76% 為天花板。詳見 [ADR-SD09-009 §11](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)。
>
> **同 commit 重跑場景說明（避免取證誤判）**：若 user 連跑 N 次 nightly **但 plugin 目錄無變動** → jsonl record 中 unique sha=1 → 即使 kill_rate 連續 7 次達標，`should_lock` 仍以 `reason=sha_partial_duplicate` 或 `sha_not_unique_full` 正確拒鎖（紀律 #12 設計預期，非 bug）。`append_history` M-05 對同 module + 同 UTC date 去重 → 單 session 重跑當日只 +1 unique sha。

### 0.2 G0 啟動前置 DoD

```
[  ] 觀察期 #1/#2/#3 全部達標（依 §0.1 表，最晚 2026-06-17）
     - #1 kill_rate 條件 ✅ 已達標（R37 76.51% > 68% effective threshold，streak 7/7；R38 PM 拍板 ADR-SD09-009 §11）；唯一剩餘為 unique sha 源碼演進閘門（需 W1 改 token_guard 源碼，idle 凍結不達標，§11.6）；80% 為長期非 G0 硬目標（等價變異天花板，非 G0 阻塞）
[  ] Tech Lead 提交 W0 task breakdown（A + C + E + F 三方研究 + G 三方研究）
[  ] ADR-SD09-001~005 草案落地 + PM 形式核准（W0 啟動前）
[  ] SD_Improving_09.md §6 PM 拍板 8 項全數填入 + §7 三方研究意見摘要 4 section 填入 → 升 v1.0
[  ] 確認 git branch 已切至 sprint/sd_09_phase9（或沿用 sprint/sd_08_phase8）
[  ] 確認 SD_08 W6 G6 commit 已 tag 為 sd_08_w6_g6_pass
[  ] gate_audit.md §1-septies 骨架建立（SD09-G0~G6 簽核紀錄空表）
[  ] risk_log.md §15 骨架建立（R-SD09-* 風險登記）
```

### 0.3 每次開啟新 session 前必跑

```bash
# 1. 測試基線
python -m pytest tests/ -q --tb=no 2>&1 | tail -3
# 期望：≥ 2,505 passed / 122 skipped（SD_09 W3 Round 6 audit P0-AUDIT-R5-B 修復後保持；含 mutation_baseline_lock sha 強化 +3 case + Round 6 time-flaky test 改相對 now）

# 2. importlinter
PYTHONUTF8=1 lint-imports --config .importlinter
# 期望：7 kept / 0 broken（**Arch-M3 修復**：路徑 b Rule 8 改 contract test 覆蓋取代 importlinter Rule，任一路徑皆 7 kept）

# 3. LOC 預算
python tools/check_loc_budget.py
# 期望：violations=0（baseline=14058 永久鎖定 / total ≤ cap=16869）

# 4. 關鍵檔案 LOC
wc -l CLAUDE.md docs/08_deployment/Production_Migration_SOP.md \
      autoclaude/utils/trace_context.py autoclaude/infra/observability/pg_health.py 2>/dev/null

# 5. NOTE(SD_09) 殘留
grep -rn "NOTE(SD_09)" autoclaude/ tests/ | wc -l
# W0 起點：0 / W6 末：0

# 6. ADR 數
ls docs/04_planning/ADR/ADR-SD09-*.md | wc -l
# W0 末：5（001~005 全數 PM 形式核准）；若議題 G PM 拍板 (a) 路徑 → +ADR-SD09-006 = 6（v0.1 PROPOSED，W2 PG 落地後升 ACCEPTED）

# 7. 觀察期狀態（**QA-C2/C3 + SD-C1 + QA-M3 修復** — 命令健壯性 + drift_log schema 對齊 + PG fallback）
# 以下為 observability 命令，初始狀態（baseline 未鎖定 / PG 不可達）允許未命中
python tools/ac4_progress_check.py --json 2>/dev/null | jq -r '.ready_for_labeled_pr // "[observing]"'

# 觀察期 #1：以歷史 jsonl 驗 7 次連續（baseline.toml 僅紀錄鎖定值非歷史）
jq -s 'map(select(.module=="token_guard")) | .[-7:] | length as $n | (all(.kill_rate >= 0.70) and $n == 7)' .mutation_history.jsonl 2>/dev/null || echo "[observing]"

# 觀察期 #3：drift_log 30 天零事件（**SD-C1**：對齊 alembic 0013 真實 schema — detected_at + severity != 'info'；drift_count 欄位不存在）
# QA-C3：場景 A 個人開發無 PG 時改走 mock fixture
if command -v psql >/dev/null && [ -n "$AUTOCLAUDE_DB_DSN" ]; then
  psql "$AUTOCLAUDE_DB_DSN" -c "SELECT count(*) FROM drift_log WHERE detected_at > now() - interval '30 day' AND severity != 'info';"
else
  jq '[.[] | select(.detected_at > (now - 30*86400 | strftime("%Y-%m-%dT%H:%M:%SZ"))) | select(.severity != "info")] | length' tests/contract/fixtures/drift_log_30day_zero.json 2>/dev/null || echo "[no_pg_no_fixture]"
fi
```

---

## 1. 全程絕對規則（違反即停止）

```
[  ] 每完成一個交付物 → 立即跑全測，全綠才繼續
[  ] equivalence snapshot 83 fixture 任一斷裂 → 立刻停止（紅線 ❌16）
[  ] importlinter 出現 broken → 立刻停止並還原
[  ] LOC 超分級 budget → 立刻拆 package 或在 .loc-budget.toml 加 override（雙簽）
[  ] CLAUDE.md > 400 行 → 立刻擴寫至 sprint_history.md（紅線 ❌17；繼承）
[  ] Plugin 不可互相 import；不可直接 import utils.observability（Rule 7 繼承）
[  ] W5 PG db_only 切換前必須通過雙條件（ADR-SD08-005 §2.2 + ADR-SD09-001 §2；紅線 ❌20）— 未達禁切換
[  ] W5 真實 staging 跑必須 AI-Agent 演練 + 人類 DBA 親演 + 人類 PM 親簽（紅線 ❌21；缺一不可）
[  ] W2 mutation 擴展每次僅 1 個新 active pilot module（紅線 ❌19；ADR-SD09-002 §2.2）
[  ] W4 perf machine 採購未確認 PM 預算簽核前禁採購（紅線 ❌22；ADR-SD09-003 §3）
[  ] W3 議題 F 路徑選擇必須 W0 三方研究 + PM 拍板（不可中途換方案；紅線 ❌23-A，SD-m2 拆編號）
[  ] **W0 PM 路徑拍板未完成前禁推進 W3 trace_id 實作**（紅線 ❌23-A）
[  ] **路徑 b 落地缺 contract test `test_trace_context_subprocess_env.py` 覆蓋禁推進 G3**（紅線 ❌23-B；Arch-M3 修復 — 取代原 Rule 8 importlinter contract；R22 audit 命名一致性修復：實作擴展既有 W0 檔，不另建 _w3c.py）
```

---

## 2. 架構紅線（繼承 SD_07/SD_08 共 20 條 + 新增 3 條，共 23 條）

> **m1 修復**：紅線編號（❌N）與 importlinter Rule 編號（N）為不同概念 — 紅線是「禁止行為」清單；Rule 是 importlinter contract。本文件僅列 SD_08 + SD_09 新增 7 條，SD_07 ❌1~❌16 見 [SD07_Execution_Guide.md §2](SD07_Execution_Guide.md)。

| # | 禁止行為 | 來源 |
|---|---------|------|
| ❌1~❌16 | （SD_07 繼承）| SD_07 §2 |
| ❌17 | CLAUDE.md > 400 行 | SD_08 ADR-SD08-001 |
| ❌18 | `IObservabilityPort` 放在 `utils/` 而非 `core/ports/` | SD_08 ADR-SD08-004 §2.1 |
| ❌19 | mutation pilot 一次啟用 ≥ 2 個 active module nightly | SD_08 ADR-SD08-002（SD_09 ADR-SD09-002 §2.2 收緊）|
| ❌20 | PG db_only 切換未達雙條件（可觀測性 GA + 30 天零 drift）| SD_08 ADR-SD08-005 §2.2 |
| ❌21 | 真實 staging（≥ 1M 列）跑未有 AI-Agent 演練 + 人類 DBA 親演 + 人類 PM 親簽前推進切換 | **SD_09 ADR-SD09-001 §2.3** |
| ❌22 | perf machine 採購未經 PM 預算簽核（W2 上半必確認；commit signed-off 或 GPG 簽核驗證，非僅 grep 字串）| **SD_09 ADR-SD09-003 §3** |
| ❌23-A (**新增**) | W0 PM 議題 F 路徑拍板未完成前推進 W3 trace_id 實作 | **SD_09 ADR-SD09-004 §3** |
| ❌23-B (**新增**) | 議題 F 路徑 (b) 落地但 contract test `tests/utils/test_trace_context_subprocess_env.py` 未建立 W3C 區段（Arch-M3 修復：取消 Rule 8 importlinter contract，改 contract test 覆蓋；R22 命名一致性修復）| **SD_09 ADR-SD09-004 §3.1** |

⚠️ **`autoclaude.execution._runner_internals` importlinter contract 持續保留**（SD_07 W5 Rule 6 / SD_08 不拔除 / SD_09 不拔除）。

---

## 3.0 並行執行框架（SD_09 W3 Round 6 補建 — Architect/SA/SD/QA 多視角）

> **背景**：SD_09 W0 觀察期採集是「背景累計 30 天」非「凍結 30 天」。原 §3 Wave 線性敘述（W0→W1→...→W6 + 議題群 A→B→C→D→E→F→G）易誤讀為「全凍結」。本節以執行軸（第三維）明確並行語意，**§3 Wave 線性敘述為向下兼容保留**，但實際執行依本節 4 軸並行。

### 3.0.1 4 軸並行框架

| 軸 | 性質 | 內容 | 觸發 | 完成條件 |
|----|------|------|------|---------|
| **軸 A — 背景觀察期** | 自動 / 無人介入 | nightly 02:00 自動跑 → +1 筆 jsonl × N 天 | schtasks 啟用（user 5/25 手動） | #1 mutation 7 天 unique sha / #2 ac4 14 天 / #3 drift 30 天（最遲 2026-06-24）|
| **軸 B — W1 前景開發** | ~~主動 / 人類駕駛~~ **✅ W1 已落地 + R38 方向訂正** | ~~補 token_guard test 64 點位→提升 kill_rate~~ W1 PR（commit `0169b96`）已補 15 case + ADR-009/010 實作；kill_rate 達 76.51%。**R38 訂正：停止「加 case / churn 源碼衝 unique sha」**（80% 為等價變異天花板不可達；衝 sha 違紀律 #12 反作弊）。**R47 訂正：#1 unique sha 為源碼演進閘門**，唯有 W1 active 開發合法改動 token_guard 源碼才達標（idle 期源碼凍結不達標，非「自然多日 commit」可解），**禁人工 churn**。詳見 [ADR-SD09-009 §11.6](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md) | ~~隨時可啟動~~ 已完成 | kill_rate 76.51% ✅ 已達標；unique sha 待 W1 改 token_guard 源碼（idle 凍結不增）|
| **軸 C — PM 拍板** | 人類決策 | ~~ADR-SD09-008 三選項拍板（觀察期 #2 strict 50ms vs 真實 51-53ms 解法）~~ **✅ 2026-05-25 拍板選項 (a) 60ms tolerant**（提前 cut-off 6 天，依據 7 筆樣本 avg=51.84ms / max=53.21ms / σ=0.73ms） | ~~用戶主動~~ **已完成** | ~~cut-off **2026-05-31**~~ **2026-05-25 ACCEPTED v0.3**；後續實作落地 §3.4.3 七項由 Architect+QA 2026-05-26 完成 |
| **軸 D — W2-W6 預備研究** | 主動 / 不依賴觀察期 | §3 W1~W6 task list 中**不碰 §3.0.3 紅線區**的研究 / 設計 / 文件 / 預先 unit test | 隨時可啟動 | W2-W6 各 Wave 入口 DoD |

### 3.0.2 30 天時間軸（user 5/25 啟用 schtasks 為起算）

```
2026-05-25 (T0) ────────────────────────────────────────────► 2026-06-24 (T+30)
│                                                                              │
├─ 軸 A：schtasks 02:00 自動 +1 jsonl × 30 天 ───────────────────────────────►│ (#3 達標)
│        ├─ 軸 A #1: kill_rate 已達標；unique sha 待 W1 改 token_guard 源碼(idle 凍結不達標,§11.6)─►│
│        ├─ 軸 A #2 cutoff: ~2026-06-16 (R55 訂正 — trailing-window 需連續無缺口) ►│
│        └─ 軸 A #3 cutoff: T+30 (2026-06-24 — drift_log 零事件) ─────────────►│
│                                                                              │
├─ 軸 B：W1 token_guard test 補測 ───────────►│ (建議 ≤ T+10 完成，越早越好)  │
│        └─ 完成後 source_sha256 變 → 軸 A #1 重置 unique sha → 重新累計 7 天   │
│                                                                              │
├─ 軸 C：✅ PM 拍板 ADR-SD09-008 v0.4 ACCEPTED 2026-05-25（提前 cut-off 6 天；v0.3→v0.4 為取證更正）│
│        └─ 拍板選 (a) 60ms tolerant；軸 A #2 達標窗口 ~2026-06-16(R55 訂正) │
│           （strict 50ms 降為觀察指標 strict_streak；持續採集 0 損失）       │
│                                                                              │
└─ 軸 D：W2-W6 預備研究（不碰紅線區）────────────────────────────────────────►│
         ├─ ADR-SD09-001~005 落地驗證細化（§3 W0 T0-2~T0-6）                  │
         ├─ trace_id multi-process 路徑研究（§3 W3 議題 F）                   │
         ├─ KB metric 落地策略研究（§3 議題 G）                                │
         └─ sprint_history.md §1.5 骨架擴寫（§3 議題 E）                      │

────► T+30+ G0 啟動窗口（2026-06-25 ~ 2026-07-03）
         └─ 軸 A/B/C 全達標 → 5 條 ADR 形式核准 → 進入 W1 正式 Wave
```

### 3.0.3 紅線區（碰即重置觀察期 — 需評估 cost/benefit）

| 觸碰路徑 | 影響觀察期 | 重置代價 | 建議 |
|---------|----------|---------|------|
| `autoclaude/plugins/token_guard/*.py` | #1 mutation | unique sha 計數歸零，重新累計 7 天 | ~~軸 B 預期會碰~~ **W1 已完成（commit `0169b96`）。R38 訂正：❌ 禁止為衝 unique sha 刻意 churn / 修改源碼**（違紀律 #12 反作弊；source_sha256 由源碼計算 + M-05 同 UTC 日去重單 session 僅 +1 → 人工 churn 機制上無效且違紀）。#1 unique sha 唯有 W1 active 開發合法改動 token_guard 源碼才達標（idle 期凍結不增，非「自然多日 commit」可解；[ADR-SD09-009 §11.6](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)）。僅在 zero-trust audit 發現真實 P0/P1 bug 時才允許觸碰 |
| `tools/run_local_nightly.ps1` / `tools/ac4_nightly_collector.py` / `tools/drift_log_snapshot.py` / `tools/observability_snapshot.py` | 該工具對應觀察期 | 採集邏輯變動 → 取證一致性破壞 → 通常重起算 | **避免**：除非 zero-trust audit 發現 P0 bug（如 Round 6 P0-B）|
| `alembic/versions/*.py`（PG schema migration）| #3 drift_log | 若 migration 寫入 severity≠'info' → 30 天重起算 | **強烈避免**：PG schema 變動延至 G0 後 W5 Production_Migration_SOP |
| `tools/mutation_baseline_lock.py` / `tools/ac4_progress_check.py` / `tools/observability_ga_check.py` | 升級判定工具 | 判定邏輯變動 → 取證口徑漂移 | **避免**：除非紀律 #4「驗證鏡子自身要被驗證」單元測試補強 |

### 3.0.4 並行安全區（30 天內可放心改，0 影響觀察期）

- ✅ `autoclaude/core/*`（除 token_guard）/ `autoclaude/execution/*` / 其他 `autoclaude/plugins/*`
- ✅ `tests/` 全部（含本輪 P0-B time-flaky test 修復）
- ✅ `docs/` 全部（含 ADR / sprint_history / NextAction 報告）
- ✅ `tools/check_loc_budget.py` / `tools/snapshot_sync.py` 等工具（非 nightly 採集鏈）
- ✅ `.claude/settings.json` / `.gitattributes` / `pyproject.toml` 等專案配置

### 3.0.5 軸間同步點（cross-axis coordination）

| 同步點 | 觸發條件 | 動作 |
|--------|---------|------|
| **SP-1**：軸 B 完成 → 軸 A #1 重置 | token_guard test 補測 commit 入 main | 觀察期 #1 unique sha 重新累計 7 天；建議軸 B commit 時間越早越好 |
| **SP-2**：✅ 軸 C 拍板 → 軸 A #2 門檻校準（**2026-05-25 已完成**）| PM 2026-05-25 簽 ADR-SD09-008 v0.4 ACCEPTED 選 (a)（v0.3 拍板 + v0.4 取證更正）| 升級門檻 50ms → **60ms tolerant**；觀察期 #2 從 2026-05-26 首筆新口徑 jsonl 起算需 14 連續綠日；**R55 forensic 訂正**：因 schtasks 漏跑日（05-22/23、05-30/31、06-02 共 5 日）+ trailing-window 機制（過去 14 日曆天需 14 筆無缺口），最早達標自 06-08 訂正為 **~2026-06-16**（最後缺口 06-02 → 需 06-03~06-16 連續無缺口）；strict 50ms 持續採集為觀察指標 strict_streak（紅線 ❌4 — 不可刪除）|
| **SP-3**：軸 A #3 達標 → 軸 D 收斂 G0 | 2026-06-24 drift_log 30 天零事件 | 5 條 ADR PM 形式核准 / AC Matrix scaffolding / sprint_history §1.5 骨架同步完成 → G0 啟動 |
| **SP-4**：軸 B 重大重構 → 軸 A 全鏈通知 | 若 token_guard 重構觸碰 importlinter / LOC budget | 跑 §0.3 5 條檢查 + Round 7 zero-trust audit；觀察期 #1 重置不算 regression |

### 3.0.6 並行執行 SOP（每次 session 開始前）

```bash
# 1. 確認背景軸 A 健康（schtasks 是否每日跑 + jsonl 進帳）
schtasks /query /TN "AutoClaude_Nightly" | findstr Status      # 期望 Ready 非 Disabled
schtasks /query /TN "AutoClaude_Nightly" /V /FO LIST | findstr "Last Run"  # 期望近 24 小時

# 2. 確認觀察期進度（紀律 #13 可見性）
tail -1 logs/nightly_latest.log                                # 期望 END observation progress

# 3. 跑 §0.3 5 條檢查（pytest 2,505 / importlinter 7 / LOC 0 / CLAUDE.md ≤ 400 / NOTE 0）

# 4. 評估本 session 計劃碰哪個軸
#    - 碰紅線區 §3.0.3 → 評估 cost/benefit + 記錄重置原因
#    - 並行安全區 §3.0.4 → 直接做

# 5. session 結束 commit 時，commit message 標記影響軸
#    例：feat(W1): 補 token_guard/compactor test 24 點位 [軸 B；觸發軸 A #1 重置 SP-1]
```

---

## 3. Wave 執行協議（A→B→C→D→E→F→G 優先順序，待 W0 PM 拍板確認）

### ── W0：SD_08 收尾 + ADR-SD09-001~005 落地 + AC4 labeled PR 啟用（C + E + F + G 議題群）──

**目標**：
- SD_08 收尾驗證（mutation observing 進度 / AC4 nightly 累計 / drift_log 計數）
- ADR-SD09-001~005 PM 形式核准（**含新增 ADR-SD09-005 canary 三階梯閾值**）
- AC4 labeled PR 觸發啟用（議題 C — 將 dormant trigger 開啟，非首次部署）
- 議題 F + G 三方研究 + PM 拍板（§6 表 #4 + #5）
- 主規劃升 v1.0 + Execution Guide 同步升 v1.0

**逐項打勾**：
```
# 規劃落地
[  ] T0-1 SD_Improving_09.md v0.2 → v1.0（W0 三方研究填入 §7 + PM 8 項拍板填入 §6）
[  ] T0-2 撰寫 ADR-SD09-001 v1.0（PG db_only 切換不可逆轉折點 — 業務語意非物理；§2 同 process trace_id GA = W5 條件 / multi-process 延 W6/SD_10；§2.3 紅線 ❌21；§3 雙條件取證 SQL + 檔案路徑）
[  ] T0-3 撰寫 ADR-SD09-002 v1.0（mutation 全模組擴展策略 — §2.2 單一時間 1 active module；§2.3 nightly 拆三 cron job + TG 鎖定後退出 nightly 改週 baseline；W1/W2 三階段排程）
[  ] T0-4 撰寫 ADR-SD09-003 v1.0（perf 雙軌轉三軌 — §3 PM 預算簽核流程 commit signed-off + 緊急路徑 W4 採購未到位則議題群延 SD_10 G4 不阻塞）
[  ] T0-5 撰寫 ADR-SD09-004 v1.0（trace_id multi-process — §2 三選項擇一決策矩陣對應 Rule 7/8/0；§3 W3C parser 內聚 trace_context.py 不新建模組；§3 紅線 ❌23）
[  ] T0-6 (**新增 ADR — Architect M1**) 撰寫 ADR-SD09-005 v1.0（PG canary 三階梯閾值 — 10%/24h + 50%/48h + 100%/7d；**drift 事件 = `severity != 'info'` 任一筆**（SD-C1 對齊 alembic 0013 真實 schema）/ WAL lag CRITICAL / 連線數異常三觸發回滾條件；rollback SLA 拆「自動回退 ≤ 3 min + 取證歸檔 ≤ 30 min」Arch-M4 修復）
[  ] T0-7 PM 形式核准 ADR-SD09-001~005（場景 A 個人開發 dev 自核）（**2026-05-21 W0 完成**：4 條 ADR 檔尾簽核行統一為「✅ ACCEPTED 2026-05-21」；ADR-006 議題 G W0 階段保 PROPOSED 待 W2 PG 落地升 ACCEPTED）
[  ] T0-8 risk_log.md §15 新增 R-SD09-A-1~G-1 風險登記（含 A-3/A-4/B-2/F-2/G-1 新增 5 條）
[  ] T0-9 (**新增 — SA M5**) gate_audit.md §1-septies 骨架建立（SD09-G0~G6 簽核紀錄空表）

# C 議題群：AC4 labeled PR 啟用（dormant trigger 開啟）
[  ] T0-C1 確認 tools/ac4_progress_check.py --json 回報 ready_for_labeled_pr=true（觀察期 #2 通過）
[  ] T0-C2 將 .github/workflows/pg-e2e-on-label.yml 由 dormant 切為 active（`on: pull_request labeled` trigger 啟用）
[  ] T0-C3 SD08_AC_Matrix.md AC4-1/AC4-2 升級為「實測 recall ≥ 0.95 + p95 < 50ms + cb_open=0」
[  ] T0-C4（可選）新建 tools/ac4_dashboard.py — 視 PD 預算決定

# E 議題群（W0 骨架階段）— 議題 E 為 W0 + W6 兩端點
[  ] T0-E1 sprint_history.md §1.5 SD_07 完整段落擴寫骨架（標題 + W0~W6 子段落空殼；W6 末填入完整 ≥ 300 行）

# F 議題群：trace_id multi-process 三方研究 + PM 拍板
[  ] T0-F1 三方獨立研究（Architect / SA / SD）三選項（a/b/c）可行性 + PD 估算（填入 §7.1/7.2/7.3）
[  ] T0-F2 QA 量測可行性評估（subprocess 邊界 unit test 設計）（填入 §7.4）
[  ] T0-F3 PM 拍板選 (a)/(b)/(c) 並寫入 ADR-SD09-004 §2 + SD_09.md §6 #4
[  ] T0-F4 (**新增 — QA M1**) PM 拍板後 Tech Lead 執行 git rm 未選路徑章節並 commit `chore(SD_09): finalize trace_id path (a)/(b)/(c)`；W3 task list 僅保留選定路徑

# G 議題群：KB metric 落地三方研究 + PM 拍板
[  ] T0-G1 三方獨立研究（Architect / SA / SD）三選項（PG / 刪除 / 延 SD_10）可行性
[  ] T0-G2 QA 評估 30 天觀察期統計需求
[  ] T0-G3 PM 拍板（落地 PG → W2~W3 補 Wave；刪除 → 移除選項；延 SD_10 → 議題群降級為 backlog）寫入 ADR + SD_09.md §6 #5

# AC Matrix scaffolding（**SA-C1 / QA-M1 修復**：累計條數隨議題 F 路徑動態）
[  ] T0-AC SD09_AC_Matrix.md v0.1 scaffolding — **SD_09 新增 9~12 條**：
       - AC11×3 PG production（**SA-C2 修復 — 三條五欄拆分**：
         * AC11-1 雙條件齊備 — 對應 ADR-SD09-001 §2.2 + 取證 ADR §3 表 + 通過 30 天綠
         * AC11-2 DBA 親演 — 對應 §2.3 + 取證 `git --show-signature SD09_DBA_DryRun_Sign_W4.md` + 通過 signed-off
         * AC11-3 PM 親簽 — 對應 §2.3 + 取證 `SD09_PM_Release_Approval_W5.md` + 通過 signed-off）
       - AC12×2 mutation 擴展 / AC13×1 AC4 升級 / AC14×2 perf machine / AC15×1 滾動下沉
       - AC16 trace_id 條目數依 PM #4 拍板：路徑 (a)=2 / (b)=3 / (c)=1
       - **累計**：SD_07 19 + SD_08 10 + SD_09（路徑 a → 40 / 路徑 b → 41 / 路徑 c → 39；皆 ≥ 35 門檻 ✅）

# 新增前置任務（**QA-C1 / QA-M4 / SA-C3 修復**）
[  ] T0-A0 (**QA-C1 修復**) 新建 `tests/integration/fixtures/fk_staging_1m_wrapper.py` — subprocess 包裝 `tools/sd06_w3_staging_dryrun.sh` + 結果解析；+1 PD 估算（W3 T3-A4 前必須就位）
[  ] T0-O1 (**QA-M4 修復**) 新建 `tools/observability_ga_check.py` — 整合 IObservabilityPort + KB metric snapshot + trace_id ContextVar 三項日紀錄至 `.observability_history.jsonl`；W5 T5-A2 取證依賴
[  ] T0-S1 (**SA-C3 修復**) 快速修正 `docs/05_development/sprint_history.md` §0 line 4 既存錯誤「目前：SD_06 + SD_07」→「目前：SD_07 + SD_08」（SD_08 W6 已完成元數據漂移）；同步 line 16

# 環境變數補充
[  ] T0-10 .env.example 補 PG_PRODUCTION_CUTOVER_GUARD=true + AUTOCLAUDE_TRACE_ID_SUBPROCESS_PROPAGATION=env_var（依 F PM 拍板結果）
```

**G0 驗證**：
```bash
[  ] ls docs/04_planning/ADR/ADR-SD09-*.md | wc -l                          # = 5（必）+ 1（若 PM #5=(a)，ADR-006 v0.1 PROPOSED）= 6
[  ] ls docs/04_planning/ADR/ADR-SD09-005-pg-canary-stage-thresholds.md     # 存在
[  ] grep -E "ready_for_labeled_pr=true" .ac4_history.jsonl                 # 命中（觀察期 #2 通過）
[  ] grep -E "needs-pg-e2e" .github/workflows/pg-e2e-on-label.yml           # 命中（已啟用）
[  ] ls docs/03_testing/SD09_AC_Matrix.md                                   # 存在
[  ] grep -E "^### 1\.[1-5]" docs/05_development/sprint_history.md          # 含 §1.5 骨架
[  ] ls docs/05_development/gate_audit.md && grep "§1-septies" docs/05_development/gate_audit.md  # 命中
[  ] grep "R-SD09-" docs/05_development/risk_log.md | wc -l                 # ≥ 10
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,094 passed
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 7 kept / 0 broken
[  ] wc -l CLAUDE.md                                                        # ≤ 400
```

**G0 通過條件**：5 條 ADR PM 形式核准 / AC4 labeled PR 已啟用 / 三方研究 F+G 完成 + PM 拍板 / sprint_history.md §1.5 骨架就位 / gate_audit §1-septies + risk_log §15 骨架就位 / 主規劃 + Guide 同升 v1.0

---

### ── W1：mutation pilot 擴展 GoalSynthesisPlugin（B 議題群上半）──

**目標**：
- TokenGuardPlugin 鎖定 → 從 nightly 移除改週 baseline（ADR-SD09-002 §2.3）
- 擴展 GoalSynthesisPlugin 兩週 pilot
- 目標 ≥ 65%
- `.mutation_baseline.toml` 補入 goal_synthesis 鎖定值

**逐項打勾**：
```
[  ] T1-B1 git tag sd_09_w0_g0_pass（W1 前快照）
[  ] T1-B2 確認 TokenGuardPlugin 已連續 7 次達 ≥ 70% 並鎖定 .mutation_baseline.toml（觀察期 #1）
[  ] T1-B3 (**Architect M2 修復**) .github/workflows/ci.yml `mutation-test-nightly` job 重構：
       - TokenGuardPlugin step 從 nightly 移除，改為週 baseline 抽測（schedule: weekly）
       - 新增 GoalSynthesisPlugin nightly step：
         * `--paths-to-mutate=autoclaude/plugins/goal_synthesis --tests-dir=tests/plugins/goal_synthesis`
         * `-p no:xdist` + `--no-progress`
         * `timeout-minutes=45` + `continue-on-error=true`
       - 拆獨立 cron job（與 TG 週 baseline + 未來 Coordinator nightly 三個獨立 schedule，不同小時觸發）
[  ] T1-B4 mutation_analysis.py 確認支援多模組（survived diff 分類擴展）
[  ] T1-B5 mutation_baseline_lock.py 確認支援多模組鎖定（連續 7 次達標 -5%）
[  ] T1-B6 W1 兩週 nightly 連跑
[  ] T1-B7 W1 末產出 docs/06_quality/SD09_Mutation_GoalSynthesis_Report.md
[  ] T1-B8 補 tests/contract/test_mutation_multi_module_lock.py（≥ 4 case：兩模組獨立鎖定 / 同步鎖定 / 抖動單日不鎖 / 模組間 LRU 順序）
```

**G1 驗證**：
```bash
[  ] grep -E "paths-to-mutate=autoclaude/plugins/goal_synthesis" .github/workflows/ci.yml   # 命中
[  ] grep -E "schedule:" .github/workflows/ci.yml | wc -l                   # ≥ 3（TG 週 + GS nightly + 未來 Coord）
[  ] grep -E "token_guard" .mutation_baseline.toml                          # 命中（前置鎖定）
[  ] ls docs/06_quality/SD09_Mutation_GoalSynthesis_Report.md               # 存在
[  ] python -m pytest tests/contract/test_mutation_multi_module_lock.py -v  # ≥ 4 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,098 passed（+4）
```

> **G1 fall-back**（R-SD09-B-1）：若 GoalSynthesis 首測 < 60% baseline，W1 末僅產 Report 含 backlog；不阻塞 W2-W6；SD_10 接續。

---

### ── W2：mutation 擴展 OrchestrationCoordinator（B 下半）+ perf machine 採購評估（D 上半）+ KB metric 落地若 (a)（G）──

**目標**：
- GoalSynthesis 鎖定 → 移除 nightly；擴展 OrchestrationCoordinator pilot 兩週（目標 ≥ 60%）
- perf machine 採購評估 + PM 預算簽核（紅線 ❌22）
- 議題 G 若 W0 PM 拍板選 (a) PG 落地則於本 Wave 實作；若選 (b)/(c) 則跳過

**逐項打勾**：
```
[  ] T2-B1 git tag sd_09_w1_g1_pass
[  ] T2-B2 確認 GoalSynthesisPlugin 已鎖定或進入 observing → 從 nightly 移除（ADR-SD09-002 §2.3）
[  ] T2-B3 (**SD C2 修復**) .github/workflows/ci.yml 新增 OrchestrationCoordinator nightly step：
       - `--paths-to-mutate=autoclaude/core/orchestration/coordinator.py`（**單檔精準，非整目錄**）
       - `--tests-dir=tests/core/orchestration`
       - 預檢：`ls tests/core/orchestration/ && find autoclaude/core/orchestration -name '*.py'`（G2 驗證納入）
[  ] T2-B4 W2 兩週 nightly 連跑
[  ] T2-B5 W2 末產出 docs/06_quality/SD09_Mutation_Coordinator_Report.md

# D 議題群上半：perf machine 採購評估
[  ] T2-D1 撰寫 docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md：
       - 候選方案（GPU vs CPU bare metal vs 雲端 GPU instance）
       - 預算評估（一次性 + 月度租用）
       - 季度校準排程設計
       - 上線時程（W2 上半確認預算 / W2 下半下訂 / W4 啟用）
       - **緊急路徑（Architect/SD C4 修復）**：W2 採購未簽核 → 議題群整體延 SD_10，W4 G4 不阻塞；tests/perf/test_pgvector_recall_perf.py 維持 `@pytest.mark.perf_machine_only` deselect
[  ] T2-D2 (**Minor m3 修復**) PM 預算簽核 — 紅線 ❌22 強制條件；以 **commit signed-off 或 GPG 簽核** 驗證（非僅 grep 字串）
[  ] T2-D3 採購排程確認（W2 下半）— self-hosted runner vs ssh 手動（**SD m1 修復 — T4-D1 副選項**）

# G 議題群（若 W0 PM 拍板選 (a) PG 落地）
[  ] T2-G1 (**SD M2 修復**) KB metric 落地 — 設計 `IKbMetricStore` port + Pg adapter（不視為 state_repository 範疇；不破壞 SD_06 storage.mode 三後端架構）
[  ] T2-G2 alembic migration 0015 — `kb_metrics` 表 schema 設計（snapshot 欄位對應 KnowledgeBaseMetrics）
[  ] T2-G3 補 tests/contract/test_kb_metric_persistence.py（≥ 4 case：PG/Local 雙 adapter 切換 / yaml_only 模式 fall-back / metric 寫入 / 跨 session 讀取）
[  ] T2-G4 若 PM 拍板選 (b) 刪除 或 (c) 延 SD_10 則跳過 T2-G1~G3
```

**G2 驗證**：
```bash
[  ] grep -E "paths-to-mutate=autoclaude/core/orchestration/coordinator.py" .github/workflows/ci.yml   # 命中（單檔精準）
[  ] ls tests/core/orchestration/                                           # 存在
[  ] ls docs/06_quality/SD09_Mutation_Coordinator_Report.md                 # 存在
[  ] ls docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md               # 存在
# QA-C5 修復：以文件查詢取代未定義環境變數 $PROCURE_OK / $KB_METRIC_PATH
[  ] [ -f docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md ] && git log --show-signature -1 -- docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md  # PM 簽核（signed-off / GPG）
# 議題 G 路徑依 SD_09.md §6 #5 PM 拍板：(a) → 必存在 / (b)(c) → 跳過
[  ] grep -qE "^\| \*\*5\*\*.*\(a\)" docs/04_planning/SD_Improving_09.md && ls autoclaude/core/ports/kb_metric_store.py || echo "[G_path_b_or_c_or_undecided]"
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,103 passed（+5）/ G (b/c) fall-back ≥ 2,101（+3）
```

---

### ── W3：PG production SOP §4-§5 補完（A 上半）+ trace_id multi-process 落地（F，依 W0 PM 拍板）──

**目標**：
- `Production_Migration_SOP.md` §4 切換時序（三階梯 canary）+ §5 回退（含 PG dump → YAML import script）補完
- 議題 F 落地（依 W0 PM 拍板選 (a)/(b)/(c)）
- AI-Agent dry-run 演練（≥ 1M 列模擬）

**逐項打勾**：
```
[  ] T3-A1 git tag sd_09_w2_g2_pass
[  ] T3-A2 (**ADR-SD09-005 對齊**) Production_Migration_SOP.md §4 切換時序補完：
       - yaml_only → both 灰度（dual_write_strict=fail_loud）
       - both → db_only 灰度（雙條件齊備後）
       - 三階梯 canary：**10% / 24h → 50% / 48h → 100% / 7d**（ADR-SD09-005 §2 鎖定）
       - 回滾觸發條件（**SD-C1 修復**：對齊 `alembic/versions/0013_drift_log.sql` 真實 schema）：**drift 事件 `severity != 'info'` 任一筆** / WAL lag CRITICAL / 連線數異常（ADR-SD09-005 §2.2）；**同時觸發以最嚴重者為依據單次回滾至 yaml_only**（Arch-M1）+ rollback 鎖定窗口 30 min 內不重複觸發
       - rollback SLA ≤ 10 min
       - state machine 圖（mermaid，**Architect 補強建議 5**）：canary 三階梯 × PgHealthMonitor WAL lag 三閾值聯動
[  ] T3-A3 (**SD M4 修復**) Production_Migration_SOP.md §5 回退範本補完：
       - rollback SQL 腳本（dual_state pg_first 回退至 yaml_first）
       - **PG dump → YAML import script**（明訂「不可逆 = 業務語意」非物理不可逆）
       - drift_log 取證流程
       - 通知模板（Slack / email）
[  ] T3-A4 (**SD M3 修復**) AI-Agent dry-run（≥ 1M 列模擬）：
       - **fixture 路徑明訂**（**QA-C1 修復**：原描述「reuse SD_06 fixture」實體不存在；SD_06 staging dry-run 實體為 shell script `tools/sd06_w3_staging_dryrun.sh`）：W0 新建 Python 包裝 fixture `tests/integration/fixtures/fk_staging_1m_wrapper.py`（subprocess 包裝 `tools/sd06_w3_staging_dryrun.sh` + 結果解析）；T0-A0 +1 PD 估算
       - 演練輸出 → docs/06_quality/SD09_DryRun_Report_W3.md
       - fall-back（R-SD09-A-3）：dry-run 失敗 → 回 W2 修補 schema/index；不阻塞 W4 SOP 文件補完
[  ] T3-A5 補 tests/contract/test_pg_migration_sop_section_4_5.py（≥ 6 case：§4 三階梯 canary / 回滾觸發 / §5 rollback SQL 範本 / PG dump → YAML script）

# F 議題群：trace_id multi-process — 路徑 (b) W3C TraceContext（**PM #4 拍板 finalized 2026-05-20；T0-F4 已 git rm 路徑 (a)/(c)**）
[  ] T3-F1b autoclaude/utils/trace_context.py **內聚** 擴展 `to_traceparent_header() -> str` + `from_traceparent_header(h: str) -> str` + `propagate_to_subprocess_env(env: dict) -> dict`（不新建模組；ADR-SD09-004 §3）
[  ] T3-F2b subprocess 注入點全覆蓋（**SD-C5 修復：9 處明確列舉**，ADR-SD09-004 §2.3）：
       (1) autoclaude/perception/pty_wrapper.py
       (2) autoclaude/execution/cross_step_validator.py
       (3) autoclaude/execution/pre_run_validator.py
       (4) autoclaude/execution/evaluator.py
       (5) autoclaude/execution/mutation_applier/_conditional.py
       (6) autoclaude/plugins/fast_path_plugin.py
       (7) autoclaude/plugins/token_guard/git_verifier.py
       (8) autoclaude/decision/prompt_builder.py
       (9) autoclaude/core/services/mutation/_conditional_evaluator.py
[  ] T3-F3b env override 衝突處理：caller 已設 TRACEPARENT 時不覆蓋
[  ] T3-F4b 擴展 tests/utils/test_trace_context_subprocess_env.py（W0 已存在 5 case；W3 新增 ≥ 4 case：traceparent 解析 / 不合法格式 / 父子 process 串接 / OTel 過渡相容；R22 命名一致性修復 — 沿用既有檔不另建 _w3c.py）
[  ] T3-F5b (**Arch-M3 修復 — Rule 8 改 contract test 覆蓋**) 補 tests/contract/test_trace_context_plugin_isolation.py（≥ 2 case：plugin 禁直接 import `to_traceparent_header` / `propagate_to_subprocess_env` 走 Port 注入）；importlinter 維持 7 kept；紅線 ❌23-B 啟用
```

**G3 驗證**：
```bash
[  ] grep -E "^## §4\." docs/08_deployment/Production_Migration_SOP.md      # 命中
[  ] grep -E "^## §5\." docs/08_deployment/Production_Migration_SOP.md      # 命中
[  ] grep -E "pg_dump|PG dump" docs/08_deployment/Production_Migration_SOP.md  # 命中（§5 PG → YAML）
[  ] grep -E "10%.*24h|50%.*48h|100%.*7d" docs/08_deployment/Production_Migration_SOP.md   # 命中（ADR-SD09-005 對齊）
[  ] grep -E "mermaid" docs/08_deployment/Production_Migration_SOP.md       # 命中（state machine 圖）
[  ] ls docs/06_quality/SD09_DryRun_Report_W3.md                            # 存在
[  ] ls tests/integration/fixtures/fk_staging_1m_wrapper.py                 # 存在（W0 T0-A0 包裝 tools/sd06_w3_staging_dryrun.sh）
[  ] python -m pytest tests/contract/test_pg_migration_sop_section_4_5.py -v   # ≥ 6 case 綠
# 路徑 (b) W3C TraceContext（PM #4 拍板 finalized）：
[  ] python -m pytest tests/utils/test_trace_context_subprocess_env.py -v   # ≥ 9 case 綠（W0 5 + W3 7 W3C）
[  ] python -m pytest tests/contract/test_trace_context_plugin_isolation.py -v   # ≥ 2 case 綠（Arch-M3 取代 Rule 8）
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # 7 kept（Arch-M3：路徑 b Rule 8 改 contract test 不增 importlinter Rule）
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,110 passed（+7）
```

> **G3 強制阻塞**：紅線 ❌21 違反（未經 AI-Agent dry-run 即推進 W4）→ G3 不放行 + git revert HEAD；紅線 ❌23-A 違反（W0 PM 未拍板）→ G3 不放行；紅線 ❌23-B 違反（路徑 b 落地缺 contract test）→ G3 不放行。
> **G3 fall-back**（R-SD09-A-3）：dry-run 失敗 → 回 W2 修補 schema/index；W4 SOP §6-§8 仍可補完，但 DBA 親演阻塞。

---

### ── W4：PG production SOP §6-§8 補完（A 中半）+ perf machine 啟用（D 下半）──

**目標**：
- SOP §6 監控 + §7 RACI + §8 演練回顧補完
- perf machine 上架 + pgvector p95 baseline 鎖定
- 人類 DBA 親演（W4 中段必須完成；紅線 ❌21）

**逐項打勾**：
```
[  ] T4-A1 git tag sd_09_w3_g3_pass
[  ] T4-A2 SOP §6 監控補完（WAL lag dashboard / 連線數 alert / drift_log 30 天 SLA / dashboard 連結）
[  ] T4-A3 SOP §7 RACI 表補完（DBA / SRE / Tech Lead / PM 角色職責矩陣 + 切換時序 RACI + 緊急回滾 escalation 路徑）
[  ] T4-A4 SOP §8 演練回顧補完（W3 dry-run 整合 + DBA 親演 checklist + 30 天統計）
[  ] T4-A5 (**紅線 ❌21**) 人類 DBA 親演（≥ 1M 列 staging）：
       - DBA 親自跑 §4 三階梯 canary（10/50/100）
       - DBA 親自驗 §5 rollback 流程（含 PG dump → YAML import）
       - DBA 簽核 docs/06_quality/SD09_DBA_DryRun_Sign_W4.md（signed-off + 時間戳）
       - fall-back（R-SD09-A-2）：DBA 親演失敗 → W5 推遲至 SD_10，W6 仍可收尾文件與 mutation
[  ] T4-A6 補 tests/contract/test_pg_migration_sop_section_6_7_8.py（≥ 6 case）

# D 議題群下半：perf machine 啟用
[  ] T4-D1 (**SD m1 修復**) perf machine 上架 + 配置（依採購方案：self-hosted runner OR ssh 手動跑 pytest，副選項 W2 PM 拍板）
[  ] T4-D2 (**SD C4 修復**) tests/perf/test_pgvector_recall_perf.py 啟用：
       - 改用 `@pytest.mark.perf_machine_only` marker（取代 PG_REAL_ENABLED gate）
       - `pyproject.toml [tool.pytest.ini_options]` 新增 `addopts = "-m 'not perf_machine_only'"`（**SD-M3 修復**：專案無 pytest.ini，配置在 pyproject.toml；目前 markers 已有 pg_real/perf/benchmark，須補註冊 `perf_machine_only: 僅 perf machine 跑（ADR-SD09-003 §2.2）`；現無 addopts 為新增，需評估與 pg_real skip 行為不衝突）
       - 緊急路徑：採購未到位 → 維持 SKIP，pgvector p95 baseline 延 SD_10，**W4 G4 不阻塞**
[  ] T4-D3 perf machine 首次跑 7 次連續 + 鎖定 .perf_baseline.toml pgvector_recall_perf
[  ] T4-D4 季度校準排程設定（GitHub Actions schedule 每季首週末）
[  ] T4-D5 補 tests/contract/test_perf_three_track.py（≥ 3 case：CI 場景 / perf machine 場景 / 開發機 fall-back）
```

**G4 驗證**：
```bash
[  ] grep -E "^## §6\.|^## §7\.|^## §8\." docs/08_deployment/Production_Migration_SOP.md  # 3 行命中
[  ] ls docs/06_quality/SD09_DBA_DryRun_Sign_W4.md                          # 存在
[  ] git log --show-signature -1 -- docs/06_quality/SD09_DBA_DryRun_Sign_W4.md  # DBA 簽核驗證
[  ] python -m pytest tests/contract/test_pg_migration_sop_section_6_7_8.py -v   # ≥ 6 case 綠
[  ] grep -E "perf_machine_only" tests/perf/test_pgvector_recall_perf.py    # 命中
# QA-C5 修復（G4 殘漏）：以文件查詢取代未定義環境變數
[  ] [ -f docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md ] && git log --show-signature -1 -- docs/06_quality/SD09_Perf_Machine_Procurement_Eval.md > /dev/null 2>&1 && grep -E "pgvector_recall_perf" .perf_baseline.toml || echo "[delay_sd10 — procurement not approved or perf machine not yet active]"
[  ] python -m pytest tests/contract/test_perf_three_track.py -v            # ≥ 3 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,120 passed（+10）
```

> **G4 強制阻塞**：人類 DBA 親演 + 親簽未完成 → G4 不放行（紅線 ❌21）。
> **G4 fall-back**（R-SD09-A-2 / R-SD09-D-1）：DBA 親演失敗 → W5 延 SD_10；perf machine 採購延期 → pgvector baseline 延 SD_10，G4 不阻塞其他項目。

---

### ── W5：真實 PG production 上線（A 下半）──

**目標**：
- 雙條件齊備驗證（**同 process** trace_id GA + 30 天零 drift；ADR-SD09-001 §2）
- 真實 PG production 切換（yaml_only → both → db_only 三階梯，依 ADR-SD09-005）
- 人類 PM 親簽 release approval

**逐項打勾**：
```
[  ] T5-A1 git tag sd_09_w4_g4_pass
[  ] T5-A2 (**Arch-C3 + SD-C1/C3 + QA-M4 + Arch-M6 修復**) 雙條件齊備驗證（紅線 ❌20）：
       - **(1a) 可觀測性 GA（IObservabilityPort + trace_id ContextVar）**：30 天 nightly 全綠（SD_08 W4 起 2026-05-19 → 2026-06-18；Arch-M6 起算日 +1 修正）；取證 `python tools/observability_ga_check.py --window 30 --json | jq -e '.green_streak >= 30'`（QA-M4 新增工具）
       - **(1b) KB metric 觀察**：若議題 G 拍板 (a) PG 落地 → 取證 `psql -c "SELECT count(*) FROM kb_metrics WHERE window_start_at > now() - interval '30 day'"` > 0；若選 (b)/(c) → 改判 N/A 並以 emit_counter 抽樣行數佐證 KB metric 仍寫入（SD-C3 拆條件）
       - **(2) 30 天零 drift**（SD-C1 對齊 alembic 0013 真實 schema：detected_at + severity；drift_count/created_at 欄位不存在）：`SELECT count(*) FROM drift_log WHERE detected_at > now() - interval '30 day' AND severity != 'info'` 連續 30 天 = 0
       - 寫入 docs/06_quality/SD09_Cutover_Precondition_Check_W5.md
       - **multi-process trace_id GA 不計入 W5 條件**（延 W6 / SD_10；ADR-SD09-001 §2 + R-SD09-F-2）
[  ] T5-A3 真實 staging（≥ 1M 列）切換演練（依 SOP §4 三階梯 + ADR-SD09-005 閾值）：
       - 10% canary 24h 觀察
       - 50% canary 48h 觀察
       - 100% canary 7 天觀察
       - drift_log 零事件確認
[  ] T5-A4 人類 PM 親簽 release approval（signed-off / GPG）：
       - PM 親自確認 §1-§8 SOP 完整執行
       - PM 親自確認 SD09_DBA_DryRun_Sign_W4 + SD09_Cutover_Precondition_Check_W5
       - PM 簽核 docs/06_quality/SD09_PM_Release_Approval_W5.md
[  ] T5-A5 production 切換正式啟用（storage.mode = db_only）
[  ] T5-A6 (**SD C3 + QA M5 修復**) 補 tests/contract/test_cutover_precondition_verified.py（≥ 4 case）：
       - fixture 規範：30 筆 jsonl 行注入 `tmp_path/ac4_history.jsonl` + `drift_log` mock（仿 tests/contract/test_ac4_progress_check.py 模式）
       - case 1：雙條件齊備（30 天 nightly 全綠 + `severity != 'info'` 計數連續 30 天 = 0；SD-C1 對齊真實 schema）
       - case 2：任一天有 `severity in ('warn','critical')` 寫入 → 阻塞
       - case 3：nightly 紅線 5 次 → 阻塞
       - case 4：WAL lag classify_lag() 回傳 NORMAL + PM 簽核 commit signature 驗證成功（QA-M2 修復語意）
       - fixture 路徑（QA-M2）：`tests/contract/fixtures/cutover_precondition_double_check.json`（30 筆 nightly + drift 模擬）+ `cutover_precondition_pm_sign.gpg`

# fall-back（R-SD09-A-4，QA C4 修復）：雙條件未達 → 不切換 db_only，維持 both mode；W5 G5 改判 conditional pass；切換動作延 SD_10；ADR-SD09-001 §2.3 明訂例外條款
```

**G5 驗證**：
```bash
[  ] ls docs/06_quality/SD09_Cutover_Precondition_Check_W5.md               # 存在
[  ] ls docs/06_quality/SD09_PM_Release_Approval_W5.md                      # 存在
[  ] git log --show-signature -1 -- docs/06_quality/SD09_PM_Release_Approval_W5.md  # PM 簽核驗證
[  ] python -m pytest tests/contract/test_cutover_precondition_verified.py -v   # ≥ 4 case 綠
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # ≥ 2,123 passed（+3）
```

> **W5 強制交付**（紅線 ❌20 + ❌21 對齊）：(a) 雙條件齊備檢查通過 + (b) DBA 親演完成 + (c) PM 親簽。三項缺一不可。
> **W5 fall-back**（R-SD09-A-4）：雙條件未達 → conditional pass；db_only 切換延 SD_10。

---

### ── W6：SD_09 Migration Guide v1.0 + Sprint 收尾 + 四方審查（E 議題群完成）──

**目標**：
- 撰寫 `docs/08_deployment/SD09_Migration_Guide.md` v1.0
- AC Matrix 累計達 **39~41 條**（SD_07 19 + SD_08 10 + **SD_09 新增 9~12 條依路徑動態**）— **SA-C1 + QA-M1 修復**
- 四方審查（Architect / SA / SD / QA）APPROVED + PM 簽核
- gate_audit + risk_log 完成更新
- 滾動下沉：**擴寫** `sprint_history.md §1.5` SD_07 完整 W0~W6 紀錄（≥ 300 行；Architect C1 + SA M1 修復）

**逐項打勾**：
```
[  ] T6-1 git tag sd_09_w5_g5_pass（W6 收尾前快照）
[  ] T6-2 撰寫 docs/08_deployment/SD09_Migration_Guide.md v1.0（§1-§9 結構仿 SD08_Migration_Guide v1.0）
[  ] T6-3 (**C1 + QA C1 修復**) 撰寫 docs/03_testing/SD09_AC_Matrix.md v1.0 — **SD_09 新增 12 條**：
       - AC11×3 PG production（雙條件齊備 / DBA 親演 / PM 親簽）
       - AC12×2 mutation 擴展（GoalSynthesis ≥ 65% / Coordinator ≥ 60%）
       - AC13×1 AC4 升級（labeled PR 觸發 + 實測 recall ≥ 0.95）
       - AC14×2 perf machine（pgvector p95 鎖定 / 三軌切換）
       - AC15×1 滾動下沉（SD_07 §1.5 ≥ 300 行）
       - AC16×3 trace_id multi-process（**SD M1 修復 — 條件式條目**）：
         * 路徑 (a)：subprocess env 傳播 ≥ 2 case；總數 AC16=2，累計 40 條
         * 路徑 (b)：W3C parser ≥ 3 case；總數 AC16=3，累計 41 條
         * 路徑 (c)：延期決議紀錄 1 case；總數 AC16=1，累計 39 條
       - **累計**（**SA-C1 + QA-M1 修復 — 改條件式表述避免誤導**）：
         * 路徑 (a) → SD_07 19 + SD_08 10 + SD_09 11 = **40 條（≥ 35 門檻 ✅）**
         * 路徑 (b) → SD_07 19 + SD_08 10 + SD_09 12 = **41 條（≥ 35 門檻 ✅）**
         * 路徑 (c) → SD_07 19 + SD_08 10 + SD_09 10 = **39 條（≥ 35 門檻 ✅）**
       - T6-4 / T6-7 新增子任務（SA-C3）：更新 `sprint_history.md` §0 line 4/16 元數據為「目前：SD_08 + SD_09」
[  ] T6-4 (**Architect C1 + SA M1 修復**) 更新 CLAUDE.md：
       (a) 加入 SD_Improving_09 W0~W6 摘要區段
       (b) **擴寫**（非「下沉」）sprint_history.md §1.5 SD_07 完整 W0~W6 紀錄（≥ 300 行；素材：SD_Improving_07.md 各 Wave + SD07_Migration_Guide.md §1 + gate_audit.md §1-quinquies）
       (c) 滾動窗口 N=2 → 保留 SD_08 + SD_09（SD_06/SD_07 已下沉至 §1.4/§1.5）
       (d) 同步 [Architecture Snapshot] SSOT 區段（執行 python tools/snapshot_sync.py）；**Arch-M5 條件式更新**：若 PM #4=(b) Snapshot Rule 數 +1（路徑 b 已改 contract test 不加 Rule 8，**仍 7 kept**；Arch-M3 修復）；若 #5=(a) Port 數 9 → 10（IKbMetricStore）
       (e) 驗證 wc -l CLAUDE.md ≤ 400；**SD-m5**：W6 中段執行預檢，若 > 380 立即下沉 SD_07 摘要
[  ] T6-5 更新 docs/05_development/gate_audit.md §1-septies（新增 SD09-G0~G6 簽核紀錄）
[  ] T6-6 更新 docs/05_development/risk_log.md §15 — R-SD09-* 全數標 CLOSED 或移交 SD_10
[  ] T6-7 (**Architect C1 修復**) 更新 sprint_history.md v1.2：
       - **§1.5 SD_07 從摘要擴寫為完整 W0~W6 紀錄（≥ 300 行）**
       - §1.7 SD_Improving_09 補完（W0~W6 詳細紀錄）
       - §2 議題索引表新增 SD_09 對應條目（PG production / mutation 擴展 / perf 三軌 / trace_id multi-process / canary 三階梯）
[  ] T6-8 四方審查（Architect / SA / SD / QA 4/4 APPROVED）
[  ] T6-9 PM 簽核（場景 A：個人開發）
[  ] T6-10 撰寫 docs/04_planning/SD_Improving_10.md 大綱（W6 同步交付；觸發來源見 SD_09.md §0 SD_10 預告）
[  ] T6-11 (**QA-C4 修復 — 行數門檻統一**) contract test 更新 tests/contract/test_claude_md_budget.py：
       - N=2 窗口檢查更新為 SD_08 + SD_09（SD_06/SD_07 已下沉）
       - **新增 case**：驗證 sprint_history.md §1.5 SD_07 段落 **≥ 300 行**（與 G6 awk 驗證一致 — QA-C4 修正 v0.2 的 ≥ 200 行錯誤）
```

**G6 最終驗證**（**QA-M7 修復**：軟硬底線判定機制）：
- **2,125+ passed** = ✅ pass
- **2,120-2,124 passed** = ⏸ conditional pass，必產 `docs/06_quality/SD09_G6_Conditional_Report.md` 列出缺漏 case 並挪入 SD_10 backlog
- **< 2,120 passed** = ❌ REJECTED 不放行 G6

```bash
[  ] python -m pytest tests/ -q --tb=no | tail -3                           # 軟目標 ≥ 2,125 / 硬底線 ≥ 2,120 / 條件式判定
[  ] python -m pytest tests/equivalence/ -q --tb=no                         # 83/83 全綠（無變動）
[  ] PYTHONUTF8=1 lint-imports --config .importlinter                       # **7 kept**（Arch-M3 修復：路徑 b Rule 8 改 contract test 不增 importlinter Rule；任一路徑皆 7 kept）/ 0 broken
[  ] python tools/check_loc_budget.py                                       # violations=0
[  ] wc -l CLAUDE.md                                                        # ≤ 400
[  ] grep -rn "NOTE(SD_09)" autoclaude/ tests/ | wc -l                      # = 0
[  ] ls docs/08_deployment/SD09_Migration_Guide.md                          # 存在
[  ] ls docs/03_testing/SD09_AC_Matrix.md                                   # 存在（≥ 12 條）
[  ] ls docs/06_quality/SD09_DBA_DryRun_Sign_W4.md                          # 存在
[  ] ls docs/06_quality/SD09_PM_Release_Approval_W5.md                      # 存在
# QA-m1 修復：awk 排除空白行避免虛胖
[  ] awk '/^### 1\.5 SD_Improving_07/,/^### 1\.6 /{if(!/^[[:space:]]*$/) print}' docs/05_development/sprint_history.md | wc -l   # ≥ 300 行
[  ] grep -E "^### 1\.7 SD_Improving_09" docs/05_development/sprint_history.md   # 命中（SD_09 已補完）
[  ] ls docs/04_planning/SD_Improving_10.md                                 # 存在
[  ] python -m pytest tests/contract/test_claude_md_budget.py -v            # 17 case 綠（含新增 §1.5 ≥ 300 行驗證 — QA-C4 修復）
```

---

## 4. 波次間 Session 切換協議

每個 Wave 開始前：

```
我正在執行 SD_Improving_09 [W編號]（[波次名稱]）。

當前狀態：
- 測試基線：[當前 passed 數] / [skipped 數]
- 前一 Gate 已通過：G[n]
- 當前 Wave 目標：[複製 §3 Wave 目標清單]
- PM 拍板事項：[列出本 Wave 對應 §6 #N PM 決議]
- 對應 ADR：[列出本 Wave 對應 ADR-SD09-XXX]

請先執行 §0 前置確認：
python -m pytest tests/ -q --tb=no | tail -3
PYTHONUTF8=1 lint-imports --config .importlinter
python tools/check_loc_budget.py
wc -l CLAUDE.md

確認後依照 SD09_Execution_Guide.md W[n] 逐項打勾執行。
```

---

## 5. 緊急停止與回退協議

### 5.1 觸發條件對照表

| 觸發條件 | 立即執行 |
|---------|---------|
| equivalence 83 fixture 任一斷裂 | `git revert HEAD`；找 SA + QA 雙簽才可重啟 |
| importlinter broken | `git stash`；找 Architect 確認再重試 |
| 全測數量下降 | `git stash`；找出哪個測試被移除/跳過 |
| CLAUDE.md > 400 行 | 立即下沉至 sprint_history.md（紅線 ❌17）|
| W2 mutation 一次啟用 ≥ 2 active modules | `git revert HEAD`（紅線 ❌19）回單模組 |
| W3 未經 AI-Agent dry-run 即推進 W4 | `git revert HEAD`（紅線 ❌21）DBA 親演前置 |
| W4 perf machine 未經 PM 預算簽核即採購 | `git revert HEAD`（紅線 ❌22）回 W2 PM 簽核 |
| W5 雙條件未達即推進 db_only 切換 | `git revert HEAD`（紅線 ❌20）回觀察期 |
| W5 真實 staging：AI-Agent 演練 + DBA 親演 + PM 親簽 缺一不可（紅線 ❌21）| 切換禁止 / 回 W4（**Minor m3 修復**）|
| W3 議題 F 路徑 (b) 落地缺 contract test `test_trace_context_subprocess_env.py` W3C 區段 | `git revert HEAD`（紅線 ❌23-B；Arch-M3 修復；R22 命名一致性修復）|
| W0 PM 路徑拍板未完成前推進 W3 trace_id 實作 | `git revert HEAD`（紅線 ❌23-A）|
| 任何 3 個連續 commit 仍紅 | 停止當前 Wave，回退至前一 G-gate commit |

### 5.2 fall-back 矩陣（**QA C2/C3/C4 + 補強建議 2 修復**）

| Wave | 失敗點 | fall-back action | 影響 Gate | 影響測試基線 |
|------|--------|------------------|----------|-------------|
| W1 | GoalSynthesis mutation < 60% baseline | 產 Report + backlog；不阻塞 W2-W6；SD_10 接續 | G1 conditional pass | 維持 |
| W2 | Coordinator mutation < 60% baseline | 同 W1 | G2 conditional pass | 維持 |
| W2 | perf machine 採購 PM 預算未簽核 | 議題群 D 整體延 SD_10；W4 G4 不阻塞其他項目 | G2 不阻塞 | -4 case（perf marker 維持 deselect）|
| W2 | KB metric 落地失敗（若選 a） | 議題群 G 降級為 backlog，延 SD_10 | G2 不阻塞 | -2 case |
| W3 | AI-Agent dry-run 失敗（≥ 1M 列） | 回 W2 修補 schema/index；W4 SOP §6-§8 文件仍可補；阻塞 W4 DBA 親演 | G3 conditional pass | 維持 |
| W3 | trace_id multi-process 路徑 (b) 超 W3 估算 | W0 PM 改選 (a) 或延 SD_10；T3-F* 對應刪除 | G3 conditional pass | -3 至 -4 case |
| W4 | 人類 DBA 親演失敗 | W5 上線推遲至 SD_10；W6 仍可收尾文件 + mutation | G4 conditional pass | -3 case（T5-A* 延期）|
| W4 | perf machine 上架失敗 | pgvector baseline 延 SD_10；CI 維持 SKIP | G4 不阻塞 W5 PG 切換 | -3 case |
| W5 | 雙條件未達（可觀測性 GA OR drift_log 任一）| 不切換 db_only，維持 both mode；W5 G5 conditional pass；db_only 切換動作延 SD_10 | G5 conditional pass | 維持 |
| W5 | PM 親簽延期 | W6 文件交付仍可完成；正式上線延 SD_10 | G5 conditional pass | 維持 |

```bash
# 找到前一 Gate 的 commit
git log --oneline | grep "G[0-6]\|sd_09"

# 回退（確認無誤後）
git reset --hard <commit-hash>
```

---

## 6. 進度追蹤表

| Wave | 狀態 | 通過日期 | 測試基線 | PM 對應項 | 對應 ADR | 備注 |
|------|------|---------|---------|----------|---------|------|
| W0 | 📋 啟動日 2026-06-18+ | — | 2,094 → 預估持平 | (待 PM §6 拍板) | ADR-SD09-001~005 | SD_08 收尾 + 5 ADR + AC4 labeled PR + F/G 三方研究 + 主規劃升 v1.0 |
| W1 | 📋 待 W0 | — | ≥ 2,098（+4）| #2 mutation 排程 | ADR-SD09-002 | GoalSynthesisPlugin pilot 兩週 + TG 退出 nightly |
| W2 | 📋 待 W1 | — | ≥ 2,103（+5）| #3 perf 預算 + #5 KB | ADR-SD09-003 (+ G) | Coordinator pilot + perf machine 採購評估 + KB metric 落地若 (a) |
| W3 | 📋 待 W2 | — | ≥ 2,110（+7）/ 路徑 c -3 | #4 trace_id 路徑 + #7 canary | ADR-SD09-001 + 004 + 005 | SOP §4-§5 + AI-Agent dry-run + trace_id multi-process（依路徑）|
| W4 | 📋 待 W3 | — | ≥ 2,120（+10）| #8 DBA 親演排程 | ADR-SD09-001 + 003 | SOP §6-§8 + perf machine 啟用 + 人類 DBA 親演 |
| W5 | 📋 待 W4 | — | ≥ 2,123（+3）| #1 上線時程 | ADR-SD09-001 | 真實 PG production 上線 + PM 親簽 |
| W6 | 📋 待 W5 | — | **≥ 2,125 軟 / ≥ 2,120 硬底線**（+2）| #6 啟動日 | — | Migration Guide v1.0 + 四方審查 + SD_07 擴寫 + SD_10 大綱 |

---

## 7. 前置已就緒項目（無需重做）

| 項目 | 狀態 | 說明 |
|------|------|------|
| PG 三層 schema + advisory lock | ✅ | SD_06 W3 G3（alembic 0007-0014）|
| IEmbedder/IVectorSearch + 雙 adapter + CircuitBreaker | ✅ | SD_06 W3 G3 |
| dual_state drift + drift_log 365 天 partition | ✅ | SD_06 W5 G5 |
| ConfigResolver 4 層 + RBAC + audit_log | ✅ | SD_06 W5 G5 |
| IObservabilityPort + LocalLogger + trace_id ContextVar + KB metric | ✅ | SD_08 W4 G4（同 process 邊界，30 天觀察期起算 2026-05-18）|
| PgHealthMonitor + WAL lag 三閾值 | ✅ | SD_08 W5 G5（adapter 214 LOC）|
| Production_Migration_SOP.md §1-§3 草案 | ✅ | SD_08 W5 G5（W3-W4 補完 §4-§8）|
| .perf_baseline.toml 3 場景鎖定 | ✅ | SD_08 W5 G5（pgvector 延 perf machine）|
| ADR-SD08-005 雙軌制 + 雙條件 | ✅ | SD_08 W5 G5（ADR-SD09-001 接續）|
| SD_06 完整下沉 §1.4 | ✅ | SD_08 W6 G6 |
| SD_07 摘要保留 CLAUDE.md + §1.5 摘要 | ✅ | 待 SD_09 W6 擴寫至 §1.5 完整 |

---

## 8. 關鍵風險即時監控（每 Wave 末複查）

```
[ Wave W0 ] R-SD08-D-1 / PM-#3 移交確認；F + G 三方研究 + PM 拍板完成
[ Wave W1 ] R-SD09-B-1 — GoalSynthesis ≥ 60% baseline？wall time ≤ 40 min？
[ Wave W1 ] R-SD09-B-2 — TG 已退出 nightly？單 active module 規則維持？
[ Wave W2 ] R-SD09-D-1 — perf machine PM 預算 signed-off？採購時程不阻塞 W4？
[ Wave W2 ] R-SD09-B-1（Coordinator）— ≥ 60% baseline？單檔精準 mutation 路徑？
[ Wave W2 ] R-SD09-G-1（若 G 落地）— IKbMetricStore port 設計 + yaml_only fall-back？
[ Wave W3 ] R-SD09-A-1 / A-3 — AI-Agent dry-run（≥ 1M 列）成功？drift_log 零事件？
[ Wave W3 ] R-SD09-F-1 — trace_id multi-process 路徑落地時程不超估算？
[ Wave W3 ] R-SD09-F-2 — multi-process 30 天觀察視窗不計入 W5 條件？
[ Wave W4 ] R-SD09-A-2 — 人類 DBA 親演 W4 中段完成？簽核 signed-off？
[ Wave W4 ] R-SD09-D-1 — perf machine 上架時程？pgvector p95 baseline 鎖定 OR 延 SD_10？
[ Wave W5 ] R-SD09-A-1 / A-4 — 雙條件齊備？人類 PM 親簽 signed-off？
[ Wave W6 ] — SD_07 §1.5 擴寫 ≥ 300 行？SD_10 大綱就位？四方審查 4/4 APPROVED？
```

---

**對應參考文件**：
- [SD_Improving_09.md](../04_planning/SD_Improving_09.md) v0.2 → v1.0 — 主規劃文件
- [SD08_Execution_Guide.md](SD08_Execution_Guide.md) v1.0 — 前置 Sprint 執行範本
- [SD_Improving_08.md](../04_planning/SD_Improving_08.md) v1.0 — 前置 Sprint 主規劃
- [SD08_Migration_Guide.md](../08_deployment/SD08_Migration_Guide.md) v1.0 §5 SD_09 延期清單 + §7 L1~L6
- [Production_Migration_SOP.md](../08_deployment/Production_Migration_SOP.md) v0.1 — §1-§3（SD_09 W3-W4 補完 §4-§8）
- [ADR-SD08-005-pg-production-dual-track.md](../04_planning/ADR/ADR-SD08-005-pg-production-dual-track.md) — PG 雙軌制
- [ADR-SD09-001~005](../04_planning/ADR/) — SD_09 5 條 ADR（W0 落地）
- [risk_log.md §14](risk_log.md) — SD_08 風險（§15 W0 同步建立）
- [gate_audit.md §1-sexies](gate_audit.md) — SD_08 簽核（§1-septies W0 同步建立）
- [sprint_history.md](sprint_history.md) v1.1 — SD_03~SD_06（v1.2 W6 末擴寫 §1.5 SD_07）

---

**文檔元數據**：
- 文件版本：**v0.2（首輪四方審查修復 — 13 Critical + 22 Major + 15 Minor 全數處理）**
- 建立日期：2026-05-19（同步主規劃 2026-05-18，落差 1 日）
- 對應規劃版本：SD_Improving_09.md v0.2 → v1.0
- G0 啟動日：**2026-06-18 或之後**（最晚觀察期結束日 2026-06-17 + ≥ 1 工作日提前期）
- 維護者：Tech Lead + PM 共同維護
