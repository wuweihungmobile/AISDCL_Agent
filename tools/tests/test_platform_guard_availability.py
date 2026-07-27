#!/usr/bin/env python3
"""架構判準的機械強制：**跨平台守門的可用性條件必須以目標平台的出廠組態為準**（R58 落地）。

## 判準的來由（DEF-101-507／508）

R58 是 R1~R57 之後**首次**在原生 Windows 11 上開工的一輪（此前全程於 macOS 模擬）。首跑
`tools/run_root_unittests.py` 的 skip 清單就揪出：

    tools/tests/test_install_windows_nightly.py:193
    @unittest.skipUnless(shutil.which("pwsh"), "本機無 pwsh，跳過語法解析…")

`install_windows_nightly.ps1` 是 **Windows 專屬**安裝器，唯一需要語法守門的平台就是 Windows；
而 Windows 11 出廠只有 Windows PowerShell 5.1、**不含 pwsh 7**（本機實測 `pwsh` NOT FOUND），
於是這道守門**在它唯一要保護的平台上恆 skip**，卻在裝了 pwsh 的 macOS 開發機上會跑——
**守門在不需要它的平台生效、在需要它的平台失效**。而「能力不可得」是假的：5.1 內建同一個
`[System.Management.Automation.Language.Parser]` API，R58 實測對該檔 parse 出 0 errors。

病灶成因可複製，證據就寫在那支測試自己的 skip 理由旁邊（「跨平台安全（macOS/Linux pwsh
皆可跑）」）——**作者當時的參照系是自己的開發機**。這是 DEF-101-348（Windows 專屬測試連續
多輪全 APPROVE 卻從未在原生 Windows 上跑過）的直系後代，只是失效點從執行環境搬到了條件式。
故不只修一行，而是升格為判準並機械化。判準全文另記於
`docs/06_quality/CrossPlatform_Scan_Dimensions.md`。

## 本檔掃什麼、不掃什麼

掃描面一律取自 `_scanned()`＝**git 已追蹤 ∪ 未追蹤但非 ignored**。初版只取 `git ls-files`，
於是本輪自己新增的測試檔（當時全是 untracked）整批在面外——「全綠」的基線在定義上排除了本輪
自己寫的程式碼。理由與實測後果詳見 `_scanned` 的 docstring（ARCH-R58R1-02／ARCH-R58SD-02）。

**已實測涵蓋**：
  * Python 測試檔（全 repo `test_*.py`，含未追蹤）內以 `shutil.which("pwsh")`／`which("pwsh")`
    取得能力、卻在**同一檔案內完全不提及 `powershell`** 者 → 判為「pwsh-only 門檻」。
  * active（非凍結版）`.ps1` 的**註解**裡出現可照抄的執行示範 `pwsh <某檔>.ps1`、而同檔完全
    不提供 `powershell` 寫法者 → 判為「使用者照抄必失敗的用法示範」（DEF-101-508 即此形態；
    與 R57 DEF-101-479 的 zsh glob 同類——執行期印給使用者複製貼上的指令本身就是缺陷面）。
  * `powershell_exe()` 這個 SSOT 的**呼叫端鎖**：自帶同語意有序 order tuple、`tools/` 非測試
    工具腳本自行串 `which()` 偏好鏈、已知消費端死 import——見
    `PowerShellExeSsotCallsiteLock`（含它自己的涵蓋面三段式劃界）。

**已實測不涵蓋**（誠實劃界，非窮舉）：
  * 以間接方式取得可執行檔名者（如把 `"pwsh"` 存進變數再 `which(var)`、從設定檔讀名字、
    字串拼接）——本檔做的是字面掃描，不做資料流分析。
  * `.sh`／`.yml`／`.md` 內的 pwsh 相依（R58 實掃：`.sh`／`.ps1` 生產碼**零支實際 spawn pwsh**，
    命中全為註解；`.yml` 的 `shell: pwsh` 是 GitHub runner 語意、runner 保證有 pwsh，
    不屬本判準範圍）。
  * 「守門在目標平台可用但**邏輯**錯誤」——那是別的測試的職責，本檔只管「可用性條件」。

**未窮舉**：本清單只列已實機量測過的形態，不做「唯一殘餘風險是 X」這類宣稱。
"""
from __future__ import annotations

import ast
import re
import sys
import unittest
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _registry_hygiene import empty_reason_keys, stale_problems  # noqa: E402
from _repo_scan import scanned  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 豁免必附理由（理由為空字串即視為未附 → 一律紅，防「先加豁免再補理由」變成永久 TODO）。
# stale 自檢：豁免列的檔案若不存在也紅（避免名冊腐化成無人維護的死清單）。
_PWSH_ONLY_EXEMPT: dict[str, str] = {
    "AISDLC_SDD/scripts/tests/test_install_post_commit_exec_bit.py": (
        "R58 Scan-A2 回源複核判定為正確而非缺陷：該檔測的是 Unix chmod +x 分支，本身另有 "
        "`skipif(os.name == 'nt')` 把 Windows 整個擋在外，故它永遠只在 macOS/Linux 上執行——"
        "而那些平台上 PowerShell 的執行檔名**就只有** `pwsh`（`powershell` 這個名字不存在）。"
        "此處無兜底是對的：兜底一個在該平台不可能存在的名字沒有意義。"
    ),
}

# ── 能力出處登記表（R58 第二條落地）─────────────────────────────────────────
# **為什麼要這張表**：DEF-101-507 的病灶不是打錯字，而是**作者以自己開發機的組態當參照系**
# ——他知道自己機器有 pwsh，就寫了 `skipUnless(which("pwsh"))`，沒問「目標平台出廠有沒有」。
# 光靠上面那條 pwsh 專屬掃描只能擋住 pwsh 這一個名字；下一個人探測別的工具（`uv`、`docker`、
# `node`…）會重演同一個錯誤，而掃描器不會說話。
#
# 故把判準前移到**登記**：任何在測試檔裡被 `which()` 探測的能力名稱，都必須在此登記
# 「哪些平台出廠就有、哪些需要另裝」。登記這個動作本身就強迫作者回答那個他原本沒問的問題。
# 這是「把人容易忘的判斷變成機械上不可略過的一步」，同 repo 既有的豁免須附理由慣例。
#
# 表中敘述**只需誠實**，本鎖不解讀內容（不做自然語言判讀，那會是假宣稱）；它只保證
# 「有人被迫寫下來過」＋「表不腐化」。真正的正確性由上面那條 pwsh 掃描與人的複審把關。
_CAPABILITY_PROVENANCE: dict[str, str] = {
    "powershell": (
        "Windows **出廠即有**（Windows PowerShell 5.1，隨 OS 附帶）；macOS/Linux **不存在**"
        "此執行檔名（PowerShell Core 的檔名是 pwsh）。故 Windows 專屬守門應以此為首選探測對象。"
    ),
    "pwsh": (
        "**兩平台皆非出廠**——Windows 11 出廠不含 pwsh 7（R58 於真 Windows 11 Pro 實測 NOT "
        "FOUND）、macOS 需 brew 安裝。**單獨探測 pwsh 等於把守門建立在『開發機剛好裝過』上**"
        "（DEF-101-507）。應走的 SSOT 是 `_platform_helpers.powershell_exe()`。"
        "【收斂現況，誠實劃界（ARCH-R58R1-03）】已機械鎖住的是：(a) 任何檔案不得自帶同語意的"
        "**有序** order tuple；(b) `tools/` 下**非測試**的工具腳本不得自行以 which() 串偏好鏈；"
        "(c) 已知消費端必須真的 import 並呼叫 SSOT——見 `PowerShellExeSsotCallsiteLock`。"
        "**尚未收斂**：測試檔內既有的 `which(\"powershell\") or which(\"pwsh\")` 手寫偏好鏈"
        "（數量以掃描為準，不在此寫死），以及 `AutoClaude/tools/` 下的同型寫法。故本欄"
        "**不宣稱**『一律已走 SSOT』——上一版寫成一律，是與同輪三份 fork 並存的自相矛盾宣稱。"
    ),
    "git": (
        "Windows 需 Git for Windows、macOS 需 Xcode CLT 或 brew——**皆非嚴格出廠**，但本 repo "
        "是 git repo，任何能 checkout 它的機器必然有 git，故以 `which('git')` 做門檻是安全的。"
    ),
    "bash": (
        "macOS **出廠即有**（/bin/bash 3.2）；Windows 需 Git for Windows 且 `Git\\bin\\bash.exe` "
        "**預設不在 PATH**（官方建議設定），故 Windows 上 `which('bash')` 常為 None 或誤中 "
        "System32 的 WSL 轉發器——本 repo 另有 `tools/lib/bash_probe_spec.py` 專責驗活，"
        "不可只靠 `which`。"
    ),
    "claude": (
        "**兩平台皆非出廠**（npm 全域安裝）。Windows 上解析為 `.cmd` shim，故需經 cmd.exe，"
        "這正是 `%VAR%` 展開缺口的來源（見 `AutoClaude/autoclaude/perception/pty_wrapper.py`）。"
    ),
    "tar": (
        "兩平台**皆出廠即有**（Windows 10 1803 起內建 bsdtar）。"
    ),
    "pytest": (
        "**非出廠**，由本 repo 的 `.venv` 提供（`uv pip install -e '.[dev,...]'`）。以 console "
        "script 名稱探測時要注意 venv 未啟用的情境。"
    ),
}

# 「可照抄的執行示範」樣式：註解行內出現 `pwsh <path>.ps1`。
# 刻意要求後面接 `.ps1`：純粹提到 pwsh 這個詞（例如說明「裝了 pwsh 也可以」）不算示範。
_PWSH_EXAMPLE_RE = re.compile(r"pwsh\s+[\w./\\$:{}-]*\.ps1", re.IGNORECASE)
_PS1_EXAMPLE_EXEMPT: dict[str, str] = {}

# ── PowerShell 執行檔探測的 SSOT 與其呼叫端鎖 ─────────────────────────────────
# 形狀刻意鏡射 `test_find_git_bash_parity._PS_STRIPPER_SSOT_MODULE`：模組名／符號名各收斂成
# 單一常數，未來再拆檔只需改這兩個字串（R57 已兌現過一次這個設計的價值）。
_PS_EXE_SSOT_MODULE = "_platform_helpers"
_PS_EXE_SSOT_SYMBOL = "powershell_exe"

# 已知消費端名冊：**刻意包含非測試檔**。`gen_ps_comment_golden.py` 是 golden fixture 的
# 產生器，引擎選錯會直接污染 ground truth（然後全 repo 的離線差分都以錯的基準為真），
# 而它的檔名不含 `test_`，在舊掃描面（只掃 `*test_*.py`）完全在面外——這正是
# ARCH-R58R1-03 指出的破口。
_PS_EXE_CONSUMERS = (
    "tools/gen_ps_comment_golden.py",
    "AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py",
    "tools/tests/test_install_windows_nightly.py",
)


def _scanned(pattern: str) -> list[str]:  # noqa: D401  (薄委派，契約見 _repo_scan)
    """掃描面 ＝ git 已追蹤 **∪** 未追蹤但非 ignored（`--others --exclude-standard`）。

    **為什麼不能只看 `git ls-files`（ARCH-R58R1-02／ARCH-R58SD-02）**：新檔在 `git add`
    之前也必須被守，否則新程式碼享有豁免。本檔與同輪其他掃描器初版都只列 tracked，而本輪
    新增的測試檔當時全是 untracked——於是「全套測試 ＋ 守門工具全綠」的基線**在定義上排除了
    本輪自己寫的程式碼**，正是本輪立案要消滅的形態（宣稱涵蓋面 ≠ 實際涵蓋面）在守門器自身
    復發。不是理論風險：複審者實測 `git add` 之後 `test_every_probed_capability_is_registered`
    立刻翻紅（`AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py` 探測的
    `powershell.exe` 未登記），證明盲區真實存在。

    **不會誤掃暫存／垃圾檔**：`--exclude-standard` 已套用 .gitignore／.git/info/exclude／
    global excludes，故 `.venv/`、`__pycache__/`、產物與 log 皆不入面（**量測時點必須註明，否則讀取當下即為假**——R58 round 2 SD-R58R2-02 訂正：
    round 1 複審時〔`git add` **前**〕實測 `*test_*.py` 未追蹤集合恰為本輪新增檔，**證明盲區真實存在**；
    收輪 `git add` **後**兩集合皆為空，union 於當下多納入 0 筆。兩個事實不衝突：前者是證據效力、
    後者是現況）。**已實測不涵蓋**：
    被刻意 ignore 的目錄仍在面外——這與 git 自身的可見性定義一致，不另行擴張。**未窮舉**：
    不宣稱「除此之外無盲區」。
    """
    # R58 round 2 ARCH-R58R2-01：實作收斂至 `_repo_scan.scanned`（同輪另一支掃描器
    # 仍是 tracked-only，兩套政策且無記載理由）。本函式保留為薄委派，只為讓本檔既有
    # 呼叫點與 docstring 不必全數改名——契約以 `_repo_scan` 為準。
    return scanned(pattern)


def _which_string_args(tree: ast.AST) -> set[str]:
    """抽出檔案內所有 `which("X")`／`shutil.which("X")` 的字面字串引數。"""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        called = (
            func.id if isinstance(func, ast.Name)
            else func.attr if isinstance(func, ast.Attribute)
            else None
        )
        if called != "which":
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            names.add(first.value)
    return names


def platform_order_sequences(tree: ast.AST) -> list[int]:
    """回傳「同時字面列出 `powershell` 與 `pwsh` 的**有序**序列（tuple/list）」的行號。

    這就是 SSOT fork 的指紋：`("powershell", "pwsh") if win else ("pwsh", "powershell")`
    被逐字複製到別的檔案。

    **刻意只認 tuple/list、不認 set**：SSOT 的全部價值就在那個**順序**（Windows 先出廠的
    5.1、其他平台先 pwsh），`set` 在語言層就沒有順序、不可能是 order tuple；而本檔自己的
    偵測器自驗需要用 `{"pwsh", "powershell"}` 斷言「探測到的名稱集合」——把 set 一併禁掉
    只會讓鎖抓到自己的斷言（假陽性），與判準無關。
    """
    hits: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Tuple, ast.List)):
            continue
        literals = {
            e.value for e in node.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        }
        if {"powershell", "pwsh"} <= literals:
            hits.add(node.lineno)
    return sorted(hits)


def powershell_which_chains(tree: ast.AST) -> list[int]:
    """回傳「自行以 `which()` 串出 powershell/pwsh 偏好鏈」（`or` 運算式）的行號。

    要求**兩個名字都出現在同一條 `or` 鏈裡**才算：單獨一個 `which("pwsh")` 不是偏好鏈
    （那是 `PwshOnlyGateTest` 的守備範圍，兩鎖不重疊也不互相取代）。
    """
    hits: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.BoolOp) or not isinstance(node.op, ast.Or):
            continue
        names: set[str] = set()
        for value in node.values:
            names |= _which_string_args(value)
        if {"powershell", "pwsh"} <= names:
            hits.add(node.lineno)
    return sorted(hits)


def _parse_or_none(path: Path) -> ast.AST | None:
    """讀檔並 parse；語法／編碼壞掉交給別的閘門，本檔不重複翻紅。"""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    try:
        with warnings.catch_warnings():
            # 掃描面內既有檔案（如 test_ps51_compat.py 的模組 docstring）帶有非 raw 字串的
            # `\s`，`ast.parse` 會噴 DeprecationWarning。那是別的檔案的既有債，本鎖不因
            # 掃描動作替它產生噪音（沿用 test_find_git_bash_parity.py 既有慣例）。
            warnings.simplefilter("ignore", DeprecationWarning)
            return ast.parse(text)
    except SyntaxError:
        return None


class PwshOnlyGateTest(unittest.TestCase):
    """Python 測試檔不得以「只認 pwsh」的條件決定守門要不要跑。"""

    def test_no_test_module_gates_on_pwsh_without_powershell_fallback(self) -> None:
        offenders: list[str] = []
        for rel in _scanned("*test_*.py"):
            if rel in _PWSH_ONLY_EXEMPT:
                continue
            tree = _parse_or_none(_REPO_ROOT / rel)
            if tree is None:  # 語法／編碼壞掉由別的閘門負責，本鎖不重複翻紅
                continue
            probed = _which_string_args(tree)
            if "pwsh" in probed and "powershell" not in probed:
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            f"偵測到「只認 pwsh、不認 powershell」的能力門檻：{offenders}\n"
            "Windows 11 出廠只有 Windows PowerShell 5.1（`powershell.exe`），pwsh 7 需另外安裝——"
            "這種條件會讓守門在它要保護的 Windows 平台上恆 skip，卻在裝了 pwsh 的 macOS 開發機"
            "上生效（DEF-101-507 實例）。修法：改用 "
            "`tools/tests/_platform_helpers.powershell_exe()`（Windows 上優先出廠 5.1，"
            "理由見該函式 docstring），或若該檔確實只該在非 Windows 平台跑，"
            f"則加入本檔 `_PWSH_ONLY_EXEMPT` 並附理由。",
        )

    def test_exemption_list_is_not_stale(self) -> None:
        """豁免名冊自檢：檔案須存在、理由須非空（判準實作見 `stale_problems`）。"""
        problems = (
            stale_problems(_PWSH_ONLY_EXEMPT, _REPO_ROOT)
            + stale_problems(_PS1_EXAMPLE_EXEMPT, _REPO_ROOT)
        )
        self.assertEqual(problems, [], f"豁免名冊已腐化：{problems}")

    def test_stale_detector_has_discrimination(self) -> None:
        """`stale_problems` 的鑑別力自驗（QA-R58R1-03）。

        為何需要：上面那支對現況名冊跑的斷言**目前不可能失敗**（`_PS1_EXAMPLE_EXEMPT`
        是空 dict、`_PWSH_ONLY_EXEMPT` 唯一一筆檔案存在且理由完整），零鑑別力的自檢
        分不出「名冊健康」與「檢查壞了」。名冊維持現狀，改用合成輸入證明三條路徑都活著。
        """
        missing = stale_problems({"tools/tests/no_such_file_at_all.py": "理由在"}, _REPO_ROOT)
        self.assertEqual(len(missing), 1, missing)
        self.assertIn("已不存在", missing[0])

        # 理由為純空白（不只空字串）也必須被抓到——空白是「看起來有寫」的偽裝形態。
        for blank in ("", "   \n\t "):
            with self.subTest(blank=repr(blank)):
                no_reason = stale_problems({"tools/tests/_platform_helpers.py": blank}, _REPO_ROOT)
                self.assertEqual(len(no_reason), 1, no_reason)
                self.assertIn("未附理由", no_reason[0])

        legit = stale_problems({"tools/tests/_platform_helpers.py": "SSOT 模組，確實存在"},
                               _REPO_ROOT)
        self.assertEqual(legit, [], f"合法條目不得誤報：{legit}")

        # R58 round 6 SD-R58R6 P3：`label` 參數（round 5 為保住表名前綴而加）原本**零測試
        # 覆蓋**——而它的用途正是讓「同一支測試驗多張表」時分得出哪張腐化。沒有覆蓋的參數
        # 就是下一次重構會被靜默改掉的參數，正是本模組自己譴責的「零鑑別力＝沒有」形態。
        for table in ("_EXEMPT", "_GROWTH_EXEMPT"):
            with self.subTest(label=table):
                labelled = stale_problems(
                    {"tools/tests/no_such_file_at_all.py": "理由在"}, _REPO_ROOT, table
                )
                self.assertEqual(len(labelled), 1, labelled)
                self.assertTrue(
                    labelled[0].startswith(f"{table} "),
                    f"`label` 前綴遺失，訊息無法分辨是哪張表：{labelled[0]!r}",
                )
        unlabelled = stale_problems({"tools/tests/no_such_file_at_all.py": "理由在"}, _REPO_ROOT)
        self.assertTrue(
            unlabelled[0].startswith("豁免項"),
            f"留空 label 時必須沿用單表呼叫端的既有訊息字面：{unlabelled[0]!r}",
        )

    def test_detector_catches_synthetic_pwsh_only_module(self) -> None:
        """偵測器自驗：合成一份 pwsh-only 條件式必須被判為 offender、有兜底的不得誤報。

        一支「掃全 repo 都沒發現問題」的測試若不自驗，無從分辨「乾淨」與「偵測器壞了」
        （本 repo 既有慣例，見 `test_python_c_percent_shim.py`）。
        """
        bad = ast.parse('import shutil\n@skipUnless(shutil.which("pwsh"), "x")\ndef f(): pass\n')
        good = ast.parse(
            'import shutil\n'
            'E = shutil.which("pwsh") or shutil.which("powershell")\n'
        )
        bad_args, good_args = _which_string_args(bad), _which_string_args(good)
        self.assertEqual(bad_args, {"pwsh"})
        self.assertTrue("pwsh" in bad_args and "powershell" not in bad_args)
        self.assertEqual(good_args, {"pwsh", "powershell"})
        self.assertFalse("pwsh" in good_args and "powershell" not in good_args)


def _code_string_constants(tree: ast.AST) -> list[str]:
    """檔內字串字面值，**排除 docstring**（模組／類別／函式的首個表達式）。

    排除 docstring 是必要的：本 repo 的掃描器慣例把「掃什麼、不掃什麼」寫進 docstring，
    那些散文必然提到 `git ls-files`／`--exclude-standard`；不排除會讓「寫了誠實劃界」
    這件事本身變成 offender（round 3 初版正是因此必須自我豁免）。
    """
    doc_ids: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if (
            isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            doc_ids.add(id(body[0].value))
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc_ids
    ]


_LS_FILES_TOKEN = "ls-files"
_UNION_FLAG_TOKENS = ("--others", "--exclude-standard")


def classify_scan_surface(tree: ast.AST) -> str | None:
    """`None`＝不提及 `ls-files`；`"union"`＝自寫聯集語意；`"tracked_only"`＝僅 tracked 列舉。"""
    strs = _code_string_constants(tree)
    if not any(_LS_FILES_TOKEN in s for s in strs):
        return None
    if any(flag in s for s in strs for flag in _UNION_FLAG_TOKENS):
        return "union"
    return "tracked_only"


class RepoScanSsotCallsiteLock(unittest.TestCase):
    """`_repo_scan.scanned()` 的呼叫端鎖（R58 round 3 ARCH-R58R3-01 立案、round 4 重設射程）。

    立案理由：round 2 新建掃描面 SSOT 時**沒有配呼叫端鎖**——而本 repo 已為此付過三次代價
    （R56 `_CI_TREE_RE` 抄三份、R57 註解剝除器抄兩份、R58 round 1 `powershell_exe()` 同輪 fork
    三份），判例文件明文寫著「**收斂與呼叫端鎖必須同一次落地**，否則是把 N 個弱鎖換成 1 個沒有
    強制力的弱鎖，嚴格更差」。本鎖補上那一半。

    ## 🔴 round 4 重設射程（QA-R58R4-01／ARCH-R58R4-02 導致的設計訂正）

    round 3 初版把射程定為「**不得自寫 `git ls-files`**」，述詞是單一硬編位元序列
    `git", "ls-files`。QA 實測證明它**只認一種拼法**：改單引號、或中間插 `-C`（被 100 字元
    行寬逼著換行時最自然的寫法）就完全隱形，樹內當時已有 3 支活的漏網——即「N 個弱鎖換成
    1 個沒有強制力的弱鎖」在本鎖自己身上成真。

    我據此把述詞改成引號無關後**重跑普查，浮出的不是 3 支而是 22 支**。逐支檢視後發現真正的錯
    不在述詞、**在射程**：那 22 支絕大多數是**刻意的 tracked-only 獨立列舉**（各有自己的
    pathspec／`core.quotePath` 設定／用途），把它們逼進 `scanned()` 會**靜默改掉語意**
    （憑空多出未追蹤檔）——那是製造缺陷，不是收斂。R56/R57/R58r1 那三次真正的病灶形態是
    **同一個行為被 fork 成多份複本**；對照本 repo 判例的第二層分診問句「這 N 份複本是否觀測
    同一個對象？」——tracked-only 列舉與 `scanned()` **觀測對象不同**，複本數本身即有鑑別力。

    故射程改為：**不得手工重寫 `scanned()` 的「聯集」語意**（tracked ∪ untracked-but-not-ignored）。
    實測全樹僅 1 支具此語意（SSOT 本體）⇒ offender 0，且該 0 **不是靠 22 筆例外湊出來的**。

    連帶訂正 **ARCH-R58R4-02**：round 3 曾以「既有掃描器（非本輪新增）」為由放行
    `tools/check_defect_log_crossref.py` 與其測試，而實測 `git show HEAD:` 兩者皆 **0** 處
    ——那是**本輪新寫的**，理由是假事實。新射程下兩者屬 tracked-only ⇒ 本來就在射程外，
    例外與假理由一併消失；round 3 記在該例外欄的「R59 正解＝把 `scanned()` 搬到 `tools/` 層」
    亦是**錯方向**（真照著改成聯集，會讓未追蹤的暫存筆記變成無人負責的假紅），已刪除。

    ## 掃描面（三段式）

    **已實測涵蓋**：`*test_*.py` ∪ `tools/*.py` 內，**非 docstring** 的字串字面值同時出現
    `ls-files` 與聯集旗標（`--others`／`--exclude-standard`）者。取 **per-file 粒度**而非
    per-call：SSOT 自己就寫成 `["git", ..., *extra, pattern]` 搭配另一處的 `extra`，更嚴的
    per-call 粒度**連立案樣本都抓不到**＝失去真實語料校準（同 `test_behavioural_lock_required`
    選同檔粒度的理由）。

    **為什麼縮射程動不到提交閘門（round 5 Architect 指出這是本設計最強的一段辯護、而它原本
    缺席）**：`git ls-files` 列的是 **index** 而非 HEAD，故「tracked-only」≡ 提交閘門所見的面
    ——**已 `git add` 的新檔本來就在裡面**。`scanned()` 相對它只多出「從未 `git add` 的本機檔」；
    對 golden／parity 這類產出共用工件的掃描器，納入那些檔正是要避免的（把機器本地狀態烤進
    共用產物）。所以縮射程只讓「本機還沒 add 的檔」在本機先跑時較不積極，pre-commit／CI 面
    分毫未減。

    **已實測不涵蓋**（誠實劃界）：
      1. 以 `str.join`／`+` 併接組成子命令字面者（本鎖只看字串字面值，不做資料流分析）。
         **注意方向**：把旗標存進**變數**（`LS = "ls-files"`）**仍會**被抓到——本鎖是 per-file
         看全檔字面值，故 round 5 SD 實測指出原文把「變數」列為不涵蓋屬保守低估，已改正。
      2. **以別的指令達成同一個聯集語意**者（round 5 Architect 實測舉例：`git status
         --porcelain --untracked-files=all` 併 `ls-files` → 本鎖判 `tracked_only`）。
         此形態落在**宣告射程內、述詞外**，是本鎖目前最實際的殘口，故具名而非只靠句末總括。
      3. `.sh`／`.ps1`／`.yml` 內的 `git ls-files`（shell 腳本自己的列舉，不共用 Python 掃描面）。
      4. **tracked-only 列舉**——刻意在射程外，但**不是盲區**：母體以 `_TRACKED_ONLY_CENSUS`
         釘住，多一支或少一支都翻紅並具名，迫使當事人明確回答「你要的是 tracked-only 還是
         聯集」。**但「母體」限上述兩個 glob 面內**（round 5 三方各自指出這句易被讀成全樹）：
         面外已知的活體 tracked-only 站點為 `AISDLC_SDD/scripts/sdd_version.py`，它不受本釘定
         約束；R59 若要擴面，代價是要把 `AutoClaude/tools/*.py` 等一併納入普查。

    **未窮舉**：不宣稱除此之外無盲區。
    """

    # 允許自寫聯集語意者（須附理由；stale 自檢：檔案不存在或理由空即紅）。
    _UNION_EXEMPT = {
        "tools/tests/_repo_scan.py": "SSOT 本體，聯集語意的唯一合法出處。",
        "tools/tests/test_platform_guard_availability.py": (
            "本鎖自身：偵測器**必須**在程式碼裡具名 `ls-files` 與兩個聯集旗標才能偵測，"
            "故對自己的述詞恆為真。這是偵測器自我豁免的標準形態，代價由下方 "
            "`UnionSemanticsDetectorSelfTest` 的合成樣本紅綠對照補回。"
        ),
    }

    # tracked-only 列舉母體（射程外，但**不得靜默成長**）。R58 round 4 QA-R58R4-01 實測釘定。
    # 為什麼只釘集合、不逐支寫理由：這些支的共同理由是同一句——「tracked-only 是刻意的，
    # 各自有自己的 pathspec／quotePath／用途，語意與 `scanned()` 不同」（完整論證見類別
    # docstring〈round 4 重設射程〉）。逐支複寫同一句只會長成無人維護的大清單，正是本檔
    # `_EXIT_CODE_CONTRACT_TARGETS` 慣例所警告的形態；反之**釘住集合**讓「多一支」與
    # 「少一支」都翻紅且具名，鑑別力就在這裡。
    _TRACKED_ONLY_CENSUS = frozenset({
        "AISDLC_SDD/scripts/tests/test_ci_paths_cover_root_consumers.py",
        "AISDLC_SDD/scripts/tests/test_copy_on_evolve.py",
        "AISDLC_SDD/scripts/tests/test_ntfs_length_gate.py",
        "tools/check_defect_log_crossref.py",
        "tools/check_gha_action_versions.py",
        "tools/check_ntfs_paths.py",
        "tools/gen_ps_comment_golden.py",
        "tools/tests/test_bash32_compat.py",
        "tools/tests/test_check_defect_log_crossref.py",
        "tools/tests/test_extras_quoting_zsh_safety.py",
        "tools/tests/test_find_git_bash_parity.py",
        "tools/tests/test_gha_action_versions.py",
        "tools/tests/test_platform_utils_dedup.py",
        "tools/tests/test_ps1_bom.py",
        "tools/tests/test_ps51_compat.py",
        "tools/tests/test_ps_comment_golden.py",
        "tools/tests/test_root_infra_parity.py",
        "tools/tests/test_smoke_ci_sync.py",
        "tools/tests/test_windows_forbidden_filename_parity.py",
        "tools/tests/test_windowsapps_guard_bash_parity.py",
        "tools/tests/test_windowsapps_guard_cross_consistency.py",
    })

    def _classify_all(self, files: list[str] | None = None) -> dict[str, list[str]]:
        """分類掃描面內每一支檔案。`files` 只給測試餵合成清單用（預設走真實掃描面）。"""
        rels = files if files is not None else sorted(
            {r for pattern in ("*test_*.py", "tools/*.py") for r in _scanned(pattern)}
        )
        buckets: dict[str, list[str]] = {"union": [], "tracked_only": []}
        for rel in rels:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    tree = ast.parse((_REPO_ROOT / rel).read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue  # 語法／編碼問題由別的閘門負責，本鎖不重複翻紅
            except (FileNotFoundError, IsADirectoryError, PermissionError):
                # R58 round 5 SA-R58R5-02：`scanned()` **刻意**含未追蹤檔，而 `git ls-files`
                # 也會列「index 有、工作樹已刪」者；兩種狀態下無條件 read_text() 會讓本鎖以
                # **無說明的 traceback** 收場，而不是印出它自己設計的具名診斷（「你要的是
                # tracked-only 還是聯集？」）。**複審期間真的發生過**：另一位並行複審者的
                # 探針在列舉後、讀取前被刪除，整個根層全套變成 `FAILED (errors=1)`。
                # 慣例早由姊妹掃描器立案：`test_check_defect_log_crossref.TestScanReverseRefs
                # ::test_missing_file_on_disk_skipped_without_crash`（「git index 有、磁碟沒有
                # → 略過不崩、不誤紅」）——本鎖 round 4 落地時只補了「登記表→檔案存在」的
                # 單向防護，量測側漏補，兩張表政策再次不對稱。
                continue
            kind = classify_scan_surface(tree)
            if kind:
                buckets[kind].append(rel)
        return {k: sorted(set(v)) for k, v in buckets.items()}

    def test_no_module_hand_rolls_the_union_semantics(self) -> None:
        buckets = self._classify_all()
        # R58 round 6 QA-R58R6 P3-2：**本鎖的綠原本沒有自證性**。偵測器一旦失明（述詞失效、
        # 掃描面塌空），offenders 恆為空 ⇒ 空真通過，而 QA 在複審期間真的觀測到那個視窗：
        # 同一次 run 內 `test_tracked_only_census_is_exact` 翻紅（母體塌成空）而本鎖是綠的。
        # 兜底原本只靠姊妹測試翻紅，兩者的耦合未載明。加兩條前置斷言讓本鎖自己也翻紅。
        self.assertTrue(
            buckets["union"] or buckets["tracked_only"],
            "掃描面塌空——本鎖的綠燈無意義（偵測器或 `scanned()` 已失效），非「樹內乾淨」",
        )
        self.assertIn(
            "tools/tests/_repo_scan.py", buckets["union"],
            "回源錨①：SSOT 本體必須仍被判為 union。它若不在 union 桶，代表述詞已失效"
            "（**或 SSOT 已改名／搬移**——此時同類別的 "
            "`test_union_exemption_registry_is_not_stale` 會同時指名真因），"
            "此時 offenders 為空是**假綠**而非乾淨",
        )
        # R58 round 7 QA-R58R7 P3 #3：錨① 只擋**全盲**。QA 實測「選擇性失明」可穿過——
        # 把述詞改成「只認得含 `def scanned(` 的檔」時 union 桶仍只有 SSOT 那一支、兩條前置
        # 斷言都過、本鎖照樣綠。原因是錨① 挑的偏偏是「述詞退化後最可能仍命中的那一支」。
        # 故加反向錨：一個已知的 tracked-only 成員必須落在**另一個**桶，單向失明即翻紅。
        self.assertIn(
            "tools/check_ntfs_paths.py", buckets["tracked_only"],
            "回源錨②（反向）：已知的 tracked-only 成員必須落在 tracked_only 桶。它若消失，"
            "代表述詞只剩單向鑑別力（選擇性失明），此時本鎖的綠同樣是假綠",
        )
        offenders = [rel for rel in buckets["union"] if rel not in self._UNION_EXEMPT]
        self.assertEqual(
            offenders, [],
            f"下列檔案手工重寫了 `scanned()` 的**聯集**語意（tracked ∪ untracked-but-not-ignored）："
            f"{offenders}\n"
            "請改用 `from _repo_scan import scanned`——本 repo 已為「同一行為 fork 成多份」付過"
            "三次代價（R56 抄三份／R57 抄兩份／R58 round 1 同輪 fork 三份）。\n"
            "若你真正需要的是 **tracked-only** 列舉（多數情況如此），請移除聯集旗標並把檔案"
            "加入 `_TRACKED_ONLY_CENSUS`；確有理由自持聯集者，加入 `_UNION_EXEMPT` 並寫明理由。",
        )

    def test_tracked_only_census_is_exact(self) -> None:
        """tracked-only 母體必須與釘定集合逐支相符（雙向）。

        這條是 round 4 的核心訂正：round 3 的普查述詞只認一種拼法，於是「22 支」這個母體
        對守門器完全隱形，而記錄裡卻寫成「抓到 6 支既有站點、已逐一登記」＝把不完整普查
        記成完整。釘住集合後，母體變成**可見且必須被維護**的事實。
        """
        self.maxDiff = None  # 母體有 20+ 支，截斷的 diff 等於沒有訊息
        measured = frozenset(self._classify_all()["tracked_only"])
        added = sorted(measured - self._TRACKED_ONLY_CENSUS)
        removed = sorted(self._TRACKED_ONLY_CENSUS - measured)
        self.assertEqual(
            (added, removed), ([], []),
            "tracked-only 列舉母體已變動——這是**要你做一個決定**，不是叫你直接改數字：\n"
            f"  新增（未登記）：{added}\n"
            f"  消失（登記卻已無）：{removed}\n"
            "新增者請先回答「你要的是 tracked-only 還是 `scanned()` 的聯集？」——若是聯集，"
            "改用 `from _repo_scan import scanned`；若刻意 tracked-only（例如像 golden fixture "
            "那樣產出**被提交、由所有人共用**的產物，掃描面納入本機未追蹤檔會把機器本地狀態"
            "烤進共用工件），才把它加入 `_TRACKED_ONLY_CENSUS`。\n"
            "消失者請確認是改走 SSOT（正常，移除登記）還是掃描面被誤刪。",
        )

    def test_union_exemption_registry_is_not_stale(self) -> None:
        self.assertEqual(
            stale_problems(self._UNION_EXEMPT, _REPO_ROOT), [],
            "`_UNION_EXEMPT` 名冊已腐化（檔案不存在或理由為空）",
        )

    def test_vanished_file_is_skipped_without_crash(self) -> None:
        """列舉後、讀取前檔案消失 → 略過不崩，且不被誤列入任何桶（round 5 SA-R58R5-02）。

        `scanned()` 刻意含未追蹤檔，故「列舉時在、讀取時不在」在本 repo 的多 agent 同樹
        工作流下是**正常狀態**而非異常——round 5 複審期間已真實發生一次，使全套變成
        `FAILED (errors=1)`。寫法與姊妹掃描器的
        `test_check_defect_log_crossref::test_missing_file_on_disk_skipped_without_crash` 對齊。
        """
        ghost = "tools/tests/test_r58r5_path_that_never_exists.py"
        self.assertFalse((_REPO_ROOT / ghost).exists(), "前置條件：該路徑必須不存在")
        buckets = self._classify_all([ghost, "tools/tests/_repo_scan.py"])
        self.assertEqual(buckets["union"], ["tools/tests/_repo_scan.py"],
                         "消失的檔案不得影響其餘檔案的分類")
        self.assertNotIn(ghost, buckets["tracked_only"])
        self.assertNotIn(ghost, buckets["union"])

    def test_census_entries_all_exist(self) -> None:
        """反方向腐化：登記在母體裡的檔案必須存在（ARCH-R58R4 P3 ②「兩張表政策不一致」）。"""
        missing = sorted(
            rel for rel in self._TRACKED_ONLY_CENSUS if not (_REPO_ROOT / rel).is_file()
        )
        self.assertEqual(missing, [], f"`_TRACKED_ONLY_CENSUS` 登記了不存在的檔案：{missing}")


class UnionSemanticsDetectorSelfTest(unittest.TestCase):
    """偵測器自驗：合成樣本必須被正確分類（本 repo 慣例——「掃全樹都乾淨」若不自驗，
    無從分辨「真乾淨」與「偵測器壞了」）。"""

    _UNION = (
        "import subprocess\n"
        "def f(p):\n"
        '    a = subprocess.run(["git", "ls-files", p])\n'
        '    b = subprocess.run(["git", "ls-files", "--others", "--exclude-standard", p])\n'
    )
    _TRACKED_ONLY = (
        "import subprocess\n"
        "def f(p):\n"
        '    return subprocess.run(["git", "-C", "/r", "ls-files", "-z", p])\n'
    )
    _SPLIT_UNION = (  # 旗標拆到另一處變數——per-file 粒度必須仍抓到（SSOT 本體即此形狀）
        "import subprocess\n"
        'EXTRA = ["--others", "--exclude-standard"]\n'
        "def f(p, extra):\n"
        '    return subprocess.run(["git", "ls-files", *extra, p])\n'
    )
    _PROSE_ONLY = (  # docstring 提及不得誤判（否則「寫了誠實劃界」就變 offender）
        '"""掃描面 ＝ git ls-files ∪ git ls-files --others --exclude-standard。"""\n'
        "def f():\n"
        "    return 1\n"
    )

    def test_union_is_flagged(self) -> None:
        self.assertEqual(classify_scan_surface(ast.parse(self._UNION)), "union")

    def test_split_flags_still_flagged_per_file(self) -> None:
        self.assertEqual(classify_scan_surface(ast.parse(self._SPLIT_UNION)), "union")

    def test_tracked_only_is_not_union(self) -> None:
        self.assertEqual(classify_scan_surface(ast.parse(self._TRACKED_ONLY)), "tracked_only")

    def test_docstring_prose_is_not_a_callsite(self) -> None:
        self.assertIsNone(classify_scan_surface(ast.parse(self._PROSE_ONLY)))

    def test_unrelated_module_is_none(self) -> None:
        self.assertIsNone(classify_scan_surface(ast.parse("x = 1\n")))


class CapabilityProvenanceRegistryTest(unittest.TestCase):
    """任何被 `which()` 探測的能力，都必須先在 `_CAPABILITY_PROVENANCE` 登記出處。

    這是把 DEF-101-507 從「pwsh 這一個名字的缺陷」提升為「能力門檻這個類別的判準」：
    登記的動作強迫作者回答「目標平台出廠有沒有」——那個他原本沒問、於是寫出單邊守門的問題。
    """

    def _probed_names(self) -> dict[str, list[str]]:
        found: dict[str, list[str]] = {}
        for rel in _scanned("*test_*.py"):
            tree = _parse_or_none(_REPO_ROOT / rel)
            if tree is None:
                continue
            for name in _which_string_args(tree):
                found.setdefault(name, []).append(rel)
        return found

    def test_every_probed_capability_is_registered(self) -> None:
        probed = self._probed_names()
        missing = {k: v for k, v in probed.items() if k not in _CAPABILITY_PROVENANCE}
        self.assertEqual(
            missing, {},
            "下列能力名稱被 `which()` 探測卻未在 `_CAPABILITY_PROVENANCE` 登記出處："
            f"{ {k: v for k, v in missing.items()} }\n"
            "請在 `tools/tests/test_platform_guard_availability.py` 的 `_CAPABILITY_PROVENANCE` "
            "補一筆，寫明**哪些平台出廠即有、哪些需要另裝**。這一步不是形式主義——"
            "DEF-101-507 的病灶正是作者以自己開發機的組態當參照系（『我機器有 pwsh』），"
            "而沒問『目標平台出廠有沒有』。登記的動作就是強迫回答那個問題。",
        )

    def test_registry_has_no_stale_entries(self) -> None:
        """登記表不得腐化：登記了卻已無人探測的名稱要移除（否則表會變成無人維護的死清單）。"""
        probed = set(self._probed_names())
        stale = sorted(set(_CAPABILITY_PROVENANCE) - probed)
        self.assertEqual(
            stale, [],
            f"下列能力已無任何測試檔探測，登記表條目應移除：{stale}"
            "（保留無效條目會讓這張表逐輪腐化成沒人敢動的死清單——本 repo 已在 MIN_TESTS "
            "與歸檔索引上各付過一次這種代價）",
        )

    def test_registry_entries_are_non_empty(self) -> None:
        empty = empty_reason_keys(_CAPABILITY_PROVENANCE)
        self.assertEqual(empty, [], f"登記表條目說明為空：{empty}")
        # 鑑別力自驗：現況登記表說明全部非空 → 上一句恆綠。用合成輸入證明判準本身活著
        # （同 `test_stale_detector_has_discrimination` 的理由，QA-R58R1-03）。
        self.assertEqual(
            empty_reason_keys({"a": "", "b": " \n\t", "c": "有寫理由"}), ["a", "b"]
        )


class Ps1UsageExampleTest(unittest.TestCase):
    """active `.ps1` 的用法示範不得只給 pwsh 寫法（使用者照抄必失敗）。"""

    def test_active_ps1_usage_examples_offer_powershell(self) -> None:
        offenders: list[str] = []
        for rel in _scanned("*.ps1"):
            # 凍結版 AISDLC_SDD_v0.NN 依 Copy-on-Evolve 紀律不回改 → 排除；LATEST 亦為凍結
            # 快照（其內容由框架版本治理側決定），故整個 AISDLC_SDD_v* 前綴一律不納入。
            if "/AISDLC_SDD_v" in rel or rel in _PS1_EXAMPLE_EXEMPT:
                continue
            text = (_REPO_ROOT / rel).read_bytes().decode("utf-8-sig")
            if _PWSH_EXAMPLE_RE.search(text) and "powershell" not in text.lower():
                offenders.append(rel)
        self.assertEqual(
            offenders, [],
            f"下列 active .ps1 的用法示範只給了 pwsh 寫法：{offenders}\n"
            "Windows 11 出廠沒有 pwsh，使用者照抄會拿到「找不到 pwsh」這個與腳本本身無關的"
            "怪錯（DEF-101-508 實例；與 R57 DEF-101-479 的 zsh glob 同類——印給使用者照抄的"
            "指令本身就是缺陷面）。修法：改用 repo 通用慣例 "
            "`powershell -NoProfile -ExecutionPolicy Bypass -File <script>.ps1`，"
            "需要時再補一句「裝有 PowerShell 7 者用 pwsh 亦可」。",
        )

    def test_detector_catches_synthetic_pwsh_only_example(self) -> None:
        """偵測器自驗：樣式要抓得到示範行、且不得把「純提及 pwsh」誤判為示範。"""
        self.assertTrue(_PWSH_EXAMPLE_RE.search("# 用法： pwsh scripts/ci-gate.ps1 --full-tlc"))
        self.assertTrue(_PWSH_EXAMPLE_RE.search("#   PWSH tools\\foo.ps1"))
        self.assertIsNone(_PWSH_EXAMPLE_RE.search("# 裝有 pwsh 7 者亦可"))
        self.assertIsNone(_PWSH_EXAMPLE_RE.search("# pwsh 與 powershell 皆可"))


class PowerShellExeSsotCallsiteLock(unittest.TestCase):
    """`_platform_helpers.powershell_exe()` 的 SSOT 呼叫端鎖（ARCH-R58R1-03）。

    **為何非有不可**：R58 把 `powershell_exe()` 立為 SSOT 的**同一輪內**，同一段選擇邏輯就
    fork 成三份且行為已經分歧——`tools/gen_ps_comment_golden.py` 逐字複製 order tuple、
    `AutoClaude/tests/tools/test_reschedule_g0_gatecheck_static.py` 改用
    `platform.system()` 判斷且非 Windows 分支不兜底 `powershell`。而同輪的
    `_CAPABILITY_PROVENANCE['pwsh']` 卻寫著「一律走 powershell_exe()」，政策自相矛盾。
    這是 R57 SA-R57R2-03（註解剝除器抄兩份）、R56（`_CI_TREE_RE` 抄三份）之後的**第三次**
    同型復發，三次的共同點都是「SSOT 沒有呼叫端鎖 ＝ 沒有強制力」。

    **掃描面**：`*test_*.py`（全 repo）**∪** `tools/*.py`。擴到 `tools/*.py` 是本鎖的關鍵——
    `gen_ps_comment_golden.py` 檔名不含 `test_`，在舊掃描面完全在面外，而它是 golden 的
    產生器，引擎選錯會直接污染 ground truth。掃描面同時含未追蹤檔（見 `_scanned`）。

    **已實測涵蓋**（三組注入實驗，每次只翻紅一支測試，還原後以 md5 核對）：把 order tuple
    抄回 `gen_ps_comment_golden.py`、把 SSOT import 換成自寫 `which("pwsh") or
    which("powershell")`、把 import 留著但不呼叫（死 import）。
    **已實測不涵蓋**：測試檔內既有的手寫 `which("powershell") or which("pwsh")` 偏好鏈族群
    ——本鎖的 (b) 只覆蓋 `tools/` 下非測試檔，測試檔族群屬既有債（見
    `_CAPABILITY_PROVENANCE['pwsh']` 的〈收斂現況〉，未在本包收斂）；`AutoClaude/tools/`
    亦在面外。**未窮舉**：換名重寫等價邏輯、以變數／設定檔間接傳入名字、`exec`／動態
    import 迂迴——與 `_ci_scan_anchors` 呼叫端鎖量到的同類逃逸面一致，不做全備宣稱。
    """

    _SSOT_FILENAME = f"{_PS_EXE_SSOT_MODULE}.py"
    # R58 round 2 ARCH-R58R2-02：豁免改用**相對路徑**比對。原以 basename 比對，
    # 任何路徑下叫 `_platform_helpers.py` 的檔案都會被豁免（現況全 repo 僅一支、
    # 暫無曝險，但那是巧合不是保證）。同一個字面另有 `test_ssot_module_is_in_the_scan_surface`
    # 在用，故收斂成單一常數。
    _SSOT_REL = f"tools/tests/{_PS_EXE_SSOT_MODULE}.py"

    def _lock_surface(self) -> list[str]:
        return sorted(set(_scanned("*test_*.py")) | set(_scanned("tools/*.py")))

    def test_no_module_hand_rolls_the_platform_order_tuple(self) -> None:
        offenders: list[str] = []
        for rel in self._lock_surface():
            path = _REPO_ROOT / rel
            # R58 round 3 ARCH-R58R3-02：本處原亦為 basename 比對（round 2 只改了另一處，
            # 註解卻讀起來像已全面改掉）。order tuple 的唯一合法出處就是那一支相對路徑。
            if rel == self._SSOT_REL:
                continue  # SSOT 本身當然要有那個 tuple
            tree = _parse_or_none(path)
            if tree is None:
                continue
            offenders += [f"{rel}:{line}" for line in platform_order_sequences(tree)]
        self.assertEqual(
            offenders, [],
            f"偵測到自帶的 PowerShell 偏好順序序列（SSOT fork）：{offenders}\n"
            f"唯一實作應在 {self._SSOT_FILENAME} 的 {_PS_EXE_SSOT_SYMBOL}()，請改為 import。"
            "複本無法互為交叉校驗，只會把同一個盲點抄 N 遍（R56 抄三份、R57 抄兩份、"
            "R58 SSOT 成立當輪就抄三份，都是同一個病灶）。需要 raise 的呼叫端請自己包 "
            "`if exe is None: raise`，不要為此複製選擇邏輯。",
        )

    def test_no_tool_script_hand_rolls_a_powershell_preference_chain(self) -> None:
        """`tools/` 下的**非測試**工具腳本不得自行以 `which()` 串偏好鏈。

        為何把這一條的面收在「非測試檔」：工具腳本選錯引擎的後果會**固化成產物**
        （golden fixture 的 ground truth、安裝器實際寫入的排程），錯誤會離開這次執行、
        被後續所有離線比對當成真；測試檔選錯引擎最壞只是這支測試本身失去鑑別力。
        測試檔內既有族群屬既有債，見類 docstring〈已實測不涵蓋〉。
        """
        offenders: list[str] = []
        for rel in _scanned("tools/*.py"):
            path = _REPO_ROOT / rel
            # R58 round 2 ARCH-R58R2-02：原判準是 `"test_" in path.name` 子字串，
            # 把生產守門工具 `tools/check_pytest_baseline_sites.py`（檔名恰含 `test_`）
            # 誤判成測試檔而靜默豁免——被誤放行的偏偏是一支會被 CI 與 pre-commit 呼叫的
            # 工具，而本鎖立案的核心論證正是「工具腳本選錯引擎會固化成產物」。
            # 改為路徑式分類（是否位於 tools/tests/），並把 SSOT 豁免改為比對相對路徑
            # （原為 basename，任何路徑下同名檔都會被豁免）。
            if rel == self._SSOT_REL or rel.startswith("tools/tests/"):
                continue
            tree = _parse_or_none(path)
            if tree is None:
                continue
            offenders += [f"{rel}:{line}" for line in powershell_which_chains(tree)]
        self.assertEqual(
            offenders, [],
            f"工具腳本自行串出 PowerShell 偏好鏈：{offenders}\n"
            f"請改用 `{_PS_EXE_SSOT_MODULE}.{_PS_EXE_SSOT_SYMBOL}()`——手寫鏈的常見錯法是"
            "在 Windows 上把 pwsh 排前面，那會用 7 去 parse 只有 7 接受的語法而在使用者的"
            "5.1 上炸掉（方向是 fail-open，理由見 SSOT 的 docstring）。",
        )

    def test_known_consumers_import_and_actually_call_the_ssot(self) -> None:
        """已知消費端必須真的 import **且**真的呼叫：只 import 不呼叫＝死 import，鎖零訊號。"""
        for rel in _PS_EXE_CONSUMERS:
            with self.subTest(consumer=rel):
                path = _REPO_ROOT / rel
                self.assertTrue(path.is_file(), f"消費端名冊已過期：{rel} 不存在")
                tree = _parse_or_none(path)
                self.assertIsNotNone(tree, f"{rel} 無法 parse，本鎖無從驗證")
                assert tree is not None  # for type narrowing
                imported = {
                    alias.asname or alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ImportFrom)
                    and node.module == _PS_EXE_SSOT_MODULE
                    for alias in node.names
                    if alias.name == _PS_EXE_SSOT_SYMBOL
                }
                self.assertTrue(
                    imported,
                    f"{rel} 未從 {_PS_EXE_SSOT_MODULE} import {_PS_EXE_SSOT_SYMBOL}——"
                    "它需要 PowerShell 能力，卻沒有走 SSOT（很可能又自帶了一份）",
                )
                called = {
                    node.func.id for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                }
                self.assertTrue(
                    imported & called,
                    f"{rel} 只 import 未呼叫 {sorted(imported)}——死 import 讓本鎖零訊號",
                )

    def test_ssot_module_is_in_the_scan_surface(self) -> None:
        """SSOT 檔本身必須落在掃描面內。

        否則「豁免 SSOT 檔名」這件事就毫無意義（豁免一個從來沒被掃到的檔案），而某天 SSOT
        被搬到掃描面外時，上面兩支鎖會安靜地失去對它的一致性參照，沒有任何訊號。
        """
        surface = self._lock_surface()
        self.assertIn(
            self._SSOT_REL, surface,
            f"SSOT 檔不在掃描面內（面大小 {len(surface)}）——鎖已失去參照點",
        )

    def test_detector_catches_synthetic_forks(self) -> None:
        """偵測器自驗：合成 fork 必須被抓、合法寫法不得誤報。

        一支「掃全 repo 都沒發現問題」的測試若不自驗，無從分辨「乾淨」與「偵測器壞了」。
        """
        forked = ast.parse(
            'order = ("powershell", "pwsh") if win else ("pwsh", "powershell")\n'
        )
        self.assertEqual(platform_order_sequences(forked), [1])
        self.assertEqual(
            platform_order_sequences(ast.parse('order = ["pwsh", "powershell"]\n')), [1]
        )
        # set 沒有順序 → 不是 order tuple，不得誤報（本檔自己的斷言即此形態）
        self.assertEqual(
            platform_order_sequences(ast.parse('x = {"pwsh", "powershell"}\n')), []
        )
        # 只列其中一個名字不算 fork
        self.assertEqual(platform_order_sequences(ast.parse('order = ("pwsh",)\n')), [])
        self.assertEqual(
            platform_order_sequences(
                ast.parse(
                    f"from {_PS_EXE_SSOT_MODULE} import {_PS_EXE_SSOT_SYMBOL}\n"
                    f"exe = {_PS_EXE_SSOT_SYMBOL}()\n"
                )
            ),
            [],
        )

        chain = ast.parse('exe = shutil.which("pwsh") or shutil.which("powershell")\n')
        self.assertEqual(powershell_which_chains(chain), [1])
        self.assertEqual(
            powershell_which_chains(
                ast.parse('exe = shutil.which("powershell") or shutil.which("pwsh")\n')
            ),
            [1],
        )
        # 單名探測不是偏好鏈（歸 PwshOnlyGateTest 管），且 `and` 鏈不是偏好鏈
        self.assertEqual(
            powershell_which_chains(ast.parse('exe = shutil.which("pwsh")\n')), []
        )
        self.assertEqual(
            powershell_which_chains(
                ast.parse('ok = shutil.which("pwsh") and shutil.which("powershell")\n')
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
