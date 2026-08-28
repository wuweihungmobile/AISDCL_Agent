# R108 可重啟點任務書（架構輪，寫於 2026-08-28 深夜）

> 用途：Fable 週軸（主控模型）已達 93%、session 軸 83%（converge、扇出 cap=0）。若主控撞牆，
> 掌舵者切 Opus 5 後 `claude -r <本 session>` 續跑；session ID＝
> `~/.claude/projects/d--CursorProject-AISDCL-Agent/` 下最後修改的 `.jsonl` 檔名。

## 一、已驗證什麼（全部有當回合 tool_result）

- 輪型＝C 架構輪（未結 64／warn 86；主檔 155,724 bytes；量測 19:09）。
- 五份產出（全為工作樹 untracked 新檔，`git status` 多次複核）：
  1. `docs/04_planning/ADR/ADR-XPLAT-014-resume-chain-hardening.md`（1155 行）
  2. `docs/04_planning/PRD_Amendment_R108_Pacing.md`（1147 行）
  3. `docs/04_planning/PRD_Amendment_R108_BurnDown_Addendum.md`
  4. `docs/04_planning/ADR-XPLAT-013_Phase2_Proposal_R108.md`
  5. `docs/06_quality/CrossPlatform_R108_Sentinel_Forensics.md`
  另：`docs/06_quality/CrossPlatform_R108_Review.md`（一審紀錄，主控彙整）。
- 複審鏈：一審四方（19 blocking）→ 修復包 #1/#2 → 二審三鏡（7 blocking）→ 修復包 #3/#4
  → 終審 QA＋Architect（Architect 對修憲案的 REJECT **已解除**；QA 總判「可 commit，
  條件＝殘餘 blocking 同 commit 修掉」）。
- 終審殘餘 blocking＝4 筆（B-I QA P16④／B-II QA P17③／B-III Architect A1 gate 第四通道／
  B-IV Architect A2 Phase2 方向鎖極性）＋一批 non-blocking，微修包 #5 任務書已寫好
  （見本檔 §三），**尚未派出**（額度閘門 cap=0 攔下，session 軸 16:00 UTC 自解）。
- 哨兵死因已證實（取證報告）：`AUTOSDD_RESUME_OFF=1` 住 User 層（主控親驗 User=1／
  Machine=空／行程=1）⇒ `quota_back_no_resume` 分支 14:02:09 自刪排程；D1~D4 四疊加缺陷；
  現存活哨兵同值會重演。
- crossref 現況 rc=1：`CrossPlatform_R108_Review.md`＋`CrossPlatform_R108_Sentinel_Forensics.md`
  未登記進 `tools/lib/governance_docs.py`（登記面已下沉該檔），早退壓住 12 道檢查。

## 二、還沒做什麼（依序）

> 🔴 2026-08-29 00:40 更新：**微修包 #5 已完成**（終審 4 blocking＋全部 non-blocking 收口，
> 五檔行數：修憲案 1181／ADR 1175／增補 549／Phase2 359／取證 354；探針驗證 gate 合取項
> 修法違反歸零）。另 `git status` 有兩支機器重生檔 ` M AutoClaude/.perf_baseline.toml`／
> ` M AutoClaude/tests/fixtures/pgvector_real_ground_truth.json`——照 R107 判例 chore 併入
> commit。**剩下的只有下列收尾窗口與其後的 commit/push**。
> 🔴 單人窗口紀律：收尾窗口同一時間只能有一個執行者——若由新 session 接手，本 session
> 的 06:00 計時器喚醒後不得再派第二個收尾包（接手方完成後本 session 即作廢）。

1. ~~微修包 #5~~（**已完成**，見上方更新）。
2. **收尾單人窗口**（一個 agent、禁並行）：
   a. `tools/lib/governance_docs.py` 登記上述兩檔（各附 WHY 一句）；
   b. DEF-200-230 回歸鎖落 `tools/tests/test_quota_policy.py`（紅線 1 條件 (b) 單站點：
      全庫 .py 完整端點 URL 字面恰 1 命中＝`tools/lib/quota_meter.py:72`）；
   c. 重釘稅一次付清：`test_adr_xplat001_c1c2_lock.py:743` raw-line 釘值 3055 → 現值，
      append-only 稽核列＋`<!-- guard-total:R108 -->` 落款；
   d. 帳本更新（🔴 先讀 `current_round()` 現值＝100 與 R107 甲路線慣例；新列「發現情境」
      欄零輪號；每列 ≤700 bytes；禁半形 `|` 於欄內）：DEF-200-231 狀態欄補取證指針
      （指向 Sentinel_Forensics.md，D1~D4 併入該列證據、不開新列）；DEF-200-230 若 (b) 鎖
      落地則結案；197/198/199 補「設計已交付待裁決」指針；
   e. `R108_HANDOFF.md`（四項＋三附件，含裁決題堆疊：Q1/Q2/Q3/Q6/Q7(ADR)/Q7~Q9(修憲)/
      QB1~QB6/D-1~D-6/AUTOSDD_RESUME_OFF 去留）。
3. **最後全套閘門（必須在最後一次寫文件之後）**：`python tools/run_root_unittests.py`／
   AutoClaude `python -m pytest tests/ -q`／`$env:PYTHONUTF8=1; lint-imports`／
   `python tools/check_defect_log_crossref.py`（rc 必須 0）／`python tools/check_handoff_carriers.py`
   ／`python AutoClaude/tools/check_loc_budget.py --json`／`ruff check <改到的檔>`。
4. **commit → push**（push 背景跑 timeout 480~570s）→ 等雲端五支 completed
   （windows/macos-compat-ci 長期紅不歸本輪）。

## 三、下一步的確切指令

- 查配速（派工前必跑）：`python tools/session_resume_planner.py --pace`
- 重派微修包 #5：用主控對話中最後一次被 cap=0 攔下的那份 prompt 原文（五檔可編輯、
  4 blocking＋non-blocking 清單、探針先行紀律）。
- 驗收 crossref：`python tools/check_defect_log_crossref.py; $LASTEXITCODE`（不接管線）。

## 三之二、🔴 交棒條件變更（掌舵者 2026-08-29 指示）

**下一輪（R109）將在 macOS 上執行。** 由此產生的收尾硬要求：

1. **本輪必須完整 commit ＋ push 到 main**——Mac 端只能從 `origin/main` 取得本輪成果；
   任何留在 Windows 工作樹未 push 的東西，對下輪等同不存在。含兩支機器重生檔
   （`AutoClaude/.perf_baseline.toml`／`AutoClaude/tests/fixtures/pgvector_real_ground_truth.json`）
   的 chore 處置也要在本次 commit 內講清楚。
2. **GitHub CI/CD 盡量修復**：push 後等雲端結論；本輪新增檔案若讓任何 workflow 轉紅，
   當輪修（compat-ci 兩軌長期紅屬既有債，需查歷史比對後才可歸類為「非本輪造成」）。
3. **HANDOFF 必須含 macOS 開場指引**：Windows 專屬前提（PowerShell 載具、schtasks、
   `AUTOSDD_RESUME_OFF` User 層變數、pythonw hook 載具）在 Mac 上全數不適用；
   R109 開場要跑的是 `bash` 側對等腳本與 launchd 側現查，且 `pmset` 睡眠姿態一律現查
   （CLAUDE.md 明載：該值不隨 clone 走、不得寫成常數）。本輪產出中所有 Windows 實測
   數字（哨兵取證、schtasks 憑證、LOC 以外的機器狀態）在 Mac 上**一律無效，須重測**。

## 四、禁止事項

- 不准 `--no-verify`、不准 `AUTOCLAUDE_SKIP_HOOKS=1`、不准 `AUTOSDD_QUOTA_GUARD_OFF=1`
  （額度閘門攔下時等視窗，不關守衛）。
- 不准動 `AUTOSDD_RESUME_OFF` User 層變數（掌舵者裁決項）。
- 不准把「未實作」寫成「已完成」；重啟後第一件事重驗本檔所有宣稱（zero-trust 對自己）。
- 帳本編輯遵 Playbook §4.6~§4.7；最後全套閘門必須在最後一次寫文件之後（R96 教訓）。
- 主控不親自寫代碼／審文件；收尾窗口單人、禁並行（鐵律七）。
