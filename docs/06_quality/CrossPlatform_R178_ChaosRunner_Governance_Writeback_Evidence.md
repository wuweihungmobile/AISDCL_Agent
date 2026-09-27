# CrossPlatform R178 — chaos_runner 裸 CLI 污染 governance/rules 根治結案證據檔

> 輪次：R178（2026-09-27，win32，Windows 11；SD/Developer 落地 Sonnet 5，主控另包）。
> 流程：設計（`R178_design.md`）＋ SA 獨立分析（`R178_sa_analysis.md`）兩份唯讀調查 → 主控裁決
> D1/D2/D3 做、D4/D5 不做 → 本 Developer 包落地＋紅綠自證 → 收尾親驗。
> 前輪：`CrossPlatform_R177_SessionGate_Recovery_Evidence.md`。本檔涵蓋 DEF-200-402（結案）、
> DEF-200-403（新立，open）。

## 一、事故時間線（既定描述；本輪未重現，governance/rules 動工前已乾淨）

`AutoClaude/logs/nightly_2026-09-26_223001.log`（逐行核實，`:722-755`）：

```
[2026-09-26 22:37:00][INFO] ===== Stage start: sdd-fsm-chaos（鏡射 aisdlc-sdd-fsm-chaos-nightly） =====
chaos sweep bounded=100/100 avg_tokens=1559.9 max_steps=13
[2026-09-26 22:37:35][INFO] ===== Stage end:   sdd-fsm-chaos（鏡射 ...）(exit=0, elapsed=00:00:34.908) =====
[2026-09-26 22:37:35][INFO] ===== Stage start: sdd-fsm-chaos-latest（DEF-200-379 觀察期） =====
[2026-09-26 22:37:35][INFO] [cpu_budget] broadcast workers=18 source=cpu_budget
chaos sweep (LATEST) bounded=100/100 avg_tokens=1573.3 max_steps=13
[2026-09-26 22:38:36][INFO] ===== Stage end:   sdd-fsm-chaos-latest（DEF-200-379 觀察期） (exit=0, elapsed=00:01:01.603) =====
```

該 61.6 秒窗口內只有一個 stage 在跑（`sdd-fsm-chaos-latest`），先跑 `pytest -m chaos`（受
`conftest.py::_isolate_rule_telemetry_default` session autouse fixture 保護，安全），再緊接著
裸呼叫 `python -m tools.fsm_runtime.chaos_runner --rounds 100 --json` 子行程（無任何遙測隔離）。
本次 nightly 的 stage `exit=0`——寫回本身不影響 rc，污染只能靠事後 `git status` 翻到，這正是本輪
新增 D3 圍籬要堵的洞。

**既定描述（本輪未重現，引自任務交辦資料，未經本 Developer 包重新量測）**：本次事故把 19 支
`governance/rules/R-9.*.yaml` 寫髒，其中一支全域規則（`trigger_states: ["*"]`，每次 transition
必命中）`fire_count` 停在 466（= 100 輪 × 平均 4.66 steps/round，與上列 log 的 `max_steps=13`／
`avg_tokens` 量級一致，屬合理外推，但 466 這個確切數字本身未在本 Developer 包重新從磁碟量測，
因為 governance/rules 動工前已是乾淨狀態——見〈六、誠實劃界〉）。

## 二、根因鏈（file:line）

| 站點 | 檔案:行 | 角色 |
|---|---|---|
| 遙測寫回入口 | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/fsm_runtime.py:386-391` | `transition()` 進態後 `if _rule_fire_telemetry_enabled():` 區塊呼叫 `rule_loader.record_state_fires(dst)`（QA P3-1 訂正：原寫 347-352 是 `transition()` 簽名處，差約 40 行） |
| D28 判準（顯式值優先） | `fsm_runtime.py:181-206` `_telemetry_writeback_allowed()` | unset 時看 `SDD_TELEMETRY_WRITEBACK_REQUIRES_HOOK`／`SDD_FSM_HOOK_ENTRY`；兩者對 nightly schtasks／GitHub Actions runner 行程樹皆不存在 ⇒ 落回 v0.24 預設 ON |
| 真規則目錄（固定、`--workdir` 不隔離它） | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/rule_loader.py:23-25` | `RULES_DIR = Path(__file__).resolve().parents[2] / "governance" / "rules"`，永遠指向真實 tracked 目錄 |
| 兩個共用入口 | `chaos_runner.py:2059`（`run_chaos_rounds()`，被 `_cli()` 與 `_chaos_b28_benchmark.py:61` 共用） | 唯一需要修的落點——兩個入口共用同一函式 |
| pytest 側既有先例（本輪修法的同構依據） | `AISDLC_SDD/AISDLC_SDD_v0.30/tools/fsm_runtime/tests/conftest.py:131-154` `_isolate_rule_telemetry_default` | session autouse fixture 把兩個遙測 env **顯式設 "0"**（不是靠 D28 hook 身分機制）——D1 照抄同一慣例，只是把它從「pytest 套件」搬到「production 呼叫端」 |

## 三、方案決策（D1～D5，詳見 `R178_design.md` §2、`R178_sa_analysis.md` §B/§C）

| 決策 | 裁決 | 落地檔案 |
|---|---|---|
| D1 源頭封殺 | **做**：`fsm_runtime.telemetry_writeback_disabled()` context manager（強制設 "0"，離開時還原原值含「原本不存在」；docstring 說明為何不用 D28 hook 身分機制），`run_chaos_rounds()` 的 round 迴圈整段 `with` 包住 | `fsm_runtime.py`（新增 import + 函式）、`chaos_runner.py`（import 改一行 + 迴圈縮排進 `with`） |
| D2 行為鎖 | **做**：兩層測試——子行程沙盒 CLI（端到端證據）＋ in-process（沿用 `test_rule_fire_telemetry_wiring.py` 的 `_rules_copy` 先例，日常回歸鎖主力） | 新檔 `tools/fsm_runtime/tests/test_chaos_runner_no_governance_writeback.py` |
| D3 nightly 圍籬（第二道防線） | **做**：`sdd-fsm-chaos-latest` stage 內、chaos-report 解析後、`Pop-Location` 前，`git status --porcelain -- 'governance/rules'` 非空即 ERROR + `$global:LASTEXITCODE = 1`（保留圍籬前的真實 rc，不被 git 原生呼叫自身 exit code 覆寫） | `AutoClaude/tools/run_local_nightly.ps1`；靜態鎖 `AutoClaude/tests/tools/test_run_local_nightly_static.py` 新增 `test_sdd_chaos_latest_stage_fences_governance_rules_writeback` |
| D4 翻 D28 預設或加「非可信入口一律拒絕」 | **不做**：翻預設會讓裸終端 CLI 驅動 FSM 的正常使用情境靜默退化成不記帳，且會撞上 43 處釘住 `unset→ON` 的既有測試 | — |
| D5 雲端 workflow 圍籬 | **不做**：GitHub Actions runner 是拋棄式檔案系統，寫回不會被 commit／push，D1 落地後 `chaos-latest` job 下次跑自動繼承修復 | — |

**明確不做**（見 §6）：補齊 `run_local_nightly.sh` 的整條 `sdd-fsm-chaos-latest` stage（DEF-200-379
遺留的既有 parity 債，範圍遠大於本輪圍籬，另立 DEF-200-403）；改動 `_chaos_b28_benchmark.py`
本身（呼叫 `run_chaos_rounds()` 自動繼承修復）；新增獨立 `governance/rules/R-9.x` 治理規則
YAML（比照 DEF-200-285／D28 先例，不無中生有新增規則）。

## 四、紅綠自證（逐字，本場 tool_result）

### D2（子行程沙盒＋in-process，`tools/fsm_runtime/tests/test_chaos_runner_no_governance_writeback.py`）

**綠（防線在）**：
```
[sdd-docker-probe] controller docker_available=True
..                                                                       [100%]
2 passed in 3.30s
```
（第一次跑時子行程沙盒因 `state_loader.py:57` 委派 `AISDLC_SDD/scripts/component_sanitizer.py`
這支跨版本共用 SSOT 而 `FileNotFoundError`——沙盒 fixture 補上該檔複本後即通過；詳見設計書
§4「未證實」項的落地結果。）

**紅（拿掉 `chaos_runner.py` 的 `with telemetry_writeback_disabled():` 一行，迴圈退縮排）**：
```
FF                                                                       [100%]
...
E       AssertionError: governance/rules/*.yaml 被裸 CLI 子行程寫回——telemetry_writeback_disabled() 防線失效（DEF-200-402 迴歸）
E       assert {'R-9.1-fsm-r...36830b7', ...} == {'R-9.1-fsm-r...36830b7', ...}
E         Differing items:
E         {'R-9.18-formal-halt-verification-m5.yaml': 'a050f8714a3d...'} != {'R-9.18-formal-halt-verification-m5.yaml': 'c435750e10f6...'}
...
E       AssertionError: governance/rules 複本被 in-process 呼叫寫回——telemetry_writeback_disabled() 防線失效（DEF-200-402 迴歸）
...
2 failed in 5.01s
```
真實樹 `git status --porcelain -- AISDLC_SDD/AISDLC_SDD_v0.30/governance/rules` 在紅、綠兩次跑
前後皆為空字串（沙盒隔離生效，未觸碰真實 tracked 目錄）。

**改回防線（用 Edit，非 git 還原）後重跑**：`2 passed in 1.81s`。

### D3（`AutoClaude/tests/tools/test_run_local_nightly_static.py::test_sdd_chaos_latest_stage_fences_governance_rules_writeback`）

**紅（暫時拿掉 ps1 圍籬段）**：
```
F                                                                        [100%]
E       AssertionError: Stage 6b 必須含 `git status --porcelain -- 'governance/rules'` 圍籬（DEF-200-402 D3；刪除＝chaos_runner 寫髒 governance/rules 時零機械訊號）
E       assert -1 > 0
1 failed, 1 warning in 2.33s
```

**改回圍籬後**：單支 `1 passed`；整份靜態鎖檔 `102 passed, 18 warnings in 8.82s`，rc=0。

（本機 PG 在場，`pytest` 需帶 `--dist loadgroup` 滿足 X1 守門，否則 rc=4 拒跑，非測試本身失敗。）

## 五、AC1～AC7 量測結果

| AC | 判準 | 結果 |
|---|---|---|
| AC1（子行程沙盒 sha256 不變） | 見 §4 D2 綠案 | 通過（`2 passed`，複本 sha256 前後相同） |
| AC2（nightly stage 跑完 git 乾淨） | 圍籬本身即 AC2 的機械化；本輪未實跑整條 100 輪 nightly stage（分鐘級），改以 D2 沙盒＋D3 靜態鎖等效覆蓋 | 覆蓋但未端到端跑滿 100 輪 nightly stage（見〈六〉） |
| AC3（未來寫回者出現時 nightly 會出聲） | D3 靜態鎖 `test_sdd_chaos_latest_stage_fences_governance_rules_writeback` 紅綠自證 | 通過 |
| AC4（既有遙測語意測試零變動） | `test_rule_telemetry_requires_hook_r7.py`／`test_rule_fire_telemetry_wiring.py`／`test_rule_catch_telemetry_wiring.py`／`test_w20/37/38_catch_wiring.py`／`test_recovery_hint.py`／`test_chaos.py` | `121 passed in 30.50s`，rc=0 |
| AC5（SDD ci-gate 兩軌 rc=0） | `bash scripts/ci-gate.sh` | rc=0；逐軌計數：`AISDLC_SDD_v0.01:1478 AISDLC_SDD_v0.30:1960 scripts/tests:363`（`arch_fitness` 僅 advisory warn，未阻擋） |
| AC6（帳本／證據檔／crossref 鎖 rc=0） | `check_defect_log_crossref.py`／`test_archive_defect_log.py`／`test_doc_loc_baseline_freshness_r60.py` | 見 §7 |
| AC7（`test_run_local_nightly_static.py` 全套） | 見 §4 D3 | `102 passed`，rc=0 |

## 六、誠實劃界

- **雲端 `chaos-latest` job 未實跑驗**：D1 落地後理論上會自動繼承修復（同一份 LATEST 程式碼），
  但本輪未觸發一次雲端 nightly 或手動 dispatch 來端到端確認；風險判斷完全基於程式碼推理
  （見 §3 D5 理由），非實測。
- **`run_local_nightly.sh` 的 chaos stage parity 債（DEF-200-403）未修**：僅立帳，需 mac 真機
  現查後再評估是否搬遷整條 `sdd-fsm-chaos-latest` stage 到 `.sh`。
- **mac／Linux 側未觸及**：`fsm_runtime.py`／`chaos_runner.py` 為純 Python、平台無關，理論上
  無需要另外驗證；但本輪僅在 Windows 11 + win32 執行過，未在其他平台重跑 D2 測試或 D3 靜態鎖。
- **"466 = 100×4.66" 這個具體數字未被本 Developer 包重新從磁碟量測**：動工前 governance/rules
  已是乾淨狀態（`git status --porcelain` 空），本輪僅能覆核事故的**時間線**（nightly log 逐行核實）
  與**根因鏈**（程式碼閱讀），無法對「19 檔／466 fire_count」這個具體數字做獨立的磁碟層覆核，
  此為交辦資料中的既定描述，非本包實測。
- **完整 100 輪 nightly `sdd-fsm-chaos-latest` stage 未在本輪端到端重跑**（分鐘級成本）：AC1～AC3
  改以 D2 沙盒測試（2 輪，秒級）與 D3 靜態鎖覆蓋等效的因果鏈，未跑滿 100 輪的真實 nightly 呼叫
  形態一次驗收。
- **`AutoClaude/tests/tools/test_run_local_nightly_static.py` 之外的 nightly 相關套件（如
  `test_run_local_nightly.py` 的行為層測試，若存在）未逐一覆核**：本輪僅新增一支靜態鎖並跑
  該檔全套（102 passed），未擴大覆核到 nightly ps1 的其他行為測試面。

## 七、缺陷帳本

| ID | 狀態 | 摘要 |
|---|---|---|
| DEF-200-402 | fixed（2026-09-27） | chaos_runner 裸 CLI 未隔離規則遙測，19 支 tracked `governance/rules/R-9.*.yaml` 被寫髒；`telemetry_writeback_disabled()` + nightly ps1 圍籬修復 |
| DEF-200-403 | open（承接輪次：未指派，解鎖條件：mac 真機現查 `run_local_nightly.sh` 是否已補上 `sdd-fsm-chaos-latest` stage） | `run_local_nightly.sh` 從未有該 stage，parity 缺口先於本輪存在，本輪不修（範圍大於本輪圍籬） |

帳本淨額棘輪：本輪為發現輪（新增 1 筆 open＝DEF-200-403，結案 0 筆未結案列本輪未關閉其他項），
以 `AUTOSDD_NET_RATCHET_OFF=1` 逃生口通過（`check_defect_log_crossref.py` rc=0）。QA C11 釐清：該棘輪比的是
`git show HEAD:<帳本>` 對磁碟現況、只掛 pre-push 不掛 pre-commit ⇒ commit 之後 disk==HEAD、diff 為空，
不帶逃生口也結構上必 rc=0；commit 前看到的 rc=1 是即時警示、不是本輪 push 的真實阻斷點。

## 八、QA 獨立複審與主控收尾單人窗口（2026-09-27，Windows，Koala-MSI）

QA（Sonnet，兼反駁者甲／乙）零信任複審總判 **APPROVE-WITH-FIXES（僅 P3）**：A1 context manager 四情境（unset／
原值 "1"／巢狀／內部拋例外）自寫片段實測皆正確還原；A2 `chaos_runner.py` 全部 `FSMRuntime(`／`.transition(`
站點皆在 `_run_single_round` 內、只由 `run_chaos_rounds` 的 `with` 區塊呼叫，`--progress` 零額外入口；A3 catch 側
`SDD_ENABLE_RULE_CATCH_TELEMETRY` 同被強制 "0"；A4 沙盒解析鏈（`parents[3]`／`parents[2]`）親推＋親跑 `2 passed`，真實樹
前後乾淨；B6／B7 兩處突變自證由 QA 親做（拿掉 `with` ⇒ `2 failed`，真實樹仍乾淨；`= 1` 改 `= 0` ⇒ 靜態鎖 `1 failed`），
Edit 改回後 diff 與 Developer 原版逐字一致；B10 AC4 `121 passed in 30.89s` 與 Developer 逐位吻合；C12 五項具體宣稱
抽查四項 CONFIRMED、一項 REFUTED（§二根因鏈原寫 `fsm_runtime.py:347-352` 是 `transition()` 簽名處，實際呼叫在 386-391，
已訂正）；C13 新檔不加 `chaos` marker 是正確設計（輕量鎖留在 PR 快層）。

主控依 QA 收尾（皆已落地）：
- **P3-1**：§二行號 347-352 → 386-391。
- **P3-2**：D3 圍籬原本 `git status … 2>$null | Out-String` 在 git 自身失敗（非 git 目錄／PATH 無 git）時 stdout 必空、會被
  靜默讀成「乾淨」。改為 `$rulesDirtyLines = @(& git status --porcelain -- 'governance/rules' 2>$null)` 後獨立一句
  `$rulesGitRc = $LASTEXITCODE`，`$rulesGitRc -ne 0` ⇒ ERROR log＋`$global:LASTEXITCODE = 1`（圍籬無法判定也 fail-loud），
  再才是髒／淨兩分支。靜態鎖整檔 `102 passed, 18 warnings in 8.63s` rc=0（本機 PG 在場帶 `--dist loadgroup`）。

同輪一併收尾的 Windows 切換缺口與機械鎖重釘（主控親跑 `tools/run_root_unittests.py` 兩次；第一次在靜態標籤掃描階段
早退、一支測試都沒跑，第二次真跑 4662 支、7 紅，逐項處置如下）：

| 紅項 | 根因 | 處置 |
|---|---|---|
| `test_adr_xplat001_c1c2_lock` 護欄棘輪 ×3（107452→107474，+22） | Developer-A 修 `test_hook_carrier_symlink.py`（DEF-200-404）+22 行 | `--print-guard-lines` 重釘三次收斂：主列 R178 +22、本表自身漂移收斂列 +21（含 E501 折行、`_ROOT_TOOLS_OLD_SCALE_DEBT_DUE_ROUND` 到期具名展延 178→183 三行註解；第一次預估 17、實測 16，加展延後 21）、`_REGRESSION_LANE_LOG` 43 全額回歸鎖軌、凍結前綴 299→301（工具印的 302 是「再追加一列後」的值，測試 `test_the_frozen_prefix_covers_every_row_this_round` 指 301）、sha `8f0be6de014b`→`81d395774077`、兩站點 guard-total（R145 附記＋improving_112）。tools/tests E501 存量 6 不增（`ruff --isolated --select E501 --line-length 100` 現量，第一版超寬兩行已折行）。最終 `淨額 107495→107495 (+0)`、`逐檔漂移 0 支` |
| `test_subprocess_encoding_hygiene…test_repo_trees_have_no_unencoded_text_subprocess` | 新測試 `subprocess.run(text=True)` 無 `encoding`（QA B9 只認 open／read_text 鎖，漏了這道 subprocess 鎖） | 補 `encoding="utf-8", errors="replace"` |
| `test_check_defect_log_crossref…test_no_code_file_claims_a_round_beyond_the_ledger` | 五處程式碼／docstring 字面 `R178` > 帳本當前輪（`current_round()` 取「發現情境」欄最大 `R\d+`＝R100） | 改寫為 DEF 編號或「該輪」，不寫輪號字面 |
| `test_check_defect_log_crossref` net ratchet ×2 | commit 前 disk≠HEAD 的暫態（見上） | 先 commit 再跑全套核實 |
| skip 分群天花板 `tools/tests@win32`（`共 46 支：platform=42／env-disabled=4／欠債型 4`） | DEF-200-404 三支由 FAIL／ERROR 轉 `[ENV-DISABLED]` skip | `skip_group_policy.py` 兩張表 `env-disabled` 2→4 逐字照填（推算值本是 5，實測 4） |
| （第一跑早退）`_TREE_FILE_FLOORS` LATEST `fsm_runtime/tests` 下限 64 過期（實測 82，78%） | DEF-200-402 新增測試檔 | `skip_tag_policy.py` 重釘 65（工具逐字指示值） |

DEF-200-404（新立即結）：`tools/tests/test_hook_carrier_symlink.py` 三支在無 symlink 權限的 Windows 本機 2 FAIL＋1 ERROR
（`WinError 1314`；cdae902 自陳 Windows 未驗；雲端 windows runner 以管理員跑、有權限故綠）。Developer-A 診斷：
`TestEnsurePosixCreation` 兩支傳 `is_windows=False` 真的走 `link.symlink_to()`、`ensure()` 接住 OSError 回 False；
`TestEnsureFailLoud` 一支是 fixture 自己 `symlink_to` 佈置。修法沿用 SSOT `_platform_helpers.create_symlink_or_skip`（R81 包 F
先例 `test_dev_start.py:2244`）：前者類級 `setUp` 探一次權限、後者 fixture 改走探針；Windows 上 `Ran 6 tests OK (skipped=3)`，
ruff 過，POSIX 斷言零弱化。`run_root_unittests.py` 無 census-only 模式（`_KNOWN_ARGV = ()`），天花板值只能由全套實跑取得。

| 缺陷 | 狀態 | 一句話 |
|---|---|---|
| DEF-200-404 | fixed（2026-09-27） | symlink 測試在無權限 Windows 上假紅，改走 `create_symlink_or_skip` 探針 skip；`tools/tests@win32` 天花板依實跑 census 重釘 |

誠實劃界（本節）：雲端 `chaos-latest` job 與 mac 側皆未在本輪真機驗證；根層全套「commit 後乾淨 env」的第三跑與 push 後
雲端五支 run 結果寫在 commit 訊息與下一則回填，不在本節預寫。
