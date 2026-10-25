"""SelfImproving 確定性卡面：渲染、顯示寬度、反解析一致性（TCS-SelfImproving-P1 R56）。

`prop-new` 預判與 `card`／`export` 共用同一個 `render`（不得有第二份卡面實作）。卡面由事件欄位、
`rN.patch` 與 `rN.md` 欄位表確定性轉換——提案者自由撰寫的摘要不取代 diff 本文。輸出前把卡面
反解析回數值並與現算值逐欄比對，不一致的卡不得送達（`CardError`）。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from . import fold as si_fold
from . import paths as si_paths
from . import props as si_props
from .events import PROPOSALS_REL
from .git import Git

CLASS_NAMES = {"M": "記憶條目", "P": "Playbook 片段", "R": "SDD 規則草案", "D": "非治理文件",
               "evaluator-change": "評估器變更", "loop-self": "迴圈自身"}
CORE_MAX = 12
R_RETIRE_HINT = "SDD 規則退役須經 set_maturity(reviewed_by=<人>)；本迴圈不呼叫 SDD 碼"
_PARSED_KEYS = ("digest8", "added", "removed", "touched_count", "extra_paths", "verdict")
Code = tuple[str, str]


class CardError(Exception):
    """卡面無法送達（rc 3）：`code` 為 PROP-NOT-FOUND、PROP-FILE-MISSING、CARD-INCONSISTENT 等。"""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code} {detail}".strip())
        self.code, self.detail = code, detail


@dataclass
class CardResult:
    prop: str
    rev: int
    digest: str
    text: str
    core_lines: int
    parsed: dict
    fields: dict = field(default_factory=dict)
    core: list = field(default_factory=list)


def width(text: str) -> int:
    """顯示寬度：`east_asian_width` 為 W／F 者算 2、其餘算 1（同根層 E501 量法）。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def render(v: dict) -> tuple[str, int, list[str]]:
    """渲染七行卡面；回（全文含結尾 LF, 核心區行數, 核心區行串列）。
    v 的鍵：pid、cls、action、target、digest8、verdict、route、symptom、risk、rollback、added、
    removed、ratio、touched_count、extra、sources、budget、patch_rel、cooldown。"""
    handoff = v["route"].startswith("handoff:")
    head = (f"[{v['pid']}] {CLASS_NAMES[v['cls']]}｜{v['action']}｜目標：{'、'.join(v['target'])}"
            f"｜digest：{v['digest8']}｜驗證：{v['verdict']}"
            + ("｜僅轉交，本迴圈不套用" if handoff else ""))
    extra = [f"  - {p}" for p in v["extra"]]
    core = [
        head, f"一、症狀：{v['symptom']}",
        f"二、改什麼：+{v['added']}／-{v['removed']} 行；觸及比例 {v['ratio']}；"
        f"觸及檔案數 {v['touched_count']}；不在 target 內的路徑：{len(extra)}",
        *extra,
        f"三、風險與回滾：{v['risk']}｜回滾：{v['rollback']}｜驗證：{v['verdict']}",
        "決定：轉交 ／ 不轉交＋一句理由" if handoff
        else "決定：核准 ／ 否決＋一句理由 ／ 退回＋一句修改要求",
    ]
    tail = [
        "--- 以下不計入核心區 ---",
        f"證據座標：{'、'.join(v['sources'])}｜預算宣告：{v['budget']}｜完整 diff 座標："
        f"{v['patch_rel']}｜冷卻狀態：{'冷卻中' if v['cooldown'] else '無'}"
        f"｜轉交通道：{v['route'].split(':', 1)[1] if handoff else '無'}",
    ]
    if v["cls"] == "R" and v["action"] == "retire":  # R127 (f)：SDD 規則退役須經人工 set_maturity
        tail.append(R_RETIRE_HINT)
    return "\n".join(core + tail) + "\n", len(core), core


def layout_problems(core: list[str], card_line_max: int) -> list[Code]:
    """核心區行數須 ≤ 12；一～三與決定四行及各路徑行的顯示寬度須 ≤ `card_line_max`。"""
    out: list[Code] = []
    if len(core) > CORE_MAX:
        out.append(("CARD-TOO-TALL", f"核心區 {len(core)} 行 > {CORE_MAX}（額外路徑過多）"))
    wide = [width(ln) for ln in core[1:]]
    if any(w > card_line_max for w in wide):
        out.append(("CARD-LINE-TOO-WIDE", f"核心區單行顯示寬度最大 {max(wide)} > {card_line_max}"))
    return out


def parse(text: str) -> dict:
    """卡面反解析：（digest 前 8 碼、added、removed、觸及檔案數、額外路徑、驗證狀態）。"""
    lines = text.split("\n")
    m1 = re.search(r"digest：([0-9a-f]{8})｜驗證：([^｜]+)", lines[0])
    m3 = re.search(r"\+(\d+)／-(\d+) 行.*觸及檔案數 (\d+)", lines[2]) if len(lines) > 2 else None
    return {"digest8": m1.group(1) if m1 else None, "added": int(m3.group(1)) if m3 else None,
            "removed": int(m3.group(2)) if m3 else None,
            "touched_count": int(m3.group(3)) if m3 else None,
            "extra_paths": [ln[4:] for ln in lines if ln.startswith("  - ")],
            "verdict": m1.group(2) if m1 else None}


def _line_count(text: str | None) -> int | None:
    if text is None:
        return None
    return len(text.split("\n")) - (1 if text.endswith("\n") else 0)


def build(repo: Path, git: Git, events: list[dict], f: si_fold.Folded, pid: str,
          params: dict) -> CardResult:
    """某 PROP 最新 rev 的卡面；查無、內容檔缺、反解析不一致皆拋 CardError。"""
    p = f.props.get(pid)
    ev = next((e for e in reversed(events) if e.get("kind") == "prop" and e.get("id") == pid
               and e.get("rev") == (p.rev if p else None)), None)
    if p is None or ev is None:
        raise CardError("PROP-NOT-FOUND", pid)
    base = repo / PROPOSALS_REL / pid
    patch_path, body_path = base / f"r{p.rev}.patch", base / f"r{p.rev}.md"
    missing = [x.name for x in (patch_path, body_path) if not x.is_file()]
    if missing:
        raise CardError("PROP-FILE-MISSING", "、".join(missing))
    patch = patch_path.read_bytes()
    body = body_path.read_bytes().decode("utf-8", "replace")
    try:
        blocks = si_paths.parse_patch(patch)
    except si_paths.PatchError as exc:
        raise CardError("CARD-INCONSISTENT", f"patch 無法解析（{exc.code}）") from exc
    _, fields = si_props.parse_body(body)
    touched = sorted({x for b in blocks for x in b.paths})
    return assemble(repo, git, f, ev, p, blocks, touched, fields, patch, body, params)


def assemble(repo: Path, git: Git, f: si_fold.Folded, ev: dict, p: si_fold.Prop,
             blocks: list, touched: list[str], fields: dict, patch: bytes, body: str,
             params: dict, *, check: bool = True) -> CardResult:
    cls = ev["cls"]
    if cls == "M":
        ratio = "n/a"
    else:
        if not git.available:
            raise CardError("GIT-UNAVAILABLE", "非 M 類卡面的觸及比例需 git 取 base 快照")
        lines = {t: _line_count(git.show(ev["base"], t)) for t in touched}
        ratio = f"{float(si_paths.touch_ratio(blocks, lines)):.2f}"
    patch_rel = f"{PROPOSALS_REL}/{p.id}/r{p.rev}.patch"
    extra = sorted(set(touched) - set(ev["target"]))
    v = {"pid": p.id, "cls": cls, "action": ev["action"], "target": ev["target"],
         "digest8": ev["digest"].split(":", 1)[-1][:8], "verdict": p.verdict or "未驗",
         "route": ev["route"], "symptom": fields.get("symptom", ""),
         "risk": fields.get("risk", ""), "rollback": fields.get("rollback", ""),
         "added": sum(len(b.added) for b in blocks), "removed": sum(len(b.removed) for b in blocks),
         "ratio": ratio, "touched_count": ev["touched_count"], "extra": extra,
         "sources": ev["sources"], "budget": fields.get("budget", ""), "patch_rel": patch_rel,
         "cooldown": any(c["prop"] == p.id for c in f.cooldowns)}
    text, n, core = render(v)
    parsed = parse(text)
    if check:
        digest = si_props.compute_digest(
            pid=p.id, rev=p.rev, cls=cls, action=ev["action"], target=ev["target"],
            touched=touched, base=ev["base"], preimage=si_props.preimage_of(blocks, touched),
            patch_sha=si_props.sha256_of(patch), body_sha=si_props.body_sha256(body), fields=fields)
        want = {"digest8": digest.split(":", 1)[-1][:8], "added": v["added"],
                "removed": v["removed"], "touched_count": len(touched), "extra_paths": extra,
                "verdict": p.verdict or "未驗"}
        bad = [k for k in _PARSED_KEYS if parsed[k] != want[k]]
        if bad:
            raise CardError("CARD-INCONSISTENT", "不符欄位：" + "、".join(bad))
    return CardResult(p.id, p.rev, ev["digest"], text, n, parsed, fields, core)
