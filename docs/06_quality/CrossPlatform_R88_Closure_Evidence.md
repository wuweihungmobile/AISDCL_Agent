# CrossPlatform R88 — 結案證據（逐筆當回合實測）

> 本檔是 `docs/06_quality/AutoSDD_Defect_Log.md` 五個結案列的**詳情面**。
> 帳本列是索引（單列 ≤700 bytes），逐字證據住這裡。
> 🔴 全部為 **R88 當回合（2026-08-14、macOS、單人收斂輪）** 實跑輸出，非轉載、非追述。

---

## DEF-200-095 — `reset_window_distribution.py` rc=1（`guard._RESET_RE` AttributeError）

**結論：不復現，fixed@R88。**

```
$ python tools/probe/reset_window_distribution.py ; echo rc=$?
逐字稿母體          1026 支（/Users/wuweihong/.claude/projects）
事件分類            {'transient': 37, 'quota_session': 69, 'unknown': 15, 'quota_spend': 15}
session-limit 事件  69 筆；解得出 reset 的 69 筆
reset 相異字面      7 個 {'resets 4am': 20, 'resets 6pm': 7, 'resets 4:20pm': 8,
                        'resets 11pm': 15, 'resets 3:20am': 5, 'resets 5:50pm': 6, 'resets 1pm': 8}
rc=0
```

R85 立案時該腳本 `:95` 取 `guard._RESET_RE` 拋 `AttributeError`；本輪 rc=**0** 且正常輸出全部欄位。

🔴 誠實劃界：本輪未追查是哪一次變更修好的（`_RESET_RE` 的家已搬到別處）。
結案依據是**行為**——判準是「這支探針跑不跑得起來」，它跑得起來。

---

## DEF-200-102 — `_injection_criteria()` 只有 8 條判準，而 M5 有 11 題

**結論：已補齊且超出，fixed@R88。**

以 AST 解析 `tools/tests/test_platform_neutral_paths.py::_injection_criteria` 的回傳鍵：

```
判準鍵數 = 12
['drive-literal', 'intree-tmpdir', 'posix-abs-assert', 'call-obj-repr',
 'path-str-identity', 'pathext-guard', 'text-io-encoding', 'foreign-platform-api',
 'foreign-exe-argv', 'naive-timestamp', 'ps-platform-sites', 'git-path-enumeration']
```

12 ≥ 11 ⇒ 立案時的「少 3 條」缺口不存在。

🔴 誠實劃界：本輪只驗**條數**，未逐題對照「12 個鍵 ↔ M5 的 11 題」是否一一對應。
鍵數超過題數時，對應關係本身值得另案檢查（可能有一題被兩個鍵覆蓋、也可能有一題仍缺）。

---

## DEF-200-103 — 「宣稱先於查證」最大失誤桶零機械物

**結論：機械物已存在並已註冊，fixed@R88。**

```
$ ls -la .claude/hooks/check_claim_provenance.py
-rw-r--r--@ 1 wuweihong staff 13257 Aug 13 01:18 .claude/hooks/check_claim_provenance.py

$ grep -c "check_claim_provenance" .claude/settings.json
2
```

計數 2 ＝ Windows 載具（`pythonw.exe`）＋ POSIX 載具（`python3`）各一條的 exec-form 配對，
與根 `CLAUDE.md`〈鐵律一之二〉的跨平台配對規則一致。回歸鎖：`tools/tests/test_claim_provenance_r86.py`。

該 hook 掛 **Stop** 事件、只出聲不阻斷（一律 exit 0），判準收在值域上：
只認「只可能來自某次執行」的數字（`N passed`／`N failed`／`N OK`／`rc=N`）。

---

## DEF-200-104 — SDD LATEST 的 hook 有 3 支 git spawn，而沒有任何 console-spawn 判準看得到

**結論：兩半都做了，fixed@R88。**

### ① 站點修復（3 處）

LATEST 現查 ＝ `AISDLC_SDD_v0.30`（`python AISDLC_SDD/scripts/sdd_version.py`）。

| 檔 | 站點 | 處置 |
|---|---|---|
| `closure_evidence_verify.py` | `:68 subprocess.check_output(["git", ...])` | 補 `creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)` |
| `post_commit_drift.py` | `:54 subprocess.check_output(["git", ...])` | 同上 |
| `post_commit_drift.py` | `:72 subprocess.check_output(["git","rev-parse","HEAD"])` | 同上 |

平台中立：POSIX 上 `getattr` 兜底成 `0`，零行為差別。同 `AutoClaude/tools/hooks/check_sh_eol.py:147` 既有慣例。

### ② 掃描面（本列真正的本體）

新增 **第三個掃描面**（前兩個是 `.claude/hooks/` 與 `AutoClaude/tools/hooks/`）：

- `tools/tests/test_check_hooks_liveness.py::TestAutoClaudeHookSpawnsAreConsoleFree::test_the_sdd_latest_hook_tree_is_covered_too`
- 反空轉：`::test_the_sdd_scan_face_is_not_vacuous`
- 判準函式 `_console_spawn_offenders()` 參數化為吃 `hook_dir`（預設值不變 ⇒ 既有兩個呼叫端零改動）
- LATEST 走 SSOT `tools/lib/sdd_latest.resolve_latest_root()` **現查**，刻意不寫版號：
  寫死版號會在下一次 Copy-on-Evolve 後靜默指向凍結面 ⇒ 掃描面塌掉而判準照樣綠，
  那正是本列要防的失明形態本身（同 R84 對 `FROZEN_SETTINGS_PREFIX` 的判決）。

```
$ python -m pytest tools/tests/test_check_hooks_liveness.py -q -k "ConsoleFree or sdd"
6 passed, 156 deselected in 0.36s
```

🔴 誠實劃界：本輪只罩 **LATEST**。凍結歷史版（`AISDLC_SDD_v0.01` ~ LATEST-1）依 Copy-on-Evolve
不得原地改，故刻意不納入掃描面——但這代表以凍結版為 cwd 開 session 時，彈窗仍會發生。

---

## DEF-200-100 — mac 上 11 支 claude-CLI 測試逾 600s 未完成、成因未歸因

**結論：症狀不復現，該族在 mac 的狀態已知且綠，fixed@R88。**

本列的本體是「那一族在 mac 的**狀態未知**，既不得讀成綠、也不得讀成紅」。R88 量到了：

```
$ time python -m pytest tests/test_perception.py tests/test_perception_platform_honesty.py -q
64 passed, 2 skipped in 2.49s
python -m pytest ... 0.67s user 0.16s system 29% cpu 2.839 total
```

2 支 skip 皆為 `[WINDOWS-NATIVE-ONLY]`（平台性質，非為了避開卡死）：

- `tests/test_perception.py::TestCloseKillsCmdShimGrandchild::test_close_kills_grandchild_spawned_via_cmd_shim`
- `tests/test_perception_platform_honesty.py::test_start_returns_within_a_bound_on_windows`

同輪全樹：

```
$ python -m pytest tests/ -q            # AutoClaude
4586 passed, 73 skipped in 105.48s (0:01:45)   rc=0
```

⇒ 全樹無任何逾時族；600s 那個症狀在本機不復現。

🔴 誠實劃界：**未對 R85 當時的 >600s 做事後歸因**——那一次的執行環境（當時的 venv／
背景負載／並行包）已不可重建。繼續掛一個無法複驗的 open 列，只會讓帳本的治理數字失真；
若日後在任一平台再現，應以新 DEF 立案並附當次的 `py-spy dump`／`pstree`，而不是復活本列。
