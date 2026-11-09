"""SelfImproving 無人運轉任務書（TCS-SelfImproving-P4 R152；ADR-SI-14）。

能力類別 `ro`：只讀 SOP 的〈無人運轉任務書範本〉程式碼圍欄，取骨架並把全部大寫占位符換成現查值；
小寫或中文占位符（`<來源 id>`、`<PROP>`、`<held-out 目錄>`、`<凍結者>`）原樣保留（那是給無人
主控的現場指令）。`template_problems` 回問題碼清單（空＝可用）；缺必含項即拒絕 spawn。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# `resume_route` 以頂層名 import 同層的 endurance_env，故先把 tools/lib 放進 sys.path
_LIB = str(Path(__file__).resolve().parents[1])
if _LIB not in sys.path:
    sys.path.insert(0, _LIB)

from lib import resume_route  # noqa: E402

SECTION = "## 無人運轉任務書範本"
UPPER_FIELDS = ("RUN", "HEAD_SHA", "NOW_ISO", "DUE_AT", "BAND", "DEGRADE_NOTE", "BUDGET_MINUTES",
                "EVENTS", "RESEARCH_RESULT", "SOURCE_FILES", "SCAN_CANDIDATES", "MAX_PROPOSALS",
                "HANDBACK_PATH")
_UPPER_RE = re.compile(r"<([A-Z][A-Z_]*)>")
_FENCE_RE = re.compile(r"^```[a-z]*[ \t]*$", re.MULTILINE)
_STEP_RE = re.compile(r"^(\d+)\. ", re.MULTILINE)
_F_LINE = "trigger=f（到期 <DUE_AT>）"
_A_LINE = "trigger=a（Console 立即啟動）"
DEGRADE_TEXT = ("降載聲明：額度帶 {band}——只做最小必要工作（研究者與歸因者各一輪、至多一張提案），"
                "預算寬裕也不擴張；有餘裕才交卷。")


def _section(sop_text: str) -> str | None:
    """範本節（該節標題起至檔尾；範本節位於 SOP 檔尾，圍欄內含 `## ` 標題，故不以下一個
    `##` 截斷）。"""
    start = sop_text.find(SECTION)
    return None if start < 0 else sop_text[start:]


def template_of(sop_text: str) -> str | None:
    """範本節第一個程式碼圍欄的內文；節或圍欄不存在＝None。"""
    sec = _section(sop_text)
    if sec is None:
        return None
    marks = list(_FENCE_RE.finditer(sec))
    if len(marks) < 2:
        return None
    return sec[marks[0].end():marks[1].start()].strip("\n") + "\n"


def template_problems(sop_text: str) -> list[str]:
    """問題碼清單（空＝可用）：`FENCE-MISSING`、`PLACEHOLDER-MISSING:<X>`、
    `HANDBACK-HEADING-MISSING:<標題>`、`FORBIDDEN-SECTION-MISSING`、`ROLE-STEP-MISSING:<N>`、
    `TRIGGER-LINE-MISSING`。"""
    body = template_of(sop_text)
    if body is None:
        return ["FENCE-MISSING"]
    out = [f"PLACEHOLDER-MISSING:{name}" for name in UPPER_FIELDS if f"<{name}>" not in body]
    lines = {ln.strip() for ln in body.splitlines()}
    out += [f"HANDBACK-HEADING-MISSING:{m}" for m in resume_route.HANDBACK_MARKERS
            if m not in lines]
    if "## 禁止事項" not in lines:
        out.append("FORBIDDEN-SECTION-MISSING")
    have = {int(n) for n in _STEP_RE.findall(body)}
    out += [f"ROLE-STEP-MISSING:{n}" for n in range(1, 9) if n not in have]
    if _F_LINE not in body:
        out.append("TRIGGER-LINE-MISSING")
    return out


def render(template: str, fields: dict, *, trigger: str = "f") -> str:
    """把大寫占位符換成 `fields` 的值（缺鍵者原樣保留，由 `template_problems`／呼叫端擋）；
    `trigger="a"` 時把到期句改成 Console 立即啟動。"""
    text = template.replace(_F_LINE, _A_LINE) if trigger == "a" else template
    return _UPPER_RE.sub(lambda m: str(fields[m.group(1)]) if m.group(1) in fields else m.group(0),
                         text)
