# AutoSDD ZeroTrust Audit 71 — pty-vs-sdk A/B 載具 + 真跑 + DEF-71-001 修復

> **對應計畫**：[AutoSDD_improving_71.md](../04_planning/AutoSDD_improving_71.md)（A 軌）。
> **日期**：2026-06-26 ｜ **柱位**：A 軌（執行器後端 A/B）。

---

## 1. 階段一零信任重偵察（硬閘）

| 檢查 | 實測 | 結論 |
|------|------|------|
| AutoClaude pytest | 3351 passed / 122 skipped / 0 failed | 硬閘通過（= 上輪 floor 3351） |
| lint-imports | 8 kept / 0 broken | 過 |
| LOC | violations=0（19377/20438） | 過 |
| snapshot | FRESH | 過 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129） | 過 |
| 上輪構件 | improving_70 `ActFirstOrderingError`+5 測開檔確認存在 | 無虛報 |
| 外部依賴 | claude CLI/credentials/外網 ✅；cc-switch CLI NOT FOUND（不阻擋 pty-vs-sdk 後端 A/B） | 健康 |

---

## 2. 真跑 A/B 證據（W-71-2，真 token，N=1）

兩後端各跑 `scripts/sdd_bridge_smoke.yaml`（yaml_only、臨時工作目錄、mock_brain 兜底），載具解析真實 Kernel utf-8 log：

```
| 指標 | pty | sdk |
| 一次通過率 | 0% | 100% |
| CORRECTION 次數 | 0 | 0 |
| SDD_CONTRACT_VIOLATION 次數 | 0 | 0 |
| token 峰值 | 0% | 0% |
| 完成步驟/總步驟 | 0/2 | 1/2 |
| run 成功/escalated | False/True | False/True |
```

- **sdk**：`KernelResult(success=False, completed_steps=1, total_steps=2, reason="max_retries_exhausted: ... regex: '\[ADD_DONE\]'", step_log=['[S01] ... ✓ (attempt 1)', "[FAIL] S02: ... (attempt 4)"], escalated=True)`。S01 keyword 過但 permission_mode=default 未實際建檔 → S02 evaluator 親跑 pytest 抓到 → escalate。
- **pty**：`KernelResult(success=False, completed_steps=0, total_steps=2, reason="[S01] 輸出未符合期望 regex: '\[TEST_READY\]'", step_log=[], escalated=True)`。wexpect 驅動 `claude --yes -p ...` 但 keyword 未被擷取 → 首步即 escalate。**修 DEF-71-001 前此後端於 main.py 直接 TypeError 崩潰**。
- **CORRECTION 皆 0**：預設 `enable_kernel_brain=False`（config.py）→ brain=None → 失敗步盲 retry 無修正（sdk S02 [FAIL] attempt 4 即 4 次無修正重試）。結構性事實，非缺陷。

---

## 3. 三鏡 zero-trust 並行複審（主樹派發，本輪含 untracked 新檔依 DEF-24-001 禁 worktree；突變已全還原無並行突變鏡）

### 3.1 Architect 鏡 — OVERALL PASS（P0=0 / P1=0）
- kernel 改動 `git diff --numstat`=**7/0** 純 additive，唯一新增＝`kernel.py:223-226` observability-only `logger.info`，不在條件分支、無 return/賦值/改控制流 → **零行為變更**。
- import-linter **8 kept / 0 broken**（196 files / 492 deps）；sdk lazy import 維持預設 pty 不耦合。
- LOC violations=0（kernel 291、main 145，皆 ≤750）。
- 載具 subprocess 固定 argv list 無 `shell=True` 有 timeout → 無注入面；marker 只含 step_id/attempt 無敏感洩漏。
- pty 接線型別逐項對齊（cfg.claude=ClaudeConfig / cfg.loop=LoopConfig / cfg.log_dir=str）修正 DEF-71-001。

### 3.2 SA-SD 鏡 — OVERALL PASS（P0=0 / P1=0）
- **DEF-71-001 活體實證**：親跑 `PtyExecutor(AppConfig())` 實得 `TypeError: missing 1 required positional argument: 'loop_cfg'` → 缺陷真實非紙上；修復接線正確。
- **載具錨點正確性（關鍵）**：grep 證 `STATE: EXECUTE/EVALUATE` 僅在棄用 `_impl.py`、**載具零引用**；親跑 `repr(KernelResult)` 確認以 `KernelResult(success=..., completed_steps=..., ..., escalated=...)` 開頭、錨點欄位全命中；`✓ (attempt N)` 確只在 kernel.py:185 進 step_log；落 log 路徑 main.py:140 `logger.info("Playbook 結束 | %s", result)` 屬實。
- CORRECTION 標記語義正確（首次通過不誤發、brain=None 不發、每有效修正恰一次）；提一**非阻斷輕微邊界**：標記在 `c.correction_prompt` 空檢查之前，空修正仍計一次（語義＝「一輪修正諮詢」，可接受，供日後收緊）。
- 獨立突變實證：載具 `==1`→`==2` 致 4 紅、kernel 標記改名致 1 紅，Edit 還原 byte-correct 復綠。
- 獨立零退化親跑：**3367/122/0**、三新測 18 passed、lint 8 kept、LOC 0、套件＝活體主樹。
- A/B 表「brain=None→CORRECTION 0」屬實（config.py `enable_kernel_brain=False`）；§4.2 真跑數值未獨立重現（需授權 token、N=1 非確定）但可成立性全查核通過、N=1/smoke 邊界已誠實標註。

### 3.3 QA 鏡 — OVERALL PASS（P0=0 / P1=0）
- 全套親跑 **3366 passed / 123 skipped / 0 failed**（總收集 3489 與 3367/122 同；一支環境條件式測試在 passed↔skipped 切換，0 failed、≥floor 3351）。
- 三新測檔 **18 passed**。
- **獨立突變重做**：`ab_compare_backends.py:88` `n==1`→`n==2` → 4 failed（含 first_pass_rate 1.0→0.0），Edit 改回 → 11 passed；全程**未用 git checkout**、`git status` 確認還原零殘留。
- 誠實性：新測無 skip/xfail/註解規避（`importorskip("anyio")` 為合法選配守門）；工作樹乾淨；DEF-71-001 P1 標註誠實（主 CLI 預設後端必崩屬功能性入口失效，未虛報 P0、誠實揭露 workaround 與 production 影響 nuance）。
- 誠實 flag：跑 pytest 產生 runtime 副作用 `.drift_log_history.jsonl`(+1)/`.perf_baseline.toml`(8 行) — 載具自然產物非程式變更。

---

## 4. 結案零退化矩陣（全項實測）

| 檢查 | 通過條件 | 實測 |
|------|---------|------|
| AutoClaude 全套 | ≥3351 / 0 failed | **3367/122/0**（floor 3351 + 16 新測）✅；QA 鏡 3366/123（同總數 3489、0 failed） |
| 架構契約 | 全 kept | 8 kept / 0 broken ✅ |
| LOC 分級 | 全過 | violations=0（kernel 291<500 / main 145<750）✅ |
| Snapshot | 新鮮 | FRESH ✅ |
| AISDLC_SDD 閘門 | exit 0 | 階段一 exit 0（本輪零 SDD 變更）✅ |
| 五軌 TLC | 僅 FSM 變更 | N/A（未碰 *.tla/FSM） |
| DAL 等價 | — | N/A（未碰 DAL/checkpoint 欄位） |

---

## 5. 結論

三鏡全 **OVERALL PASS、P0=0 / P1=0**，無待修發現（SA-SD 提之 CORRECTION 空修正計數邊界為非阻斷觀察，供日後收緊）。本輪：
- 交付可重複 pty/sdk A/B 指標載具（W-71-1，11 測 + 突變實證）；
- 真跑揭露並當場修復 **DEF-71-001**（預設 pty 後端 CLI 必崩，長期潛伏；W-71-2，3 回歸測守門 + 真跑驗證）；
- 為 Kernel 補 CORRECTION observability 標記（2 測 + 突變實證）使第四指標可測；
- 真跑 A/B（N=1）誠實呈現執行器層差異，且**載具初版誤錨棄用 runner 路徑由真跑當場揭露並改錨 Kernel 真實輸出**——體現真跑驗收勝於紙上 A/B。

`L_合體=min(A=L5,B=L5,C=L5)=L5` 維持（A/B 載具與缺陷修復屬工程加固，非成熟度推進）。
