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


def usable_bash_for_fixture() -> str | None:
    """回傳一支**真的能跑 repo bash 腳本**的 bash 路徑；一支都探不到回 `None`。

    🔴 **凡測試需要「真的把某支 .sh 跑起來」，一律用本函式取得直譯器，不得直接把
    字面值 `"bash"` 當 argv[0] 交給 `subprocess`**（`tools/tests/
    test_bash_probe_spec_contract.py::TestNoBareBashInvocationInToolsTests` 機械掃描
    守護）。理由**不是**「PATH 順序可能讓 WSL 排在前面」，而是更硬的一條：Windows
    上 `subprocess` 以 `CreateProcess(lpApplicationName=NULL)` 解析裸名，其搜尋順序
    是「應用程式目錄 → 當前目錄 → **System32** → Windows 目錄 → **PATH**」——
    **System32 排在 PATH 之前**。於是只要 argv[0] 是裸名，`C:\\Windows\\System32\\
    bash.exe`（WSL 啟動器）就**必定**先命中，PATH 上排多前面的 Git Bash 都救不了。
    未安裝發行版時它以 **UTF-16LE** 印
    `Windows Subsystem for Linux has no installed distributions.` 並 `exit 1`，
    受測腳本一行都沒被執行，測試看到的卻是「腳本回了非預期 rc」＝**歸因完全錯誤**
    的紅燈（DEF-101-753：R69 收輪 push 後由雲端 windows-compat-ci 抓到）。

    **同一次 CI run 內就有對照組可證此機制**（run 30739865214）：
    `test_dev_start.TestPickPythonGeMin` 用的是 `shutil.which("bash")`（只查 PATH）
    ⇒ 拿到真 Git Bash、全數通過；`test_smoke_ci_sync` 用的是字面值 `"bash"`
    ⇒ 拿到 WSL、三支全紅。**同一台機器、同一個 PATH，兩種解析路徑結果相反**，
    這排除了「PATH 上沒有 Git Bash」這個解釋。推論：唯一安全的用法是 argv[0] 給
    **絕對路徑**——這正是本函式的回傳值。`shutil.which("bash")` 雖能避開
    CreateProcess 的 System32 優先，但它沒有 System32 段排除，在「WSL 佔位版確實排
    在 Git Bash 之前」的開發機（DEF-101-617 已記載該機型）仍會回 WSL，故一併不用。

    解析順序（與 `AISDLC_SDD/scripts/bash_probe.py::usable_bash()` 生產端同構）：
    **git 相鄰的 bash 優先**（隨 git 安裝、必為真 Git Bash），PATH 上的裸 bash 次之
    且須通過 System32 整段排除。每個候選以 `bash_probe_spec.PROBE_CMD` 實跑驗活
    （`echo` + `dirname` 兩段，DEF-101-275：只驗 echo 會讓缺 coreutils 的精簡版
    Git Bash 誤判為可用），第一個通過的才回傳。

    **為何住在本檔**：本函式是第①類收納物（測試 fixture 對開發者本機環境的隱性
    假設）。收斂前 `tools/tests/` 內有兩份 fixture 用途的複本
    （`test_bash_probe_spec_contract._probe_a_real_usable_bash_for_fixture` 與
    `test_macos_smoke_skip_honesty._usable_bash`），且**兩份的排除規則並不一致**
    ——後者對裸 bash 完全沒有 System32 排除，只是恰好因為驗活會失敗才沒出事
    （fail-closed 的僥倖，不是設計）。這正是本檔 docstring 第②類判準所描述的
    「同一盲點被抄 N 遍」形態，故比照 R57 `strip_ps_comments` 判例收斂為一份。

    **刻意不收斂的兩份**：`test_pre_push_dispatcher._usable_bash()` 與
    `test_git_hooks_install_common._usable_bash()` 是**生產端探針的獨立重寫回歸鎖**
    （見 `tools/lib/bash_probe_spec.py` docstring），其獨立性本身就是鑑別力來源
    ——共用函式會讓它們與被測對象同時失效。本函式與它們的差別是**用途**：本函式
    要的是「給我一支能跑的 bash」，它們要的是「驗證探測規則本身」。
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
    for cand in candidates:
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

    真實 Windows 機器踩到的落差（tools/tests 首次真跑於本機 venv-launcher
    佈局才顯形，Mock/CI 環境不重現）：Windows 上（尤其 uv/`python -m venv`
    建立的 `.venv/Scripts/python.exe`）sys.executable 常是依賴同層
    `pyvenv.cfg`（記錄 `home=` 指回真正安裝目錄）才能運作的轉導 stub，並非
    完整直譯器本體；只複製這個 exe、不帶走 pyvenv.cfg，會得到一個檔案存在
    但 subprocess 執行 rc=106（"No pyvenv.cfg file"）的壞掉直譯器，讓本應
    測「健康」情境的測試誤判為「不健康」。一併複製 pyvenv.cfg（若源頭存在）
    並維持同層相對位置（dest 上一層），讓複製後的直譯器仍可正確解析 home=。

    R21 四方一審（Architect/SA/SD/QA）追加（DEF-101-256）：當 sys.executable
    本身**不是**透過 venv 執行時（任何未啟用 venv 的官方支援直譯器安裝
    路徑皆會命中同一情境——pyenv-win、winget／python.org 安裝器版型，見
    ONBOARDING.md §1；uv 管理的直譯器因走上面 pyvenv.cfg 分支已被涵蓋），
    複製出的直譯器旁邊沒有同層相依 DLL（`python3*.dll`／`vcruntime140*.dll`），
    在 Windows 上啟動會因 STATUS_DLL_NOT_FOUND（0xC0000135）失敗
    （rc=3221225781）。修法無條件（不做任何 `if is_windows()` 平台分支）
    從 exe 本身同層 glob 具名 DLL pattern 並複製到 dest 同層——macOS/Linux
    上 sys.executable 同層通常沒有 `.dll` 副檔名檔案，glob 自然空手，本身
    即是安全的 no-op，三平台行為天生一致，不需要平台條件判斷（避開
    R19/R20 QA 抓到過的「條件分支寫反/從未真正執行卻沒人發現」風險形態）。
    刻意使用具名 glob pattern（非裸 `*.dll` 全複製）避免誤複製到
    sqlite3/libssl/tcl-tk 等不必要的 DLL（增加 I/O 與被鎖檔風險）。
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
        test_case.skipTest(f"本機無建立 symlink 權限（{e}），略過 symlink 情境")


# `#` 只在引號外、且位於行首或這些字元之後才算註解起點（避免誤剝 `$#`、`c#`）。
#
# R57 round 3 SD-R57R3-01：原集合 `" \t;|({,"` **漏掉右括號類與引號類收尾字元**，
# 使「以 `)`／`}`／`]`／`"`／`'` 結尾的功能碼後緊接的 `#`」不被視為註解起點而原樣保留
# ——「錨點只認功能碼」的鎖因此 fail-open。SD 以本機 pwsh 7 的真 PowerShell parser
# （`[System.Management.Automation.Language.Parser]::ParseInput` 取 Comment token）
# 取得 ground truth，逐條確認這五種形態在 PowerShell 中**確實都是註解**：
#     Write-Host (1)#c    if ($true) { }#c    $a[0]#c
#     Write-Host "a"#c    Write-Host 'a'#c
# 對照組 `c#`／`$#`／`Write-Host $a#b` 的 Comment token 為空，即現行 lead-char 設計要
# 保護的情形——補上這五個字元不會傷到它們（Architect round 4 以 64 案差分實測
# FAIL_CLOSED=0，零退化）。
#
# **R57 round 4 SD-R57R4-01 訂正「為什麼安全」的理由**（原寫「其前一字元是字母／`$`，
# 仍不在集合內」——該理由與 PowerShell 真實規則**不等價**，被後人採信會導向錯誤修法）：
# 真正的保護來源是 PowerShell 的 **command/argument（bareword）解析模式**——bareword
# 本身可含 `#`，與前導字元無關。同一個 `$x#c` 在 **expression 模式**下 `#` 就**是**註解
# （pwsh 7.6.3 實測：`$c#zz` → Comment@2；`$v = $x#  -WakeToRun` → Comment@7）。
# 換言之 `$` 不構成「保護類別」，lead-char 白名單只是對 parse-mode 的近似（見下方
# `strip_ps_comments` docstring「已知不涵蓋」第 5 條的完整量測與修法方向（**R59 改派**：原寫「R58 修法方向」，而 R58 整輪作廢＝指向不存在的輪次；改派為 R60 起未指派 backlog，見帳本 DEF-101-521））。
# SD 並以 bug-injection 實證可繞過：把 `tools/install_windows_nightly.ps1` 的功能碼
# `-WakeToRun` 刪除、只在 `Write-Output "note"#…-WakeToRun…` 註解裡留下字樣後，
# `test_windows_nightly_anchor_parity.py` 6 支測試**全數 OK**（負對照：不留註解則正常翻紅）。
# 全語料實掃 137 支 `.ps1` 的 2,847 個真 Comment token，現況洩漏數為 0 ⇒ 屬 latent
# fail-open，與 round 2 的 A-R57R2-02（here-string 誤判）同級同型。
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
