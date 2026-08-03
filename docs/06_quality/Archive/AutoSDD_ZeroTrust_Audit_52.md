# AutoSDD ZeroTrust Audit 52 — C 軌新 BOM hook 審查 + 修復複審證據

> **對應計畫**：`docs/04_planning/AutoSDD_improving_52.md`。**日期**：2026-06-23。
> **標的**：`AutoClaude/tools/hooks/check_ps1_encoding.py`（commit `097d196`）+ 雙層 wiring + 單元測試。
> **方法**：parent 親跑階段一基線 → 主樹派 Architect/SA/QA 三鏡 zero-trust → 就地修復 SA 揪出之 P1+2×P2 → parent 親跑零退化矩陣複審。

## 1. 階段一基線（parent 親跑，逐位元可複現）

```
git log --oneline -6           → HEAD=47018db；工作樹乾淨
git log a2909d7..HEAD -- 'AISDLC_SDD/**/.claude/**'  → 空（SDD .claude 位元級零變更）
python -m pytest tests/ -q     → 3241 passed, 122 skipped in 123.46s（0 failed）
PYTHONUTF8=1 lint-imports      → Contracts: 8 kept, 0 broken
python tools/check_loc_budget.py → violations=0 (absolute=0 tier=0 special=0 total=0)
python tools/snapshot_sync.py --check → OK
pytest tests/tools/hooks/test_check_ps1_encoding.py → 6 passed（修復前）
```

**硬閘通過**：0 failed、3241 ≥ C 軌 floor 3,060。

## 2. 三鏡 zero-trust 裁定（主樹並行，DEF-24-001 合規：審 tracked 乾淨檔→主樹）

### Architect 鏡 — OVERALL PASS（2× P3）
- auto-fix vs exit 2 阻斷差異有實質技術根據（Write 無法產 BOM↔可控 LF）＝by-design。
- 雙層 wiring 必要（root 不遞迴載子目錄 hook）；matcher `Write|Edit`↔`Edit|Write` 集合語意等價。
- CLAUDE.md hook 表 6 個 distinct script 與 settings 一一對應，計數誠實。
- findings：ARCH-PS1-1（P3 UTF-16 雙 BOM 邊界，實測 `efbbbffffe...`）、ARCH-PS1-2（P3 子層缺 timeout）。

### SA 鏡 — OVERALL FAIL（1× P1 + 2× P2 + 1× P3）→ 修復後消解
- **FIND-1（P1，真缺陷）**：`main()` 僅防 None/falsy，不防錯型別真值；`resolve_path` except 不接 `TypeError`。subprocess 實證：
  - `file_path=[1,2]` / `12345` → `TypeError` @ `Path()` → rc=1
  - `tool_input=[1,2,3]` / `"oops"` → `AttributeError: .get` → rc=1
  - 頂層 `[1,2,3]` / `42` → `AttributeError: .get` → rc=1
  - （空 stdin/非 JSON/缺 tool_input/null/超長路徑 → rc=0 ✅）
  - 違反 docstring「永遠 exit 0、絕不阻斷」+ Nightly 紀律 #4「驗證鏡子自身要被驗證」。
- **FIND-2（P2）**：UTF-16(LE/BE) 被 `all(b<0x80)` 判非 ASCII → 前置 UTF-8 BOM。實測 `[UTF16LE noBOM] ret=1 head=efbbbf57007200`（損毀）/ `[UTF16LE+BOM] head=efbbbf fffe`（雙 BOM）。
- **FIND-3（P2）**：Big5/cp950 補 BOM → `utf8-decode-after-fix: FAIL 0xa7`，製造矛盾檔。
- **FIND-4（P3）**：`_init_utf8_streams()` 僅 `__main__` 呼叫；ascii-strict console 直接 import 呼叫 `fix_ps1_encoding` 之中文 print 拋 `UnicodeEncodeError`。但生產 wiring 經實證為 subprocess（`.claude/settings.json:30` / 根 `:44`）→ `__main__` 必走 → 風險為零。
- 路徑處理（相對/`..`/不存在/超長）、空檔、idempotency 皆安全。

### QA 鏡 — OVERALL PASS（2× P2 覆蓋缺口）
- 親跑 6 passed；6 測試非空殼、`== UTF8_BOM + body` 精確斷言符 Rule 9。
- `parents[3]` = AutoClaude 根（正確）、HOOK_SCRIPT exists=True，測試真指 HEAD hook 本體非死路徑。
- CLAUDE.md hook 表第 6 個登錄正確、描述與行為一致，帳本誠實。
- 缺口：G1（`.psm1/.psd1` 未測）、G6（`abs_path is None` 未經 CLI）、G9（壞 JSON，可選）。

## 3. 就地修復（dev-build-test 循環）

修復檔（皆 AutoClaude，非 SDD 凍結本體，免 Copy-on-Evolve）：
- `AutoClaude/tools/hooks/check_ps1_encoding.py`：
  - `read_hook_payload`：`return obj if isinstance(obj, dict) else {}`
  - `main`：`isinstance(tool_input, dict)` + `isinstance(file_path, str) and file_path` 雙守門
  - `resolve_path`：except 補 `TypeError`
  - `fix_ps1_encoding`：補 BOM 前 `raw.decode("utf-8")`，`UnicodeDecodeError`→no-op（一閘消解 FIND-2+FIND-3）
  - docstring：精確化「合法 UTF-8 且無 BOM 才補」分支
- `AutoClaude/.claude/settings.json`：BOM hook 補 `"timeout": 10`
- `AutoClaude/tests/tools/hooks/test_check_ps1_encoding.py`：+7 測試

## 4. 修復後複審（parent 親跑，QA 複審閘）

```
pytest tests/tools/hooks/test_check_ps1_encoding.py -v → 13 passed in 0.49s（6→13）
python -m pytest tests/ -q     → 3248 passed, 122 skipped in 122.87s（0 failed；基線 3241 + 7）
PYTHONUTF8=1 lint-imports      → Contracts: 8 kept, 0 broken
python tools/check_loc_budget.py → violations=0
python tools/snapshot_sync.py --check → OK
json.load(.claude/settings.json) + (../.claude/settings.json) → 雙檔 OK
```

端到端取證（生產命令形態 subprocess，`python AutoClaude/tools/hooks/check_ps1_encoding.py`）：
```
錯型別 payload {"file_path":[1,2]}     → rc=0（P1 修復；舊碼 rc=1）
正常中文 .ps1（Windows 絕對路徑）       → AUTO-FIX stderr + rc=0；head: efbbbf5772 69（補 BOM）
UTF-16 LE .ps1                          → 不動（fix_ps1_encoding 直呼單元測試 test_utf16_le_bom_ps1_is_noop 權威驗證）
```

**SA P1 攻擊向量已編成測試並通過**：`test_cli_wrong_type_file_path_fail_soft`（list/int file_path）、`test_cli_non_dict_tool_input_fail_soft`（list/str tool_input + 頂層 array/number）——此二測試在**修復前必紅**（SA 實證 rc=1），修復後 rc=0 綠，符 Rule 9。

## 5. 複審裁定

| 維度 | 結論 |
|------|------|
| 修復方向正確 | ✅ 型別守門兌現 fail-soft 契約；UTF-8 合法性閘消解編碼損毀，皆對齊 docstring 與 Nightly 紀律 #4 |
| 執行過程與結果真實 | ✅ 全部 parent 親跑，命令輸出逐筆引證（無虛報，守 [[no-fabricated-tool-output]]） |
| 未破壞收斂 | ✅ pytest 3241→3248（+7，0 failed）、lint 8 kept、LOC=0、snapshot fresh、TLC N/A |
| 缺陷帳本完整誠實 | ✅ DEF-52-001~006 全入帳並分流（5 fixed@improving_52 + 1 wontfix+理由），無漏記/虛報 |

**OVERALL: PASS**。SA 鏡 FAIL 之 P1+2×P2 已就地清償並以測試固定，Architect/QA 鏡 PASS。本輪結案。
