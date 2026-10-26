"""SelfImproving `check` 唯一的子行程出口：環境被淨化的 `git`（TCS-SelfImproving-P0 R8 (c)）。

每個呼叫一律 `subprocess.run`、`shell` 不為真、argv 以 `git -C <repo>` 起頭、帶 timeout
與 UTF-8 解碼；列舉路徑的呼叫另帶 `-c core.quotepath=false`。git 不可用（找不到執行檔、
不是工作樹、逾時）一律回 None／False，由呼叫端判成 blocking NE，不以預設值頂替。
console-free：SessionStart 簡報（`session_brief.si_status_line`）在 pythonw 載具下呼叫本類，
spawn 不帶 `CREATE_NO_WINDOW` 時 Windows 每次開視窗都閃一個黑框；POSIX 上該常數不存在、取 0。
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_STRIP_ENV = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)
_TIMEOUT = 60
_GREP_LINE_RE = re.compile(r"^(.*?):(\d+):(.*)$")


def apply_numstat(repo: Path, patch_file: Path) -> list[str]:
    """`git apply --numstat -z` 看到的路徑（改名／複製兩端皆列）；git 不可用拋 OSError。
    只能檢查、不能當 `touched` 的來源（R51 (b)）；測試以 mock.patch.object 模擬漏看。"""
    cp = Git(repo).run("-c", "core.autocrlf=false", "apply", "--numstat", "-z", str(patch_file))
    if cp is None or cp.returncode != 0:
        raise OSError("git apply --numstat 失敗或 git 不可用")
    toks = cp.stdout.split("\0")
    out, i = [], 0
    while i < len(toks):
        parts = toks[i].split("\t", 2)
        if len(parts) == 3 and parts[2] == "" and i + 2 < len(toks):
            out += [toks[i + 1], toks[i + 2]]
            i += 3
            continue
        if len(parts) == 3:
            out.append(parts[2])
        i += 1
    return [p for p in out if p]


class Git:
    def __init__(self, repo: Path) -> None:
        self.repo = repo.resolve()
        self._ok: bool | None = None
        self.timed_out = False  # 最近一次 `run` 是否因逾時而回 None（分辨逾時與 git 不可用）

    def _env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k not in _STRIP_ENV}
        env["GIT_OPTIONAL_LOCKS"] = "0"
        return env

    def run(self, *args: str, timeout: int | None = None) -> subprocess.CompletedProcess | None:
        """`timeout` 選用（牆鐘秒數；預設仍為 60 秒，P1 的呼叫不變）。"""
        argv = ["git", "-C", str(self.repo), *args]
        self.timed_out = False
        try:
            return subprocess.run(
                argv, capture_output=True, encoding="utf-8", errors="replace",
                timeout=_TIMEOUT if timeout is None else timeout, shell=False, env=self._env(),
                check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except subprocess.TimeoutExpired:
            self.timed_out = True
            return None
        except (OSError, subprocess.SubprocessError):
            return None

    @property
    def available(self) -> bool:
        if self._ok is None:
            cp = self.run("rev-parse", "--is-inside-work-tree")
            self._ok = bool(cp and cp.returncode == 0 and cp.stdout.strip() == "true")
        return self._ok

    def is_commit(self, sha: str) -> bool:
        cp = self.run("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
        return bool(cp and cp.returncode == 0)

    def is_ancestor(self, sha: str) -> bool:
        cp = self.run("merge-base", "--is-ancestor", sha, "HEAD")
        return bool(cp and cp.returncode == 0)

    def log_first_parent(self, rel: str, rev_range: str | None = None) -> list[str] | None:
        args = ["-c", "core.quotepath=false", "log", "--first-parent", "--reverse", "--format=%H"]
        if rev_range:
            args.append(rev_range)
        cp = self.run(*args, "--", rel)
        if cp is None or cp.returncode != 0:
            return None
        return [ln.strip() for ln in cp.stdout.split("\n") if ln.strip()]

    def show(self, commit: str, rel: str) -> str | None:
        cp = self.run("show", f"{commit}:{rel}")
        return cp.stdout if cp is not None and cp.returncode == 0 else None

    def head(self) -> str | None:
        cp = self.run("rev-parse", "HEAD")
        sha = cp.stdout.strip() if cp is not None and cp.returncode == 0 else ""
        return sha if re.fullmatch(r"[0-9a-f]{40}", sha) else None

    def log_times(self, rel: str) -> list[tuple[str, int]] | None:
        """動過 `rel` 的 commit：(sha, committer 時間 epoch)，git 的預設走訪序（新→舊）。"""
        cp = self.run("-c", "core.quotepath=false", "log", "--format=%H %ct", "--", rel)
        if cp is None or cp.returncode != 0:
            return None
        pairs = [ln.split() for ln in cp.stdout.split("\n") if ln.strip()]
        return [(a, int(b)) for a, b in pairs]

    def commit_time(self, sha: str) -> int | None:
        cp = self.run("show", "-s", "--format=%ct", sha)
        txt = cp.stdout.strip() if cp is not None and cp.returncode == 0 else ""
        return int(txt) if txt.isdigit() else None

    def grep_only(self, pattern: str) -> list[tuple[str, int, str]] | None:
        """整個 repo（含未追蹤但未被忽略的檔）的 `-o` 命中：(相對路徑, 行號, 命中片段)。"""
        cp = self.run("-c", "core.quotepath=false", "grep", "-I", "-n", "-o", "--untracked",
                      "-E", pattern)
        if cp is None or cp.returncode not in (0, 1):
            return None
        hits = []
        for ln in cp.stdout.split("\n"):
            m = _GREP_LINE_RE.match(ln.rstrip("\r"))
            if m:
                hits.append((m.group(1), int(m.group(2)), m.group(3)))
        return hits
