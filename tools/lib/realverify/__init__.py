"""realverify：真機自驗載具（真 `claude -p`＋repo 外沙盒專案＋真 schtasks＋讀真逐字稿判定）。

WHY 存在：帳本裡一批「fixed 但待真機」的尾巴永遠掛著，成因是沒有任何載具同時具備上列四件事，
所以 AutoClaude 自己驗不完（設計稿
docs/06_quality/CrossPlatform_R215_PendingVerification_Closure.md §4）。

給「寫案例的人」的最短路徑（完整範例見 `cases/hooks.py`）：

    from lib.realverify.cases import case, CaseContext

    @case("RV-X1", "myfamily", refs=("V-X1",))
    def rv_x1(ctx: CaseContext) -> None:
        sb = ctx.sandbox()                 # 建沙盒（repo 外、git init、含探針 hook），自動清
        r = ctx.run_claude(sb, "say hi")   # 真 `claude -p --model haiku`；r.rc／r.stdout
        tr = ctx.transcript(sb)            # 讀沙盒 sid 的真逐字稿
        ctx.check(tr.has_blocking_error("Stop", "RV_STOP"), "Stop 推回記錄在逐字稿")
        ctx.evidence(tr.coords(tr.hook_blocking_errors("Stop")[0]))   # 逐字稿座標進帳本

把檔放進 `tools/lib/realverify/cases/<family>.py` 即自動發現，不需改任何登記檔
（`docs/06_quality/RealVerify_Protocol/cases.json` 只做「案例 id → V／AT／DEF」反查）。
"""

from __future__ import annotations
