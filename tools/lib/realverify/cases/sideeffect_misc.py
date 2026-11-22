# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""sideeffect 家族（六）：RV-SE03（全批快照差異為空）、RV-SE11（既有家族每案快照）、RV-SE14（PRD 只追加與 REQ-SE-61 範圍）、
RV-SE16（F5 自身副作用進帳）。RV-SE03／SE11 的父案例**不**走 schtasks 全域鎖（子 runner 內的 sched 案例要拿它）。"""
from __future__ import annotations

import ast
import difflib
import re
import subprocess
import time
from pathlib import Path

from .. import interactive, leases, snapshot
from ..driver import EnvMissing
from ..sandbox import REPO, claude_home
from . import CaseContext, case
from .sessionctl_park import PY, run
from .sideeffect_lib import control_dir, ledger_names, new_run_tokens, plain_env, unclosed_ledgers

_RV = [PY, str(REPO / "tools" / "realverify.py")]
LEDGER_MD = REPO / "docs" / "06_quality" / "RealVerify_Result_Ledger.md"


def _child(*args: str, timeout: int):
    return run([*_RV, *args], cwd=REPO, env=plain_env(), timeout=timeout)


def _claude_json_keys() -> list[str]:
    p = claude_home().parent / ".claude.json"  # 唯讀：只取 projects 鍵名
    return snapshot._claude_json_keys(p)  # noqa: SLF001 — 與快照同一個取數函式


def _batch_leak_check(ctx: CaseContext, label: str, out: str, before_snap: dict, before_ledgers: set[str]) -> None:
    after = snapshot.take()
    toks = new_run_tokens(before_ledgers)
    items = snapshot.diff(before_snap, after, toks)
    hits = [i for i in items if i["token"]]
    ctx.check(not hits, f"{label}：整體 diff 含本批字樣項應為 0：{[snapshot.fmt(i) for i in hits[:5]]}")
    ctx.check("SIDE-EFFECT LEAK" not in out, f"{label}：任何案例 detail 都不該含 SIDE-EFFECT LEAK")
    last = [ln for ln in out.splitlines() if ln.startswith("REALVERIFY_VERDICT=")]
    ctx.check(bool(last) and "reason=leak" not in last[-1] and "reason=orphans" not in last[-1], f"{label}：判決不得因 leak／orphans 失敗：{last[-1:]}")
    ctx.check(before_snap["claude_json"] == after["claude_json"] == _claude_json_keys(), f"{label}：~/.claude.json 鍵名集合前後應相同")
    bad = unclosed_ledgers(ledger_names() - before_ledgers)
    ctx.check(not bad, f"{label}：本批所有帳檔都應 closed：{bad}")
    ctx.evidence(f"{label}：diff 含字樣項 0（總差異 {len(items)} 項為並行噪音）、本批 {len(toks)} 個字樣、帳檔全 closed、claude.json 鍵名不變、判決 {last[-1][:90] if last else '?'}")


@case("RV-SE03", "sideeffect", refs=("E2E-SE-03",))
def rv_se03(ctx: CaseContext) -> None:
    """全批快照差異為空：`snapshot --out`→`run --all`（非 long；案例清單不含任何 `RV-SE*`、結果帳本批無 sideeffect 列）→`snapshot --out`→
    `snapshot --diff --tokens`：含字樣項 0、`~/.claude.json` 鍵名不變、本批所有帳檔 closed、判決不因 leak／orphans 失敗。
    本案例會花真額度（既有案例的 `claude -p` haiku 呼叫）；耗時以分鐘計，請以 `sessionctl runlong` 分段等。"""
    d = control_dir(ctx)
    before_ledgers, ledger0 = ledger_names(), (LEDGER_MD.read_text(encoding="utf-8") if LEDGER_MD.is_file() else "")
    b, a = d / "before.json", d / "after.json"
    ctx.check(_child("snapshot", "--out", str(b), timeout=300).returncode == 0, "snapshot --out(before) 失敗")
    before_snap = snapshot.load(b)
    r = _child("run", "--all", timeout=14_400)
    out = r.stdout + r.stderr
    ctx.check(_child("snapshot", "--out", str(a), timeout=300).returncode == 0, "snapshot --out(after) 失敗")
    ids = re.findall(r"^\[(?:PASS|FAIL|ENV )\s*\] (RV-[A-Za-z0-9\-]+)", out, flags=re.M)
    ctx.check(bool(ids) and not [i for i in ids if i.startswith("RV-SE")], f"`run --all` 的案例清單不得含 RV-SE*（D-19）：{[i for i in ids if i.startswith('RV-SE')]}")
    ledger1 = LEDGER_MD.read_text(encoding="utf-8") if LEDGER_MD.is_file() else ""
    ctx.check("sideeffect" not in ledger1[len(ledger0):] and "RV-SE" not in ledger1[len(ledger0):], "結果帳本批不得有 sideeffect／sideeffect_selftest 列")
    _batch_leak_check(ctx, "run --all", out, before_snap, before_ledgers)
    ctx.evidence(f"run --all rc={r.returncode}：{len(ids)} 案；" + (re.findall(r"^REALVERIFY_VERDICT=.*$", out, flags=re.M) or ["?"])[-1][:200])
    if r.returncode != 0:
        ctx.notes.append("run --all 本身非 0（非 leak／orphans）：" + "；".join(ln for ln in out.splitlines() if ln.startswith(("[FAIL", "[ENV")))[:600])


@case("RV-SE11", "sideeffect", refs=("E2E-SE-11",))
def rv_se11(ctx: CaseContext) -> None:
    """真跑既有 park／parkroute／watch／keepwarm 家族案例（`RV-K*`、`RV-PR1`、`RV-PR2`、`sessionctl_watch`、`sessionctl_keepwarm`；
    不含 long），每案前後快照由 runner 自帶；本案例另以整批前後快照＋本批帳字樣確認真 `~/.autosdd`
    （handoff／handback／plans／context_feed／traces/park）無含沙盒字樣的新檔或改動。"""
    before_ledgers = ledger_names()
    before_snap = snapshot.take()
    outs, problems = [], []
    for fam in ("sessionctl_park", "sessionctl_parkroute", "sessionctl_watch", "sessionctl_keepwarm"):
        r = _child("run", "--family", fam, timeout=5_400)
        out = r.stdout + r.stderr
        outs.append(out)
        if r.returncode != 0:
            problems.append(f"{fam} rc={r.returncode}：{[ln[:110] for ln in out.splitlines() if ln.startswith(('[FAIL', '[ENV'))][:4]}")
        ctx.check("SIDE-EFFECT LEAK" not in out, f"家族 {fam} 任一案例都不該有 SIDE-EFFECT LEAK")
    _batch_leak_check(ctx, "park／watch／keepwarm 家族", "\n".join(outs), before_snap, before_ledgers)
    ctx.check(not problems, "既有家族案例應全過（四個家族都跑完才判）：" + "；".join(problems))

def _char_subsequence(small: str, big: str) -> bool:
    it = iter(big)
    return all(ch in it for ch in small)


@case("RV-SE14", "sideeffect", refs=("E2E-SE-14",))
def rv_se14(ctx: CaseContext) -> None:
    """真 repo：(1) 以修憲前 blob 對工作樹 PRD 跑「只追加」判準——修憲前每行在新檔中逐字存在且相對次序不變，例外限 ≤3 行且為某新行的字元子序列
    （R217 三個 hunk）；(2) REQ-SE-61 範圍：workflows／SI／openitems／nightly／local_ci_gate 內沒有「同一呼叫同時含 realverify 與 --all」。"""
    prd = "docs/01_requirements/AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md"
    sha = None
    for cand in ("133c3a38",):
        if subprocess.run(["git", "cat-file", "-e", f"{cand}:{prd}"], cwd=str(REPO), capture_output=True, check=False).returncode == 0:  # noqa: S603,S607
            sha = cand
    ctx.check(sha is not None, "修憲前 blob（133c3a38）取不到：DES 附錄 A 指定的比對基準不存在於本 repo（歷史改寫？）")
    old = subprocess.run(["git", "show", f"{sha}:{prd}"], cwd=str(REPO), capture_output=True, check=True).stdout.decode("utf-8").splitlines()  # noqa: S603,S607
    new = (REPO / prd).read_text(encoding="utf-8").splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    lost = [(i1, old[i1:i2], new[j1:j2]) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag in ("delete", "replace")]
    bad = []
    for i1, olds, news in lost:
        pool = news or []
        for line in olds:
            if not any(_char_subsequence(line, cand) for cand in pool):
                bad.append((i1 + 1, line[:60]))
    ctx.check(not bad, f"PRD 修憲只准追加：修憲前這些行消失或被改寫（且不是新行的字元子序列）：{bad[:5]}")
    inline = sum(len(olds) for _i, olds, news in lost if news)
    ctx.check(inline <= 3, f"行內改動的舊行應 ≤3（R217 三 hunk）：{inline}")
    adds = sum(1 for tag, *_ in matcher.get_opcodes() if tag == "insert")
    # (2) REQ-SE-61
    scope = [".github/workflows", "tools/lib/selfimproving", "tools/lib/openitems", "tools/openitems.py", "tools/run_local_nightly.ps1",
             "tools/run_local_nightly.sh", "tools/install_windows_nightly.ps1"]
    files: list[Path] = []
    for rel in scope:
        p = REPO / rel
        files += sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else ([p] if p.is_file() else [])
    files += sorted((REPO / "tools").glob("local_ci_gate*"))
    hits = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for n, ln in enumerate(text.splitlines(), 1):
            if "realverify" in ln and "--all" in ln:
                hits.append(f"{f.relative_to(REPO)}:{n}")
        if f.suffix == ".py":
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, (ast.List, ast.Call)):
                    toks = " ".join(c.value for c in ast.walk(node) if isinstance(c, ast.Constant) and isinstance(c.value, str))
                    if "realverify" in toks and "--all" in toks:
                        hits.append(f"{f.relative_to(REPO)}:{node.lineno}(AST)")
    ctx.check(not hits, f"REQ-SE-61 範圍內不得出現同一呼叫含 realverify 與 --all：{hits[:5]}")
    ctx.evidence(f"PRD 對 {sha}：舊行全在（行內改動 {inline} 行）、新增段 {adds} 處；REQ-SE-61 範圍 {len(files)} 檔 0 筆")
    ctx.notes.append("誠實劃界：『新增行只落在附錄 A 五處＋豁免來源』無法逐段機械對映（PRD 另有其他並行修憲追加），本案例只判『修憲前每行不丟、次序不變』")


@case("RV-SE16", "sideeffect", refs=("E2E-SE-16",))
def rv_se16(ctx: CaseContext) -> None:
    """F5 自身副作用進帳：`interactive.trusted_sandbox`（真宿主、真隱藏探針；宿主未信任 ⇒ ENV）＋`open_window(visible=False)` 起真
    `claude --model haiku`（不帶提示、零推論）後收：帳依序含 sandbox_root（外層）、worktree、探針 process／temp_file、視窗 process，並全數結清；
    worktree 在 `<外層>/wt` 且探針判 ready；宿主 worktree 登記無殘留。"""
    try:
        sb = interactive.trusted_sandbox(ctx)
    except interactive.NotTrusted as exc:
        raise EnvMissing(f"宿主未信任，判 ENV（不是 PASS）：{exc}") from exc
    ctx.check(sb.trust_verdict == "ready" and sb.root == sb.home / "wt", f"worktree 應在 <外層>/wt 且探針判 ready：{sb.trust_verdict} {sb.root}")
    proc = interactive.open_window(sb, ["--model", "haiku"], visible=False)
    time.sleep(8)
    ctx.check(proc.poll() is None, f"視窗行程應仍在（隱藏主控台、零推論）：rc={proc.poll()}")
    run_id = leases.current_run_id()
    residue = ctx.close()  # 與 runner 收尾同一函式；之後再收一次無妨（冪等）
    ctx.check(not [n for n in residue if n.startswith("RESIDUE")], f"收尾不得有殘留：{residue}")
    rows = [r for r in leases.read_rows(leases.LEASE_DIR / f"{run_id}.jsonl") if r.get("state") == "intent"]
    kinds = [r["kind"] for r in rows]
    ctx.check(kinds[0] == "sandbox_root", f"帳首列應為 sandbox_root（外層）：{kinds[:4]}")
    ctx.check("worktree" in kinds and kinds.index("worktree") > 0, f"帳應有 worktree（在外層之後）：{kinds}")
    procs = [r for r in rows if r["kind"] == "process"]
    probe = [r for r in procs if "trustprobe" in " ".join(map(str, (r.get("meta") or {}).get("keys", [])))]
    window = [r for r in procs if str(r["ident"]).startswith("sid:") and sb.sid in str(r["ident"])]
    ctx.check(bool(probe) and any(r["kind"] == "temp_file" and "trustprobe" in str(r["ident"]) for r in rows) and bool(window), f"帳應含探針 process／temp_file 與視窗 process（以沙盒 sid 為鍵）：{[(r['kind'], str(r['ident'])[:50]) for r in rows]}")
    for kind in ("sandbox_root", "worktree", "process", "temp_file", "transcript_dir"):
        ctx.check(not leases.own_pending(run_id, kind), f"{kind} 帳列應全數結清：{leases.own_pending(run_id, kind)}")
    listed = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=str(interactive.HOST), capture_output=True, text=True, encoding="utf-8", check=False).stdout  # noqa: S603,S607
    ctx.check(str(sb.root).replace("\\", "/").lower() not in listed.replace("\\", "/").lower(), "宿主 worktree 登記不得殘留")
    ctx.evidence(f"帳序 {kinds[:6]}…；探針 ready；視窗行程 8 秒仍在、收尾後全數結清；宿主 worktree 無殘留")
