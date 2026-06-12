# SD_09 W3 Round 38 — nightly 機制十五度閉環 + PM 拍板選項 A ACCEPTED + 軸 B 方向訂正落地

| 項目 | 內容 |
|------|------|
| Round | 38（接續 R37 十四度閉環）|
| 日期 | 2026-05-28（CST 13:43→13:49，run_id=134308）|
| 觸發 | 用戶要求「徹底解決 + 派 PM 與對應 Agent + 完全不信任 zero-trust audit + 全面徹底補做 + 確認 AutoClaude_Nightly 可完整測試與正確結果 + 加速進入 SD10 + 執行軸 B 選項 A」|
| 結果 | ✅ **OVERALL CONDITIONAL PASS** — 0 P0 / 1 P1 / 2 P2 / 1 NOTE（全部已修或列 backlog）|
| Agents | PM Agent（拍板選項 A）+ Architect/SA/SD/QA 全能 Agent（zero-trust audit）+ 主 agent 獨立覆核（trust-but-verify）|

---

## 1. 第 35 跑 nightly 取證（run_id=134308）

`logs/nightly_2026-05-28_134308.log` → `END nightly summary: mutation=0 pg-e2e=0 perf=2 drift=0 obs=0` **5 綠 + 1 合法 WARN**

| Stage | rc | elapsed | 說明 |
|-------|----|---------|------|
| Docker-PG-bring-up | 0 | 0.374s | 沿用既有 autoclaude_pg |
| mutation-test | 0 | 5:09.878 | mutmut bitmask bit0=0；kill_rate=76.17%（killed 113 / survived 35 / suspicious 1）|
| pg-e2e + AC4 | 0 | 13.104s | p95 status=observing；tolerant_streak=7/14 |
| perf-baseline | **2 (WARN)** | 56.544s | decide_correction +15.1% 本應 BLOCK，samples=7<20 undersampled BLOCK→WARN（ADR-SD08-003 §2.6 v1.1）；token_halt 0.5→0.8ms sub-ms jitter |
| drift_log-scan | 0 | 0.484s | severity!='info'=0 |
| observability-snapshot | 0 | 0.628s | — |

- kill_rate=76.17% = (113+0.5×1)/149 = 0.761744…，與 `.mutation_history.jsonl` 最新筆完全一致（calc_kill_rate 已實作 ADR-SD09-009 0.5×suspicious 半 kill）
- source_sha256=20940e1b903dc19d；tail7 non-None=5 僅 2 unique → `should_lock reject reason=sha_partial_duplicate` 正確阻 lock（紀律 #12 預期）
- 觀察期 delta=0 stage=0（M-05 同 UTC 日去重）：#1=7/7 #2=7/14 #3=6/30 obs=6/30 維持 R36 進帳

---

## 2. PM 拍板（選項 A ACCEPTED）

派 PM Agent 獨立審議 + 親自讀 `autoclaude/plugins/token_guard/thresholds.py:36` 覆核等價變異論點 → **同意選項 A**，落地 [ADR-SD09-009 v1.1 §11](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md)：

| 決議 | 內容 |
|------|------|
| **76% 真實水位** | 接受 token_guard mutation kill_rate ~76% 為真實水位（等價變異天花板）。R38 kill_rate=76.17% > 68% effective threshold，streak 7/7 → **觀察期 #1 的 kill_rate 條件已正式達標** |
| **80% 降級** | 80% 不再是 G0 硬目標，下修為長期非 G0 硬目標（SD_10+ 重構 should_compact_decision 消等價變異再評估）|
| **#1 唯一剩餘瓶頸** | unique source_sha256 條件為**時間閘門**（紀律 #12），靠自然多日 commit 累積相異 sha（約 2026-06-02~03），**禁人工 churn 源碼** |

**等價變異論證（PM + audit 雙重獨立驗證屬實）**：`should_compact_decision` 通過 `token_pct < threshold` guard 後所有路徑回 True，`in_correction_loop`/`correction_history_len` 對輸出零影響 → 恆等 `return token_pct >= threshold` → backlog #125/126/127 為等價變異不可殺。

---

## 3. Zero-Trust Audit 發現 + 修復

| ID | 級 | 視角 | 根因 / 修法 | 狀態 |
|----|----|------|------------|------|
| **P1-R38-1** | P1 | SA/文件治理 | commit `0169b96`「W1 同 PR 落地全 7 任務」已 merge main 且改 production tools，但 CLAUDE.md 仍稱「W0 收尾期」→ 敘事補述「軸 B/W1 部分提前落地 commit 0169b96，per §3.0 4 軸框架」消歧義 | ✅ 已修 CLAUDE.md |
| **P2-R38-1** | P2 | QA | 跨文件數字並存：ADR §11/Guide 引用 R37 76.51%（114/susp0）vs R38 76.17%（113/susp1），皆 >68% 結論不變 → CLAUDE.md/metadata 標明輪次 | ✅ 已修 |
| **P2-R38-2** | P2 | SD | `.mutmut-cache` bind-mount 本地殘留 2 份，本輪未污染（mutmut Docker 內跑 + cache cleared）→ 列 SD_10 backlog 清理 | 📋 SD_10 backlog |
| **NOTE-R38-1** | NOTE | Arch | 80% 降級對齊等價變異天花板方向正確；SD_10 重構後再評估 | — |

**ADR-SD09-009 文件 drift 修復**：標頭 line 6 已是 ACCEPTED v1.0（Round 14 拍板）但正文 §3.2/§6/版本紀錄停留 PROPOSED → PM Agent 同步為 ACCEPTED；釐清「政策 ACCEPTED + 實作已於 W1 PR commit `0169b96` 落地」（calc_kill_rate 加 0.5×suspicious + should_lock 加 EXTRA_TOLERANCE=0.02 + ≥5 case test）。

---

## 4. 四大技術主張獨立查證（均屬實）

| 主張 | 結論 | 證據 |
|------|------|------|
| A. should_compact_decision 等價變異天花板 | ✅ 屬實 | 窮舉所有路徑回 True（thresholds.py:36-45）|
| B. calc_kill_rate 已實作 0.5×suspicious | ✅ 屬實 | (113+0.5)/149=0.7617 與 jsonl 一致（mutation_baseline_lock.py:140）|
| C. #1 unique sha 時間閘門非缺陷 | ✅ 屬實 | tail7 僅 2 unique 正確阻鎖（紀律 #12 設計預期）|
| D. perf 隨亞毫秒 jitter 在 0↔2 擺動 | ✅ 屬實 | 上輪 decide +9.1% 綠 → 本輪 +15.1% 黃，非穩態 |

---

## 5. 收斂判定（QA 覆審 PASS — 實跑非引述）

| 指標 | R37 | R38 | 收斂 |
|------|-----|-----|------|
| pytest passed | 2,716 | 2,716 | PASS |
| pytest skipped | 122 | 122 | PASS |
| importlinter | 7 kept | 7 kept | PASS |
| LOC violations | 0 | 0（total=15117）| PASS |
| CLAUDE.md 行數（wc -l）| 382 | 382 ≤ 400 | PASS |
| CLAUDE.md 最長行 | ≤ 800 cp | line4=761 / 無 >800 | PASS |
| 源碼異動 | 無 | 無（僅文件 + 3 受版控 artifact）| PASS |

**收斂未破壞** — 本輪純文件決策與訂正，無源碼異動。

---

## 6. 4 軸並行下一步規劃（R38 拍板後）

| 軸 | 動作 | 主檔案 | 時機 | 狀態 |
|----|------|--------|------|------|
| **A 背景觀察期** | schtasks 02:00 持續跑；#1 unique sha 待自然多日 commit（~6/2~3）、#2 ac4 7/14（達標 6/8）、#3 drift/obs 6/30（達標 6/24）累計至門檻 | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) | 每日 | 🟢 加速軌道內 |
| **B（已訂正）** | ✅ W1 已落地（commit 0169b96）+ R38 方向訂正完成。**停止人工 churn 衝 sha**；#1 unique sha 靠自然多日 commit 解 | [ADR-SD09-009 §11](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md) | 已完成 | ✅ 訂正落地 |
| **C PM 拍板** | ✅ 選項 A ACCEPTED（76% 真實水位 + 軸 B 訂正）；11 ADR 全 ACCEPTED，無待拍板項 | ADR-SD09-009 v1.1 | 本輪完成 | ✅ 完成 |
| **D W2-W6 預備研究** | Production_Migration_SOP §6-§8 預研 + kb_metric_store port 設計（ADR-SD09-006）+ jsonl append-only sub-recorder 設計（SD_10 backlog）+ multi-process trace_id 9 處 mapping + perf machine 三方案評估 | docs/08_deployment/、autoclaude/core/ports/ | 持續 | 🟢 持續 |

**下一步優先序**：① #2 ac4 自然累計至 6/8 達標；② #1 unique sha 靠自然多日 commit 至 ~6/2~3；③ #3 drift/obs 至 6/24 達標 → 三觀察期全達標 → G0 啟動（最遲 2026-06-26）進 W1 正式 Wave。

---

## 7. SD09_Execution_Guide.md 未執行項目現況

專案仍在 W0 收尾期（軸 B/W1 已部分提前落地）。G0 前置 DoD：

- **#1 mutation**：✅ kill_rate 條件達標（76.17% > 68% effective、streak 7/7）；唯一剩餘 unique sha 時間閘門（~6/2~3）
- **#2 AC4**：7/14（達標日 2026-06-08）
- **#3 drift**：6/30（達標日 2026-06-24）
- 其餘 DoD（ADR PM 核准 / branch / gate_audit + risk_log 骨架）W0 已完成

W1~W6 正式 Wave 因 G0 受三觀察期牽制尚未啟動（軸 B/W1 mutation 補測 PR 已提前落地為例外）。

---

## 8. 變更檔案清單

### 文件更新
- [CLAUDE.md](../../CLAUDE.md) — line 4（R38 header + W0/W1 消歧義 + 選項 A ACCEPTED，761 cp ≤ 800）+ metadata v5.2
- [ADR-SD09-009](../04_planning/ADR/ADR-SD09-009-mutmut-suspicious-policy.md) — 升 v1.1 + 新增 §11（等價變異天花板 / 76% 真實水位）+ §3.2/§6/版本紀錄同步 ACCEPTED（PM Agent）
- [SD09_Execution_Guide.md](SD09_Execution_Guide.md) — §0.1/§0.2/§3.0.1/§3.0.3 更新（PM Agent）
- [sprint_history.md §1.7.3 R38](sprint_history.md) — R38 條目
- [SD09_W3_Round38_NextAction.md](SD09_W3_Round38_NextAction.md) — 本檔

### Nightly 自動採集副作用（受版控）
- `.drift_log_history.jsonl` / `.perf_history.jsonl` / `perf_regression_comment.md` — 第 35 跑 record

**無源碼異動。**

---

**結論**：✅ **R38 十五度閉環 CONDITIONAL PASS — PM 拍板選項 A ACCEPTED 里程碑**。接受 76% 真實水位 → 觀察期 #1 kill_rate 條件正式達標 → 解除假性卡關 → 加速進 SD10；軸 B 方向訂正落地（ADR-SD09-009 v1.1 §11）；ADR 文件 drift 全修；收斂未破壞（pytest 2,716 持平）。下一步：三觀察期靠背景 schtasks + 自然多日 commit 累計至門檻（最遲 6/24）→ G0 啟動。
