"""SelfImproving 反事實回測的寫檔動詞：`cases --build`、`prepare`、`cleanup`（FR-SI-46；P6）。

能力類別 `rw`：案例檔寫進 `docs/06_quality/SelfImproving_Backtest/`（專屬建立、不覆寫既有版本）；
批次目錄（任務書、`batch.json`、快照 worktree）一律在 repo **外**的家目錄。快照一律經 `Git.run`
（`git worktree add --detach`；移除一律 `git worktree remove` 不帶強制旗標，再
`git worktree prune`，
不以整個資料夾刪除代替——否則留下 `.git/worktrees/` 的死登記）。全程零網路、不呼叫任何模型。
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from . import btcases, btscore
from . import writeverbs as wv
from .btcases import BtError
from .git import Git

_WT_TIMEOUT = 600
_SEED_MAX = 2**31 - 1


def _out(rc: int, lines: list[str], as_json: bool, obj: dict) -> wv.Out:
    return wv.Out(rc, json.dumps(obj, ensure_ascii=False) + "\n" if as_json
                  else "\n".join(lines) + "\n")


def _git(repo: Path) -> Git:
    git = Git(repo)
    if not git.available or git.head() is None:
        raise BtError([("GIT-UNAVAILABLE", "git 不可用或無 commit")])
    return git


def cases_build(repo: Path, version: int | None, as_json: bool) -> wv.Out:
    """`cases --build`：產生新版案例檔；零案例＝`BT-CASES-EMPTY`；同版號檔已存在＝
    `BT-CASES-VERSION-EXISTS`（專屬建立，絕不覆寫）。"""
    git = _git(repo)
    built = btcases.build(repo, git)
    if not built["cases"]:
        raise BtError([("BT-CASES-EMPTY", f"零合格案例（排除 {len(built['excluded'])} 筆）")])
    ver = version if version is not None else (btcases.versions(repo) or [0])[-1] + 1
    if ver < 1:
        raise wv.UsageError("--version 須為正整數")
    path = btcases.cases_path(repo, ver)
    exists = BtError([("BT-CASES-VERSION-EXISTS", f"{path.name} 已存在，不覆寫")])
    if path.exists():
        raise exists
    text = btcases.dumps(btcases.file_object(ver, btcases.now_iso(), git.head(), built))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "xb") as fh:
            fh.write(text.encode("utf-8"))
            fh.flush()
            os.fsync(fh.fileno())
    except FileExistsError:
        raise exists from None
    except OSError as exc:
        path.unlink(missing_ok=True)
        raise wv.UsageError(f"案例檔寫入失敗（{type(exc).__name__}）") from exc
    n, ex = len(built["cases"]), len(built["excluded"])
    return _out(0, [f"ok backtest cases version={ver} cases={n} excluded={ex} file={path.name}"],
                as_json, {"ok": True, "verb": "backtest", "sub": "cases", "version": ver,
                          "cases": n, "excluded": ex, "file": path.name})


def _next_batch(repo: Path, root: Path) -> int:
    nums = [int(p.name[3:]) for p in root.glob("BT-*") if btcases.BATCH_RE.match(p.name)
            ] if root.is_dir() else []
    ledger = repo / btcases.RESULTS_REL
    if ledger.is_file():
        for ln in ledger.read_bytes().decode("utf-8", "replace").splitlines():
            try:
                b = json.loads(ln).get("batch", "")
            except (ValueError, AttributeError):
                continue
            nums += [int(b[3:])] if isinstance(b, str) and btcases.BATCH_RE.match(b) else []
    return max(nums, default=0) + 1


def _remove_worktrees(git: Git, paths: list[Path]) -> list[Path]:
    """逐一 `git worktree remove`（不帶強制旗標）；回被 git 拒絕而保留者。最後 `prune`。"""
    kept = []
    for p in paths:
        if not p.exists():
            continue
        cp = git.run("worktree", "remove", str(p), timeout=_WT_TIMEOUT)
        if cp is None or cp.returncode != 0:
            kept.append(p)
    git.run("worktree", "prune")
    return kept


def _task(template: str, case: dict, slot: str, snap: Path, nonce: str) -> str:
    return btcases.render_task(template, {
        "SNAP_ROOT": str(snap), "CASE": slot, "SYMPTOM": case["symptom"], "NONCE": nonce,
        "TOP_N": str(btcases.BT_TOP), "BUDGET": btcases.BT_BUDGET})


def _gate(repo: Path, seed: int, k: int, root: Path) -> tuple[dict, bytes, int, str]:
    """前置檢查（零寫入）：回（案例檔物件, 原位元組, 版本, 任務書範本）。"""
    if not 1 <= k <= btcases.BT_K_MAX:
        raise BtError([("BT-K-RANGE", f"--k 須介於 1 與 {btcases.BT_K_MAX}")])
    if not 0 <= seed <= _SEED_MAX:
        raise BtError([("BT-SEED-RANGE", f"--seed 須介於 0 與 {_SEED_MAX}")])
    if btscore.inside(repo, root):
        raise BtError([("BT-ROOT-INSIDE-REPO", f"--root 不得在 repo 之內：{root}")])
    found = btcases.latest(repo)
    if found is None:
        raise BtError([("BT-CASES-MISSING", "沒有案例檔，先跑 backtest cases --build")])
    obj, raw = btcases.load(found[1])
    bad = btcases.format_problems(raw, obj)  # commit 可解析與否由 worktree add 本身把關
    if bad:
        raise BtError(bad)
    if len(obj["cases"]) < k:
        raise BtError([("BT-POOL-TOO-SMALL", f"pool={len(obj['cases'])} k={k}")])
    sop = repo / btcases.SOP_REL
    template = btcases.template_of(sop.read_bytes().decode("utf-8", "replace")) if sop.is_file() \
        else None
    if template is None or any(f"<{p}>" not in template for p in btcases.PLACEHOLDERS):
        raise BtError([("BT-TEMPLATE-INVALID", "SOP〈反事實回測〉範本缺或缺必含占位符")])
    return obj, raw, found[0], template


def prepare(repo: Path, seed: int, k: int | None, root: str | None, as_json: bool) -> wv.Out:
    """`prepare`：可重現抽樣、repo 外的快照 worktree、任務書與 `batch.json`；失敗整批回退。"""
    git, k = _git(repo), btcases.BT_K_DEFAULT if k is None else k
    base = Path(root) if root else btcases.root_default()
    obj, raw, version, template = _gate(repo, seed, k, base)
    chosen = btcases.pick(obj["cases"], seed, k)
    base.mkdir(parents=True, exist_ok=True)
    first = _next_batch(repo, base)
    for num in range(first, first + 1000):  # 並行 prepare 搶同一號時順延；有界
        batch = f"BT-{num:03d}"
        try:
            (base / batch).mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise wv.UsageError("批號配不到（連續 1000 個都已存在）")
    bdir, made, slots = base / batch, [], []
    try:
        for sub in ("snap", "tasks", "answers"):
            (bdir / sub).mkdir()
        for i, case in enumerate(chosen, 1):
            slot, snap = f"s{i}", bdir / "snap" / f"s{i}"
            cp = git.run("-c", "core.longpaths=true", "worktree", "add", "--detach", str(snap),
                         case["pre_commit"], timeout=_WT_TIMEOUT)
            if cp is None or cp.returncode != 0:
                raise BtError([("BT-WORKTREE-FAILED", f"{slot} 的快照建立失敗")])
            made.append(snap)
            nonce = btcases.nonce_of(batch, case["id"], seed)
            (bdir / "tasks" / f"{slot}.md").write_bytes(
                _task(template, case, slot, snap, nonce).encode("utf-8"))
            slots.append({"slot": slot, "id": case["id"], "snap": str(snap), "nonce": nonce,
                          "pre_commit": case["pre_commit"],
                          "changed_files": case["changed_files"]})
        meta = {"schema_rev": 1, "batch": batch, "seed": seed, "k": k, "created_at":
                btcases.now_iso(), "head_sha": git.head(), "cases_version": version,
                "cases_sha256": btcases.sha_of(raw), "cases": slots}
        (bdir / "batch.json").write_bytes(btcases.dumps(meta).encode("utf-8"))
        (bdir / "binding.json").write_bytes(
            btcases.dumps({"schema_rev": 1, "answers": {}}).encode("utf-8"))
    except BaseException:
        _remove_worktrees(git, made)
        shutil.rmtree(bdir, ignore_errors=True)
        git.run("worktree", "prune")
        raise
    lines = [f"ok backtest prepare batch={batch} seed={seed} k={k} cases_version={version} "
             f"pool={len(obj['cases'])}"]
    lines += [f"  {s['slot']} snap={s['snap']} task={bdir / 'tasks' / (s['slot'] + '.md')}"
              for s in slots]
    return _out(0, lines, as_json, {
        "ok": True, "verb": "backtest", "sub": "prepare", "batch": batch, "seed": seed, "k": k,
        "cases_version": version, "pool": len(obj["cases"]),
        "slots": [{"slot": s["slot"], "snap": s["snap"],
                   "task": str(bdir / "tasks" / (s["slot"] + ".md"))} for s in slots]})


def cleanup(repo: Path, batch: str, root: str | None, as_json: bool) -> wv.Out:
    """`cleanup`：每個快照 `git worktree remove`（不帶強制旗標）；被拒＝`BT-WORKTREE-DIRTY` 並保留
    該目錄、其餘照做；最後 `prune`。"""
    git = _git(repo)
    meta = btcases.load_batch(Path(root) if root else None, batch)
    kept = _remove_worktrees(git, [Path(c["snap"]) for c in meta.get("cases", [])])
    if kept:
        raise BtError([("BT-WORKTREE-DIRTY", f"被 git 拒絕而保留：{p}") for p in kept])
    return _out(0, [f"ok backtest cleanup batch={batch}"], as_json,
                {"ok": True, "verb": "backtest", "sub": "cleanup", "batch": batch})
