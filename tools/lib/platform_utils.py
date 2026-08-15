#!/usr/bin/env python3
"""平台判斷 + hook 腳本 I/O 初始化共用模組
（monorepo 根層共用，AutoClaude 與 AISDLC_SDD 兩側皆可用）。

收斂背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛，在 macOS/Linux 上也會無條件把 sys.stdout/stderr
換成新的 TextIOWrapper——POSIX 終端機預設已是 UTF-8，重新包裝除了改變
buffering 行為（TextIOWrapper 預設非 line-buffered）、丟棄原始 stream 物件外
沒有任何好處，是純粹的行為分歧風險。本模組以「有守衛」版本為唯一正確實作。

只依賴 stdlib：供 AutoClaude/tools/hooks/ 下的 hook 腳本以
`sys.path.insert(0, str(repo_root / "tools" / "lib"))` 方式 import——hook 腳本
執行環境不保證能 import 完整 autoclaude 套件，僅假設 stdlib + repo 根目錄可達。
"""
from __future__ import annotations

import atexit
import importlib.util
import json
import sys
from pathlib import Path


def is_windows() -> bool:
    return sys.platform == "win32"


# 供 venv_python_path() 內部呼叫的別名（R17 DEF-101-231 觀察點 1+2）：該函式的
# `is_windows` 參數名與本函式同名，函式體內 `is_windows` 一律指向參數（區域變數
# 遮蔽全域函式，Python 詞法範圍規則），故需在此另存一個不同名稱的參照才能在
# 參數為 None 時呼叫到真正的平台判斷。
_is_windows = is_windows


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_posix() -> bool:
    return sys.platform != "win32"


def os_label() -> str:
    """三態標籤：windows/mac/linux（同 tools/dev_start.py 的 `_now_label()`）。"""
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return "linux"


def venv_python_path(venv_dir: Path, is_windows: bool | None = None) -> Path:
    """venv_dir 內對應本平台的直譯器路徑：windows → Scripts/python.exe，否則 bin/python。

    收斂背景（R17 DEF-101-231 觀察點 1+2）：`tools/dev_start.py::_venv_python_at()`
    與 `tools/bootstrap_core.py::venv_python_path()` 各自獨立寫了同一款
    「Scripts/python.exe vs bin/python」判斷，本函式收斂為單一真相源。

    `is_windows` 參數為 `None`（預設）時呼叫本模組的 `is_windows()` 判斷目前執行
    平台；保留可覆寫參數是因為呼叫端（如 dev_start.py 的 venv 換手快取邏輯）需要
    針對「目標平台形狀」而非「目前執行平台」算路徑（例：判斷另一平台快取目錄內
    的直譯器是否存在），與目前程序實際執行的平台無關。
    """
    if is_windows is None:
        is_windows = _is_windows()
    return venv_dir / "Scripts" / "python.exe" if is_windows else venv_dir / "bin" / "python"


# ── 「強制 stdout/stderr 為 UTF-8」：本檔**只委派**，實作不在這裡（R75 去重）────────
#
# 🔴 缺陷本體：同一份知識先前有**兩個各自宣稱是 SSOT 的家**——本檔的
# `init_utf8_streams()`（`io.TextIOWrapper` 換掉串流、只在 `__main__` 呼叫）與
# `tools/_stdio_utf8.py::reconfigure_stdio_utf8()`（`.reconfigure()` 就地改、import 期
# 即生效），而後者的檔頭逐字自稱「本模組把該段保護收斂為單一 helper」。兩者實作／啟用
# 時機／對測試替身的行為三者皆不同，消費端分屬兩群（本檔 8 支 AutoClaude hook 與工具／
# 那支 15 支根層 tools），**換用另一支會靜默改變行為**，而兩把鎖都只守自己那一支。
# R74 的 P0（`sys.stderr` 預設 `errors='backslashreplace'` 讓 hook 中文指引在非 CJK
# codepage 降解）正好就落在這一層。
#
# 🔴 **SSOT 為何是那一支、不是本檔**（R75 第一版選反了、當回合被實測打回）：
# `tools/_stdio_utf8.py` 的既有契約**包含「被複製到別處單獨執行」**——
# `AISDLC_SDD/scripts/tests/test_copy_on_evolve.py`／`test_ntfs_length_gate.py` 會把
# `tools/check_ntfs_paths.py` 連同它複製進 tmp 沙箱 repo（**不含 `tools/lib/`**）再以
# 子行程執行。第一版把實作搬進本檔、讓那支改成 `from platform_utils import …`，於是沙箱
# 裡 import 期 `ModuleNotFoundError`、6 支測試當場紅。
# ⇒ 可搬遷性是**硬約束**，而只有自我完備的那一支能滿足它 ⇒ **自我完備的那一支就是
#   SSOT，本檔委派過去**。方向由約束決定，不是由「哪一層比較像共用層」決定。
#
# 委派刻意做成**惰性**（在函式體內解析、而非模組層 import）：本檔同時被
# `bootstrap_core`／`dev_start`／`integration_gate_core`／`snapshot_sync` 為了
# `is_windows()` 而 import，而 `_stdio_utf8` 的 import **本身就是副作用**；模組層 import
# 會讓「只想問平台」的消費者也被動手術（pytest 擷取期尤其不可）。
#
# 兩件事由 `tools/tests/test_platform_utils_dedup.py::TestR75StdioUtf8HasOneImplementation`
# 機械釘住：① 本檔不得含任何強制 stdio 的**機制**（只准委派）；② SSOT 的可搬遷契約
# （複製到 tmp 後單獨 import、以 cp1252 子行程實跑中文不降解）。


def _stdio_utf8_impl():
    """取 SSOT（`tools/_stdio_utf8.py`）的 `reconfigure_stdio_utf8`；取不到回 `None`。

    以 `importlib` 由**絕對路徑**載入並註冊進 `sys.modules["_stdio_utf8"]`，而不是
    `sys.path.insert(tools/)`：後者會把根層 `tools/` 底下十幾支 CLI 模組掛上 hook 行程的
    import 面（hook 的執行環境刻意維持最小，見本檔檔頭），且註冊進 `sys.modules` 讓之後
    任何 `import _stdio_utf8` 拿到**同一個模組物件**（否則會有兩份、各自套用一次）。
    """
    mod = sys.modules.get("_stdio_utf8")
    if mod is None:
        # 本檔住 `<repo>/tools/lib/` ⇒ parents[1] 就是 `<repo>/tools/`。
        path = Path(__file__).resolve().parents[1] / "_stdio_utf8.py"
        if not path.is_file():  # pragma: no cover - 完整 checkout 下必然存在
            return None
        try:
            spec = importlib.util.spec_from_file_location("_stdio_utf8", path)
            if spec is None or spec.loader is None:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules["_stdio_utf8"] = mod
            spec.loader.exec_module(mod)  # ← import 期即套用一次（那就是它的契約）
        except Exception:  # noqa: BLE001 — 保護性程式碼不得反過來讓呼叫端崩潰
            sys.modules.pop("_stdio_utf8", None)
            return None
    return getattr(mod, "reconfigure_stdio_utf8", None)


def init_utf8_streams() -> None:
    """把 sys.stdout/stderr 強制為 UTF-8（`errors="replace"`），不分平台。

    **公開名與呼叫契約完全不變**（8 支 AutoClaude hook／工具沿用），行為改為委派到唯一
    實作 `tools/_stdio_utf8.py::reconfigure_stdio_utf8`——三條分支（就地 reconfigure／
    wrapper 回退／安全 no-op）與 R16 訂正的完整理由都寫在該函式的 docstring，本處不複寫
    （複寫就是下一次漂移）。

    取不到 SSOT 時**靜默不動**而非拋例外：本函式的呼叫端全是 `__main__` 進入點的保護性
    前置，保護件自己把行程弄掛是最糟的失敗模式。完整 checkout 下取不到是不可能的
    （同 repo 的兄弟檔），故這條路徑沒有需要嚷嚷的情境。
    """
    impl = _stdio_utf8_impl()
    if impl is not None:
        impl()


# ── hook 的 stdin payload 讀取：**單一實作**（R81／SUB-S1-04）─────────────────────
#
# 🔴 為何併進本檔而不另開 `tools/lib/hook_payload.py`（初稿真的開過，當回合被兩件事
# 打回）：① 本檔的立案理由與本節逐字同型——「`init_utf8_streams()` 曾被複製貼上到至少
# 8 個檔案、其中 6 份漏了守衛」，而 payload 讀取器是同一個病的下一層，兩者同屬「hook
# 腳本 I/O」這個主題，不是硬塞；② `tools/lib/` 有一道掃描面下限帶，新開第 21 支檔當場
# 讓 6 支 `test_platform_neutral_paths.py` 的判準轉紅（實測），而在一個以架構減法為
# 目標的輪次裡，靠重釘別人的鎖來容納自己新增的檔是反方向的動作。消費端零額外成本：
# 那 5 支 AutoClaude hook 本來就 `from platform_utils import …`。
#
# 病本身：這份讀取器此前以手抄本住在 **7 支** hook 裡，實測已漂移成 **3 種**行為
# （4 份原樣回傳 `json.loads` 的結果／1 份回 `{}`／2 份回 `None`）。代價不是抽象的：
# `enforce_docs_path.py` 是**阻斷級** PreToolUse hook，餵它 `[1,2,3]` 或 `null` 會
# rc=1 AttributeError ⇒ 守衛還在、判定卻沒產出，而全 repo 零判準會轉紅。
#
# 兩個公開函式**不是**重複，是兩種各有消費者的契約——刻意保留而非硬統一，因為差別是
# 載重的：`lint_powershell_command` 對「讀不出來」與「讀到一個沒有 tool_name 的
# payload」印不同訊息、走不同 rc 分支（實測兩者 stderr 逐字不同）。
#
# 行為契約：**任何輸入都不得拋例外**（hook 崩潰會讓阻斷級守衛的判定靜默消失；
# `.claude/settings.json` 記載過的 P0 是「hook 誤觸 deny 會把所有工具硬鎖死」）。
# 合法 JSON object → 該 dict；空／壞 JSON／頂層非 object／stdin 讀取失敗 → 退化。
# 跨平台：純 stdlib、**零平台分支**（鐵律三）。
# 回歸鎖：`tools/tests/test_pre_commit_dispatcher_sigpipe.py::TestHookPayloadSingleHome`


def read_payload() -> dict | None:
    """讀 stdin 的 hook payload；`None`＝退化。契約見上方區塊註解。

    走 **bytes 端**再 UTF-8+replace 解碼：zh-TW Windows 的 pipe 預設 cp950，文字端
    read 遇含中文的 UTF-8 payload 會拋 UnicodeDecodeError（那次修復的回歸鎖＝
    `AutoClaude/tests/tools/hooks/test_hooks_stdin_utf8.py`）。無 `.buffer`（測試以
    StringIO 當替身）時回退文字端。
    """
    try:
        buffer = getattr(sys.stdin, "buffer", None)
        raw = (buffer.read().decode("utf-8", "replace") if buffer is not None
               else sys.stdin.read())
        # 空輸入借道 `"null"`：與「頂層非 object」走同一個出口，少一條會漂移的分支。
        payload = json.loads((raw or "").strip() or "null")
    except Exception:  # noqa: BLE001 — 任何失敗都是退化，不是崩潰（見上方的 P0）
        return None
    return payload if isinstance(payload, dict) else None


def read_hook_payload() -> dict:
    """同 `read_payload()`，但退化回 `{}`——給「拿不到就放行」的消費者。"""
    return read_payload() or {}


# ── hook → **模型 context** 的唯一發射口（R91／`DEF-200-135`）─────────────────────
#
# 病本體：hook 寫 stderr **在 exit 0 下不進模型 context**（官方契約：PostToolUse 只有
# exit 2 才把 stderr 回饋給模型）。`context_budget_guard.py` 的 75% WARN 分支正是
# `stderr + exit 0` ⇒ 模型在 75~90% 這一整帶結構上收不到任何訊號（本輪實測：1h49m／
# 45 turns 零訊號）。唯一送得進去的通道是 **stdout 上的 `hookSpecificOutput`**，而它
# 已經在 production 用了一年（`tools/lib/quota_gate.py::note_degraded`）——同一份知識
# 因此必須只有一個家（R73 `Find-GitBash` 判例），本函式就是那個家。
#
# 三條硬約束，每一條都是**實測或判例**得來的，不是風格：
#  ① **事件名由呼叫端傳，不得寫死**。R83／D3 已為同一件事下過判詞：`hookEventName` 與
#     實際事件不符時 Claude Code **直接把整個 `additionalContext` 丟掉** ⇒ 靜默失效，
#     而它的外觀與「水位很低／額度很健康」完全相同。
#  ② **`ensure_ascii=True`**。本模組層的 `reconfigure` 包在裸 `except: pass` 裡（見
#     消費端 hook 的檔頭）：reconfigure 失敗時 `ensure_ascii=False` 的 CJK 在 cp1252 上
#     會 `UnicodeEncodeError` → 被 hook `main()` 的 catch-all 吞掉 → **rc=0 靜默失聲**，
#     外觀同樣與「水位很低」相同。逃脫序列由 CC 的 JSON parser 還原，讀者端零損失。
#  ③ **一個行程至多發射一份 JSON**。額度降級通報（閂鎖 TTL 180s／per source）與 context
#     warn（閂鎖 per tier/window）**可以在同一次 hook 呼叫裡同時開火**；兩份相接的 JSON
#     物件會讓 parse 失敗 ⇒ **兩則訊息一起消失**。⇒ `emit_to_model()` 只累積、不輸出，
#     真正的輸出集中在 `flush_to_model()`，而 production 只有 `atexit` 這**一個**呼叫站點
#     （鎖＝`tools/tests/test_context_budget_guard.py::SingleEmitterHasOneFlushSiteTest`）。
#     選 `atexit` 而不是在 `main()` 裡 try/finally：`main()` 有六個 return 出口，且既有
#     接線鎖以 AST 認 `main` 這個函式名（改名會打紅它）。
_MODEL_MSGS: list[str] = []
_MODEL_EVENT = ""


def emit_to_model(event: str, msg: str) -> bool:
    """把 `msg` 排進「這個行程要送給模型的那一份 JSON」；回「有沒有被收下」。

    `event` 必須是 payload 的 `hook_event_name` 原值（見上方約束①）。第二次以後的呼叫
    **併入**同一份，事件名沿用第一次收下的那個——同一次 hook 呼叫裡兩軸的事件名必然相同，
    不同就是呼叫端傳錯了，而那時把後者丟掉比讓兩則一起消失安全。
    任何輸入都不得拋例外（hook 崩潰會讓守衛的判定靜默消失，見上方 `read_payload` 的 P0）。
    """
    global _MODEL_EVENT
    if not isinstance(event, str) or not event.strip() or not msg:
        return False
    if not _MODEL_MSGS:
        _MODEL_EVENT = event
        atexit.register(flush_to_model)
    _MODEL_MSGS.append(str(msg))
    return True


def flush_to_model() -> str:
    """把累積的訊息寫成**單一** JSON 物件到 stdout；回實際送出的文字（`""`＝沒送）。

    production 只由 `atexit` 呼叫（見上方約束③）；測試可顯式呼叫以觀測。寫失敗一律吞掉：
    送不出去最多是少一則提示，絕不可反過來變成守衛的故障源。
    """
    if not _MODEL_MSGS:
        return ""
    body = "\n".join(_MODEL_MSGS)
    _MODEL_MSGS.clear()
    try:
        sys.stdout.write(json.dumps(
            {"hookSpecificOutput": {"hookEventName": _MODEL_EVENT,
                                    "additionalContext": body}},
            ensure_ascii=True) + "\n")
        sys.stdout.flush()
    except Exception:  # noqa: BLE001 — 見 docstring 最後一句
        return ""
    return body
