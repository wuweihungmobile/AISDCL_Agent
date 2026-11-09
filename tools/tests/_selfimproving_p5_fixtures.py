# 受測面：tools/lib/selfimproving/fourqparse.py（程式碼鎖，非散文）
"""SelfImproving P5 測試共用夾具（TCS-SelfImproving-P5 §3；底線開頭、不被收集）。

建在 P2 夾具之上（呼叫形態不變）；各 P5 測試檔的 `setUpModule` 呼叫 `fx.setup("si_p5_")`。
合成編號一律於執行期以字串相加組出（`rid`／`pid`／`obs_id`）；本檔不寫不存在於真帳本的字面編號。
"""

from __future__ import annotations

import json
import os
import shutil
import types
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2

from lib.selfimproving import fourq

SOP_REL = "docs/05_development/SelfImproving_Operations_SOP.md"
MINI_SOP = "# 迷你 SOP\n\n夾具第三行：金絲雀只在本檔的別處出現過一次。\n"
SRC_TABLE = {"schema_rev": 1, "sources": [
    {"id": "src-a", "url": "https://example.com/a", "kind": "docs", "extract": "讀",
     "added_by": "T1"},
    {"id": "src-old", "url": "https://example.com/o", "kind": "docs", "extract": "讀",
     "added_by": "T1", "retired": True}]}
RUN = fx.rid(1)
Q1_LINE = ("- Q1-1｜領域：SRE｜做法：金絲雀回滾演練｜機制：漸進放量比對錯誤率｜"
           "座標：" + SOP_REL + ":1｜查詢：「金絲雀回滾演練」＝零命中｜"
           "查詢：「漸進放量比對」＝零命中")
Q1X_LINE = ("- Q1-X{n}｜考慮：迷你說明已涵蓋｜查詢：「迷你 SOP」＝命中｜座標：" + SOP_REL + ":1")
Q2F_LINE = "- Q2-F1｜來源：src-a｜座標：src=src-a 片段一｜發現：新版釋出說明"
Q2G_LINE = ("- Q2-G1｜URL：https://example.org/feed｜分級：T1｜為何前沿：官方釋出｜"
            "更新頻率：每週")
Q3_LINE = "- Q3-1｜對象：Q1-1｜方法：金絲雀分析｜工具：playbooks/demo.yaml"
Q4_LINE = ("- Q4-1｜擬提案：回滾演練｜指標類別：M1｜症狀定義：`git grep -c x`｜"
           "反證：演練後症狀仍再現｜收斂：依 PRD 的 M1 判定細則")
DEFAULT = {"q1": [Q1_LINE], "q2": [Q2F_LINE, Q2G_LINE], "q3": [Q3_LINE], "q4": [Q4_LINE]}


def answers(run: str = RUN, **mods) -> str:
    """合法答案檔建構器：`q1`～`q4` 傳行串列即整問抽換；`head`／`titles` 可覆寫首行與四標題。"""
    from lib.selfimproving import fourqparse as fp

    body = {**DEFAULT, **{k: v for k, v in mods.items() if k in DEFAULT}}
    titles = mods.get("titles", list(fp.TITLES))
    out = [mods.get("head", f"# 四問審視 {run}")]
    for i, t in enumerate(titles, 1):
        out += [t, *body[f"q{i}"]]
    return "\n".join(out) + "\n"


def p5_base(prm=None) -> Path:
    """P2 基線 repo 加迷你 SOP 與來源表；`fourq_from_run`＝1（夾具內全部運轉皆適用）。"""
    dest = fx.new_dir("p5")
    repo = fx2.make_p2_repo(dest, prm={"fourq_from_run": 1, **(prm or {})},
                            sources=json.dumps(SRC_TABLE, ensure_ascii=False, indent=2) + "\n")
    fx.put(repo, SOP_REL, MINI_SOP)
    fx.commit_all(repo, "C4")
    return repo


def free_band(band: str = "free"):
    return mock.patch.object(fourq, "QUOTA_READ", lambda now: types.SimpleNamespace(band=band))


def clone(R: Path) -> Path:
    dest = fx.new_dir("cp")
    shutil.copytree(R, dest)
    return dest


class P5TestCase(fx2.P2TestCase):  # 名稱含 TestCase：discover 守門不解析跨檔基底鏈（OBS-SI-162）
    """受測：`tools/lib/selfimproving/fourq.py`（測試基底，額度帶預設 free）。"""

    def setUp(self) -> None:
        super().setUp()
        p = free_band()
        p.start()
        self.addCleanup(p.stop)

    def run_id(self, R: Path) -> str:
        return fx2.open_run(R)

    def fq(self, R: Path, text: str, *extra: str, run: str | None = None, by: str = "REV"):
        """把 `text` 存成答案檔後跑 `fourq`；回 (rc, out, err)。"""
        run = run or self.run_id(R)
        path = fx.new_dir("ans")
        path.mkdir()
        f = path / "a.md"
        f.write_bytes(text.encode("utf-8") if isinstance(text, str) else text)
        return self.M(R, "fourq", "--run", run, "--answers-file", str(f), "--by", by, *extra)

    def good(self, R: Path, **mods) -> str:
        return answers(self.run_id(R), **mods)

    def snap(self, R: Path):
        home = Path(os.environ["AUTOSDD_SI_DIR"])
        tree = {p.relative_to(home).as_posix(): p.read_bytes() for p in sorted(home.rglob("*"))
                if p.is_file() and "locks" not in p.parts}
        return fx.snap(R), tree


# ---- SOP 判準（TCS-P5 AT-441-1／AT-445-3；圍欄感知：答案檔範本圍欄內含 `# `／`## `）----
RESEARCHER_SHA = "e961796c0a61ab4281db40c6d52a0f7274ff880048bb6883c65deefd526b1593"
METHODOLOGY_SHA = "deb9716bb56cdd6f9cf47a28fa62aa1a869d71b0ab6a4aa8146dab5f8f69b2b2"
METHODOLOGY_REL = "docs/05_development/SelfImproving_Research_Methodology_SOP.md"
REQ = ("Read／Grep／Glob", "無 Web", "不得 Write／Edit", "零遞迴", "不同代理實例", "--pace",
       "任務書不含任何迴圈層量測值")


def section(text: str, title: str, level: str = "## ") -> str | None:
    """標題行起到下一個同級標題（圍欄外）之前；`\n`.join(行) 加結尾 LF。"""
    lines, fence, start = text.replace("\r\n", "\n").split("\n"), False, None
    for i, ln in enumerate(lines):
        if ln.startswith("```"):
            fence = not fence
        if fence or not ln.startswith(level):
            continue
        if start is not None:
            return "\n".join(lines[start:i]) + "\n"
        if ln == level + title:
            start = i
    return None if start is None else "\n".join(lines[start:]) + "\n"


def _fences(sec: str) -> list[str]:
    parts = sec.split("```")
    return [p for i, p in enumerate(parts) if i % 2 == 1]


def sop_p5_problems(text: str, methodology: bytes | None = None) -> list[str]:
    from lib.selfimproving import fourqparse as fp

    sec = section(text, "四問審視者")
    out: list[str] = []
    if sec is None:
        out.append("SOP-P5-SECTION-MISSING")
    else:
        out += [f"SOP-P5-REQ-MISSING:{r}" for r in REQ if r not in sec]
        out += [f"SOP-P5-QUESTION-MISSING:{i}" for i, q in enumerate(fp.QS, 1) if q not in sec]
    heads = [ln[3:] for ln in text.split("\n") if ln.startswith("## ")]
    want = ["研究者", "四問審視者", "運轉配方"]
    if [h for h in heads if h in want] != want:
        out.append("SOP-P5-SECTION-ORDER")
    rc = section(text, "rc 契約表（先存 rc 再判停）", "### ") or ""
    row = next((ln for ln in rc.split("\n") if ln.startswith("| `fourq` |")), "")
    cells = [c.strip() for c in row.strip("|").split("|")]
    if len(cells) < 6 or not all(cells[i] for i in (1, 2, 4)):
        out.append("SOP-P5-RC-ROW-MISSING")
    seq = section(text, "最小序列（有提案的運轉）", "### ") or ""
    import re

    for name, fence in zip(("ps", "bash"), _fences(seq)[:2], strict=False):
        pos = [(m.start() if (m := re.search(rf"\b{w}\b", fence)) else -1)
               for w in ("scan", "fourq", "attr")]
        if not (0 <= pos[0] < pos[1] < pos[2]):
            out.append(f"SOP-P5-SEQ-ORDER:{name}")
    pf = section(text, "提案檔（`prop-new --patch-file <r.patch> --body-file <r.md>`）", "### ")
    if pf is None or "method" not in pf or "proof" not in pf:
        out.append("SOP-P5-PROP-FIELDS-MISSING")
    import hashlib

    res = section(text, "研究者") or ""
    if hashlib.sha256(res.encode("utf-8")).hexdigest() != RESEARCHER_SHA:
        out.append("SOP-P5-RESEARCHER-CHANGED")
    if methodology is not None and hashlib.sha256(
            methodology.replace(b"\r\n", b"\n")).hexdigest() != METHODOLOGY_SHA:
        out.append("SOP-P5-METHODOLOGY-CHANGED")
    return out
