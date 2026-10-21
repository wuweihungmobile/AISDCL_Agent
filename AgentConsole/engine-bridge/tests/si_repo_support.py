"""SelfImproving 差分測試的夾具建構器與真 CLI 輔助（TCS-SelfImprovingMirror-P1b §5.1、R25）。

不是測試（檔名不以 test_ 開頭）；被 test_si_*.py 與 si_golden_regen.py import。

「真 CLI」＝把 `CLI_CLOSURE`（根層 `export` 的 import 閉包）自 monorepo 複製進 tmp 倉，加
`tests/fixtures/si_repo/` 的帳本複本與取自真 repo 的 `params.json`，`git init` 並以固定作者與
日期提交一次＝狀態 A；追加一筆觀察列與一筆事件再提交一次＝狀態 B。閉包不完備時建構器直接大聲
失敗（`SiFixtureError`，訊息含 `CLI_CLOSURE` 與 CLI 的 stderr），絕不退回假 CLI。

建倉所得的 HEAD 隨複製進倉的閉包與夾具內容而變（樹內容進雜湊），所以**不被當作常數、不進黃金檔**。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from app import si_cli

TESTS_DIR = Path(__file__).resolve().parent
#: <monorepo>（tests → engine-bridge → AgentConsole → monorepo）
MONOREPO = TESTS_DIR.parents[2]
FIXTURE_REPO = TESTS_DIR / "fixtures" / "si_repo"
GOLDEN_DIR = TESTS_DIR / "fixtures" / "si_golden"

#: 根層 `export` 的 import 閉包（現查：以真 CLI 在複本倉實跑五個 kind 皆 rc 0、無 `__pycache__`）。
#: 日後變動時，本常數、`.github/workflows/agentconsole-ci.yml` 的 `paths` 與 AT-940-4-1 同一個
#: commit 收齊。
CLI_CLOSURE: tuple[str, ...] = (
    "tools/selfimproving.py",
    "tools/_stdio_utf8.py",
    "tools/lib/platform_utils.py",
    "tools/lib/selfimproving/",
)
#: 建倉時自真 repo 複製（使 `params.json` 的結構演進會讓 Bridge 測試誠實變紅）。
PARAMS_SRC = "docs/06_quality/SelfImproving_Protocol/params.json"

SCRIPT_REL = "tools/selfimproving.py"
FIXED_NAME, FIXED_EMAIL = "si-fixture", "si-fixture@example.invalid"
DATE_A = "2026-10-21T00:00:00+08:00"
DATE_B = "2026-10-21T00:10:00+08:00"
#: 狀態 B 的 `run.open` 事件所帶的固定 head_sha（不取自建倉所得的 HEAD）。
FIXED_RUN_HEAD = "73ff8e3cdefeb993f9d4213ef88e3c184055a60a"
OBS_B_ROW = ("| OBS-SI-013 | 2026-10-21 00:10 | 主控・夾具 | 狀態 B 追加的一般觀察列（差分負控） | "
             "`docs/06_quality/SelfImproving_Protocol/params.json` | bug | P3 | open | "
             "面=產品;來源=工具;回報者=主控 |")
EVENT_B = {"seq": 7, "t": DATE_B, "kind": "run.open", "by": "主控", "run": "RUN-SI-002",
           "trigger": "a", "coords": ["夾具座標：狀態 B 追加的運轉"], "head_sha": FIXED_RUN_HEAD}
OBS_LEDGER_REL = "docs/06_quality/SelfImproving_Observation_Ledger.md"
EVENT_LEDGER_REL = "docs/06_quality/SelfImproving_Event_Ledger.jsonl"
KINDS = si_cli.SI_KINDS


class SiFixtureError(RuntimeError):
    """夾具建構失敗（閉包不完備、git 失敗…）：一律大聲，不退回假 CLI。"""


# ── 真 CLI 的執行（差分基準）────────────────────────────────────────────────────────────────
def cli_env(root: Path) -> dict[str, str]:
    """與 Bridge 子行程同一份環境（`si_cli.build_env`）：基準與被測者吃同樣的環境，差異只會來自
    Bridge 自己。呼叫時才讀 `os.environ`，所以測試可先把 HOME／USERPROFILE 指向 tmp。"""
    return si_cli.build_env(os.environ, root)


def cli_run(root: Path, *args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[bytes]:
    argv = [sys.executable, str(root / SCRIPT_REL), *args]
    return subprocess.run(argv, cwd=str(root), env=cli_env(root), stdin=subprocess.DEVNULL,
                          capture_output=True, timeout=timeout, check=False)


def cli_export(root: Path, kind: str, *flags: str) -> dict[str, Any]:
    """基準：直接以 `sys.executable` 跑 `export --json --kind <kind> …` 並解析 stdout。"""
    done = cli_run(root, "export", "--json", "--kind", kind, *flags)
    if done.returncode != 0:
        raise SiFixtureError(f"真 CLI export {kind} rc={done.returncode}："
                             f"{done.stderr.decode('utf-8', errors='replace')[-500:]}")
    return json.loads(done.stdout.decode("utf-8"))


def cli_card(root: Path, prop: str) -> str:
    """`si card` 的 stdout（UTF-8 解碼、不經 strip）。"""
    done = cli_run(root, "card", prop)
    if done.returncode != 0:
        raise SiFixtureError(f"真 CLI card {prop} rc={done.returncode}")
    return done.stdout.decode("utf-8")


# ── git 與建倉 ─────────────────────────────────────────────────────────────────────────────
def git(root: Path, *args: str, date: str | None = None) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"GIT_AUTHOR_NAME": FIXED_NAME, "GIT_AUTHOR_EMAIL": FIXED_EMAIL,
                "GIT_COMMITTER_NAME": FIXED_NAME, "GIT_COMMITTER_EMAIL": FIXED_EMAIL})
    if date is not None:
        env.update({"GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date})
    hooks = root.parent / f"{root.name}-no-hooks"
    hooks.mkdir(exist_ok=True)
    argv = ["git", "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
            "-c", f"core.hooksPath={hooks}", "-c", "init.defaultBranch=main",
            "-C", str(root), *args]
    done = subprocess.run(argv, env=env, capture_output=True, stdin=subprocess.DEVNULL,
                          timeout=120, check=False)
    if done.returncode != 0:
        raise SiFixtureError(f"git {' '.join(args)} rc={done.returncode}："
                             f"{done.stderr.decode('utf-8', errors='replace')[-500:]}")
    return done.stdout.decode("utf-8", errors="replace")


def head_of(root: Path) -> str:
    return git(root, "rev-parse", "HEAD").strip()


def _copy_closure(dest: Path, closure: Iterable[str]) -> None:
    for rel in closure:
        clean = rel.rstrip("/")
        src, dst = MONOREPO / clean, dest / clean
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        else:
            raise SiFixtureError(f"CLI_CLOSURE 的項目在 monorepo 內不存在：{rel}")


def _verify_closure(root: Path, closure: Iterable[str]) -> None:
    """閉包完備性自檢：真 CLI 必須跑得起來（缺檔會在 import 就死，stderr 指出缺哪個）。"""
    done = cli_run(root, "export", "--json", "--kind", "status")
    if done.returncode != 0:
        tail = done.stderr.decode("utf-8", errors="replace")[-800:]
        raise SiFixtureError(
            f"CLI_CLOSURE 不完備，真 CLI 跑不起來（rc={done.returncode}；閉包＝{list(closure)}）："
            f"{tail}")


def make_si_repo(tmp_path: Path, state: str = "A", *, name: str | None = None,
                 closure: Iterable[str] = CLI_CLOSURE,
                 before_commit: Callable[[Path], None] | None = None) -> Path:
    """建 tmp 倉並回傳其根。`state`＝`A`｜`B`；`B` 是在 A 之上追加一列一事件再提交（等同
    `advance_to_b(make_si_repo(tmp_path, "A"))`）。`before_commit(root)` 在第一次提交前被呼叫
    （可重現性負控用：對閉包複本追加註解）。"""
    if state not in ("A", "B"):
        raise ValueError(f"state 必須是 A 或 B：{state!r}")
    closure = tuple(closure)
    root = tmp_path / (name or f"si-repo-{state}")
    root.mkdir(parents=True)
    _copy_closure(root, closure)
    shutil.copytree(FIXTURE_REPO, root, dirs_exist_ok=True)
    params = root / PARAMS_SRC
    params.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MONOREPO / PARAMS_SRC, params)
    _verify_closure(root, closure)
    if before_commit is not None:
        before_commit(root)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture A", date=DATE_A)
    return advance_to_b(root) if state == "B" else root


def advance_to_b(root: Path) -> Path:
    """把狀態 A 的倉推進到狀態 B（原地；追加 `OBS-SI-013` 與 seq 7 的 `run.open`，再提交）。"""
    with (root / OBS_LEDGER_REL).open("ab") as fh:
        fh.write((OBS_B_ROW + "\n").encode("utf-8"))
    with (root / EVENT_LEDGER_REL).open("ab") as fh:
        fh.write((json.dumps(EVENT_B, ensure_ascii=False, separators=(",", ":")) + "\n")
                 .encode("utf-8"))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "fixture B", date=DATE_B)
    return root


class _SubprocessProxy:
    """只換掉 `Popen` 的 `subprocess` 代理：`si_cli` 以外（例如 `cli_run` 的基準呼叫）不受影響。"""

    def __init__(self, popen: Callable[..., Any]) -> None:
        self.Popen = popen

    def __getattr__(self, name: str) -> Any:
        return getattr(subprocess, name)


def record_si_popen(monkeypatch: Any) -> list[list[str]]:
    """紀錄器：包住 `si_cli` 用的 `Popen`（呼叫真的 Popen），回傳會被追加的 argv 清單。"""
    calls: list[list[str]] = []

    def wrapper(argv: Any, **kwargs: Any) -> Any:
        calls.append([str(a) for a in argv])
        return subprocess.Popen(argv, **kwargs)

    monkeypatch.setattr(si_cli, "subprocess", _SubprocessProxy(wrapper))
    return calls


def isolate_home(monkeypatch: Any, tmp_path: Path, name: str = "home") -> Path:
    """HOME 與 USERPROFILE 指向 tmp 內的空目錄（Bridge 子行程繼承它；真家目錄不得被碰）。"""
    home = tmp_path / name
    home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


# ── 欄名對映（R9）的參考實作 ───────────────────────────────────────────────────────────────
_CAMEL_KEY = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+")


def camel(key: str) -> str:
    """鍵符合 `^[a-z][a-z0-9]*(_[a-z0-9]+)+$` 才轉（首段不動、其後各段首字元大寫），其餘恆等。"""
    if not _CAMEL_KEY.fullmatch(key):
        return key
    head, *rest = key.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def camel_keys(obj: Any) -> Any:
    """全層級的物件鍵經 `camel`；值（含 `null`、字串）一律不動。兩鍵撞成同名＝大聲失敗。"""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            new = camel(key)
            if new in out:
                raise SiFixtureError(f"欄名對映撞鍵：{key!r} → {new!r} 已存在")
            out[new] = camel_keys(value)
        return out
    if isinstance(obj, list):
        return [camel_keys(x) for x in obj]
    return obj


# ── 黃金檔與子集比較（⚖ 30）───────────────────────────────────────────────────────────────
ZERO_SHA = "0" * 40
GOLDEN_GENERATED_AT = DATE_A
HEAD_PLACEHOLDER = "<HEAD>"


def collect_state_outputs(root: Path, *, with_one: bool = True) -> dict[str, dict[str, Any]]:
    """對一個倉取五個 kind 與（可選）單筆提案的真輸出（未正規化）。"""
    out = {kind: cli_export(root, kind) for kind in KINDS}
    if with_one:
        out["proposal_one"] = cli_export(root, "proposals", "--id", "PROP-SI-004")
    return out


def to_golden(outputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """snake_case 黃金檔：各回應頂層 `generated_at` 置占位、頂層 `head_sha`（40 碼 hex）置
    40 個 `0`；其餘鍵值一律保留真輸出。"""
    golden: dict[str, dict[str, Any]] = {}
    for key, resp in outputs.items():
        copy = json.loads(json.dumps(resp))
        copy["generated_at"] = GOLDEN_GENERATED_AT
        if isinstance(copy.get("head_sha"), str):
            copy["head_sha"] = ZERO_SHA
        golden[key] = copy
    return golden


def render_json(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def mask_heads(obj: Any) -> Any:
    """全部深度：鍵名為 `head_sha` 的值一律換成占位（比對前雙方都做）。"""
    if isinstance(obj, dict):
        return {k: (HEAD_PLACEHOLDER if k == "head_sha" else mask_heads(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_heads(x) for x in obj]
    return obj


def subset_diffs(golden: Any, real: Any, path: str = "$") -> list[str]:
    """黃金檔的每個鍵與值都要在真輸出的同一位置存在且相等；陣列個數與順序相同；真輸出可多鍵。
    回傳差異清單（空＝相符）。"""
    if isinstance(golden, dict):
        if not isinstance(real, dict):
            return [f"{path}：黃金檔是物件、真輸出不是"]
        out: list[str] = []
        for key, value in golden.items():
            if key not in real:
                out.append(f"{path}.{key}：真輸出缺這個鍵")
            else:
                out += subset_diffs(value, real[key], f"{path}.{key}")
        return out
    if isinstance(golden, list):
        if not isinstance(real, list) or len(golden) != len(real):
            return [f"{path}：陣列個數不同（黃金檔 {len(golden)}，"
                    f"真輸出 {len(real) if isinstance(real, list) else '非陣列'}）"]
        out = []
        for i, (g, r) in enumerate(zip(golden, real, strict=True)):
            out += subset_diffs(g, r, f"{path}[{i}]")
        return out
    return [] if golden == real and type(golden) is type(real) else [
        f"{path}：{golden!r} != {real!r}"]


def golden_subset_diffs(golden: dict[str, dict[str, Any]],
                        outputs: dict[str, dict[str, Any]]) -> list[str]:
    diffs: list[str] = []
    for key, resp in golden.items():
        real = {k: v for k, v in outputs[key].items() if k != "generated_at"}
        want = {k: v for k, v in resp.items() if k != "generated_at"}
        diffs += [f"{key}{d[1:]}" for d in subset_diffs(mask_heads(want), mask_heads(real))]
    return diffs


# ── 前後快照（AT-932-2-2）────────────────────────────────────────────────────────────────────
def repo_snapshot(root: Path) -> dict[str, Any]:
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_file() and not rel.startswith(".git/"):
            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    git_dir = root / ".git"
    refs = {p.relative_to(git_dir).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted((git_dir / "refs").rglob("*")) if p.is_file()}
    return {"status": git(root, "status", "--porcelain"), "head": head_of(root), "files": files,
            "git_head": (git_dir / "HEAD").read_text(encoding="utf-8"), "refs": refs}


def tree_listing(directory: Path) -> list[str]:
    return sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*"))
