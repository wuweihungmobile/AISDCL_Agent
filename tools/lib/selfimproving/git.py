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
import sys
from pathlib import Path
from shutil import which

#: 守門判定與實際推送**共用**的 git 環境剔除集合（單一來源，資安審查 F-14）：改變 repo／物件庫
#: 位置的變數，加上能從環境注入設定、改變 ssh 命令或 git 程式路徑的變數。`GIT_ASKPASS`、
#: `GIT_CONFIG_GLOBAL`、`GIT_CONFIG_NOSYSTEM` 是使用者既有的憑證與設定來源，不在此列。
STRIP_ENV = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE",
    "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_SSH_COMMAND", "GIT_SSH", "GIT_EXEC_PATH",
)
_STRIP_PREFIXES = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")
_TIMEOUT = 60
_VALUE_CHARS = re.compile(r"[A-Za-z0-9+/_.=\-]{12,}")
_KV = (r"(?i)\b([A-Z0-9_]*(?:token|password|passwd|secret|key|(?<![a-z])pat(?![a-z]))[A-Z0-9_]*)"
       r"(\s*[=:]\s*)(\S+)")


def _kv_hit(m: re.Match) -> bool:
    return bool(_VALUE_CHARS.fullmatch(m.group(3)))


def _auth_hit(m: re.Match) -> bool:
    return len(m.group(2)) >= 12


#: 機密樣式表（TCS-P7 附錄 A.8；**全套件唯一定義**，
#: `pushguard.SECRET_PATTERNS` 為其別名；封閉清單）：
#: （樣式名, 比對式, 遮罩替換式, 掃描時要再過的條件或 None＝命中即算）。
SECRET_PATTERNS = (
    ("key-value", re.compile(_KV), r"\1\2{m}", _kv_hit),
    ("auth-header", re.compile(r"(?i)\bAuthorization:\s*(\S+)\s+(\S+)"), r"Authorization: \1 {m}",
     _auth_hit),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
     "{m}", None),
    ("sk-token", re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"), "{m}", None),
    ("aws-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "{m}", None),
    ("private-key", re.compile(r"-----BEGIN[^\r\n]*PRIVATE KEY-----"), "{m}", None),
    ("url-userinfo", re.compile(r"://[^/\s]*@"), "://{m}@", None),
)


def _decoded(text: str) -> str:
    """`%xx` 解碼（只解 ASCII 位元組，不 import 網路模組）；非法序列原樣保留。"""
    if "%" not in text:
        return text
    return re.sub(r"(?:%[0-9A-Fa-f]{2})+",
                  lambda m: bytes.fromhex(m.group().replace("%", "")).decode("utf-8", "replace"),
                  text)


def mask(text: str, mark: str = "***") -> str:
    """機密遮罩的**單一實作**（推送結果、`last_error`、探針輸出尾段共用；審查 F-09）：依
    `SECRET_PATTERNS` 把值換成 `mark`；先對輸入做一次 `%xx` 解碼（URL 編碼形不漏）。"""
    text = _decoded(text)
    for _name, rx, repl, _cond in SECRET_PATTERNS:
        text = rx.sub(repl.replace("{m}", mark), text)
    return text


def scan_names(text: str) -> list[str]:
    """`text` 命中的樣式名（掃描規則比遮罩嚴：`key-value` 須值 ≥12 字元且只含值字元，避免把散文與
    型別標註判成機密）；不含命中的值。"""
    text = _decoded(text)
    out = []
    for name, rx, _repl, cond in SECRET_PATTERNS:
        if any(cond is None or cond(m) for m in rx.finditer(text)):
            out.append(name)
    return out


def scrub_env(env) -> dict[str, str]:
    """去掉 `STRIP_ENV` 與 `GIT_CONFIG_KEY_*`／`GIT_CONFIG_VALUE_*`（守門與推送共用）。"""
    return {k: v for k, v in env.items()
            if k not in STRIP_ENV and not k.startswith(_STRIP_PREFIXES)}


def safe_path(env=None) -> str:
    """`PATH` 去掉 repo 與虛擬環境之下的目錄（審查 F-10／F-16：那裡的 `git` 是被攻擊面）。"""
    env = os.environ if env is None else env
    repo = Path(__file__).resolve().parents[3]
    banned = [repo]
    if sys.prefix != sys.base_prefix:  # 在虛擬環境內：環境根本身也不可信（可能不在 repo 之下）
        banned.append(Path(sys.prefix).resolve())
    keep = []
    for d in (env.get("PATH") or "").split(os.pathsep):
        try:
            inside = bool(d) and any(Path(d).resolve().is_relative_to(b) for b in banned)
        except OSError:
            inside = True
        if d and not inside:
            keep.append(d)
    return os.pathsep.join(keep)


def resolve_git(env=None) -> str | None:
    """git 執行檔的絕對路徑（審查 F-10）：只在 `safe_path` 內解析；解析不到＝None（呼叫端
    fail-closed）。`push-run` 與守門只用它。"""
    return which("git", path=safe_path(env))


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
        env = scrub_env(os.environ)
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

    def run_bytes(self, *args: str,
                  timeout: int | None = None) -> subprocess.CompletedProcess | None:
        """同 `run`，但 stdout／stderr 原樣回位元組（不解碼、不換行轉換）。"""
        argv = ["git", "-C", str(self.repo), *args]
        self.timed_out = False
        try:
            return subprocess.run(
                argv, capture_output=True, timeout=_TIMEOUT if timeout is None else timeout,
                shell=False, env=self._env(), check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
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
