# CrossPlatform_R81_Ledger_Triage — R81 缺陷帳本 87 筆未結列的四類分流

## §0 這份檔為什麼存在

本檔是 `docs/06_quality/CrossPlatform_R81_Scan_Findings.md` 的**姊妹檔**（拆分理由與對照表
見該檔 §8）：R81 第一批的 `scan:ledger` 路產出 34 筆分流結論，體積無法與其餘八路同居一檔。

**分流的四類**（任務書定義，逐字）：

- **(A)** 其實已經修好了，只差狀態欄沒跟上 → 可直接結案；
- **(B)** 前提已不成立／該主張今日為假 → 可結案（`closed-by-decision`）；
- **(C)** 真待辦，本輪做得完 → 交給下游修復包；
- **(D)** 真待辦，本輪做不完 → **必須改派具名承接輪次，不能留白**。

🔴 **本路自陳的三條可信度邊界（逐字重點，全文見 §3）**：

1. 87 筆**逐筆讀完全部、實查驗證了約 40 筆**；另約 47 筆只讀帳本原文、未做磁碟複驗。
2. 跨平台條件一項都驗不了（本機 Windows），凡涉 macOS 或雲端 runner 的解鎖條件只能報
   「今天走不通」，不能報「已滿足」或「不成立」。
3. **未結列的算術沒有實跑驗證**——「能降幾筆」是依 `_classify()` 判準推得的，實際降幾筆
   必須改完帳本後重跑 `check_defect_log_crossref.py --unresolved-count` 才算數。

🔴 沿用 R80 的誠實標準：**寧可留 open 也不要假結案**。本路在 `LDG-S1-04`／`LDG-S1-31`／
`LDG-S1-32`／`LDG-S1-34` 四筆都遇到「零成本可結但關掉會製造假事實」的抉擇，一律標成
「需明說走哪一條」而不是替人拍板。

## §1 分流全景

**筆數 34**（P0 1／P1 6／P2 16／P3 11）　**agentId** `af5fb0f96a12df6b8`

| 類 | 語意 | 筆數 | 本檔 ID |
|---|---|---|---|
| (A) | 已修好，只差狀態欄 | 6 | `LDG-S1-02`, `LDG-S1-03`, `LDG-S1-04`, `LDG-S1-08`, `LDG-S1-17`, `LDG-S1-34` |
| (B) | 前提不成立，可 closed-by-decision | 2 | `LDG-S1-05`, `LDG-S1-33` |
| (C) | 真待辦，本輪做得完 | 7 | `LDG-S1-09`, `LDG-S1-10`, `LDG-S1-11`, `LDG-S1-12`, `LDG-S1-13`, `LDG-S1-14`, `LDG-S1-22` |
| (D) | 真待辦，本輪做不完 → 須改派具名承接輪次 | 18 | `LDG-S1-06`, `LDG-S1-07`, `LDG-S1-15`, `LDG-S1-16`, `LDG-S1-18`, `LDG-S1-19`, `LDG-S1-20`, `LDG-S1-21`, `LDG-S1-23`, `LDG-S1-24`, `LDG-S1-25`, `LDG-S1-26`, `LDG-S1-27`, `LDG-S1-28`, `LDG-S1-29`, `LDG-S1-30`, `LDG-S1-31`, `LDG-S1-32` |
| (?) | 閘門本身現在是紅的（不屬四類，屬今天就要修） | 1 | `LDG-S1-01` |

> 分類鍵取自各筆**標題自己寫的** `(A)`／`(B)`／`(C)`／`(D)` 標記（`(A/部分)`、`(C/D)` 這種混合標記歸到第一個字母）；`LDG-S1-01` 標題沒有分類標記，因為它不是帳本內容問題，是**閘門今天就是紅的**。

### §1.1 索引

| 本檔 ID | 原始 ID | sev | 標題（逐字） | 檔案:行 | 成本 |
|---|---|---|---|---|---|
| `LDG-S1-01` | S1-01 | P0 | 【今天就紅】crossref 根層閘門 rc=1 — 舵手洩壓歸檔使 3 筆超長列豁免過期 | tools/lib/defect_ledger_index.py:552,582,607 | small |
| `LDG-S1-02` | S1-02 | P1 | (A) DEF-101-205 可直接結案 — 它自訂的解鎖條件已於 R80 落地並今日實跑通過 | tools/tests/test_platform_neutral_paths.py:3853 | small |
| `LDG-S1-03` | S1-03 | P1 | (A) DEF-101-470 可直接結案 — 回報者給的建議修法已逐字落地，今日實跑通過 | AutoClaude/tests/test_shell_deny_chars_parity.py:96 | small |
| `LDG-S1-04` | S1-04 | P2 | (A) DEF-101-740 修復已於 R80 落地並具名引用本列 — 惟解鎖條件寫死 macOS 實測，Windows 上取不到 | tools/git-hooks/pre-push:62,71 | small |
| `LDG-S1-05` | S1-05 | P1 | (B) DEF-101-271 主張今日為假 — 根層 tools/ 已納入 LOC 分級治理；但同一次量測揭露它的升級門檻只剩 1 行餘裕 | AutoClaude/tools/check_loc_budget.py:179,191 | small |
| `LDG-S1-06` | S1-06 | P1 | (D)【最高 ROI】7 筆列處於閘門自己印出的 fail-open 窗口，R81 第一列一落地就全變硬紅孤兒 | docs/06_quality/AutoSDD_Defect_Log.md:122,144,145,146,147,149,150 | small |
| `LDG-S1-07` | S1-07 | P1 | (D) GitHub Actions 帳務今天仍是停擺的 — 4 筆列的解鎖條件結構上不可達，且兩筆列上「已恢復」的記載已回退為假 | docs/06_quality/AutoSDD_Defect_Log.md:132,104,89,114 | medium |
| `LDG-S1-08` | S1-08 | P2 | (A/部分) DEF-101-876 的解鎖條件①③ 已達成 — R78 確實補跑了 R77 積欠的四方複審 | docs/06_quality/CrossPlatform_R78_Review.md:1 | small |
| `LDG-S1-09` | S1-09 | P2 | (C) DEF-101-238 今日逐字複現 — 兩份姊妹白名單仍不一致，且缺 _DENY_CHARS 第二層那一半仍在 | AutoClaude/autoclaude/execution/mutation_applier/_conditional.py:23 | small |
| `LDG-S1-10` | S1-10 | P2 | (C) DEF-101-055 今日以真 PG 實測複現 — ORM CheckConstraint 名與 DB 實際名仍分歧 | AutoClaude/autoclaude/infra/repositories/_pg_models.py:74,138 | small |
| `LDG-S1-11` | S1-11 | P3 | (C) DEF-101-235 ① 今日複現 — dev_start.py 三處 kernel32 呼叫全檔零 restype | tools/dev_start.py:675,973,1053 | small |
| `LDG-S1-12` | S1-12 | P2 | (C) DEF-101-596 今日複現 — hub_sync outbox 路徑仍寫死在生產碼 | AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/hub_sync.py:593 | small |
| `LDG-S1-13` | S1-13 | P2 | (C) DEF-101-402 今日複現 — autoclaude-ci.yml 仍不在 CI paths meta-lock 的對照表內 | AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:257 | small |
| `LDG-S1-14` | S1-14 | P2 | (C/D) DEF-101-758 今日複現 — dev_start 開工第一道檢查對未追蹤檔仍隱形，且 behind==0 早退未動 | tools/dev_start.py:745 | medium |
| `LDG-S1-15` | S1-15 | P1 | (D) DEF-101-752 今日逐檔實測 — 11 個承接站點有 10 個仍是 tracked-only 掃描面 | tools/tests/test_windowsapps_guard_cross_consistency.py:488 | large |
| `LDG-S1-16` | S1-16 | P2 | (D) DEF-101-764 今日複現核心、但「未入帳」那半邊已不成立 | tools/lib/WindowsAppsGuard.ps1:140 | medium |
| `LDG-S1-17` | S1-17 | P2 | (A/部分) DEF-101-870 解鎖條件① 已於 R80 達成 — 兩處生產碼註解都已改成與帳本一致 | tools/lib/sdd_latest.py:36 | small |
| `LDG-S1-18` | S1-18 | P2 | (D) DEF-101-736 描述的問題在放大 — 「已結列殘留待辦」由 18 筆漲到 34 筆 | docs/06_quality/AutoSDD_Defect_Log.md | medium |
| `LDG-S1-19` | S1-19 | P2 | (D) DEF-101-399 的債在長大 — 兩支 compat workflow 由 935/679 行漲到 1628/1113 行，reusable workflow 仍零採用 | .github/workflows/windows-compat-ci.yml | large |
| `LDG-S1-20` | S1-20 | P3 | (D) DEF-101-060 部分收斂 — 18 條無上限相依今日只解決 2 條，另新增 1 條 | AutoClaude/pyproject.toml:42 | medium |
| `LDG-S1-21` | S1-21 | P3 | (D) DEF-101-018 的兩半分開處置 — 教學指令半邊已解、存量半邊今日實測 796 筆 | AutoClaude/pyproject.toml:35 | medium |
| `LDG-S1-22` | S1-22 | P3 | (C) DEF-101-856 ② 死碼判定今日成立 — verify_token_guard_e2e.py 零 production 消費者 | AutoClaude/tools/verify_token_guard_e2e.py | small |
| `LDG-S1-23` | S1-23 | P3 | (D) DEF-101-243 ② 今日複現 — README badge 與 CLAUDE.md 日期仍是純人工欄位 | AutoClaude/README.md | small |
| `LDG-S1-24` | S1-24 | P3 | (D) DEF-101-268／296 需舵手拍板 — repo-wide 停寫 bytecode 的決策至今未做 | docs/06_quality/CrossPlatform_R78_Debt_Audit.md:145 | medium |
| `LDG-S1-25` | S1-25 | P3 | (D) DEF-101-338 今日複現 — 4 支疑似測試污染的假 SHA 檔仍被 git 追蹤 | AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/drift/COMMIT-sha-low.yaml | medium |
| `LDG-S1-26` | S1-26 | P3 | (D) DEF-101-336 今日複現 — 凍結版禁改機械鎖仍不存在 | docs/06_quality/AutoSDD_Defect_Log.md:69 | medium |
| `LDG-S1-27` | S1-27 | P3 | (D) DEF-101-388 今日抽驗複現 — 凍結版 FF-17 斷言未回補，且解鎖需 Copy-on-Evolve 例外 | AISDLC_SDD/AISDLC_SDD_v0.10/tools/arch_fitness/arch_fitness.py | medium |
| `LDG-S1-28` | S1-28 | P2 | (D) DEF-101-803 主症狀已治、狀態欄未跟上 — 遞迴斷點已落地但 :1330 仍寫「結構性修法未做」 | tools/tests/test_run_root_unittests.py:1330 | small |
| `LDG-S1-29` | S1-29 | P2 | (D) DEF-101-701／746 — MIN_TESTS 已釘 2466，但註記自陳判準仍有一半未滿足 | tools/run_root_unittests.py:58 | medium |
| `LDG-S1-30` | S1-30 | P2 | (D) DEF-101-676 容量結構解仍未做 — 而今天的洩壓歸檔正好再次實證它的論點 | tools/lib/defect_ledger_index.py:580 | medium |
| `LDG-S1-31` | S1-31 | P3 | (D) DEF-42-001 逾 130 天零回執 — routed 卻無承接者，且標的在凍結版 v0.17 | AISDLC_SDD/AISDLC_SDD_v0.17/tools/fsm_runtime/tests/test_file_lock.py | small |
| `LDG-S1-32` | S1-32 | P3 | (D) DEF-53-001 逾 130 天零回執 — latent 判定今日仍成立（零 runtime 消費者） | AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/hub_merge.py:87 | small |
| `LDG-S1-33` | S1-33 | P2 | (B/部分) DEF-101-798 的兩半今日一真一假 — 掃描器覆蓋那半已被推翻，hook 橋接那半仍為真 | .claude/settings.json | small |
| `LDG-S1-34` | S1-34 | P2 | (A/確認) DEF-101-755 條件(a) 今日在 Windows 真機再次驗證通過 — 只剩結構上不可達的 (b) | tools/tests/test_dev_start.py:5304 | small |

## §2 逐筆（證據逐字保全）

### `LDG-S1-01`｜[P0] 【今天就紅】crossref 根層閘門 rc=1 — 舵手洩壓歸檔使 3 筆超長列豁免過期

- **檔案:行**：tools/lib/defect_ledger_index.py:552,582,607
- **成本**：small

**為何要緊（逐字）**：這不是帳本內容問題而是閘門本身現在是紅的：舵手為了洩壓做的歸檔把三列搬出主檔，於是它們的「超長豁免」變成沒有對應物的空額度。工具訊息逐字說明留著的後果＝「日後無聲加回去的額度」——也就是未來有人把某列寫爆時不會轉紅。任何後續修復包在 push 前都會撞到這個 rc=1，且成因與他們的改動無關，極易被誤歸因為環境問題。

**當回合實測證據（逐字保全）**：

```text
當回合實跑 `& .venv\Scripts\python.exe tools\check_defect_log_crossref.py` → **RC=1**，輸出逐字：`❌ 帳本體積與逐列位元組上限（3 筆）` / `DEF-01-007：列在 OVERSIZE_ROW_GRANDFATHERED，但主檔實測查無此 ID⇒ 豁免已過期…` / 同樣三行分別為 `DEF-101-274`、`DEF-101-422`。實查常數：`OVERSIZE_ROW_GRANDFATHERED`(:552 frozenset)、`OVERSIZE_ROW_CEILING = 101`(:582)、`OVERSIZE_ROW_EXCESS_CEILING = 143303`(:607)。該檔 :580 自己的註解記載上一次同型清理（「四筆已於本輪開場搬進 archive_63…豁免過期」）⇒ 這是歸檔動作的已知副作用，會在下一次 push 被 pre-push 擋下。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（零風險、5 分鐘）：把 DEF-01-007／DEF-101-274／DEF-101-422 三個 ID 自 :552 的 frozenset 移除，並在**同一次變更**內把 :582 與 :607 兩個棘輪常數改為當回合實測值（依該檔 :551 的取值紀律：直接填 `--check` 印出的實測數、零加減推算、不留成長緩衝）。改完重跑 `check_defect_log_crossref.py` 應 rc=0。
```

### `LDG-S1-02`｜[P1] (A) DEF-101-205 可直接結案 — 它自訂的解鎖條件已於 R80 落地並今日實跑通過

- **檔案:行**：tools/tests/test_platform_neutral_paths.py:3853
- **成本**：small

**為何要緊（逐字）**：這筆自 R14 open 逾六十輪，是「散文式延後」的代表列。修復已經在磁碟上、有雙向注入自證、今天跑得過——狀態欄沒跟上而已。留著它同時污染兩件事：未結列計數（逼近 fail 線 98），以及「還有幾類危害沒人守」這個治理數字。

**當回合實測證據（逐字保全）**：

```text
該列解鎖條件逐字＝「以 `git ls-files -s` 取出 mode 100755 的檔案集合，與 ONBOARDING.md §6 執行權限政策句具名的 755 清單逐項互比，不符即 rc=1」。實查 `tools/tests/test_platform_neutral_paths.py:3853 test_the_index_exec_set_matches_the_onboarding_policy_sentence`，其 docstring 逐字寫「🔴 DEF-101-205 自訂的解鎖條件本體（R80 落地）」，實作為 `exec_bit_prose_scope(ONBOARDING.md)` + `exec_bit_scope_problems(self.modes, scope)`。當回合實跑 `python -m unittest test_platform_neutral_paths.TestExecBitIsGovernedViaTheGitIndex -v` → **Ran 10 tests, OK, RC=0**，含 `test_the_exec_scope_criterion_is_red_in_both_directions`（雙向紅綠自證）與 `test_the_index_mode_channel_is_alive`（取數管道自證）。另實跑 `git ls-files -s | 100755` 得 9 支。
```

**分流結論／建議修法（逐字）**：

```text
結案：狀態欄改 `fixed@R80`，證據引 `tools/tests/test_platform_neutral_paths.py::TestExecBitIsGovernedViaTheGitIndex::test_the_index_exec_set_matches_the_onboarding_policy_sentence` 與當回合 rc=0。未結列 −1。
```

### `LDG-S1-03`｜[P1] (A) DEF-101-470 可直接結案 — 回報者給的建議修法已逐字落地，今日實跑通過

- **檔案:行**：AutoClaude/tests/test_shell_deny_chars_parity.py:96
- **成本**：small

**為何要緊（逐字）**：該列被 R60 判為「死信」（交棒的 C 軌容器零登記）並改派未指派，實際上修復早已完成。它是「已修好但沒人回來關」最乾淨的一個實例——結案零風險、零爭議。

**當回合實測證據（逐字保全）**：

```text
該列建議修法逐字＝「改為 `prompts=("clean step", f"step two {bad_char}")` 並斷言 `"步驟 1"` 出現在 `verdict.reason`」。實查該檔 :109-120：`gate.evaluate(goal_hash="h1", step_count=2, prompts=("clean step", f"build the thing {bad_char} now"))` + `assert "步驟 1" in verdict.reason`，且 :103-107 的 docstring 逐字具名 `🔴 DEF-101-470` 並複述該退化形態。當回合實跑 `python -m pytest tests/test_shell_deny_chars_parity.py -q` → **16 passed, RC=0**。
```

**分流結論／建議修法（逐字）**：

```text
結案：狀態欄改 `fixed`，證據引該測試檔 :96-120 與當回合 16 passed。未結列 −1。
```

### `LDG-S1-04`｜[P2] (A) DEF-101-740 修復已於 R80 落地並具名引用本列 — 惟解鎖條件寫死 macOS 實測，Windows 上取不到

- **檔案:行**：tools/git-hooks/pre-push:62,71
- **成本**：small

**為何要緊（逐字）**：這是 (A) 類但帶一個誠實邊界：該列自訂的解鎖條件逐字要求「在無 venv 的 macOS 上實跑一次 push 前置驗證（python／python3 兩種 PATH 形態各一）並附 rc」。本機是 Windows，取不到那個 rc。若照 R80 的紀律（寧可留 open 也不要假結案），不能單方面宣稱已滿足；但若照條件字面永遠關不掉（沒有 mac 真機的輪次一律無法結）。

**當回合實測證據（逐字保全）**：

```text
實查 `tools/git-hooks/pre-push`：:62 逐字 `# 🔴 DEF-101-740（R80）：直譯器候選由 `python` 一支擴為 `python → python3`，與姊妹`；:71 `for _py_cand in python python3; do`；:272/:317/:412/:432 四處 fail-loud 訊息皆已改寫為「找不到 python／python3」。即該列所述硬阻擋（未啟用 venv 的 macOS 只有 python3 ⇒ 所有 push 被擋）在程式碼上已被消除。
```

**分流結論／建議修法（逐字）**：

```text
二擇一，需在帳本上明說走哪一條：(甲) 結案 `fixed@R80`，並在結案句誠實寫「修法本體已落地並具名，macOS rc 未取得；回歸由 `tools/tests/test_root_infra_parity.py` 一類的姊妹 hook parity 鎖承擔」；(乙) 維持未結但把解鎖條件改寫為「補一支不需 mac 真機的 PATH 形態注入測試」。我建議 (甲)——條件寫死一台不存在的機器，正是本 repo 反覆記載的「孤兒解鎖條件」形態。
```

### `LDG-S1-05`｜[P1] (B) DEF-101-271 主張今日為假 — 根層 tools/ 已納入 LOC 分級治理；但同一次量測揭露它的升級門檻只剩 1 行餘裕

- **檔案:行**：AutoClaude/tools/check_loc_budget.py:179,191
- **成本**：small

**為何要緊（逐字）**：前提消滅可讓這筆 open watch 結案（未結列 −1）。但更要緊的是那 1 行餘裕：該列自訂「若任一輪實測超過 2000 行即升級為該輪必修（不得再以需人工決策為由延後）」——下一個要動 dev_start.py 的人（例如 DEF-101-758 要修的 step_sync 正在同一支檔）會在加第一行時當場破線，而正確處置不是調高門檻。

**當回合實測證據（逐字保全）**：

```text
該列主張逐字＝「收斂出的 Python 核心檔**完全不在任何 LOC 分級政策管轄範圍內**」。當回合實跑 `python AutoClaude\tools\check_loc_budget.py` → RC=0，輸出逐字含 `violations=0 (absolute=0 tier=0 special=0 root_tools=0 total=0)` 與獨立的 `[ROOT-TOOLS-WARN] 2 支根層 tools/ 檔案 tier 餘裕 ≤ 6 行：[guardrail_cli<=750] tools/session_resume_planner.py: 749 / [guardrail_lib<=400] tools/lib/skip_group_policy.py: 395` ⇒ 根層 tools/ 有自己的分級（guardrail_cli／guardrail_lib）。另 :191 `"../tools/dev_start.py": 2000` 存在。**同一次輸出**另印 `[special<=2000] ../tools/dev_start.py: 1999 （餘裕 1 行）`。
```

**分流結論／建議修法（逐字）**：

```text
結案 `closed-by-decision`（治理範圍缺口已由 R68/R69 補上，前提不再成立），並在結案句就地標註「dev_start.py 現 1999/2000，升級門檻已在門口，拆分責任由 DEF-101-398 承接」。同時把 DEF-101-398（Architect 建議拆 bootstrap_lock.py／nightly_heartbeat.py）改派 R81 並升為必修。
```

### `LDG-S1-06`｜[P1] (D)【最高 ROI】7 筆列處於閘門自己印出的 fail-open 窗口，R81 第一列一落地就全變硬紅孤兒

- **檔案:行**：docs/06_quality/AutoSDD_Defect_Log.md:122,144,145,146,147,149,150
- **成本**：small

**為何要緊（逐字）**：這 7 筆現在是靜默的：閘門只印 warning。但硬規則② 的判準是「承接輪號必須 ≥ 當前輪」——R81 一旦寫入第一列帳本，當前輪推進為 R81，這 7 筆的 R80 就低於當前輪，全部同時變成 rc=1 硬紅。也就是說下一輪開工的第一個動作會把根層閘門打紅 7 筆，而那時處理它們的選擇跟現在完全一樣、只是更慌。這是本次盤點中投入最小、避免的損害最大的一項。

**當回合實測證據（逐字保全）**：

```text
當回合實跑 `check_defect_log_crossref.py` 的 warning 區逐字印出 7 筆：`:122 DEF-101-796`、`:144 DEF-101-912`、`:145 DEF-101-917`、`:146 DEF-101-918`、`:147 DEF-101-919`、`:149 DEF-101-925`、`:150 DEF-101-926`，訊息逐字＝「承接輪次 R80 **恰等於**由『發現情境』欄推得的當前輪 …本列實為『交棒給剛結束的那一輪』而硬規則② 抓不到（fail-open 窗口，於本輪第一列落地時自動關閉）」。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（純帳本編輯）：7 筆逐列就地追加「改派為：R81」或「回執」，解鎖條件逐字沿用不改寫（體例比照 DEF-101-886/887/889 已完成的 R80→R81 改派）。不動任何程式碼。
```

### `LDG-S1-07`｜[P1] (D) GitHub Actions 帳務今天仍是停擺的 — 4 筆列的解鎖條件結構上不可達，且兩筆列上「已恢復」的記載已回退為假

- **檔案:行**：docs/06_quality/AutoSDD_Defect_Log.md:132,104,89,114
- **成本**：medium

**為何要緊（逐字）**：受阻四筆：DEF-101-866（解鎖＝額度恢復後 dispatch，未達）、DEF-101-703（解鎖②＝nightly-full 排程窗口成功，未達；且 R69 寫的『帳務已於 2026-08-01 恢復』今日為假）、DEF-101-518（解鎖①『GitHub 帳務已恢復』在 R68 標為已達成，今日已回退）、DEF-101-755(b)（『於 Windows CI 實跑一次並附 skip 明細取證』，通道不通）。這四筆若不集中標註成外部阻塞，下一輪會有人再花一次時間重新發現同一件事——這正是帳本存在的目的失效。

**當回合實測證據（逐字保全）**：

```text
當回合唯讀實跑（零 Actions 額度）`gh run list --limit 25 --json ...` → RC=0：最新 push（2026-08-08T11:14:50Z、R80 收輪 commit）7 支 workflow 中 6 支 `conclusion=failure`。再跑 `gh run view 31254543751 --json jobs`（windows-compat-ci）→ 三個 job：`Windows smoke` failure **steps=0** 起 11:14:51 訖 11:14:53（2 秒）、`nightly 失敗提醒` skipped steps=0、`nightly full suite` skipped steps=0 —— 與 DEF-101-703／866 記載的帳務失敗指紋（steps 長度 0、2~4 秒、conclusion=failure）完全一致。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並在四筆各加一句「外部阻塞：GitHub Actions 帳務，當回合唯讀取證 run 31254543751 三 job 皆 steps=0」。DEF-101-518 與 DEF-101-703 需**就地訂正**先前『帳務已恢復』的宣稱（帳本只增不刪，追加訂正不改寫原文）。另建議把「帳務是否恢復」做成一支唯讀探針（`gh run view <最新 push run> --json jobs` 判 steps==0），讓下一輪不必人工重查。
```

### `LDG-S1-08`｜[P2] (A/部分) DEF-101-876 的解鎖條件①③ 已達成 — R78 確實補跑了 R77 積欠的四方複審

- **檔案:行**：docs/06_quality/CrossPlatform_R78_Review.md:1
- **成本**：small

**為何要緊（逐字）**：三項解鎖條件中兩項已達成而該列仍整筆 open，等於把一筆「大部分已還」的債繼續算在未結列裡。同時它的存在讓「R77 未經第三方複驗」這個真正還沒關的部分（條件②：skipped 治理／承接稽核覆蓋率／依賴債三包）被稀釋在一句話裡，沒有人看得出剩下的是什麼。

**當回合實測證據（逐字保全）**：

```text
實讀該檔前 14 行，檔頭逐字：「本檔是什麼：R78 對上一輪 R77 的四方獨立複審（Architect／SA／SD／QA）結果…」「為何有這一輪：R77 的四方複審**一次都沒跑**（月度支出上限，`DEF-101-876`），因此該輪所有『已修畢』皆為作者自證…R78 開場第一件事就是補跑它。」⇒ 條件① 達成且具名回指本列。條件③（重釘 MIN_TESTS）：實查 `tools/run_root_unittests.py:58` → `MIN_TESTS = 2466`，註記逐字「R80 收尾重釘…前值 2341 為 R79 值」。
```

**分流結論／建議修法（逐字）**：

```text
本輪處置：①③ 就地寫回執（引 CrossPlatform_R78_Review.md 檔頭與 MIN_TESTS=2466），把剩餘的條件② 三包拆成一句可查的殘餘描述並改派 R81。若逐包核實後三包皆有著落（skipped 治理已於 R79 落地、依賴債見 S1-20），則整列可結 `fixed@R78+R80`。**不建議直接結案**——依賴債那一包今日實測仍大面積未做。
```

### `LDG-S1-09`｜[P2] (C) DEF-101-238 今日逐字複現 — 兩份姊妹白名單仍不一致，且缺 _DENY_CHARS 第二層那一半仍在

- **檔案:行**：AutoClaude/autoclaude/execution/mutation_applier/_conditional.py:23
- **成本**：small

**為何要緊（逐字）**：該列自 R16 open，R55 收斂了 spec-fragment 消毒家族但明文「刻意不動 CONDITIONAL 家族」，於是原始缺口原封不動至今。SD 當初判定 `!` 在非互動殼無展開意義故非安全漏洞——這個判定今天仍成立，所以它是低風險；但兩份會各自演化的白名單正是 R73 主軸（同一份知識住兩個家）的活標本。

**當回合實測證據（逐字保全）**：

```text
實查兩處：`execution/mutation_applier/_conditional.py:23` → `_SAFE_COND_PATTERN = re.compile(r'^[\w\s\-./=:!"\']+$')`（**含 `!`**），且全檔 grep `_DENY_CHARS` 零命中（只在 :39 用 `_SAFE_COND_PATTERN.match`）；`core/services/mutation/_conditional_evaluator.py:28` → `^[\w\s\-./=:'\"]+$`（**不含 `!`**）、:30 → `_DENY_CHARS = frozenset("!`$~><|&;()*?\\\n\r\t")`。R55 抽出的 SSOT `autoclaude/utils/shell_deny_chars.py:14 BASE_DENY_CHARS = frozenset("!`><~$&;")` 只被 `goal_freeze_gate.py:19` 與 `sdd_to_playbook_adapter.py:31` 消費，CONDITIONAL 家族兩支都沒接。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：把 `execution/mutation_applier/_conditional.py` 的白名單字元集與 `_conditional_evaluator.py` 對齊（移除 `!`），並補上同一份 `_DENY_CHARS` 第二層；或更好——兩支都改讀 `autoclaude/utils/shell_deny_chars.BASE_DENY_CHARS` 的顯式聯集寫法（R55 已建立的判例）。加一支逐字元集合相等的 parity 測試。
```

### `LDG-S1-10`｜[P2] (C) DEF-101-055 今日以真 PG 實測複現 — ORM CheckConstraint 名與 DB 實際名仍分歧

- **檔案:行**：AutoClaude/autoclaude/infra/repositories/_pg_models.py:74,138
- **成本**：small

**為何要緊（逐字）**：該列自 R? 起 open，原判定是「cosmetic、PG 未上線無急迫」。但 PG 現在是本機長駐且 alembic 已在鏈頭（記憶 local-env-docker-postgres），前提已從『未上線』移動。實害仍如原文所述：任何 migration 寫 `DROP CONSTRAINT ck_playbook_runs_status` 會在真 DB 上失敗。

**當回合實測證據（逐字保全）**：

```text
當回合對本機長駐 PG 實跑 `docker exec autoclaude_pg psql -U autoclaude -d autoclaude -tAc "select conname from pg_constraint where contype='c' and conrelid in ('playbook_runs'::regclass,'knowledge_entries'::regclass) order by 1;"` → RC=0，回傳 5 列：`ck_kb_embedding_status` / `ck_runs_run_kind` / `ck_runs_three_tier_has_goal` / **`knowledge_entries_outcome_check`** / **`playbook_runs_status_check`**。ORM 側實查 `_pg_models.py:74 name="ck_playbook_runs_status"`、`:138 name="ck_kb_outcome"` ⇒ 兩個 ORM 名在真 DB 上**不存在**，分歧今日成立。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：二擇一並在帳本寫明——(甲) 開一支 rename migration 把 DB 兩個 inline CHECK 改名為 `ck_*`（與 0017/0018 的顯式命名慣例一致）；(乙) 把 ORM 宣告改成 DB 實際名。任一做完即可結案。若判定仍不值得動，正確處置是 `closed-by-decision` 並寫明理由，而不是繼續 open。
```

### `LDG-S1-11`｜[P3] (C) DEF-101-235 ① 今日複現 — dev_start.py 三處 kernel32 呼叫全檔零 restype

- **檔案:行**：tools/dev_start.py:675,973,1053
- **成本**：small

**為何要緊（逐字）**：該列自 R16 起把它記為「理論殘留無已知真實觸發」，五十餘輪未變。在 64-bit Windows 上 HANDLE 是 64 位元，預設 restype 會截斷高 32 位——今天沒炸是因為實務上 handle 值小；但這條路徑正是 dev_start 的 bootstrap 互斥鎖與 PID 存活追蹤（每次開工都跑），失效表徵會是「誤判行程已死」這種靜默錯誤。

**當回合實測證據（逐字保全）**：

```text
實查 `tools/dev_start.py`：`grep restype` → **0 命中**；同檔 `ctypes.windll.kernel32` 站點：:675 `OpenMutexW(`、:680/:977 `CloseHandle(`、:685/:979 `GetLastError()`、:973 `OpenProcess(0x1000, False, pid)`、:1051-1053 `kernel32 = ctypes.windll.kernel32` / `CreateToolhelp32Snapshot(th32cs_snapprocess, 0)`。即回傳 HANDLE 的三支 API 皆使用預設 32-bit `int` restype。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：為三支加上 `.restype = ctypes.c_void_p`（OpenMutexW／OpenProcess／CreateToolhelp32Snapshot）與對應 `.argtypes`，`CloseHandle` 的 argtypes 同步。⚠️ 前置：dev_start.py 現 1999/2000 行（見 S1-05），加註解會破棘輪 ⇒ 必須與拆分（DEF-101-398）同批，或用零行成本寫法。
```

### `LDG-S1-12`｜[P2] (C) DEF-101-596 今日複現 — hub_sync outbox 路徑仍寫死在生產碼

- **檔案:行**：AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/hub_sync.py:593
- **成本**：small

**為何要緊（逐字）**：該列 R61 明文指派、R67 因五輪零回執改派未指派，至今 20 輪沒人動。它的根因在生產碼（不是測試），所以 test_hub_sync.py 的並行競態改測試無法根治——而並行競態正是本 repo 反覆吃虧的假紅來源（[[parallel-mutation-audit-collision]]）。修法明確、範圍一支檔。

**當回合實測證據（逐字保全）**：

```text
實查該檔（R66 訂正後的正確座標）：`:589 # Real push: write anonymized text under endpoint-specific outbox.` / `:593 outbox = REPO_ROOT / "build" / "reports" / "hub" / "push-outbox" / ep.id` / `:594 outbox.mkdir(parents=True, exist_ok=True)` ⇒ 與 R66 記載逐字一致，一行未動。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：把 outbox 根目錄改為可注入參數（預設維持 `REPO_ROOT / build/reports/hub/push-outbox`），測試側傳 `mkdtemp()`。驗收＝`bash AISDLC_SDD/scripts/ci-gate.sh` 全綠。⚠️ v0.30 是 LATEST（非凍結版），不需 Copy-on-Evolve 例外。
```

### `LDG-S1-13`｜[P2] (C) DEF-101-402 今日複現 — autoclaude-ci.yml 仍不在 CI paths meta-lock 的對照表內

- **檔案:行**：AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:257
- **成本**：small

**為何要緊（逐字）**：該列查證過這不是理論盲區：`AutoClaude/tests/integration/test_sdd_bridge/` 兩支測試以 subprocess 實際消費 v0.01/v0.02/v0.05 凍結版 fsm_runtime，而 autoclaude-ci.yml 的 paths 目前只是「手動維護剛好正確」。這與 DEF-101-037→042→068(a)→391→395 同族的假綠盲區。

**當回合實測證據（逐字保全）**：

```text
實查 `_WORKFLOW_TEST_DIRS`（:257-261）逐字只有三筆：`"aisdlc-sdd-ci.yml"`、`"windows-compat-ci.yml"`、`"macos-compat-ci.yml"`。同檔另有三處 `autoclaude-ci.yml` 字串（:1072/:1080/:1085），但逐行讀取確認全部落在 `test_module_level_list_literal_paths_are_visible()` 的**合成 fixture 字串**內（`src = "_LIVE_DOCS = [\n" ...`），不是登記表 ⇒ 該 workflow 的 paths 仍零機械保護。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：在 `_WORKFLOW_TEST_DIRS` 新增 `"autoclaude-ci.yml": AutoClaude/tests` 一筆並跑通。⚠️ 該檔屬 AISDLC_SDD 子專案 scope，若本輪修復包持有面是根層則須改派並在帳本寫明具名承接者（不要再寫「轉交子專案後續輪次」——那正是 R60 判為死信的形態）。
```

### `LDG-S1-14`｜[P2] (C/D) DEF-101-758 今日複現 — dev_start 開工第一道檢查對未追蹤檔仍隱形，且 behind==0 早退未動

- **檔案:行**：tools/dev_start.py:745
- **成本**：medium

**為何要緊（逐字）**：這是 DEF-101-751/752 那個病（untracked 對掃描面隱形，害四輪四方複審全綠、git add 那刻才翻紅）長在**每次開工都會跑的第一道檢查**上。該列自 R70 open 至今零動作。

**當回合實測證據（逐字保全）**：

```text
實查 `tools/dev_start.py:744-745`：`# 只看已追蹤檔的修改：未追蹤檔不擋同步…` / `status_r = _git("status", "--porcelain", "--untracked-files=no")` ⇒ 與該列記載逐字一致。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並附三項解鎖條件（該列已寫好，逐字沿用）：(a) `-uno`→`-uall` 與 `behind == 0` 早退**一併**處理；(b) 回歸鎖須對真檔注入；(c) 鎖併入既有 `tools/tests/test_dev_start.py`（該樹檔數 shrink-only）。⚠️ 本輪不建議逕改：這是每次開工的互動流程行為變更，會產生一批新告警面，需舵手認可；且 dev_start.py 只剩 1 行 LOC 餘裕（見 S1-05）。
```

### `LDG-S1-15`｜[P1] (D) DEF-101-752 今日逐檔實測 — 11 個承接站點有 10 個仍是 tracked-only 掃描面

- **檔案:行**：tools/tests/test_windowsapps_guard_cross_consistency.py:488
- **成本**：large

**為何要緊（逐字）**：該列是 P1，根因是「掃描面政策」不是單一檔案；R70 只修了 3/14 站點就標 partial 並指派 R71，R71 實查未承接後改未指派，之後九輪無人動。它擋不住的正是 R69 那次事故的複現路徑：新增的 .py 在 git add 之前對全部把關結構性隱形。

**當回合實測證據（逐字保全）**：

```text
當回合對該列點名的站點逐檔數 `exclude-standard` 命中：test_windowsapps_guard_cross_consistency.py=0、test_windowsapps_guard_bash_parity.py=0、test_ps1_bom.py=0、test_bash32_compat.py=0、test_ps51_compat.py=0、test_windows_forbidden_filename_parity.py=0、test_find_git_bash_parity.py=0、test_workflow_permission_concurrency_lock.py=0、tools/check_gha_action_versions.py=0、tools/macos_smoke_local.sh=0；只有 AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py=1。與 R71 帳本列記載的同一組量測（當時全部為 0）一致 ⇒ R71~R80 十輪零進展。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81，並把 12 個站點依該列已排好的風險×成本序拆成可獨立驗收的小包（每包 2~3 站點，各附 untracked 探針的注入紅綠）。⚠️ 該列已標明六處「加 untracked 反而有害」的站點必須維持 tracked-only，不可一律套用。
```

### `LDG-S1-16`｜[P2] (D) DEF-101-764 今日複現核心、但「未入帳」那半邊已不成立

- **檔案:行**：tools/lib/WindowsAppsGuard.ps1:140
- **成本**：medium

**為何要緊（逐字）**：撞號今天仍在（同一 ID 指兩件事），而該列自己已誠實劃界說機械判準抓不到撞號、只能抓「引用了不存在的 ID」——所以 (b) 那道鎖蓋起來也治不了 (a)。真正的動作是 (a) 的人工改號決策，該列明說「本包不代決」。

**當回合實測證據（逐字保全）**：

```text
全樹 grep（*.py/*.ps1/*.sh）：`DEF-101-759` 今日仍同時掛在兩個不相干缺陷上——(A) pyenv-win POSIX shim：`tools/lib/WindowsAppsGuard.ps1:140`、`:159`、`:200`；(B) 心跳彙總行解析／fallback：`tools/lib/baseline_origin.py:211`、`:266`、`:555` 與 `tools/tests/test_doc_loc_baseline_freshness_r60.py:88`、`:2595`、`:2633`、`:2680`、`:2716`。掃描面：`tools/check_defect_log_crossref.py:83-105 _CROSSREF_TARGETS` 逐字仍只有 ONBOARDING.md ＋ 兩支 compat workflow ＋ SD10 文件 ＋ `docs/04_planning/ADR/ADR-*.md` glob，**零原始碼**。另實查 `grep '^| DEF-101-(759|760|761|762|763) |' docs/06_quality/` → 命中 `AutoSDD_Defect_Log_archive_51.md` ⇒ 該列所述「四筆全程未入帳」今日已為假。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並拆成兩件事：(a) 由舵手拍板改號方向（759 給站點多的 (B) 只需改 2 處，或 763 給 (B) 需改 7 處），這是需人工決策項；(b) 為 `_CROSSREF_TARGETS` 加原始碼掃描面（tracked ∪ untracked-not-ignored），附「引用不存在 ID 必紅／移除必綠」雙向注入。就地追加訂正：「四筆未入帳」已由 archive_51 消解。
```

### `LDG-S1-17`｜[P2] (A/部分) DEF-101-870 解鎖條件① 已於 R80 達成 — 兩處生產碼註解都已改成與帳本一致

- **檔案:行**：tools/lib/sdd_latest.py:36
- **成本**：small

**為何要緊（逐字）**：三項解鎖條件中的① 已達成而該列仍整筆 open、承接輪次未指派。剩餘的②（三段版號 `\d+\.\d+` 漏抓 v1.0.1 形態、與 DEF-101-500 ③⑤ 收斂）與③（具名承接者）沒人扛。

**當回合實測證據（逐字保全）**：

```text
實查兩處皆已就地訂正並具名回指本列：`tools/lib/sdd_latest.py:36-40` 逐字「🔴 R80 訂正本段原有的狀態宣稱（DEF-101-870 ①）：原文逐字寫「DEF-101-500 third item／DEF-101-521，未隨本次收斂修復，仍 open」，而當回合實查兩列**都不是 open**…現行唯一載體＝`DEF-101-870`」；`tools/tests/test_windows_forbidden_filename_parity.py:690-693` 逐字「🔴 R80 訂正本段原有的狀態宣稱（DEF-101-870 ①）…現行唯一載體＝`DEF-101-870`（三段版號漏抓本身仍未修，只是不再假裝有人在追）」。
```

**分流結論／建議修法（逐字）**：

```text
本輪：① 寫回執（引上述兩處行號）；②③ 改派 R81。②的修法很小：把 `FROZEN_VERSION_DIR_RE`／版號 pattern 由 `\d+\.\d+` 擴為支援三段，或明文 `wontfix`（凍結版目錄名慣例本就兩段）並刪掉那兩處「既知缺口」註解——後者若成立，整列可直接結案。
```

### `LDG-S1-18`｜[P2] (D) DEF-101-736 描述的問題在放大 — 「已結列殘留待辦」由 18 筆漲到 34 筆

- **檔案:行**：docs/06_quality/AutoSDD_Defect_Log.md
- **成本**：medium

**為何要緊（逐字）**：這是一個結構性黑洞：已結列的殘留待辦既進不了孤兒承接稽核（只掃未結列），warning 又不 fail，且多數已離開主檔搬進 archive ⇒ 只讀主檔的人完全看不到。18→34 表示每輪都在往裡面丟東西。同時它是**未結列數的反面**：把待辦藏進已結列可以讓 87 這個數字好看，而那正是本次訴求最該防的作弊路徑。

**當回合實測證據（逐字保全）**：

```text
當回合 `check_defect_log_crossref.py` 逐字印出：「⚠️ 已結列殘留待辦 **34 筆**（已結分類使它們結構上進不了承接稽核；真待辦請拆出獨立 DEF 列承接，敘事引述可忽略）」並列出全部 34 筆座標（:38 DEF-01-009、:41 DEF-100-002、:43 DEF-101-022 … :159 DEF-101-959）。該列開立時（R69）逐字記的是「已結列殘留待辦 18 筆」。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81，並把「逐筆判讀 34 筆是真待辦還是敘事引述」拆成一個獨立包（該列明說這屬人工判斷、超出原包授權面）。建議同時把這 34 筆的計數納入收輪報表（與未結列 87 並列印出），否則降低 87 的最省力方式就是把東西搬到這一桶。
```

### `LDG-S1-19`｜[P2] (D) DEF-101-399 的債在長大 — 兩支 compat workflow 由 935/679 行漲到 1628/1113 行，reusable workflow 仍零採用

- **檔案:行**：.github/workflows/windows-compat-ci.yml
- **成本**：large

**為何要緊（逐字）**：該列自 R50 open 三十輪，期間兩份純手動鏡射的檔案各長了六成以上，而「兩份 workflow 的 job/step 骨架是否仍鏡射」至今零機械鎖，只靠檔頭註解「改這邊記得改那邊」。這與 DEF-101-796（雙向落差）是同一個危害面的兩端。

**當回合實測證據（逐字保全）**：

```text
當回合 grep `workflow_call|composite` 於整個 `.github/` → **No matches found**（與 R50 記載的「全庫零命中」一致）。行數實測：`windows-compat-ci.yml` **1628 行**、`macos-compat-ci.yml` **1113 行**（R50 記載為 935／679）⇒ 分別 +74%／+64%。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81。務實修法不是一次抽 reusable workflow（1628 行的重構風險太大且 CI 現在跑不動無法驗），而是**先補 parity 鎖**：一支比對兩份 workflow job/step 骨架的結構測試（比照 `tools/check_script_parity.py` 的精神），讓下一次單邊漂移當場紅。抽 workflow_call 留待 CI 通道恢復後再做。
```

### `LDG-S1-20`｜[P3] (D) DEF-101-060 部分收斂 — 18 條無上限相依今日只解決 2 條，另新增 1 條

- **檔案:行**：AutoClaude/pyproject.toml:42
- **成本**：medium

**為何要緊（逐字）**：該列的核心主張（頭痛醫頭、任一條在新環境 pip install 都有連鎖破壞風險）今日仍成立，而 `mako<1.4` 正是它預言的那個實例真的發生了（R76 實測 5 支模組 ImportError）——即證據站在該列這一邊。它同時是 DEF-101-876 條件② 未完成的三包之一。

**當回合實測證據（逐字保全）**：

```text
實讀 pyproject.toml:30-134。**已解決**：`hypothesis==6.156.6`(:52)、`keyboard>=0.13,<0.14`(:92，R76 移入 hotkey extra 並加上限)。**額外新增的上限**：`mako<1.4`(:120，R76 DEF-101-838)。**仍無上限**（今日逐字）：`pytest-mock>=3.14`(:43)、`cachetools>=5.3`(:45,:122 出現兩次)、`click>=8.0`(:56)、`import-linter>=2.0`(:69)、`plyer>=2.1`(:97)、`win10toast>=0.9`(:98)、`sqlalchemy>=2.0`(:108)、`asyncpg>=0.29`(:109)、`psycopg2-binary>=2.9`(:110)、`alembic>=1.13`(:111)、`tenacity>=8.2`(:121)、`pgvector>=0.3`(:127)、`claude-agent-sdk>=0.2.110`(:134)。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81。採該列建議的 (b) 而非 (a)：新增機械檢查「無上限宣告需顯式列入白名單並附理由」（比照 `check_script_parity.py` 的 tier+reason 二元組體例），讓現況 13 條一次性登記為存量、之後新增一律要辯護。這比逐條升版驗證便宜得多，且能擋住新增。
```

### `LDG-S1-21`｜[P3] (D) DEF-101-018 的兩半分開處置 — 教學指令半邊已解、存量半邊今日實測 796 筆

- **檔案:行**：AutoClaude/pyproject.toml:35
- **成本**：medium

**為何要緊（逐字）**：存量由 R23 的 1,147 降到 796（真的有在降），且 588 筆可自動修 ⇒ 這不是無底洞。更值得注意的是那 1 筆 `F821 undefined-name`——那是可能的真 bug，被埋在 796 筆噪音裡沒有人會看到。

**當回合實測證據（逐字保全）**：

```text
當回合實跑（cwd=AutoClaude）`python -m ruff check . --statistics` → **RC=1**，`Found 796 errors`、`588 fixable with the --fix option`；分佈前五：UP045×320、E501×158、I001×87、F401×79、UP037×64，另含 **F821 undefined-name ×1**。`ruff check . -q --output-format concise` 行數 = 796（交叉核對）。教學指令半邊：根 CLAUDE.md 已於 R77 就地訂正為「只 lint 你改到的檔」並記明「對整棵樹跑今天回 rc=1、且沒有任何閘門在跑它」。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81，但拆成兩件：(甲) **本輪就查那 1 筆 F821**（`ruff check . --select F821`，成本近零，可能是真缺陷）；(乙) 存量清理分批（先跑 `--fix` 處理 588 筆可自動修的，逐檔驗 LOC 棘輪不破線——⚠️ E501 只能用行內 noqa，見 [[precommit-ruff-wholefile-vs-loc-tier]]）。
```

### `LDG-S1-22`｜[P3] (C) DEF-101-856 ② 死碼判定今日成立 — verify_token_guard_e2e.py 零 production 消費者

- **檔案:行**：AutoClaude/tools/verify_token_guard_e2e.py
- **成本**：small

**為何要緊（逐字）**：這是 DEF-101-856 六項殘留中最容易關的一項，且該列的第 ① 項已被證實在同一輪就做完（R76 收尾訂正）——顯示這一列的殘留項是可以逐項收斂的，只是沒人回來收。

**當回合實測證據（逐字保全）**：

```text
全 AutoClaude 樹 grep `verify_token_guard_e2e` 僅 7 筆命中，全部落在兩個檔內：該檔自己的 usage docstring（:17,:18,:20,:22）與 print 標籤（:107），以及它自己的單元測試 `AutoClaude/tests/tools/test_verify_token_guard_e2e.py:1,:21`。零 CI／nightly／playbook／其他模組呼叫點。
```

**分流結論／建議修法（逐字）**：

```text
本輪修（小）：刪除 `AutoClaude/tools/verify_token_guard_e2e.py` 與其單元測試，並在 DEF-101-856 就地寫回執「② 已刪，實測 Test-Path False」。⚠️ 刪除會影響 MIN_TESTS 收集數與 `check_script_parity` 登記面，須與收尾重釘同批（比照 R76 刪 reschedule_g0_gatecheck.ps1 的判例：刪除須同步 5 檔 7 處）。
```

### `LDG-S1-23`｜[P3] (D) DEF-101-243 ② 今日複現 — README badge 與 CLAUDE.md 日期仍是純人工欄位

- **檔案:行**：AutoClaude/README.md
- **成本**：small

**為何要緊（逐字）**：該列的 ①③ 已於 R19 修復並經 R22 校正核實，只剩 ② 這一項拖了六十輪。它是典型的「單項殘留把整列釘在未結」——而 ② 本身的成本很低。

**當回合實測證據（逐字保全）**：

```text
全 repo grep `sprint-verified|sprint_verified` → 8 個檔命中，逐一檢視：`AutoClaude/README.md`（badge 本體）＋ 7 份文件／帳本／archive（皆為記載本缺陷的敘述）。**零命中任何 .py 驗證腳本**——與該列 R18 記載的量測結果一字不差。對照組：pytest 基線數字有 `tools/check_pytest_baseline_sites.py` 機械鎖。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 或本輪修（小）：二擇一——(甲) 比照 `check_pytest_baseline_sites.py` 加一支日期新鮮度告警；(乙) 明文 `wontfix`／刪掉那個 badge（若沒有人在維護，一個永遠停在某個 sprint 的 badge 本身就是假事實）。我傾向 (乙)：加鎖去守一個沒人在讀的欄位是負收益。
```

### `LDG-S1-24`｜[P3] (D) DEF-101-268／296 需舵手拍板 — repo-wide 停寫 bytecode 的決策至今未做

- **檔案:行**：docs/06_quality/CrossPlatform_R78_Debt_Audit.md:145
- **成本**：medium

**為何要緊（逐字）**：這兩筆自 R25／R33 open，是「靠紀律不靠機械」的活標本——每一份 HANDOFF 都在教人手動加前綴，等於同一份知識抄了五份，而任何一次忘記就會拿到約 1/15 機率的假紅。同時 sync_onboarding_baselines 明文說加了會改變量測值 ⇒ 這不是無腦全開就好的事。

**當回合實測證據（逐字保全）**：

```text
全 repo grep `dont_write_bytecode|PYTHONDONTWRITEBYTECODE`：**無任何 conftest.py 設定 `sys.dont_write_bytecode`**；命中全屬 (a) 個別測試內的子行程 env（test_archive_defect_log.py:1491,:2591、test_platform_utils_dedup.py:1010）、(b) 五份 R76~R80 HANDOFF 文件的手動指令前綴、(c) 帳本／證據檔敘述。`tools/sync_onboarding_baselines.py:1088` 更逐字寫「⚠️ 刻意**不加** PYTHONDONTWRITEBYTECODE=1…加了會量到不同的數字」。`CrossPlatform_R78_Debt_Audit.md:145` 已把這兩筆列為「需人工決策」。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並標「需掌舵者拍板」（本 repo 對此類已有既定分流）。拍板選項三選一：(甲) conftest 設 `sys.dont_write_bytecode = True` 但把 sync_onboarding_baselines 的量測路徑排除；(乙) 只在四方複審／並行 agent 作業型態下設；(丙) 明文 `wontfix` 並把手動前綴收斂成一個腳本（消滅五份 HANDOFF 複本）。
```

### `LDG-S1-25`｜[P3] (D) DEF-101-338 今日複現 — 4 支疑似測試污染的假 SHA 檔仍被 git 追蹤

- **檔案:行**：AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/drift/COMMIT-sha-low.yaml
- **成本**：medium

**為何要緊（逐字）**：根因（某支測試沒用 tmp_path，把產物寫進真 repo 路徑並被 commit）從未被查。留著的代價不只是 4 個垃圾檔——那支測試如果還在跑，每次都在污染工作樹，而該樹是凍結版（Copy-on-Evolve），漂移在這裡特別難察覺。

**當回合實測證據（逐字保全）**：

```text
當回合實跑 `git ls-files "AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/drift/COMMIT-*"` → RC=0，5 筆：`COMMIT-769eea4e3f66.yaml`（真 SHA 形態）＋ `COMMIT-sha-3rd.yaml`／`COMMIT-sha-high.yaml`／`COMMIT-sha-low.yaml`／`COMMIT-testsha-001.yaml`（假 SHA 形態）⇒ 與 R60 round 2 的實查結果一字不差，二十輪未動。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81。解鎖條件（該列已寫好）：在 v0.01 樹內找出寫這些檔的測試、確認是否缺 tmp_path fixture。⚠️ 該樹為凍結版，若須改測試碼得走 Copy-on-Evolve 例外核准（歷來三次例外皆經舵手明文核准）。若判定不值得動，正確處置是 `closed-by-decision`＋把 4 檔加進 .gitignore 並 `git rm --cached`。
```

### `LDG-S1-26`｜[P3] (D) DEF-101-336 今日複現 — 凍結版禁改機械鎖仍不存在

- **檔案:行**：docs/06_quality/AutoSDD_Defect_Log.md:69
- **成本**：medium

**為何要緊（逐字）**：該列揭露的是「凍結基線鐵律曾被實際打破而無機械訊號攔截」（commit 687abac 選擇性回改 28 份凍結版）。歷輪已三次經舵手核准打破 Copy-on-Evolve（R44/R45/R46）⇒ 這件事會再發生，而今天仍然是零訊號。

**當回合實測證據（逐字保全）**：

```text
當回合對 `tools/**` 全樹 grep `禁止 commit|禁止提交|forbid.*commit|frozen.*commit` → 6 筆命中，逐一檢視全部屬 R79 auto-pilot「無人看管那一跑不准 commit/push」的守衛（`tools/session_resume_planner.py:243,:262`、`tools/tests/test_adr_xplat001_c1c2_lock.py:917`、`test_check_hooks_liveness.py:1099`、`test_context_budget_guard.py:1562`），**與凍結版一行關係都沒有** ⇒ 該列 R60 round 2 記的「零命中」在語意上今日仍成立。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並標「需先拍板政策」。該列自己已寫明關鍵約束：鎖**不可寫成無條件硬擋**（歷來三次核准例外），須留「使用者核准例外」通道——建議形態＝pre-commit 對 `AISDLC_SDD/AISDLC_SDD_v0.[0-2]*/` 路徑的改動要求 commit message 帶具名例外標記，否則 rc=1。
```

### `LDG-S1-27`｜[P3] (D) DEF-101-388 今日抽驗複現 — 凍結版 FF-17 斷言未回補，且解鎖需 Copy-on-Evolve 例外

- **檔案:行**：AISDLC_SDD/AISDLC_SDD_v0.10/tools/arch_fitness/arch_fitness.py
- **成本**：medium

**為何要緊（逐字）**：影響面窄（只影響 `SDD_FW_VERSION=v0.05~v0.29` 這個 debug/二分定位用途），但它是 25 個凍結版同時失效，且解鎖需要舵手授權——沒有授權就永遠是孤兒。放著不管的成本是：下一次要二分定位歷史版本時才發現這條路不通。

**當回合實測證據（逐字保全）**：

```text
抽驗 v0.10（該列具名的重現版本）：`grep 'sort -V|tail -1|sdd_version'` 於該檔 → **4 命中** ⇒ 舊 glob 慣用語仍在，未改為 SSOT `sdd_version.py` 解析。該列 R74 已補承接指派＝未指派，解鎖條件＝取得 Copy-on-Evolve 例外授權。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並標「需舵手核准 Copy-on-Evolve 例外」。若舵手不核准，正確處置是 `closed-by-decision`（明文接受這 25 版的 debug 路徑不可用並在 ci-gate.sh 檔頭寫明），而不是繼續掛未指派——那是本 repo 明文禁止的散文式延後。
```

### `LDG-S1-28`｜[P2] (D) DEF-101-803 主症狀已治、狀態欄未跟上 — 遞迴斷點已落地但 :1330 仍寫「結構性修法未做」

- **檔案:行**：tools/tests/test_run_root_unittests.py:1330
- **成本**：small

**為何要緊（逐字）**：該列 R79 判定「結構性修法仍未落地」——那個判定今天只對了一半：造成 823s→3813s 爆炸與 TimeoutExpired 的遞迴主因已被斷掉，剩下的是「外層仍跑一次整棵樹」這個較弱的殘留。維持原描述會讓下一個承接者以為要重做一次已經做完的事。

**當回合實測證據（逐字保全）**：

```text
實讀 :1320-1354：R79 記載的「硬編 timeout=300」已不存在，現為 `_ZERO_DEP_PROBE_ENV = "RRU_IN_ZERO_DEP_PROBE"`(:1337) ＋ `_ZERO_DEP_PROBE_TIMEOUT = 600`(:1338)，且 :1332-1336 逐字記載「本輪實測到的真正主因是遞迴…正解是斷遞迴——子行程帶 `_ZERO_DEP_PROBE_ENV` 旗標，本類別見到旗標即自我 skip」，:1346 `child_env = {**os.environ, _ZERO_DEP_PROBE_ENV: "1"}` 已接線，:1447 亦有對應 skip。**但** :1330 逐字仍寫「結構性修法（探針不應在套件內重跑整套）已登記 DEF-101-803，承接輪次見該列」。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81 並**就地下修描述**：把「結構性修法未落地」訂正為「遞迴主因已於 R79/R80 斷掉（`_ZERO_DEP_PROBE_ENV`），殘留＝外層探針仍跑一次整棵樹」。若判定殘留可接受，本列可直接 `closed-by-decision`——這是本次盤點中最接近可結案的 partial 列之一。
```

### `LDG-S1-29`｜[P2] (D) DEF-101-701／746 — MIN_TESTS 已釘 2466，但註記自陳判準仍有一半未滿足

- **檔案:行**：tools/run_root_unittests.py:58
- **成本**：medium

**為何要緊（逐字）**：兩列講的是同一個結構衝突（「重釘取當下實測」× 「收輪是多波次」），歷輪已留下 756/845/994/1063/1318/1343/1526/1557/1580/1581/1588/1592/1594/1819/1979/2105/2201/2284/2341 這一長串中途值 ⇒ 這是已重演十餘次、且每次都被誠實記下卻沒人修的模式。

**當回合實測證據（逐字保全）**：

```text
實查 `MIN_TESTS = 2466`（R80 收尾重釘，前值 2341 為 R79）。同行註記當回合逐字自陳：「🔴 **本行自己的判準仍有一半未滿足，照實記**：R80 四方複審跑了兩審、blocking 全收斂，但二審收斂包與本收尾包其後落地的改動**沒有再被第三方看過**…依成熟度判準 M3『作者自證不計分』，那一段仍是自證。」DEF-101-746 要求的「把判準寫成可注入紅綠的檢查」在該檔內無對應實作。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81（兩列合併承接）。可直接執行的修法（DEF-101-701 已寫好）：重釘量測前後各取一次**含內容**的工作樹指紋（`git status --porcelain` ＋ `git diff HEAD` ＋ untracked 內容雜湊）並要求不變才放行，把它接進 `tools/run_root_unittests.py` 的重釘路徑。另 DEF-101-701 的 R69 補記要求把 MIN_TESTS 的兩個角色解耦（下限 vs 零相依探針鑑別門檻）——那一項因 S1-28 的遞迴斷點落地已降低急迫性，可一併重評。
```

### `LDG-S1-30`｜[P2] (D) DEF-101-676 容量結構解仍未做 — 而今天的洩壓歸檔正好再次實證它的論點

- **檔案:行**：tools/lib/defect_ledger_index.py:580
- **成本**：medium

**為何要緊（逐字）**：未結列 87 逼近 fail 線 98，而未結列結構上不可歸檔 ⇒ 歸檔對本次訴求零幫助（舵手已指出）。真正的出路只有真結案／改派，而這一列是「為什麼容量會一直回來」的根因載體。

**當回合實測證據（逐字保全）**：

```text
該列自訂雙條件＝「單輪吞吐 ∧ 健康餘裕**同時**成立」，並點名 26KB 級槓桿（歸檔索引 bullet 與 archive 標頭去重）自 R68 起一行未動。今日證據：舵手洩壓歸檔到 231,742 bytes 之後，`check_defect_log_crossref.py` 立刻因三筆過期豁免 rc=1（見 S1-01），而該檔 :580 的註解正記載上一輪同型事件（「四筆已於本輪開場搬進 archive_63…豁免過期」）⇒ 「輪替機制自身是單調成長源／每次釋出都要付索引與訂正成本」這個論點今日第 N 次成立。
```

**分流結論／建議修法（逐字）**：

```text
改派 R81。務實下一步不是重做結構解，而是先把 S1-01 的三筆過期豁免清掉（那是今天的紅），再把「歸檔 --apply 每次新增約 1.1KB 索引」這個成本做成可觀測：讓 `--plan` 同時印出「本次釋出 X bytes／新增索引 Y bytes／淨 Z」。淨值長期為負才是真的解。
```

### `LDG-S1-31`｜[P3] (D) DEF-42-001 逾 130 天零回執 — routed 卻無承接者，且標的在凍結版 v0.17

- **檔案:行**：AISDLC_SDD/AISDLC_SDD_v0.17/tools/fsm_runtime/tests/test_file_lock.py
- **成本**：small

**為何要緊（逐字）**：這是全部 87 筆未結列中**最老的一筆**（與 DEF-53-001 並列）。它是 `routed`（已分流待修）卻沒有任何分流去向的執行者，而標的在凍結版 v0.17 ⇒ 依 Copy-on-Evolve 本來就不會被修。它佔著一個未結列名額，且讓「routed」這個狀態字失去意義。

**當回合實測證據（逐字保全）**：

```text
帳本列（發現日期 2026-06-21，狀態 `**routed**（archive_01 improving_42 段；非回歸 flaky）`）自立帳起無任何輪次回執。當回合實查標的檔存在：`Test-Path AISDLC_SDD\AISDLC_SDD_v0.17\tools\fsm_runtime\tests\test_file_lock.py` → **True**。該列自述「主 agent 隔離 3/3 全綠 → 確認非回歸」。
```

**分流結論／建議修法（逐字）**：

```text
需舵手拍板二擇一：(甲) `closed-by-decision`——凍結版依 Copy-on-Evolve 不改、且已確認非回歸（flaky 且隔離下 3/3 綠），寫明「凍結版 flaky 不修，LATEST 若復發另立新列」；(乙) 具名改派 R81。我建議 (甲)：這筆的實質內容是一個 130 天前在一個凍結版上觀察到的 flaky，沒有任何人會去修它，繼續 routed 是假的。未結列 −1。
```

### `LDG-S1-32`｜[P3] (D) DEF-53-001 逾 130 天零回執 — latent 判定今日仍成立（零 runtime 消費者）

- **檔案:行**：AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/hub_merge.py:87
- **成本**：small

**為何要緊（逐字）**：與 S1-31 同為最老的兩筆。原文已說明「無 runtime 消費者、無活路徑可觸發（latent）」，同家族的 DEF-CLDREV-030（hub_sync yaml 大小上限）早已 fixed@v0.20 ⇒ 剩下的這半邊是一條死路徑上的理論風險。

**當回合實測證據（逐字保全）**：

```text
當回合實查 LATEST（v0.30）：`hub_merge.py` 有 `:67 def _read_yaml`、`:87 def detect_conflict`，**`resolve_or_record` 已不存在任何 def**。跨全樹（排除 v0.01~v0.29 凍結版）搜 `detect_conflict|resolve_or_record` 的呼叫端 → 僅 `AISDLC_SDD_v0.30/tools/fsm_runtime/tests/test_hub_sync.py:628,642,659,679,703`（測試）與 `hub_merge.py:21,22,87`（自身 import/def）⇒ **零 runtime 消費者**，該列 R? 的 latent 判定今日逐字成立。
```

**分流結論／建議修法（逐字）**：

```text
需舵手拍板二擇一：(甲) `closed-by-decision`——latent、零 runtime 消費者、同家族已修，若未來 `detect_conflict` 被 wire 進 runtime 再重開新列；(乙) 本輪順手為 `_read_yaml` 加讀取上限（成本極小，一支檔一個常數），做完直接 `fixed`。我建議 (乙)：比拍板便宜，且能真正消滅一筆。未結列 −1。
```

### `LDG-S1-33`｜[P2] (B/部分) DEF-101-798 的兩半今日一真一假 — 掃描器覆蓋那半已被推翻，hook 橋接那半仍為真

- **檔案:行**：.claude/settings.json
- **成本**：small

**為何要緊（逐字）**：半邊為假卻整列 open，會讓下一輪有人去補一支已經存在的鎖（本 repo R80 剛因「低報分子」吃過這個虧）。而仍為真的半邊 R79 已判定屬「需掌舵者拍板」（把 4 支橋進根層＝改變每個根 session 的 PreToolUse deny 面，該檔自記過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0）。

**當回合實測證據（逐字保全）**：

```text
**已為假的半邊**：該列主張「鐵律三的 8 項觸發清單只有 4 項有掃描器」——根 CLAUDE.md 該表今日已擴到 13 列且多數具名機械物（`test_platform_neutral_paths.py` 的 TestWorktreeEolMatchesPolicy／TestShebangImpliesLfLineEndings／TestNaiveLocalTimestampsAreNotPersisted／TestExecBitIsGovernedViaTheGitIndex／TestDirEntryPrimitivesAreAccountedFor／TestPowerShellPlatformSensitiveSites 等），且 R80 已把「自陳沒人守的宣稱必須通過證偽探針」做成 `TestIronLaw3NoMechanismClaimsAreFalsifiable`。**仍為真的半邊**：當回合逐字解析根 `.claude/settings.json`，其引用的 hook 腳本為 `_hook_launcher.py／audit_session.py／block_bash_on_windows.py／check_ps1_encoding.py／check_sh_eol.py／context_budget_guard.py／hook_wiring.py／lint_powershell_command.py／sdd_hook_router.py／session_resume_planner.py`（＋3 支測試檔名）；對 `enforce_docs_path.py／loc_budget_check.py／check_lang.py／claude_md_freshness.py` 四個字串**全部 False** ⇒ 仍未橋接。
```

**分流結論／建議修法（逐字）**：

```text
本輪：就地追加訂正，把「8 項只有 4 項有掃描器」標為已被 R74~R80 推翻（引根 CLAUDE.md 現行表與 TestIronLaw3NoMechanismClaimsAreFalsifiable）。剩餘半邊改派 R81 並標「需掌舵者拍板」，逐支風險評估已在 `CrossPlatform_R79_Debt_Audit.md` 的 `## DEF-101-798` 節。
```

### `LDG-S1-34`｜[P2] (A/確認) DEF-101-755 條件(a) 今日在 Windows 真機再次驗證通過 — 只剩結構上不可達的 (b)

- **檔案:行**：tools/tests/test_dev_start.py:5304
- **成本**：small

**為何要緊（逐字）**：R71 已驗過一次、R80 之後今天再驗一次仍綠 ⇒ 修復是穩定的，不是一次性僥倖。這筆卡住的唯一原因是解鎖條件寫死了一條今天走不通的驗證管道（GitHub Actions 帳務）。

**當回合實測證據（逐字保全）**：

```text
當回合 Windows 11 真機實跑 `python -m unittest test_dev_start.TestGetPythonGeMinPowerShell -v` → **Ran 4 tests in 0.666s，OK，RC=0**，四支逐一列出且**零 skip**：`test_fake_39_shim_is_live_so_the_version_check_is_what_rejects_it`（正控）、`test_ps1_wrapper_delegates_and_wires_fail_loud`、`test_remediation_lists_actionable_commands`、`test_skips_sub_311_candidate`（即 R71 移除 `@skipIf(os.name == "nt")` 的那一支）。條件 (b)「於 Windows CI 實跑一次並附 skip 明細取證」：見 S1-07，最新 push run 的 windows job steps=0 ⇒ 通道不通。
```

**分流結論／建議修法（逐字）**：

```text
二擇一並在帳本明說：(甲) 結案 `fixed@R71`，把 (b) 降級為「CI 恢復後的順帶複核」而非結案前置——理由是條件 (a) 走的路線讓 (b) 的原始關切（Windows 上該類是殭屍）已被真機直接反證；(乙) 維持未結但改派 R81 並與 S1-07 的四筆一起標為外部阻塞。⚠️ 該列另記載一筆待修的過度宣稱：`tools/tests/test_dev_start.py:5346` 的 docstring 逐字寫「R71（DEF-101-755 結案）」而帳本說未結——無論走 (甲)(乙) 都要同批訂正這一處。
```

## §3 本路 `verified_commands`（逐字保全）

```text
全部指令皆以 PowerShell 工具執行（禁 Bash 工具），rc 一律不接管線取得。

1. `& "D:\CursorProject\AISDCL_Agent\.venv\Scripts\python.exe" "D:\CursorProject\AISDCL_Agent\tools\check_defect_log_crossref.py" --unresolved-count` → **rc=0**；輸出「未結列數＝87／全部 125 列｜warn=86 fail=98」＋87 筆 ID 清單
2. `& $py "D:\...\tools\check_defect_log_crossref.py"`（完整檢查） → **rc=1**；`❌ 帳本體積與逐列位元組上限（3 筆）`（DEF-01-007／DEF-101-274／DEF-101-422 豁免過期）＋7 筆 fail-open 窗口 warning＋「已結列殘留待辦 34 筆」
3. `& $py "D:\...\AutoClaude\tools\check_loc_budget.py"` → **rc=0**；`violations=0 (absolute=0 tier=0 special=0 root_tools=0 total=0)`、`[special<=2000] ../tools/dev_start.py: 1999（餘裕 1 行）`、`[ROOT-TOOLS-WARN] guardrail_cli<=750 / guardrail_lib<=400`
4. `& $py -c "...len(...read_bytes().split(b'\n'))"` on tools/dev_start.py → 2000
5. `git ls-files "AISDLC_SDD/AISDLC_SDD_v0.01/build/reports/drift/COMMIT-*"` → **rc=0**；5 筆（含 4 支假 SHA）
6. `git ls-files -s` ＋ 篩 `^100755` → count755=9（逐筆列出）
7. `Push-Location tools\tests; & $py -m unittest test_platform_neutral_paths.TestExecBitIsGovernedViaTheGitIndex -v` → **rc=0**，`Ran 10 tests … OK`
8. `Push-Location AutoClaude; & $py -m pytest tests/test_shell_deny_chars_parity.py -q --no-header -p no:cacheprovider` → **rc=0**，`16 passed`
9. `Push-Location tools\tests; & $py -m unittest test_dev_start.TestGetPythonGeMinPowerShell -v` → **rc=0**，`Ran 4 tests in 0.666s OK`（零 skip）
10. `Push-Location AutoClaude; & $py -m ruff check . --statistics` → **rc=1**，`Found 796 errors`、`588 fixable`；`ruff check . -q --output-format concise` 行數 796（交叉核對）
11. `gh run list --limit 25 --json databaseId,name,displayTitle,event,status,conclusion,createdAt` → **rc=0**；最新 push（2026-08-08T11:14:50Z）7 支 workflow 中 6 支 failure
12. `gh run view 31254543751 --json jobs` → **rc=0**；windows-compat-ci 三 job 皆 `steps=0`、2 秒、failure/skipped（帳務停擺指紋）
13. `docker exec autoclaude_pg psql -U autoclaude -d autoclaude -tAc "select conname from pg_constraint where contype='c' and conrelid in ('playbook_runs'::regclass,'knowledge_entries'::regclass) order by 1;"` → **rc=0**；回 `playbook_runs_status_check`／`knowledge_entries_outcome_check`（非 ORM 的 ck_*）
14. 逐檔 `Select-String -Pattern 'exclude-standard'` 於 DEF-101-752 點名的 11 個站點 → 10 個為 0、1 個為 1
15. 逐字串比對根 `.claude/settings.json` 對 6 個 hook 檔名 → enforce_docs_path/loc_budget_check/check_lang/claude_md_freshness 皆 False；check_ps1_encoding/check_sh_eol 皆 True
16. Grep 工具（不經 shell）命中並逐行核對：tools/git-hooks/pre-push:62,71｜tools/dev_start.py:745,675,973,1053｜AutoClaude/tools/check_loc_budget.py:114,179,191｜AISDLC_SDD_v0.30/tools/fsm_runtime/hub_sync.py:589-597｜AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:257-261,1068-1086｜tools/lib/sdd_latest.py:33-41｜tools/tests/test_windows_forbidden_filename_parity.py:686-694｜tools/check_defect_log_crossref.py:83-108,238-260,278-281,379-388｜tools/lib/defect_ledger_index.py:550-645｜AutoClaude/autoclaude/execution/mutation_applier/_conditional.py:23｜AutoClaude/autoclaude/core/services/mutation/_conditional_evaluator.py:28,30｜AutoClaude/autoclaude/utils/shell_deny_chars.py:14｜AutoClaude/autoclaude/infra/repositories/_pg_models.py:74,138
17. Read 工具：tools/tests/test_run_root_unittests.py:1310-1369｜AutoClaude/pyproject.toml:30-134｜AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py:1040-1099｜docs/06_quality/CrossPlatform_R78_Review.md 前 14 行
18. Grep `workflow_call|composite` 於 `.github/` → **No matches found**；`(Get-Content).Count` → windows-compat-ci.yml 1628 行、macos-compat-ci.yml 1113 行
19. Grep `DEF-101-759|760|761|762|763` 於 *.py/*.ps1/*.sh → 759 同時命中 WindowsAppsGuard.ps1:140,159,200 與 baseline_origin.py:211,266,555＋test_doc_loc_baseline_freshness_r60.py:88,2595,2633,2680,2716；Grep `^\| DEF-101-(759|760|761|762|763) \|` 於 docs/06_quality → 命中 archive_51
20. Grep `dont_write_bytecode|PYTHONDONTWRITEBYTECODE` 全 repo → 零 conftest 設定
21. Grep `verify_token_guard_e2e` 於 AutoClaude → 僅自身＋自身單元測試
22. Grep `sprint-verified|sprint_verified` 全 repo → 8 檔，零驗證腳本
23. `Select-String 'run_root_unittests.py' MIN_TESTS` → `MIN_TESTS = 2466`
24. Get-ChildItem 遞迴定位 hub_merge.py／run_tlc.ps1／run_self_evolution.ps1；Select-String `detect_conflict|resolve_or_record` 排除凍結版 → 僅測試呼叫
25. `Select-String -Pattern 'sort -V|tail -1|sdd_version'` 於 AISDLC_SDD_v0.10/tools/arch_fitness/arch_fitness.py → 4 命中
```

## §4 本路 `honest_gaps`（逐字保全）

```text
我沒能驗證的部分，逐項列出：

**1. 87 筆只逐筆讀完全部、實查驗證了約 40 筆；另約 47 筆只讀了帳本原文未做磁碟複驗。** 未複驗的多數是已具名承接 R81 的列（DEF-101-886/887/889/936/938/941/947/950/951/960/961/967/974）——它們的 (D) 條件已滿足，不是本次的瓶頸；以及純方法論記事列（DEF-101-214/217/296/308/309/313/324/333/335/348/392/398/400/401/412/610/675/693/702/733/739/746/748/769/795/796/797/802/863/867/912/917/918/919/925/926）。這些我依帳本原文分類，**沒有當回合實查證據**，不應被當成已驗證。

**2. 跨平台條件我一項都驗不了。** 本機是 Windows 11。DEF-101-740 的 macOS rc、DEF-101-755(b) 的 Windows CI skip 明細、DEF-101-796 的 mac 側對稱物、DEF-101-377 的 `.py` 行尾在 mac 側行為——全部無法取得。凡涉及 macOS 或雲端 runner 的解鎖條件，我只能報「今天走不通」，不能報「已滿足」或「不成立」。

**3. 我沒有跑根層全套 unittest，也沒跑 AutoClaude 全套 pytest。** 只跑了三個具名測試類／檔（10+16+4 支）。所以我對「這些列的修復不會打破別的東西」零證據；任何依我建議動手的包必須自己跑閘門。理由是 token 預算與「不改任何檔案」的唯讀約束。

**4. DEF-101-018 的 796 筆我只量了 cwd=AutoClaude 那一個口徑。** pyproject.toml:39-40 明文警告「AutoClaude/ 與 monorepo 根是兩個不同的量，混用就是製造下一筆 stale」——我沒量根層那個數，所以 796 只能用在 AutoClaude 這個 cwd 下。

**5. DEF-101-235 的 ③④ 兩項我沒驗完。** ③（run_local_nightly.ps1 的 nightly_latest.log Copy-Item 無重試）我只看到 :330 的註解提到「原 Copy-Item…失敗時僅於 try/catch 內降級」，沒有讀完實作判斷是否已補重試；④（PS 5.1 版本守衛在兩處逐字重複）我量到 v0.30 的 run_tlc.ps1 只有 1 處 PSVersion 命中、run_self_evolution.ps1 在 arch_fitness/ 子目錄而我未逐檔比對。故 S1-11 只報 ① 一項，③④ 狀態不明。

**6. DEF-101-876 的解鎖條件② 我只驗了「三包之一」。** 「skipped 治理」由記憶推斷 R79 已做（136→44）、「依賴債」由 S1-20 實測判為大面積未做、「承接稽核覆蓋率」我完全沒查。所以我不建議直接結案這一列。

**7. 我沒有驗證任何一筆的「結案後不會製造假事實」。** R80 有兩筆零成本可結卻刻意不關，理由是關掉會製造假事實——我在 S1-04、S1-31、S1-32、S1-34 都遇到同型抉擇，一律標成「需明說走哪一條」而不是替人拍板。這四筆若被草率結掉，就是本次訴求最可能出的錯。

**8. 我不知道 S1-01 那個 rc=1 是不是也會擋 pre-push。** 我只驗了直接執行該腳本回 rc=1，沒有實查 `tools/git-hooks/pre-push` 是否呼叫它（我讀了該 hook 的 python 候選段落但沒逐段確認呼叫面）。若它其實不在 pre-push 鏈上，S1-01 的嚴重度應由 P0 下修。

**9. 未結列的算術我沒有實跑驗證。** 我宣稱 S1-02/03 各能 −1、S1-05/31/32 各可能 −1，那是依 `_classify()` 的判準（unresolved ∈ ['None','open','routed']、`partial` 歸 open）推得的，**不是實跑 `--unresolved-count` 量到的**。實際降幾筆必須改完帳本後重跑該入口才算數。
```

## §8 姊妹檔對照表（`DEF-101-587` 體例）

`docs/06_quality/` 的具名治理文件受體積守門（fail 262,144 bytes ／ warn 245,760 bytes，
上限來源＝Read 工具單次讀取上限，與缺陷帳本是同一條物理界線）。R81 第一批的輸出量
超過單檔容量（第一版實測 253,373 bytes，已越 warn 線），故拆成**三份姊妹檔**，
三份**都**登記進 `tools/lib/governance_docs.py` 的 `_GOVERNANCE_DOCS`。
本檔＝`docs/06_quality/CrossPlatform_R81_Ledger_Triage.md`。

| 檔 | 承載 |
|---|---|
| `docs/06_quality/CrossPlatform_R81_Scan_Findings.md`（入口） | §0 誠實劃界／§1 九路全景／§2 scan:xplat 7 筆／§3 scan:subtraction 8 筆／§4 scan:skipped 12 筆／§5 scan:autoclaude-helm 10 筆 |
| `docs/06_quality/CrossPlatform_R81_Quota_Review.md` | §2 research:quota 12 筆／§3 ADR-XPLAT-005 的核心決策・實作步驟・開放問題／SA 與 SD 兩份 verdict 的逐筆 blocking 與 non-blocking |
| `docs/06_quality/CrossPlatform_R81_Ledger_Triage.md` | scan:ledger 的 34 筆未結列四類分流（A 已修好只差狀態欄／B 前提不成立／C 本輪做得完／D 本輪做不完須改派） |
| `docs/04_planning/ADR/ADR-XPLAT-005-quota-aware-throttling-and-fanout-resume.md` | ADR 全文（狀態 `Proposed`；SA 給 REJECT、SD 給 APPROVE_WITH_CONDITIONS，11 筆 blocking 未收斂前不得視為已核准） |

## §9 這三份檔為何屬於「具名治理文件」

兩項義務同時成立，與 `CrossPlatform_R80_Scan_Findings.md` 的資格相同：

1. **體積守門**——複審者要判「R81 還有哪些缺口開著」就得讀完它，所以它承擔與缺陷帳本
   同等的可讀性義務；
2. **指針稽核**——它逐筆寫出「某發現的座標在某檔某行」的宣稱，而那些宣稱會過期。

## §5 R81 包 D（缺陷帳本清債）— 被搬離帳本列的原文逐字保全

本節是 `docs/06_quality/AutoSDD_Defect_Log.md` 的**位元組洩壓出口**。`tools/lib/defect_ledger_index.OVERSIZE_ROW_EXCESS_CEILING` 是零成長容忍的棘輪，所以在一個豁免列上「追加一句結案理由」方向本身就是錯的——**結案與瘦身必須是同一個動作**（R80 包 C 判例）。以下各節是被換掉的狀態欄**原文，一個字未刪**；帳本列上只留結案字、一句當回合實查結論與指回本節的指針。

### DEF-42-001（結案：凍結版 v0.17 的 flaky，130 天零回執）

原狀態欄（逐字）：

```text
**routed**（archive_01 improving_42 段；非回歸 flaky）
```

### DEF-53-001（結案：hub_merge 讀取上限，走乙案順手修）

原狀態欄（逐字）：

```text
**routed**（latent；archive_01 審查輪八段；**註**：與 DEF-CLDREV-030〔hub_sync yaml 大小上限 fixed@v0.20〕同家族，本項 hub_merge 路徑仍 latent）
```

### DEF-101-205（結案：exec bit 由 git 索引治理）

原狀態欄（逐字）：

```text
open（記事存證）：🔴 **R68 訂正（Pkg-8，硬規則② 二擇一機械鎖上線後具名補標）**——本列自 R14 起 open 逾五十輪，原分流逐字「擇機」＝無輪號、無「未指派」、無觸發條件，是「散文式延後」這一類的代表（R68 實測：未結列中 61 筆兩者皆無）。改標**未指派**並附**可機械查**的解鎖條件：以 `git ls-files -s` 取出 mode `100755` 的檔案集合，與 `ONBOARDING.md` §6 執行權限政策句具名的 755 清單逐項互比（散文即 SSOT，手法比照本檔《格式定義》↔ `_STATUS_FIRST_WORDS` 雙向綁定），不符即 rc=1。R68 現查缺口仍成立（`grep -rn '100755\|core.fileMode' tools/*.py tools/tests/*.py` 零守門）
```

### DEF-101-271（結案：根層 tools/ 的 LOC 分級管轄）

原狀態欄（逐字）：

```text
open watch（R26 Architect 架構專項檢視發現，記事存證；不影響本輪任何機械閘門判準，四支既有治理工具本輪複跑皆綠；排入下一輪 C 軌候選，待人工決定新分級門檻後落地）。**R26 一審 Architect 追加具體觸發門檻（避免變成無限期開放式延後）**：`tools/dev_start.py` 現況 1772 行，**若未來任一輪複審實測其超過 2000 行，即升級為該輪必修**（須完成 `check_loc_budget.py` `SCAN_ROOT` 擴充與新分級門檻拍板落地，不得再以「需人工決策」為由延後）；在達到此門檻前維持 open watch 觀察。**R47 新鮮度複測**：`wc -l tools/dev_start.py`（根層 `tools/dev_start.py`，非 `AutoClaude/tools/dev_start.py`——R26 原始記載路徑略有偏差）2026-07-26 再測仍為 **1772 行**，與 DEF-101-274 R27 量測值一致；尚未升級為必修；供下一輪免重新從頭推導。🔴 **R74 補承接指派（硬規則② 合法出口②）：承接輪次＝未指派**，解鎖條件＝`AutoClaude/tools/check_loc_budget.py` 的 `SPECIAL_FILES["../tools/dev_start.py"] = 2000` 棘輪轉紅（該門檻自 R68 起**已有機械量測者**，不再依賴有人記得手測）。⚠️ 本欄先前寫下的行數與餘裕快照**已過期、勿引用**——一律以 `python tools/check_loc_budget.py --json` 現查為權威
```

### DEF-101-470（結案：shell deny chars parity 退化形態）

原狀態欄（逐字）：

```text
open（deferred）：回報者已自標 `platformRelevant=false`，本輪授權範圍限 macOS/Windows 11 相容性，故不動手。建議修法（回報者已給）：改為 `prompts=("clean step", f"step two {bad_char}")` 並斷言 `"步驟 1"` 出現在 `verdict.reason`。建議由 C 軌（AutoClaude 自身能力）工作流帳本排程處理 🔴 **R60 改派（round 1 QA-R60-04【4】／Scan-G G-03）**：本欄交棒的「C 軌工作流帳本」容器存在但零登記（實測同 `DEF-101-422`）⇒ 死信。**改派為：未指派 backlog（C 軌）**，回執規則同硬規則③。見 DEF-101-555（現居 archive_33）。
```

### DEF-101-676（瘦身＋改派：帳本容量的結構解）

原狀態欄（逐字）：

```text
**partial@R68**（🔴 **R69 P3 追記：解鎖判準已成立，但本列仍不宣稱 fixed**——本輪執行一次 `archive_defect_log.py --apply --archive-num 47 --ack-handoff DEF-101-524`（該列的交棒字樣經逐字複核只是引用 `DEF-101-517` 的解鎖條件，而該筆本身早已歸檔於 `AutoSDD_Defect_Log_archive_30.md`，搬走 524 不埋葬任何待辦），該次 `--apply` 落地當下，`--plan` 印的「距 fail 線」確實一度越過本列自訂門檻、該行由 ❌ 轉 ✅（**實數不寫在此**：每跑一次 `--plan` 當場現算，寫進散文就是下一個 stale 站點）。**但同輪其他修復包持續入帳，數小時內即再度掉回 ❌** —— 這正是本列要治的病的原形：一次性釋出買到的餘裕，會被同一輪的正常寫入吃回去。**為何仍不結案**：本列真正要治的是「單輪吞吐」與「健康餘裕」**同時**成立，而這次的餘裕是靠具名承認一列大條目換來的一次性釋出，不是結構解；原文末段點名的 26KB 級槓桿（歸檔索引 bullet 與 archive 標頭去重）一行未動。改派維持：未指派。以下為 R68 原文：🔴 **R68 收輪主控據實下修：本列自訂的可機械查解鎖條件在同輪稍後即再度不成立**——R68 十二維掃描的 9 列入帳後主檔 260777 bytes、餘裕 1367，兩次輪替（archive_45／46，釋出 10476 bytes）後距 fail 線僅約 8000，**低於本列自訂的 10240 健康門檻**。本輪選擇據實下修狀態，而非再具名承認更多列去把數字湊過線——湊數字正是本列立這條判準要防的事，且 R67 round 4 已因「量測快照當判準」被四方交叉命中過一次。**政策解本身確實落地且有效**（動工前可搬 0 筆＝結構性死結，現已能在輪中反覆 `--apply` 釋出容量，本輪兩次輪替即為實證），但「單輪吞吐」與「健康餘裕」是兩件事：前者已解，後者未達。**改派為：未指派**。解鎖條件維持原判準不變（`--plan` 的「搬後主檔約 N bytes」距 fail 線 ≥ 10240），下一個已識別槓桿見本列原文末段與 R68 專責 agent 交回的 not_solved #2：44 條歸檔索引 bullet 佔約 37400 bytes、且每次 `--apply` 再加約 1300，讓 bullet 與 archive 標頭去重估可回收約 26KB。以下為原 `fixed@R68` 敘述逐字保留：R68 專責 agent 落地；本欄原為 `open（**未指派**…）`，R67 round 4 所訂之可機械查解鎖條件——「`--plan` 印出的『搬後主檔約 N bytes』距 fail 線 ≥ 10240」——已成立並改由程式常數 `archive_defect_log._UNLOCK_HEADROOM_BYTES` 現算，見下）。**三條候選方向逐條實評結果**：**①（判準③ 由硬擋改為搬走時訂正指針）＝採納，但改寫成根因解**：真正的缺口不在判準太嚴，而在 `check_defect_log_crossref._load_ledger_status()` **只讀主檔** ⇒ 任何被掃描目標宣稱過的列一經歸檔，`_scan_target()` 就報「帳本查無此 ID」，歷輪遂用「不准搬」去繞「搬了會假紅」。R68 補上 `_load_archive_status()`（每份 archive 各以**自己的表頭**定位狀態欄，不沿用主檔 layout），帳本 SSOT 至此才真的是它一直宣稱的「主檔 ∪ archive 家族」；判準③ 隨之由 blocker 改寫為事後條件「搬後宣稱仍解析得到」，並新增 `--check` 判準(8) 逐筆實跑驗證（**不是把檢查刪掉**——刪掉才是本工具立帳要消滅的「宣稱一道機械檢查存在而它不存在」）。**實測釋放 11 筆／16217 bytes**（原本**只**被判準③ 擋著）。**②（未結列搬進 open-backlog archive、主檔只留指針）＝駁回**，理由是它會讓兩條硬規則同時瞎掉：(甲) `orphan_backlog_problems()`（硬規則②，R67 才落地）的輸入是**主檔全文**，未結列一旦搬出主檔，孤兒承接輪次偵測對「唯一需要偵測的那一群」變成零檢查；(乙) 未結項才是每輪開工必讀的那一半，搬走只留指針等於要求讀者多讀一支檔——而容量問題的成因恰恰是「一次讀不完」，換個地方放並沒有解決它。駁回鎖：`tools/tests/test_defect_log_capacity_policy_r68.py::TestOpenBacklogArchiveIsRejected`。**③（檢討硬線 262144）＝駁回，且已實測反證「R67 的認知過期」這個假設本身**：2026-08-01 於 macOS 26.5.2 arm64 真機對 Read 工具實跑探針，2097152 bytes 檔回 `File content (2MB) exceeds maximum allowed size (256KB).`、307200 bytes 檔回 `File content (300KB) exceeds maximum allowed size (256KB).`，兩發皆在**還沒讀到內容**時即被工具拒絕、訊息逐字載明 256KB ⇒ 硬線綁的確實是當下仍生效的工具事實，**不是政策自由度**。調高它不會讓帳本變好，只會讓主檔變成任何 agent 都無法單次完整讀取的檔（讀者被迫分段讀又不知漏了哪些列＝靜默失效，比撞閘門壞）。已加常數 `gate._READ_TOOL_MAX_BYTES` ＋ 鎖 `TestHardLineIsToolFact` 綁死兩者相等。**④（不在原三條內，R68 現查新增的真正大宗）**：判準② 是對**整個狀態欄**的裸子字串掃描，實測 16 筆已結列（39705 bytes）命中的字元分屬三類與本列現況無關的東西——(a) 程式碼片段裡的 Python 內建函式 `open`（`DEF-101-391` 的 `yaml.safe_load(open(...))`、`DEF-101-524` 的 `open(..., newline=\"\")`）；(b) **引述本列自己被推翻的舊狀態**（`DEF-101-554` 的「本欄原文為『open（待主控還原）』」、`DEF-101-581` 的「原記狀態 `open（未指派）`」——引述的目的正是宣告它已不成立，判準② 卻讀成還成立，語意剛好相反）；(c) 在講別的 DEF-ID。此與判準② 當初為消滅 `OpenMutexW` 誤報而加 ASCII 邊界**完全同型**，只是逸出面從「英文字母相鄰」換成「反引號／角引號內」。故收窄為「排除程式碼片段與角引號引述後仍命中」，復用工具既有基元 `_CODE_SPAN_RE`／`_CORNER_QUOTE_RE`（不另寫第二份規則）。**實測釋放 6 筆／18637 bytes**，且三道鑑別力原封不動：裸散文照樣命中、判準① 仍先要求首詞已結、判準④ 完全未動——實證 `DEF-101-521`／`524`／`554` 收窄後隨即落在判準④ 手上要求 `--ack-handoff`，安全網未破。**落地取證（2026-08-01 macOS 真機逐條實跑）**：`--apply --archive-num 44` 搬 13 筆／23150 bytes ⇒ 主檔 **260747 → 242370 bytes**（釋出 19499、索引 bullet 新增 1122）；`--plan` 現印「距 fail 線 19774 bytes｜DEF-101-676 解鎖判準（≥ 10240）：✅ 成立」；`--check` rc=0（判準(8) 實算：主檔 96 列 ＋ archive 718 列＝帳本家族解析面，四份掃描目標的狀態宣稱全部可解析且一致）；`check_defect_log_crossref.py` rc=0；`run_root_unittests.py` rc=0 零退化。**真正的解不是這 19499 bytes，而是輪替吞吐被恢復**：R68 動工前主檔 31 筆已結列中可搬 0 筆（全被判準②③ 的誤報釘住）⇒ 每輪新增只能靠當輪自己的已結列抵銷、不可搬核心單調成長；落地後**已無任何已結列被誤報型機械判準擋住**，殘餘 11 筆（22258 bytes）逐筆檢視為判準② 的**真陽性**（例：`DEF-101-565` 的 `routed@R61（執行層）`、`DEF-101-560` 的 `open（archive 側 14 列，承接輪次：未指派）` 確為本列尚存的活半邊），另 7 筆（18415 bytes）是判準④ 要求人工具名承認——**兩者都是設計上該擋，不是死結**。🔴 **誠實揭露未解部分**：主檔 242370 bytes 中有 **40776 bytes（17%）** 落在「歷史複驗註記 — 已歸檔」段，其中 44 條歸檔索引 bullet 佔 37400 bytes（平均 850 B／條），且 `--apply` 每跑一次就再加約 1100 bytes＝**輪替機制自身是一個單調成長源**（每釋出 ~1.5KB／列要付 ~1.1KB 索引）。本輪未處理：壓縮既有 44 條 bullet 會毀掉「哪支 archive 收了哪些 ID」這個讀者實際會用的索引資訊，且判準⑤ 的雙向涵蓋性檢查綁在 bullet 上；此為**下一個容量槓桿**（估可回收 ~26KB），解鎖條件：先讓 `--apply` 生成的 bullet 與 archive 標頭去重（archive 標頭已完整載明搬遷判準與逐筆 ID）後再回頭壓縮既有條目。承接輪次：**未指派**）｜🔴 **R75 容量包回執（仍不結案）**：本輪 `--apply --archive-num 57`（具名承認 9 筆判準④ 誤報，逐筆查證見該 archive 標頭的操作備註）後，`--plan` 的解鎖判準行由 ❌ 轉 ✅——**實數一律現跑 `--plan` 取得、本列刻意不寫死**，理由同上方 R69 追記。**維持不結案，且理由與 R69 追記逐字相同、本輪一項未變**：這次餘裕同樣是具名承認換來的一次性釋出而非結構解，本列原文末段點名的 26KB 級槓桿（歸檔索引 bullet 與 archive 標頭去重）仍一行未動——本輪索引檔反而再增 1587 bytes，正是本列所述「輪替機制自身是單調成長源」的第 N 次實證；且主控本輪還要再寫約 12 列，餘裕會被同輪正常寫入吃回去。依本列自訂的雙條件（單輪吞吐 ∧ 健康餘裕**同時**成立），後者仍未達。改派維持：未指派
```

### DEF-101-740（結案：pre-push 直譯器候選擴為 python→python3）

原狀態欄（逐字）：

```text
open（承接輪次：未指派）。建議修法＝加 `python3` 回退並**維持 fail-loud**（不改成 skip：軟跳過會讓整條 leg 退回「宣告有、執行者無」）。🔴 **本包刻意未動該檔的這一段**：本輪有其他 agent 併行編輯同檔，盲改會製造衝突；本包只對該檔做了 `DEF-101-742` 那一處單行修正。解鎖條件＝在無 venv 的 macOS 上實跑一次 push 前置驗證（`python`／`python3` 兩種 PATH 形態各一）並附 rc
```

### §5.9 「已結列殘留待辦」35 筆的逐筆歸屬（`DEF-101-736`）

**為什麼要有這一節**：`check_defect_log_crossref.py` 每次都會 warn「已結列殘留待辦 N 筆」，
而 `_UNRESOLVED_CLASSES` 排除 `fixed` ⇒ 這些字樣**結構上進不了承接稽核**。把待辦藏進已結列
因此可以讓 `--unresolved-count` 好看——這是本輪訴求最該防的作弊路徑。但反過來也成立：
`DEF-101-871` 已記載「每做一次首詞訂正該數就 +1」，所以**這個數字本身不是健康度指標**。
本節交出的是**判讀結果**，不是那個數字。

#### 判別法（三問，可被第三方逐筆複跑）

一筆命中屬於**敘事引述**，若下列任一成立：

1. **(a) 訂正體例**——命中詞落在「🔴 R__ 訂正首詞（原文逐字接於後／逐字保全）」之後的
   歷史原文段。本 repo 的訂正紀律要求原文一個字不刪，於是舊狀態裡的「未指派／backlog／
   下一輪」會被整段帶進已結列。這是**體例的副產物**，不是新的待辦。
2. **(b) 指向別的載體**——命中詞所在句把工作轉記到另一個 `DEF-` ID（例如
   `DEF-101-233` 引述 `DEF-101-200`、`DEF-101-726` 明寫「追貼線請看 271／274」）。
   真待辦有它自己的未結列，重複計算會讓同一件事有多個載體。
3. **(c) 落在「現象與證據」欄**——該欄記的是**當時量到什麼**，結構上不可能是待辦。

只有**三問皆否**、且命中詞是「本列現行且尚未履行的指派或解鎖條件」，才算**真待辦**。

#### 逐筆歸屬（當回合實測 35 筆）

| 類別 | 筆數 | ID（帳本行號為當回合值） |
|---|---|---|
| **真待辦** | 4 | `DEF-101-557`（狀態逐字「本輪不落機械載具…已提跨包請求。承接輪次：未指派」）／`DEF-101-560`（「fixed@R60（主檔）／open（archive 側 14 列，承接輪次：未指派）」）／`DEF-101-649`（「其產出已由 MACNIGHTLY 包交付但 **ADR 尚未回填**」）／`DEF-101-880`（「🔴 未做：R77 那組違規率未以新尺重算，下輪重跑前不得引用舊值」） |
| **待複驗** | 3 | `DEF-101-200`（分流欄「排下輪 Windows 輪」的 ensure 語意升級是否已隨 R75 訂正完成，本包未查）／`DEF-101-242`（分流欄兩項「排下輪」補測試是否已做，本包未查）／`DEF-101-550`（狀態同時有「R60 僅查證未修」與後續複驗段，本包未逐項對帳） |
| **判準假陽性** | 6 | `DEF-101-848`（命中的是函式名 `orphan_backlog_problems` 裡的 `backlog`）／`DEF-101-946`（「保留唯一無**承接**者的『候選不存在』案」在描述測試案例）／`DEF-101-959`（「拿掉**改派**出口→紅」在描述注入實驗）／`DEF-101-565`・`DEF-101-872`・`DEF-101-923`（三筆的命中落在「現象與證據」欄，即上文 (c)） |
| **敘事引述／已履行** | 22 | `DEF-01-009`／`DEF-100-002`／`DEF-101-022`／`068`／`233`／`263`／`278`／`297`／`351`／`242` 之外的其餘：`418`／`435`／`500`／`561`／`726`／`747`／`792`／`801`／`810`／`871`／`878`／`888`／`979`（逐筆命中皆落在 (a) 訂正保全段、(b) 指向別的載體，或分流去向欄的**立案當時**分流字樣） |

#### 處置（以及為什麼不是「各自新增一列」）

四筆真待辦**併入 `DEF-101-736` 承接**，不各自開新的 DEF 列。依據是 `DEF-101-856` 已建立的
判例——「同源事項優先併入既有收集列，不無條件新增」——而 `DEF-101-736` 正是「已結列殘留
待辦」這個結構性黑洞的載體本身。併入之後這四筆**進得了承接稽核**（`DEF-101-736` 是未結列，
且已具名承接輪次），可見度問題就解決了；各自開四列只會讓未結存量 +4 而可見度不變。

#### 🔴 一個當回合量到的反向事實：兩個桶是連通管

本包結掉 6 列之後，這個 warning 由 **35 筆變成 37 筆**，新增的恰是 `DEF-101-205` 與
`DEF-101-271` ——**本包剛結掉的兩列**。原因是它們的「分流去向」欄本來就寫著
「承接輪次：**未指派**」這類字樣；未結時那些字樣算在未結列身上，一旦結案就整列滑進
「已結列殘留待辦」桶。⇒ **降低未結列會抬高這個數字，兩者是同一批文字的兩種記法**。
這正好從反面印證了原始關切：若只看其中一個數字，另一個方向的移動就是免費的。
正確的讀法是兩個一起看，而它們**現在都由同一次 `check_defect_log_crossref.py` 輸出**。
