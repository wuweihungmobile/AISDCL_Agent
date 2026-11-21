# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""workprogress 家族（OIR 真 CLI，沙盒根）：RV-WP50（立案驗證三拒絕）、RV-WP43（並行立案連號＋壞行容錯）。
全部經真 `python tools/openitems.py --root <沙盒> --trace-dir <沙盒>/traces`，不碰真帳本。"""

from __future__ import annotations

import json
import re
import shutil
import threading
from pathlib import Path

from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

CLI = str(REPO / "tools" / "openitems.py")
LEDGER_REL = "docs/06_quality/OpenItems_Event_Ledger.jsonl"


def oi(sb, *args: str, timeout: int = 120):
    return run([PY, CLI, "--root", str(sb.root), "--trace-dir", str(sb.root / "traces"), *args], cwd=sb.root, env=sb.env(), timeout=timeout)  # noqa: E501


def seed_docs(sb) -> None:
    sb.write_file("docs/01_requirements/src.md", "# 沙盒來源\n")
    sb.write_file("README.md", "# readme\n")
    (sb.root / "docs" / "06_quality" / "OpenItems_Protocol").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO / "docs" / "06_quality" / "OpenItems_Protocol" / "params.json", sb.root / "docs" / "06_quality" / "OpenItems_Protocol" / "params.json")


def n_lines(sb) -> int:
    p = sb.root / LEDGER_REL
    return len([ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]) if p.is_file() else 0


GOOD = ["open", "--title", "rv 沙盒列", "--source", "docs/01_requirements/src.md", "--scope", "REQ-X", "--kind", "auto", "--check", '{"realverify":"RV-L1"}', "--by", "human"]  # noqa: E501


@case("RV-WP50", "workprogress", refs=("E2E-WP-50", "REQ-WP-02", "REQ-WP-06"))
def rv_wp50(ctx: CaseContext) -> None:
    """沙盒 OIR 真 CLI：`open` human 缺 `why_not_auto`、observe 缺 `due`、`source` 指向 README.md ⇒ 三者 rc 2、帳本行數不變；
    對照組合法 auto 列 rc 0 且行數 +1（證明拒絕是驗證造成、不是 CLI 壞了）。"""
    sb = ctx.sandbox(probe_hooks=False)
    seed_docs(sb)
    ok = oi(sb, *GOOD)
    ctx.check(ok.returncode == 0 and n_lines(sb) == 1, f"對照組合法立案應 rc 0、行數 1：rc={ok.returncode} lines={n_lines(sb)} {ok.stderr[-300:]}{ok.stdout[-200:]}")  # noqa: E501
    base = n_lines(sb)
    bad = {
        "human_missing_why_not_auto": ["open", "--title", "t", "--source", "docs/01_requirements/src.md", "--scope", "S", "--kind", "human", "--by", "human"],  # noqa: E501
        "observe_missing_due": ["open", "--title", "t", "--source", "docs/01_requirements/src.md", "--scope", "S", "--kind", "observe", "--check", '{"argv":["python","-V"],"pass":"rc0"}', "--by", "human"],  # noqa: E501
        "source_readme": ["open", "--title", "t", "--source", "README.md", "--scope", "S", "--kind", "auto", "--check", '{"realverify":"RV-L1"}', "--by", "human"],  # noqa: E501
    }
    rcs = {}
    for name, argv in bad.items():
        r = oi(sb, *argv)
        rcs[name] = r.returncode
        ctx.check(r.returncode == 2, f"{name} 應 rc 2：rc={r.returncode} {r.stdout[-200:]}{r.stderr[-200:]}")
    ctx.check(n_lines(sb) == base, f"被拒絕的立案不得寫帳本：{base}→{n_lines(sb)}")
    ev(ctx, "three_rejections", f"rc={rcs}；帳本行數 {base}→{n_lines(sb)}（不變）；對照組合法列 rc 0")


@case("RV-WP43", "workprogress", refs=("E2E-WP-43", "REQ-WP-07", "REQ-WP-01"))
def rv_wp43(ctx: CaseContext) -> None:
    """同時起 2 個真 `openitems open` 行程序列，各連開 20 列 ⇒ 40 個 id 互不相同且當日連號、帳本 40 行皆可 fold；
    之後追加一行壞 JSON，真 `list` 末行 `bad=1`。"""
    sb = ctx.sandbox(probe_hooks=False)
    seed_docs(sb)
    outs: list[list] = [[], []]

    def worker(k: int) -> None:
        for i in range(20):
            r = oi(sb, *GOOD[:2], f"rv {k}-{i}", *GOOD[3:])
            outs[k].append(r)

    ths = [threading.Thread(target=worker, args=(k,)) for k in (0, 1)]
    [t.start() for t in ths]
    [t.join() for t in ths]
    rcs = [r.returncode for o in outs for r in o]
    ctx.check(all(rc == 0 for rc in rcs), f"有立案失敗：{[(o.returncode, o.stderr[-120:]) for g in outs for o in g if o.returncode][:2]}")
    ids = [m.group(1) for o in outs for r in o for m in [re.search(r"(OI-\d{8}-\d{3})", r.stdout + r.stderr)] if m]
    ctx.check(len(ids) == 40 and len(set(ids)) == 40, f"40 個 id 應互不相同：{len(ids)}／{len(set(ids))}")
    nums = sorted(int(i.rsplit("-", 1)[1]) for i in ids)
    ctx.check(nums == list(range(nums[0], nums[0] + 40)), f"id 應當日連號：{nums[:3]}…{nums[-3:]}")
    rows = [json.loads(ln) for ln in (sb.root / LEDGER_REL).read_text(encoding="utf-8").splitlines() if ln.strip()]
    ctx.check(len(rows) == 40, f"帳本應 40 行：{len(rows)}")
    ev(ctx, "ids_unique_consecutive", f"40 個 id 互異、連號 {nums[0]}…{nums[-1]}（兩行程各 20 列並行）")
    with Path(sb.root / LEDGER_REL).open("a", encoding="utf-8", newline="\n") as f:
        f.write("{this is not json\n")
    r = oi(sb, "list")
    last = [ln for ln in r.stdout.splitlines() if ln.strip()][-1] if r.stdout.strip() else ""
    ctx.check("bad=1" in last, f"list 末行應含 bad=1：rc={r.returncode} {last!r}")
    ev(ctx, "bad_line_tolerated", f"追加壞 JSON 後 list 末行：{last}")
