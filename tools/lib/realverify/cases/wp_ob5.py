# ruff: noqa: E501
# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""RV-OB5（observe；V-PK5／E2E-WP-60）：park 上線 14 天對照，`waste_census --resume-metrics --since-days 14`。

observe 案例由 OIR observe 驅動器在 `due` 之後才跑；未到期回「環境缺件」（rc 2，不算綠、不縮參數代跑）。
達標判準（對照上線前基線，TCS-SessionPark V-PK5：M-R1 P90 294.4 分、無憑證停點 6）：
  ① M-R4「無憑證停點」＝0（每個額度停工都掛了續航憑證）；② M-R1 的 p90 ≤ 基線 P90 294.4 分（醒得更快或不變）。
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
DUE = "2026-11-30"
BASELINE_P90_MIN = 294.4


@case("RV-OB5", "workprogress", refs=("E2E-WP-60", "REQ-WP-90", "V-PK5"), long=True)
def rv_ob5(ctx: CaseContext) -> None:
    if datetime.now().astimezone().date().isoformat() < DUE:
        raise EnvMissing(f"observe 未到期（due={DUE}）：不縮短參數代跑，由 OIR observe 驅動器到期觸發")
    sb = ctx.sandbox(probe_hooks=False)
    r = run([PY, str(REPO / "tools" / "probe" / "waste_census.py"), "--since-days", "14", "--resume-metrics"], cwd=sb.root, env=sb.env(), timeout=300)
    ctx.check(r.returncode == 0, f"waste_census rc={r.returncode} {r.stderr[-300:]}")
    m4 = re.search(r"M-R4[^\n]*?無憑證停點 (\d+) 個", r.stdout)
    m1 = re.search(r"M-R1[^\n]*?p90=([0-9.]+)", r.stdout)
    ctx.check(bool(m4) and bool(m1), f"輸出缺 M-R4／M-R1：\n{r.stdout[-600:]}")
    n4, p90 = int(m4.group(1)), float(m1.group(1))
    ctx.check(n4 == 0, f"無憑證停點應＝0，實為 {n4}")
    ctx.check(p90 <= BASELINE_P90_MIN, f"M-R1 p90 {p90:.1f} 分 > 基線 {BASELINE_P90_MIN}")
    ev(ctx, "no_uncertified_stops", f"M-R4 無憑證停點＝{n4}")
    ev(ctx, "r1_p90_not_worse", f"M-R1 p90＝{p90:.1f} 分 ≤ 基線 {BASELINE_P90_MIN}（due={DUE}）")
