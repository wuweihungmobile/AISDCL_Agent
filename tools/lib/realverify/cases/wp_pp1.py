# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-PP1（E2E-WP-63；ADR-XPLAT-004 §2.14 推送快層先行）：repo 外 `git clone --shared` 沙盒（跨磁碟機無法硬連結），故意放一個 ruff 紅檔，
真跑 `tools/git-hooks/pre-push`：快層紅 ⇒ 慢層與子專案 leg 沒啟動（輸出無其起始字樣）、rc≠0；修好 ruff 檔後快層綠，
慢層起始字樣出現（等到字樣就收掉行程，不等數十分鐘慢層跑完）。

載具：Git Bash（由 `git.exe` 位置推 `bin\\bash.exe`，不用 system32 的 WSL 佔位版）；Python／ruff 走 PATH 前綴
`<repo>/.venv/Scripts`（不建 junction：沙盒 rmtree 跟進 junction 會刪到真 .venv）。
"""

from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, kill_tree
from . import CaseContext, case
from .prd_px_lib import ev

NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FAST_RED = "快層守門未過"
SLOW_MARKS = ("執行 root-infra 慢層", "push 範圍含 AutoClaude/", "背景並行")
SLOW_START = "執行 root-infra 慢層"


def git_bash() -> str:
    g = shutil.which("git")
    if not g:
        raise EnvMissing("找不到 git")
    cand = Path(g).resolve().parent.parent / "bin" / "bash.exe"
    if not cand.is_file():
        raise EnvMissing(f"找不到 Git Bash：{cand}")
    return str(cand)


def sh(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, encoding="utf-8", errors="replace", creationflags=NOWIN, timeout=300)  # noqa: S603,S607
    if r.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} rc={r.returncode} {r.stderr[-300:]}")
    return r.stdout.strip()


def run_prepush(clone: Path, local: str, remote: str, *, stop_on: str | None, timeout: int = 900) -> tuple[int | None, str]:
    """真跑 pre-push（stdin 餵一行 push 範圍）；`stop_on` 字樣出現即收掉行程（回 rc=None）。"""
    env = {**__import__("os").environ}
    env["PATH"] = str(REPO / ".venv" / "Scripts") + ";" + env.get("PATH", "")
    env.pop("AUTOCLAUDE_SKIP_HOOKS", None)
    env["PYTHONUTF8"] = "1"
    env["AUTOSDD_ALLOW_PATH_PYTHON"] = "1"  # 沙盒 clone 沒有自己的 .venv（不建 junction）；官方人為逃生口，python 取自上面 PATH 前綴
    proc = subprocess.Popen([git_bash(), (clone / "tools" / "git-hooks" / "pre-push").as_posix(), "origin", "file:///rv"], cwd=str(clone), env=env,  # noqa: S603
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=NOWIN)
    proc.stdin.write(f"refs/heads/main {local} refs/heads/main {remote}\n".encode())
    proc.stdin.close()
    buf: list[str] = []

    def pump() -> None:
        for raw in proc.stdout:
            buf.append(raw.decode("utf-8", errors="replace"))

    th = threading.Thread(target=pump, daemon=True)
    th.start()
    t0 = time.monotonic()
    rc = None
    while time.monotonic() - t0 < timeout:
        rc = proc.poll()
        if rc is not None:
            break
        if stop_on and stop_on in "".join(buf):
            kill_tree(proc)
            rc = None
            break
        time.sleep(1)
    else:
        kill_tree(proc)
    th.join(timeout=10)
    return rc, "".join(buf)


@case("RV-PP1", "workprogress", refs=("E2E-WP-63", "REQ-WP-93", "ADR-XPLAT-004-§2.14"))
def rv_pp1(ctx: CaseContext) -> None:
    sb = ctx.sandbox(probe_hooks=False)
    clone = sb.root / "clone"
    sh(sb.root, "clone", "--shared", "--quiet", str(REPO), str(clone))
    sh(clone, "config", "user.email", "rv@example.invalid")
    sh(clone, "config", "user.name", "realverify")
    base = sh(clone, "rev-parse", "HEAD")
    red = clone / "tools" / "rv_pp1_red.py"
    red.write_text("import os\n", encoding="utf-8", newline="\n")  # F401：ruff 必紅
    sh(clone, "add", "tools/rv_pp1_red.py")
    sh(clone, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "rv: ruff red")
    head = sh(clone, "rev-parse", "HEAD")
    rc, out = run_prepush(clone, head, base, stop_on=None)
    ctx.check(rc is not None and rc != 0, f"快層紅時 pre-push 應 rc≠0：rc={rc}\n{out[-600:]}")
    ctx.check(FAST_RED in out and "ruff check" in out, f"輸出缺快層紅字樣／ruff 失敗行：\n{out[-800:]}")
    started = [m for m in SLOW_MARKS if m in out]
    ctx.check(not started, f"快層紅卻啟動了慢層／子專案 leg：{started}")
    ev(ctx, "fast_red_blocks_slow", f"rc={rc}；輸出含「{FAST_RED}」；慢層／子專案 leg 起始字樣 0 個（{SLOW_MARKS}）")
    # 修好：刪掉紅檔改成乾淨檔 ⇒ 快層綠 ⇒ 慢層起始字樣出現（等到字樣即收）
    red.write_text("X = 1\n", encoding="utf-8", newline="\n")
    sh(clone, "add", "tools/rv_pp1_red.py")
    sh(clone, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "rv: ruff fixed")
    head2 = sh(clone, "rev-parse", "HEAD")
    rc2, out2 = run_prepush(clone, head2, base, stop_on=SLOW_START)
    ctx.check(FAST_RED not in out2, f"修好後快層不該再紅：\n{out2[-800:]}")
    ctx.check(SLOW_START in out2, f"修好後快層綠應啟動慢層（等不到「{SLOW_START}」）：rc={rc2}\n{out2[-800:]}")
    ev(ctx, "fixed_starts_slow", f"修好後輸出含「{SLOW_START}」（等到即收行程，不等慢層跑完）")
