"""sessionctl_switchcensus 家族：換 session 成本量測的真實逐字稿實跑（R216 WP-G；TCS-SessionSwitch-
CostModel E2E-SS-01／02、REQ-SS-20）。

載具：真行程 `python tools/probe/waste_census.py --switch-metrics／--replay-switch／--calibrate-switch`，
讀本機**真實**專案逐字稿（唯讀、零 token、不開沙盒、不碰任何 session）。
母體會隨時間漂移（新逐字稿進來、舊的滾出視窗），所以斷言只判**不變式**——同一份母體快照重放兩次
逐字相同、重放的 FRESH 決定與正式 `costmodel.fresh_is_cheaper` 逐筆一致、各指標互相對得上——而不是
把設計文件當日的絕對數字寫死（那是歷史快照，漂移後必假紅）。當日數字對帳寫進證據檔，不寫進斷言。
"""  # noqa: E501
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from ..driver import EnvMissing
from ..sandbox import REPO
from . import CaseContext, case

_PROBE = REPO / "tools" / "probe" / "waste_census.py"
_NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_DAYS = "14"


def _census(*args: str) -> tuple[int, str, str]:
    r = subprocess.run([sys.executable, str(_PROBE), *args], capture_output=True, text=True,  # noqa: S603
                       encoding="utf-8", errors="replace", timeout=240, creationflags=_NOWIN, cwd=str(REPO))  # noqa: E501
    return r.returncode, r.stdout, r.stderr


def _real_population(ctx: CaseContext, tmp: Path) -> tuple[Path, str]:
    """真行程讀真逐字稿 → 母體快照；回 (快照路徑, 該次 stdout)。沒有真逐字稿＝環境缺件，不偽造。"""
    snap = tmp / "population.json"
    rc, out, err = _census("--since-days", _DAYS, "--replay-switch", "--dump-population", str(snap))
    if rc == 1 and "逐字稿目錄不存在" in err:
        raise EnvMissing("本機沒有此專案的真實逐字稿目錄（~/.claude/projects/<slug>）")
    ctx.check(rc == 0 and snap.is_file(), f"waste_census rc={rc} {err[-300:]}")
    pop = json.loads(snap.read_text(encoding="utf-8"))
    if not pop["main"]:
        raise EnvMissing("近 14 天沒有主控逐字稿，無法重放")
    return snap, out


@case("RV-SC1", "sessionctl_switchcensus", refs=("E2E-SS-01", "REQ-SS-20"))
def rv_sc1(ctx: CaseContext) -> None:
    """`--replay-switch --switch-metrics` 對真逐字稿：rc 0 且印出設計 §7 全部列（P1／P3／P4b／S1／S2）；
    同一份快照重放兩次逐字相同（決定性）；重放的 P3 FRESH 決定與正式 `costmodel.fresh_is_cheaper` 對
    同一批真實事件逐筆一致；M-K3 件數＝S2 事件數、M-K4 件數＝S1 事件數（兩個入口量的是同一批事件）；
    快照不含對話內容（只有 usage／時間戳／起因／工具名）。"""  # noqa: E501
    with tempfile.TemporaryDirectory(prefix="rv-sc1-") as tmp:
        snap, out = _real_population(ctx, Path(tmp))
        for needle in ("P1 主控保溫", "P3 額度續跑選路（q=1）", "P4b 邊界軟線掃描", "S1 冷續棒", "S2 子代理分段等待"):  # noqa: E501
            ctx.check(needle in out, f"重放輸出缺「{needle}」：{out[-400:]}")
        flags = ["--population", str(snap), "--switch-metrics", "--replay-switch"]
        rc1, one, e1 = _census(*flags)
        rc2, two, _ = _census(*flags)
        ctx.check(rc1 == 0 and rc2 == 0 and one == two, f"同一快照重放兩次不同（非決定性）rc={rc1}/{rc2} {e1[-200:]}")  # noqa: E501
        # —— 與正式 F4 逐筆一致（真實事件，不是合成）——
        # costmodel 要 lazy import tools/lib 的 quota_policy_env，所以路徑保留到行程結束（runner 一案一行程）  # noqa: E501
        sys.path[:0] = [str(REPO / "tools"), str(REPO / "tools" / "lib")]
        from lib.sessionctl import costmodel
        from lib.wastecensus import sections_keep as sk
        pop = json.loads(snap.read_text(encoding="utf-8"))
        rep = sk.replay_all(pop, 45.0)
        f_cost = rep["f_cost"]
        events = [g for g in sk.idle_gaps(pop["main"]) if g["cause"] == "quota_resume" and g["rew"]]
        for row in rep["p3"]:
            env = {costmodel.FRESH_COST_KEY: str(f_cost), costmodel.VALUE_Q_KEY: str(row["q"])}
            want = sum(1 for g in events if costmodel.fresh_is_cheaper(g["ctx"], cold=True, env=env))  # noqa: E501
            ctx.check(row["fresh"] == want, f"q={row['q']} 重放判 FRESH {row['fresh']} 件，正式 F4 判 {want} 件")  # noqa: E501
        met = sk.switch_metrics(pop, [])
        ctx.check(met["m_k3"]["count"] == rep["subs"]["s2_events"], "M-K3 件數與 S2 事件數不同")
        ctx.check(met["m_k4"]["count"] == rep["subs"]["s1_events"], "M-K4 件數與 S1 事件數不同")
        ctx.check(rep["p1"]["rewrites"] == met["m_k1"]["count"], "P1 的可保溫重寫件數與 M-K1 不同")
        text = snap.read_text(encoding="utf-8")
        ctx.check(not any(f'"{k}"' in text for k in ("message", "content", "first_prompt", "text")), "快照含對話欄位（應只有 usage／時間戳）")  # noqa: E501
        ctx.evidence(f"RV-SC1 真母體 主控 {len(pop['main'])}／子代理 {len(pop['sub'])}；P1 保溫省 {rep['p1']['saved']:,.0f}（{rep['p1']['pings']} 次）；"  # noqa: E501
                     f"P3 q=1 FRESH {rep['p3'][-1]['fresh']}/{rep['p3'][-1]['events']}；S2 {rep['subs']['s2_events']} 件 "  # noqa: E501
                     f"{rep['subs']['s2_base']:,.0f}→{rep['subs']['s2_cost']:,.0f}；M-K2＝{met['m_k2']['count']}")  # noqa: E501


@case("RV-SC2", "sessionctl_switchcensus", refs=("E2E-SS-02", "REQ-SS-20"))
def rv_sc2(ctx: CaseContext) -> None:
    """`--calibrate-switch` 對真逐字稿＋真 `autosdd_resume_cost.jsonl`：rc 0；F 的 p25≤中位≤p75 且樣本
    數≥5；B 中位落在 10 萬～30 萬 tokens（接手後穩定上下文的合理量級）；resume_cost 區段讀到真列
    （n≥1，且冷窗的寫入占比有算）；校準值只印、不改任何 env 或檔案（唯讀）。出廠 F 是否落在實測
    p25～p75 內寫進證據（漂移訊號，不當失敗）。"""  # noqa: E501
    with tempfile.TemporaryDirectory(prefix="rv-sc2-") as tmp:
        out_json = Path(tmp) / "cal.jsonl"
        rc, out, err = _census("--since-days", _DAYS, "--calibrate-switch", "--out", str(out_json))
        if rc == 1 and "逐字稿目錄不存在" in err:
            raise EnvMissing("本機沒有此專案的真實逐字稿目錄")
        ctx.check(rc == 0, f"--calibrate-switch rc={rc} {err[-300:]}")
        cal = json.loads(out_json.read_text(encoding="utf-8").splitlines()[0])["calibrate"]
        f, b, rcost = cal["f"], cal["b"], cal["resume_cost"]
        ctx.check(f["n"] >= 5, f"F 樣本數過少（{f['n']}）：母體不足，量不出建議值")
        ctx.check(f["p25"] <= f["median"] <= f["p75"], f"F 分位數順序錯：{f}")
        ctx.check(100_000 <= b["median"] <= 300_000, f"B 中位 {b['median']} 不在合理量級")
        real = Path.home() / ".autosdd" / "traces" / "autosdd_resume_cost.jsonl"
        if real.is_file() and real.stat().st_size:
            ctx.check(rcost["n"] >= 1, f"本機有真 resume_cost 檔卻讀到 {rcost['n']} 列")
        for needle in ("F 接手成本", "B 接手後穩定上下文", "P_fix", "SESSION_RESUME 首回合實付"):
            ctx.check(needle in out, f"校準輸出缺「{needle}」")
        in_band = f["p25"] <= 480_000 <= f["p75"]
        ctx.evidence(f"RV-SC2 F n={f['n']} p25={f['p25']:,.0f} 中位={f['median']:,.0f} p75={f['p75']:,.0f}；"  # noqa: E501
                     f"出廠 480,000 {'在' if in_band else '不在'}實測 p25～p75 內；B 中位={b['median']:,.0f}；"  # noqa: E501
                     f"resume_cost n={rcost['n']}（冷窗 {rcost['cold_n']} 筆、寫入占比≥80% {rcost['write_share_ge_80pct_cold']} 筆）")  # noqa: E501
