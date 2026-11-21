"""OIR 結案證據判準（DES §3.2 `close`、§5、REQ-WP-16；TCS AT-WP-18、E2E-WP-44）。

兩種證據、兩個判準，都不看措辭、只看可重驗的座標：
  · `human_proof`：掌舵者真人發言座標 `<sid> L<行>`——逐字稿該行必須是真人打的 user 記錄
    （`origin.kind=human`、非 `isMeta`、非 tool_result、非 harness 注入）。AskUserQuestion 的回答是
    tool_result，永遠不算（K=1 決定只認真人親打，根 CLAUDE.md〈收尾常態規則〉）。
  · `run_check`：auto／observe 的 `check` 規格（RealVerify 帳出現晚於 `open` 的 pass 列，
    或 argv 判準）。
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from pathlib import Path

from lib import platform_utils, transcript_activity

from .ledger import parse_ts

_COORD = re.compile(r"^(?P<sid>[0-9A-Za-z._-]+)\s+L(?P<line>\d+)$")
RV_LEDGER_REL = "docs/06_quality/RealVerify_Result_Ledger.md"
ARGV_TIMEOUT_SECONDS = 600


def _find_transcript(sid: str, projects_dir: Path | None) -> Path | None:
    base = (Path(projects_dir) if projects_dir is not None
            else platform_utils.claude_home() / "projects")
    try:
        return next(iter(sorted(base.glob(f"*/{sid}.jsonl"))), None)
    except OSError:
        return None


def _typed_text(record: dict) -> str | None:
    """真人打字的文字；含 tool_result 或不是文字回 `None`。"""
    message = record.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    return "\n".join(str(b.get("text") or "") for b in content
                     if isinstance(b, dict) and b.get("type") == "text")


def human_proof(evidence: str, projects_dir: Path | None = None) -> tuple[bool, str]:
    """證據字串是不是「掌舵者真人發言座標」；回 `(成立, 理由)`。"""
    m = _COORD.match((evidence or "").strip())
    if not m:
        return False, "證據格式必須是 `<sid> L<行號>`（掌舵者真人發言的逐字稿座標）"
    sid, line_no = m["sid"], int(m["line"])
    path = _find_transcript(sid, projects_dir)
    if path is None:
        return False, f"找不到 session {sid} 的逐字稿"
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            line = next((ln for i, ln in enumerate(handle, start=1) if i == line_no), None)
        record = json.loads(line) if line else None
    except (OSError, ValueError):
        record = None
    if not isinstance(record, dict) or record.get("type") != "user":
        return False, f"{sid} L{line_no} 不是 user 記錄"
    origin = record.get("origin")
    if record.get("isMeta") or not (isinstance(origin, dict) and origin.get("kind") == "human"):
        return False, f"{sid} L{line_no} 不是真人發言（isMeta 或 origin.kind≠human）"
    text = _typed_text(record)
    if text is None:
        return False, f"{sid} L{line_no} 是 tool_result（AskUserQuestion 回答不算掌舵者發言）"
    if transcript_activity.is_machine_prompt(text):
        return False, f"{sid} L{line_no} 是 harness 注入、不是真人打字"
    return True, f"{sid} L{line_no}"


def realverify_pass(root: Path, case: str, since: datetime) -> tuple[datetime, str] | None:
    """RealVerify 帳裡 `case` 最近一次晚於 `since` 的 pass 列；沒有回 `None`。

    新格式（≥8 欄）只認第 8 欄「執行案例」列出的 id；舊 7 欄只在「選取」恰為該單一案例 id 時有效
    （`family=…`／`all` 舊列不算——REQ-WP-82 的判讀由 E1 接手時覆寫本函式，介面不變）。"""
    try:
        text = (Path(root) / RV_LEDGER_REL).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    best: tuple[datetime, str] | None = None
    for raw in text.splitlines():
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[2] != "pass":
            continue
        stamp = parse_ts(cells[0])
        if stamp is None or stamp <= since:
            continue
        ran = ({x for x in re.split(r"[,，、\s]+", cells[7]) if x} if len(cells) >= 8
               else {cells[1]})
        failed = {x for x in re.split(r"[,，、\s]+", cells[4]) if x}
        if case in ran and case not in failed and (best is None or stamp > best[0]):
            best = (stamp, f"{RV_LEDGER_REL} {cells[0]} {case}")
    return best


def run_check(item: dict, root: Path, now: datetime) -> tuple[bool, str]:
    """auto／observe 項目的 `check` 是否成立；回 `(成立, 證據或失敗理由)`。"""
    check = item.get("check")
    if not isinstance(check, dict):
        return False, "此項目沒有 check（人工項目請用 --by human 與掌舵者發言座標結案）"
    due = parse_ts(item.get("due")) if item.get("kind") == "observe" else None
    if due is not None and now < due:
        return False, f"尚未到期（due={item['due']}）"
    if "realverify" in check:
        hit = realverify_pass(root, check["realverify"], parse_ts(item["opened"]))
        if hit is None or (due is not None and hit[0] < due):
            return False, f"RealVerify 帳沒有晚於 open 的 {check['realverify']} pass 列"
        return True, hit[1]
    try:
        proc = subprocess.run(
            check["argv"], cwd=str(root), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=ARGV_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"argv 無法執行：{exc.__class__.__name__}"
    rule = check["pass"]
    ok = proc.returncode == 0 if rule == "rc0" else bool(re.search(rule[6:], proc.stdout))
    return ok, f"argv rc={proc.returncode} pass={rule}"
