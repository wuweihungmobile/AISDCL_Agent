"""換手與掌控量測（`sections_ctl`）的 I/O 層：逐字稿、交接包、park 標記、額度讀數 → 純函式輸入。

零 token、只讀檔；壞行略過。判準在 `sections_ctl`；本檔只做「把檔案讀成母體」與印表。
母體快照（`--dump-population`／`--population`）以 `pop["ctl"]` 帶 `{packs, parks, burn}`，讓 CI
與本機跑同一組判準（快照只留時刻／sid／讀數，不含對話內容）。
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import transcript_activity as ta

from lib.sessionctl import control

from . import sections_ctl as sc
from . import supervision_load as sl

#: 「回頭讀舊資料」：新 session 去讀前棒的 prompts sidecar、舊逐字稿、交接包目錄。
OLD_DATA = re.compile(r"\.prompts\.md|[\\/]projects[\\/][^\s\"']*\.jsonl|[\\/]handoff[\\/]", re.I)
_PACK_NAME = re.compile(r"^(?P<sid>[\w-]+)_\d{8}T\d{4,6}Z?\.md$")
_SINCE_PAD_S = 3600


def _epoch(raw) -> float | None:
    try:
        return datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _reads(rec: dict) -> list[str]:
    out = []
    for block in sl._blocks(rec):  # noqa: SLF001 — 同套件內共用的區塊切片
        if block.get("type") != "tool_use":
            continue
        data = block.get("input") if isinstance(block.get("input"), dict) else {}
        out.append(str(data.get("file_path") or data.get("path") or data.get("command")
                       or data.get("pattern") or "")[:300])
    return out


def light(raw: dict) -> dict | None:
    """`supervision_load.light` 加上 assistant 的 `reads`（工具輸入摘要，M-C2 用）。"""
    got = sl.light(raw)
    if got is not None and got["type"] == "assistant":
        got["reads"] = _reads(raw)
    return got


def load_sessions(base: Path, since_days: float) -> list[dict]:
    return sl.load_sessions(base, since_days, light_fn=light)


def load_packs(handoff_dir: Path) -> list[dict]:
    """交接包 → `{sid, sealed_at, acker, acked_at}`（epoch 秒；缺檔／壞值 ⇒ None）。"""
    rows = []
    try:
        names = sorted(handoff_dir.glob("*.md"))
    except OSError:
        return rows
    for path in names:
        found = _PACK_NAME.match(path.name)
        if found is None:
            continue
        row = {"sid": found.group("sid"), "sealed_at": None, "acker": None, "acked_at": None}
        try:
            row["sealed_at"] = _epoch(path.with_suffix(".sealed").read_text(encoding="utf-8"))
        except OSError:
            pass
        try:
            parts = path.with_suffix(".ack").read_text(encoding="utf-8").split()
            row["acked_at"] = _epoch(parts[1])
            row["acker"] = next((p.split("=", 1)[1] for p in parts if p.startswith("sid=")), None)
        except (OSError, IndexError):
            pass
        rows.append(row)
    return rows


def _jsonl(path: Path) -> list[dict]:
    out = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def load_ctl(handoff_dir: Path, trace_dir: Path) -> dict:
    """重放用的 `{packs, parks, burn}`：park 標記取 `trace_dir/park/*.json`，
    讀數取 `quota_burn.jsonl`。"""
    parks = []
    for path in sorted((trace_dir / "park").glob("*.json")):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(row, dict):
            parks.append(row)
    return {"packs": load_packs(handoff_dir), "parks": parks,
            "burn": _jsonl(trace_dir / "quota_burn.jsonl")}


def heartbeat_spans(trace_dir: Path) -> dict[str, list[tuple[float, float, str]]]:
    """目前還在的 watch 心跳檔（`watch/<sid>.<pid>.json`）→ 憑證區間。歷史心跳在 watch 結束時已刪，
    所以這只涵蓋執行中的 watch；歷史憑證靠逐字稿的「看管中」出聲（`credential_intervals`）。"""
    out: dict[str, list[tuple[float, float, str]]] = {}
    for path in (trace_dir / "watch").glob("*.json"):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        t0, t1 = _epoch(row.get("started_at")), _epoch(row.get("heartbeat_at"))
        sid = path.name.split(".")[0]
        if t0 is not None and t1 is not None:
            out.setdefault(sid, []).append((t0, t1, "heartbeat"))
    return out


def _worked_between(path: Path, since: float, until: float) -> bool:
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return False
    with handle:
        for line in handle:
            if '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            at = _epoch(rec.get("timestamp")) if isinstance(rec, dict) else None
            if at is None or not since < at <= until or rec.get("isSidechain"):
                continue
            if any(b.get("type") == "tool_use" and b.get("name") not in ta.READ_ONLY_TOOLS
                   and not control.is_supervision_call(b) for b in sl._blocks(rec)):  # noqa: SLF001
                return True
    return False


def _finalize_times(path: Path) -> list[float]:
    """逐字稿裡 `handoff --finalize` 呼叫的時刻（封存戳會被後續 finalize 覆寫，歷史戳只剩逐字稿
    記得；呼叫時刻與戳相差秒級，量測用足夠）。"""
    out: list[float] = []
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return out
    with handle:
        for line in handle:
            if "--finalize" not in line or '"tool_use"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            at = _epoch(rec.get("timestamp")) if isinstance(rec, dict) else None
            if at is not None and not rec.get("isSidechain") and any(
                    b.get("type") == "tool_use" and "--finalize" in json.dumps(b.get("input"))
                    for b in sl._blocks(rec)):  # noqa: SLF001
                out.append(at)
    return out


def make_judge(base: Path, packs: list[dict]):
    """M-C1 的 `judge(trace_row)`：推回當下（`_at`）本 sid 最新（≤ 該刻）封存戳之後主控有非監督
    工作 ⇒ `invalidated`，否則 `effective`；沒有可用戳 ⇒ `unknown`（不計）。判準＝`control` 的
    `is_supervision_call`＋唯讀工具集，與 `sealed_effective` 同。"""
    def judge(row: dict) -> str:
        sid, at = row.get("sid"), row.get("_at")
        path = Path(base) / f"{sid}.jsonl"
        stamps = [p["sealed_at"] for p in packs if p["sid"] == sid and p.get("sealed_at")
                  is not None and at is not None and p["sealed_at"] <= at]
        stamps += [t for t in _finalize_times(path) if at is not None and t <= at]
        if not stamps:
            return "unknown"
        worked = _worked_between(path, max(stamps), at)
        return control.SEAL_INVALIDATED if worked else control.SEAL_EFFECTIVE
    return judge


# ───────────────────────────────────────────────────────── 印表
def _q(x) -> str:
    return "—" if x is None else str(x)


def print_ctl(got: dict) -> None:
    w1, c1, c2, c6 = got["m_w1"], got["m_c1"], got["m_c2"], got["m_c6"]
    fixed, bound = w1["corrected"], w1["upper_bound"]
    print(f"   M-W1（修正，讀真實憑證）無看管區間：{fixed['n']} 筆合計 "
          f"{fixed['total_hours']} 小時；"
          f">30 分 {fixed['gt_30min']} 筆、>60 分 {fixed['gt_60min']} 筆、最大 "
          f"{fixed['gap_min'].get('max')} 分（憑證區間 {w1['credential_spans'] or '無'}）")
    print(f"   M-W1（{bound['label']}）：{bound['n']} 筆／{bound['total_hours']} 小時、>30 分 "
          f"{bound['gt_30min']} 筆——只當上界、不與修正版相減（口徑不同）")
    print(f"   M-C1 A4 回歸：封存後派工被冷叫醒推回 {c1['after_seal_work']}／推回 {c1['blocks']}"
          f"（分母 exempt {c1['exempt']}；W1 後回歸 {_q(c1['regression'])}；目標 0）"
          f"{'（' + c1['note'] + '）' if c1['note'] else ''}")
    print(f"   M-C2 接續完整度：手貼 {c2['pasted']}／{c2['n_interactive']}"
          f"（{_q(c2['paste_pct'])}%；"
          f"目標 ≤5%）；機器交接開場 {c2['machine_start']} 個 session，第一小時回頭讀舊資料中位 "
          f"{_q(c2['reread_median'])}、非零 {c2['reread_nonzero']}")
    print(f"   M-C6 無人窗口子代理被終止：{c6['killed']} 件／{c6['sessions']} 個 session（目標 0）")


def print_switch_ctl(got: dict) -> None:
    c3, c4, c5 = got["m_c3"], got["m_c4"], got["m_c5"]
    print(f"   M-C3 park 提前恢復：{c3['recovered']} 件，省 {c3['saved_min']} 分；探針 "
          f"{c3['probes']} 次，unmeasured {c3['unmeasured']}（{_q(c3['unmeasured_ratio'])}）")
    print(f"   M-C4 換手判定：{c4['plans']} 筆 {c4['by_action'] or '尚無資料'}；"
          f"提示 {c4['advise']} 次、"
          f"{sc.FOLLOW_MIN} 分內跟進 {c4['advise_followed']}（{_q(c4['follow_pct'])}%）；"
          f"M-K6 觸發源 {c4['triggers'] or '尚無資料'}")
    print(f"   M-C5 F′（冷回、F4 判換新、無封存載具）：{c5['f_prime']}／冷回 {c5['cold_returns']}"
          f"（F4 判換新 {c5['f4_fresh']}；基線 8／14 天）")


def print_replay_plan(res: dict, meta: dict) -> None:
    print(f"== 換手決策重放（DES §7.6 同形表；母體：主控 {meta['main']}／子代理 {meta['sub']}／"
          f"包 {meta['packs']}／park 標記 {meta['parks']}／額度讀數 {meta['burn']}）==")
    print("| 判定點 | 命中 | 備註 |")
    print("|---|---|---|")
    for row in res["rows"]:
        print(f"| {row['name']} | {row['hits']} | {row['note']} |")
    print("誠實限制：在飛代理以代理檔首末時間戳近似；母體只存工具名，Bash／PowerShell 一律算工作；"
          "park 提前量為下界；帳號變動取自讀數指紋（同組織換使用者可能漏看）。")
