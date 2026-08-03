# AutoSDD ZeroTrust Audit 69 — SDK 整合收尾（W-69-1 活體 A/B + W-69-2 can_use_tool 接線）

> 2026-06-25 ｜ 對應計畫 `docs/04_planning/AutoSDD_improving_69.md`。所有數字來自本輪真實命令輸出。

---

## §1 階段一零信任重偵察（硬閘）

派兩個 general-purpose agent 並行實測（主樹），全項 PASS、硬閘未觸發：

| 項目 | 實測 | 來源 |
|------|------|------|
| AutoClaude pytest | 3345 passed / 122 skipped / 0 failed | `python -m pytest tests/ -q` 結尾原文 |
| lint-imports | 8 kept / 0 broken | `PYTHONUTF8=1 lint-imports` |
| LOC | violations=0（19344 / cap 20438） | `check_loc_budget.py` |
| snapshot | FRESH（OK） | `snapshot_sync.py --check` |
| improving_68 構件 | sdk_executor_adapter.py:69（288 行）+ test 12 passed + config.py:231 預設 pty + .importlinter:94-118 雙向隔離 + pyproject:69-71 [sdk] | file:line 親驗 |
| SDD ci-gate | exit 0（v0.01:1478 / v0.26:1665 / scripts:129，arch_fitness fail=0/warn=3 advisory） | `bash scripts/ci-gate.sh` |
| 缺陷帳本 | open 3 / routed 3，全 P3 | 主表狀態欄逐筆解析 |

**環境 (f) 實測**：外網通（api.anthropic.com 405 / github 200）、`~/.claude/.credentials.json` 存在、`claude` 在 PATH、SDK 0.2.110 已裝、`get_context_usage` API 存在。

---

## §2 階段三/四：實作與收斂（零退化矩陣）

| 檢查 | 通過條件 | 實測 | 判定 |
|------|---------|------|------|
| AutoClaude 全套 | ≥ 3345 / 0 failed | 3349 / 122 / 0 | ✅ +4 新測，零退化 |
| lint-imports | 全 kept | 8 kept / 0 broken | ✅ |
| LOC | 全過 | violations=0（19367 / cap 20438） | ✅ |
| snapshot | 新鮮 | OK | ✅ |
| SDD ci-gate | 全綠 | exit 0（階段一；本輪零 SDD 變更，git `AISDLC_SDD/` 0 改） | ✅ |
| 五軌 TLC | 僅 FSM 變更 | 不適用（無 `*.tla`/凍結本體變更） | N/A |

**變更面（git 實證）**：4 檔 tracked 修改（sdk_executor_adapter.py +16 / main.py +25-6 / config.py +5 / test +44），共 84 insertions / 6 deletions；零 SDD 變更。

---

## §3 W-69-1 活體 A/B 證據鏈（去風險 R-68-7）

| 宣稱 | 證據 | 決定性 |
|------|------|--------|
| SDK 連真實 Claude Code | bundled claude.exe、8.6s、out.text='PONG' | ✅ |
| 事件串流真實映射 | partial_output/token_pct/completion 全到位 | ✅ |
| get_context_usage 真值 | maxTokens=1,000,000 / autoCompactThreshold=967,000 / percentage=5 | ✅ |
| act-first 真值判定安全 | _act_first_safe=True；halt 900k < autocompact 967k | ✅ |
| can_use_tool deny 真實生效 | **副作用對照**：負例(allowlist=[Read]) 哨兵檔不存在 + transcript `blocked by allowlist: Bash`；正例(含 Bash) 哨兵檔存在 | ✅ 決定性 |

**誠實留證**：
1. 探針 #2（純字串 `HELLO_FROM_BASH`）不可區分真跑/偽造 → 據實判不決定性，改用副作用對照（探針 #3）。**未以模糊證據宣稱 deny 生效。**
2. `ContextUsageResponse` 疑為非 dict 物件之疑慮 → 親驗為 `TypedDict`（runtime 即 dict、鍵名一致）→ **非缺陷，未入帳本**。

---

## §4 多專家 Zero-Trust 審查閉環

**派發隔離判準（DEF-24-001）**：本輪變更＝tracked 檔未 commit 修改 + 新增 untracked docs；`git worktree add` 由 HEAD 建樹不攜帶未 commit 修改 → audit agent **一律主樹派發**（且無並行 mutation，主樹安全）。

**結果**：見 §5（Architect / SA-SD / QA 複審記錄）。

---

## §5 三鏡複審記錄

主樹並行派發（DEF-24-001 鐵律：本輪 tracked 未 commit 修改 + untracked 新 docs，worktree 從 HEAD 建樹看不到本輪工作 → 主樹）。**三鏡全 OVERALL PASS**。

### Architect 鏡 — OVERALL PASS（P0=P1=P2=P3=0）
- adapter 類別本體 byte-for-byte 零改動，`build_tool_allowlist_predicate` 為 module-level 純函式（line 48-61，類別在 85 才起）。
- main.py 維持 thin wiring；`sdk_tool_allowlist=None`→`can_use_tool=None`（零退化邊界）。
- 選配依賴隔離實跑：`sys.modules['anyio']=None; sys.modules['claude_agent_sdk']=None; import autoclaude.main` → OK（預設 pty 零耦合未破）。
- `.importlinter` 0 改動、8 kept/0 broken；新函式同模組已受 executor 雙向隔離契約涵蓋。
- LOC 304<400、violations=0；config 純 additive。

### SA-SD 鏡 — OVERALL PASS（P3-1 流程提醒，非設計缺陷）
- deny-by-default + fail-closed 鏈完整（line 56-61 + _wrap_can_use_tool 281-288）。
- 介面 delta 與計畫 §3.2/§4.1 相符（git numstat 84+/6-）。
- **活體判讀可信度查核**：探針 #2 不決定性判斷正確；探針 #3 副作用對照為決定性；`blocked by allowlist: Bash` 經 grep 確認**唯一出處**為 `_wrap_can_use_tool` line 287（無從偽造）。
- act-first 真值驗算正確：`verify_act_first_ordering(967000, 1000000, 90)` → halt 900,000 < 967,000 → True。
- 無新 ToolInvocationPort 外呼路徑（閘工具名非 domain，無 SSRF 面）。
- P3-1：4 檔變更尚未 commit（工作樹另有既有 `docs/myPrompt.md` M），commit 時須只納本輪檔，勿夾帶。

### QA 鏡 — OVERALL PASS（含 1 件 QA 自身 P1 過程事故，已修復並經 parent 獨立複核）
- 獨立親跑全套 pytest：**3349 passed / 122 skipped / 0 failed**（與計畫相符）。
- **突變測試證非空殼**：把 `_predicate` 的 `return tool_name in allow_set` 改 `return True`（破壞 deny-by-default）→ 3 個 deny 斷言測試轉紅（`test_build_predicate_allows_listed_denies_others` / `test_build_predicate_empty_list_denies_all` / `test_build_predicate_injected_denies_unlisted_via_sdk_hook`）；還原後 16 passed。測試確能抓錯。
- 缺陷帳本誠實性：git 證 `AISDLC_SDD/` 零變更，「本輪無新框架缺陷」屬實。
- lint-imports 8 kept/0 broken。

> **🟠 QA P1 過程事故（誠實揭露 + parent 補救，零殘留）**：QA 還原突變時誤用 `git checkout -- sdk_executor_adapter.py`。因該檔工作樹版本是本輪**未 commit 新工作**（HEAD 從無 `build_tool_allowlist_predicate`），`git checkout` 把整個函式連同突變一併抹回 HEAD。QA 以 `.pyc` 編譯快取 + 原始 Grep 片段逐位元重建並交叉驗證，但重建版**漏了參數型別標註 `: list[str]`**（QA 從 pyc 推斷「無參數標註」之理由有誤——PEP 563 `from __future__ import annotations` 下參數標註仍以字串入 `__annotations__`）。**parent 補救（zero-trust 不照單全收 agent 重建）**：以本 session context 中的原始 Edit 精確還原簽章為 `(allowed_tools: list[str])`，`git diff HEAD` 確認該檔淨 +16 行、與原設計逐位元一致；重跑全套 **3349/122/0**、lint 8 kept、LOC 0、`git status` 工作樹乾淨無突變殘留。**教訓（新增流程紀律候選）**：對**未 commit 的新增工作**做「還原突變」時，**嚴禁 `git checkout --`（會連同未提交工作一起抹除、且無 git 備份）**，應改用 Edit 手動改回突變那一行；此與 Nightly 紀律 #18「mutation 須隔離樹」同根——突變操作須可無損還原。

### Parent 收斂複核（重建後親驗）
編譯 OK、全套 **3349 passed / 122 skipped / 0 failed**、lint-imports **8 kept / 0 broken**、LOC violations=0、`git status` 工作樹＝4 AutoClaude tracked 修改 + 2 untracked 新 docs（`docs/myPrompt.md` 為 session 前既有，非本輪），無突變殘留。

## §6 結案判定

三鏡全 OVERALL PASS（P0=P1=0 設計/實作面；QA P1 為過程事故已修復零殘留）。零退化矩陣全綠。**improving_69 結案。** `L_合體=min(A=L5,B=L5,C=L5)=L5` 維持。
