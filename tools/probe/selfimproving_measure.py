"""SelfImproving 量測腳本（C11）：M1～M5、資訊欄、反證條件與判準指紋（TCS-P3 R124～R126）。

用法：`python tools/probe/selfimproving_measure.py [--repo DIR] [--json]`。零 token、唯讀、
離線、不寫任何檔；窗與指標只經 `lib.selfimproving` 的唯讀模組取得（與 `measure` 共用單一窗
規則實作）；同一 HEAD 與工作樹重跑輸出逐位元相同。rc：0＝已輸出（NOT-EVALUABLE 不是錯誤，
rc 不隨指標值或反證結果改變）、3＝無法執行（未知旗標、`--repo` 不是目錄、`params.json` 的
量測鍵缺或無效）。不接任何閘門（AC-SI-22-2）。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.selfimproving import events as si_events  # noqa: E402
from lib.selfimproving import mea, meastat  # noqa: E402
from lib.selfimproving import params as si_params  # noqa: E402
from lib.selfimproving.git import Git  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
KEYS = ("w_opp", "w_min", "w_evt", "w_n", "metrics_rev")
PARAMS_REL = f"{si_params.PROTOCOL_REL}/params.json"


class UsageError(Exception):
    """無法執行（rc 3）。"""


def _load_params(repo: Path) -> dict:
    try:
        obj = json.loads((repo / PARAMS_REL).read_bytes().decode("utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise UsageError(f"params.json 讀不到或不是 JSON（{type(exc).__name__}）") from exc
    if not isinstance(obj, dict):
        raise UsageError("params.json 頂層不是物件")
    bad = [k for k in KEYS if k not in si_params.valid_keys(obj)]
    if bad:
        raise UsageError("params.json 必要鍵缺失或無效：" + "、".join(bad))
    return obj


def build_report(repo: Path) -> dict:
    """探針輸出物件（鍵序固定）；`params.json` 的量測鍵無效拋 `UsageError`。"""
    params, git = _load_params(repo), Git(repo)
    events = si_events.load_sound_events(repo / si_events.LEDGER_REL)
    ctx = mea.build_ctx(repo, git, params, events or [])
    rep = meastat.metrics(repo, git, ctx, events is not None)
    fp, parts = meastat.fingerprint(repo, params)
    return {"schema_rev": 1, "fingerprint": fp, "fingerprint_parts": parts, "head_sha": git.head(),
            "params": {k: params[k] for k in ("w_opp", "w_min", "w_evt", "w_n")},
            "success": rep["success"], "info": rep["info"], "falsification": rep["falsification"],
            "ne": rep["ne"]}


def _val(x: dict) -> str:
    if x["status"] != "read":
        return f"NOT-EVALUABLE（{x['reason']}）"
    return f"{x['value']:.4f}" if isinstance(x["value"], float) else str(x["value"])


def render_text(rep: dict) -> str:
    s, i, f = rep["success"], rep["info"], rep["falsification"]
    m1 = s["m1"]
    out = ["== 成功指標 ==", f"M1: {_val(m1)} n={m1['n']}"
           + (f" recurred={m1['recurred']}" if m1["status"] == "read" else "")]
    for r in m1["per_prop"]:
        why = r["reason"] or "evaluable"
        out.append(f"  prop {r['prop']} result={r['result']} events={r['events']} "
                   f"opp_n={r['opp_n']} {why}")
    out.append(f"M4: {_val(s['m4'])}")
    out += [f"M5 main: {_val(s['m5']['main'])} n={s['m5']['main']['n']}",
            f"M5 all: {_val(s['m5']['all'])} n={s['m5']['all']['n']}", "== 資訊欄 =="]
    out += [f"提案數: {i['proposals']}",
            "決定分佈: " + (" ".join(f"{k}={v}" for k, v in i["decisions"].items()) or "無"),
            f"OBS 列數: {i['obs_rows']}", f"closed-by-decision: {i['closed_by_decision']}",
            f"未驗採納: {i['unverified_ack']}", f"窗後回滾: {i['late_rollbacks']}",
            f"unplaced_rows: {i['unplaced_rows']}",
            f"unattributable_candidates: {i['unattributable_candidates']}",
            f"M2: {_val(i['m2'])} n={i['m2']['n']} excluded={i['m2']['excluded']}",
            f"M3: {_val(i['m3'])} n={i['m3']['n']} excluded={i['m3']['excluded']}",
            f"全域窗 M1: {_val(i['global_m1'])} n={i['global_m1']['n']}",
            f"反證條件: falsified={f['falsified']} keys={','.join(f['falsified_keys']) or '無'}"
            f" missing={','.join(f['missing']) or '無'}", f"fingerprint={rep['fingerprint']}"]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    args, repo, as_json = list(sys.argv[1:] if argv is None else argv), REPO, False
    try:
        while args:
            flag = args.pop(0)
            if flag == "--json":
                as_json = True
            elif flag == "--repo" and args:
                repo = Path(args.pop(0))
            else:
                raise UsageError(f"未知旗標或缺值：{flag}")
        if not repo.is_dir():
            raise UsageError(f"--repo 不是目錄：{repo}")
        rep = build_report(repo)
    except UsageError as exc:
        sys.stderr.write(f"selfimproving_measure: {exc}\n")
        return 3
    text = json.dumps(rep, ensure_ascii=False) + "\n" if as_json else render_text(rep)
    sys.stdout.buffer.write(text.encode("utf-8"))
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
