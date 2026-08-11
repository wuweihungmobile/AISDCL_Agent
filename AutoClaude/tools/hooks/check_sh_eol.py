#!/usr/bin/env python
r"""PostToolUse(Edit|Write) — `.sh` / `.bash` 行尾守門：擋「會被 commit 進 repo 的 CRLF」。

紀律來源：CLAUDE.md §Nightly / CI 取證紀律 #8（SD_09 W0 P0-AUDIT-31 修復項）——跨
Docker container 執行的 `.sh` 若是 CRLF，Linux bash 會噴 `$'\r': command not found`
+ syntax error，視為 P0。`.gitattributes` 的 `*.sh text eol=lf` 是事後保險，本 hook
是事中守門。

🔴 判準問的是 **git blob（repo 端內容）**，不是磁碟此刻的位元組。
WHY：`core.autocrlf=true` 的 Windows checkout 會在**取出檔案時**把 `.gitattributes`
標成 `text` 的檔案轉成 CRLF 寫進工作樹，而 `text eol=lf` 只保證「存進去是 LF」，
對「已經躺在工作樹裡的檔案」不會回頭正規化。因此「磁碟含 CR」這個判準會把
**「這個工作樹是何時 clone 的、當時 `core.autocrlf` 是什麼值」變成閘門結果**：
  · 同一個 commit，在新 clone 上一支都不擋，在 `autocrlf=true` 的舊工作樹上擋掉上百支
    ——「同一份程式碼在兩台機器上守門結論不同」本身就是判準失效的證據；
  · 被擋的檔案 repo 端本來就是 LF，作者沒做錯任何事，且多半位於 AISDLC_SDD 凍結版樹
    ——Copy-on-Evolve 鐵律禁止就地改寫，於是使用者會被要求去 dos2unix 一批
    「規則上不准動」的檔案，唯一能讓閘門變綠的動作正好是違反另一條鐵律。
紀律本意是「`.sh` **存進 repo** 時必須是 LF」，所以判準改問 repo 端：

  磁碟不含 CR                                → exit 0（絕大多數情形）
  非 LATEST 的 AISDLC_SDD 凍結版樹            → exit 0 + stderr 說明（Copy-on-Evolve 不得回改）
  git tracked 且 blob 不含 CR                → exit 0 + stderr 說明（磁碟 CRLF 係 checkout 產物）
  未追蹤／新建檔，或 blob 自己含 CR           → **exit 2 阻斷**（這才是作者當下寫進去的 CRLF）
  非 `.sh` / `.bash`                         → exit 0（射程不擴大）

跨平台：macOS/Linux 沒有 checkout 期行尾轉換，磁碟即 blob，一律在第一條就回 0，
連 `git` 都不會被呼叫；判準沒有任何一段只在 Windows 成立（`DEF-101-766` 同型教訓）。

🔴 fail-open 紅線：本 hook 在根 `.claude/settings.json` 註冊為 exit 2 **硬阻斷**，而該
檔記載過「hook 誤觸 deny 會把所有工具硬鎖死」的 P0。故 git 缺席／非 git 樹／LATEST
解析失敗／任何非預期例外**一律放行**（exit 0）並在 stderr 說明理由——寧可漏擋一次新檔
的 CRLF（CI 側行尾檢查是第二道），也不可讓守門自身的故障把整個 session 鎖死。

LATEST 版本一律問共用層 `tools/lib/sdd_latest.py`（→ SSOT
`AISDLC_SDD/scripts/sdd_version.py`）；本檔不得自帶版本 glob／regex（`DEF-101-133`）。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_AUTOCLAUDE_ROOT = Path(__file__).resolve().parents[2]
_MONOREPO_ROOT = _AUTOCLAUDE_ROOT.parent

# 🔴 R74（PKG-4 G）：解析基準由 `AutoClaude/` 上移到 **monorepo 根**。
#
# WHY：舊版以 `AutoClaude/` 為根，而 `normalize_rel_path()` 對「resolve 後不在該根底下」
# 的絕對路徑一律回 None ⇒ exit 0。於是在 monorepo 根 session 下編輯
# `tools/*.sh`／`AISDLC_SDD/**/*.sh` 時，本 hook **整支靜默失效**——`AutoClaude/` 之外的
# 每一支 .sh 都沒有事中守門，而本 hook 的立意（紀律 #8：CRLF 的 .sh 在 Linux container
# 內噴 `$'\r': command not found`，視為 P0）與檔案住在哪個子專案完全無關。
# 這正是「鎖射程只圈一個站點」的同型（`DEF-101-757`／`DEF-101-777`）：守衛存在、
# 但它看得見的範圍只有當初落地的那一棵樹。
#
# 🔴 R75 訂正（SD 複審）：**monorepo 佈局是本檔的硬前提，沒有第二條路徑**。
# 此處曾寫成「根層 tools/lib/platform_utils.py 存在 → 用 monorepo 根，否則退回
# AutoClaude 根（獨立 checkout）」，但下方緊接著就**無條件** import `platform_utils`，
# 而全庫該模組只有一份、住在根層 `tools/lib/`（Glob 實查）。也就是說要走到那條退路，
# 前提是那個 import 已經炸掉——退路永遠不會被執行到，只有註解在宣稱它存在。
# 實測（把本檔複製到一棵沒有根層 tools/lib 的假樹再跑）：
#   ModuleNotFoundError: No module named 'platform_utils'，**rc=1**。
# rc=1 而非 2 這點是刻意保留的安全性質：PostToolUse 的 1 是「非阻斷錯誤」，
# 所以缺 monorepo 佈局時本 hook 只會吵，不會把工具鎖死（同檔頭 fail-open 紅線）。
# 要真的支援獨立 AutoClaude checkout，得先讓 `platform_utils` 有可運作的降級路徑；
# 那是另一件事，不得再用一行不成立的註解代替。
# 變數名沿用 `PROJECT_ROOT`：既有單元測試以 `monkeypatch.setattr(mod, "PROJECT_ROOT", …)`
# 注入假樹，改名會讓那些測試靜默失去注入點（測試會照綠，但驗的是別的東西）。
PROJECT_ROOT = _MONOREPO_ROOT

sys.path.insert(0, str(_MONOREPO_ROOT / "tools" / "lib"))
# 本檔會被 `runpy.run_path()`（.claude/settings.json 的 shim）與
# `importlib.util.spec_from_file_location()`（單元測試）載入，兩者都**不會**把本檔所在
# 目錄放進 sys.path ⇒ 同層模組必須自己接上，否則 hook 會在 import 期炸掉。
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_path_scope import (  # noqa: E402
    repo_relative_posix as _repo_relative_posix,  # type: ignore[import-not-found]
)
from platform_utils import (  # noqa: E402
    init_utf8_streams as _init_utf8_streams,  # type: ignore[import-not-found]
)
from platform_utils import read_hook_payload  # noqa: E402,F401

SHELL_SUFFIXES = {".sh", ".bash"}

# git 子行程逾時上限：hook 掛在 PostToolUse，卡住等於卡住使用者的每一次 Edit/Write。
# 逾時被上層當成「量不出來」→ fail-open 放行。
GIT_TIMEOUT_SEC = 15


def _warn(message: str) -> None:
    """放行類訊息一律進 stderr（exit 0 不阻斷，但不可靜默——漏擋要看得見）。"""
    print(f"[check_sh_eol] {message}", file=sys.stderr)


def normalize_rel_path(file_path: str) -> Path | None:
    """payload 路徑 → 相對 PROJECT_ROOT 的 Path；不在樹內回 None（→ main 放行）。

    🔴 正規化本體住共用層 `hook_path_scope.py`（與 `enforce_docs_path.py` 同一份實作）。
    舊版直接吃 `resolve().relative_to(PROJECT_ROOT)` 的 flavour 語意：`PureWindowsPath`
    的 `relative_to` 不分大小寫、`PurePosixPath` 的分 ⇒ 在 POSIX 上只要 root 前綴大小寫
    對不上就拋 ValueError → 回 None → 本 hook **整支靜默略過**（CRLF 守衛 fail-open，
    沒有人會發現）。純字面 casefold 比對讓兩種 flavour 對同一組輸入同判決。

    回傳型別維持 `Path`：下游用到 `rel.suffix` / `rel.parts` / `PROJECT_ROOT / rel`，
    改成 str 會讓那些站點靜默改變語意。
    """
    rel_posix = _repo_relative_posix(file_path, PROJECT_ROOT)
    return None if rel_posix is None else Path(rel_posix)


def _has_cr(raw: bytes) -> bool:
    """bytes 是否含 CR。CRLF 與孤立 CR 都算——兩者在 Linux bash 下都會炸。"""
    return b"\r" in raw


def has_crlf(abs_path: Path) -> bool:
    try:
        raw = abs_path.read_bytes()
    except OSError:
        return False
    return _has_cr(raw)


def _run_git(args: list[str]) -> tuple[int, bytes]:
    """在 PROJECT_ROOT 執行 git，回傳 (rc, stdout bytes)。

    刻意**不解碼** stdout：blob 要逐 byte 驗 CR，任何文字層解碼都可能把行尾改寫掉
    （Windows 側「取數管道給假數字」同一類坑）。git 缺席／逾時直接讓例外往上拋，
    由 check_sh_eol() 統一 fail-open。

    🔴 `creationflags` 非有不可（R84 訴求 7／C1；平台中立寫法，POSIX 上 `getattr`
    兜底成 0）：本 hook 自 R80／R81 起由 **exec form** 的 `pythonw.exe` 啟動，而
    `pythonw.exe` 是 GUI 子系統程式、**沒有 console**。Windows 上一個無 console 的父
    行程去 spawn `git.exe`（console 子系統）時，OS 會**替它配一個新 console 視窗**
    ⇒ 每次 Write／Edit 到 `.sh` 就閃一次。這正是 exec form 治掉 `bash.exe` 那個彈窗
    之後**剩下的另一個彈窗來源**：載具不閃了，載具生的孫子還在閃。
    `CREATE_NO_WINDOW` 只影響「有沒有配 console」，不影響 rc／stdout ⇒ 對本函式的
    取數語意零副作用。
    """
    proc = subprocess.run(
        ["git", "-C", str(PROJECT_ROOT), *args],
        capture_output=True,
        timeout=GIT_TIMEOUT_SEC,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return proc.returncode, proc.stdout


def git_repo_available() -> bool:
    """PROJECT_ROOT 是否為可查詢的 git 工作樹（tarball／非 repo 場景回 False）。"""
    rc, _ = _run_git(["rev-parse", "--git-dir"])
    return rc == 0


def tracked_blob(rel: Path) -> bytes | None:
    """index 內該路徑的 blob bytes；未被 git 追蹤時回 None。

    `git show :<path>` 取的是 **index 內容**＝「這個檔案存進 repo 的樣子」：已套用
    `.gitattributes` 的 eol 正規化，且不受工作樹 checkout 轉換影響。這正是紀律 #8
    真正在乎的那份位元組（Docker 裡跑的是 clone 出來的檔案）。
    """
    rc, out = _run_git(["show", f":{rel.as_posix()}"])
    return out if rc == 0 else None


def frozen_sdd_version(rel: Path) -> str | None:
    """rel 位於「非 LATEST」的 AISDLC_SDD 版本樹底下 → 回該版本目錄名；否則 None。

    凍結版為何排除在阻斷面外：Copy-on-Evolve 鐵律禁止就地改寫歷史版本快照，所以對
    這些路徑「阻斷 + 要求修檔」是一個**沒有合法修法**的紅燈——守門唯一能達成的效果
    是逼人違反另一條鐵律。

    LATEST 一律問共用層 `tools/lib/sdd_latest.py`（→ SSOT `sdd_version.py`），本檔
    不自帶版本 glob／regex（`DEF-101-133`）。解析不出來時回 None（＝不做凍結分類），
    此時仍由 blob 判準把守——分類失敗不擴大阻斷面，也不放掉真違規。
    """
    parts = rel.parts
    if len(parts) < 3 or parts[0] != "AISDLC_SDD":
        return None
    try:
        from sdd_latest import (  # type: ignore[import-not-found]
            FROZEN_VERSION_DIR_RE,
            resolve_latest_name,
        )
    except ImportError:
        # 共用層不在 sys.path（例如殘缺 checkout）→ 不做凍結分類，交給 blob 判準。
        return None
    if not FROZEN_VERSION_DIR_RE.fullmatch(parts[1]):
        return None
    sdd_root = PROJECT_ROOT / "AISDLC_SDD"
    if not (sdd_root / "scripts" / "sdd_version.py").is_file():
        return None
    latest = resolve_latest_name(sdd_root)  # 失敗拋 AssertionError → 上層 fail-open
    return None if parts[1] == latest else parts[1]


def check_sh_eol(rel: Path) -> int:
    if rel.suffix.lower() not in SHELL_SUFFIXES:
        return 0
    abs_path = PROJECT_ROOT / rel
    if not abs_path.exists():
        return 0
    if not has_crlf(abs_path):
        # 絕大多數情形（含 macOS/Linux 全部情形）在此結束——不呼叫 git，零額外成本。
        return 0

    shown = rel.as_posix()
    try:
        frozen = frozen_sdd_version(rel)
        if frozen is not None:
            _warn(
                f"ALLOW: '{shown}' 磁碟含 CR，但它位於凍結版樹 {frozen}"
                f"（Copy-on-Evolve 禁止就地改寫）→ 不阻斷。"
                f" 若 repo 端真的存了 CRLF，修法是在 LATEST 版修並隨 Copy-on-Evolve 帶下去。"
            )
            return 0
        if not git_repo_available():
            _warn(
                f"ALLOW: '{shown}' 磁碟含 CR，但此處不是可查詢的 git 工作樹"
                f"（無法區分『作者寫的』與『checkout 轉的』）→ fail-open 不阻斷。"
            )
            return 0
        blob = tracked_blob(rel)
    except Exception as exc:
        _warn(
            f"ALLOW: '{shown}' 判準執行失敗 → fail-open 不阻斷"
            f"（deny 類 hook 絕不因自身故障把工具鎖死）：{exc!r}"
        )
        return 0

    if blob is not None and not _has_cr(blob):
        _warn(
            f"ALLOW: '{shown}' git blob 是 LF，磁碟上的 CRLF 是 checkout 期轉換產物"
            f"（core.autocrlf + .gitattributes text eol=lf）→ 不阻斷。"
            f" commit 進 repo 的內容仍是 LF，紀律 #8 未被破壞；要讓工作樹也變 LF 可跑"
            f" `git add --renormalize .`（非必要，不是閘門條件）。"
        )
        return 0

    if blob is None:
        cause = "尚未被 git 追蹤（新建／未 add 檔），磁碟這份位元組就是即將被 commit 的內容"
    else:
        cause = "git blob 本身就含 CR（CRLF 會真的被 commit 進 repo）"
    print(
        f"[check_sh_eol] BLOCK: '{shown}' 含 CR/CRLF 行尾——{cause}。"
        f"跨 Docker container 執行的 .sh 必須為 LF（CLAUDE.md 紀律 #8 / .gitattributes）。"
        f" 修復：編輯器改行尾為 LF 或 dos2unix 後重寫該檔。",
        file=sys.stderr,
    )
    return 2


def main() -> int:
    payload = read_hook_payload()
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or ""
    if not file_path:
        return 0

    rel = normalize_rel_path(file_path)
    if rel is None:
        return 0

    return check_sh_eol(rel)


if __name__ == "__main__":
    _init_utf8_streams()
    try:
        sys.exit(main())
    except Exception as exc:  # SystemExit 不是 Exception，正常 exit 不會被吃掉
        # fail-open 最後一道：本 hook 是 exit 2 硬阻斷，自身崩潰不得升級成「鎖死工具」。
        print(f"[check_sh_eol] ALLOW: hook 自身異常 → fail-open：{exc!r}", file=sys.stderr)
        sys.exit(0)
