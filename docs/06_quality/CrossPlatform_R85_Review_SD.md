# CrossPlatform R85 — SD（System Designer）獨立複審

**角色**：判準品質守門人。本檔只回答一件事——**本輪新增／改動的判準裡，哪些是裝飾品**。
**平台**：macOS（Darwin 25.5.0）。涉及 Windows 的結論一律標「靜態推論、未真機驗證」。
**紀律**：不採信任何自陳；每筆 finding 附可重跑指令＋真實輸出。讀 rc 一律不接管線。
**唯讀**：本輪未改任何 tracked 檔、未執行任何 git 寫入。所有注入均在**記憶體內**（monkeypatch 類別屬性）
或**合成字串**上進行，未觸碰工作樹（工作樹是收尾窗口正在收的東西）。

---

## 0. 全樹實況（先立基準，避免把「沒看到 FAIL」讀成通過）

```bash
cd tools/tests && ../../.venv/bin/python -m unittest discover -p 'test_*.py'
```
```
Ran 3284 tests in 411.268s
FAILED (failures=23, skipped=44)
```

⇒ **收集數 3284**、**當下 23 紅**。這兩個數字同時證偽兩件本輪宣稱（見 B-1、M-1）。
`tools/run_root_unittests.py` 會在靜態標籤掃描階段短路，故上面刻意走裸 `unittest discover`。

🔴 **兩次全樹跑的紅數不一致，照實記**：第二次同指令跑（只 grep `^FAIL:`）只抓到 **17** 個相異名字，
且 `TestGuardLayerRatchet` 那 6 筆中有 4 筆**未重現**（`test_editing_an_existing_row_in_place_is_red`／
`test_the_docs_cite_the_live_guard_total`／`test_the_extended_doc_surface_covers_the_handoff_without_false_reds`／
`test_the_repin_log_accounts_for_the_frozen_table`）⇒ 這一族有**順序／狀態相依**（本 repo 已登記過
DEF-101-499 的非決定性翻紅）。**但 B-1 的那一支在兩次跑中皆紅**，它不是非決定性的：
```
FAIL: test_the_real_repin_log_stays_inside_the_cost_envelope     ← 兩次都在
FAIL: test_appending_one_row_keeps_the_history_digest_stable     ← 兩次都在
```
第二次跑捕到的 17 個相異名字（去除上兩支後，其餘 15 支集中在
`test_check_defect_log_crossref`／`test_governance_docs` 一族與 `test_subprocess_encoding_hygiene`）：
```
test_a_legal_first_word_can_no_longer_land_in_the_vague_soft_exit      test_main_returns_1_when_row_arity_mismatched
test_an_unregistered_sibling_is_caught_and_named                      test_main_returns_1_when_status_first_word_illegal
test_broken_archive_rows_do_not_red_the_main_ledger_gate              test_main_warns_but_passes_when_archive_approaches_limit
test_e501_debt_only_shrinks                                           test_main_warns_but_passes_when_ledger_approaches_rotation_limit
test_every_sibling_on_disk_is_registered                              test_the_real_gate_still_reaches_the_late_checks
test_main_against_real_repo_is_clean                                  test_the_three_named_docs_are_exactly_what_the_glob_finds
test_main_returns_0_when_consistent                                   test_the_volume_check_no_longer_masks_the_later_checks
test_without_the_new_lock_the_soft_exit_reappears_and_counts_are_separated
```

---

## BLOCKING

### B-1（P2）`test_the_real_repin_log_stays_inside_the_cost_envelope` 當下就是紅的，而它紅的方式是「把本輪的結果寫死進鎖」

**持有面**：`tools/tests/test_adr_xplat001_c1c2_lock.py`（單一檔，收尾窗口可處置）

P2 把該測試原本的斷言 `all(delta > 0 …)` 翻成 `any(delta <= 0 …)`，理由逐字寫「R85 起這句話為假（**該輪是第一次淨減法輪**）」。

```bash
cd tools/tests && ../../.venv/bin/python -c "
import sys; sys.path.insert(0,'.'); import test_adr_xplat001_c1c2_lock as A
print(A.repin_round_nets(A._GUARD_LINES_REPIN_LOG))"
```
```
[(77, 3505), (78, 2243), (79, 3120), (80, 2334), (81, 3033), (82, 5400), (83, 5260), (84, 3755), (85, 468)]
```

**R85 的逐輪淨額是 +468，是正的。** 該前提在寫下它的當回合即為假。實跑：

```bash
cd tools/tests && ../../.venv/bin/python -m unittest test_adr_xplat001_c1c2_lock.TestGuardLayerRatchet
```
```
FAIL: test_appending_one_row_keeps_the_history_digest_stable
FAIL: test_editing_an_existing_row_in_place_is_red
FAIL: test_the_docs_cite_the_live_guard_total
FAIL: test_the_extended_doc_surface_covers_the_handoff_without_false_reds
FAIL: test_the_real_repin_log_stays_inside_the_cost_envelope
FAIL: test_the_repin_log_accounts_for_the_frozen_table
Ran 37 tests … FAILED (failures=6)
AssertionError: False is not true : 整段稽核痕跡至今**一列都沒有下降過**（實得逐輪淨額 […, (85, 468)]）
```

**為什麼是 blocking 而不是「收尾重釘就好」**：其餘 5 紅是凍結表／指紋／文件總量的例行漂移，
收尾窗口補一列重釘即可歸零；**但這一條不行**——補一列重釘只會讓 R85 的淨額從 +468 變得更大
（表尾對帳缺口目前是 `83306 → 83319`，即再 +13）。要讓它變綠，本輪必須**真的**在護欄層做到
淨額 ≤ 0，否則唯一出路就是把剛寫上去的斷言再改回去（＝本 repo 判過的 ARCH-02「沒有出路的鎖會被關掉」）。

**同一支 docstring 自相矛盾**（`:3220-3226` vs `:3233-3237`）：上半段仍寫「真表**每一列都在上升**（立案量測：R77→R83 +24,895／零列下降）」，
下半段的斷言卻要求至少有一列下降。同一份知識住兩個家、兩種內容。

**修法草案**（擇一，皆為單檔）：
① 若本輪真要當淨減法輪 → 在護欄層做出 ≤0 的淨額後再收輪；
② 若做不到 → 把斷言改成**不預判本輪結果**的形態，例如「一旦出現過非正淨額，就不得再回到全正」
（`if any(d <= 0 for …): assert …` 的守衛式寫法），並同步改掉上半段那句已過期的立案量測。
無論擇哪一條，`_GUARD_TOTAL_TRIPLE_RE` 收 `-`／`−` 那個修正本身是對的、應保留（見裁決表）。

---

### B-2（P6）新判準的立案數字是假的（實測 302/301，宣稱 199/198），且落地後**活分母＝1**

**持有面**：`AISDLC_SDD/scripts/agent_template_lint.py` ＋ `AISDLC_SDD/scripts/tests/test_agent_template_lint.py`（兩檔，同一持有面）

宣稱（兩處逐字複本）：
```bash
grep -n "199\|198" AISDLC_SDD/scripts/agent_template_lint.py AISDLC_SDD/scripts/tests/test_agent_template_lint.py
```
```
agent_template_lint.py:24:   而 `dependencies` 實際有五個桶。另四桶當回合實測共 **199 條**，其中 **198 條**是裸檔名、
tests/test_agent_template_lint.py:156:# **一個**桶，而 `dependencies` 有五個桶。另四桶當回合實測共 199 條、其中 198 條在版本樹內
tests/test_agent_template_lint.py:158:# 以下 case 鎖死的是「分母不得再被桶名窄化」：任一 case 退化，198 條幽靈依賴的假綠即復活。
```

用該 lint **自己的掃描面**（`agent/core/*.yaml` + `agent/specialized/*.yaml`，實查 `agent_template_lint.py:99-100`）獨立複算：

```bash
.venv/bin/python - <<'PY'   # 逐檔 yaml.safe_load，四桶計數；HEAD 版走 git show
… （腳本見本節下方「可重跑指令」）
PY
```
```
HEAD: files=28 per-bucket={'data': 79, 'tasks': 97, 'checklists': 75, 'tools': 51} total=302 with-ext=302
WT  : files=28 per-bucket={'data': 1,  'tasks': 0,  'checklists': 0, 'tools': 0}  total=1   with-ext=1
```

三項認定：
1. **立案數字錯**：302／301，不是 199／198。去重亦非 199。錯數字已被複製到兩支檔，且其中一份逐字宣稱「198 條幽靈依賴的假綠即復活」——那句話今天不可能被任何人驗證為真。
2. **活分母＝1**：本輪的修法是把 301 條幽靈依賴**刪掉**（原文搬進註解），只留 1 條真引用。新判準因此上線當下守的是一個近乎空集合；`tools` 桶更是 **0**。「1 桶擴到 4 桶」在覆蓋率上讀起來像保護力增加，實際的可違反面是 1。
3. **逃生門被釘成契約**：`if not _TMPL_EXT.search(norm): continue`（`\.(md|ya?ml|json)$`）⇒ 把幽靈依賴寫成無副檔名（`tasks:` 桶本來就常這樣寫）即結構上不進分母，而 `test_dep_bucket_non_file_entry_is_not_a_false_red` 把這個行為釘成契約。

**可重跑指令**（本節數字的唯一取數方式）：
```bash
.venv/bin/python - <<'PY'
import glob, re, yaml, subprocess
B=("data","tasks","checklists","tools"); EXT=re.compile(r'\.(md|ya?ml|json)$')
files=sorted(glob.glob('AISDLC_SDD/AISDLC_SDD_v0.30/agent/core/*.yaml')+
             glob.glob('AISDLC_SDD/AISDLC_SDD_v0.30/agent/specialized/*.yaml'))
for tag in ("HEAD","WT"):
    tot={b:0 for b in B}; n=0
    for f in files:
        txt=(subprocess.run(["git","show",f"HEAD:{f}"],capture_output=True,text=True).stdout
             if tag=="HEAD" else open(f,encoding='utf-8').read())
        deps=(yaml.safe_load(txt) or {}).get("dependencies") or {}
        if isinstance(deps,dict):
            for b in B:
                for d in (deps.get(b) or []):
                    if isinstance(d,str): tot[b]+=1; n+=1
    print(tag, tot, "total=",n)
PY
```

**修法草案**：① 把兩處 199/198 改成現查得到的 302/301（或改成「一律現查」＋附上上面那支腳本，體例同本 repo 對 reset 分佈／misstep 分群的處置）；② 在 docstring 誠實揭露「擴面後活分母＝1、`tools` 桶＝0，本判準是純寫入面」（同 `_FOREIGN_EXE_ARGV_DEBT` 那一格的體例）；③ `_TMPL_EXT` 逃生門若要保留，至少對 `tasks` 桶另立「裸名必須能在 treepool 內以 basename 解析」的判準，否則該桶恆綠。

---

### B-3（P12）授權邊界的「唯一的家」比它取代的第二份實作**弱**，且弱在鐵律二明訂的呼叫形態上

**持有面**：`tools/lib/unattended_authz.py`（判準）＋ `.claude/hooks/lint_powershell_command.py`（PS 側消費端）

P12 宣稱「判準與訊息一律住 `tools/lib/unattended_authz.py`，兩支 hook 都向這裡取用」。同輪 P7/P12 在
`AutoClaude/autoclaude/execution/evaluator.py` 落地了**第二份刻意的實作**（`.importlinter` 第 9 條所致）。
把兩份餵同一組輸入：

```bash
cd AutoClaude && AUTOSDD_UNATTENDED=1 ../.venv/bin/python -c "
from autoclaude.execution.evaluator import unattended_refusal as U
import sys; sys.path.insert(0,'../tools/lib'); from unattended_authz import authz_hits as A
for c in [r'& \"C:\Program Files\Git\bin\git.exe\" push', r\"& 'C:\Program Files\Git\bin\git.exe' commit -m x\",
          'sudo git push','VAR=1 git commit','git push']:
    print(('HIT ' if U(c) else 'MISS'), ('HIT ' if A(c) else 'MISS'), repr(c))"
```
```
evaluator=HIT   authz_SSOT=MISS   '& "C:\\Program Files\\Git\\bin\\git.exe" push'
evaluator=HIT   authz_SSOT=MISS   "& 'C:\\Program Files\\Git\\bin\\git.exe' commit -m x"
evaluator=HIT   authz_SSOT=MISS   'sudo git push'
evaluator=HIT   authz_SSOT=MISS   'VAR=1 git commit'
evaluator=HIT   authz_SSOT=HIT    'git push'
```

`evaluator.py` 的 `_UNATTENDED_WRITE` 明文收了 `\"[^\"\n]*[\\/]`／`'[^'\n]*[\\/]` 的引號路徑前綴與
`[A-Za-z_]\w*=\S*|env|sudo|nohup|command` 前綴；被宣告為「唯一的家」的 `unattended_authz.py` 兩者皆無。

**mac 側今天沒事，Windows 側有事**（後者為靜態推論，未真機驗證）：

```bash
# Bash 側（block_destructive_git 有真解析器 git_invocations，會補上前綴類）
printf '{"hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{"command":"sudo git push"}}' \
  | AUTOSDD_UNATTENDED=1 .venv/bin/python .claude/hooks/block_destructive_git.py >/dev/null 2>&1; echo rc=$?
rc=2      # 擋下
# 但引號絕對路徑那一種，兩個工具名都擋不下：
… tool=Bash quoted-abs-path rc=1
… tool=PowerShell quoted-abs-path rc=1     # rc≠2 ⇒ 未阻斷
```
PowerShell 側走的是 `lint_powershell_command.unattended_hits()`＝**沒有解析器的正則路徑**，且它先做
`mask_regions(..., keep_expandable=False)`：
```bash
.venv/bin/python -c "…; print(repr(m.mask_regions(r\"& 'C:\Program Files\Git\bin\git.exe' push\", keep_expandable=False)))"
'&                                    push'
```
引號區整段被遮蔽 ⇒ `git` 這個 token 根本不存在於判準看得到的字串裡。而
**根 CLAUDE.md 鐵律二明文要求「一律絕對路徑」**，Windows 上 Git 的預設安裝路徑就帶空白、必須加引號
⇒ **這是該平台上最可能被寫出來的形態，恰好是判準看不見的那一種**。

**另有一筆假紅**（同一支正則，PS 側）：
```
FALSE+ 'git config push.default simple'      # authz_hits 命中
ok     'git log --grep=push'
```
`(?![\w-])` 允許 `push` 後接 `.`，於是 `push.default` 被讀成子指令 `push`。

**修法草案**：把 `evaluator.py::_UNATTENDED_WRITE` 已驗證的兩段前綴（引號路徑 ＋ 賦值/sudo/env/nohup/command）
併回 `tools/lib/unattended_authz.py` 的 `GIT_WRITE_RE`／`GH_WRITE_RE`，並把 `(?![\w-])` 改成 `(?![\w.-])`
（與同檔 `git(?:\.exe)?(?![\w.-])` 一致）。兩份實作**不必**合併（架構契約禁止），但 SSOT 不得是弱的那一份。

---

### B-4（P7）可攜性要求只加在 `condition_evaluator`；同樣進 `shell=True` 的 `new_step_evaluator_command` 兩處未加，而鎖用「關鍵字出現」量它

**持有面**：`AutoClaude/autoclaude/decision/prompt_builder.py` ＋ `AutoClaude/tests/execution/test_shell_portability_contract_r85.py`

本輪 `prompt_builder.py` 的 diff 只有一行（`condition_evaluator` 的佔位字串加上可攜性指示）。
但同一段 schema 內另有兩個 LLM 產生的 shell 欄位：
```bash
sed -n '40,90p' AutoClaude/autoclaude/decision/prompt_builder.py
    "new_step_evaluator_command": "<驗證注入步驟成功的 shell 指令，例如 pytest tests/test_foo.py>",   # INJECT_AFTER
    "new_step_evaluator_command": "<驗證前置步驟成功的 shell 指令，例如 pip show fastapi>",           # INJECT_BEFORE
```
它們的執行鏈實查：
```bash
grep -rn "new_step_evaluator_command" AutoClaude/autoclaude/ | grep -v pyc
autoclaude/execution/mutation_applier/_simple_mutations.py:79:  mutation.new_step_evaluator_command or _default_fallback_evaluator_command()
autoclaude/execution/mutation_applier/_complex_mutations.py:50: 同上
autoclaude/core/services/mutation/_helpers.py:14:               evaluator_command=m.new_step_evaluator_command,
```
⇒ 它變成注入步驟的 `evaluator_command`，最終走 `evaluator.py:166` 的 `shell=True`。
**與 `condition_evaluator` 完全同一個危害面，且同樣「唯一產生者是 LLM」。**

而 P7 的鎖是：
```python
def test_the_mutation_schema_demands_portable_commands(self):
    assert "condition_evaluator" in _MUTATION_SCHEMA_SECTION
    assert "可攜" in _MUTATION_SCHEMA_SECTION
    assert "cmd.exe" in _MUTATION_SCHEMA_SECTION
```
**三條都是「整段 schema 內某個字串出現過」**——一個欄位加了可攜性指示，整段就算過。
欄位級的缺口對它結構上不可見。實查：
```bash
grep -c "new_step_evaluator_command" AutoClaude/tests/execution/test_shell_portability_contract_r85.py
0
```
該欄位名在整份 P7 鎖裡**一次都沒出現**。

**修法草案**：① 在 `_MUTATION_SCHEMA_SECTION` 的兩處 `new_step_evaluator_command` 佔位字串補上同一段可攜性指示；
② 把鎖改成**逐欄位**：列出「這段 schema 內所有會被送進 `shell=True` 的欄位名」（可由 `models/step_mutation.py`
的註解或一份具名 tuple 現查），對每一個斷言其佔位字串內含可攜性指示 —— 新增第三個 shell 欄位時當場紅。

---

## MAJOR

### M-1（P2）`MIN_TESTS` 3279 → 3268 是**無必要的放寬**；最終樹實測 3284

```bash
cd tools/tests && ../../.venv/bin/python -c "
import unittest; print(unittest.defaultTestLoader.discover('.', pattern='test_*.py').countTestCases())"
3284
```
- 舊下限 **3279** < 現值 **3284** ⇒ 舊下限在最終樹上**不會紅**，下修在結果上不是必要的。
- 下修後「靜默蒸發仍全綠」的窗口由 **0 支** 擴到 **16 支**。
- 兩層保鮮期都不會出聲：3284/3268 = 1.005，遠低於 `RATCHET_WARN_RATIO=1.10` 與 `RATCHET_STALE_RATIO=1.25`。
- 常數註解逐字寫「值取本 runner 當回合印出的計數 3268，零加減推算」——該值在 P2 交件那一刻可能為真，
  但其後其他包淨增測試（`test_block_destructive_git_r83.py` +5／`test_doc_loc_baseline…` +5／
  `test_platform_neutral_paths.py` +6／`test_adr_xplat…` +1）⇒ **今天它 stale 16**。

**修法草案**：收尾窗口以最終樹重釘為 **3284**（方向回到「往上＝收緊」），並在註解中把「本次為放寬」那段
改寫成史料。並表本身不必回退（見裁決表）。

### M-2（P2）併表後 3 族只有 1 族有樣本數鎖；`countTestCases()` 對「刪注入樣本」結構上失明

記憶體內注入（未動磁碟）：
```bash
cd tools/tests && ../../.venv/bin/python - <<'PY'
import sys, unittest; sys.path.insert(0,'.')
import test_dev_start as t
cls=[c for c in vars(t).values() if isinstance(c,type) and issubclass(c,unittest.TestCase)
     and '_FALSE_NEGATIVE_CASES' in c.__dict__][0]
cls._FALSE_NEGATIVE_CASES = cls._FALSE_NEGATIVE_CASES[:1]   # 3 → 1
cls._FALSE_POSITIVE_CASES = cls._FALSE_POSITIVE_CASES[:1]   # 2 → 1
r=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite([
    cls('test_r23_false_negative_variants_are_still_detected'),
    cls('test_r25_end_suffixed_words_do_not_false_trigger')]))
print('wasSuccessful=', r.wasSuccessful())
PY
```
```
test_r23_false_negative_variants_are_still_detected … ok
test_r25_end_suffixed_words_do_not_false_trigger    … ok
OK
wasSuccessful= True
```
砍掉 3 個注入樣本，**兩支測試全綠**，而且 `countTestCases()` 前後不變（subTest 不計入）
⇒ `MIN_TESTS` 這道下限對這種縮水結構上看不到。對照組（族① 有鎖）：
```bash
… cls._FORBIDDEN_CASES = cls._FORBIDDEN_CASES[:9]; run
AssertionError: 9 != 10 : 注入樣本數變了——本族是史料回歸鎖，樣本只准增不准減
```
```bash
grep -rn "_FALSE_NEGATIVE_CASES\|_FALSE_POSITIVE_CASES\|_FORBIDDEN_CASES" tools/ | grep -v pyc
tools/tests/test_check_wrapper_thinness.py:161:  len(self._FORBIDDEN_CASES), 10,      ← 唯一的計數鎖
tools/tests/test_dev_start.py:3187/3205/3219/3231                                  ← 無任何計數鎖
```
**修法草案**：在 `test_dev_start.py` 兩支併表測試各補一行 `assertEqual(len(...), 3)` / `== 2`，
訊息沿用族① 的措辭（「本族是史料回歸鎖，樣本只准增不准減」）。單檔、三行。

### M-3（P12）exe-argv 的 transitive 可達性有**跨模組假綠**，且 WHY 未劃這條界

`guard_scope_transitive()` 只在**本檔內**找呼叫端。合成注入六格（`scan_foreign_exe_argv` 直餵字串）：
```
RED    1 one-of-two-callsites-unguarded
RED    2 zero in-file callsites
GREEN  3 all callsites guarded
RED    4 depth-4 chain
GREEN  5 CROSS-MODULE: 唯一的 in-file 呼叫端有守衛，但函式是 public、可被別的模組 unguarded 呼叫
RED    6 method-name collision rescue attempt
```
格 5 是真的假綠：只要在**本檔內**留一個被守住的呼叫端，該函式即使是 public、被別的模組
unguarded 呼叫，判準照樣通過。而 `sites` 為空才回紅的設計，正好對「只有一個 in-file 呼叫端」失效。

今天全庫 24 筆 exe-argv 使用點中，靠 transitive 過關的有 3 筆：
```
AutoClaude/autoclaude/utils/notifier.py:143  osascript        （private `_try_osascript`，單一呼叫端，合法）
AutoClaude/tests/tools/test_run_local_nightly_static.py:2245  powershell.exe
tools/check_scheduled_task_drift.py:146      powershell.exe   ← 其鏈上有 public `export_task_xml`／`query_task_info`
```
`check_scheduled_task_drift` 的 public 包裝已實際被別的模組取用（`tools/tests/test_install_windows_nightly.py:1236`
直接呼叫 `self.mod.export_task_xml(...)`）。今天不是缺陷（測試沒真的跑到 powershell 分支），
但這條路上**沒有任何東西會在下一個人加第三個呼叫端時轉紅**——與該判準自己在治的 `dev_start.py:1051` 逐字同型。

`_EXE_ARGV_TRANSITIVE_DEPTH` 上方那段 WHY 寫得很完整，但**沒有一句提到跨模組**。
**修法草案**：① 在 WHY 補一節〈誠實劃界〉，明說「跨模組呼叫端不在射程內」；
② 判準收窄成「只有**私有**函式（`_` 開頭）才准走 transitive」——public 函式一律要求站點級守衛或行尾豁免。
今天實測命中的 3 筆裡有 2 筆會因此需要處置，可用行尾 `# xplat-ok:` 附呼叫端契約。

### M-4（P7）母體宣稱「9 支 playbook／19 值」雙向失準，且蒐集器有兩個靜默丟值的形態

`_real_evaluator_commands()` 的蒐集面是 `AutoClaude/**/*.y*ml` 的**行導向 regex**。
- **多算**：`AutoClaude/scripts/bridge_e2e/strutils_prd_plan.yaml` 經 `Playbook.model_validate` 判定 **INVALID**
  （頂層鍵 `project_id/name/description/goal_tasks`，屬 `models/three_tier_schema.py::Project`）。它貢獻 5 值。
  真正的 playbook 只有 **8 支**貢獻 14 值。
- **少算**：以 `Playbook.model_validate` 對全庫 YAML 實測，合法 playbook 共 **20 支**（另 5 支嵌套在 sd07 fixture）。
  docstring 把「碰巧含 `evaluator_command:` 行的檔案數」寫成「playbook 母體」，於是
  「這一格會隨新 playbook 自動長大」對**檔案數**不成立（只對值成立）。
- **靜默丟值形態一**：`if val and not val.startswith(("|", ">", "{", "[", "#"))` ⇒ 有人把 evaluator_command
  改成 YAML block scalar（`evaluator_command: |`）該值**完全消失於母體**，且 `>= 15` 那道自證閘今天餘裕充足、
  不會出聲。
- **靜默丟值形態二**：`.strip("\"'")` 讓 19 值中 **2 值失真**（`09_conditional.yaml`／`10_full_e2e_dry_run.yaml`
  的 `python -c "print('…')"` 被咬掉尾引號）——與 docstring 自陳「這才是 `Evaluator.run` 的真實輸入面」不符。
- **AutoClaude/ 外的鍵位命中實測為 0**，故 glob root 釘在 `AutoClaude/` 今天無實害；但
  `AISDLC_SDD/<LATEST>/agent/specialized/sdd-prd-to-playbook-zh.yaml` 是**產生 playbook 的模板**、內含
  evaluator 白名單自律條款（`pytest`／`python`／`python3`／`autoclaude-artifact-check`）。
  那份白名單與 P7 的可攜性詞彙表是兩個家、彼此無機械綁定。

**修法草案**：① docstring 改寫成「N 個 `evaluator_command` 值，來自 M 支 YAML（其中一支是三層 PRD 計畫）」，
不要把值數當檔數；② 蒐集器改用 `yaml.safe_load` 走真 schema（block scalar 與引號都自然正確），
或至少把 block scalar 那條 `startswith` 排除改成 fail-loud（遇到就紅並要求改判準）。

### M-5（收尾）`_ADR_LOC_CAP_MIN = 1000` 兩端皆無機械綁定

```bash
grep -rn "_ADR_LOC_CAP_MIN" tools/ | grep -v pyc
tools/tests/test_doc_loc_baseline_freshness_r60.py:2193:_ADR_LOC_CAP_MIN = 1000
tools/tests/test_doc_loc_baseline_freshness_r60.py:2263:  if not (k == "cap" and int(v) < _ADR_LOC_CAP_MIN)]
```
只有定義與使用，**沒有任何測試**斷言：
- live LOC cap（實測 `check_loc_budget.py --json` → `cap=20438`）必須 **>** 1000；
- 額度派發上限 `AUTOSDD_QUOTA_MAX_FANOUT`（出廠 16）必須 **<** 1000。

兩個錨都只活在該常數的散文註解裡。任一端漂移（LOC 分級大幅瘦身／額度上限被調高）時，
豁免面會靜默變寬或變窄，而表徵與正常一模一樣。這正是本 repo 判過的「同一份知識住多個家、只有一個家被鎖」。
**鑑別力本身是好的**（`test_quota_domain_cap_is_told_apart_from_the_loc_cap` 雙向自證，我覆跑通過）——
問題只在那個分界數字沒被釘住。

**修法草案**：在同一支測試加兩行：`assertGreater(live["cap"], _ADR_LOC_CAP_MIN)` 與
`assertLess(quota_policy.MAX_FANOUT_DEFAULT, _ADR_LOC_CAP_MIN)`，訊息寫明「兩個領域的量級一旦靠攏，
本判準就失去鑑別力，請改用別的分辨方式而不是調這個常數」。

---

## MINOR

### m-1（P11）`_notify_enabled` 結構鎖是行首字串啟發式
```
GREEN  gate itself                     （正確）
RED    single-line bypass              （正確）
RED    multi-line bypass `notify(`     （正確 — 首行 strip 後即 "notify("）
RED    trailing-comment bypass         （正確）
GREEN  ok = notify("t","m")            ← 漏
GREEN  self._n.notify("t","m")         ← 漏
GREEN  aliased import n("t","m")       ← 漏
```
`notify()` 回 bool，`if notify(...)` / `ok = notify(...)` 並非不可能的寫法。
另 `assert text.count("self._notify(") == 2` 是寫死站點數，未來會以「把 2 改成 3」的方式被滿足
（作者已在訊息裡自陳這一點，故僅列 minor）。
**修法草案**：改用 `ast` 找 `Call(func=Name('notify'))`，判「該 Call 的 keywords 是否含 `enabled`」。

### m-2（收尾）現查入口鎖的分母由散文慣例決定
`_LIVE_ENTRY_RE = \b(?:python|python3)\s+((?:tools|scripts|AISDLC_SDD|AutoClaude|\.claude)[\w/.-]*\.py)`
⇒ 只有 CLAUDE.md 內**反引號中寫了 `python ` 前綴**的路徑才進分母，實測 6 支。
而同一份 CLAUDE.md 同樣要求「現跑」卻沒寫前綴的三支 probe 不在分母：
`tools/probe/misstep_attribution.py`（「現跑那支腳本即可」）／`tools/probe/audit_session.py`／
`tools/probe/xplat_hazard_census.py`。今日實跑三支皆 rc=0、無 traceback，故**今天無實害**；
但立案缺陷 C5 正是「文件要你現跑的東西壞了沒人知道」，而那三支就在射程外。
**修法草案**：把 regex 的 `python\s+` 前綴改成可選，或另立一條「`tools/probe/*.py` 全部納入」的分母。

### m-3（P6）`ci-gate.sh:280` 註解已成假話，且該檔本輪未被修改
```
280:# advisory warn。**advisory：永遠 exit 0、不阻擋硬閘**（P3，對齊 DEF-37-001 routed「缺即 warn」）。
```
`gitignore_coverage_lint.py` 改 fail-closed 後「永遠 exit 0」不再成立（`ci-gate.sh:22` 是 `set -euo pipefail`、
該行無 `|| true`）。同一份知識住兩個家、只改了一個家。

### m-4（P2）「三族」vs「四族」
`run_root_unittests.py:58` 的重釘註解逐字寫「**三族**」（wrapper forbidden 族＋dev_start R23 族＋R25 族），
交付給複審的說明寫「四族」。實際是 3 族、12 支方法（不是 11 支，見裁決表）。

---

## 鑑別力裁決表

| # | 判準 | 注入紅 | 還原綠 | 會被無關錯誤誤觸？ | 裁決 |
|---|------|--------|--------|------------------|------|
| 1 | `_FORBIDDEN_CASES` 併表 ＋ 計數鎖（P2） | 截斷 10→9 ⇒ `9 != 10` FAIL；拔掉 SSOT 內 `.ForEach(` ⇒ **只有** `case='ps1:array-foreach-method'` 這一格 FAIL 並在訊息中具名 | 真表 rc=0 | 否——逐案 subTest，失敗訊息直指樣本名與立案史料 | ✅ 有鑑別力 |
| 2 | `_FALSE_NEGATIVE_CASES` / `_FALSE_POSITIVE_CASES` 併表（P2） | 破壞正則會紅（沿用原斷言） | 真表綠 | 否 | ⚠️ 判準本身可用，**但無樣本數鎖**：3→1／2→1 截斷後全綠（M-2） |
| 3 | `net_cap_schedule_problems()`（P2） | 三種注入我各覆跑一次：改寫既有列／輪號不遞增／追加更寬上限 → 皆有對應標籤 | 真表 `[]`；正確方向追加（更晚輪號＋更小上限）→ `[]` | 否——三個標籤互不串音 | ✅ 有鑑別力 |
| 4 | `_GUARD_TOTAL_TRIPLE_RE` 收負號（P2） | `20000 → 19000（-1000）` → `(20000,19000,-1000)`；`−`(U+2212) 同 | `（+1000）` → `+1000` 不變 | 否 | ✅ 修正正確（但它服務的那條斷言本身是 B-1） |
| 5 | `agent_template_lint` 四桶（P6） | — | — | — | ❌ 立案數字假、活分母 1、逃生門被釘成契約（B-2） |
| 6 | 4 支 lint fail-open→fail-closed（P6） | `main([空 repo])` → rc=1 ＋ `::error::` 進 stderr | 正常 repo rc=0 | 否——`== 1` 精確相等，退回 `return 0` 立刻紅 | ✅ 有鑑別力；2 支「把 fail-open 釘成契約」的測試確為**同位置改寫**（原名／原 docstring／原斷言逐字保留在新 docstring），非刪測試 |
| 7 | `test_shell_portability_contract_r85` 射程普查（P7） | 合成新 `shell=True` 面 → 掃描器看得到（該檔自帶 `test_the_scanner_itself_can_see_a_new_surface`，我覆跑通過） | 122 passed | 否 | ✅ 有鑑別力 |
| 8 | 同上「真實 playbook 假紅普查」（P7） | 母體非空自證 `>= 15` | 命中 0 | 否 | ⚠️ 母體敘述失準＋兩個靜默丟值形態（M-4） |
| 9 | `test_the_mutation_schema_demands_portable_commands`（P7） | 只要整段 schema 內有「可攜」二字即通過 | — | 否 | ❌ 關鍵字當充分條件，欄位級缺口不可見（B-4） |
| 10 | `test_r85_subtraction_locks` GoalSynthesis 三格（P11） | `validation_failed` 有健康客戶端對照組（恆真檢查） | 122 passed | 否 | ✅ 有鑑別力（含反向恆真自證，是本輪體例最好的一支） |
| 11 | `_notify_enabled` 結構鎖（P11） | 單行／多行／帶註解 bypass 皆紅 | 閘門本體綠（第一版假陽性確已修正） | 否 | ⚠️ 三種寫法漏抓（m-1） |
| 12 | `unattended_authz` 授權邊界（P12） | Bash 端到端：`git push`／`sudo git push`／`VAR=1 git commit`／`xargs git push` 皆 rc=2；`# git-guard-ok:` 豁免**無效**（仍 rc=2） | `git status`／`ls -la && echo hi`／`python -c "print(1)"`／未設 UNATTENDED 皆 rc=0 | 否（mac 側零附帶面實測） | ⚠️ mac/Bash 側成立；**PS 側失守 ＋ 一筆假紅**（B-3） |
| 13 | exe-argv transitive 可達性（P12） | 一半守／零呼叫端／深度 4 皆紅；`git`／`python`／`node`／`docker` 不判 | 全庫 24 筆使用點 → offenders 0、parse_failures 0、band [] | 否——雙平台方向各自自證 | ⚠️ 跨模組假綠（M-3）；分母非 0（24），不是恆綠 |
| 14 | 現查載具 smoke（P12/收尾） | 合成 `import definitely_not_a_module_r85` → traceback 被抓到；reset probe 合成語料端到端印出「reset 相異字面 1 個」 | 6 支入口實跑 0 traceback | 否——改判 traceback 而非 rc，2/6 合法非零不誤觸 | ✅ 有鑑別力；分母偏窄（m-2）。「rc 改判 traceback」這個取捨我覆跑同意 |
| 15 | ADR 量測 token 領域鑑別（收尾） | `cap=19999`（LOC 量級、與現查 20438 不符）→ 1 筆紅並具名 | `cap=4`／`cap=16`（額度量級）→ `[]` | 否 | ✅ 有鑑別力，**但分界常數兩端無鎖**（M-5） |

---

## `MIN_TESTS` 3279 → 3268 的裁決（指定任務）

### 逐族樣本數（我逐字比對，不採信自陳）

| 族 | HEAD 測試方法 | WT 測試方法 | HEAD 樣本 | WT 樣本 | 逐字保留？ | 有樣本數鎖？ |
|---|---|---|---|---|---|---|
| ① `test_check_wrapper_thinness._FORBIDDEN_CASES` | 10 支 `test_forbidden_*` | 1 支 `test_forbidden_patterns_are_detected` | 10 | **10** | ✅ 10/10 逐字（含 `for f in "$@"` 那個跨行拼接字串，我逐段對過） | ✅ `assertEqual(len,10)` |
| ② `test_dev_start._FALSE_NEGATIVE_CASES` | 3 支 | 1 支 | 3 | **3** | ✅ 3/3 逐字（三行 log 注入完全相同） | ❌ 無 |
| ③ `test_dev_start._FALSE_POSITIVE_CASES` | 2 支 | 1 支 | 2 | **2** | ✅ 2/2 逐字（`daemon backend ` / `high-end ` 兩段雜訊字面不變） | ❌ 無 |
| 合計 | 15 支 | 3 支 | 15 | **15** | 零損失 | 1/3 |

方法數淨變化 **−12**（9＋2＋1），不是 −11。

**生產側同步驗證**（併表同時把 `check_wrapper_thinness.py` 的 16 份重複關鍵字收成兩個常數，−177 行）：
```bash
.venv/bin/python  # AST 取 HEAD 與 WT 的 _FORBIDDEN，逐鍵逐值比對
HEAD keys 16 WT keys 16
keys equal: True
value diffs: {}
```
⇒ 16 個鍵、每一鍵的關鍵字 tuple **完全相同**，判準零損失。

**逐案鑑別力實證**（併表後仍逐案報出）：拔掉 SSOT 內 `.ForEach(` 一個關鍵字 →
```
FAIL … (case='ps1:array-foreach-method', why='DEF-101-095 …(1,2,3).ForEach({...}) 是陣列型別的 .ForEach() 方法…')
AssertionError: False is not true : ps1:array-foreach-method 注入後診斷未出現 '.ForEach('
```
**只有那一格**紅，並在失敗訊息中帶出案例名與立案史料。

### 裁決

- **併表本身：正當。** 15 個注入樣本一個不少、期望 token 一個不變、逐案報出且鑑別力經合成注入實證；
  生產側 `_FORBIDDEN` 16 鍵值 AST 比對零差異。P2「注入樣本、期望值與斷言一個都沒有少」這句**經查為真**。
- **`MIN_TESTS` 下修：不正當。** 最終樹實測收集 **3284 > 舊下限 3279** ⇒ 舊下限根本不會紅，
  下修不是併表的必要後果，而是把「靜默蒸發仍全綠」的窗口從 0 擴到 16，且兩層保鮮期都不會出聲。
  下修同時削掉了本 repo 唯一還看得見「族②③ 樣本被刪」的間接訊號（見 M-2 — 併表後那個訊號本來就沒了，
  下修讓總量面也一起鬆掉）。
- **配套條件**：收尾窗口以最終樹重釘為 **3284**；並補上族②③ 的樣本數鎖（M-2，三行）。
  兩件事做完之後，這次併表在我這裡是**淨改善**。

---

## 我駁回的本輪宣稱（逐筆附實測）

| # | 被駁回的宣稱 | 出處 | 實測 |
|---|---|---|---|
| 1 | 「R85 是第一次淨減法輪」 | `test_adr_xplat001_c1c2_lock.py:3236` | `repin_round_nets()` → `(85, **+468**)`，正值；該測試當下 FAIL |
| 2 | 「四桶當回合實測共 199 條，其中 198 條…」 | `agent_template_lint.py:24` ＋ 其測試 `:156,:158` | 以 lint 自己的掃描面實算 = **302 / 301** |
| 3 | 「值取本 runner 當回合印出的計數 3268，零加減推算」 | `run_root_unittests.py:58` | 最終樹 `countTestCases()` = **3284**（stale 16） |
| 4 | 「本輪實測母體：**9 支 playbook**、19 個 evaluator_command 值」 | `test_shell_portability_contract_r85.py:248` | 其中一支經 `Playbook.model_validate` **INVALID**；真 playbook 母體 **20 支** |
| 5 | 「mac 側那半已經補上了…判準與訊息兩邊共用 `tools/lib/unattended_authz.py` 這一個家」 | `lint_powershell_command.py` 檔頭訂正 | 那個「家」對引號絕對路徑／`sudo git`／`VAR=1 git` 全 MISS，而同輪另一份實作全 HIT；PS 側端到端 rc≠2 |
| 6 | 「1 桶擴到 4 桶」＝擴面 | P6 交件說明 | 落地後活分母 **1**（`tools` 桶 **0**）；且無副檔名條目結構上不進分母 |
| 7 | 「三族／四族」的族數與方法數 | `run_root_unittests.py:58` vs 任務書 | 實為 **3 族、−12 支方法** |

**我不駁回**（覆跑後同意）：
- P12「smoke 判準由 rc 改判 traceback」——我覆跑 6 支入口，`check_loc_budget.py` 因真實預算狀態回 rc=1、
  `quota_policy.py` 對未知引數回 rc=2，判 rc=0 確實是 2/6 假紅。取捨正確。
- P11「`_notify_enabled` 第一版判準是假陽性、當回合自證修正」——現版對閘門本體正確放行，該自陳為真。
- P6「2 支測試是改寫意圖而非刪測試」——`git diff` 顯示為同位置修改，原名／原 docstring／原斷言
  逐字保留在新 docstring 內，且新斷言用精確 `== 1`，退回 `return 0` 會立刻紅。

---

## Blocking 清單（附持有面）

| ID | 標題 | 持有面（常數／史料／消費端是否同一持有面） | 建議處置窗口 |
|----|------|------|------|
| **B-1** | 淨減法輪斷言把本輪結果寫死，當下就紅 | `tools/tests/test_adr_xplat001_c1c2_lock.py` **單檔**（常數＋斷言＋docstring 同住） | 收尾單人窗口 |
| **B-2** | P6 立案數字假（199/198 vs 302/301）＋活分母 1 ＋逃生門被釘成契約 | `AISDLC_SDD/scripts/agent_template_lint.py` ＋ 同目錄 `tests/`，**兩檔同一持有面**（錯數字兩份都要改） | 可派並行包（持有面完整） |
| **B-3** | 授權邊界 SSOT 弱於它取代的實作；Windows 側對鐵律二明訂形態失守＋一筆假紅 | `tools/lib/unattended_authz.py`（判準）＋ `.claude/hooks/lint_powershell_command.py`（消費端）＋ `tools/tests/test_check_hooks_liveness.py`（鎖）— **三處，跨持有面** | 收尾單人窗口（鐵律七） |
| **B-4** | 可攜性要求漏 `new_step_evaluator_command`；鎖用關鍵字當充分條件 | `AutoClaude/autoclaude/decision/prompt_builder.py` ＋ `AutoClaude/tests/execution/test_shell_portability_contract_r85.py`，**兩檔同一持有面** | 可派並行包 |

**MAJOR 五筆**（M-1 … M-5）建議與 B 同輪收；其中 M-1／M-2 必須與收尾重釘同一次變更完成，
否則 `MIN_TESTS` 會再一次以「當回合量測值」的名義被寫成一個已經過期的數字。

---

## 誠實劃界（本複審**沒有**做到什麼）

1. **Windows 未真機驗證。** B-3 的「PS 側失守」由三段可重跑的純函式量測支撐
   （`unattended_hits()` 直呼、`mask_regions()` 輸出、兩份實作對比），但「Claude Code 在 Windows 上
   實際送出的 `tool_input.command` 長什麼樣」未取證 ⇒ 標**靜態推論**。
2. **P6 我只驗了 `agent_template_lint` 與 fail-closed 四支的判準本身**，未逐支重跑 `ci-gate.sh`
   （會動到 AISDLC_SDD 的閘門執行面，且本複審唯讀）。`agent_scg_anchor_lint.py` 同輪夾帶的
   新判準 5（SCG 閘門英文名跨檔一致）我只確認分母非空（7 支閘門、0 problems），未做合成注入。
3. **紅燈我沒有逐筆歸因。** 我只確認了 `TestGuardLayerRatchet` 那一族的性質（1 筆 blocking＝B-1、
   其餘屬例行重釘漂移且部分為非決定性，見 §0）。其餘 15 支（`test_check_defect_log_crossref`／
   `test_governance_docs` 一族，以及 `test_subprocess_encoding_hygiene::test_e501_debt_only_shrinks`
   實測 `141 not less than or equal to 139`）只確認存在，未判「屬收尾漂移或真缺陷」。
   ⇒ **不要把本檔讀成「除了 B/M/m 之外全樹乾淨」。**
   另外：**兩次同指令全樹跑的紅數不一致（23 vs 17 個相異名字）本身就是一筆待查**——
   我沒有追它的根因，只確認 B-1 不在非決定性那一側。
4. **P11 的 `TestExamplePlaybookAgainstPostgres` 走 `pg_real` 標記**，本輪環境雖有 PG DSN 注入，
   我未確認該類是否真的執行過（122 passed 內是否含它未逐案查）。
5. **注入全部在記憶體內完成**，未產生任何可供他人重現的磁碟副本；重跑請直接用本檔各節貼出的指令。
