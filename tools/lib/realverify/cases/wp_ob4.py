# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-OB4（observe；E2E-SS-05／E2E-WP-60）：換 session 成本模型上線 14 天觀察，`M-K2`（主控閒置自動壓縮）＝0。

observe 案例由 OIR observe 驅動器在 `due` 之後才跑；未到期直接回「環境缺件」（rc 2，不算綠、不縮參數代跑）。
判準：到期後對本機真逐字稿跑 `waste_census --switch-metrics --since-days 14`，`M-K2` 的壓縮次數 ＝ 0 即 PASS
（基線 9，目標 0；`--since-days 14` 在 due 當日只含上線後的 14 天）。
"""

from __future__ import annotations

import re
from datetime import datetime

from ..driver import EnvMissing
from ..sandbox import REPO
from . import CaseContext, case
from .prd_px_lib import ev
from .sessionctl_park import PY, run

KIND = "observe"
DUE = "2026-12-02"


@case("RV-OB4", "workprogress", refs=("E2E-WP-60", "REQ-WP-90", "E2E-SS-05"), long=True)
def rv_ob4(ctx: CaseContext) -> None:
    if datetime.now().astimezone().date().isoformat() < DUE:
        raise EnvMissing(f"observe 未到期（due={DUE}）：不縮短參數代跑，由 OIR observe 驅動器到期觸發")
    sb = ctx.sandbox(probe_hooks=False)
    r = run([PY, str(REPO / "tools" / "probe" / "waste_census.py"), "--since-days", "14", "--switch-metrics"], cwd=sb.root, env=sb.env(), timeout=300)
    ctx.check(r.returncode == 0, f"waste_census rc={r.returncode} {r.stderr[-300:]}")
    m = re.search(r"M-K2[^\n]*?：(\d+) 次／", r.stdout)
    ctx.check(bool(m), f"輸出缺 M-K2 行：\n{r.stdout[-600:]}")
    n = int(m.group(1))
    ctx.check(n == 0, f"M-K2 應＝0（主控閒置自動壓縮），實為 {n}：{m.group(0)}")
    ev(ctx, "m_k2_zero", f"M-K2＝{n}（近 14 天，due={DUE}）")
