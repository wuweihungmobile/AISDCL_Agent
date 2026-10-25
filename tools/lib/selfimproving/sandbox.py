"""SelfImproving 沙盒：匯出到樹外、抽取預檢、套用、`touched` 與回滾乾跑（TCS-P2 R85、R86）。

能力類別 `rw`：只寫家目錄 `<si>/sandbox/<PROP>`（先在暫名目錄組裝、鎖內重驗後換入），正式面零變更。
清理＝丟棄該 PROP 的副本目錄樹（絕不經 git，鐵律五）。P2 全部 `git apply` 與 `git archive` 一律帶
`-c core.autocrlf=false`：Git for Windows 的系統層 `core.autocrlf=true` 會把無 `.git` 樹內被改的檔
整個寫成 CRLF，正向加反向套用後與 base 逐位元不同。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import tarfile
from dataclasses import dataclass, field
from pathlib import Path

from . import decverify, evwrite, heldout, manifest
from . import events as si_events
from . import fold as si_fold
from . import paths as si_paths
from . import refs as si_refs
from . import writeverbs as wv
from .decwrite import Out, UsageError, ok_out, refuse_unattended
from .git import Git

_NOCRLF = ("-c", "core.autocrlf=false")
_FORCE_KEYS = ("event_max_bytes", "stop_after_bad", "probe_timeout_seconds")
_REPARSE = 0x400
_CTL = {chr(c) for c in range(0x20)} | {chr(0x7F)}


class SandboxError(Exception):
    """沙盒階段的失敗；`code` 為成因碼（R85 (g)）。"""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code} {detail}".strip())
        self.code, self.detail = code, detail


@dataclass
class Result:
    applied: bool
    touched_ok: bool | None
    rollback_ok: bool | None
    fail_code: str | None
    sha: str | None
    causes: list = field(default_factory=list)


def _member_reason(m: tarfile.TarInfo) -> str | None:
    name = m.name
    segs = name.replace("\\", "/").split("/")
    bad = (".." in segs or name.startswith(("/", "\\")) or ":" in name
           or any(ch in _CTL for ch in name) or any(s.endswith((".", " ")) and s for s in segs)
           or not (m.isreg() or m.isdir()))
    return "SANDBOX-MEMBER-REJECTED" if bad else None


def precheck_members(tar_path, root: Path) -> list[tuple[str, str]]:
    """先於任何寫入檢查 tar 的每個成員；回 [(成員名, 原因碼)]（空＝通過）。"""
    out, seen = [], set()
    with tarfile.open(tar_path) as tf:
        members = tf.getmembers()
    for m in members:
        reason = _member_reason(m)
        key = m.name.rstrip("/")
        if key in seen:
            reason = reason or "SANDBOX-MEMBER-REJECTED"
        seen.add(key)
        if reason is None and manifest.path_too_long(Path(root), [m.name.rstrip("/")]):
            reason = "SANDBOX-PATH-TOO-LONG"
        if reason:
            out.append((m.name, reason))
    return out


def extract_checked(tar_path, root: Path) -> None:
    """預檢加 `extractall(…, filter="data")`；預檢不過拋 `SandboxError`（先於任何寫入）。"""
    if not hasattr(tarfile, "data_filter"):
        raise SandboxError("TARFILE-FILTER-MISSING", "直譯器無 tarfile.data_filter，不降級")
    bad = precheck_members(tar_path, root)
    if bad:
        raise SandboxError(bad[0][1], "、".join(name for name, _ in bad))
    Path(root).mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar_path) as tf:
        tf.extractall(root, filter="data")


def apply_patch(root: Path, patch_path: Path, timeout: int | None = None) -> set[str]:
    """`git -c core.autocrlf=false apply`（cwd＝沙盒根）；回實際寫入的路徑集合（前後樹差異）。"""
    before = _hashes(root)
    git = Git(root)
    cp = git.run(*_NOCRLF, "apply", str(patch_path), timeout=timeout)
    if git.timed_out:
        raise SandboxError("SANDBOX-APPLY-TIMEOUT", "git apply 逾時")
    if cp is None or cp.returncode != 0:
        raise SandboxError("SANDBOX-APPLY-FAILED", (cp.stderr if cp else "git 不可用").strip())
    after = _hashes(root)
    return {rel for rel in before.keys() | after.keys() if before.get(rel) != after.get(rel)}


def reverse_apply(root: Path, patch_path: Path, timeout: int | None = None) -> bool:
    cp = Git(root).run(*_NOCRLF, "apply", "-R", str(patch_path), timeout=timeout)
    return bool(cp is not None and cp.returncode == 0)


def _hashes(root: Path) -> dict[str, str]:
    return {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest()
            for rel in manifest.tree_files(root)}


def _export(repo: Path, base: str, tar_path: Path, root: Path, timeout: int) -> None:
    git = Git(repo)
    cp = git.run(*_NOCRLF, "archive", "--format=tar", f"--output={tar_path}", base,
                 timeout=timeout)
    if git.timed_out:
        raise SandboxError("SANDBOX-EXPORT-TIMEOUT", f"git archive 超過 {timeout} 秒")
    if cp is None or cp.returncode != 0:
        raise SandboxError("SANDBOX-GIT-FAILED", (cp.stderr if cp else "git 不可用").strip())
    extract_checked(tar_path, root)


def _export_memory(memory_dir: Path, touched, root: Path) -> None:
    for rel in sorted(touched):
        src = memory_dir / rel.split("/", 1)[1] if rel.startswith("memory/") else None
        if src is not None and src.is_file():
            dst = root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
    root.mkdir(parents=True, exist_ok=True)


def assemble(repo: Path, ev: dict, patch_path: Path, touched, memory_dir: Path | None,
             root: Path, tar_path: Path, timeout: int) -> Result:
    """在暫名根組裝沙盒：匯出→抽取預檢→套用→`touched` 判→回滾乾跑；結束時樹回到 base 狀態。"""
    try:
        if memory_dir is None:
            _export(repo, ev["base"], tar_path, root, timeout)
        else:
            _export_memory(memory_dir, touched, root)
    except SandboxError as exc:
        return Result(False, None, None, "SANDBOX-EXPORT-FAILED", None, [(exc.code, exc.detail)])
    sha = manifest.tree_manifest(root)
    try:
        changed = apply_patch(root, patch_path, timeout)
    except SandboxError as exc:
        return Result(False, None, None,
                      "SANDBOX-APPLY-TIMEOUT" if exc.code == "SANDBOX-APPLY-TIMEOUT" else None,
                      sha)
    allowed = {p.replace("\\", "/") for p in touched}
    touched_ok = {p.replace("\\", "/") for p in changed} <= allowed
    undone = reverse_apply(root, patch_path, timeout)
    return Result(True, touched_ok, bool(undone) and manifest.tree_manifest(root) == sha, None, sha)


def _is_link_path(path: Path) -> bool:
    if os.path.islink(path):
        return True
    attrs = getattr(os.lstat(path), "st_file_attributes", 0) if os.path.lexists(path) else 0
    return bool(attrs & _REPARSE)


def rmtree(path: Path) -> None:
    def fix(func, p, _exc):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    shutil.rmtree(path, onerror=fix)


def swap_dir(src: Path, dst: Path) -> None:
    """目錄換入的唯一原語（單次嘗試、不重試）：`OSError` 一律轉 `SANDBOX-SWAP-FAILED`（detail＝
    例外類名），不讓原生例外外洩；呼叫端各自轉成 rc 1 的拒收（寫入鎖內）或拒收碼（`verify`）。"""
    try:
        os.replace(src, dst)
    except OSError as exc:
        raise SandboxError("SANDBOX-SWAP-FAILED", type(exc).__name__) from exc


def _root_guard(repo: Path, si: Path, prop: str) -> Path:
    """R85 (a)：沙盒根不得在 repo 樹內或 `.claude/worktrees/` 之下；清理目標本身不得是連結。"""
    box = si / "sandbox"
    real_box, real_repo = os.path.realpath(box), os.path.realpath(repo)
    try:
        inside = os.path.commonpath([real_box, real_repo]) == real_repo
    except ValueError:  # Windows：家目錄與 repo 在不同磁碟機 ⇒ 沒有共同路徑，當然不在 repo 內
        inside = False
    frag = ".claude/worktrees/"
    if inside or any(frag in str(x).replace("\\", "/") + "/" for x in (box, real_box)):
        raise UsageError("SANDBOX-ROOT-IN-REPO 沙盒根在 repo 樹內或 .claude/worktrees/ 之下")
    final = box / prop
    if _is_link_path(final):
        raise UsageError(f"SANDBOX-ROOT-IN-REPO 清理目標 {final} 本身是連結，不得清理")
    return final


def prop_context(repo: Path, ev: dict) -> tuple[Path, list[str]]:
    d = repo / si_events.PROPOSALS_REL / ev["id"]
    patch = d / f"r{ev['rev']}.patch"
    return patch, si_paths.touched_of(patch.read_bytes())


def _gate_codes(repo: Path, ns, f, events: list, params: dict, p, ev: dict) -> list:
    """R86 前置（rc 1）：態、凍結、記憶目錄、digest；其後才回查 `dec(approve)`。"""
    if p.state != "approved":
        return [("STATE-NOT-APPROVED", f"{p.id} 為 {p.state}，只收 approved")]
    codes = []
    if not any(e["kind"] == "heldout.freeze" and e.get("prop") == p.id for e in events):
        codes.append(("HELDOUT-NOT-FROZEN", "同 PROP 沒有 heldout.freeze（凍結須先於沙盒）"))
    if p.cls == "M" and not ns.memory_dir:
        codes.append(("MEMORY-DIR-MISSING", "M 類須給 --memory-dir"))
    approve = [e for e in events if e["kind"] == "dec" and e.get("prop") == p.id
               and e.get("dkind") == "approve"]
    now = decverify.recompute_digest(repo, ev)
    if now is None or now != ev["digest"] or (approve and approve[-1].get("digest") != now):
        codes.append(("DIGEST-MISMATCH", "自 rN.patch、rN.md 重算的 digest 不同於事件或核准時者"))
    if codes:
        return codes
    gate = decverify.dec_gate(decverify.Ctx(repo, events, Git(repo), params), approve[-1]
                              if approve else None)
    return [gate] if gate else []


def run(repo: Path, ns, as_json: bool) -> Out:
    if not si_events.valid_by(ns.by):
        raise UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    if not si_events.PROP_RE.match(ns.prop):
        raise UsageError("位置參數須為 PROP-SI-NNN")
    refused = refuse_unattended(repo, "sandbox", as_json)
    if refused:
        return refused
    params = wv.params_for(repo, *_FORCE_KEYS)
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    if not hasattr(tarfile, "data_filter"):
        raise UsageError("TARFILE-FILTER-MISSING 直譯器無 tarfile.data_filter，不降級")
    final = _root_guard(repo, si, ns.prop)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    p = f.props.get(ns.prop)
    if p is None:
        return wv.reject(repo, "sandbox", [("PROP-NOT-FOUND", f"{ns.prop} 不存在")], as_json)
    ev = next(e for e in reversed(events) if e["kind"] == "prop" and e["id"] == p.id
              and e["rev"] == p.rev)
    codes = _gate_codes(repo, ns, f, events, params, p, ev)
    if codes:
        return wv.reject(repo, "sandbox", codes, as_json)
    patch_path, touched = prop_context(repo, ev)
    tmp = si / "sandbox" / f".tmp-{p.id}-{os.getpid()}"
    tar = tmp.with_suffix(".tar")
    for stale in (tmp, tar):
        rmtree(stale) if stale.is_dir() else stale.unlink(missing_ok=True)
    (si / "sandbox").mkdir(parents=True, exist_ok=True)
    try:
        memory = Path(ns.memory_dir) if ns.memory_dir else None
        res = assemble(repo, ev, patch_path, touched, memory, tmp, tar,
                       params["probe_timeout_seconds"])
        return _commit(repo, ns, params, p, ev, res, tmp, final, as_json)
    finally:
        tar.unlink(missing_ok=True)
        if tmp.exists():
            rmtree(tmp)


def _commit(repo, ns, params, p, ev, res: Result, tmp: Path, final: Path, as_json) -> Out:
    backup = final.with_name(f".old-{p.id}-{os.getpid()}")

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        cur = f2.props.get(p.id)
        if cur is None or cur.state != "approved" or cur.digest != p.digest:
            raise evwrite.Reject([("STATE-CHANGED", "鎖內重驗：PROP 態或 digest 已變")])
        nums = [int(e["id"].rsplit("-", 1)[1]) for e in state.events
                if e["kind"].startswith("app.")]
        if tmp.exists():
            try:
                if final.exists():
                    swap_dir(final, backup)
                # 還原登記在第一次換入之後、第二次之前：第二次失敗時舊沙盒也要搬回（R71）
                state.cleanups.append(lambda: _undo(final, backup))
                swap_dir(tmp, final)
            except SandboxError as exc:
                raise evwrite.Reject([(exc.code, exc.detail)]) from exc
        return {"kind": "app.sandbox", "by": ns.by, "id": f"APP-SI-{max(nums, default=0) + 1:03d}",
                "prop": p.id, "rev": ev["rev"], "base": ev["base"], "sandbox_sha256": res.sha,
                "applied": res.applied, "touched_ok": res.touched_ok,
                "rollback_ok": res.rollback_ok, "fail_code": res.fail_code}

    def render(e):
        return ok_out("app.sandbox", e["seq"], e["id"], [
            ("applied", e["applied"]), ("touched_ok", e["touched_ok"]),
            ("rollback_ok", e["rollback_ok"]), ("fail_code", e["fail_code"])], as_json).text
    out = wv.append(repo, "sandbox", build, params, as_json, render)
    if out.rc != 0:
        return Out(out.rc, out.text)
    if backup.exists():
        rmtree(backup)
    err = "".join(f"{c} {d}\n" for c, d in res.causes)
    text = out.text
    if not res.applied and not as_json:
        draft = wv.draft_for(repo, "sandbox", [("SANDBOX-NOT-APPLIED", "")], symptom=(
            f"si sandbox 未套用：applied=false fail_code={res.fail_code}（{p.id}）"))
        text += "obs-draft:\n" + draft + "\n"
    return Out(0, text, err)


def _undo(final: Path, backup: Path) -> None:
    if final.exists():
        rmtree(final)
    if backup.exists():
        try:
            os.replace(backup, final)
        except OSError:
            pass  # 還原是盡力而為（cleanup 語意）；雙重失敗時舊沙盒仍完整留在 `.old-*`


_FREEZE_ILLEGAL = ("rejected", "handed-off", "promoted", "measuring", "closed")


def _freeze_codes(repo: Path, ns, f, events: list, si: Path) -> list:
    """`heldout-freeze` 的政策與狀態類碼（R83 (b)）；PROP 不存在由呼叫端先判。"""
    p, codes = f.props[ns.prop], []
    final = si / "heldout" / ns.prop
    if p.route.startswith("handoff:"):
        codes.append(("ROUTE-HANDOFF", "handoff 路由的 PROP 不進沙盒、不凍結"))
    if final.exists() or any(e["kind"] == "heldout.freeze" and e.get("prop") == ns.prop
                             for e in events):
        codes.append(("HELDOUT-EXISTS", f"{ns.prop} 已凍結過（每 PROP 至多一次）"))
    if p.sandbox_seq is not None:
        codes.append(("HELDOUT-AFTER-SANDBOX", "該 PROP 已有 app.sandbox，凍結須先於沙盒"))
    if p.state in _FREEZE_ILLEGAL:
        codes.append(("PROP-STATE-ILLEGAL", f"{ns.prop} 為 {p.state}，不可凍結 held-out"))
    if ns.by == p.proposer:
        codes.append(("FROZEN-BY-PROPOSER", "凍結者不得等於該 PROP 的提案者"))
    src = Path(ns.src)
    if (si / "heldout").resolve() in (src.resolve(), *src.resolve().parents):
        codes.append(("HELDOUT-FROM-INSIDE", "--from 不得在家目錄的 heldout 之內"))
    if heldout.find_links(src):
        codes.append(("HELDOUT-LINK", "--from 目錄內含符號連結"))
    known = set(si_refs.obs_rows(repo)) | si_refs.def_ids(repo)
    return codes + heldout.load(src, known).problems


def heldout_freeze(repo: Path, ns, as_json: bool) -> wv.Out:
    """`heldout-freeze`（R83）：把 `--from` 全部檔案複製進家目錄並把 digest 記入帳本。"""
    refused = refuse_unattended(repo, "heldout-freeze", as_json)  # R70：先於其餘一切前置檢查
    if refused:
        return refused
    if not si_events.valid_by(ns.by):
        raise UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    src = Path(ns.src)
    if not src.is_dir():
        raise UsageError(f"--from 不存在或不是目錄：{src}")
    params = wv.params_for(repo, "event_max_bytes", "stop_after_bad")
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    if ns.prop not in f.props:
        return wv.reject(repo, "heldout-freeze", [("PROP-NOT-FOUND", f"{ns.prop} 不存在")], as_json)
    codes = _freeze_codes(repo, ns, f, events, si)
    if codes:
        return wv.reject(repo, "heldout-freeze", codes, as_json)
    root = si / "heldout"
    tmp = root / f".tmp-{ns.prop}-{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(src, tmp)
    final = root / ns.prop
    info = {"n": len(heldout.load(tmp).data["cases"]), "digest": manifest.tree_manifest(tmp)}

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        p2 = f2.props.get(ns.prop)
        again = any(e["kind"] == "heldout.freeze" and e.get("prop") == ns.prop
                    for e in state.events)
        if p2 is None or p2.state in _FREEZE_ILLEGAL or p2.sandbox_seq is not None or again \
                or final.exists():
            raise evwrite.Reject([("STATE-CHANGED", "寫入鎖內重驗：PROP 態或凍結狀況已變")])
        try:
            swap_dir(tmp, final)
        except SandboxError as exc:
            raise evwrite.Reject([(exc.code, exc.detail)]) from exc
        state.cleanups.append(lambda: shutil.rmtree(final, ignore_errors=True))
        return {"kind": "heldout.freeze", "by": ns.by, "prop": ns.prop, "digest": info["digest"],
                "n": info["n"], "frozen_by": ns.by}

    def render(e):
        return wv.ok_text("heldout.freeze", e["seq"], None, [
            ("prop", ns.prop), ("n", e["n"]), ("digest8", e["digest"].split(":", 1)[-1][:8])],
            as_json)
    try:
        return wv.append(repo, "heldout-freeze", build, params, as_json, render)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


__all__ = ["heldout_freeze", "SandboxError", "precheck_members", "extract_checked", "apply_patch",
           "reverse_apply", "assemble", "run"]
