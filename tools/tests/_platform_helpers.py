#!/usr/bin/env python3
"""tools/tests 共用的①跨平台測試 fixture 輔助函式，與②供靜態鎖消費的原始碼解析 SSOT。

R57 round 3 ARCH-R57R3-02 訂正收納契約：本檔原本只宣告第①類（收納判準見下段「對開發者本機
環境有隱性假設」），但 R57 收進了 `strip_ps_comments` 家族——那是一支 PowerShell 原始碼
tokenizer、被靜態鎖消費，既不是 fixture 也與本機環境假設無關，佔全檔一半以上行數。契約與
內容脫節是「雜物抽屜」的早期訊號，故明列兩類。**第②類的收納判準**：被兩處以上靜態鎖消費、
且複本化會導致「同一盲點被抄 N 遍」（見 `docs/06_quality/CrossPlatform_Scan_Dimensions.md`
的 R57 Scan-E 判例）。更徹底的做法是把解析器拆到獨立的 `_ps_source.py`，但那需連動呼叫端鎖
翻修，依 Rule 3 外科式原則列 backlog。**R59 改派**：原寫「列 R58 backlog」，而 R58 整輪作廢（`reset --hard 75aab89`）＝指向不存在的輪次、無承接者；改派為 R60 起未指派 backlog（帳本 DEF-101-521 立帳）。

四方複審 S21（architecture-review-own-finding）落地：F2（_copy_functional_interpreter）
與 F3（symlink 建立失敗 → skipTest）都是同一類「測試 fixture 對開發者本機環境有隱性
假設」的問題，且都只有在真的於目標作業系統上跑一次才會顯形（見
docs/06_quality/AutoSDD_Defect_Log.md DEF-101-064／DEF-101-069）。集中在本檔，供
tools/tests/ 內未來新測試直接複用，不必重新踩雷。

若 AutoClaude/tests 出現對等需求（同款「複製直譯器模擬健康 venv」或「建立 symlink」
情境），比照本檔邏輯在 AutoClaude/tests/conftest.py 加對稱 fixture 並互相加文件連結
——兩套測試框架 pytest root 不同，不強求單一檔案共用，但邏輯必須一致。

R57 SA-R57R2-03 收斂：`cut_ps_inline_comment`／`strip_ps_comments`（PowerShell
註解剝除，供「錨點只認功能碼、不認註解」的靜態鎖使用）原本在
`test_find_git_bash_parity.py` 與 `test_windows_nightly_anchor_parity.py` 各存一份
AST 逐字相同的複本，且無一致性鎖——同輪卻把 `_ci_scan_anchors.py` 的三份複本以
「三份複製只是把同一個盲點抄了三遍」為由收斂，兩套標準。事後被 A-R57R2-02／
R57R2-QA-01 證實：兩份複本確實同時帶著同一個 here-string 起始誤判的 fail-open。
故一併收斂進本檔，呼叫端一致性由
`test_find_git_bash_parity.py::TestPsCommentStripperSsotCallsiteLock` 機械守護。

R69 後續（DEF-101-753）同判例第二次套用：`usable_bash_for_fixture()`（取得一支真的
能跑 .sh 的 bash）原本在 `test_bash_probe_spec_contract.py` 與
`test_macos_smoke_skip_honesty.py` 各存一份 fixture 用途複本、且**排除規則不一致**，
而 `test_smoke_ci_sync.py` 乾脆兩份都沒用、直接把字面值 `"bash"` 交給 subprocess ⇒
Windows CI 上跑到 WSL 佔位 bash 翻紅。三處收斂為本檔一份，呼叫端一致性由
`test_bash_probe_spec_contract.py::TestNoBareBashInvocationInToolsTests` 機械守護。
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PureWindowsPath

# 驗活探測「參數」（PROBE_CMD／期望輸出／System32 排除段）的既有單一真相源，供
# `usable_bash_for_fixture()` 消費（不另立第二份字面值；WHY 見該檔 docstring）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import bash_probe_spec as _spec  # noqa: E402

# 平台中立的假「絕對」repo 根（R11 真 Mac 首跑實證，抽自 test_check_hooks_liveness.py）：
# 受測函式常依賴「repo_root / 絕對路徑 → 直接取代」的 pathlib join 語意，但 "D:/repo"
# 只在 Windows 是絕對路徑；POSIX 上 join 會變成 D:/repo/D:/repo/…、resolve 後恆不相等
# → Windows 全綠、Mac/Linux 假紅。凡測試需要「絕對路徑」語意者一律用本常數，
# 不可寫死磁碟機代號（tools/tests/test_platform_neutral_paths.py 機械掃描守護）。
ABS_FAKE_REPO = Path("D:/repo") if sys.platform == "win32" else Path("/repo")

# `usable_bash_for_fixture()` 的候選子路徑：Git for Windows 的兩個 bash.exe 佈局，
# 外加 POSIX 佈局（macOS/Linux 上 git 相鄰目錄往上數層即命中 `/bin/bash`）。
_BASH_SUBPATHS = ("usr/bin/bash.exe", "bin/bash.exe", "usr/bin/bash", "bin/bash")


def _bash_candidates() -> list[str]:
    """本機 bash 候選路徑（依序）：**git 相鄰的 bash 優先**（隨 git 安裝、必為真 Git
    Bash），PATH 上的裸 bash 次之且須通過 System32 整段排除。

    抽成獨立函式而非讓兩個消費者（`usable_bash_for_fixture()`／
    `path_honouring_bash_for_fixture()`）各寫一份：候選蒐集規則裡的 System32 排除
    正是 DEF-101-753 的本體，抄第二份就是把同一個盲點再種一次（本檔 docstring 第②類
    收納判準）。兩個消費者的差別只在**怎麼挑**，不在**有哪些候選**。
    """
    candidates: list[str] = []
    git = shutil.which("git")
    if git:
        for up in list(Path(git).resolve().parents)[:4]:
            for sub in _BASH_SUBPATHS:
                cand = up / sub
                if cand.is_file():
                    candidates.append(str(cand))
    bare = shutil.which("bash")
    if bare and not any(
        part.lower() == _spec.SYSTEM32_SEGMENT for part in PureWindowsPath(bare).parts
    ):
        candidates.append(bare)
    return candidates


# `honours_external_path()` 的量測探針：**全部是 shell builtin**，一個外部指令都不用。
# WHY：這支探針要在「PATH 只剩一個空目錄」下執行，任何外部指令（`tr`／`wc`／`env`…）
# 本身就查不到 ⇒ 用了就量不到東西、還會把「查不到外部指令」誤記成「探針壞掉」。
# `IFS=:` 讓 `$PATH` 依段切分、`set -f` 關掉未加引號展開時的 glob，`set --` 把各段變成
# 位置參數；輸出兩行＝段數、第一段內容。
_PATH_ECHO_CMD = 'IFS=: ; set -f ; set -- $PATH ; echo $# ; echo "$1"'


def honours_external_path(bash: str) -> bool:
    """這支 bash 是否**照單全收**呼叫端傳入的 `PATH`（沒有自我注入額外目錄）？

    🔴 這是一條**載具性質**判準，不是「被測物會不會通過」的預判——它問的是「我用
    `env={"PATH": …}` 限縮外部 PATH 這個模擬手法，對這支解譯器到底有沒有作用」。
    量測方式是叫 bash 自己把它看到的 `$PATH` 段數與第一段印回來，與 `PROBE_CMD`／
    `dirname` 完全無關：就算有人把 `PROBE_CMD` 退化成只剩 `echo`，本函式的判定也一字
    不變（不會因此多 skip 掉一支測試）。

    WHY 需要它（DEF-101-618(a) 的殘留，R71 於 Windows 11 真機實測收斂）：Git for
    Windows 的 `bin\\bash.exe` 是 **MSYS 啟動器**，啟動時**無條件**把
    `/mingw64/bin:/usr/bin`（相對自身安裝根）插到自己內部 PATH 最前面，不理會外部傳
    進去的 PATH。實測（`env={"PATH": <單一空目錄>}`）：

        Git\\bin\\bash.exe     -> $PATH 段數 4，
                                 /mingw64/bin:/usr/bin:/d/bin:<空目錄>   ← 自我注入
        Git\\usr\\bin\\bash.exe -> $PATH 段數 1，<空目錄>                 ← 照單全收

    前者上面「限縮 PATH 讓 `dirname` 查不到」的模擬**完全是 no-op**（`dirname` 仍解析
    到 `/usr/bin/dirname`），任何建立在該手法上的斷言量到的都是載具失效而非被測物缺陷。

    判定為 True 的條件：子行程起得來、`rc == 0`、回報的 `$PATH` 只有 **1 段**、且該段
    帶著我們剛建立的唯一暫存目錄名。任一條不成立即 False（fail-closed：寧可判成「這支
    不能用來做這個模擬」，也不要在無鑑別力的載具上跑出誤導性的紅燈）。

    已知邊界（誠實劃界）：段數以 `:` 切分，是 bash 內部的 PATH 分隔符，故 MSYS 會把
    `C:\\Users\\…` 轉成 `/c/Users/…` 的情形已被涵蓋；若某天出現「不做 POSIX 轉換、原樣
    保留磁碟機代號」的 bash，`C:` 的冒號會被算成兩段而判為 False ⇒ 方向仍是 fail-closed。
    """
    with tempfile.TemporaryDirectory(prefix="path_honour_probe_") as only_dir:
        try:
            proc = subprocess.run(
                [bash, "-c", _PATH_ECHO_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=20, env={"PATH": only_dir},
            )
        except Exception:  # noqa: BLE001 — 任何載具問題都只代表「這支不能用來做模擬」
            return False
        lines = proc.stdout.splitlines()
        if proc.returncode != 0 or len(lines) < 2:
            return False
        return lines[0].strip() == "1" and Path(only_dir).name in lines[1]


def path_honouring_bash_for_fixture() -> str | None:
    """回傳一支「外部傳入的 PATH 真的管得住其外部指令查找」的 bash；一支都沒有回 `None`。

    給的是**做「限縮 PATH」這類模擬時該用的解譯器**，與 `usable_bash_for_fixture()`
    的用途不同，兩者在同一台機器上很可能回不同的二進位，這是設計而非瑕疵：
      · `usable_bash_for_fixture()` 要的是「能真的把 repo 的 .sh 跑完」⇒ 會挑通過
        `PROBE_CMD` 驗活的那支。Windows 上當 ambient PATH 沒有 coreutils 目錄時，
        `usr\\bin\\bash.exe` 會驗活失敗（找不到 `dirname`）而落到自我注入的
        `bin\\bash.exe`——那支**能跑腳本**，正是它要的。
      · 本函式要的是「我說 PATH 只有這些，它就只找這些」⇒ 刻意**不**要求候選通過
        `PROBE_CMD` 驗活。要求了反而會把唯一合格的 `usr\\bin\\bash.exe` 排除掉
        （它在受限 ambient PATH 下驗活本來就會失敗），等於自我否定。

    回 `None` 代表本機沒有任何載具能做這個模擬。呼叫端必須**帶理由 skip**，且該情況
    不得靜默——由 `test_bash_probe_spec_contract.py::
    TestRestrictedPathCarrierCannotSilentlyVanish` 反向哨兵 fail-loud。
    """
    for cand in _bash_candidates():
        if honours_external_path(cand):
            return cand
    return None


def usable_bash_for_fixture() -> str | None:
    """回傳一支**真的能跑 repo bash 腳本**的 bash 路徑；一支都探不到回 `None`。

    🔴 **凡測試需要「真的把某支 .sh 跑起來」，一律用本函式取得直譯器，不得直接把
    字面值 `"bash"` 當 argv[0] 交給 `subprocess`**（`tools/tests/
    test_bash_probe_spec_contract.py::TestNoBareBashInvocationInToolsTests` 機械掃描
    守護）。理由：Windows 上 `subprocess` 以 `CreateProcess(lpApplicationName=NULL)`
    解析裸名，搜尋順序「應用程式目錄 → 當前目錄 → **System32** → Windows 目錄 →
    **PATH**」——`C:\\Windows\\System32\\bash.exe`（WSL 啟動器）必先命中真 Git Bash。
    未裝發行版時該啟動器 `exit 1` 令腳本一行未跑卻被讀成「腳本回了非預期 rc」；裝了
    發行版則悄悄把 repo 腳本送進 Linux 真的跑起來，無錯誤訊息、無非零 rc
    （DEF-101-753；`shutil.which("bash")` 同樣不安全，缺 System32 排除段）。

    解析順序（與 `AISDLC_SDD/scripts/bash_probe.py::usable_bash()` 生產端同構）：
    **git 相鄰的 bash 優先**（隨 git 安裝、必為真 Git Bash），PATH 上的裸 bash 次之
    且須通過 System32 整段排除。每個候選以 `bash_probe_spec.PROBE_CMD` 實跑驗活
    （`echo` + `dirname` 兩段，DEF-101-275：只驗 echo 會讓缺 coreutils 的精簡版
    Git Bash 誤判為可用），第一個通過的才回傳。

    本函式收斂自 `tools/tests/` 內原本三份互相複製、排除規則不一致的 fixture
    （逐項取證、R71 對「僥倖 vs 設計」因果宣稱的訂正實測、R80 AST 正規化雜湊比對
    ＝三份逐字相同 vs 生產端兩份各自獨立）全文搬至
    `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`〈usable_bash_for_fixture
    沿革〉節。收斂後由 `test_bash_probe_spec_contract.py` 承接更硬的覆蓋（活 stub
    真解析）：System32 整段排除／子字串不誤排／缺 coreutils 拒絕／正向接受，四類
    各自的具名測試見該檔。
    """
    for cand in _bash_candidates():
        try:
            proc = subprocess.run(
                [cand, "-c", _spec.PROBE_CMD],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=20,
            )
        except Exception:  # noqa: BLE001 — 任何載具問題都只代表「這個候選不可用」
            continue
        lines = proc.stdout.splitlines()
        if (
            proc.returncode == 0
            and len(lines) >= 2
            and lines[0].strip() == _spec.PROBE_EXPECT_ECHO
            and lines[1].strip() == _spec.PROBE_EXPECT_DIRNAME
        ):
            return cand
    return None


def copy_functional_interpreter(dest: Path) -> None:
    """把目前真正在跑的直譯器複製到 dest，供測試偽裝成「健康的既有 venv」。

    只複製 exe **不夠**，兩種壞法都會讓本應測「健康」的情境誤判成「不健康」：
      ① Windows 的 `.venv/Scripts/python.exe` 常只是依賴同層 `pyvenv.cfg`（`home=`
         指回真正安裝目錄）的轉導 stub ⇒ 必須一併複製 pyvenv.cfg 並維持同層相對
         位置（dest 上一層）；
      ② sys.executable 本身不在 venv 內時，複製出的 exe 旁沒有相依 DLL ⇒ 從 exe
         同層 glob `python3*.dll`／`vcruntime140*.dll` 一併帶走（DEF-101-256）。
    ② 刻意**無條件**執行、不做 `if is_windows()` 分支：POSIX 上 glob 自然空手＝天生
    no-op，加分支反而製造 R19/R20 QA 抓過的「條件寫反卻從未被執行到」形態；也刻意用
    具名 glob 而非裸 `*.dll`（避免誤複製 sqlite3/libssl/tcl-tk，徒增 I/O 與鎖檔風險）。
    兩種壞法的實測 rc 與立案原文＝`docs/06_quality/CrossPlatform_R89_Closure_Evidence.md`。
    """
    shutil.copy(sys.executable, dest)
    src_cfg = Path(sys.executable).resolve().parent.parent / "pyvenv.cfg"
    if src_cfg.is_file():
        shutil.copy(src_cfg, dest.parent.parent / "pyvenv.cfg")

    # DLL 來源目錄變數與上面 pyvenv.cfg 分支的 src_cfg 目錄變數完全分開、
    # 獨立命名（SD 指出的關鍵風險：混用同一個 `.parent.parent` 表達式會
    # 讓 glob 恆空，看起來改了程式碼但實際上什麼都沒複製到，比現狀更
    # 隱蔽的退化）——DLL 與 exe 本體同層，用 exe 本身的 `.parent`，
    # 不是 venv 根目錄層級的 `.parent.parent`。
    interpreter_dll_dir = Path(sys.executable).parent
    for dll_pattern in ("python3*.dll", "vcruntime140*.dll"):
        for dll_src in interpreter_dll_dir.glob(dll_pattern):
            shutil.copy(dll_src, dest.parent / dll_src.name)


def create_symlink_or_skip(
    test_case: unittest.TestCase,
    link_path: Path,
    target: Path,
    *,
    target_is_directory: bool = False,
) -> None:
    """建立測試用 symlink；本機無權限（Windows 未開發者模式/非管理者，WinError 1314）
    時 skipTest 而非算失敗。

    這是測試 fixture 本身的前置需求做不到，不是 production 邏輯需要建立 symlink
    的權限（production 只需偵測/清除既有 symlink，不需要建立）。
    """
    try:
        link_path.symlink_to(target, target_is_directory=target_is_directory)
    except OSError as e:
        test_case.skipTest(
            f"[ENV-DISABLED] 本機無建立 symlink 權限（{e}），略過 symlink 情境。"
            "🔴 R81 包 F 實查（不是推測）：Developer Mode 未開啟"
            "（HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\AppModelUnlock 的 "
            "AllowDevelopmentWithoutDevLicense 為空）、token 內無 "
            "SeCreateSymbolicLinkPrivilege ⇒ 這是**未啟用**不是缺件。"
            "開法：設定 → 系統 → 開發人員專用 → 開發人員模式（需系統管理員；"
            "本輪執行環境 IsAdmin=False，故未代開），開完重開 session 本 skip 即消失。"
            "🔴 junction 不是替代品：本機實測 `_winapi.CreateJunction` 建得起來，但 "
            "`Path.is_symlink()` 對它回 False ⇒ 拿它頂替會讓斷言測到別的東西"
        )


# PowerShell 子行程輸出編碼的 UTF-8 前置（DEF-101-350／DEF-101-760 同一修法）。
#
# WHY 需要它：PowerShell 寫進 pipe 的位元組編碼＝`[Console]::OutputEncoding`，預設值
# 是**主控台 output code page**（繁中 Windows＝950/Big5），不是 UTF-8，含中文或
# `❌`（U+274C）的輸出以 `encoding="utf-8"` 解碼即成亂碼／`?`。`chcp` 是行程外共用
# 狀態，靠較早測試切過 65001 沾光不是自足的綠 ⇒ 每個呼叫端自帶前置。
#
# WHY 只准有一種寫法（R71，第①類收納物）：R71 曾抄出第 4 種寫法，理由是「避免 BOM」，
# 但單變因實測（真機比對 stdout 原始位元組）證明三種既有寫法輸出逐位元組相同、BOM
# 一次都沒出現——那條理由不成立，分歧沒有實益卻會獨立漂移。取既有多數寫法為唯一
# 形態，實測數據與逐版沿革全文搬至
# `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`〈PS_UTF8_PRELUDE 沿革〉節；
# 一致性由 `test_dev_start.py::TestPsUtf8PreludeIsSingleSpelling` 守護。
PS_UTF8_PRELUDE = "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "


def ps_utf8_command(snippet: str) -> str:
    """把 PowerShell 片段包成「輸出編碼已釘成 UTF-8」的 `-Command` 引數字串。

    🔴 凡測試要斷言 PowerShell 子行程 stdout 的**非 ASCII 內容**，一律用本函式組
    `-Command` 引數，不要在呼叫端行內再抄一次前置——抄第 N 份就會長出第 N 種寫法
    （R71 實例與量測見上方 `PS_UTF8_PRELUDE` 註解）。
    """
    return PS_UTF8_PRELUDE + snippet


# `#` 只在引號外、且位於行首或這些字元之後才算註解起點（避免誤剝 `$#`、`c#`）。
#
# R57 round 3：原集合漏掉右括號類與引號類收尾字元，使「功能碼後緊接 `#`」的五種
# 真實 PowerShell 註解形態不被剝除（ground truth＝pwsh 7 parser 的 Comment token；
# 對照組 `c#`／`$#` 等現行設計要保護的情形不受影響，64 案差分實測 FAIL_CLOSED=0）。
# round 4 訂正「為什麼安全」的理由：保護來源是 command/argument（bareword）解析
# 模式（bareword 本身可含 `#`），不是「前一字元是字母／`$`」——同一個 `$x#c` 在
# expression 模式下 `#` 就是註解，原理由與 PowerShell 真實規則不等價。bug-injection
# 與全語料實掃（137 支 `.ps1`、2,847 個真 Comment token，現況洩漏數 0）等逐項量測
# 全文搬至 `docs/06_quality/CrossPlatform_R104_Scan_Findings.md`〈_PS_COMMENT_LEAD
# 沿革〉節；已知不涵蓋的第 5 條見 `strip_ps_comments` docstring。
_PS_COMMENT_LEAD = " \t;|({,)}]\"'"
# here-string 起始 token（`@"`／`@'`）只在行首或這些「分隔語境」之後才成立。
# R57 A-R57R2-02：舊版只用 `re.search(r'@(["\'])\s*$', line)` 比對整行行尾，
# `Write-Host "user@"` 這種「普通字串字面值恰以 @ 結尾」即誤開 here-string，
# 而終止條件 `"@` 幾乎不會出現 → 其後整份檔案停止剝註解（latent fail-open）。
_PS_HERE_STRING_LEAD = " \t=(,;|{"


def _scan_ps_line(line: str, in_block: bool) -> tuple[str, bool, str | None]:
    """單行掃描器：回傳 (剝除註解後保留的片段, 行末是否仍在 `<#…#>` 內, here-string 起始引號)。

    逐字元掃描而非正則，因此**引號感知**貫穿三種註解形態：行內 `#`、區塊
    `<#…#>`、here-string 起始偵測都只在「引號外」才成立（R57 R57R2-QA-01：舊版
    區塊註解用 `re.sub(r"<#.*?#>", "", text, DOTALL)` 不具引號感知，
    `$x = "<# not a comment #>"` 會被吃成 `$x = ""`，且 `$a = "<#"` 會讓其後功能碼
    整段消失）。PowerShell 引號規則：單引號內無跳脫（`''`＝字面單引號）；雙引號
    內以反引號跳脫（`""` 亦為字面雙引號）。
    """
    out: list[str] = []
    i, n = 0, len(line)
    while i < n:
        if in_block:
            end = line.find("#>", i)
            if end == -1:
                return "".join(out), True, None
            i, in_block = end + 2, False
            continue
        ch = line[i]
        if ch in "'\"":  # 字串字面值整段原樣保留（黑名單比對要看字串內容）
            start, quote, i = i, ch, i + 1
            while i < n:
                if quote == '"' and line[i] == "`":
                    i += 2
                    continue
                if line[i] == quote:
                    if i + 1 < n and line[i + 1] == quote:
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append(line[start:i])
            continue
        if (
            ch == "@"
            and i + 1 < n
            and line[i + 1] in "\"'"
            and not line[i + 2 :].strip()
            and (i == 0 or line[i - 1] in _PS_HERE_STRING_LEAD)
        ):
            return "".join(out) + line[i:], in_block, line[i + 1]
        if line.startswith("<#", i):
            i, in_block = i + 2, True
            continue
        if ch == "#" and (i == 0 or line[i - 1] in _PS_COMMENT_LEAD):
            return "".join(out), False, None
        out.append(ch)
        i += 1
    return "".join(out), in_block, None


def cut_ps_inline_comment(line: str) -> str:
    """單行：切掉引號外的註解，**保留**字串字面值內容（`strip_ps_comments` 的單行版）。

    刻意不比照 `test_ps51_compat.split_code_comment`（它把字串抹成等長空白）：
    呼叫端的 `bin\\bash.exe`／`"nightly_latest.log"` 等黑名單／錨點比對要看的正是
    字串字面值內容，抹掉即失效。本函式**不帶跨行狀態**（區塊註解只在同一行內閉合
    才處理乾淨）；要正確處理跨行 `<#…#>` 與 here-string 請用 `strip_ps_comments`。
    """
    return _scan_ps_line(line, False)[0]


def strip_ps_comments(text: str) -> str:
    """剝除 PowerShell 註解後回傳「只剩功能碼」的文字（保留字串字面值內容）。

    供「錨點只認功能碼」的靜態鎖使用：註解裡留著舊字樣會讓錨點假陽性（真刪功能碼
    卻全綠）。空行一律濾除。

    **已實測涵蓋**（逐項有回歸測試，見 `test_find_git_bash_parity.py` 的
    `StripPsCommentsTest`／`StripPsCommentsBoundaryTest`）：整行 `#` 註解、尾隨行內
    註解（**前導字元集合＝`_PS_COMMENT_LEAD`：空白／tab／`;`／`|`／`(`／`{`／`,`／
    `)`／`}`／`]`／`"`／`'`**——R57 round 3 SD-R57R3-01 以 pwsh 真 parser 取
    ground truth 後補上後五個；措辭刻意改為明列集合而非籠統的「尾隨行內註解」，
    因為後者曾把「以 `)` 收尾的功能碼後的 `#`」也涵蓋進宣稱而與實作不符）、
    跨行與單行內聯 `<#…#>` 區塊註解、單/雙引號字串內的 `#` 與 `<#`／`#>` 不
    誤剝（含 `''`／`""` 雙寫跳脫、反引號跳脫）、反引號跳脫的 `` `# ``、`$#`／`c#`
    這類無前置分隔的 `#` 不誤剝、here-string（`@"`／`@'` 起、`"@`／`'@` 止）整段
    原樣保留、字串字面值以 `@` 結尾（`"user@"`）不誤開 here-string、註解內容以
    `@"` 結尾不誤開 here-string。

    **已知不涵蓋**（逐項實測確認為現行行為，不做全備宣稱；下列形態在本 repo 掃描
    面即 137 支 git 追蹤 `.ps1` 內實掃皆不存在）：
      1. 跨行字串（雙引號字串內含真換行）第二行起的引號狀態不追蹤，該情形下字串
         內的 `#` 可能被誤剝。
      2. stop-parsing 符號 `--%`：其後所有內容原樣傳給原生指令、`#` 不是註解，本
         函式仍會剝除（R57 A-R57R2-04）。**刻意不修**：`--%` 之後不剝＝多留一段
         「其實是註解」的文字當功能碼，等於在鎖上開一條新的 fail-open（本輪
         A-R57R2-02／R57R2-QA-01 修的正是這一類）；反之現行的多剝只會造成假紅
         （fail-closed）。真出現 `--%` 用法時再連同回歸測試一起處理。
      3. `<#` 出現在**未閉合**的字串字面值中（如 `$x = "<# …` 該行無閉合引號）時，
         引號掃描會吃到行尾，`<#` 不被視為區塊起始。
      4. here-string 終止判定較 PowerShell 寬鬆：本函式亦接受縮排後的 `"@`
         （`ln.strip() == '"@'`），PowerShell 只認行首。方向為提早結束＝多剝
         （fail-closed）。
      5. **不在 `_PS_COMMENT_LEAD` 內的前導字元**後的 `#` 一律不視為註解起點。
         **這不是「未來可能」的風險，而是現行、已量測的結構性限制**（R57 round 4
         Architect／SD 交叉實測後改述）：真實規則是 tokenizer 的 command/argument
         對 expression **模式相依**，前導字元白名單原理上不可能完備——expression
         模式下 `#` 幾乎恆為 token 終止＋註解起點，前導字元可以是任意數字／識別字／
         `::`／`]$var`…。Architect 以 pwsh 7.6.3 真 parser 對 64 個實務形態差分得
         **FAIL_OPEN=27**（其中 **20 案 parseErrors=0** ＝完全合法的日常寫法，如
         `$a = 1#c`、`$env:PATH#c`、`$a = [int]$b#c`、`$a = $b?.Length#c`）、
         **FAIL_CLOSED=0**；SD 另以約 130 條探針得 FAIL_OPEN=37，並實證仍可用
         `$note = $x#  -WakeToRun` 繞過 `test_windows_nightly_anchor_parity.py`
         （round 3 修掉的 `Write-Output "note"#…` 手法已確認關閉）。
         **方向為 fail-open**（漏剝＝註解冒充功能碼），故必須明確揭露而非淡化。
         **不在 R57 修的理由**：全語料實測洩漏數為 **0**（137 支 `.ps1`／2,847 個真
         Comment token，Architect 與 SD 各自獨立差分皆得 0），屬 latent；真正的修法
         是換模型——**建議（R59 改派：原寫「R58 建議」，R58 整輪作廢故無承接者；改派為 R60 起未指派 backlog，見帳本 DEF-101-521）**把 pwsh parser 對全語料的 Comment token 凍結成 golden
         fixture 做離線差分，可在 CI 不裝 pwsh 的前提下把 ground truth 機械化，一次
         消掉整個天花板（同法亦可解 `_ci_scan_anchors.py` 判例第 (3) 條的同型天花板）。
         **切勿再往集合裡補字元**——那是 whack-a-mole，本條存在正是為了阻止它。
      6. `_PS_HERE_STRING_LEAD`（`" \t=(,;|{"`）同樣未含 `]`／`)`，故
         `[string]@"` 這類以 `]` 收尾的 here-string 起始不被辨識。方向為多剝
         （fail-closed，不影響鎖的正確性），本輪一併登記不修（SD-R57R3-01 第 4 點）。
    """
    out: list[str] = []
    here_delim: str | None = None
    in_block = False
    for ln in text.splitlines():
        if here_delim is not None:  # here-string 內文原樣保留，不剝任何東西
            out.append(ln)
            if ln.startswith(here_delim + "@") or ln.strip() == here_delim + "@":
                here_delim = None
            continue
        cut, in_block, here_delim = _scan_ps_line(ln, in_block)
        if cut != ln:  # 只在真的切掉東西時 rstrip，未命中的行原樣保留
            cut = cut.rstrip()
        out.append(cut)
    return "\n".join(ln for ln in out if ln.strip())
