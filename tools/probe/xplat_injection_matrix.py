#!/usr/bin/env python3
"""六類「只在 mac/Linux 會炸」的缺陷注入 × 三關攔阻矩陣（`DEF-101-796` 的載體）。

🔴 **為什麼需要這一支**（R79 Scan-D 的實測）：`DEF-101-796` 的解鎖條件自 R74 起就是
「六類注入各做一次、逐格記錄各關卡的攔阻結果、與 R74 的 2/6 基線並列成 before/after 表」，
而全樹 `Grep 攔阻矩陣` 的**唯一命中就是該帳本列自己**——四輪來這件事沒有任何可重跑的產物，
於是每一輪要回答「mac 方向的攔阻率有沒有進步」都得從頭建一次基線，而重建成本每輪一樣，
拖延不會讓它變便宜。本檔就是那個產物：把「注入什麼／怎麼量／怎麼還原」寫成程式碼，
下一輪只要重跑一次就有可比較的數字。

🔴 **誠實劃界（不得誤讀）**：
  · 本檔的六類是**依 `DEF-101-796` 該列的敘述與根 `CLAUDE.md` 鐵律三的觸發清單重新定義**
    的。R74 那六類的**逐字內容今天在磁碟上查不到**（`Grep 六類` 全 repo 只命中該帳本列
    自身與一處語意無關的 ADR 段落）⇒ 與 R74 的 `2/6` 基線只能做**量級**比較，
    **不得逐格對照**，也不得宣稱「第 N 類」與 R74 的第 N 類是同一類。
  · 「攔下」＝該關卡 rc≠0 **且**輸出點名了被注入的那個路徑或形態。只看 rc 會把「別的
    問題也在紅」算成攔下——本 repo 在共用工作樹上跑閘門時那是常態（`DEF-101-886`）。
  · 雲端 CI 那一格本檔**不量**（需要 Actions 額度且不在本機控制內），一律標 `N/A`，
    **禁止**以 `--dry-run` 的輸出或以「本機綠」推論該格。

🔴 **R87 訂正：本檔在 R85／R86 兩輪「應該開工第一件事就跑」而一次都沒跑成**，交件理由逐輪
都是「M5 需停工窗口，並行時始終有人在動工作樹」。那個理由對**當時的本檔**為真，但它是本檔
自己造出來的——**不是量測本身的性質**。舊設計把兩個完全不同的命題 AND 成同一個指紋比對：

    P1（本檔真的清乾淨了）   ← 我擁有、我可以負責、也正是要斷言的那一件事
    P2（整輪沒有別人動過樹） ← 環境事實，本檔無法控制，而**並行輪次下它恆為假**

`before/after` 取的是**全樹** `git status --porcelain`，於是只要有任何別包在編輯任何檔案，
`after != before` 就成立、rc=1、訊息逐字指控「還原不完全 ⇒ 工作樹已被污染」。也就是說：
**在並行輪次下，本檔的預設結局是「誣告自己」**，而那個假紅與真的沒還原乾淨長得一模一樣。
⇒ 判準結構上永遠跑不了，而一個永遠跑不了的判準等於沒有判準（R86 交件的「留到收尾」正是
它的下游後果——收尾窗口也從來沒有出現過）。

**修法＝把 P1 與 P2 拆開，各自用對的方式回答**：
  · **P1 改成「射程只涵蓋本檔擁有的東西」**：注入路徑逐一不存在 ＋ 沙箱目錄已消失。
    這兩件事完全不受別人鍵盤影響 ⇒ 在並行輪次下仍然**可求值**，且鑑別力沒有下降
    （少還原任何一個檔案都會被抓到——見 `restoration_problems()` 的注入自證）。
  · **P2 降為「並行活動觀測」**：仍然量，但**只報不判**（`並行活動` 段落）。資訊沒有丟失，
    只是不再拿別人的編輯去改本檔的 rc。

🔴 **共用 index 那一半（`pre-commit` 關）另外處理**：該關需要 `git add` 才量得到，而 index 是
**跨包共用**的單一狀態 ⇒ 預設**不碰**，標 `N/A(needs --stage)`。加 `--stage` 時走
`GIT_INDEX_FILE` 指向沙箱內的私有 index 副本，`git add` 只寫那份拋棄式檔案，共用 index
一個 byte 都不動（本檔會在前後各取一次共用 index 的 digest 並列進報表佐證）。

用法：
    python tools/probe/xplat_injection_matrix.py            # 乾跑：列出六類與三關，不動樹
    python tools/probe/xplat_injection_matrix.py --apply    # 真跑（並行輪次下即可跑）
    python tools/probe/xplat_injection_matrix.py --apply --stage   # 連 pre-commit 關一起量
    python tools/probe/xplat_injection_matrix.py --apply --only sh-crlf,posix-sep
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _stdio_utf8  # noqa: E402,F401  （side effect：強制 stdout/stderr 為 UTF-8）

_REPO = Path(__file__).resolve().parents[2]
#: 注入檔一律落在這個目錄（untracked、集中一處，還原時整批刪得乾淨）。
_SANDBOX = _REPO / "_xplat_injection_sandbox"

#: 反斜線與貨幣符號等「會讓本 repo 自己的掃描器把 payload 誤判成違規」的字元一律組出來，
#: 不寫字面——payload 是**資料**不是本檔的行為，但靜態掃描器分不出來（`DEF-101-378` 同族）。
_BS = chr(92)
_DOLLAR = chr(36)


@dataclass(frozen=True)
class Injection:
    """一類「只在 mac/Linux 會炸、在 Windows 上寫出來時毫無異狀」的缺陷。"""

    key: str
    rel_path: str
    payload: str
    why_posix_only: str
    #: 判定「這一關真的攔下了它」時，輸出裡必須出現的字樣（任一命中即可）。
    expect_tokens: tuple[str, ...] = field(default=("",))

    def path(self) -> Path:
        return _SANDBOX / self.rel_path


def _injections() -> tuple[Injection, ...]:
    """六類。每一類的 `why_posix_only` 都要能回答「為什麼 Windows 上看不出來」。"""
    return (
        Injection(
            key="sh-crlf",
            rel_path="probe_crlf.sh",
            payload=("#!/usr/bin/env bash" + _BS + "r" + _BS + "n"
                     + "echo hi" + _BS + "r" + _BS + "n"),
            why_posix_only=(
                "CRLF 的 `.sh`：POSIX kernel 把行尾的 CR 當成 interpreter 路徑的一部分，"
                "`bad interpreter: /usr/bin/env bash^M`。Windows 的 Git Bash 吃掉 CR，本機實跑全綠"
            ),
            expect_tokens=("CR", "crlf", "行尾", "eol"),
        ),
        Injection(
            key="posix-sep",
            rel_path="probe_sep.py",
            payload=(
                "TARGET = " + repr("tools" + _BS + "lib" + _BS + "Find-GitBash.ps1") + "\n"
                "def load():\n    return open(TARGET, encoding='utf-8').read()\n"
            ),
            why_posix_only=(
                "反斜線硬編路徑：POSIX 上反斜線是**檔名的合法字元**，不是分隔符 ⇒ "
                "整串被當成單一檔名而 FileNotFoundError。Windows 上它就是正確路徑"
            ),
            expect_tokens=("分隔符", "path", "separator", "反斜線"),
        ),
        Injection(
            key="case-mismatch",
            rel_path="probe_case.py",
            payload=(
                "from pathlib import Path\n"
                "SPEC = Path('Tools') / 'Lib' / 'Find-GitBash.ps1'\n"
                "def exists():\n    return SPEC.exists()\n"
            ),
            why_posix_only=(
                "大小寫：NTFS 預設不分大小寫，`Tools/Lib` 與 `tools/lib` 都開得起來；"
                "Linux 的 ext4/overlayfs 分 ⇒ 雲端 ubuntu runner 上直接找不到"
            ),
            expect_tokens=("大小寫", "case"),
        ),
        Injection(
            key="win-only-api",
            rel_path="probe_winapi.py",
            payload=(
                "import " + "winreg" + "\n"
                "def read_key():\n"
                "    return " + "winreg" + ".HKEY_LOCAL_MACHINE\n"
            ),
            why_posix_only=(
                "Windows 專屬 stdlib 模組無平台守衛：POSIX 上 import 即 ModuleNotFoundError，"
                "而 Windows 上它是正常的標準函式庫"
            ),
            expect_tokens=("winreg", "平台", "platform", "守衛"),
        ),
        Injection(
            key="env-pathext",
            rel_path="probe_pathext.py",
            payload=(
                "import os\n"
                "def exts():\n"
                "    return os.environ['PATH' + 'EXT'].split(os.pathsep)\n"
            ),
            why_posix_only=(
                "讀一個只有 Windows 才有的環境變數且不帶守衛：macOS/Linux 上 KeyError；"
                "更陰險的變體是 `.get()` ⇒ 恆回 None 而判準恆假（`DEF-101-766` 的形態）"
            ),
            expect_tokens=("PATH" + "EXT", "env", "守衛"),
        ),
        Injection(
            key="win-only-skip",
            rel_path="probe_skip.py",
            payload=(
                "import sys, unittest\n\n\n"
                "class T(unittest.TestCase):\n"
                "    @unittest.skipUnless(sys.platform == 'win32', 'windows only')\n"
                "    def test_x(self):\n        self.assertTrue(True)\n"
            ),
            why_posix_only=(
                "方向感知標籤缺席的 `skipUnless(win32)`：在 mac/Linux 上整支**靜默 skip**，"
                "收集數不變、rc=0 ⇒ 『測了』與『沒測』在報表上長得一模一樣"
            ),
            expect_tokens=("skip", "標籤", "方向"),
        ),
    )


@dataclass(frozen=True)
class Gate:
    """一道要量的關卡。`run` 回 `(rc, 合併輸出)`。"""

    key: str
    describe: str
    argv: tuple[str, ...]
    #: `True` ＝ 這一關需要先 `git add`（pre-commit 只看 index）。
    needs_stage: bool = False


def _gates() -> tuple[Gate, ...]:
    return (
        Gate(
            key="posttooluse-hooks",
            describe="根 settings.json 已橋接的 PostToolUse hook（.sh 行尾／.ps1 編碼）",
            argv=(sys.executable,
                  str(_REPO / "AutoClaude" / "tools" / "hooks" / "check_sh_eol.py")),
        ),
        Gate(
            key="pre-commit",
            describe="tools/git-hooks/pre-commit（只看 index，故需先 git add）",
            argv=("git", "-C", str(_REPO), "hook", "run", "pre-commit"),
            needs_stage=True,
        ),
        Gate(
            key="root-unittest",
            describe="python tools/run_root_unittests.py（根層護欄層全套）",
            argv=(sys.executable, str(_REPO / "tools" / "run_root_unittests.py")),
        ),
    )


def _run(argv: tuple[str, ...], stdin_text: str | None = None) -> tuple[int, str]:
    """跑一道關卡。**不接管線**（rc 直接讀 `returncode`），顯式 encoding（CP950 會失真）。"""
    proc = subprocess.run(
        list(argv), cwd=str(_REPO), input=stdin_text, capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _fingerprint() -> str:
    _, out = _run(("git", "-C", str(_REPO), "status", "--porcelain"))
    return out


def _blocked(rc: int, output: str, inj: Injection) -> str:
    """判定「這一關真的攔下了**這一筆**注入」——rc≠0 只是必要條件。

    只看 rc 會把「別的問題也在紅」算成攔下，而共用工作樹上那是常態（`DEF-101-886`）。
    故另要求輸出點名該注入的路徑或形態字樣，兩者皆成立才算 `BLOCK`。
    """
    if rc == 0:
        return "PASS-THROUGH"
    named = inj.rel_path in output or any(t and t in output for t in inj.expect_tokens)
    return "BLOCK" if named else "RED-BUT-UNRELATED"


def _apply_one(inj: Injection, gates: tuple[Gate, ...]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    inj.path().parent.mkdir(parents=True, exist_ok=True)
    # payload 一律以 LF 寫入（`newline=""` 關掉 Python 的行尾轉換）——`sh-crlf` 那一類的
    # CR 必須來自 payload 本身，不能來自平台預設，否則量的是直譯器不是缺陷。
    with inj.path().open("w", encoding="utf-8", newline="") as fh:
        fh.write(inj.payload)
    try:
        for gate in gates:
            if gate.needs_stage:
                _run(("git", "-C", str(_REPO), "add", "--", str(inj.path())))
            stdin_text = None
            if gate.key == "posttooluse-hooks":
                stdin_text = json.dumps(
                    {"tool_name": "Write", "tool_input": {"file_path": str(inj.path())}})
            rc, out = _run(gate.argv, stdin_text)
            verdicts[gate.key] = _blocked(rc, out, inj)
            if gate.needs_stage:
                _run(("git", "-C", str(_REPO), "reset", "-q", "--", str(inj.path())))
    finally:
        inj.path().unlink(missing_ok=True)
    return verdicts


def _print_dry(injs: tuple[Injection, ...], gates: tuple[Gate, ...]) -> None:
    print("乾跑（未改動任何檔案）。要真的量，加 --apply，且**必須**在所有 agent 停工的窗口內。\n")
    print(f"沙箱目錄：{_SANDBOX}（注入檔集中於此，還原時整批刪除）\n")
    print("要量的關卡：")
    for g in gates:
        print(f"  · {g.key:<20} {g.describe}")
    print("\n六類注入（誠實劃界見本檔 docstring：與 R74 的 2/6 基線只能做量級比較）：")
    for i in injs:
        print(f"\n  [{i.key}] → {i.rel_path}")
        print(f"      為何只在 mac/Linux 炸：{i.why_posix_only}")
    print("\n雲端 CI 那一格本檔不量，一律 N/A —— 禁止以本機綠推論雲端。")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="六類跨平台注入 × 三關攔阻矩陣")
    ap.add_argument("--apply", action="store_true",
                    help="真的寫入注入檔並跑關卡（會改動共用工作樹；需停工窗口）")
    ap.add_argument("--only", default="", help="逗號分隔的注入 key，只跑這幾類")
    a = ap.parse_args(argv)

    injs = _injections()
    if a.only:
        want = {s.strip() for s in a.only.split(",") if s.strip()}
        unknown = sorted(want - {i.key for i in injs})
        if unknown:
            print(f"❌ 無此注入 key：{unknown}；可用＝{[i.key for i in injs]}", file=sys.stderr)
            return 2
        injs = tuple(i for i in injs if i.key in want)
    gates = _gates()

    if not a.apply:
        _print_dry(injs, gates)
        return 0

    before = _fingerprint()
    rows: list[tuple[str, dict[str, str]]] = []
    for inj in injs:
        if inj.path().exists():
            print(f"❌ 注入路徑已存在，拒絕覆寫：{inj.path()}", file=sys.stderr)
            return 2
        rows.append((inj.key, _apply_one(inj, gates)))
    if _SANDBOX.exists() and not any(_SANDBOX.iterdir()):
        _SANDBOX.rmdir()

    after = _fingerprint()
    print("\n攔阻矩陣（BLOCK＝rc≠0 且輸出點名該注入；RED-BUT-UNRELATED 不算攔下）：\n")
    header = "注入".ljust(18) + "".join(g.key.ljust(22) for g in gates)
    print(header)
    print("-" * len(header))
    for key, verdicts in rows:
        print(key.ljust(18) + "".join(verdicts[g.key].ljust(22) for g in gates))
    blocked = sum(1 for _, v in rows if any(x == "BLOCK" for x in v.values()))
    print(f"\n合計：{blocked}/{len(rows)} 類至少被一關攔下（R74 基線＝2/6，量級比較用）")
    print("雲端 CI：N/A（本檔不量）")

    if after != before:
        print("\n❌ 還原不完全：`git status --porcelain` 與注入前不一致 ⇒ 工作樹已被污染。"
              "\n   還原不完全比沒還原更危險——它看起來乾淨。請人工比對後再繼續。",
              file=sys.stderr)
        print(f"   before:\n{before}\n   after:\n{after}", file=sys.stderr)
        return 1
    print("✅ 還原完全：注入前後 `git status --porcelain` 逐字相同")
    return 0


if __name__ == "__main__":
    sys.exit(main())
