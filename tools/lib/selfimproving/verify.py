"""SelfImproving `verify`：三步對照、載具自證、暴露掃描與證據入帳（TCS-SelfImproving-P2 R88～R90）。

能力類別 `exec`：探針只經 `runner.run_probe`；每步每個探針各執行一次（不重試至通過，禁令 4）；
非逾時的失敗不略過其後步驟（證據齊備，由 `verdict.verdict_of` 判級），只有逾時才使其後步驟不執行。
⓪ 沙盒失敗先於預檢：不跑探針、直接收 verdict。證據逐探針落地為 `verify<K>.json`（只新建、重驗失敗
即刪回）。
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

from . import events as si_events
from . import evwrite, heldout, manifest, propfiles, runner, verdict
from . import fold as si_fold
from . import sandbox as si_sandbox
from . import transcript as si_transcript
from . import writeverbs as wv
from .decwrite import Out, UsageError, ok_out, refuse_unattended

_KEYS = ("event_max_bytes", "stop_after_bad", "probe_timeout_seconds", "verify_runs_max",
         "min_heldout")
_VERIFIABLE = ("sandboxed", "verified")
_NEEDLES = ("selfimproving_protocol/params.json", "tools/probe/selfimproving_measure.py")


def _latest(events: list[dict], kind: str, prop: str, rev: int | None = None) -> dict | None:
    hits = [e for e in events if e["kind"] == kind and e.get("prop") == prop
            and (rev is None or e.get("rev") == rev)]
    return hits[-1] if hits else None


def _expand(argv: list[str], held: Path) -> list[str]:
    return [a.replace("{heldout}", str(held)) for a in argv]


def _step(probes: list[dict], held: Path, root: Path, timeout: int) -> tuple[list[dict], bool]:
    """跑一步的全部探針（各恰一次）；逾時即停並回 `timed_out` 為真。"""
    recs: list[dict] = []
    for pr in probes:
        res = runner.run_probe(_expand(pr["argv"], held), cwd=root, sandbox_root=root,
                               timeout=timeout)
        recs.append({"id": pr["id"], "cmd": pr["argv"], "rc": res.rc, "timed_out": res.timed_out,
                     "out_sha256": res.out_sha256, "out_bytes": res.out_bytes,
                     "n_pop": pr["n_pop"], "tail": res.tail})
        if res.timed_out:
            return recs, True
    return recs, False


def _carrier(probes: list[dict], root: Path, timeout: int) -> tuple[bool, dict]:
    """載具自證：每個相異 `module` 在沙盒環境載入，其 `__file__` 須在沙盒樹根之下。"""
    out: dict[str, str] = {}
    real_root = os.path.realpath(root)
    for mod in sorted({p["module"] for p in probes if "module" in p}):
        res = runner.run_probe(["{python}", "-c", f"import {mod}; print({mod}.__file__)"],
                               cwd=root, sandbox_root=root, timeout=timeout)
        lines = [ln for ln in res.tail.splitlines() if ln.strip()]
        path = os.path.realpath(lines[-1]) if res.rc == 0 and lines else ""
        if not path or os.path.commonpath([path, real_root]) != real_root:
            return False, {}
        out[mod] = Path(path).relative_to(real_root).as_posix()
    return True, out


def _all(recs: list[dict], pred) -> bool:
    return all(not r["timed_out"] and r["rc"] is not None and pred(r["rc"]) for r in recs)


def _three_steps(probes, held: Path, root: Path, patch: Path, mutation: Path | None,
                 timeout: int) -> dict:
    """RED→GREEN→突變 RED；逾時使其後步驟不執行；結束後反向套用還原沙盒樹到 base。"""
    steps: dict = {"baseline": [], "patched": [], "mutated": None}
    flags: dict = {"baseline_red": None, "patched_green": None, "mutated_red": None}
    applied: list[Path] = []
    try:
        steps["baseline"], hung = _step(probes, held, root, timeout)
        flags["baseline_red"] = None if hung else _all(steps["baseline"], lambda rc: rc != 0)
        if not hung:
            si_sandbox.apply_patch(root, patch, timeout)
            applied.append(patch)
            steps["patched"], hung = _step(probes, held, root, timeout)
            flags["patched_green"] = None if hung else _all(steps["patched"], lambda rc: rc == 0)
        if not hung and mutation is not None:
            si_sandbox.apply_patch(root, mutation, timeout)
            applied.append(mutation)
            steps["mutated"], hung = _step(probes, held, root, timeout)
            flags["mutated_red"] = None if hung else _all(steps["mutated"], lambda rc: rc != 0)
    except si_sandbox.SandboxError:
        pass  # 套用失敗（沙盒階段已判過，此處不應發生）：該步欄位維持 None，由判定層收 NE
    finally:
        for patch_path in reversed(applied):
            si_sandbox.reverse_apply(root, patch_path, timeout)
    return {"steps": steps, **flags, "timed_out": hung}


def _evidence(prop: str, ev: dict, k: int, digest, carrier: dict, steps: dict) -> str:
    obj = {"schema_rev": 1, "prop": prop, "rev": ev["rev"], "k": k, "base": ev["base"],
           "heldout_digest": digest, "carrier": carrier, "steps": steps}
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _gate(events: list, f, ns, params: dict) -> tuple[list, object, dict | None]:
    p = f.props.get(ns.prop)
    if p is None:
        return [("PROP-NOT-FOUND", f"{ns.prop} 不存在")], None, None
    codes: list = []
    if p.state not in _VERIFIABLE:  # 態不符即定案：其後的凍結、次數判準對該態無意義
        why = f"{p.id} 為 {p.state}，只收 sandboxed 或 verified"
        return [("STATE-NOT-VERIFIABLE", why)], p, None
    freeze = _latest(events, "heldout.freeze", p.id)
    if freeze is None:
        codes.append(("HELDOUT-NOT-FROZEN", "同 PROP 沒有 heldout.freeze"))
    done = sum(1 for e in events if e["kind"] == "app.verify" and e.get("prop") == p.id
               and e.get("rev") == p.rev)
    if done >= params["verify_runs_max"]:
        codes.append(("VERIFY-RUNS-EXCEEDED", f"同 (prop, rev) 的 app.verify 已達 "
                                              f"{params['verify_runs_max']} 次，須升級人工"))
    return codes, p, freeze


def _tree_problems(repo, ns, si: Path, ev: dict, sb: dict, params: dict, tree: Path) -> list:
    """沙盒樹 manifest 須等於 `sandbox_sha256`；不符或不在則重新匯出，仍不符＝漂移。回拒收碼
    （空＝可用）；換入失敗另碼 `SANDBOX-SWAP-FAILED`（不借 `SANDBOX-TREE-DRIFT`：成因是檔案系統
    而非他機差異）。"""
    if tree.is_dir() and manifest.tree_manifest(tree) == sb["sandbox_sha256"]:
        return []
    patch, touched = si_sandbox.prop_context(repo, ev)
    memory_dir = getattr(ns, "memory_dir", None)
    if ev.get("cls") == "M" and not memory_dir:  # M 類樹自記憶目錄組裝，重建同樣要它（R88 勘誤三）
        return [("MEMORY-DIR-MISSING", "M 類沙盒樹重建須給 --memory-dir")]
    tmp = si / "sandbox" / f".tmp-{ev['id']}-{os.getpid()}"
    tar = tmp.with_suffix(".tar")
    if tmp.exists():
        si_sandbox.rmtree(tmp)
    (si / "sandbox").mkdir(parents=True, exist_ok=True)
    try:
        res = si_sandbox.assemble(repo, ev, patch, touched,
                                  Path(memory_dir) if memory_dir else None, tmp, tar,
                                  params["probe_timeout_seconds"])
        if res.sha != sb["sandbox_sha256"]:
            return [("SANDBOX-TREE-DRIFT", "沙盒樹與 sandbox_sha256 不符，重新匯出後仍不符"
                                           "（他機或 git 版本差異）")]
        if tree.exists():
            si_sandbox.rmtree(tree)
        try:
            si_sandbox.swap_dir(tmp, tree)
        except si_sandbox.SandboxError as exc:
            return [(exc.code, exc.detail)]
        return []
    finally:
        tar.unlink(missing_ok=True)
        if tmp.exists():
            si_sandbox.rmtree(tmp)


def run(repo: Path, ns, as_json: bool) -> Out:
    if not si_events.valid_by(ns.by):
        raise UsageError("--by 須為非空、無空白、≤32 字元的標籤")
    if not si_events.PROP_RE.match(ns.prop):
        raise UsageError("位置參數須為 PROP-SI-NNN")
    if ns.mutation is not None and not Path(ns.mutation).is_file():
        raise UsageError(f"--mutation 不是檔案：{ns.mutation}")
    refused = refuse_unattended(repo, "verify", as_json)
    if refused:
        return refused
    params = wv.params_for(repo, *_KEYS)
    si = si_events.si_dir()
    try:
        evwrite.ensure_home(si)
    except evwrite.HomeUnwritable as exc:
        raise UsageError(f"HOME-UNWRITABLE {exc}") from exc
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
    f = si_fold.fold(events, params["stop_after_bad"])
    codes, p, freeze = _gate(events, f, ns, params)
    if codes:
        return wv.reject(repo, "verify", codes, as_json)
    ev = next(e for e in reversed(events) if e["kind"] == "prop" and e["id"] == p.id
              and e["rev"] == p.rev)
    sb = _latest(events, "app.sandbox", p.id, p.rev) or {}
    held = si / "heldout" / p.id
    fields = _measure(repo, ns, si, params, ev, sb, freeze, held, as_json)
    if isinstance(fields, wv.Out):  # 拒收（含 TREE-DRIFT、SWAP-FAILED）；decwrite.Out 是它的子類
        return Out(fields.rc, fields.text)
    return _commit(repo, ns, params, p, ev, sb, freeze, fields, as_json)


def _measure(repo, ns, si, params, ev, sb, freeze, held, as_json):
    """回量測欄位 dict，或（拒收，形態隨 `as_json`）`Out`。⓪ 路徑不預檢、不跑探針。"""
    prop = ev["id"]
    empty = {"probes_n": 0, "baseline_red": None, "patched_green": None, "mutated_red": None,
             "carrier_proof": None, "verify_sha256": None, "heldout_digest": None,
             "reasons": [], "file": None}
    if verdict.sandbox_layer(sb) is not None:
        return empty
    digest = manifest.tree_manifest(held) if held.is_dir() else None
    tree = si / "sandbox" / prop
    bad = _tree_problems(repo, ns, si, ev, sb, params, tree)
    if bad:
        return wv.reject(repo, "verify", bad, as_json)
    loaded = heldout.load(held) if held.is_dir() else heldout.Loaded(None, [])
    data = loaded.data
    mutation = _mutation(ns, held, data)
    recorded: list[str] = []
    when = datetime.fromisoformat(freeze["t"])
    hit = si_transcript.exposure(repo, str(held), list(_NEEDLES), when, ev["id"],
                                 datetime.fromisoformat(ev["t"]))
    recorded += [hit] if hit else []
    probes = (data or {}).get("probes") or []
    out = dict(empty, probes_n=len(probes), heldout_digest=digest)
    if not probes:
        out["reasons"] = recorded
        return out
    patch, _ = si_sandbox.prop_context(repo, ev)
    timeout = params["probe_timeout_seconds"]
    proof, carrier = _carrier(probes, tree, timeout)
    got = _three_steps(probes, held, tree, patch, mutation, timeout)
    recorded += ["PROBE-TIMEOUT"] if got["timed_out"] else []
    k = sum(1 for e in si_events.load_sound_events(repo / si_events.LEDGER_REL) or []
            if e["kind"] == "app.verify" and e.get("prop") == prop) + 1
    out.update(carrier_proof=proof, baseline_red=got["baseline_red"],
               patched_green=got["patched_green"], mutated_red=got["mutated_red"],
               reasons=recorded, file=(k, _evidence(prop, ev, k, digest, carrier, got["steps"])))
    return out


def _mutation(ns, held: Path, data) -> Path | None:
    own = (data or {}).get("mutation")
    if ns.mutation is not None and own is not None:
        raise UsageError("突變來源二擇一：manifest 已有 mutation，不可再給 --mutation")
    if ns.mutation is not None:
        return Path(ns.mutation)
    return held / own if own else None


def _commit(repo, ns, params, p, ev, sb, freeze, fields: dict, as_json: bool) -> Out:
    written: list[Path] = []
    file = fields.pop("file")
    if file is not None:
        k, text = file
        written.append(propfiles.write_verify(repo, p.id, k, text))
        fields["verify_sha256"] = "sha256:" + hashlib.sha256(
            text.replace("\r\n", "\n").encode("utf-8")).hexdigest()
    verdict_, reasons = verdict.verdict_of(sb, fields, freeze, params["min_heldout"])
    fields["reasons"] = reasons

    def build(state):
        f2 = si_fold.fold(state.events, params["stop_after_bad"])
        cur = f2.props.get(p.id)
        runs = sum(1 for e in state.events if e["kind"] == "app.verify" and e.get("prop") == p.id
                   and e.get("rev") == p.rev)
        if (cur is None or cur.state not in _VERIFIABLE or cur.digest != p.digest
                or runs >= params["verify_runs_max"]):
            raise evwrite.Reject([("STATE-CHANGED", "鎖內重驗：PROP 態、digest 或驗證次數已變")])
        state.cleanups.append(lambda: propfiles.remove(written))
        nums = [int(e["id"].rsplit("-", 1)[1]) for e in state.events
                if e["kind"].startswith("app.")]
        return {"kind": "app.verify", "by": ns.by, "id": f"APP-SI-{max(nums, default=0) + 1:03d}",
                "prop": p.id, "rev": ev["rev"], "verdict": verdict_,
                "baseline_red": fields["baseline_red"], "patched_green": fields["patched_green"],
                "mutated_red": fields["mutated_red"], "carrier_proof": fields["carrier_proof"],
                "probes_n": fields["probes_n"], "verify_sha256": fields["verify_sha256"],
                "heldout_digest": fields["heldout_digest"], "reasons": reasons}

    def render(e):
        base = [("verdict", e["verdict"]), ("probes_n", e["probes_n"]), ("reasons", e["reasons"])]
        more = [(k, e[k]) for k in ("baseline_red", "patched_green", "mutated_red",
                                    "carrier_proof")] if as_json else []
        return ok_out("app.verify", e["seq"], e["id"], base + more, as_json).text
    out = wv.append(repo, "verify", build, params, as_json, render)
    if out.rc != 0:
        propfiles.remove(written)
        return Out(out.rc, out.text)
    if verdict_ == "PASS":
        return Out(0, out.text)
    draft = wv.draft_for(repo, "verify", [(c, "") for c in reasons], symptom=(
        f"si verify 判 {verdict_}：{'、'.join(reasons)}（{p.id}）"))
    if as_json:
        obj = json.loads(out.text)
        obj["obs_draft"] = draft
        return Out(0, json.dumps(obj, ensure_ascii=False) + "\n")
    return Out(0, out.text + "obs-draft:\n" + draft + "\n")
