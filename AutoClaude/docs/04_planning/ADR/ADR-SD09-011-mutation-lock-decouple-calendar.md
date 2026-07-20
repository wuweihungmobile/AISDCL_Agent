# ADR-SD09-011：Mutation baseline 鎖定判準解除日曆綁定（unique-sha 計數 × 源碼變動觸發）

| 欄位 | 內容 |
|------|------|
| 狀態 | **ACCEPTED — 2026-06-30 PM（掌舵者）signoff**（approve 進實作、migration 方案 A、觸發兩者皆備、CONSECUTIVE_RUNS 維持 7）；improving_101 已落地 + 三鏡 zero-trust audit OVERALL PASS |
| 提案輪 | AutoSDD improving_101（C 軌 SD_09 W1 觀察期收斂） |
| supersede | ADR-SD08-002 §2.4「連續 7 次達標鎖定」的**日曆綁定語意** + ADR-SD09-009 §11.6「需多日演進」的**時間代理**（反作弊與門檻數值不變） |
| 相關 | 紀律 #12（unique sha 反作弊）、紀律 #6（採集寬鬆 vs 升級嚴格分軌） |

---

## 1　Context（問題）

### 1.1 現況：鎖定難收斂、長期空轉
SD_09 W1 mutation pilot（TokenGuardPlugin）`should_lock` 需 tail 7 筆紀錄、7 個 unique `source_sha256`。實測（improving_100，2026-06-30）：kill_rate 閘已過（tail7 最小 0.6956 ≥ 0.68），但 unique sha 卡在 **3/7**，懸停逾 G0 deadline（2026-06-26）。

### 1.2 根因：兩機制把「源碼演進證據」綁死成「日曆天數」
1. **觸發點**：`tools/run_local_nightly.ps1:25` schtasks `/SC DAILY /ST 02:00` + `autoclaude-ci.yml` cron — **每天只跑一次**（R14 註：GHA cron 已於 2026-07-20 CI-2 額度裁決降為每週一，每日觸發僅剩本地 schtasks——本節其餘推論不受影響，unique-sha 累積反而更慢，更凸顯本 ADR 解耦決策的必要）。
2. **M-05 去重**：`mutation_baseline_lock.py:197-203` 去重鍵＝「同 module + 同 **UTC 日期**」（**不看 sha**）→ 同一天即使源碼改 N 次（N 個不同 sha），也只留最後一筆。

兩者疊加 ⇒ **unique sha 每 UTC 日最多 +1** ⇒ 7 個 unique sha **至少需 7 個日曆天**；中間任一日 idle，tail 7 窗口被重複 sha 稀釋 ⇒ 可能永不收斂（空轉數週至一月）。

### 1.3 為何這是缺陷（非保守）
- **mutation test 是確定性的**：同源碼同測試，kill_rate 必然相同。「每天重測同一個 sha」**不產生任何新資訊**——把鎖定信心綁在「熬日曆天」上是純粹的時間懲罰、無信心增益。
- **原始 rationale 已被取代**：ADR-SD08-002 §2.4「連續 7 次」初衷＝SD_08「2 週 pilot 觀察期」防「單日抖動誤鎖」。但 SD_09 後此防抖動目的已被三個更精準機制涵蓋：
  1. unique sha（紀律 #12）— 防同 commit 騙鎖；
  2. ±2pp tolerance（ADR-SD09-009 §5.5）— 緩衝 mutmut suspicious flake；
  3. `compute_consistency_warning`（`mutation_baseline_lock.py:265`）— 同 sha 多 run kill_rate variance 抓非確定性抖動。
  ⇒ 「綁日曆天」如今是無對應防護目標的遺留懲罰。

---

## 2　Decision（決策：unique-sha 計數與日曆解耦）

**核心原則**：鎖定要求「**N 個真實不同的源碼版本（unique sha）都達標**」，而非「熬 N 個日曆天」。三項改動：

### 2.1 去重鍵：UTC 日期 → `source_sha256`
`append_history` 去重鍵改為「同 module + 同 `source_sha256`」（同源碼版本重跑只保留最新一筆——因確定性，無新資訊；保留最新以反映最近一次量測）。
- 效果：**同一天的多個不同 sha 全部計入**；反作弊強度不減反增（直接按源碼指紋，比日期代理更精準）。
- 缺 sha 的 legacy 紀錄（2026-05-20/21 兩筆）：沿用 `MAX_BACKWARD_COMPAT_MISSING` 既有寬鬆處理。

### 2.2 觸發點：每日 nightly → token_guard 源碼變動時觸發
- **鎖定累積**改由「偵測 `token_guard/*.py` 變動」觸發（pre-push git hook 或 CI on-path-change），有變才跑 mutation 記一筆。
- **nightly 角色轉為監控**（紀律 #6 分軌精神）：監控 kill_rate 漂移 + `compute_consistency_warning` flaky 偵測，**不再充當鎖定計時器**。
- 效果：源碼演進證據隨開發節奏即時累積，不靠日曆；idle 不空轉計時。

### 2.3 tail 語意：每源碼版本一筆，tail N = 最近 N 個 unique sha
改 §2.1 後 history 每 unique sha 一筆，`should_lock` 的 tail N 自然＝「最近 N 個不同源碼版本」，idle 不再產生重複筆稀釋窗口。kill_rate 閘（tail N all ≥ effective threshold）與 unique sha 閘（恆成立）維持。
- `CONSECUTIVE_RUNS=7`、effective threshold（0.68）、kill_rate 公式**數值全不變**——只改「7 的計量單位」從日曆天變源碼版本。

---

## 3　反作弊強度對照（關鍵：沒有放寬安全性）

| 防護目標 | 原機制 | 新機制 | 強度 |
|---|---|---|---|
| 同 commit 重跑騙鎖 | unique sha + 同日去重 | unique sha（按 sha 去重） | **相同/更精準** |
| 要真實源碼演進 | 綁 7 個日曆天 | 綁 7 個 unique sha | **相同**（演進證據不變，只解時間綁定） |
| 單日抖動 / flaky 誤鎖 | 連續 7 日 | ±2pp tolerance + consistency_warning | **相同**（已分軌承擔） |
| 人工最終閘 | 紅線 PM signoff | 紅線 PM signoff | **不變** |

新機制唯一「放寬」的，是**與安全無關的日曆懲罰**。

---

## 4　Migration（既有 30 筆歷史相容）

`.mutation_history.jsonl` 現有 30 筆（按 UTC 日、含大量重複 sha：`20940e1b` ×21 筆等）。Cutover 策略（待 signoff 定案，傾向方案 A）：
- **方案 A（一次性按 sha 壓縮，傾向）**：保留每個 unique sha 的**最新一筆**，原檔備份為 `.mutation_history.jsonl.pre_sd09_010.bak`。壓縮後 token_guard 約剩 5 個 unique sha 紀錄（5208cff/20940e1b/4af78567/55013d0a + 2 筆 legacy 缺 sha 擇一）。tail 7 仍未滿 7 → 不會「假鎖定」，符合誠實（真實只演進過 4~5 個版本）。
- 方案 B（cutover 日切，新機制從此累積）：較簡單但丟棄既有演進證據，傾向不採。

---

## 5　Consequences

### 正面
- 解除空轉：開發活躍時幾輪內湊滿 unique sha，idle 不空轉計時。
- 更精準的反作弊（按源碼指紋而非日期代理）。
- nightly 回歸其本職（監控/flaky），職責更清晰（紀律 #6 分軌）。

### 風險 / 待驗
- **R1**：on-change 觸發需新 hook/CI 配置；pre-push 跑 mutation 可能慢（token_guard ~400-600 mutation）——緩解：on-change 只跑 token_guard 單模組（既有 pilot 範圍）、或 CI 非阻塞跑、本地 hook 可 opt-in。
- **R2**：既有歷史壓縮須保證不「假鎖定」（壓縮後 unique sha 數 ≤ 真實演進版本數）——方案 A 已滿足。
- **R3**：改 `append_history` 去重鍵影響既有 M-05 測試——須同步更新測試（受控突變驗牙）。
- **R4**：此為 ADR 級語意變更，須三鏡 audit + PM signoff。

### Rejected alternatives
- **維持現狀**：空轉，掌舵者明確否決。
- **純降 `CONSECUTIVE_RUNS` 7→N**：治標，仍綁日曆、仍會 idle 稀釋。
- **放寬 unique sha 守門**：ADR-SD09-009 §11 已封死（弱化反作弊），不採。

---

## 6　DoD（signoff 後 improving_101 實作驗收）
1. `append_history` 去重鍵 date→sha + 單元測試（含「同日不同 sha 皆計入」「同 sha 重跑只留最新」受控突變驗牙）。
2. `should_lock` tail 語意對齊 + 既有測試更新。
3. on-change 觸發機制（hook/CI）+ nightly 角色註解轉為監控。
4. 既有 history 方案 A 壓縮 + 備份。
5. 零退化（AutoClaude pytest ≥ 基線、lint 8 kept、LOC 0）。
6. 三鏡 zero-trust audit OVERALL PASS。
7. 文件：本 ADR 轉 ACCEPTED + 更新 ADR-SD08-002 §2.4／ADR-SD09-009 §11.6 supersede 註記 + CLAUDE.md SD_09 段。
