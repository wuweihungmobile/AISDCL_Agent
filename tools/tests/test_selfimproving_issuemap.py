# 受測面：tools/lib/selfimproving/issuemap.py（程式碼鎖，非散文）
"""議題中心對照表的驗收測試（TCS-IssueCenter §3.2 的 RM 組；AT-IC-01-1、01-4、01-7 的純表部分）。

方法名含 AT 底線形。本檔只放不需要帳本夾具的純表 AT；需要 repo 夾具的 FR-IC-01 AT 在
`test_selfimproving_issues.py`（TCS §7.2 Q2）。判準函式取參數，故真值與合成值用同一份碼自證。
"""

from __future__ import annotations

import re
import unittest
from itertools import product

import _selfimproving_fixtures as fx

from lib.selfimproving import defs as si_defs
from lib.selfimproving import events as si_events
from lib.selfimproving import issuemap as im
from lib.selfimproving import rows as si_rows

REAL_DEFECT_LOG = fx.ROOT / "docs" / "06_quality" / "AutoSDD_Defect_Log.md"
# 八個處置首詞探針 → 對照表鍵（`fixed@`、`merged@`、`proposed@`、`DEF-` 以前綴為鍵）
PROBES = {
    "open": "open",
    "deferred": "deferred",
    "retired": "retired",
    "decided": "decided",
    "fixed@abc1234": "fixed@",
    "DEF-1-1": "DEF-",
    "merged@OBS-SI-001": "merged@",
    "proposed@PROP-SI-001": "proposed@",
}
FOREIGN_PROBES = ("later", "closed")  # 未列探針：disp_token 回 None
WINDOWS = (None, "clean", "recurred", "rolled-back", "pending")
COUNTS = (0, 1, 2)  # decided、pending、consumed 的取值格


class TestIssueMapClosure(unittest.TestCase):
    """`tools/lib/selfimproving/issuemap.py` 的雙向封閉與唯一歸類（AC-IC-01-1、01-7 的字典鎖）。"""

    def test_AT_IC_01_1_1_every_machine_value_has_exactly_one_classification(self):
        self.assertEqual(im.closure_problems(), [])
        up = im.real_upstream()
        self.assertEqual(im.real_table(), up)  # 表內沒有可鎖集合以外的鍵，雙向相等
        for key, decision, established in product(sorted(up["disp_tokens"]), (False, True),
                                                  (False, True)):
            hit = im.status_of("obs", key, decision=decision, established=established)
            self.assertIsNotNone(hit, (key, decision, established))
            self.assertIn(hit[0], im.STATUSES)
            self.assertTrue(hit[1] is None or hit[1] in im.RESULTS, hit)
            if key == "open":
                want = "待您決定" if decision else ("待解" if established else "候選")
                self.assertEqual(hit, (want, None))
        for key, sibling in product(sorted(up["def_labels"]), (False, True)):
            hit = im.status_of("def", key, sibling=sibling)
            self.assertIsNotNone(hit, (key, sibling))
            self.assertEqual(hit[0] == "延後", sibling)
            self.assertTrue(hit[1] is None or hit[1] in im.RESULTS, hit)
        for state, window, decided, pending, consumed in product(
                sorted(up["prop_states"]), WINDOWS, COUNTS, COUNTS, COUNTS):
            cond = dict(window=window, decided=decided, pending=pending, consumed=consumed)
            hit = im.status_of("prop", state, **cond)
            self.assertIsNotNone(hit, (state, cond))
            self.assertIn(hit[0], im.STATUSES)
            if hit[1] is not None and hit[1] not in im.RESULTS:  # 唯一的非表內結果＝量不到
                self.assertEqual((state, hit[1]), ("closed", im.unmapped("closed")))
        for kind, key in (("obs", "later"), ("def", "later"), ("prop", "zombie"), ("zz", "open")):
            self.assertIsNone(im.status_of(kind, key), (kind, key))
        self.assertIsNone(im.status_of("obs", None))
        self.assertIsNone(im.status_of("def", None))

    def test_AT_IC_01_1_2_disposition_probes_and_pattern_branch_count(self):
        for probe, key in PROBES.items():
            token = si_rows.disp_token(probe)
            self.assertIsNotNone(token, probe)
            self.assertEqual(im.obs_key(token), key, probe)
            self.assertIsNotNone(im.status_of("obs", token, established=True), probe)
        for probe in FOREIGN_PROBES:
            self.assertIsNone(si_rows.disp_token(probe), probe)
            self.assertIsNone(im.obs_key(si_rows.disp_token(probe)), probe)
        group = re.match(r"\^\(([^()]*)\)", si_rows.DISP_TOKEN_RE.pattern)
        self.assertIsNotNone(group)
        self.assertEqual(len(group.group(1).split("|")), 8)
        self.assertEqual(len(im._first_group_branches(si_rows.DISP_TOKEN_RE.pattern)), 8)
        self.assertEqual(set(PROBES.values()), im.real_upstream()["disp_tokens"])

    def test_AT_IC_01_1_E_1_upstream_additions_are_reported_by_name(self):
        base = im.real_upstream()
        self.assertEqual(im.closure_problems(base), [])  # 對照組：真上游回空
        variants = {
            "prop_states": "zombie",
            "kinds": "foo",
            "dkinds": "bar",
            "categories": "ux",
            "disp_tokens": "later",  # 處置探針加第 9 分支
            "def_labels": "stale",
        }
        for dim, value in variants.items():
            with self.subTest(dim):
                synthetic = {**base, dim: {*base[dim], value}}
                found = im.closure_problems(synthetic)
                self.assertTrue(found, dim)
                self.assertTrue(all(value in p and "上游有而表無" in p for p in found), found)
                self.assertTrue(all(p.startswith(f"{dim}：") for p in found), found)

    def test_AT_IC_01_1_E_2_table_deletions_and_additions_are_reported_both_ways(self):
        table = im.real_table()
        missing = {**table, "prop_states": table["prop_states"] - {"promoted"}}
        found = im.closure_problems(table=missing)
        self.assertEqual(len(found), 1, found)
        self.assertTrue("表缺" in found[0] and "promoted" in found[0], found)
        extra = {**table, "prop_states": {*table["prop_states"], "ghost"}}
        found = im.closure_problems(table=extra)
        self.assertEqual(len(found), 1, found)
        self.assertTrue("表多" in found[0] and "ghost" in found[0], found)
        self.assertEqual(im.closure_problems(table=table), [])  # 對照組


class TestIssueMapDictionaries(unittest.TestCase):
    """`tools/lib/selfimproving/issuemap.py` 的嚴重度函式與三本中文字典（AC-IC-01-4、01-7）。"""

    def test_AT_IC_01_4_1_severity_mapping_for_both_groups(self):
        want = {"P1": ("緊急", 1), "P2": ("高", 2), "P3": ("中", 3), "P4": ("低", 4)}
        for raw, hit in want.items():
            self.assertEqual(im.severity_of("obs", raw), hit, raw)
        self.assertIsNone(im.severity_of("obs", "P0"))  # 觀察組只有 P1～P4
        cases = {
            "P0": ("緊急", 1),
            "P1": ("緊急", 1),
            "P2": ("高", 2),
            "P3": ("中", 3),
            "P4": ("低", 4),
            "**P1** 說明": ("緊急", 1),  # 開頭的強調記號與後綴說明都不影響
            " P2（後綴）": ("高", 2),
            "_P3_": ("中", 3),
            "P4-備註": ("低", 4),
        }
        for raw, hit in cases.items():
            self.assertEqual(im.severity_of("def", raw), hit, raw)
        for raw in ("(P1)", "- P1", "備註 P1", "`P2`", "p1", "P", "", "—（流程紀錄）"):
            self.assertIsNone(im.severity_of("def", raw), raw)  # 只略過空白、`*`、`_`
        self.assertEqual({k for k in im.DEF_SEVERITIES}, {"P0", "P1", "P2", "P3", "P4"})

    def test_AT_IC_01_4_2_real_defect_ledger_first_codes_are_inside_the_constant(self):
        rows = si_defs.load_rows(REAL_DEFECT_LOG)
        self.assertGreater(len(rows), 100)  # 讀得到真主檔，不是 0 列假綠
        first = [re.match(r"^[\s*_]*(P\d+)", r.severity) for r in rows]
        self.assertTrue(all(first), [r.ident for r, m in zip(rows, first) if not m])
        self.assertLessEqual({m.group(1) for m in first}, set(im.DEF_SEVERITIES))
        self.assertTrue(all(im.severity_of("def", r.severity) for r in rows))

    def test_AT_IC_01_7_2_channel_event_and_decision_dictionaries(self):
        suffixes = {r.split(":", 1)[1] for r in si_events.ROUTES if r.startswith("handoff:")}
        self.assertEqual(suffixes, {"DEF", "R", "T1", "PRD"})
        self.assertEqual(set(im.ROUTE_LABELS), suffixes)
        self.assertEqual(set(im.EVENT_LABELS), set(si_events.KINDS))
        self.assertEqual(len(im.EVENT_LABELS), 21)
        self.assertEqual(set(im.DKIND_LABELS), set(si_events.DKINDS))
        self.assertEqual(len(im.DKIND_LABELS), 9)
        for name, book in (("通道", im.ROUTE_LABELS), ("事件", im.EVENT_LABELS),
                           ("決定", im.DKIND_LABELS)):
            values = list(book.values())
            self.assertTrue(all(isinstance(v, str) and v for v in values), name)
            self.assertEqual(len(set(values)), len(values), f"{name}字典的中文須互異")
        for suffix in suffixes:
            self.assertEqual(im.route_label(suffix), im.route_label(f"handoff:{suffix}"))
        self.assertIsNone(im.route_label("loop"))
        self.assertIsNone(im.event_label("zombie.act"))
        self.assertIsNone(im.dkind_label("zombie"))


if __name__ == "__main__":
    unittest.main()
