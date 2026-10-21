"""SelfImproving P2 元層驗收測試（TCS-P2 MT 檔）：AT 錨定規則的可重跑檢查（R102）、Operations SOP
〈P2 動詞〉與〈審查者〉的必備條文（R108、SOP-P2-REQ）、P1 零退化與夾具升級（R107、R109）。

判準函式（`parse_at_headers`、`anchor_problems`、`sop_p2_problems`）住本檔，取參數（TCS 文字、
收集結果、
SOP 文字），故真檔與合成輸入用同一份碼自證。方法名含 AT 底線形（錨定 `-k AT_240_9_1_` 只收一個）。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
from _selfimproving_p2_fixtures import P2TestCase

from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import params as si_params

ROOT = fx.ROOT
TCS_DIR = ROOT / "docs" / "03_testing" / "contracts"
SOP = ROOT / "docs" / "05_development" / "SelfImproving_Operations_SOP.md"


def setUpModule() -> None:
    fx.setup("si_p2m_")


def tearDownModule() -> None:
    fx.teardown()


# --------------------------------------------------------------------------- R102：AT 錨定規則
_HEAD_RE = re.compile(r"^# (AT-[\d-]+(?:-E-\d+|-\d+)?)\s*\n(?:#[^\n]*\n){3}"
                      r"# 判定指令: python -m pytest "
                      r"(\S+) -k (\S+)", re.M)


def parse_at_headers(tcs_text: str) -> list[tuple[str, str, str]]:
    """（AT id, 測試檔路徑, `-k` 值）；自 §2 每個 AT 標頭取得。"""
    return [(a, f, k) for a, f, k in _HEAD_RE.findall(tcs_text)]


def underscore_form(at_id: str) -> str:
    return at_id.replace("-", "_")


def anchor_problems(ats, collected: dict[str, list[str]]) -> list[str]:
    """R102 (c)(d)(e)：`ats`＝[(AT id, 檔, -k)]；`collected`＝{檔名: [節點 id]}。"""
    out, claimed = [], {}
    for at, f, k in ats:
        nodes = collected.get(Path(f).name, [])
        hits = [n for n in nodes if k.lower() in n.lower()]
        if not k.endswith("_"):
            out.append(f"{at}：-k 值 {k} 非錨定（無結尾底線）")
        elif k[:-1] != underscore_form(at):
            out.append(f"{at}：-k 值去掉結尾底線後 {k[:-1]} 不等於 AT 底線形")
        if len(hits) != 1:
            why = "零命中" if not hits else f"命中 {len(hits)} 個"
            bare = [n for n in nodes if underscore_form(at).lower() in n.lower() and re.search(
                rf"::test_{re.escape(underscore_form(at))}$", n)]
            out.append(f"{at}：{why}" + ("（函式名缺 slug）" if bare else ""))
        for n in hits:
            if n in claimed and claimed[n] != at:
                out.append(f"{at}：函式 {n} 同時被 {claimed[n]} 命中")
            claimed[n] = at
    return out


def collect_nodes(files: list[Path], cwd: Path) -> dict[str, list[str]]:
    out = {}
    for f in files:
        cp = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p",
            "no:xdist",
                             "-o", "addopts=", str(f)], cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
        out[f.name] = [ln.strip() for ln in cp.stdout.splitlines() if "::" in ln]
    return out


def real_tcs(prefix: str) -> str:
    (path,) = sorted(TCS_DIR.glob(f"TCS-SelfImproving-{prefix}-*.md"))
    return path.read_text(encoding="utf-8")


class TestAnchorRule(unittest.TestCase):
    # 受測面：tools/lib/selfimproving/sandbox.py（程式碼鎖，非散文）
    def test_AT_240_9_1_every_at_anchors_one_function(self):
        text = real_tcs("P2")
        ats = parse_at_headers(text)
        self.assertEqual(len(ats), 137)
        files = sorted({ROOT / f for _, f, _ in ats})
        collected = collect_nodes(files, ROOT)
        self.assertEqual(anchor_problems(ats, collected), [])
        for nodes in collected.values():
            for n in nodes:
                name = n.rsplit("::", 1)[-1]
                if name.startswith("test_AT_"):
                    self.assertRegex(name, r"^test_AT_[0-9A-Z_]+_[a-z0-9_]+$", n)

    def test_AT_240_9_E_1_checker_has_teeth(self):
        tmp = fx.new_dir("anchor")
        tmp.mkdir(parents=True)
        path = tmp / "test_synth.py"
        path.write_text("""import unittest


class T(unittest.TestCase):
    def test_AT_999_1_E_1_alpha(self): pass
    def test_AT_999_1_E_10_beta(self): pass
    def test_AT_999_2_1_gamma(self): pass
    def test_AT_999_3_1(self): pass
""", encoding="utf-8")
        collected = collect_nodes([path], tmp)
        syn = "tools/tests/" + "test_synth.py"  # 合成檔名，不是真鎖檔參照
        mk = lambda at, k: [(at, syn, k)]  # noqa: E731
        self.assertTrue(any("非錨定" in p for p in anchor_problems(
            mk("AT-999-1-E-1", "AT_999_1_E_1"), collected)))
        self.assertEqual(anchor_problems(mk("AT-999-1-E-1", "AT_999_1_E_1_"), collected), [])
        self.assertEqual(anchor_problems(mk("AT-999-1-E-10", "AT_999_1_E_10_"), collected), [])
        self.assertTrue(anchor_problems(mk("AT-999-2-1", "AT_999_2_2_"), collected))
        self.assertTrue(anchor_problems(mk("AT-999-4-1", "AT_999_4_1_"), collected))
        both = [("AT-999-2-1", syn, "AT_999_2_1_"),
                ("AT-999-2-1", syn, "AT_999_2_1_")]
        self.assertEqual(anchor_problems(both, collected), [])  # 同一 AT 重複不算兩個 AT 命中
        two = [("AT-999-2-1", syn, "AT_999_2_1_"),
               ("AT-999-2-X", syn, "AT_999_2_1_")]
        self.assertTrue(any("同時被" in p for p in anchor_problems(two, collected)))
        got = anchor_problems(mk("AT-999-3-1", "AT_999_3_1_"), collected)
        self.assertTrue(any("零命中" in p and "缺 slug" in p for p in got), got)
        cp = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p",
            "no:xdist",
                             "-o", "addopts=", "-k", "AT_999_1_E_1", str(path)], cwd=tmp,
                            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(len([ln for ln in cp.stdout.splitlines() if "::" in ln]), 2)


# --------------------------------------------------------------------------- R108：SOP 條文
HEAD_RE = re.compile(r"^(#{1,6}) (.*)$")


def heading_section(text: str, key: str) -> str:
    """含 `key` 的標題及其內文（至下一個同層或更高層標題前）；找不到回空字串。"""
    lines, out, level = text.replace("\r\n", "\n").split("\n"), [], None
    for ln in lines:
        m = HEAD_RE.match(ln)
        if level is None:
            if m and key in m.group(2):
                level, out = len(m.group(1)), [ln]
        elif m and len(m.group(1)) <= level:
            break
        else:
            out.append(ln)
    return "\n".join(out)


VERBS = ("decide", "heldout-freeze", "sandbox", "verify", "promote", "rollback", "card --issue",
         "obs-add", "obs-close")
REVIEW = ("審查者", [("REQ-24", ["審查者≠提案者", "不同代理實例與不同 context"]),
                    ("REQ-25", ["全程唯讀"]), ("REQ-26", ["不得自起背景長任務"]),
                    ("REQ-27", ["主依據為外部可重跑訊號"]),
                    ("REQ-28", ["LLM 意見不得單獨把 FAIL 改成 PASS"])])
P2 = "P2 動詞"
# （項, 節, 同一行必含的片段, 刪除時動的片段；None＝取第一個片段）
LINE_REQS = [
    *[(f"REQ-{3 + i:02d}", P2, [f"| `{v}` |", "rc 0", "rc 1", "rc 3"], f"| `{v}` |")
      for i, v in enumerate(VERBS)],
    ("REQ-12", P2, ["rc 0 不論 verdict", "讀 verdict 不讀 rc"], "rc 0 不論 verdict"),
    ("REQ-13", P2, ["VERIFY-RUNS-EXCEEDED", "升級人工"], None),
    ("REQ-14", P2, ["rc 0 涵蓋 applied=false"], None),
    ("REQ-16", P2, ["不寫引言", "不寫 `--reason`"], None),
    ("REQ-17", P2, ["凍結者≠提案者", "`prop-new` 之後", "`sandbox` 之前"], None),
    ("REQ-18", P2, ["PASS 用前式", "NE 用未驗採納式"], None),
    ("REQ-19", P2, ["主控 commit", "DEC-ID"], None),
    ("REQ-20", P2, ["回滾", "decide --kind rollback", "`rollback`"], "decide --kind rollback"),
    ("REQ-22", P2, ["decide --carrier console", "obs-add", "obs-close", "主機端", "單窗口"], None),
    ("REQ-23", P2, ["AUTOSDD_UNATTENDED", "rc 1", "入帳期間", "不手編 OBS 帳本"], None),
    *[(rid, REVIEW[0], frags, None) for rid, frags in REVIEW[1]],
    ("REQ-29", P2, ["遇 R-9.6 擋寫或 harness 分類器拒絕"], None),
    ("REQ-30", P2, ["不得以改派子代理或換路徑繞過"], None),
    ("REQ-31", P2, ["改由符合條件的視窗處理或走轉交"], None),
    ("REQ-32", P2, ["逐字入帳", "指令", "rc", "out_sha256", "out_bytes", "遮蔽末段"], "逐字入帳"),
    ("REQ-33", P2, ["[他包回報]"], None),
    ("REQ-34", P2, ["主控親跑後才升格為已驗證"], None),
    ("REQ-35", P2, ["貼不出輸出者改寫為未驗證"], None),
]
SEQ_TOKENS = ["card --issue", "decide", "heldout-freeze", "sandbox", "verify",
              "decide --kind promote", "promote"]


def _fences(section: str) -> list[str]:
    return re.findall(r"```[a-z]*\n(.*?)```", section, re.S)


def sop_p2_problems(text: str) -> list[str]:
    """R108／SOP-P2-REQ：逐項判，每項只在自己的片段缺失時被點名（`REQ-NN` 起頭）。"""
    out: list[str] = []
    p2, rev = heading_section(text, P2), heading_section(text, REVIEW[0])
    if not p2 or "待補" in p2.split("\n", 1)[0] or "待補" in p2:
        out.append("REQ-01：〈P2 動詞〉節缺或含「待補」")
    if "呼叫它們一律 rc 3" in p2:
        out.append("REQ-02：含「呼叫它們一律 rc 3」")
    for rid, sec, frags, _ in LINE_REQS:
        body = rev if sec == REVIEW[0] else p2
        raw = [ln for ln in body.split("\n") if all(f in ln for f in frags)]
        outside = [ln for ln in fx.lines_outside_fences(body) if all(f in ln for f in frags)]
        if not outside:
            out.append(f"REQ-{rid[4:]}：缺必備片段 {frags}" + ("（條文不在圍欄外）" if raw else ""))
    blocks = _fences(p2)
    seq = next((b for b in blocks if "card --issue" in b), "")
    pos, ordered = 0, True
    for tok in SEQ_TOKENS:
        found = seq.find(tok, pos)
        ordered = ordered and found >= 0
        pos = found + len(tok) if found >= 0 else pos
    if not ordered:
        out.append("REQ-15：最小序列缺項或順序不符")
    if not (any("powershell" in m.lower() for m in re.findall(r"```(\w*)", p2))
            and any(m.lower() == "bash" for m in re.findall(r"```(\w*)", p2))):
        out.append("REQ-21：PowerShell 與 bash 兩形態須各有程式碼圍欄")
    if "SCG-4 收尾前" not in text:
        out.append("REQ-36：全檔缺「SCG-4 收尾前」")
    return out


def remove_probe(text: str, section: str, frags, probe: str) -> str:
    """自該項的第一條命中行（圍欄外）刪去其動的片段第一次出現；其餘位元組不動。"""
    body = heading_section(text, section)
    hits = [ln for ln in fx.lines_outside_fences(body) if all(f in ln for f in frags)]
    assert hits, (section, frags)
    for ln in hits:  # 所有命中行都動，才不會被同一條文的另一行頂替
        text = text.replace(ln, ln.replace(probe, "", 1), 1)
    return text


def wrap_in_fence(text: str, section: str, frags) -> str:
    body = heading_section(text, section)
    lines = [ln for ln in fx.lines_outside_fences(body) if all(f in ln for f in frags)]
    out = text
    for ln in lines:
        out = out.replace(ln, f"```\n{ln}\n```", 1)
    return out


class TestSopP2(unittest.TestCase):
    def test_AT_240_13_1_real_sop_passes(self):
        text = SOP.read_text(encoding="utf-8")
        self.assertEqual(sop_p2_problems(text), [])

    def test_AT_240_13_E_1_each_item_has_teeth(self):
        text = SOP.read_text(encoding="utf-8")
        self.assertEqual(sop_p2_problems(text), [])
        deleted = 0
        for rid, sec, frags, probe in LINE_REQS:
            with self.subTest(rid):
                changed = remove_probe(text, sec, frags, probe or frags[0])
                problems = sop_p2_problems(changed)
                self.assertTrue(any(p.startswith(f"REQ-{rid[4:]}") for p in problems), (rid,
                    problems))
                self.assertEqual([p for p in problems if not p.startswith(f"REQ-{rid[4:]}")], [],
                                 rid)
                deleted += 1
        self.assertEqual(deleted + 5, 36)  # REQ-01、02、15、21、36 另以變形測（見下）
        rev = heading_section(text, REVIEW[0])
        wrapped = text.replace(rev, "```\n" + rev.split("\n", 1)[1] + "\n```", 1)
        flagged = {p[:6] for p in sop_p2_problems(wrapped)}
        self.assertEqual(flagged, {f"REQ-{n}" for n in range(24, 29)})  # 〈審查者〉五項，只點名它們
        swapped = text.replace("& $py $si heldout-freeze", "@@A@@").replace(
            "& $py $si sandbox", "& $py $si heldout-freeze", 1).replace(
            "@@A@@", "& $py $si sandbox", 1)
        self.assertTrue(any(p.startswith("REQ-15") for p in sop_p2_problems(swapped)))
        self.assertTrue(any(p.startswith("REQ-01") for p in sop_p2_problems(
            text.replace("### P2 動詞", "### P2 動詞（待補）", 1))))
        self.assertTrue(any(p.startswith("REQ-02") for p in sop_p2_problems(
            text + "\n呼叫它們一律 rc 3\n")))
        self.assertTrue(any(p.startswith("REQ-36") for p in sop_p2_problems(
            text.replace("SCG-4 收尾前", "SCG-4 前"))))
        self.assertTrue(any(p.startswith("REQ-12") for p in sop_p2_problems(
            text.replace("rc 0 不論 verdict", "rc 0 表示通過"))))
        no_pwsh = text.replace("```powershell", "```text")
        self.assertTrue(any(p.startswith("REQ-21") for p in sop_p2_problems(no_pwsh)))

class TestSopRoles(P2TestCase):
    def test_AT_218_1_1_machine_half_accepts_legal_split(self):
        rev = heading_section(SOP.read_text(encoding="utf-8"), "審查者")
        for _, frags in REVIEW[1]:
            self.assertTrue(fx.line_has_all(rev, *frags), frags)
        self.new_home()
        R = fx2.p2_base()
        run = fx2.open_run(R)
        rc, out, err = self.M(R, "prop-new", "--run", run, *fx.good_prop_args(
            R, "D", patch=fx.patch_insert(fx2.DEMO, 50, ["FIXED-LINE"],
            old=fx.fixture_files()[fx2.DEMO]),
            target=[fx2.DEMO], reviewer="RV"))
        self.assertEqual(rc, 0, out + err)
        p = re.search(r"id=(\S+)", out).group(1)
        pe = fx2.prop_event(R, p)
        self.assertEqual((pe["reviewer"], pe["proposer"]), ("RV", "SA"))
        fx2.issue_card(R, p)
        self.assertEqual(fx2.decide_say(R, p, f"核准 {p}")[0], 0)
        rc, out, err = fx2.cli(R, "heldout-freeze", p, "--from", fx2.make_heldout(fx.new_dir("ho")),
                               "--by", "FZ")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(fx2.last_event(R, "heldout.freeze")["frozen_by"], "FZ")

    def test_AT_218_1_E_1_roles_must_differ(self):
        self.new_home()
        R = fx2.p2_base()
        run = fx2.open_run(R)
        snap0 = fx.snap(R)
        rc, out, _ = self.M(R, "prop-new", "--run", run, *fx.good_prop_args(
            R, "D", patch=fx.patch_insert(fx2.DEMO, 50, ["FIXED-LINE"],
            old=fx.fixture_files()[fx2.DEMO]),
            target=[fx2.DEMO], reviewer="SA"))
        self.assertEqual(rc, 1)
        self.assertIn("REVIEWER-IS-PROPOSER", fx.codes_of(out))
        self.assertEqual(fx.snap(R), snap0)
        p = fx2.drive_to(R, "approved")
        snap1 = fx.snap(R)
        rc, out, _ = self.M(R, "heldout-freeze", p, "--from", fx2.make_heldout(fx.new_dir("ho")),
                            "--by", "SA")
        self.assertEqual(rc, 1)
        self.assertIn("FROZEN-BY-PROPOSER", fx.codes_of(out))
        self.assertEqual(fx.snap(R), snap1)
        text = SOP.read_text(encoding="utf-8")
        for rid, frags, _ in [(r, f, p_) for r, s, f, p_ in LINE_REQS if r in {x for x,
            _ in REVIEW[1]}]:
            problems = sop_p2_problems(remove_probe(text, REVIEW[0], frags, frags[0]))
            self.assertTrue(any(p_.startswith(f"REQ-{rid[4:]}") for p_ in problems), rid)

    def test_AT_215_3_1_guard_surface_only_hands_off(self):
        text = SOP.read_text(encoding="utf-8")
        self.assertTrue(fx.line_has_all(heading_section(text, P2),
            "遇 R-9.6 擋寫或 harness 分類器拒絕",
                                        "不得以改派子代理或換路徑繞過",
                                        "改由符合條件的視窗處理或走轉交"))
        self.new_home()
        R = fx2.p2_base()
        pg = fx2.new_prop(R, route="handoff:T1")
        self.assertEqual(fx2.prop_event(R, pg)["route"], "handoff:T1")
        fx2.issue_card(R, pg)
        rc, out, _, _, _ = fx2.decide_say(R, pg, f"核准 {pg}", issue=False)
        self.assertEqual(rc, 1)
        self.assertEqual(fx.codes_of(out), {"ROUTE-HANDOFF"})
        rc, out, err, _, _ = fx2.decide_say(R, pg, f"轉交 {pg}", issue=False)
        self.assertEqual(rc, 0, out + err)

    def test_AT_215_3_E_1_wider_rules_do_not_bypass_guard_surface(self):
        self.new_home()
        R = fx2.p2_base()
        prm = json.loads(fx.read(R, fx.PARAMS))
        wide = [g for g in prm["non_evolvable_globs"] if g != "**/.claude/**"]
        fx.set_params(R, non_evolvable_globs=wide)
        target = ".claude/hooks/new_guard.py"
        pf = fx2.drive_to(R, "verified", action="add", target=target,
                          heldout=fx2.make_heldout(fx.new_dir("ho"), probes="exists",
                          target=target))
        fx2.decide_say(R, pf, f"晉升 {pf}")
        fx.put(R, fx.PARAMS, fx.dump_params(prm))
        snap0 = fx.snap(R)
        rc, out, _ = self.M(R, "promote", pf)
        self.assertEqual(rc, 1, out)
        self.assertIn("NON-EVOLVABLE-NOW", fx.codes_of(out))
        self.assertIn(target, out)
        self.assertIn("**/.claude/**", out)
        self.assertEqual(fx.snap(R), snap0)
        self.assertFalse((R / target).exists())
        text = SOP.read_text(encoding="utf-8")
        for rid in ("REQ-29", "REQ-30", "REQ-31"):
            item = next(i for i in LINE_REQS if i[0] == rid)
            problems = sop_p2_problems(remove_probe(text, item[1], item[2], item[3] or item[2][0]))
            self.assertTrue(any(p.startswith(f"REQ-{rid[4:]}") for p in problems), rid)

    def test_AT_221_2_1_evidence_clauses_and_event_provenance(self):
        text = SOP.read_text(encoding="utf-8")
        p2 = heading_section(text, P2)
        for frags in (["逐字入帳", "指令", "rc", "out_sha256", "out_bytes", "遮蔽末段"],
                      ["[他包回報]"], ["主控親跑後才升格為已驗證"], ["貼不出輸出者改寫為未驗證"]):
            self.assertTrue(fx.line_has_all(p2, *frags), frags)
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "sandboxed")
        rc, out, err = self.M(R, "verify", p, "--by", "VF1")
        self.assertEqual(rc, 0, out + err)
        ev = fx2.last_event(R, "app.verify")
        self.assertEqual(ev["by"], "VF1")
        self.assertRegex(ev["t"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")
        vf1 = next((R / fx.PROPS_REL / p).glob("verify1.json"))
        doc = json.loads(vf1.read_text(encoding="utf-8"))
        for step in ("baseline", "patched"):
            for rec in doc["steps"][step]:
                self.assertLessEqual({"cmd", "rc", "out_sha256", "out_bytes", "tail"}, set(rec))

    def test_AT_221_2_E_1_missing_evidence_clauses_are_flagged(self):
        text = SOP.read_text(encoding="utf-8")
        for rid in ("REQ-32", "REQ-33", "REQ-34", "REQ-35"):
            item = next(i for i in LINE_REQS if i[0] == rid)
            problems = sop_p2_problems(remove_probe(text, item[1], item[2], item[3] or item[2][0]))
            self.assertTrue(any(p.startswith(f"REQ-{rid[4:]}") for p in problems), rid)
        item = next(i for i in LINE_REQS if i[0] == "REQ-33")
        moved = wrap_in_fence(text, P2, item[2])
        self.assertTrue(any("不在圍欄外" in p for p in sop_p2_problems(moved)))
        self.new_home()
        R = fx2.p2_base()
        p = fx2.drive_to(R, "sandboxed", heldout=fx2.make_heldout(fx.new_dir("ho"), probes="none"))
        rc, out, err = self.M(R, "verify", p, "--json")
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(json.loads(out)["verdict"], "NE")
        self.new_home()
        R2 = fx2.p2_base()
        p2 = fx2.drive_to(R2, "sandboxed", heldout=fx2.make_heldout(fx.new_dir("ho2"),
            probes="none"))
        rc, out, err = self.M(R2, "verify", p2)
        lines = out.split("\n")
        self.assertTrue(lines[lines.index("obs-draft:") + 1].startswith("| OBS"))


# --------------------------------------------------------------------------- R107、R109：零退化
P1_PARAMS = ("cap_frac", "card_line_max", "churn_max", "event_max_bytes", "export_limit_max",
             "ledger_fail_bytes", "ledger_warn_bytes", "max_archive_entries_per_card",
             "max_new_entries",
             "max_proposals_per_run", "max_revisions", "max_touch_ratio", "metrics_rev",
             "migration_base_sha", "min_events", "min_heldout", "min_obs_rows",
             "non_evolvable_globs",
             "research_bytes_max", "research_fetch_max", "research_timeout_seconds",
             "row_max_bytes",
             "spec_body_globs", "stop_after_bad", "w_evt", "w_min", "w_n", "w_opp")
P1_NON_EVOLVABLE = [
    "**/.claude/**", "**/CLAUDE.md", "**/docs_template/**",
    "AISDLC_SDD/*/governance/rules/R-*.yaml",
    "AISDLC_SDD/AISDLC_SDD_v*/**", "docs/01_requirements/SelfImproving_PRD.md",
    "docs/05_development/SelfImproving_*.md", "docs/06_quality/SelfImproving_Event_Ledger.jsonl",
    "docs/06_quality/SelfImproving_Observation_Ledger.md",
    "docs/06_quality/SelfImproving_Proposals/**",
    "docs/06_quality/SelfImproving_Protocol/**", "tools/guard.py", "tools/lib/aa.py",
    "tools/lib/bb.py",
    "tools/lib/cc.py", "tools/lib/selfimproving/**", "tools/probe/selfimproving_measure.py",
    "tools/selfimproving.py"]
P1_SPEC_BODY = ["**/docs/01_requirements/**", "**/docs/02_architecture/**", "**/docs/03_testing/**"]


class TestZeroRegression(P2TestCase):
    def test_AT_240_14_1_p1_scenarios_replay_and_at_coverage(self):
        seq_events, seqs = fx.sc_seq()
        scenarios = {"sc_close": (fx.sc_close(), None), "sc_seq": (seq_events, seqs),
                     "sc_legal": (fx.sc_legal(), None), "sc_rev": (fx.sc_rev(), None),
                     "sc_susp": (fx.sc_susp(), None)}
        for name, (events, seqs_) in scenarios.items():
            with self.subTest(name):
                self.new_home()
                R = fx2.make_p2_repo(fx.new_dir("zr"))
                fx.write_events(R, events, seqs=seqs_)
                res = self.check(R)
                self.assertEqual(self.S(res, "events.structure"), "PASS")
                codes = {c for _, c in self.F(res, "events.transitions")}
                self.assertFalse(codes & {"TRANSITION-ILLEGAL", "TRANSITION-ORPHAN"}, codes)
                folded = si_fold.fold(si_events.sound(fx.EV(R)), 2)
                if name == "sc_susp":
                    self.assertIsNotNone(folded.suspended)
        surface = list((ROOT / "tools" / "tests").glob("*.py")) + [
            ROOT / "AutoClaude" / "tests" / "contract" / "test_evolution_propose_only.py"]
        names = "\n".join(n for p in surface if p.is_file()
                          for n in re.findall(r"def (test_\w+)", p.read_text(encoding="utf-8")))
        ids = []
        for prefix in ("P0", "P1"):
            ids += sorted({m for m in re.findall(r"^# (AT-[\d-]+(?:-E-\d+|-\d+)?)\s*$",
                                                 real_tcs(prefix), re.M)})
        self.assertEqual(len(ids), 205)
        missing = [a for a in ids if underscore_form(a) not in names]
        self.assertEqual(missing, [])
        self.assertEqual(set(si_params.PARAM_SPECS), {*P1_PARAMS, "probe_timeout_seconds",
                                                      "verify_runs_max"})
        prm = fx.params_dict()
        self.assertEqual(prm["non_evolvable_globs"], P1_NON_EVOLVABLE)
        self.assertEqual(prm["spec_body_globs"], P1_SPEC_BODY)

    def test_AT_240_14_E_1_explicit_values_stay_wrong(self):
        n = 124
        bad = [
            ("EVENT-TYPE", fx.dec_ev(n, "approve", digest="sha256:bad")),
            ("EVENT-TYPE", fx.dec_ev(n, "promote", flags=["x"])),
            ("EVENT-TYPE", fx.dec_ev(n, "reject", reason_class="隨便")),
            ("EVENT-TYPE", fx.ev("app.sandbox", "main", prop=fx.pid(n), applied=True,
            touched_ok=None)),
            ("EVENT-TYPE", fx.ev("app.verify", "main", prop=fx.pid(n), verdict="PASS",
                                 reasons=["BASELINE-NOT-RED"])),
            ("EVENT-TYPE", fx.ev("card", "main", prop=fx.pid(n), rev=0)),
            ("EVENT-KEY-UNKNOWN", fx.ev("app.promote", "main", prop=fx.pid(n),
            commit_sha="a" * 40)),
            ("EVENT-TYPE", fx.ev("heldout.freeze", "main", prop=fx.pid(n), n=0)),
        ]
        for code, event in bad:
            with self.subTest(event["kind"] + str(sorted(event))[:30]):
                obj = fx.compose([event], "0" * 40, [9])[0]
                self.assertIn(code, {c for c, _ in si_events.validate(obj)})
        for ok in (fx.dec_ev(n, "approve"), fx.prop_ev(n, 1)):
            obj = fx.compose([ok], "0" * 40, [9])[0]
            self.assertEqual(si_events.validate(obj), [])


if __name__ == "__main__":
    unittest.main()
