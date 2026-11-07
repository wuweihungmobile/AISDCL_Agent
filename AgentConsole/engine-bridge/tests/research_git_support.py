"""分流測試的共用支援（TCS-ResearchToPRD-P1 §5.2 的 `GIT`、`GH`；PKG-BR-D1）。

hermetic 三件事：
  · `GIT`：拋棄式 git 倉。預設是**迷你 monorepo**（`make_mini_repo`：`AutoClaude/`、
    `AgentConsole/`、`AISDLC_SDD/AISDLC_SDD_v9.99/`、`docs/` 加一筆初始 commit，分支 `main`）
    ——比 clone 整個 monorepo 快、且不依賴本機歷史；`clone_repo` 是 `git clone --no-hardlinks`
    的變體（整合棒用）。全部 git 呼叫都帶隔離環境（`GIT_CONFIG_GLOBAL`／`GIT_CONFIG_SYSTEM`
    指向空檔、固定作者），不讀也不寫使用者設定。
  · `GH`：假 gh 可執行檔夾具（`fixtures/research/fake_gh/`；Windows `gh.cmd`、POSIX `gh`，
    兩形態都入庫、只有本平台那份在本機實跑）。行為由環境變數 `FAKE_GH_MODE` 切換：
    `ok`｜`unauth`｜`fail-create`｜`leak`。
  · `make_route_db`：拋棄式研究資料庫，套到 V19（V19 檔不在時退回從 Architecture K.4 抽 DDL，
    避免與 PKG-DB-P1 的合併順序綁死）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from tests.research_pg_support import MIGRATION_DIR, REPO_ROOT, ThrowawayDb, make_research_db

FAKE_GH_DIR = Path(__file__).resolve().parent / "fixtures" / "research" / "fake_gh"
FAKE_TOKEN = "ghp_FAKE_R2P1_TOKEN_000000000000000000"
ARCHITECTURE = REPO_ROOT / "AgentConsole" / "docs" / "02_architecture" / "Architecture.md"
V19_FILE = "V19__research_route_scr_delivery.sql"


# ── 資料庫（V19）───────────────────────────────────────────────────────────────────────────
def _k4_ddl() -> str:
    text = ARCHITECTURE.read_text(encoding="utf-8")
    start = text.index("**K.4　`V19__research_route_scr_delivery.sql`")
    block = text.index("```sql", start) + len("```sql")
    return text[block: text.index("```", block)]


def make_route_db() -> ThrowawayDb:
    """套到 V19 的拋棄式研究庫。V19 檔在（PKG-DB-P1 已合併）就走正規路徑；不在就先套 V1～V18 再套
    Architecture K.4 的 DDL（同一份文字，DB-P1 的 V19 檔逐字取自它）。"""
    if (MIGRATION_DIR / V19_FILE).is_file():
        return make_research_db(19)
    db = make_research_db(18)
    try:
        import psycopg

        with psycopg.connect(db.dsn, autocommit=True) as conn:
            conn.execute("SET search_path TO console")
            conn.execute(_k4_ddl())
    except BaseException:
        db.drop()
        raise
    return db


# ── git ────────────────────────────────────────────────────────────────────────────────────
def git_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("GIT_", "BRIDGE_", "SDD_")) and k not in ("PYTHONPATH",)}
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "tester",
                "GIT_AUTHOR_EMAIL": "tester@example.invalid", "GIT_COMMITTER_NAME": "tester",
                "GIT_COMMITTER_EMAIL": "tester@example.invalid", "GIT_TERMINAL_PROMPT": "0",
                "GIT_OPTIONAL_LOCKS": "0"})
    env.update(extra or {})
    return env


def git(cwd: Path, *args: str, check: bool = True) -> str:
    """測試端自己的 git 呼叫（隔離環境；不經 Bridge 的 gitops）。回 stdout。"""
    proc = subprocess.run(["git", *args], cwd=str(cwd), env=git_env(), capture_output=True,
                          text=True, encoding="utf-8", check=False)
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} rc={proc.returncode}: {proc.stderr}")
    return proc.stdout


def make_mini_repo(path: Path) -> Path:
    """迷你 monorepo（含 sdd 的 LATEST 目錄形態）與初始 commit；分支 `main`。"""
    path.mkdir(parents=True)
    for rel in ("AutoClaude/README.md", "AgentConsole/README.md",
                "AISDLC_SDD/AISDLC_SDD_v9.99/README.md", "docs/README.md", "tools/keep.txt",
                "CLAUDE.md"):
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"# {rel}\n", encoding="utf-8", newline="\n")
    git(path, "init", "-b", "main")
    git(path, "add", "-A")
    git(path, "commit", "-m", "init")
    return path


def clone_repo(source: Path, dest: Path) -> Path:
    """`git clone --no-hardlinks`（整合棒的拋棄式 clone 載具）；只對來源做唯讀的 clone。"""
    git(source.parent, "clone", "--no-hardlinks", str(source), str(dest))
    return dest


def snapshot(repo: Path) -> dict[str, Any]:
    """主工作樹的零擾動量測：status、HEAD、worktree 清單、index 雜湊、分支、stash。"""
    index = git(repo, "ls-files", "-s")
    return {"status": git(repo, "status", "--porcelain"),
            "head": git(repo, "rev-parse", "HEAD").strip(),
            "worktrees": git(repo, "worktree", "list", "--porcelain"),
            "index": hashlib.sha256(index.encode("utf-8")).hexdigest(),
            "branches": git(repo, "branch", "--list"),
            "current": git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
            "stash": git(repo, "stash", "list")}


def tree_hash(root: Path) -> str:
    """目錄樹的內容雜湊（相對路徑＋位元組；不含 mtime；不存在＝空樹）。"""
    digest = hashlib.sha256()
    if root.exists():
        for p in sorted(root.rglob("*")):
            digest.update(p.relative_to(root).as_posix().encode("utf-8"))
            if p.is_file():
                digest.update(p.read_bytes())
    return digest.hexdigest()


def cleanup_worktrees(repo: Path) -> None:
    """收尾：把測試建的 worktree 逐一移除（測試端的清理，不是 Bridge 的動作）。"""
    for line in git(repo, "worktree", "list", "--porcelain", check=False).splitlines():
        if line.startswith("worktree ") and Path(line[9:]).resolve() != repo.resolve():
            git(repo, "worktree", "remove", "--force", line[9:], check=False)


# ── 假 gh ──────────────────────────────────────────────────────────────────────────────────
@dataclass
class FakeGh:
    bin_dir: Path
    log_path: Path
    monkeypatch: pytest.MonkeyPatch

    def mode(self, name: str) -> None:
        self.monkeypatch.setenv("FAKE_GH_MODE", name)

    def calls(self) -> list[dict[str, Any]]:
        if not self.log_path.is_file():
            return []
        return [json.loads(line) for line in self.log_path.read_text(
            encoding="utf-8").splitlines() if line.strip()]

    def clear(self) -> None:
        self.log_path.unlink(missing_ok=True)


def install_fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeGh:
    """把假 gh 夾具複製到暫存 bin 目錄、前置到 PATH（`shutil.which('gh')` 解析到它）。本平台那份
    實跑：Windows 用 `gh.cmd`、POSIX 用 `gh`（複製後補 exec 位元）。"""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    shutil.copy2(FAKE_GH_DIR / "gh_fake.py", bin_dir / "gh_fake.py")
    if sys.platform == "win32":
        shutil.copy2(FAKE_GH_DIR / "gh.cmd", bin_dir / "gh.cmd")
    else:
        shutil.copy2(FAKE_GH_DIR / "gh", bin_dir / "gh")
        (bin_dir / "gh").chmod(0o755)
    log = tmp_path / "fake_gh.log.jsonl"
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("FAKE_GH_LOG", str(log))
    monkeypatch.setenv("FAKE_GH_PYTHON", sys.executable)
    monkeypatch.setenv("FAKE_GH_MODE", "ok")
    return FakeGh(bin_dir, log, monkeypatch)


def hide_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    """讓 PATH 上沒有 gh（容器模式）：丟掉含 gh 執行檔的目錄（git 與 python 另在的目錄保留）。
    若 git 與 gh 住同一個目錄，git 也會一併消失——該環境請改用 `FAKE_GH`／別的做法。"""
    dirs = [d for d in os.environ.get("PATH", "").split(os.pathsep) if d and not any(
        (Path(d) / name).exists() for name in ("gh", "gh.exe", "gh.cmd", "gh.bat"))]
    monkeypatch.setenv("PATH", os.pathsep.join(dirs))

# ── 掃描 ────────────────────────────────────────────────────────────────────────────────────
def contains_secret(text: str, secret: str) -> bool:
    return secret in text or secret[:8] in text


def all_text_columns(db: ThrowawayDb) -> Iterator[tuple[str, str, Any]]:
    """`console.research_*` 全部表的全部文字欄與 JSONB 欄（`information_schema` 列舉，不手抄）。"""
    cols = db.q("SELECT table_name, column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'console' AND table_name LIKE 'research\\_%' "
                "AND data_type IN ('text', 'character varying', 'jsonb', 'ARRAY', 'character')")
    for table, column, _kind in cols:
        for (value,) in db.q(f'SELECT "{column}"::text FROM console."{table}"'):
            yield table, column, value


def scan_files(root: Path, secret: str) -> list[str]:
    hits = []
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file() and ".git" not in p.parts:
                try:
                    if contains_secret(p.read_text(encoding="utf-8", errors="ignore"), secret):
                        hits.append(str(p))
                except OSError:
                    continue
    return hits


# ── 播種：Gate 0 之後的研究專案（PRD 含「模組落點表」）──────────────────────────────────────────
PRD_PLACEMENT = ("# PRD\n\n## 1. 背景\n分流測試用 PRD。\n\n## 2. 驗收\nAC-001：P99 低於 10 ms。\n\n"
                 "## 9. 模組落點表\n\n| 元件 | 落點 |\n|---|---|\n| UI 與後端 | AgentConsole |\n")

@dataclass
class RouteEnv:
    """分流測試的環境：活 Bridge（真 SDD 樹）、拋棄式 repo、worktree 根、scaffold 根、拋棄式庫。"""

    env: Any
    repo: Path
    worktrees: Path
    scaffold: Path
    rdb: ThrowawayDb
    tmp: Path

    def console_project(self, name: str = "route-target") -> str:
        """console-api 先建的 `projects` 列（FK 目標）；回 id。"""
        label = f"{name}-{uuid.uuid4().hex[:6]}"
        row = self.rdb.one("INSERT INTO console.projects (name, execution_path, pass_criteria) "
                           "VALUES (%s, %s, 'x') RETURNING id", label, str(self.tmp / label))
        assert row is not None
        return str(row[0])


def build_route_env(make_env: Callable[..., Any], rdb: ThrowawayDb, tmp_path: Path, tree: Path,
                    **over: Any) -> RouteEnv:
    """活 Bridge＋四個路徑設定（repo／worktree／scaffold 皆在 `tmp_path` 下並併入允許根）。"""
    repo = make_mini_repo(tmp_path / "repo")
    worktrees, scaffold = tmp_path / "wt", tmp_path / "scaffold"
    scaffold.mkdir()
    roots = tuple(p.resolve() for p in (tmp_path / "workspace", tmp_path / "projects", repo,
                                         worktrees, scaffold))
    worktrees.mkdir(exist_ok=True)
    fields: dict[str, Any] = {
        "research_repo_root": repo, "research_worktree_root": worktrees,
        "research_scaffold_root": scaffold, "allowed_path_roots": roots}
    fields.update(over)
    env = make_env(tree, rdb, **fields)
    return RouteEnv(env=env, repo=repo, worktrees=worktrees, scaffold=scaffold, rdb=rdb,
                    tmp=tmp_path)


def seed_gate0(renv: RouteEnv, slug: str = "demo", *, prd: str = PRD_PLACEMENT,
               target_scope: str | None = None, approve: bool = True) -> str:
    """Given：Gate 0 已核准的研究專案（外環 FSM SPEC_FROZEN、游標 route／FROZEN、有凍結摘要）。
    走真 HTTP（建立、存 PRD、`:approve-baseline`），與 P0 的 Gate 0 測試同一條路徑。"""
    from app.research import fsm_ops, layout
    from tests import test_research_approve as ap
    from tests import test_research_router as rt

    env = renv.env
    body = rt.project_body(slug)
    rid = str(body["research_id"])
    assert env.post("/research/projects", body).status_code == 201
    saved = env.put(f"/research/projects/{rid}/prd", {
        "base_version": 0, "content": prd, "author": rt.ALICE})
    assert saved.status_code == 201, saved.text
    ws = ap.workspace(env, rid)
    layout.write_workspace_file(ws, ap.MATRIX_REL, ap.MATRIX_TEXT)
    layout.write_workspace_file(ws, ap.ADR_REL, ap.ADR_TEXT)
    ap.seed_round(env, rid, 1, 1)
    ctx = rt.fsm_ctx_of(env, rid)
    fsm_ops.transition(ctx, to="SPEC_DRAFTING", reason="start drafting")
    fsm_ops.transition(ctx, to="SCG_VALIDATION", reason="ready for review")
    fsm_ops.gate(ctx, gate="SCG_VALIDATION", result="PASS", reason="review passed")
    env.db.set_cursor(research_id=rid, actor="bridge", flow={
        "step": "studio", "phase": "GATE0_PENDING", "status": "WAITING_HUMAN", "detail": ""})
    if approve:
        resp = ap.approve(env, rid, ap.seen(env, rid, ap.BASELINE_REL))
        assert resp.status_code == 200, resp.text
    if target_scope is not None:
        renv.rdb.exec("UPDATE console.research_projects SET target_scope = %s WHERE id = %s",
                      target_scope, rid)
    return rid


def body_a(renv: RouteEnv, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"track": "A", "target_module": "agentconsole",
                            "approver": "admin@example.com"}
    body.update(over)
    return body


def body_b(renv: RouteEnv, **over: Any) -> dict[str, Any]:
    body: dict[str, Any] = {"track": "B", "project_name": "demo-app", "owner": "octocat",
                            "stack_template": "python-fastapi", "create_github": False,
                            "approver": "admin@example.com"}
    body.update(over)
    return body


def confirm(renv: RouteEnv, rid: str, body: dict[str, Any], **extra: Any) -> Any:
    """確認執行（帶 console_project_id；每次呼叫建一個新的 Console 專案列）。"""
    payload = {"console_project_id": renv.console_project(f"p{len(body)}-{extra.get('n', 0)}"),
               **{k: v for k, v in body.items()}}
    payload.update({k: v for k, v in extra.items() if k != "n"})
    return renv.env.post(f"/research/projects/{rid}:route", payload)


def preview(renv: RouteEnv, rid: str, body: dict[str, Any]) -> Any:
    return renv.env.post(f"/research/projects/{rid}:route-preview",
                         {k: v for k, v in body.items() if k not in ("approver",)})

# ── pytest 夾具（各測試檔以 `route_db, real_tree, renv, fake_gh = rgs.…` 引入；`make_env` 取自
#    `tests.test_research_router`）─────────────────────────────────────────────────────────────
@pytest.fixture
def route_db() -> Iterator[ThrowawayDb]:
    db = make_route_db()
    try:
        yield db
    finally:
        db.drop()


@pytest.fixture
def real_tree() -> Path:
    """真 SDD 樹（缺 `SDD_ROOT`＝`TOOL-ABSENCE` skip；SCG-4 證據須 0 skipped）。"""
    from tests.test_research_fsm_ops import real_sdd_root

    return real_sdd_root()


@pytest.fixture
def fake_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeGh:
    return install_fake_gh(tmp_path, monkeypatch)


@pytest.fixture
def renv(make_env: Callable[..., Any], route_db: ThrowawayDb, tmp_path: Path, real_tree: Path,
         fake_gh: FakeGh) -> Iterator[RouteEnv]:
    built = build_route_env(make_env, route_db, tmp_path, real_tree)
    try:
        yield built
    finally:
        cleanup_worktrees(built.repo)
