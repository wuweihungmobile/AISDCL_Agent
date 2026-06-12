# SD_09 W3 Round 31 — Zero-Trust Audit nightly 機制八度閉環 + R30 取證敘述訂正 + mutmut variance protection

| 項目 | 內容 |
|------|------|
| Round | 31（接續 R30 七度閉環） |
| 日期 | 2026-05-27（CST 22:00） |
| 觸發 | 用戶要求「徹底解決 + PM + 對應 Agent + 完全不信任 + 全面徹底補做 + 確認 nightly 完整測試與正確結果」 |
| 結果 | ✅ **OVERALL CONDITIONAL PASS** — 5 大修復全交付 + 收斂未破壞 + R30 取證敘述訂正 |
| Audit Agents | Architect/SA/SD/QA 全能（zero-trust + 修復 + QA 三段式） |

---

## 1. 第 27 跑 nightly 取證

| 指標 | 第 26 跑（R30, 21:18）| 第 27 跑（R31, 21:52）| 趨勢 |
|------|----------------------|----------------------|------|
| Elapsed | 6:09 | 5:49 | -20s |
| mutation rc | 0 | 0 | PASS |
| pg-e2e rc | 0 | 0 | PASS |
| perf rc | 2 (WARN) | 2 (WARN) | 持平（亞毫秒 jitter）|
| drift rc | 0 | 0 | PASS |
| obs rc | 0 | 0 | PASS |
| kill_rate | **85.57%**（killed 124 / survived 18 / suspicious 7）| **74.83%**（killed 109 / survived 35 / suspicious 5）| **-10.74pp 同 sha 反證 outlier** |
| AC4 p95 | 53.12ms | 54.99ms | < 60ms tolerant 穩定 |
| source_sha256 | 20940e1b903dc19d | 20940e1b903dc19d | **同 sha**（plugin 未變動）|
| 觀察期累計 | mutation=6/7 ac4=6/14 obs=5/30 drift=5/30 | 6/7 6/14 5/30 5/30（delta=0 全部，UTC date dedup）| 待跨 5/28 UTC 進帳 |

---

## 2. Zero-Trust Audit 發現 + 修復

### P1-R31-1 — R30 commit 取證敘述「+10.40pp 大幅躍升」概括聲稱不嚴謹（紀律 #3 邊界違反）

**證據**：R30 commit (`c2b98a6`) 宣稱「W1 補測對 mutmut survived 殺傷實證有效」；本輪同 commit、同 sha、cache fresh、僅 34 分鐘後復跑 → kill_rate 跌至 74.83%（回到 R28~R29 baseline 74-75% 水位）→ R30 +10.40pp 純屬 mutmut suspicious classification non-determinism。

**修復**：[sprint_history.md §1.7.3 R30](sprint_history.md) 段落末追加 blockquote 訂正註記，明示 W1 補測對 kill_rate 影響統計接近 0；實質價值在 +64 case 形式覆蓋 + pytest 規模擴張 + 未來源碼變更時殺傷承載力。

### P1-R31-2 — jsonl dedup 讓 same-sha multi-run variance 不可見（紀律 #12 機制缺口）

**證據**：`.mutation_history.jsonl` M-05 same UTC date dedup → R30 record 已被本輪覆寫，**今日 85.57% vs 74.83% variance 永久遺失於 jsonl**（仍存於 nightly log）；下游 baseline_lock tail 7 取「該日最後一跑」無法反映 same-sha variance。

**修復**：
- [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) 新增 `compute_consistency_warning(history, module, threshold=0.03) -> tuple[bool, str]` 47 行；main() 出口 stderr WARN 不阻斷 lock
- [tests/tools/test_mutation_baseline_lock.py](../../tests/tools/test_mutation_baseline_lock.py) 新增 **6 case**（high/low variance / different sha / module filter / missing sha / custom threshold）
- [Nightly_Forensic_Discipline.md §紀律 #12](../06_quality/Nightly_Forensic_Discipline.md) 補「R31 強化條目」

**設計限制（同意 SD_10 backlog）**：本機制對「未來新增 record」有效；對「今日已被 dedup 覆寫」的歷史 variance 無能為力，需 SD_10 補 append-only sub-jsonl recorder 才能徹底解。

### P2-R31-1 — perf token_halt_roundtrip 亞毫秒 jitter 標籤

**修復**：[tools/perf_regression_check.py](../../tools/perf_regression_check.py) `emit_annotation()` WARN level + `|baseline - current| < 1.0` ms → 末加 `(sub-ms jitter range)` 標籤，避免 PR comment 「+84.9%」誤導。

### P2-R31-2 — observation_p95 streak=0 設計預期註記

**修復**：[sprint_history.md §1.7](sprint_history.md) 觀察期 #2 補一行：「按 ADR-SD09-008 v0.4，observation_streak (50ms 軌) 不影響 G0；strict_streak (60ms 軌) 為唯一升級指標，目前 6/14」。

### 附加 — CLAUDE.md status header R31 更新

**修復**：[CLAUDE.md](../../CLAUDE.md) line 4 改述「R31 nightly 機制八度閉環 + R30 取證敘述訂正 + mutmut variance protection 落地」；維持 382 行 ≤ 400 ≤ 800 char/line 全合規。

---

## 3. 收斂判定（QA 獨立驗證）

| 指標 | R30 基線 | R31 實測 | Δ | 收斂 |
|------|---------|---------|---|------|
| pytest passed | 2,707 | **2,713** | **+6** (新增 consistency case) | PASS |
| pytest skipped | 122 | 122 | 0 | PASS |
| importlinter | 7 kept | 7 kept | 0 | PASS |
| LOC violations | 0 | 0 | 0 | PASS |
| CLAUDE.md 行數 | 382 | 382 | 0 | PASS |
| CLAUDE.md long line ≤ 800 cp | 0 violation | 0 violation | 0 | PASS |
| NOTE(SD_09) in code | 0 | 0 | 0 | PASS |
| compute_consistency_warning（3 場景）| N/A | A=True / B=False / C=False | NEW | PASS |
| jsonl 寫入邏輯 | M-05 dedup 不變 | M-05 dedup 不變 | 0 | PASS |
| perf CLI 介面 | OK | OK | 0 | PASS |

**收斂狀態：未破壞** — 所有 hard 指標完全持平或進帳（+6 test），新增機制經 3 場景驗證符合設計意圖。

---

## 4. 14 條紀律合規矩陣（R31）

| # | 紀律 | R30 | R31 |
|---|------|-----|-----|
| 1 | stage rc 區分 | PASS | PASS |
| 2 | 完整統計 | PASS | PASS |
| 3 | PASS 聲稱引 RunId log:L | CONDITIONAL（R30 commit）| **PASS**（已訂正）|
| 4 | 驗證鏡子被驗證 | PASS | PASS |
| 5 | 跨工具數字對齊 | PASS | PASS |
| 6 | 採集寬鬆 vs 升級嚴格分軌 | PASS | PASS |
| 7 | cache fresh | PASS | PASS |
| 8 | .sh LF 行尾 | PASS | PASS |
| 9 | Docker SKIP 跨 stage 一致 | PASS | PASS |
| 10 | fallback jsonl 可區分 | PASS | PASS |
| 11 | latest log pointer 完整 | PASS | PASS |
| 12 | mutation history sha + 7 unique | PARTIAL（dedup 缺口）| **強化 PASS**（新增 multi-run variance WARN）|
| 13 | 觀察期 jsonl 進度可見 | PASS | PASS |
| 14 | schtasks PATH + StrictMode | PASS | PASS |

**合規率：12 PASS（R30）→ 14 PASS（R31，+2 紀律 #3/#12 強化）**

---

## 5. 4 軸並行下一步規劃（R31 後更新）

| 軸 | 動作 | 主檔案 | 時機 | 狀態 |
|----|------|--------|------|------|
| **軸 A 背景觀察期** | schtasks 02:00 自動跑（第 28 跑，跨 5/28 UTC date）→ 觀察期 #1=7/7 + AC4=7/14 + drift=6/30 + obs=6/30 全部 +1 進帳 | [tools/run_local_nightly.ps1](../../tools/run_local_nightly.ps1) | 2026-05-28 02:00 | 🟢 Ready ==> 等自動進帳 |
| **軸 B W1 前景** | W1-B7 產出 [SD09_Mutation_GoalSynthesis_Report.md](../06_quality/) 規劃 + mutation_analysis.py 多模組支援驗證；W1 64 case 已落地（R30）但 kill_rate 反證無實質提升 → 加做 W2 真實源碼層級補測（policy/compactor/git_verifier 三模組各加 2~3 deep semantic case） | [docs/06_quality/](../06_quality/), [tools/mutation_analysis.py](../../tools/mutation_analysis.py) | ≤ 2026-06-02 | 🟢 持續推進，重新評估補測策略 |
| **軸 C PM 拍板** | 五條 ADR 全 ACCEPTED；R31 無新拍板 | — | — | 🟢 100% |
| **軸 D W2-W6 預備** | Production_Migration_SOP §6-§8 預先研究（W4 入口）+ kb_metric_store port 設計（W2 依議題 G）+ DBA 親演演練 SOP 草稿 + **新**：jsonl append-only sub-recorder 設計（SD_10 backlog 提前研究）| [docs/08_deployment/](../08_deployment/), [autoclaude/core/ports/](../../autoclaude/core/ports/) | 持續 | 🟢 持續推進 |

### 5.1 下一步執行檔案與大綱（優先順序）

1. **等 nightly 第 28 跑（5/28 02:00 自動）** → 跨 UTC date 觀察期 #1/#2/#3/obs 全部 +1 進帳；mutation=7/7 達標窗口開啟（但 sha unique 仍只 2 需 +5 才能 lock）
2. **W1 軸 B 重新評估**：R31 audit 反證 W1 64 case 對 kill_rate 無實質貢獻 → 改執行 **W2 真實源碼層級 deep semantic case 補測**（pre-W2 提前進行）；目標每模組加 2~3 個能 kill suspected mutmut survived（如 `policy.py` 邊界判斷 + `compactor.py` 截斷條件 + `git_verifier.py` env propagation）
3. **觀察期 #1 達標窗口**：[tools/mutation_baseline_lock.py:226-291 should_lock](../../tools/mutation_baseline_lock.py#L226) 需 kill_rate ≥ 70% 連 7 + unique sha ≥ 7；以當前 sha unique=2 推估需再 +5 unique sha 才能 lock → 最早達標日由 W2 真實源碼補測節奏決定
4. **觀察期 #2 達標**（2026-06-08）→ [ac4_progress_check.py](../../tools/ac4_progress_check.py) ready_for_labeled_pr=true
5. **觀察期 #3 達標**（2026-06-24）→ drift_log severity!='info'=0 連續 30 天
6. **G0 啟動**（最遲 2026-06-26）→ 進入 W1 正式 Wave 上半（GoalSynthesisPlugin mutation pilot 擴展）

### 5.2 可繼續安排的改進（短期）

- **W1 軸 B 策略修正**：R30 「+64 case → +10.40pp」誤判 → W2 改執行 deep semantic case；同時評估提早觸發 `mutation_baseline_lock` 鎖定 token_guard 為週 baseline（釋放 nightly 給 GoalSynthesis）
- **W2 議題 G（KB metric）三方研究**：W0 期間可平行做 backlog 設計
- **multi-process trace_id 完整 9 處覆蓋**：W3 任務但 W0 期間可預先 mapping 設計
- **perf machine 採購評估**：W2 任務但 W0 期間可預先研究三方案
- **新**：jsonl append-only sub-recorder 設計（紀律 #12 進階強化，SD_10 backlog 提前研究）

### 5.3 中長期改進（SD_10 backlog 候選）

- jsonl dedup 改 append-only 或新增 sub-jsonl recorder（紀律 #12 進階版）
- mutmut suspicious 半確定性問題（升級 mutmut 至新版或改用 cosmic-ray）
- perf samples < 20 自動降級 → 評估改為強制累積至 20 才解鎖
- multi-process trace_id 完整支援（W6 / SD_10）
- mutmut regex SSOT helper（R25 P1 黃線 backlog）

---

## 6. 專案成熟度評估

| 維度 | R30 | R31 | 趨勢 |
|------|-----|-----|------|
| nightly 機制成熟度 | A+ 級（30 輪累積 + 七度閉環）| **A+ 級（31 輪累積 + 八度閉環 + 取證紀律強化）** | ↑ |
| 觀察期累計 | 6/7, 6/14, 5/30, 5/30 | 6/7, 6/14, 5/30, 5/30（待 5/28 跨日 +1）| → |
| 紀律落地 | 12 PASS + 1 CONDITIONAL + 1 PARTIAL | **14 PASS（+ 強化紀律 #3/#12）** | ↑ |
| 文件治理 | CLAUDE.md 382 行 / 0 違規 | 382 行 / 0 違規 + R31 訂正落地 | ↑ |
| 收斂保護 | contract test + 5 P1 closure | + 6 R31 consistency case | ↑ |

**結論**：專案達到 **A+ 級成熟度持續**，**新增 nightly 機制取證紀律自我修正能力**（R30 commit message 過度概括 → R31 同 sha 復跑反證 → 訂正 → 機制強化）；G0 達標日 2026-06-24 軌道內（最遲 2026-06-26）。

---

## 7. 變更檔案清單

### 源碼變更
- [tools/mutation_baseline_lock.py](../../tools/mutation_baseline_lock.py) — 新增 `compute_consistency_warning` 47 行 + main() stderr WARN 接入
- [tools/perf_regression_check.py](../../tools/perf_regression_check.py) — `emit_annotation` WARN level + sub-ms jitter range 標籤（12 行修改）

### 新增 test
- [tests/tools/test_mutation_baseline_lock.py](../../tests/tools/test_mutation_baseline_lock.py) — +6 R31 case（high/low variance / different sha / module filter / missing sha / custom threshold）（82 行新增）

### 文件更新
- [CLAUDE.md](../../CLAUDE.md) — status header R31 八度閉環 + R30 訂正 + mutmut variance protection 落地
- [docs/05_development/sprint_history.md](sprint_history.md) — §1.7.3 R30 末追加 R31 audit 訂正 blockquote + §1.7 觀察期 #2 ADR-SD09-008 v0.4 註記
- [docs/06_quality/Nightly_Forensic_Discipline.md](../06_quality/Nightly_Forensic_Discipline.md) — 紀律 #12 補 R31 強化條目

### Nightly 自動採集副作用
- `.drift_log_history.jsonl` — 第 27 跑 record（同 UTC date dedup 後 1 筆）
- `.perf_history.jsonl` — 第 27 跑 perf record
- `perf_regression_comment.md` — 第 27 跑 perf comment 自動再生

### 新建報告
- [docs/05_development/SD09_W3_Round31_NextAction.md](SD09_W3_Round31_NextAction.md) — 本檔

---

**結論**：✅ **R31 八度閉環 PASS — nightly 機制 + 取證紀律自我修正能力雙強化** — 修復 P1×2 + P2×2 + 附加 CLAUDE.md 更新；收斂未破壞（pytest +6 進帳 / 其他 hard 指標持平）；軸 B 補測策略由「形式 case 補測」修正為「W2 deep semantic case 補測」；G0 達標日 2026-06-24 加速軌道內。
