# WHY：全檔以中文敘述斷言訊息，東亞寬字元計 2 欄、折行會切斷句意；E501 於本檔整體豁免。
"""quota_rush 家族：RV-R1（配速床抬帶／趕工戳記開關到期／熱讀）、RV-R2（burst 上界／無人 rush 拒絕／回放）。

全部經真 CLI（`session_resume_planner.py --pace`、`sessionctl.py rush`）；額度讀數用 `AUTOSDD_QUOTA_CACHE_DIR`
指到沙盒快取、痕跡／戳記用 `AUTOSDD_TRACE_DIR` 指到沙盒、TEMP 也指到沙盒（派發帳／燃燒率落款不污染主控）。
絕不碰主控真實的 `~/autosdd_quota.json` 與 `~/.autosdd/traces/quota_rush.json`。
"""  # noqa: E501

from __future__ import annotations

import time

from ..sandbox import REPO, Sandbox
from . import CaseContext, case
from .sessionctl_park import PY, axis, run, write_quota

PLANNER = str(REPO / "tools" / "session_resume_planner.py")
CTL = str(REPO / "tools" / "sessionctl.py")


def _env(sb: Sandbox, **extra) -> dict:
    e = sb.env()
    tmp = sb.root / "tmp"
    tmp.mkdir(exist_ok=True)
    e.update({"AUTOSDD_QUOTA_CACHE_DIR": str(sb.root / "qcache"), "TEMP": str(tmp), "TMP": str(tmp),
              "PYTHONDONTWRITEBYTECODE": "1"})
    e.pop("AUTOSDD_UNATTENDED", None)
    e.update(extra)
    return e


def _pace(sb: Sandbox, **extra):
    return run([PY, PLANNER, "--pace", "--model", "sonnet"], cwd=sb.root, env=_env(sb, **extra), timeout=120)  # noqa: E501


def _rush(sb: Sandbox, *args: str, **extra):
    return run([PY, CTL, "rush", *args], cwd=sb.root, env=_env(sb, **extra), timeout=60)


def _lifted(out: str) -> bool:
    return "配速床：" in out and "超過允許線" in out


@case("RV-R1", "quota_rush", refs=("V-P1", "V-P2", "V-P3"))
def rv_r1(ctx: CaseContext) -> None:
    """短窗 70pp／剩 240 分（允許線遠低於 70）⇒ `--pace` 印「配速床：…超過允許線」；`rush` 發戳記 ⇒ 改印
    「趕工戳記生效中」；`--off` ⇒ 恢復；極短戳記到期 ⇒ 自動恢復（`rush --status` 前後各一次）。每次呼叫都是
    新行程（熱讀＝下一次呼叫即生效，不必重啟）。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    write_quota(sb, [axis("five_hour", 70, 240)])
    base = _pace(sb)
    ctx.check(base.returncode == 0 and _lifted(base.stdout), f"床沒抬帶：rc={base.returncode}\n{base.stdout[-500:]}{base.stderr[-300:]}")  # noqa: E501
    r = _rush(sb, "--hours", "0.5", "--why", "realverify R1 趕工")
    ctx.check(r.returncode == 0, f"rush rc={r.returncode} {r.stderr}")
    on = _pace(sb)
    ctx.check("趕工戳記生效中" in on.stdout and not _lifted(on.stdout), f"趕工期間床應暫停：\n{on.stdout[-500:]}")  # noqa: E501
    ctx.check("趕工戳記有效" in _rush(sb, "--status").stdout, "rush --status 應顯示有效")
    ev = (sb.root / "traces" / "autosdd_pace_floor.jsonl")
    ctx.check(ev.is_file() and "pace_rush_on" in ev.read_text(encoding="utf-8"), "痕跡檔缺 pace_rush_on")  # noqa: E501
    off = _rush(sb, "--off")
    ctx.check(off.returncode == 0, f"--off rc={off.returncode}")
    ctx.check(_lifted(_pace(sb).stdout), "撤銷後床應恢復")
    # 到期：0.0008 小時≈2.9 秒
    ctx.check(_rush(sb, "--hours", "0.0008", "--why", "realverify R1 到期").returncode == 0, "短戳記發不出")  # noqa: E501
    ctx.check("趕工戳記有效" in _rush(sb, "--status").stdout, "到期前 --status 應有效")
    time.sleep(6)
    st = _rush(sb, "--status").stdout
    ctx.check("已過期" in st, f"到期後 --status 應「已過期」：{st}")
    ctx.check(_lifted(_pace(sb).stdout), "到期後床應自動恢復")
    ctx.evidence("RV-R1 床抬帶→趕工暫停→--off 恢復→到期自動恢復（皆真 CLI、沙盒快取）")


@case("RV-R2", "quota_rush", refs=("V-P4", "V-P5", "V-P6"))
def rv_r2(ctx: CaseContext) -> None:
    """V-P4 burst 設 25 ⇒ `--pace` 出聲「高於上界」並採用 20；V-P5 無人窗口 rush ⇒ rc 2、無戳記、訊息含「無人」；
    V-P6 屬 D5（TCS 明載順延未落地），只釘「未落地」。"""  # noqa: E501
    sb = ctx.sandbox(probe_hooks=False)
    write_quota(sb, [axis("five_hour", 70, 240)])
    ok = _pace(sb)
    ctx.check("高於上界" not in ok.stdout + ok.stderr, "未設 burst 時不該有上界出聲")
    hi = _pace(sb, AUTOSDD_QUOTA_PACE_BURST_PP="25")
    both = hi.stdout + hi.stderr
    ctx.check("高於上界" in both and "20" in both, f"burst=25 應出聲「高於上界 20」：\n{both[-600:]}")  # noqa: E501
    un = _rush(sb, "--hours", "1", "--why", "realverify R2 無人窗口", AUTOSDD_UNATTENDED="1")
    ctx.check(un.returncode == 2 and "無人" in un.stderr, f"無人 rush 應 rc 2 含「無人」：rc={un.returncode} {un.stderr}")  # noqa: E501
    ctx.check(not (sb.root / "traces" / "quota_rush.json").exists(), "無人 rush 不該寫出戳記檔")
    # V-P6：TCS-TokenWaste §10 明載 D5（`--pace-metrics`／`--replay-pace-floor`）本期未做、順延後續期；  # noqa: E501
    # 旗標在 waste_census 不存在（argparse rc 2）。規格不得宣稱磁碟上沒有的元件 ⇒ 這裡只釘「它確實未落地」，  # noqa: E501
    # 一旦落地此斷言轉紅、提醒補上真跑 rc 0 的驗證（不是假裝它已驗）。
    census = REPO / "tools" / "probe" / "waste_census.py"
    r = run([PY, str(census), "--since-days", "14", "--pace-metrics"], cwd=sb.root, env=_env(sb), timeout=120)  # noqa: E501
    ctx.check(r.returncode == 2 and "unrecognized arguments" in r.stderr,
              "waste_census --pace-metrics 已落地？請把 V-P6 改成真跑 rc 0 的驗證")
    ctx.evidence("RV-R2 burst 25→20 出聲；無人 rush rc 2；V-P6＝D5 順延未落地（旗標不存在，已釘）")
