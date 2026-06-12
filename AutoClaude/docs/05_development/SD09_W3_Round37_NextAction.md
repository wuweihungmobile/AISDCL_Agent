# SD_09 W3 Round 37 — Zero-Trust Audit nightly 機制十四度閉環 + 軸 B 方向訂正里程碑

| 項目 | 內容 |
|------|------|
| Round | 37（接續 R36 十三度閉環） |
| 日期 | 2026-05-28（CST 11:31→11:37） |
| 觸發 | 用戶要求「徹底解決 + PM + 對應 Agent + 完全不信任 + 全面徹底補做 + 確認 nightly 完整測試與正確結果 + 加速進入 SD10 + 執行軸 B 直接觸發 unique sha」 |
| 結果 | ✅ **OVERALL CONDITIONAL PASS** — 機制+結果正確（0 P0 / 0 P1），軸 B 方向經獨立查證確認錯誤（2 P2 已修） |
| Audit Agents | general-purpose（全能 Architect/SA/SD/QA，zero-trust）+ 主 agent 雙重獨立驗證 |

---

## 1. 第 34 跑 nightly 取證（run_id=113110）

`logs/nightly_2026-05-28_113110.log` → `END nightly summary: mutation=0 pg-e2e=0 perf=2(WARN) drift=0 obs=0` **5 綠 + 1 合法 WARN**

| Stage | rc | elapsed | 說明 |
|-------|----|---------|------|
| Docker-PG-bring-up | 0 | 0.370s | 沿用既有 autoclaude_pg |
| mutation-test | 0 | 4:34.443 | mutmut bitmask bit0=0；kill_rate=76.51%（killed 114/survived 35/suspicious 0）|
| pg-e2e + AC4 | 0 | 12.413s | p95 status=observing；tolerant_streak=7/14 |
| perf-baseline | **2 (WARN)** | 54.123s | token_halt_roundtrip 0.5→0.8ms +59.5%；samples=7<20 undersampled BLOCK→WARN（ADR-SD08-003 §2.6 v1.1）|
| drift_log-scan | 0 | 0.436s | severity!='info'=0 |
| observability-snapshot | 0 | 0.587s | — |

- source_sha256=20940e1b903dc19d 維持；tail7 non-None=5 筆僅 2 unique → `should_lock reject reason=sha_partial_duplicate` 正確阻 lock
- 觀察期 delta=0 stage=0（M-05 同 UTC 日去重，本輪 5/28 03:35 UTC 覆寫同日先前跑）：#1=7/7 #2=7/14 #3=6/30 obs=6/30 維持 R36 進帳

---

## 2. Zero-Trust Audit 發現 + 修復（2 P2）

### P2-1 — R36「perf 全綠 / 6 stage 全綠」過度聲稱（紀律 #3 取證精確性）

**證據**：R37 同源碼（sha 20940e1）同 baseline 下 perf=2 WARN（token_halt +59.5%），非 R36 的 perf=0（token_halt -3.7%）。證明 perf 在 undersampled baseline（`.perf_baseline.toml` samples=7<20）下隨**亞毫秒 jitter 在 0↔2 間擺動**，perf=0 為偶發非穩態。

**修復**：[CLAUDE.md](../../CLAUDE.md) line 4 + metadata 改述為「perf 隨亞毫秒 jitter 在 0↔2 擺動，皆合法非穩態」。

### P2-2 — 軸 B「churn 源碼衝 unique sha / 衝 80%」方向錯誤且機制上不可行

**4 項獨立證據**（主 agent + 子 agent 雙重驗證一致）：

1. `compute_source_sha256`（[mutation_baseline_lock.py:227](../../tools/mutation_baseline_lock.py#L227)）由 `autoclaude/plugins/token_guard/*.py` **源碼**計算 → **加測試 case 不改 sha**（tests/ 不在 plugin 目錄）。
2. `append_history` M-05 對「同 module + 同 UTC date」去重只留每日最後一筆 → **單一 session 無論改幾次源碼重跑當日只 +1 unique sha**，「+3 in one session」機制上不可能。
3. 現況 tail7 non-None=5 筆僅 2 unique（5208cff×3 + 20940e1×2）→ 被 `sha_partial_duplicate` 正確阻鎖；最早解鎖約 **2026-06-02~03**（需未來連續多日各有相異源碼 sha）。
4. **窮舉 168/300 組實證** `should_compact_decision`（[thresholds.py:36](../../autoclaude/plugins/token_guard/thresholds.py#L36)）恆等於 `return token_pct >= threshold`，`in_correction_loop`/`correction_history_len` 對輸出零影響 → backlog #125/126/127（L43-44 correction-loop 分支）為**等價變異（equivalent mutants）任何測試殺不掉**。

**結論**：kill_rate ~76% 為**等價變異天花板**（R30→R31 加 64 case 對 kill_rate 無實質提升已佐證）；刻意 churn 源碼衝 unique sha **違反紀律 #12 反作弊精神**（#12 本意防同 commit 重跑騙鎖，要求自然多日演進）。

**修復**：本檔 + [sprint_history.md §1.7.3 R37](sprint_history.md) + CLAUDE.md 記錄方向訂正；§1.7.6 G0 條件「軸 B 加速關鍵」改述。

---

## 3. 收斂判定（QA 覆審 PASS）

| 指標 | R36 | R37 | 收斂 |
|------|-----|-----|------|
| pytest passed | 2,716 | 2,716（87.93s）| PASS |
| pytest skipped | 122 | 122 | PASS |
| importlinter | 7 kept | 7 kept | PASS |
| LOC violations | 0 | 0（total=15117）| PASS |
| CLAUDE.md 行數 | 382 | 383 ≤ 400 | PASS |
| 源碼異動 | 無 | 無（僅 3 受版控 artifact + 文件）| PASS |

**收斂未破壞** — 本輪無源碼異動，純文件方向訂正。

---

## 4. PM 決策建議（待拍板 — 解鎖 #1 與進 SD10 的關鍵岔路）

| 選項 | 內容 | 取捨 |
|------|------|------|
| **A（建議）** | 接受 76% 為 token_guard 真實水位（ADR-SD09-009 ±2pp → 68% effective threshold，kill_rate streak 已 7/7 達標）；下修或維持 80% 為長期非 G0 硬目標 | 立即解除 #1 唯一瓶頸的「假性卡關」，加速進 SD10；符合業界 mutation testing 對等價變異的標準處理 |
| **B** | 維持需 unique sha 解 #1，靠 W1 自然多日 commit 演進累積相異 sha（約 6/2~6/3）| 不犧牲標準，但 G0 受時間閘門牽制；**絕不可人工 churn 源碼** |

> 無論 A/B，**禁止為衝 sha 刻意改源碼**（違紀律 #12）。

---

## 5. 4 軸並行下一步規劃（R37 訂正後）

| 軸 | 動作 | 主檔案 | 時機 | 狀態 |
|----|------|--------|------|------|
| **A 背景觀察期** | schtasks 02:00 持續跑；#2 ac4 7/14、#3 drift/obs 6/30 待自然累計至門檻 | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) | 每日 | 🟢 加速軌道內 |
| **B（訂正）** | **停止「加 case/churn 源碼衝 unique sha」**；改為提請 PM 拍板選項 A/B；若 B 則 #1 靠 W1 自然 commit 解 | PM 拍板 + [SD_Improving_09.md](../04_planning/SD_Improving_09.md) | ≤ 2026-06-02 | 🟡 待 PM 決策 |
| **C PM 拍板** | 10 ADR 全 ACCEPTED；新增「軸 B 方向訂正 + 76% 真實水位」待拍板 | — | 本輪後 | 🟡 1 項待拍板 |
| **D W2-W6 預備** | Production_Migration_SOP §6-§8 預研 + kb_metric_store port 設計 + jsonl append-only sub-recorder 設計（SD_10 backlog）| docs/08_deployment/、autoclaude/core/ports/ | 持續 | 🟢 持續 |

**下一步優先序**：① PM 拍板選項 A/B（解 #1 假性卡關）；② #2/#3 觀察期自然累計（6/8、6/24）；③ 三觀察期全達標 → G0 啟動進 W1。

---

## 6. 專案成熟度評估

| 維度 | R36 | R37 | 趨勢 |
|------|-----|-----|------|
| nightly 機制成熟度 | A+（36 輪+十三度閉環）| **A+（37 輪+十四度閉環）** | → |
| audit 自我反證能力 | 反證自身框架誤判 | **反證專案自身 R36 軸 B 規劃方向 + perf 全綠過度聲稱** | ↑ |
| 文件治理 | CLAUDE.md 382 / 0 違規 | 383 / 0 違規 + R37 方向訂正 | ↑ |
| 收斂保護 | 0 regression | 0 regression（無源碼異動）| → |

**結論**：A+ 級成熟度持續；R37 最大價值為**破除軸 B 迷思、釐清 #1 lock 為時間閘門 + 等價變異天花板、給 PM 明確決策路徑**，實質加速進入 SD10。

---

## 7. 變更檔案清單

### 文件更新
- [CLAUDE.md](../../CLAUDE.md) — line 4（R37 header + P2-1/P2-2 訂正）+ metadata v5.1
- [sprint_history.md](sprint_history.md) — §1.7.3 R37 條目 + §1.7.5 表 + §1.7.6 G0 條件訂正
- [SD09_W3_Round37_NextAction.md](SD09_W3_Round37_NextAction.md) — 本檔

### Nightly 自動採集副作用（受版控）
- `.drift_log_history.jsonl` / `.perf_history.jsonl` / `perf_regression_comment.md` — 第 34 跑 record

**無源碼異動。**

---

**結論**：✅ **R37 十四度閉環 CONDITIONAL PASS — nightly 機制與結果均正確，軸 B 方向訂正落地**。修復 P2-1（perf 敘事）+ P2-2（軸 B 方向，4 證據）；收斂未破壞（pytest 2,716 持平）；提請 PM 拍板選項 A（接受 76% 真實水位）以加速進 SD10。
