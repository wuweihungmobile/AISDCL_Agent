# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（A6g）：以 TCS-WorkProgress 逐條 E2E-WP 補案例——真 CLI／真逐字稿／真 `claude -p`／真 git。
不開互動視窗、不登記任何排程。沙盒 OIR 走 `openitems --root <沙盒> --trace-dir <沙盒>/traces`。"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO, projects_dir
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run
from .wp_oir import CLI, LEDGER_REL, oi, seed_docs

_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
PRD = REPO / "docs" / "01_requirements" / "AutoClaude_Token_監控與喚醒機制_PRD_v2.1.md"
DES = REPO / "docs" / "02_architecture" / "WorkProgress_Axis_Design.md"


def _real(sb, *args: str, timeout: int = 300):
    """對真 repo 跑 `openitems`（唯讀動詞；痕跡導到沙盒）。"""
    return run([PY, CLI, "--trace-dir", str(sb.root / "traces"), *args], cwd=REPO, env=sb.env(), timeout=timeout)


def _last(text: str) -> str:
    rows = [ln for ln in text.splitlines() if ln.strip()]
    return rows[-1] if rows else ""


# ───────────────────────── E2E-WP-01：真 repo scan ─────────────────────────
@case("RV-WP01", "workprogress", refs=("E2E-WP-01", "REQ-WP-04"))
def rv_wp01(ctx: CaseContext) -> None:
    """真 repo `python tools/openitems.py scan`：rc 0、末行 `OPENITEMS_SCAN=mapped=N unmapped=M`、unmapped＝0（A8 後）。
    與 ARC E6（143 處／61 檔）對帳：印出本次命中處數、檔數與差額，差異不靜默吞。"""
    sb = ctx.sandbox(probe_hooks=False)
    r = _real(sb, "scan")
    last = _last(r.stdout)
    m = re.fullmatch(r"OPENITEMS_SCAN=mapped=(\d+) unmapped=(\d+)", last)
    ctx.check(m is not None, f"末行格式不符：{last!r}")
    mapped, unmapped = int(m[1]), int(m[2])
    rows = [ln for ln in r.stdout.splitlines() if re.match(r"^(mapped|UNMAPPED)\s", ln)]
    files = {re.sub(r"^(mapped|UNMAPPED)\s+", "", ln).split(":")[0] for ln in rows}
    ev(ctx, "scan_totals", f"mapped={mapped} unmapped={unmapped} 命中處={mapped + unmapped}（ARC E6 基準 143 處／61 檔；差額 {mapped + unmapped - 143}）、涉及檔={len(files)}（基準差 {len(files) - 61}）")
    bad = [ln[:160] for ln in rows if ln.startswith("UNMAPPED")]
    ctx.check(unmapped == 0 and r.returncode == 0, f"A8 後 unmapped 應為 0、rc 0：rc={r.returncode} unmapped={unmapped}；未對應：{bad}")


# ───────────────────────── E2E-WP-26／27：真機量測類 ─────────────────────────
def _wb2(ctx, sb, sid: str) -> tuple[int, int, str]:
    r = run([PY, str(REPO / "tools" / "probe" / "waste_census.py"), "--wake-metrics", "--sid", sid], cwd=REPO, env=sb.env(), timeout=300)
    out = r.stdout
    ctx.check(r.returncode == 0, f"--wake-metrics rc={r.returncode} {r.stderr[-200:]}")
    m = re.search(r"M-WB2[^\n]*?：(\d+) 件（子代理完成通知 (\d+) 則）", out)
    ctx.check(m is not None, f"沒有 M-WB2 列：{out[-300:]}")
    wb1 = re.search(r"M-WB1 [^\n]*", out)
    return int(m[1]), int(m[2]), (wb1[0].strip() if wb1 else "")


@case("RV-WP26", "workprogress", refs=("E2E-WP-26", "REQ-WP-33"))
def rv_wp26(ctx: CaseContext) -> None:
    """真逐字稿重放 `waste_census --wake-metrics`：修前逐字稿 31ea79d4 的 M-WB2＝8（重現事故）；修後新逐字稿（4a45bc75，
    子代理完成通知 ≥10 則）M-WB2＝0；M-WB1 印出數值（資訊欄不作判準）。"""
    sb = ctx.sandbox(probe_hooks=False)
    pre, pre_n, pre_wb1 = _wb2(ctx, sb, "31ea79d4-a54d-46ee-a950-5b9dff42d598")
    ctx.check(pre == 8, f"修前逐字稿 31ea79d4 的 M-WB2 應重現 8：{pre}")
    post, post_n, post_wb1 = _wb2(ctx, sb, "4a45bc75-afdb-4e86-82de-be508230e99b")
    ctx.check(post_n >= 10 and post == 0, f"修後逐字稿 4a45bc75 的 M-WB2 應為 0（通知 ≥10 則才有鑑別力）：重複叫醒 {post}、通知 {pre_n if False else post_n}")
    ev(ctx, "wb2_pre_post", f"修前 31ea79d4 M-WB2={pre}（通知 {pre_n} 則）；修後 4a45bc75 M-WB2={post}（通知 {post_n} 則）")
    ev(ctx, "wb1_info", f"{pre_wb1} ｜ {post_wb1}")


@case("RV-WP27", "workprogress", refs=("E2E-WP-27", "REQ-WP-42", "REQ-WP-43"))
def rv_wp27(ctx: CaseContext) -> None:
    """真機 `sessionctl status`：不再出現 ab573c773ef06f035「安靜」；滿壽命殘局只顯示計數；`retired.jsonl` 有該殘局列。"""
    sb = ctx.sandbox(probe_hooks=False)
    env = {k: v for k, v in os.environ.items()}
    env["PYTHONUTF8"] = "1"
    env.pop("AUTOSDD_TRACE_DIR", None)  # 名冊在真持久痕跡目錄
    r = run([PY, str(REPO / "tools" / "sessionctl.py"), "status"], cwd=REPO, env=env, timeout=120)
    out = r.stdout
    ctx.check(r.returncode == 0, f"status rc={r.returncode} {r.stderr[-200:]}")
    ctx.check("ab573c773ef06f035" not in out, "status 仍列出 ab573c773ef06f035")
    ctx.check(not re.search(r"安靜", out), f"status 仍出現「安靜」：{[ln for ln in out.splitlines() if '安靜' in ln][:2]}")
    m = re.search(r"已退役殘局：(\d+) 筆", out)
    ctx.check(m is not None and int(m[1]) >= 1, f"沒有「已退役殘局：N 筆」計數行：{out[-300:]}")
    p = Path.home() / ".autosdd" / "traces" / "roster" / "retired.jsonl"
    rows = []
    for ln in (p.read_text(encoding="utf-8", errors="replace").splitlines() if p.is_file() else []):
        try:
            rows.append(json.loads(ln))
        except ValueError:
            continue
    ids = {r.get("id") for r in rows if r.get("event") == "residue_retired"}
    ctx.check(len(ids) >= 3 and int(m[1]) == len(ids), f"status 計數應＝retired.jsonl 的殘局數（≥3）：status {m[1]}、retired.jsonl {sorted(map(str, ids))}（{p}）")
    ev(ctx, "status_quiet_retired", f"status 無 ab573c773ef06f035／「安靜」；{m[0]}＝retired.jsonl 的 {len(ids)} 筆 id；ab573c773ef06f035 不在退役表（由 E2E-WP-07 不列規則排除，非靠退役）")
    _ = sb


# ───────────────────────── E2E-WP-40：期 C 收尾後的真 repo 現況 ─────────────────────────
@case("RV-WP40", "workprogress", refs=("E2E-WP-40", "REQ-WP-70", "REQ-WP-76"))
def rv_wp40(ctx: CaseContext) -> None:
    """真 repo：`scan` unmapped＝0、`list --undriven` undriven＝0；PRD 修訂表 v2.1.23 列與 DES 附錄 A-1 的列文逐字相同。"""
    sb = ctx.sandbox(probe_hooks=False)
    s = _real(sb, "scan")
    m = re.search(r"unmapped=(\d+)", _last(s.stdout))
    ctx.check(m is not None and int(m[1]) == 0, f"scan unmapped 應為 0：{_last(s.stdout)!r}")
    u = _real(sb, "list", "--undriven")
    n = len([ln for ln in u.stdout.splitlines() if re.match(r"^\s*OI-\d{8}-\d{3}", ln)])
    ctx.check(u.returncode == 0 and n == 0, f"undriven 應為 0：rc={u.returncode} n={n}\n{u.stdout[-300:]}")
    prd = PRD.read_text(encoding="utf-8").splitlines()
    row = [ln for ln in prd if ln.startswith("| **v2.1.23")]
    des = DES.read_text(encoding="utf-8").splitlines()
    a1 = [ln for ln in des if ln.startswith("| A-1 ")]
    ctx.check(len(row) == 1, f"PRD 修訂表沒有（恰一列）v2.1.23 列：{len(row)} 列（期 C 收尾未落地？）")
    ctx.check(len(a1) == 1, f"DES 附錄沒有 A-1 列：{len(a1)}")
    m2 = re.search(r"`(\| \*\*v2\.1\.23.*)`\s*\|\s*$", a1[0])
    ctx.check(m2 is not None and m2[1] == row[0], "PRD v2.1.23 列與 DES 附錄 A-1 的引文不逐字相同")
    ev(ctx, "revision_row_verbatim", "PRD 修訂表 v2.1.23 列＝DES 附錄 A-1 引文（逐字）")
    ev(ctx, "oir_clean", f"scan unmapped=0、undriven={n}")


# ───────────────────────── E2E-WP-44：真逐字稿重放 close 證據 ─────────────────────────
def _find_coords(base: Path) -> tuple[Path, int, int] | None:
    """最小的、同時含 AskUserQuestion tool_result 與真人打字 user 行的真逐字稿：`(檔, ask 行, human 行)`。"""
    files = sorted((p for p in base.glob("*/*.jsonl") if p.stat().st_size < 12_000_000), key=lambda p: p.stat().st_size)
    for p in files[:80]:
        ask_ids: set[str] = set()
        ask_line = human_line = 0
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for i, ln in enumerate(lines, start=1):
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            msg = d.get("message") if isinstance(d, dict) else None
            content = msg.get("content") if isinstance(msg, dict) else None
            if d.get("type") == "assistant" and isinstance(content, list):
                ask_ids |= {c.get("id") for c in content if isinstance(c, dict) and c.get("type") == "tool_use" and c.get("name") == "AskUserQuestion"}
            elif d.get("type") == "user" and isinstance(content, list) and not ask_line:
                if any(isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in ask_ids for c in content):
                    ask_line = i
            elif d.get("type") == "user" and isinstance(content, str) and not human_line:
                o = d.get("origin")
                if not d.get("isMeta") and isinstance(o, dict) and o.get("kind") == "human" and not content.lstrip().startswith("<"):
                    human_line = i
        if ask_line and human_line:
            return p, ask_line, human_line
    return None


@case("RV-WP44", "workprogress", refs=("E2E-WP-44", "REQ-WP-16"))
def rv_wp44(ctx: CaseContext) -> None:
    """從本機真逐字稿現查 AskUserQuestion 的 tool_result 行與真人打字行，複本放沙盒 projects；沙盒 OIR 一列 k1，
    真 CLI `close --by human --evidence "<sid> L<行>"`：AskUserQuestion 座標 ⇒ rc 2＋無 close；真人座標 ⇒ rc 0＋`close` 證據引該座標；`--by` 非 human ⇒ rc 2。"""
    sb = ctx.sandbox(probe_hooks=False)
    seed_docs(sb)
    found = _find_coords(projects_dir())
    if found is None:
        raise EnvMissing("本機 ~/.claude/projects 找不到同時含 AskUserQuestion 結果與真人打字行的逐字稿")
    src, ask_ln, human_ln = found
    sandbox_proj = sb.root / "projects" / "slug"
    sandbox_proj.mkdir(parents=True)
    shutil.copy2(src, sandbox_proj / src.name)
    sid = src.stem
    o = oi(sb, "open", "--title", "rv k1 列", "--source", "docs/01_requirements/src.md", "--scope", "REQ-X", "--kind", "k1", "--why-not-auto", "只認掌舵者真人親打的決定", "--by", "human")
    mid = re.search(r"(OI-\d{8}-\d{3})", o.stdout + o.stderr)
    ctx.check(o.returncode == 0 and mid is not None, f"立案 k1 失敗：rc={o.returncode} {o.stdout[-200:]}{o.stderr[-200:]}")
    item = mid[1]

    def close(coord: str, by: str = "human"):
        return oi(sb, "close", item, "--by", by, "--evidence", coord, "--projects-dir", str(sb.root / "projects"))

    def closes() -> int:
        return len([ln for ln in (sb.root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if '"ev": "close"' in ln or '"ev":"close"' in ln])

    r1 = close(f"{sid} L{ask_ln}")
    ctx.check(r1.returncode == 2 and closes() == 0, f"AskUserQuestion 座標應 rc 2、帳本無 close：rc={r1.returncode} closes={closes()} {r1.stdout[-200:]}{r1.stderr[-200:]}")
    r3 = close(f"{sid} L{human_ln}", by="sid:abc")
    ctx.check(r3.returncode == 2 and closes() == 0, f"--by 非 human 應 rc 2：rc={r3.returncode}")
    r2 = close(f"{sid} L{human_ln}")
    ctx.check(r2.returncode == 0 and closes() == 1, f"真人座標應 rc 0 且 close 1 列：rc={r2.returncode} closes={closes()} {r2.stdout[-200:]}{r2.stderr[-200:]}")
    rows = [json.loads(ln) for ln in (sb.root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if ln.strip()]
    cl = [r for r in rows if r.get("ev") == "close"][0]
    ctx.check(f"{sid} L{human_ln}" in str(cl.get("evidence")), f"close 證據應引該座標：{cl}")
    ev(ctx, "ask_rejected_human_accepted", f"{sid[:8]} L{ask_ln}（AskUserQuestion）rc=2；L{human_ln}（真人）rc=0 證據＝{cl['evidence']}；--by sid:abc rc=2")


# ───────────────────────── E2E-WP-49：spawn 前置與 SI dirty_paths 的自有面判準 ─────────────────────────
_DIRTY_SCRIPT = r"""
import json, subprocess, sys
from pathlib import Path
repo = Path(sys.argv[1]); sandbox = Path(sys.argv[2])
sys.path.insert(0, str(repo / "tools")); sys.path.insert(0, str(repo / "tools" / "lib"))
from lib.sessionctl import handoff
from lib.selfimproving import sched
def porcelain():
    return subprocess.run(["git", "status", "--porcelain"], cwd=sandbox, capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
lines = porcelain()
print("J=" + json.dumps({"lines": lines,
    "foreign_preflight": [ln for ln in lines if not handoff._auto_owned(ln, sandbox)],
    "dirty_paths": sched.dirty_paths(sandbox)}))
"""


@case("RV-WP49", "workprogress", refs=("E2E-WP-49", "REQ-WP-09"))
def rv_wp49(ctx: CaseContext) -> None:
    """沙盒真 git repo（含 OIR 事件帳與 RealVerify 結果帳的初始 commit）：兩本帳各追加一行後，真 `git status --porcelain` 餵
    `handoff._auto_owned`（spawn 前置判準）與真 `selfimproving.sched.dirty_paths`：都判「無非自有髒檔」；再改一個非自有檔：兩者皆指名該檔。"""
    sb = ctx.sandbox(probe_hooks=False)
    seed_docs(sb)
    for rel in ("docs/06_quality/OpenItems_Event_Ledger.jsonl", "docs/06_quality/RealVerify_Result_Ledger.md", "notes.txt"):
        sb.write_file(rel, "init\n")
    for args in (["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", *args], cwd=str(sb.root), check=True, capture_output=True, creationflags=_NOWIN)
    for rel in ("docs/06_quality/OpenItems_Event_Ledger.jsonl", "docs/06_quality/RealVerify_Result_Ledger.md"):
        with (sb.root / rel).open("a", encoding="utf-8", newline="\n") as f:
            f.write("appended\n")

    def probe() -> dict:
        r = run([PY, "-I", "-c", _DIRTY_SCRIPT, str(REPO), str(sb.root)], cwd=sb.root, env=sb.env(), timeout=120)
        m = re.search(r"^J=(.*)$", r.stdout, re.M)
        ctx.check(r.returncode == 0 and m is not None, f"判準子行程失敗 rc={r.returncode} {r.stderr[-400:]}")
        return json.loads(m[1])

    a = probe()
    ctx.check(len(a["lines"]) == 2 and not a["foreign_preflight"] and not a["dirty_paths"], f"只有兩本帳髒時應不擋：{a}")
    (sb.root / "notes.txt").write_text("changed\n", encoding="utf-8", newline="\n")
    b = probe()
    ctx.check(any("notes.txt" in ln for ln in b["foreign_preflight"]) and any("notes.txt" in p for p in b["dirty_paths"]), f"加非自有檔後兩者都應指名 notes.txt：{b}")
    ev(ctx, "own_ledgers_not_dirty", f"兩本帳髒：preflight 非自有={a['foreign_preflight']}、dirty_paths={a['dirty_paths']}")
    ev(ctx, "foreign_file_named", f"加 notes.txt：preflight={b['foreign_preflight']}、dirty_paths={b['dirty_paths']}")
