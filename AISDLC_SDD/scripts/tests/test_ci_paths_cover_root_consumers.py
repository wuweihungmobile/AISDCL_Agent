"""CI paths 覆蓋根層消費檔 meta contract — DEF-101-042 治本鎖 / DEF-101-068(a) 擴充（S6）.

WHY（Rule 9 / Rule 12 fail-loud）：測試目錄的 contract test 消費 monorepo
根層檔案時，其 CI 載體的 paths 過濾必須包含該根層檔，否則「只改根層消費檔」的
變更下回歸鎖恰好不跑（假綠盲區）。此同構缺陷已三度出現於 aisdlc-sdd-ci
（DEF-101-037 → DEF-101-042 → 複審抓 sdd_hook_router.py 殘漏），人工盤點 paths
已被實證不可靠——本鎖把「paths 與消費點同步」升級為機械斷言，永久終結打地鼠：
未來任何測試新增根層消費點而漏補 paths，本測試即紅。

S6（第六輪複審 DEF-101-068(a)）：先前本鎖只讀 aisdlc-sdd-ci.yml 一份、只掃
AISDLC_SDD/scripts/tests/ 一個目錄，對 windows-compat-ci.yml／macos-compat-ci.yml
與其實際執行的 tools/tests/ 完全零機械保護——這正是先前一輪 windows-compat-ci.yml
漏補 tools/check_ntfs_paths.py 能夠逃過檢測的結構性根因。現擴充為「workflow ↔
其實際執行的測試目錄」對照表，逐一參數化驗證：

  - aisdlc-sdd-ci.yml      ↔ AISDLC_SDD/scripts/tests/（`python -m pytest scripts/tests/`）
  - windows-compat-ci.yml  ↔ tools/tests/（`unittest discover -s tools/tests`）
  - macos-compat-ci.yml    ↔ tools/tests/（`unittest discover -s tools/tests`）

做法：正則掃描對應目錄所有 test_*.py 源碼的根層消費慣用法——
  ``os.path.join(_monorepo_root(), "a", "b")`` / ``_monorepo_root() / "a" / "b"``
（AISDLC_SDD/scripts/tests/ 慣用法）與
  ``os.path.join(REPO_ROOT, "a", "b")`` / ``REPO_ROOT / "a" / "b"``
（tools/tests/ 慣用法，該目錄下 ``REPO_ROOT = Path(__file__).resolve().parents[2]``
剛好等於 monorepo 根）——重組 repo 相對路徑；凡指向磁碟上存在且不在 AISDLC_SDD/
下（該前綴由 "AISDLC_SDD/**" 天然覆蓋）的檔案，斷言被對應 workflow 的
push＋pull_request paths 覆蓋（fnmatch glob 語意）。另附兩道防呆：push/PR
清單對稱鎖（防單側漏補，三份 workflow 皆驗）、已知消費檔必被掃出（防正則退化
令本鎖形同虛設）。

S26（第八輪複審 R6，Architect 親自實測 fnmatch 逐一比對抓到）：`_scan_dir_for_root_paths()`
先前只認得 `os.path.join(REPO_ROOT, "a", "b")` / `REPO_ROOT / "a" / "b"` 這種「引用固定
路徑字串」的慣用法，完全沒有涵蓋 `tools/tests/` 三支新測試檔
（test_check_hooks_liveness.py／test_check_defect_log_crossref.py／
test_check_wrapper_thinness.py）皆使用的 `import check_hooks_liveness as m`（搭配
`sys.path.insert(0, str(Path(__file__).resolve().parents[1]))` 把待測目錄的父目錄
塞進 sys.path）這種「直接 import 根層同儕模組」慣用法——導致
windows-compat-ci.yml／macos-compat-ci.yml 皆漏收 tools/check_hooks_liveness.py／
check_defect_log_crossref.py／check_wrapper_thinness.py／_stdio_utf8.py 四支模組
（後者透過前三者遞移 import 被消費）卻毫無機械訊號。新增 `_scan_import_consumed_paths()`：
以 BFS 從 `directory` 內的 test_*.py 出發，掃描其 `import <module>`／
`import <module> as <alias>` 頂層陳述式，將 `module` 解析為「該來源檔自身所在目錄」
下的 `<module>.py`（對齊本 repo `sys.path.insert(0, parents[1])` 慣例），並對新發現的
根層 .py 檔遞迴重複同一掃描（fixed point，關閉「測試只 import A，A 內部又 import B」
的第二層盲區，如 check_hooks_liveness.py → _stdio_utf8.py）。與既有
`os.path.join`/`REPO_ROOT /` 正則並行執行、聯集後再套用磁碟存在性過濾器，兩種偵測
機制互不排斥。

R50（第 50 輪 Mac/Windows 相容性四方複審）：`tools/tests/test_windowsapps_guard_cross_consistency.py`
用 `_tracked_files(pattern)`（`git ls-files -- pattern`）對整個 repo 做 glob 動態掃描
（例：`_tracked_files("*.ps1")` 取得「當下全部 git 追蹤的 .ps1 檔」），而非引用某個
固定路徑字面值或 import 陳述式——這是與盲區 A（`_scan_dir_for_root_paths()`／
`_scan_import_consumed_paths()` 解析器猜測範圍不夠）、盲區 B（`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`
登記的執行期子行程消費）並列的第三種消費形態（盲區 C），且先前無任何機械訊號涵蓋
——連盲區 B 那種手動登記清單兜底都沒有，四方複審實測 10/10 全綠卻未攔下該檔案
新增 6 支 .ps1 消費檔（呼叫 python 未經 WindowsApps guard SSOT）未被
macos-compat-ci.yml paths 覆蓋的缺口。比照盲區 B 手法：新增 `_KNOWN_GLOB_SCAN_CONSUMERS`
顯式登記「哪個測試檔＋掃描哪個 glob pattern」，斷言該 pattern 字面值仍存在於來源碼中
（防登記腐化），再對其*動態即時*執行 `git ls-files -- pattern` 取得的真實結果
（非寫死清單，隨檔案新增/刪除自動同步，不會像盲區 B 清單一樣需要人工同步維護內容）
逐一機械斷言被對應 workflow 的 push/pull_request paths 覆蓋。刻意不比照盲區 A
擴充成通用正則掃描器：該檔另一處 `_tracked_files("*.py")` 語意上會匹配整個
`AutoClaude/`（500+ 檔）等大範圍前綴，若也納入通用掃描器會逼 CI paths 逐一列舉
數百檔或改用會讓每次原始碼異動都觸發本 workflow 的過寬萬用字元，這既不實際也偏離
本輪複審實測揪出的具體缺口（.ps1 6 支檔案）；`_KNOWN_GLOB_SCAN_CONSUMERS` 僅登記
已被實測證實有真實覆蓋缺口的 `*.ps1` 一項，`*.py` 的更廣語意留待未來若有實測缺口
再議（同盲區 B 手動登記僅涵蓋已知具體案例的既有慣例）。

S12（第七輪複審 DEF-101-068(a) 續）：四份 workflow 中 root-infra-ci.yml 是唯一
「刻意不設 paths 過濾」者（見該檔頭註解：NTFS 敵意檔名閘需對任何路徑生效，
paths 白名單必留盲區）——硬套上方「消費檔 ⊆ paths」同一套正則毫無意義（沒有
paths 可比對）。root-infra-ci.yml 真正的同構風險改頭換面成另一種盲區：它的
bash -n／py_compile 兩個步驟只用 ``find tools ...`` 掃描根層 ``tools/`` 一個
目錄；若日後在 monorepo 根新增另一個含 .sh／.py 腳本的目錄（如 ``scripts/``、
``bin/``），該目錄會完全逃過 root-infra-ci 的語法守門而不自知——這正是
DEF-101-042／DEF-101-068(a) 那種「消費者存在但守門忘了看它」的同一類缺陷，
只是發生在「掃描根目錄清單」而非「觸發 paths 清單」上。故本節另立兩道專屬
root-infra-ci.yml 的機械鎖（見檔案下方）：
  1. 鎖死「刻意不設 paths」的設計決策本身，防止日後被誤「補全」paths 而
     重新引入假綠盲區；
  2. 掃描 git 追蹤的全部 .sh／.py 檔，斷言不在 AutoClaude/、AISDLC_SDD/、
     .claude/（皆各自已有獨立 CI／既有 paths 鎖覆蓋）之外、也不在 tools/
     之內的「無主根層腳本」為空集——一旦出現即代表有新目錄逃過 root-infra-ci
     的語法守門。

R52（第 52 輪 Mac/Windows 相容性四方複審 Architect/SA/SD 交叉發現）：
`tools/tests/test_dev_start.py` 的 `TestNightlyHeartbeatFilenameContract` 用
`self._REPO / "AutoClaude" / "tools" / "run_local_nightly.sh"`（class 屬性
`self._REPO`，非字面 token `REPO_ROOT`／`_monorepo_root()`）讀取原始碼——與
盲區 B／C 同屬「掃描器方法論邊界」而非「解析器猜測範圍不夠」，`_JOIN_RE`／
`_SLASH_RE` 對此結構上零訊號，導致 windows-compat-ci.yml 漏列
`AutoClaude/tools/run_local_nightly.sh` 逃過本鎖（11 passed 未攔截）。第四種
消費形態（盲區 D），比照盲區 B／C 手法新增 `_KNOWN_LITERAL_PATH_CONSUMERS`
顯式登記「檔案＋消費它的來源檔」並機械斷言覆蓋 workflow paths。

R53（第 53 輪 Mac/Windows 相容性四方複審 Architect/SA/SD/QA 交叉發現）：兩處
獨立缺陷同輪修復——
(1) 盲區 D 登記表 R52 只補了 `test_dev_start.py` 用 `self._REPO` 消費
    `run_local_nightly.sh` 這一筆，但同一支消費檔內用完全相同手法（`self._REPO`
    ／class 屬性 `_REPO`）另外讀取了 `run_local_nightly.ps1`（僅 1 處）與
    `install_mac_nightly.sh`（3 處呼叫點、橫跨 3 個測試類）卻未登記——現行雖因
    `windows-compat-ci.yml` 的 `**/*.ps1` 萬用字元＋明列 `install_mac_nightly.sh`、
    `macos-compat-ci.yml` 的 `**/*.sh` 萬用字元＋明列 `run_local_nightly.ps1`
    意外雙重覆蓋而無假綠，但登記表本身名不符實、零機械保護，補齊這 2 筆
    （`tools/install_mac_nightly.sh`／`AutoClaude/tools/run_local_nightly.ps1`）。
(2) `_JOIN_RE`（`os.path.join(REPO_ROOT, ...)` 慣用法掃描器）只認得無底線字面
    token `REPO_ROOT`，對 `tools/tests/` 下 21/24 個測試檔慣用的底線前綴
    `_REPO_ROOT` 變數命名結構性零命中；而並用的 `_SLASH_RE`（`REPO_ROOT / "a"`
    慣用法）先前因**無錨定的純子字串匹配**才「巧合」命中 `_REPO_ROOT`——這反而
    是另一種未防護的假陽性風險（子字串匹配對 `FOO_REPO_ROOT` 這類非本意識別字
    同樣會誤命中，見下方測試）。改用共用 token `_REPO_ROOT_TOKEN`（顯式收斂
    `_REPO_ROOT`／`REPO_ROOT`／`_monorepo_root()` 三種寫法皆為完整識別字，非
    子字串）＋前置負向 lookbehind 防止嵌在更長識別字中誤判，`_JOIN_RE`／
    `_SLASH_RE` 兩者行為對稱一致；並新增獨立單元測試直接驗證兩個正則物件本身
    的涵蓋面（回應「安全網自身缺乏測試」的測試設計缺口）。

R54（第 54 輪複審 SA/SD 交叉觀察，純架構前瞻 watch item，非現行缺陷，19 passed
無違規）：本鎖的三份手寫登記字典——`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`（盲區 B，
R19）／`_KNOWN_GLOB_SCAN_CONSUMERS`（盲區 C，R50）／`_KNOWN_LITERAL_PATH_CONSUMERS`
（盲區 D，R52，且 R53 才發現盲區 D 內部登記本身漏補）——已與 WindowsApps guard
家族（DEF-101-400）同構演化出「正則/登記表軍備競賽」模式，但後者已有 Architect
明訂的收斂門檻（「若出現第 6 個繞過手法，優先評估 AST-based 掃描」），本鎖側從未
被賦予對等門檻。比照 DEF-101-400 措辭訂立決策準則供未來輪參考：**若再出現第 4
個盲區，或單一盲區內部第 2 次漏登記，優先評估收斂為程式化反向驗證（如對
`_KNOWN_*` 字典本身跑一次「有無遺漏子路徑」的通用掃描），而非再疊一份手寫登記
字典**。本節純記錄門檻，不阻擋、不改動任何測試邏輯。
"""
from __future__ import annotations

import fnmatch
import os
import re
import subprocess

import pytest
import yaml

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _monorepo_root() -> str:
    # scripts/tests/ → scripts/ → AISDLC_SDD/ → monorepo 根
    return os.path.dirname(os.path.dirname(os.path.dirname(_TESTS_DIR)))


_WORKFLOWS_DIR = os.path.join(_monorepo_root(), ".github", "workflows")

# workflow 檔名 ↔ 其實際執行的測試目錄（見各 workflow 內對應 run: 步驟）。
_WORKFLOW_TEST_DIRS: dict[str, str] = {
    "aisdlc-sdd-ci.yml": _TESTS_DIR,
    "windows-compat-ci.yml": os.path.join(_monorepo_root(), "tools", "tests"),
    "macos-compat-ci.yml": os.path.join(_monorepo_root(), "tools", "tests"),
}


def _workflow_paths(workflow_filename: str) -> tuple[list[str], list[str]]:
    wf = os.path.join(_WORKFLOWS_DIR, workflow_filename)
    with open(wf, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)  # YAML 1.1 把裸 key `on` 解析為布林 True
    return on["push"]["paths"], on["pull_request"]["paths"]


# _monorepo_root()（AISDLC_SDD/scripts/tests/ 慣用法）與 REPO_ROOT／_REPO_ROOT
# （tools/tests/ 慣用法，該目錄下巧合等於 monorepo 根；21/24 個測試檔實際採用
# 底線前綴 `_REPO_ROOT` 命名慣例，僅 3 個無底線）皆可能出現在被掃描目錄中；
# 三者統一辨識為完整識別字（前置負向 lookbehind 防止嵌在更長識別字中誤判，如
# `FOO_REPO_ROOT`），誤配對到的候選路徑會被下方「磁碟上存在」過濾器自然濾除
# （安全網）。R53：修復 `_JOIN_RE` 先前只認無底線 `REPO_ROOT`、與 `_SLASH_RE`
# （先前靠無錨定子字串匹配才「巧合」吃到底線前綴）行為不對稱的正則死角。
_REPO_ROOT_TOKEN = r"(?:_monorepo_root\(\)|_REPO_ROOT|REPO_ROOT)"
_NOT_WORD_BEFORE = r"(?<![A-Za-z0-9_])"
_JOIN_RE = re.compile(
    rf"os\.path\.join\(\s*{_NOT_WORD_BEFORE}{_REPO_ROOT_TOKEN}\s*,([^)]*)\)"
)
_SLASH_RE = re.compile(
    rf'{_NOT_WORD_BEFORE}{_REPO_ROOT_TOKEN}((?:\s*/\s*"[^"]+")+)'
)
_STR_RE = re.compile(r'"([^"]+)"')

# S26：`import <module>` / `import <module> as <alias>` 頂層陳述式（tools/tests/ 三支
# 新測試檔的「直接 import 根層同儕模組」慣用法，見上方檔頭 S26 說明）。
_IMPORT_RE = re.compile(
    r"^import\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s+as\s+[A-Za-z_][A-Za-z0-9_]*)?\s*(?:#.*)?$",
    re.MULTILINE,
)

# R19 四方一審 QA 對抗式 bug-injection 發現：`_IMPORT_RE` 只認 `import X`／
# `import X as Y`，`from X import Y` 這種同樣常見的頂層 import 陳述式完全零防護
# （QA 實測：建一支根層模組＋一支測試以 `from <module> import <name>` 消費，掃描器
# 10 passed 全綠、完全偵測不到）。補一支對稱正則堵上這第三種消費模式。
_FROM_IMPORT_RE = re.compile(
    r"^from\s+([A-Za-z_][A-Za-z0-9_]*)\s+import\s+",
    re.MULTILINE,
)

# R19 修復包 A 盲區 A：`sys.path.insert(0, str(Path(__file__).resolve().parents[N]))`
# 或其後接 `/ "seg1" / "seg2" ...` 路徑片段（如 tools/tests/test_platform_utils_dedup.py
# 的 `parents[1] / "lib"`，把 tools/lib/ 塞進 sys.path 才能 `import platform_utils`）。
# 舊版 candidate_base_dirs 只猜「own_dir / parent(own_dir)」兩層寫死候選，platform_utils.py
# 實際多一層 lib/ 子目錄，兩個候選都撲空。本正則動態抓出原始碼裡實際出現的
# sys.path.insert 陳述式所指向的路徑，相對於來源檔自身位置解析 parents[N]，
# 取代猜測。
_SYSPATH_PARENTS_RE = re.compile(
    r"sys\.path\.insert\(\s*0\s*,\s*str\(\s*Path\(__file__\)\.resolve\(\)\.parents\[(\d+)\]"
    r"((?:\s*/\s*\"[^\"]+\")*)\s*\)\s*\)"
)


def _resolve_sys_path_insert_dirs(src: str, source_file: str) -> list[str]:
    """動態解析 `source_file` 原始碼中 `sys.path.insert(0, str(Path(__file__)
    .resolve().parents[N] / "seg" ...))` 陳述式實際指向的絕對目錄（見上方 R19 說明），
    取代「own_dir / parent(own_dir)」兩層寫死猜測（盲區 A）。
    """
    dirs: list[str] = []
    for m in _SYSPATH_PARENTS_RE.finditer(src):
        n = int(m.group(1))
        base = source_file
        for _ in range(n + 1):
            base = os.path.dirname(base)
        segs = _STR_RE.findall(m.group(2))
        dirs.append(os.path.join(base, *segs) if segs else base)
    return dirs


def _scan_dir_for_root_paths(directory: str) -> set[str]:
    found: set[str] = set()
    if not os.path.isdir(directory):
        return found
    for name in sorted(os.listdir(directory)):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as f:
            src = f.read()
        for m in _JOIN_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
        for m in _SLASH_RE.finditer(src):
            segs = _STR_RE.findall(m.group(1))
            if segs:
                found.add("/".join(segs))
    return found


def _scan_import_consumed_paths(directory: str) -> set[str]:
    """BFS 掃描 `directory` 內 test_*.py 的頂層 `import <module>`，將 module 解析為
    「來源檔自身所在目錄」或「其父目錄」下的 `<module>.py`（本 repo 兩種並存慣例：
    tools/*.py 用 `sys.path.insert(0, ...parent)`＝自身目錄；tools/tests/test_*.py
    用 `sys.path.insert(0, ...parents[1])`＝父目錄——兩者恰好都解到 tools/ 本身，
    故兩層候選皆試、以磁碟上實際存在者為準），並對新發現的根層 .py 檔遞迴重複同一
    掃描（fixed point），關閉「測試只 import A、A 內部又 import B」的第二層盲區
    （見檔頭 S26）。
    """
    if not os.path.isdir(directory):
        return set()
    seed_files = [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.startswith("test_") and name.endswith(".py")
    ]
    consumed: set[str] = set()
    visited: set[str] = set()
    queue = list(seed_files)
    while queue:
        f = os.path.abspath(queue.pop(0))
        if f in visited or not os.path.isfile(f):
            continue
        visited.add(f)
        with open(f, encoding="utf-8") as fh:
            src = fh.read()
        own_dir = os.path.dirname(f)
        candidate_base_dirs = [
            own_dir,
            os.path.dirname(own_dir),
            *_resolve_sys_path_insert_dirs(src, f),
        ]
        module_names = [m.group(1) for m in _IMPORT_RE.finditer(src)]
        module_names += [m.group(1) for m in _FROM_IMPORT_RE.finditer(src)]
        for module_name in module_names:
            for base_dir in candidate_base_dirs:
                candidate_abs = os.path.join(base_dir, module_name + ".py")
                if not os.path.isfile(candidate_abs):
                    continue
                rel = os.path.relpath(candidate_abs, _monorepo_root()).replace(os.sep, "/")
                consumed.add(rel)
                queue.append(candidate_abs)
    return consumed


def _consumed_root_paths(directory: str) -> set[str]:
    found = _scan_dir_for_root_paths(directory) | _scan_import_consumed_paths(directory)
    # 只留「磁碟上存在的檔案」——join 到目錄／動態片段者非本鎖標的
    return {p for p in found if os.path.isfile(os.path.join(_monorepo_root(), p))}


@pytest.mark.parametrize(
    "src,expect_join,expect_slash",
    [
        # 無底線 REPO_ROOT／_monorepo_root()：既有慣用法，修復前後皆須命中。
        ('os.path.join(REPO_ROOT, "a", "b")', True, None),
        ('REPO_ROOT / "a" / "b"', None, True),
        ('os.path.join(_monorepo_root(), "a", "b")', True, None),
        ('_monorepo_root() / "a" / "b"', None, True),
        # R53：底線前綴 _REPO_ROOT（tools/tests/ 21/24 檔實際命名慣例）——修復前
        # _JOIN_RE 結構性零命中，_SLASH_RE 靠無錨定子字串「巧合」命中；修復後
        # 兩者須對稱皆命中。
        ('os.path.join(_REPO_ROOT, "a", "b")', True, None),
        ('_REPO_ROOT / "a" / "b"', None, True),
    ],
)
def test_join_re_and_slash_re_symmetric_for_underscore_prefix(src, expect_join, expect_slash):
    """R53 QA/Architect/SA/SD 四方交叉發現：`_JOIN_RE`／`_SLASH_RE` 這兩個「防
    假綠安全網」正則自身先前無任何獨立單元測試驗證涵蓋面，導致 `_JOIN_RE` 對
    底線前綴 `_REPO_ROOT`（主流命名慣例）結構性零命中的死角長期無訊號。本測試
    直接對正則物件斷言，鎖住修復後的對稱行為，防止未來再退化。
    """
    if expect_join is not None:
        assert bool(_JOIN_RE.search(src)) is expect_join, f"_JOIN_RE 對 {src!r} 命中應為 {expect_join}"
    if expect_slash is not None:
        assert bool(_SLASH_RE.search(src)) is expect_slash, (
            f"_SLASH_RE 對 {src!r} 命中應為 {expect_slash}"
        )


def test_slash_re_does_not_match_longer_embedding_identifier():
    """R53 附帶防呆：`_SLASH_RE` 修復底線前綴死角時新增的前置負向 lookbehind，
    須確認未反過來對「REPO_ROOT 只是更長識別字尾碼」的情況（如
    `FOO_REPO_ROOT`）誤判為本鎖標的變數——修復前的純子字串匹配對此會誤命中
    （見 R53 檔頭說明），修復後應正確排除。
    """
    assert not _SLASH_RE.search('FOO_REPO_ROOT / "a" / "b"'), (
        "_SLASH_RE 不應把 FOO_REPO_ROOT 這類更長識別字尾碼誤判為 REPO_ROOT 本尊"
    )


@pytest.mark.parametrize("workflow_filename", sorted(_WORKFLOW_TEST_DIRS))
def test_push_and_pr_paths_symmetric(workflow_filename):
    push, pr = _workflow_paths(workflow_filename)
    assert push == pr, (
        f"{workflow_filename}: push 與 pull_request paths 不對稱（單側漏補）：{push} vs {pr}"
    )


def test_known_consumers_detected():
    """正則退化防呆：已知消費檔必被掃出，否則本鎖形同虛設。"""
    consumed: set[str] = set()
    for directory in _WORKFLOW_TEST_DIRS.values():
        consumed |= _consumed_root_paths(directory)
    expected = {
        "tools/check_ntfs_paths.py",
        "tools/git-hooks/pre-commit",
        ".claude/settings.json",
        "AutoClaude/.claude/settings.json",
        ".claude/hooks/sdd_hook_router.py",
        # S26：import-based BFS 新增偵測（見上方檔頭 S26 說明）
        "tools/check_hooks_liveness.py",
        "tools/check_defect_log_crossref.py",
        "tools/check_wrapper_thinness.py",
        "tools/_stdio_utf8.py",  # 經 check_hooks_liveness.py 等三檔遞移 import 偵得
        # R19 修復包 A 盲區 A：test_platform_utils_dedup.py 的
        # `sys.path.insert(0, ...parents[1] / "lib")` 動態解析偵得
        "tools/lib/platform_utils.py",
    }
    missing = expected - consumed
    assert not missing, f"掃描器漏抓已知消費檔（正則退化）：{missing}"


@pytest.mark.parametrize("workflow_filename", sorted(_WORKFLOW_TEST_DIRS))
def test_all_root_consumers_covered_by_ci_paths(workflow_filename):
    push, _ = _workflow_paths(workflow_filename)
    tests_dir = _WORKFLOW_TEST_DIRS[workflow_filename]
    uncovered = [
        p
        for p in sorted(_consumed_root_paths(tests_dir))
        if not p.startswith("AISDLC_SDD/")
        and not any(fnmatch.fnmatch(p, pat) for pat in push)
    ]
    assert not uncovered, (
        f"根層消費檔未列入 {workflow_filename} paths"
        f"（只改該檔時其回歸鎖不會跑，DEF-101-042 同構）：{uncovered}"
    )


# --- root-infra-ci.yml 專屬機械鎖（S12 / DEF-101-068(a)）---------------------------
# root-infra-ci.yml 刻意不設 paths 過濾，上方 _workflow_paths()/_consumed_root_paths()
# 一套「消費檔 ⊆ paths」正則對它不適用（沒有 paths 可比對）。以下改針對它真正的
# 同構風險（掃描根目錄清單而非觸發 paths 清單）另立專屬檢核，見檔頭 S12 說明。

_ROOT_INFRA_CI_PATH = os.path.join(_WORKFLOWS_DIR, "root-infra-ci.yml")

# bash -n／py_compile 兩步驟只掃描根層 tools/；AutoClaude/、AISDLC_SDD/、.claude/
# 各自已有獨立 CI 或既有 paths 鎖覆蓋其 .sh／.py（見 test_known_consumers_detected
# 已驗證 .claude/hooks/sdd_hook_router.py 被 windows-compat-ci.yml／aisdlc-sdd-ci.yml
# paths 覆蓋），故豁免；其餘任何根層 .sh／.py 若不在 tools/ 之下即為無主腳本。
_ROOT_INFRA_SCAN_EXEMPT_PREFIXES = ("AutoClaude/", "AISDLC_SDD/", ".claude/", "tools/")


def _git_ls_files(pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", pathspec],
        cwd=_monorepo_root(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def test_root_infra_ci_has_no_paths_filter():
    """鎖死 root-infra-ci.yml「刻意不設 paths 過濾」的設計決策（見該檔頭註解）。

    NTFS 敵意檔名閘必須對任何路徑的新增檔案生效，paths 白名單天生必留盲區，
    故此 workflow 唯一安全做法是不設 paths（每次 push/PR 全跑，皆為輕量步驟，
    成本可忽略）。若日後有人「比照其餘三份 workflow」補上 paths 清單，會
    重新引入本測試檔案存在的目的正要根除的假綠盲區——只改被排除路徑時，
    NTFS 閘／腳本語法閘就不會跑。本鎖鎖死此決策，防止被誤「補全」。
    """
    with open(_ROOT_INFRA_CI_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    on = data.get("on") or data.get(True)
    push = on.get("push") or {}
    pull_request = on.get("pull_request") or {}
    assert "paths" not in push, (
        "root-infra-ci.yml 的 push 觸發不應設 paths 過濾"
        "（NTFS 敵意檔名閘需對任何路徑生效，見該檔頭註解；補 paths 會重新引入假綠盲區）"
    )
    assert "paths" not in pull_request, (
        "root-infra-ci.yml 的 pull_request 觸發不應設 paths 過濾（理由同 push，見上）"
    )


# --- 執行期子行程消費（盲區 B，R19 修復包 A）---------------------------------------
# AutoClaude/tools/run_act_core.py 完全不被 tools/tests/ 下任何測試檔以 import 或
# 路徑字串引用——它是被 run_act.sh/.ps1 以「子行程呼叫殼腳本」方式消費，測試測的是
# 黑盒殼腳本行為（subprocess 呼叫 shell script），而非直接 import 核心邏輯。這類
# 「執行期子行程消費」關係，上方 `_scan_import_consumed_paths()` 的靜態正則 import-BFS
# 結構上永遠看不到——與盲區 A 不同性質（盲區 A 是解析器猜測範圍不夠，這裡是掃描器
# 方法論邊界），故不再對此加新正則規則（過去 S6→S12→S26 三輪皆是加新正則打地鼠），
# 改用顯式清單 + 機械斷言其被對應 workflow 的 push+pull_request paths 覆蓋
# （fail-loud：檔案不存在或未被覆蓋即讓本測試紅），手法仿照上方
# test_known_consumers_detected() 的 expected 顯式集合。
# R32 Scan-B 訂正：tools/bootstrap_core.py 已於 R31（DEF-101-281）新增
# tools/tests/test_bootstrap_core.py 直接 import 之，不再是「執行期子行程消費」，
# 已被上方 `_scan_import_consumed_paths()` 一般掃描器自動涵蓋，故自本清單移除；
# 僅 run_act_core.py 仍屬此盲區（見 DEF-101-286 待補測試）。
_KNOWN_SUBPROCESS_ONLY_CONSUMERS: dict[str, tuple[str, ...]] = {
    "AutoClaude/tools/run_act_core.py": ("macos-compat-ci.yml", "windows-compat-ci.yml"),
}


def test_known_subprocess_only_consumers_covered_by_ci_paths():
    """盲區 B 機械鎖：見上方 _KNOWN_SUBPROCESS_ONLY_CONSUMERS 說明。"""
    for rel_path, workflow_filenames in _KNOWN_SUBPROCESS_ONLY_CONSUMERS.items():
        abs_path = os.path.join(_monorepo_root(), rel_path)
        assert os.path.isfile(abs_path), (
            f"{rel_path} 不存在（已改名/搬移？）— _KNOWN_SUBPROCESS_ONLY_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                assert any(fnmatch.fnmatch(rel_path, pat) for pat in paths), (
                    f"{rel_path}（執行期子行程消費，靜態 import-BFS 結構上看不到）"
                    f"未被 {workflow_filename} 的 {label} paths 覆蓋"
                )


# --- git ls-files glob 動態掃描消費（盲區 C，R50）---------------------------------
# tools/tests/test_windowsapps_guard_cross_consistency.py 用 `_tracked_files(pattern)`
# （`git ls-files -- pattern`）動態掃描全部 git 追蹤檔案，而非靜態字面路徑引用或
# import 陳述式——上方 `_scan_dir_for_root_paths()`／`_scan_import_consumed_paths()`
# 兩種偵測機制對此結構性零訊號（見檔頭 R50 說明），連盲區 B 的手動登記清單都沒有。
# 比照盲區 B（`_KNOWN_SUBPROCESS_ONLY_CONSUMERS`）手法：顯式登記「哪個測試檔＋
# 掃描哪個 glob pattern」，再對其*動態即時*執行 `git ls-files -- pattern` 取得的
# 真實結果（非寫死清單，隨檔案新增/刪除自動同步）逐一機械斷言被對應 workflow 的
# push+pull_request paths 覆蓋。與盲區 B 不同：盲區 B 登記的是固定檔名，本清單登記
# 的是「測試檔＋pattern」，覆蓋範圍隨 git 追蹤狀態自動變動，不需要每次新增/刪除
# 符合 pattern 的檔案時手動同步清單內容（只有 pattern 本身或消費它的測試檔改名時
# 才需要同步）。
_KNOWN_GLOB_SCAN_CONSUMERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "tools/tests/test_windowsapps_guard_cross_consistency.py": (
        "*.ps1",
        ("macos-compat-ci.yml", "windows-compat-ci.yml"),
    ),
}


def test_known_glob_scan_consumers_covered_by_ci_paths():
    """盲區 C 機械鎖：見上方 _KNOWN_GLOB_SCAN_CONSUMERS 說明。"""
    for rel_test_path, (pattern, workflow_filenames) in _KNOWN_GLOB_SCAN_CONSUMERS.items():
        abs_test_path = os.path.join(_monorepo_root(), rel_test_path)
        assert os.path.isfile(abs_test_path), (
            f"{rel_test_path} 不存在（已改名/搬移？）— _KNOWN_GLOB_SCAN_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        with open(abs_test_path, encoding="utf-8") as f:
            src = f.read()
        assert f'"{pattern}"' in src or f"'{pattern}'" in src, (
            f"{rel_test_path} 原始碼已不含 glob pattern {pattern!r}（改名/改寫？）"
            "——_KNOWN_GLOB_SCAN_CONSUMERS 顯式清單須同步更新，否則本鎖名不符實"
        )
        # 排除 AISDLC_SDD/ 前綴：與 test_all_root_consumers_covered_by_ci_paths()
        # 同一政策（見檔頭說明），該前綴由各 workflow 既有的 "AISDLC_SDD/**" 系列
        # pattern 天然覆蓋，不需本鎖重複驗證。
        matched = [rel for rel in _git_ls_files(pattern) if not rel.startswith("AISDLC_SDD/")]
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                uncovered = [
                    rel for rel in matched if not any(fnmatch.fnmatch(rel, pat) for pat in paths)
                ]
                assert not uncovered, (
                    f"{rel_test_path} 以 `_tracked_files({pattern!r})`（git ls-files "
                    "glob 動態掃描，靜態 import-BFS／路徑字面正則結構上看不到，盲區 C）"
                    f"消費的檔案未被 {workflow_filename} 的 {label} paths 覆蓋：{uncovered}"
                )


# --- self._REPO 字面路徑消費（盲區 D，R52）---------------------------------------
# tools/tests/test_dev_start.py 的 TestNightlyHeartbeatFilenameContract 用
# `self._REPO / "AutoClaude" / "tools" / "run_local_nightly.sh"`（class 屬性
# `_REPO = Path(dev_start.__file__).resolve().parents[1]`，非字面 token
# `REPO_ROOT`／`_monorepo_root()`）讀取原始碼做心跳契約錨點斷言——上方
# `_JOIN_RE`／`_SLASH_RE` 只認得字面 token `REPO_ROOT`／`_monorepo_root()`，對
# 這種 class 屬性間接消費慣用法結構上零訊號（R52 四方複審實測揪出：
# windows-compat-ci.yml 漏列此檔案、本鎖 11 passed 未攔截）。與盲區 B／C 性質
# 相同（掃描器方法論邊界，非解析器猜測範圍不夠），比照同一手法：顯式登記
# 「檔案 + 消費它的來源檔」+ 機械斷言消費關係仍存在（防登記腐化）＋覆蓋
# workflow paths。
#
# R53（Architect/SA/SD/QA 交叉發現）：同一支消費檔 `test_dev_start.py` 內用完全
# 相同手法（`self._REPO` 或其 class 屬性 `_REPO`）另外讀取了
# `run_local_nightly.ps1`（`TestNightlyHeartbeatFilenameContract
# .test_windows_reader_filename_matches_ps1_writer`）與 `install_mac_nightly.sh`
# （`TestNightlyHeartbeatFilenameContract.test_installer_third_site_filename_
# and_threshold`／`TestCrossSiteLiteralLocks._installer_text`／
# `TestNightlyHeartbeatCrossSiteBehavioralEquivalence._INSTALLER`，橫跨 3 個
# 測試類）卻未登記，R52 只補了 `run_local_nightly.sh` 一筆。`tools/tests/` 同時
# 被 windows-compat-ci.yml／macos-compat-ci.yml 兩份 workflow 執行（見
# `_WORKFLOW_TEST_DIRS`），故兩檔皆須登記兩份 workflow：`run_local_nightly.ps1`
# 現行由 windows 側 `**/*.ps1` 萬用字元＋macos 側明列覆蓋，`install_mac_nightly.sh`
# 現行由 macos 側 `**/*.sh` 萬用字元＋windows 側明列覆蓋——雙重覆蓋非巧合免驗證
# 的理由，仍須機械鎖住，否則任一側覆蓋機制被移除即靜默失效。
_KNOWN_LITERAL_PATH_CONSUMERS: dict[str, tuple[str, tuple[str, ...]]] = {
    "AutoClaude/tools/run_local_nightly.sh": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml",),
    ),
    "AutoClaude/tools/run_local_nightly.ps1": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml", "macos-compat-ci.yml"),
    ),
    "tools/install_mac_nightly.sh": (
        "tools/tests/test_dev_start.py",
        ("windows-compat-ci.yml", "macos-compat-ci.yml"),
    ),
}


def test_known_literal_path_consumers_covered_by_ci_paths():
    """盲區 D 機械鎖：見上方 _KNOWN_LITERAL_PATH_CONSUMERS 說明。"""
    for rel_path, (consumer_rel_path, workflow_filenames) in _KNOWN_LITERAL_PATH_CONSUMERS.items():
        abs_path = os.path.join(_monorepo_root(), rel_path)
        assert os.path.isfile(abs_path), (
            f"{rel_path} 不存在（已改名/搬移？）— _KNOWN_LITERAL_PATH_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        abs_consumer_path = os.path.join(_monorepo_root(), consumer_rel_path)
        assert os.path.isfile(abs_consumer_path), (
            f"{consumer_rel_path} 不存在（已改名/搬移？）— _KNOWN_LITERAL_PATH_CONSUMERS "
            "顯式清單須同步更新，否則本鎖名不符實"
        )
        with open(abs_consumer_path, encoding="utf-8") as f:
            consumer_src = f.read()
        basename = rel_path.rsplit("/", 1)[-1]
        assert basename in consumer_src, (
            f"{consumer_rel_path} 原始碼已不含 {basename!r}（改名/改寫？）"
            "——_KNOWN_LITERAL_PATH_CONSUMERS 顯式清單須同步更新，否則本鎖名不符實"
        )
        for workflow_filename in workflow_filenames:
            push, pr = _workflow_paths(workflow_filename)
            for label, paths in (("push", push), ("pull_request", pr)):
                assert any(fnmatch.fnmatch(rel_path, pat) for pat in paths), (
                    f"{rel_path}（`self._REPO` 等非字面 REPO_ROOT/_monorepo_root() "
                    f"token 間接消費，靜態正則看不到，盲區 D）未被 {workflow_filename} "
                    f"的 {label} paths 覆蓋"
                )


def test_root_infra_ci_bash_and_py_scan_roots_have_no_stray_scripts():
    """root-infra-ci.yml 的 bash -n／py_compile 步驟只掃描根層 tools/。

    若日後在 monorepo 根新增另一個含 .sh／.py 腳本、且不屬於 AutoClaude/、
    AISDLC_SDD/、.claude/（各自已有獨立 CI 或既有 paths 鎖）的目錄，該目錄會
    完全逃過 root-infra-ci 的語法守門而不自知——與 DEF-101-042／DEF-101-068(a)
    同一類「消費者存在但守門忘了看它」缺陷，只是發生在掃描根目錄清單而非
    觸發 paths 清單。本鎖機械斷言：git 追蹤的全部 .sh／.py 檔，扣除上述三個
    有獨立覆蓋的子專案／目錄後，必須全部落在 tools/ 之下。
    """
    for ext in (".sh", ".py"):
        tracked = _git_ls_files(f"*{ext}")
        stray = [
            p
            for p in tracked
            if not p.startswith(_ROOT_INFRA_SCAN_EXEMPT_PREFIXES)
        ]
        assert not stray, (
            f"發現不在 tools/ 下、也不屬於 AutoClaude/／AISDLC_SDD/／.claude/ 的根層"
            f"{ext} 腳本，root-infra-ci.yml 的 bash -n／py_compile 掃描不到"
            f"（DEF-101-068(a) 同構盲區）：{stray}"
        )
