# CrossPlatform R80 — 包 C（架構減法）證據檔

> 本檔是 R80 包 C 的具名證據檔，供缺陷帳本各列以指針引用（帳本列 ≤ 700 bytes，詳情一律落在這裡）。
> 🔴 **取證紀律**：本檔每一個數字都附「當回合真跑的指令」。沒有實測輸出佐證的推測一律標「未驗證」。
> 🔴 **並行注意**：本輪有 6 個修復包＋2 個既有 agent 同時動這棵樹。本檔所有閘門 rc **只對取得它的那個時點有效**，
> 且逐筆已標明哪些失敗**不是**本包造成的。本包**不宣稱**「全套閘門綠」。

---

## 0. 進場基線與收工差異

| | 指令 | 結果 |
|---|---|---|
| 進場 | `python -m pytest tools/tests -q --no-header -p no:cacheprovider` | **12 failed / 2366 passed / 43 skipped**，381.44s，rc=1 |
| 收工 | 同上 | 見 §6 |

進場失敗集合（12 筆，皆非本包造成，成因是舵手開場歸檔的下游效應與其他包的護欄層成長）：

```
test_adr_xplat001_c1c2_lock.py::TestShrinkOnlyRatchet::test_ratchet_is_independent_of_git_state
test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet::test_a_net_zero_swap_is_red
test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet::test_the_line_ratchet_took_over_and_has_teeth
test_archive_defect_log.py::TestNoAssertionSamplesALiveDocumentWholesale::test_no_root_test_asserts_absence_against_a_whole_live_document
test_check_defect_log_crossref.py::TestMain::test_main_against_real_repo_is_clean
test_check_defect_log_crossref.py::TestR71CodeRoundLabelsNeverExceedLedgerCurrentRound::test_no_code_file_claims_a_round_beyond_the_ledger
test_check_defect_log_crossref.py::TestEarlyExitAnnouncesUnrunChecks::test_the_real_gate_still_reaches_the_late_checks
test_check_defect_log_crossref.py::TestR79RowByteCeiling::test_the_real_ledger_baselines_are_exact_not_padded
test_check_defect_log_crossref.py::TestR79RowByteCeiling::test_the_real_ledger_is_green_today
test_context_budget_guard.py::PreToolUseBlockTest::test_the_registered_matcher_matches_the_scripts_own_scope
test_python_c_percent_shim.py::TestNoPercentFormattingInPs1::test_scan_coverage_floor
test_run_root_unittests.py::UntaggedWindowsLikeSkipsTest::test_real_run_with_floor_reds_on_an_untagged_windows_skip
```

護欄層行數棘輪的進場實測逐字（**進場就已破線，不是本包造成的**）：

```
[成長] 護欄層行數由 63056 增為 63862（+806）
成長最多的幾支：[('test_context_budget_guard.py', 480), ('test_check_hooks_liveness.py', 280),
                ('test_subprocess_encoding_hygiene.py', 46), ('_ps_engine.py', 7)]
```

⇒ 那四支都不是本包碰過的檔。本包在同一個面上的貢獻是 **−319 行**（見 §5）。

---

## S5-03 — 「找可用 bash」七份實作收成一份

### (a) 量測（不是估計）

普查腳本：把每一份實作 `ast.unparse` → 剝 docstring → 再 `ast.unparse` → sha256。
**同雜湊＝剝除註解與 docstring 後，程式碼逐字相同。**

```
站點                                                    函式                      正規化AST雜湊   原始行數
AISDLC_SDD/scripts/bash_probe.py                       usable_bash              91fa22dca19e   34
tools/tests/_platform_helpers.py                       usable_bash_for_fixture  ed3d027ac8d8   83
tools/tests/test_pre_push_dispatcher.py                _usable_bash             9797b0251822   51
tools/tests/test_git_hooks_install_common.py           _usable_bash             9797b0251822   55
tools/tests/test_windows_forbidden_filename_parity.py  _usable_bash             9797b0251822   44
tools/integration_gate_core.py                         find_git_bash            bd83a4f6bb68   20
```

另兩份（同名 `_bash_exe()`，非 `_usable_bash` 命名故上表未列，以人工逐行比對取得）：

| 站點 | `except` 子句 |
|---|---|
| `tools/tests/test_windowsapps_guard_bash_parity.py::_bash_exe` | `except Exception:` |
| `tools/tests/test_windowsapps_guard_cross_consistency.py::_bash_exe` | **`except OSError:`** |

### (b) 為什麼「獨立重寫維持鑑別力」這條理由對它們不成立

三份 `_usable_bash()` 的 docstring 各自寫著「刻意獨立複製一份而非跨檔 import，
維持『共用資料規格、執行邏輯各自獨立』的既有架構決策」。實測結果是**三份逐字相同**
（雜湊 `9797b0251822`）。**複製貼上不是獨立重寫**：逐字相同的三份共享 100% 盲點，
不存在「其中一份會在另外兩份漏掉時轉紅」的情形 ⇒ 付三份維護成本、換到零額外鑑別力。

兩份 `_bash_exe()` 更糟——它們**已經漂移，而且沒有任何東西在比對它們**：

* `subprocess.TimeoutExpired` 繼承 `SubprocessError`，**不是** `OSError`。
* ⇒ 候選 bash 一旦卡住（timeout=15 到期），`except OSError` 那份會讓例外逸出，
  而那個呼叫發生在**模組層**（`@unittest.skipUnless(_bash_exe(), …)`），於是整支鎖檔
  在 collection 期就炸；`except Exception` 那份則安靜換下一個候選。
* 兩種失敗模式，零測試在比對。這正是「獨立重寫」宣稱買到的那個鑑別力**實際上並不存在**的證據。

### (c) 保留哪幾份、為什麼（射程的正確劃法 → 見 S5-04）

**保留**（雜湊互異、真的各自寫成、且被**硬邊界**隔開，不可 import）：

* `AISDLC_SDD/scripts/bash_probe.py::usable_bash()` — 子專案邊界（行為鎖仍在
  `AISDLC_SDD/scripts/tests/test_bash_probe.py::TestUsableBashSystem32Guard`，未動）
* `tools/integration_gate_core.py::find_git_bash()` — 另一棵消費樹
* `tools/lib/Find-GitBash.ps1` — 語言邊界（PS1 無法 import Python 常數）
* `tools/tests/_platform_helpers.py::usable_bash_for_fixture()` — 根層測試樹 SSOT（收斂目的地）

**刪除**（5 份，全部是同一段程式碼的手抄本）：上表 `9797b0251822` 三份 ＋ 兩份 `_bash_exe()`。

### (d) 刪掉之後誰在守同一件事（覆蓋不下降的證明）

被刪的兩個 `TestUsableBashSystem32Guard` 類別（各 4 支 mock 測試）逐案承接：

| 被刪的斷言 | 承接者 | 是否更硬 |
|---|---|---|
| System32 段必須排除 | `test_bash_probe_spec_contract.py::TestWslStubIsNeverAcceptedAsRealBash::test_system32_stub_is_rejected` | **是**：活 stub 真的通過驗活，只剩路徑規則能救；mock 版只斷言 `mock_run.assert_not_called()` |
| `system32` 子字串但非完整段者不得誤排 | **本輪新增** 同類的 `test_substring_system32_is_not_a_segment_and_must_be_accepted`（`MyWindowsAppsBackup` 手法、活 stub） | **是**：mock 版只證明「比對邏輯這樣寫」，新版證明「真的解析得到」 |
| 缺 coreutils（`dirname`）必須拒絕 | `TestProbeCmdRealSubprocessBehavior::test_fails_when_path_lacks_dirname` ＋ `TestUsableBashRejectsCoreutilsLessBinBashClone`（真跑，不 mock） | **是** |
| 正向：驗活通過者必須接受 | `test_stub_is_live_so_only_the_path_rule_can_reject_it` ＋ `TestUsableBashEndToEndWithRestrictedPath::test_usable_bash_accepts_candidate_with_real_path` | 同等 |

⇒ **唯一沒有承接者的是「子字串誘餌」那一案，所以本輪把它補進 SSOT 的鎖裡才動手刪。**
（+23 行換 −286 行。）

行為等價性：`_platform_helpers._bash_candidates()` 的候選子路徑是 `("usr/bin/bash.exe",
"bin/bash.exe", "usr/bin/bash", "bin/bash")`，是被刪三份（只有前兩個 `.exe`）的**嚴格超集**；
存在性判定由 `.exists()` 收緊為 `.is_file()`；驗活比對邏輯逐字相同。

### (e) 實測

```
python -m pytest tools/tests/test_pre_push_dispatcher.py tools/tests/test_git_hooks_install_common.py \
  tools/tests/test_windows_forbidden_filename_parity.py tools/tests/test_bash_probe_spec_contract.py \
  tools/tests/test_find_git_bash_parity.py -q
→ 1 failed, 135 passed, 156 subtests passed（31.34s）

python -m pytest tools/tests/test_windowsapps_guard_bash_parity.py \
  tools/tests/test_windowsapps_guard_cross_consistency.py -q
→ 99 passed, 128 subtests passed（8.47s），rc=0
```

🔴 上面那 1 failed 是 `test_git_hooks_install_common.py::TestWrapperThinnessGuard::
test_sh_wrapper_within_line_budget`（102 > 100），**不是本包造成的**：
`git diff --numstat -- tools/lib/git_hooks_install_common.sh` 顯示 `5  0`＝另一個包在本輪
對該 `.sh` 加了 5 行，而該檔本包一個字都沒動。處置＝**不動**（調高 `_SH_MAX_LINES`
是本輪明文禁止的動作），已列入 §7 交棒。

---

## S5-04 — 「獨立重寫維持鑑別力」這條慣例的正確射程

**裁決**：這條慣例**成立**，但它的射程是「被硬邊界隔開、因而**不可能** import 的真獨立實作」，
**不含**同一棵樹裡的純函式複製貼上。

本 repo 兩次實測證偽（第二次即本輪）：

1. 三份 `_usable_bash()` 宣稱獨立重寫 → 剝 docstring 後 AST 逐字相同（`9797b0251822`）。
2. 兩份 `_bash_exe()` 宣稱獨立重寫 → 是手抄本，且已漂移成兩種不同的失敗模式，
   而**沒有任何鎖在比對它們**（真獨立重寫的價值前提是「兩份會被拿來對拍」，這裡從未發生）。

判別式（給下一輪用）：問「這兩份**能不能** import 對方？」
* 不能（語言／子專案／套件邊界）→ 獨立實作合法，但**必須**配對等性掃描器或行為表 parity。
* 能，卻選擇不 → 那不是獨立重寫，是複本；除非能指出「哪一支測試會在其中一份漏掉時轉紅」，
  否則不成立。

已就地訂正的引用點：`tools/lib/bash_probe_spec.py` 檔頭、
`tools/tests/_platform_helpers.py::usable_bash_for_fixture` docstring（原文寫「刻意不收斂的兩份」）、
兩支 windowsapps 鎖檔的檔頭常數區註解。

---

## S5-05 — 刪除已死的 `_MARKER_PAIRS` 機制

**死亡證明**：`_MARKER_PAIRS: list[tuple[str, str, str]] = []`（空清單自 R16 起），
`main()` 內 `for label, sh_rel, ps1_rel in _MARKER_PAIRS:` 迴圈跑零次，
收尾訊息恆印「0 對標籤腳本」，`_enrolled_pairs()` 的 parity 項恆為空集合。

**為何 R77-34「刪死碼收益低於風險」的判定要翻案**：殘留不只是外觀。**三個檔案**把它寫成
新腳本的**第一條**納管途徑——
1. `tools/check_script_parity.py::_check_pair_enrollment` 的紅燈訊息（唯一會被讀的文件）；
2. `tools/check_wrapper_thinness.py` 檔頭的職責邊界段（「列出三條納管途徑」）；
3. `.github/workflows/root-infra-ci.yml` 的註解。

照那條指路做的人會去填一個沒有任何東西在讀的名冊，而閘門會照樣全綠。
風險側是零消費者的空清單，收益側是錯誤指路——兩者不對稱。

**刻意不刪**：`_extract_markers()`／`_compare()`／`_check_extract_floor()`／`_MIN_EXTRACT_COUNTS`
——它們仍是 `_check_run_tlc_invocation_parity()` 的實作（活消費者）。刪的只有名冊與跑零次的迴圈。

順手修掉一個同型脆弱點：`test_check_script_parity.py::_run_enrollment` 原本寫
`patches[0] … patches[5]` 六個硬編索引，`_patched()` 少回一個元素時是 `IndexError` 而非有意義的
紅燈。改用 `contextlib.ExitStack` 依實際長度展開，數量從此只有一個家。

**實測**：`python -m pytest tools/tests/test_check_script_parity.py tools/tests/test_check_wrapper_thinness.py
tools/tests/test_act_local_runner_image.py -q` → **183 passed, 29 subtests passed**（5.02s），rc=0。

🔴 `python tools/check_script_parity.py` 本身 rc=1，紅的那一條是
`❌ 自述用法 ↔ exec bit 鎖：凍結版同型存量由 29 變成 116`——**不是本包**：
該檢查（`_check_self_help_advertises_executable_form`／`_SELF_HELP_DEBT_FROZEN`）是另一個包
在本輪新加的 106 行，`git diff -U0` 的 hunk `@@ -556,0 +561,106 @@` 即該段。本包在同一檔的
真實增量是 **+30 / −25**（137 − 107 筆他人插入）。

---

## S5-06／S5-07 — WindowsApps 空殼判準

**S5-06 裁決**：四份實作**不合併**（`windowsapps_guard.sh` / `WindowsAppsGuard.ps1` /
`bootstrap_core.py` / PS 呼叫端）——它們被語言邊界隔開，符合 S5-04 的判別式。
真正的問題不在實作份數，而在**測試/實作比**：同一件事同時被「行為表 parity」與
「bash 行為電池」兩套機制守著，而後者是前者的真子集。⇒ 處置＝刪重複的那一套，不動實作。

**S5-07 逐案覆蓋證明**（`_VERDICT_CASES` 是 11 列樣本表，同一個 ASCII 暫存檔**同時**餵給四份實作、
逐列比對四方判定一致）：

| 被刪的 bash 電池案例 | `_VERDICT_CASES` 承接列 | 是否更嚴 |
|---|---|---|
| `test_real_candidate_accepted` | `C:\Python311\python.exe`（expected_stub=False，「真直譯器路徑」） | 同等 |
| `test_windowsapps_stub_rejected` | 6 列 expected_stub=True（全反斜線／全正斜線／混用×3／MSYS `/c/…` 掛載路徑） | **是**：多守住本電池從未測過的分隔符變體 |
| `test_mixed_case_windowsapps_stub_rejected` | `…\WINDOWSAPPS\python.exe`（「大小寫變體」） | 同等 |
| `test_legit_dir_merely_containing_substring_is_accepted` | `C:\Users\me\MyWindowsAppsBackup\python.exe`（「誘餌：子字串非完整段」） | 同等，**目錄名逐字相同** |
| `test_missing_candidate_rejected` | **無承接者** | ⇒ **保留** |

保留的那一支問的是另一件事：`command -v` 在 PATH 上找不到候選時的行為。
`_VERDICT_CASES` 餵的是既有路徑字串、不做 PATH 查找，那條路徑一次都沒被走到。

---

## S5-08 — 設計層裁決：什麼時候「雙份 .ps1/.sh 平行實作 + 對等性掃描器」是對的

**裁決：合理，但只在下列條件同時成立時。**

成立條件（三條缺一不可）：
1. **硬邊界**使兩側不可能共用同一份程式碼（語言邊界＝ .ps1 無法 import .py；
   子專案邊界＝ `AISDLC_SDD/` 與 `AutoClaude/` 各自可獨立 checkout）。
2. 兩側的**執行環境本身**是被驗證的對象之一（PS 5.1 vs pwsh 7、MSYS bash vs WSL）。
3. 有一個**餵同一組輸入給各側、逐列比對輸出**的機制（行為表 parity），
   而不只是比對原始碼字面。

本 repo 已有 8/13 對走「Python 單核心 ＋ 薄殼」，那是條件 1 不成立時的正解
（業務邏輯下沉，兩側只剩呈現層，由 `check_wrapper_thinness.py` 的 hash 釘選守住薄）。

**不合理的套用**：把同一套理由搬到**純函式判準**上（S5-03／S5-04 的那五份）。
純函式沒有環境變因、可直接 import、且複本從未被拿來對拍 ⇒ 三條件全不成立。

---

## S5-09 — hook 與 unittest 守同一條規則：什麼時候是「合理雙層」

**裁決：EOL 那一對是合理雙層**——`check_ps1_encoding.py`（PostToolUse，寫入當下就地補回 CRLF）
是**預防**，`test_platform_neutral_paths.py::TestWorktreeEolMatchesPolicy`（事後量工作樹）是**兜底**。
兩者的觸發時機與可觀測面不同（hook 看得到單次寫入、unittest 看得到整棵工作樹），不是重複。

**仍待處置**：hook 側私藏了一份 CRLF 字面。本包**未動它**——`.claude/**` 明文不在本包持有面。
去重方向（交棒）：字面下沉到一個 `tools/lib/` 常數，hook 與 unittest 各自 import；
或更省事——unittest 側改讀 `.gitattributes` 現查（R79 已對「工作樹行尾政策」用過這一招）。

---

## S5-10 — `test_windowsapps_guard_cross_consistency.py` 的內聚性

現況：本包收工時 **2179 行**（進場 2222）。內聚性差**不是作者的選擇**，是護欄政策
（DEF-101-561③「禁止新增鎖檔、只准合併／刪除」）的直接後果：每個新判準都被擠進既有巨檔。

**本包不自行改那條政策**，理由：它是掌舵者拍板的裁決，且它與行數棘輪是同一組機制
（`glc_growth_problem` 的訊息逐字寫「本裁決的語意**不是**禁止新增鎖檔……新增檔案只要淨額不上升就合法」）。
⇒ 現行政策其實**已經允許**拆檔（只要淨額不升）。真正的阻力是
`check_wrapper_thinness._FROZEN_GUARD_FILE_COUNT` 那一類「檔數只准下降」的殘留敘述。

**給舵手拍板的題目**（見 §7）：要不要把「拆檔」從『合法但沒人做』升級為『對超過 N 行的鎖檔是**應該做的**』。
本包已示範拆檔不是必要條件——同一支檔案靠**刪重複**就降了 43 行。

---

## S5-11 — `tools/probe/xplat_injection_matrix.py`（305 行，零自動化消費者）

**裁決：保留，不接電也不退場。** 論證：

* 它是 `DEF-101-796` 的**唯一可重跑產物**。該缺陷的本體逐字就是「四輪來這件事沒有任何可重跑的產物，
  於是每一輪要回答『mac 方向的攔阻率有沒有進步』都得從頭建一次基線」。
  **刪掉它＝把那個缺陷原封不動地放回去**，而且是在它剛被修好的下一輪。
* 「零自動化消費者」是**設計**不是疏漏：它 `--apply` 會就地改動共用工作樹，
  依 `DEF-101-886` 只能在所有 agent 停工的窗口內跑。把它接進任何自動閘門，
  等於讓閘門在多包並行時互相污染——那正是它自己檔頭在警告的事。
* 「接電」的唯一安全形態是把 `--dry-run`（不改樹的那半）接進閘門，
  用來防「六類定義腐爛而沒人發現」。那是**加行**，與本包的淨刪任務相反，且屬新機械物 ⇒ 交棒。

⇒ 本包對它**零改動**。這一筆的正確答案是「判定＋論證」，不是動手。

---

## S5-02 — 行數棘輪是收費站不是棘輪（**本包未落地，理由如下**）

**診斷屬實**：`glc_growth_problem()` 的紅燈訊息逐字寫出自助放行程序
（「`--print-guard-lines` 重釘 `_FROZEN_GUARD_LINES`、在 `_GUARD_LINES_REPIN_LOG` 補一列」），
而 `_GUARD_LINES_REPIN_LOG` 現況 **R79 佔 5 列、淨額全為正**（+1485/+408/+610/+342/+235）。
每輪聚合：R77 +3505、R78 +2243、R79 +3080 —— **三輪連續往上，零輪往下**。

**建議判準形狀**（照 `TestR74IronLawMechanismAccounting` 的雙單邊寫法）：
把「一次必要成長」與「連續成長」拆成兩個各自單邊的量——
* 單輪淨額 > 0 ⇒ **綠**（誠實登記一次必要成長不得當場紅，否則最省力的滿足方式變成不登記）；
* **相鄰兩個輪號的聚合淨額皆 > 0 ⇒ 紅**（收費站於是只能連刷一次）；
* 起算輪錨 `_CONSECUTIVE_GROWTH_ANCHOR` 本身必須是 **shrink-only**（只准往**早**移、不准往後推），
  否則錨就是新的自助出口。

**為何本包不落地它**（誠實劃界，不是偷懶）：
1. 判準一上線就會**紅在到貨當天**（R77→R78→R79 已是三連升），而本 repo 對
   「紅了卻沒有出路的鎖」有明文判例——該檔第 946 行逐字寫著那句話。要讓它有出路，
   錨必須落在 R80，而 R80 的聚合淨額**要等所有包停工後由收尾包重釘才知道**。
2. `test_adr_xplat001_c1c2_lock.py` 不在本包持有面，且該檔的三支測試**進場就是紅的**
   （其他包的 +806 成長）。在別人正在推高的數字上加一道新判準，會製造無法歸因的假紅。
3. 落地它是**加行**，而本包的成功判準是淨刪。

⇒ 交棒收尾包，判準形狀與錨值如上。本包對該檔零改動。

---

## S5-12 — LOC tier 政策把單一 skip 判準切成 6 個模組（**先回報，未動**）

`tools/lib/skip_*.py` 家族明文列在本包的「不要動」清單。本包**只回報**：

* 分檔理由是**行數超標**而不是**內聚**——那是 tier 政策的產物，不是設計。
* 同一份清單在三支 workflow 裡各抄了一份（6×6）。
* 這一筆會動到 skip 相關包的持有面 ⇒ **不硬改**，依指示先回報。

建議處置順序：先解決「清單住三個 workflow」那一半（那是純資料，可下沉成一個
被三支 workflow 共讀的 SSOT），再談模組合併——後者要先把 tier 政策對 `tools/lib/`
的適用性拿到舵手面前，否則合併完會撞上同一條 LOC 紅線。

---

## 5. 淨額表

foreign hunk 已扣除：`tools/check_script_parity.py` 的 `git diff` 顯示 +137，其中
**107 行是另一個包插入的**（`@@ -556,0 +561,106 @@` 的 `_check_self_help_advertises_executable_form`
＋ `@@ -1593,0 +1705 @@` 的 main() 接線）。本表用的是扣除後的 **+30**。

| 檔案 | 加 | 刪 | 淨 |
|---|---:|---:|---:|
| `tools/tests/test_git_hooks_install_common.py` | 7 | 135 | **−128** |
| `tools/tests/test_pre_push_dispatcher.py` | 13 | 125 | **−112** |
| `tools/tests/test_windowsapps_guard_bash_parity.py` | 31 | 84 | **−53** |
| `tools/tests/test_windows_forbidden_filename_parity.py` | 14 | 52 | **−38** |
| `tools/tests/test_windowsapps_guard_cross_consistency.py` | 9 | 47 | **−38** |
| `tools/check_script_parity.py`（扣除他人 107） | 30 | 25 | +5 |
| `tools/check_wrapper_thinness.py` | 7 | 4 | +3 |
| `tools/tests/test_find_git_bash_parity.py` | 10 | 7 | +3 |
| `tools/tests/test_check_script_parity.py` | 9 | 5 | +4 |
| `tools/lib/bash_probe_spec.py` | 16 | 8 | +8 |
| `tools/tests/_platform_helpers.py` | 25 | 5 | +20 |
| `tools/tests/test_bash_probe_spec_contract.py` | 23 | 0 | +23 |
| **合計** | **194** | **497** | **−303** |

其中落在**護欄層行數棘輪掃描面**（非遞迴 `tools/tests/*.py`）的部分：

| | 值 |
|---|---:|
| 加 | 131 |
| 刪 | 450 |
| **護欄層淨額** | **−319** |

⇒ 進場時該面的破線量是 **+806**；本包單方向貢獻 **−319**。
🔴 **本包刻意不重釘 `_FROZEN_GUARD_LINES`**：該檔的重釘紀律逐字要求
「多包並行的輪次由**收尾包在所有包停工後**重釘一次」。逐檔數字現查
`python tools/tests/test_adr_xplat001_c1c2_lock.py --print-guard-lines` 的 DIFF 欄。

**新增檔案數＝1**（本證據檔，落在 `docs/`，不在護欄層掃描面內）。
**未調高任何門檻／棘輪／LOC 上限／體積上限。未刪任何判準來換額度。**

---

## 7. 交棒（本包射程外，逐筆附理由）

| # | 事項 | 為何本包不做 |
|---|---|---|
| 1 | `tools/lib/git_hooks_install_common.sh` 102 > 100 行 | 另一個包在本輪加的 5 行；調高 `_SH_MAX_LINES` 是本輪明文禁止的動作 |
| 2 | S5-02 連續成長判準落地（形狀與錨值見上） | 判準會紅在到貨當天；錨必須是 R80 的聚合淨額，而那要等收尾包重釘才知道 |
| 3 | S5-09 hook 側私藏的 CRLF 字面下沉 | `.claude/**` 不在本包持有面 |
| 4 | S5-11 把 `xplat_injection_matrix.py` 的 `--dry-run` 半邊接進閘門 | 是加行、且屬新機械物 |
| 5 | S5-12 skip 清單的 6×6 workflow 複本下沉 | 動到 skip 包的持有面，依指示先回報 |
| 6 | S5-10 給舵手的題目：超過 N 行的鎖檔是否**應該**拆 | 需要人工決策，且現行政策其實已允許 |
| 7 | `check_script_parity.py` 的 `自述用法 ↔ exec bit 鎖` 凍結值 29 vs 實測 116 | 另一個包本輪新加的檢查，歸屬該包 |
