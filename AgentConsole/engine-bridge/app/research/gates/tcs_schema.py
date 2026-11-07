"""TCS 草稿的確定性驗證（SCG 預檢；D-109；TCS AT-961-9-3）。

`tcs-draft` stage 的 agent 只寫 `03_execution/tcs_draft.md`（D-74：工具權限只到工作區）；是否合格由
這裡的純函式判定——LLM 不決定迴圈與停止（Rule 5）。規則（任一不過＝stage `FAILED`、
`exit_reason=tcs_invalid`，內環鍵留在 SPEC_DRAFTING）：

  · `no_at`          草稿一個 AT 標頭都沒有；
  · `at_orphan`      AT 所屬 AC（AT ID 前兩段數字）不在凍結 PRD 的 AC 集合；
  · `ac_uncovered`   凍結 PRD 的某個 AC 沒有任何 AT（AC 全涵蓋、AT↔AC 一一對映）；
  · `judge_command_empty` 某 AT 區塊沒有非空的「判定」指令欄；
  · `secret`         內文含機密樣式（`gitops.redact` 會遮蔽的任何東西）；
  · `file_name`      發佈檔名不合 `routers/sdd.py` 的 `_TCS_NAME`（不內嵌第二份規則）。

同一支模組也是 evaluator 的命令列入口（`python -I -m app.research.gates.tcs_schema --workspace
<工作區>`；rc 0＝合格、1＝違規〔每行一條到 stderr，引擎帶進下一次重試〕、2＝用法錯誤）：輸入只有
工作區內的檔案（Bridge 預先寫好的 `tcs_inputs.json` 與 agent 的草稿），沒有資料庫與網路。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Collection, Sequence
from pathlib import Path

from .schemas import Violation, violation_lines

TCS_INPUTS_REL = "03_execution/tcs_inputs.json"
TCS_DRAFT_REL = "03_execution/tcs_draft.md"
RC_OK, RC_INVALID, RC_USAGE = 0, 1, 2
_AT_HEAD_RE = re.compile(r"^\s*#{1,6}\s*(AT-\d{3}-\d+(?:-[A-Za-z0-9]+)*)\b")
_JUDGE_RE = re.compile(r"^\s*(?:[#>*-]\s*)*判定(?:指令)?\s*\**\s*[:：]\s*(.*)$")
_AC_OF_AT_RE = re.compile(r"^AT-(\d{3}-\d+)")


def ac_of(at_id: str) -> str | None:
    """AT ID 前兩段數字＝所屬 AC（`AT-001-12-3-a` 屬 `AC-001-12`）。"""
    match = _AC_OF_AT_RE.match(at_id)
    return f"AC-{match.group(1)}" if match else None


def target_name(slug: str, date: str) -> str:
    """發佈檔名 `TCS-<slug>-<yyyymmdd>.md`。"""
    return f"TCS-{slug}-{date}.md"


def parse_blocks(text: str) -> dict[str, list[str]]:
    """AT ID → 該 AT 區塊的各行（標頭之後到下一個 AT 標頭之前；同 ID 重複時合併）。"""
    blocks: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in text.splitlines():
        match = _AT_HEAD_RE.match(line)
        if match:
            current = blocks.setdefault(match.group(1), [])
            continue
        if current is not None:
            current.append(line)
    return blocks


def _has_secret(text: str) -> bool:
    # 延遲匯入：gitops 較重；只有驗證時才需要
    from ..gitops import redact

    return redact(text) != text


def validate(text: str, frozen_acs: Collection[str], *, file_name: str | None = None
             ) -> list[Violation]:
    """回違規清單（空＝合格）。`frozen_acs`＝凍結 PRD 的 AC 編號集合。"""
    found: list[Violation] = []
    blocks = parse_blocks(text)
    if not blocks:
        found.append(Violation("no_at", TCS_DRAFT_REL, "草稿沒有任何 AT 標頭（# AT-NNN-Y-Z）"))
    wanted = set(frozen_acs)
    covered: set[str] = set()
    for at_id, body in blocks.items():
        owner = ac_of(at_id)
        if owner not in wanted:
            found.append(Violation("at_orphan", at_id, f"{at_id} 所屬的 {owner} 不在凍結 PRD 內"))
        else:
            covered.add(str(owner))
        commands = [m.group(1).strip() for line in body if (m := _JUDGE_RE.match(line))]
        if not any(commands):
            found.append(Violation("judge_command_empty", at_id, f"{at_id} 缺非空的「判定」指令欄"))
    found += [Violation("ac_uncovered", ac, f"{ac} 沒有任何對應的 AT")
              for ac in sorted(wanted - covered)]
    if _has_secret(text):
        found.append(Violation("secret", TCS_DRAFT_REL, "草稿含疑似機密的字樣（內容不予回顯）"))
    if file_name is not None:
        # 與 `:freeze` 同一個判準，不內嵌第二份
        from ...routers.sdd import _TCS_NAME

        if not _TCS_NAME.match(file_name):
            found.append(Violation("file_name", file_name,
                                   "檔名須以 TCS- 或 TEST-CONTRACT-SPEC- 起頭"))
    return found


def summarize(violations: Sequence[Violation]) -> dict[str, list[str]]:
    """事件用的摘要：規則 → 受影響的 AC／AT 編號（不含任何內文，所以不洩機密）。"""
    out: dict[str, list[str]] = {}
    for v in violations:
        out.setdefault(v.rule, []).append("" if v.rule == "secret" else v.path)
    return out


RULE_LABELS = {
    "no_at": "草稿沒有任何 AT", "at_orphan": "孤兒 AT（所屬 AC 不在凍結 PRD）",
    "ac_uncovered": "缺 AT 的 AC", "judge_command_empty": "判定指令欄為空的 AT",
    "secret": "含疑似機密字樣", "file_name": "檔名不合"}


def human_summary(violations: Sequence[Violation]) -> str:
    """游標 `flow_detail` 與 stage 失敗說明用的人讀缺項摘要（只含規則與 AC／AT 編號，不含內文）。"""
    parts = []
    for rule, ids in summarize(violations).items():
        shown = "、".join(i for i in ids if i)
        parts.append(f"{RULE_LABELS.get(rule, rule)}：{shown}" if shown else RULE_LABELS.get(
            rule, rule))
    return "；".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.research.gates.tcs_schema", description=__doc__)
    parser.add_argument("--workspace", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return RC_USAGE if exc.code else RC_OK
    ws = Path(args.workspace)
    try:
        inputs = json.loads((ws / TCS_INPUTS_REL).read_text(encoding="utf-8"))
        acs = [str(item["id"]) for item in inputs["acs"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        sys.stderr.write(f"[R1] {TCS_INPUTS_REL}: 讀不到或格式不合（{type(exc).__name__}）\n")
        return RC_INVALID
    try:
        text = (ws / TCS_DRAFT_REL).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        sys.stderr.write(f"[R1] {TCS_DRAFT_REL}: 檔案讀不到或不是 UTF-8（{type(exc).__name__}）\n")
        return RC_INVALID
    problems = validate(text, acs)
    for line in violation_lines(problems):
        sys.stderr.write(line + "\n")
    return RC_INVALID if problems else RC_OK


if __name__ == "__main__":
    raise SystemExit(main())
