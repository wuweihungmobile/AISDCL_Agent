# 受測面：tools/lib/selfimproving/issues.py（程式碼鎖，非散文）
"""議題中心聚合的驗收測試（TCS-IssueCenter §3.2 的 RI 組；AC-IC-01～06、12 的 repo 夾具部分）。

方法名含 AT 底線形。夾具建構函式住本檔模組層（TCS D-R11；`test_selfimproving_issuemap.py` 與
`test_selfimproving_export_status.py` 的議題匯出類別由此取用）。合成編號一律於執行期組出：假缺陷號
用 `def999`（999 族為合成測試保留）、假觀察號用 `fx.obs_id`，原始碼不寫不存在於真帳本的字面編號。
注入縫（TCS §5.2）只在 in-process 的 `build_obj`／`self.M` 路徑可用，子行程路徑不經縫。
"""

from __future__ import annotations

import builtins
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import unittest
from pathlib import Path
from unittest import mock

import _selfimproving_fixtures as fx
import _selfimproving_p2_fixtures as fx2
import _selfimproving_p3_fixtures as f3
from _selfimproving_fixtures import aid, obs_id, pid

import selfimproving
from lib.selfimproving import card as si_card
from lib.selfimproving import check as si_check
from lib.selfimproving import events as si_events
from lib.selfimproving import fold as si_fold
from lib.selfimproving import issuemap as im
from lib.selfimproving import issues
from lib.selfimproving import mea as si_mea
from lib.selfimproving import meaplan as si_meaplan
from lib.selfimproving.git import Git

TOOLS = fx.TOOLS
ENTRY = TOOLS / "selfimproving.py"
PKG = TOOLS / "lib" / "selfimproving"
QUALITY = "docs/06_quality"
SIB_BLOCKED = f"{QUALITY}/AutoSDD_External_Blocked_Log.md"
SIB_DEBT = f"{QUALITY}/AutoSDD_Structural_Debt_Log.md"
OBS_ARCHIVE = f"{QUALITY}/SelfImproving_Observation_Ledger_archive_01.md"
DEF_ARCHIVE = f"{QUALITY}/AutoSDD_Defect_Log_archive_01.md"
DEF_SEP = "|---|---|---|---|---|---|---|"
SIB_HEAD = (
    "# 姊妹軌（夾具）\n\n## 格式定義\n\n| 欄位 | 說明 |\n|---|---|\n| `DEF-ID` | 夾具說明 |\n\n"
    "## 缺陷總表\n\n| DEF-ID | 具名阻塞源 | 阻塞起始日 | 解鎖條件（可機械查） | 最近複查日 |\n"
    "|---|---|---|---|---|\n"
)
MARKS = "面=產品;來源=代理;回報者=QA"
# PRD §5.4 的 22 個英文狀態詞（TCS §5.4；整詞比對、前後字元不屬英數與 `-`）
ENGLISH_STATE_WORDS = (
    "open", "deferred", "fixed", "decided", "retired", "merged", "proposed", "routed", "wontfix",
    "closed-by-decision", "no_action_needed", "partial", "workaround", "verified", "approved",
    "returned", "sandboxed", "promoted", "measuring", "closed", "rejected", "handed-off",
)
ID_FORM = re.compile(r"OBS-SI-\d{3,}|PROP-SI-\d{3,}|DEF-\d+-\d+")
LEGAL_VERBS = (
    "check", "status", "scan", "card", "export", "run-open", "run-close", "attr", "attr-confirm",
    "attr-reject", "prop-new", "prop-revise", "research", "decide", "heldout-freeze", "sandbox",
    "verify", "promote", "rollback", "obs-add", "obs-close", "measure", "capacity",
)


def setUpModule() -> None:
    fx.setup("si_ic_")


def tearDownModule() -> None:
    fx.teardown()


# --------------------------------------------------------------------------- 夾具建構器（D-R11）
def def999(n: int) -> str:
    """合成缺陷號（999 族）；執行期組字，沿 `fx.def_id` 的慣例。"""
    return "DEF" + f"-999-{n:03d}"


def obs_row(n, cat="bug", sev="P3", disp="open", marks=MARKS, symptom=None,
            time="2026-10-18 10:00 +08:00", evidence="tools/lib/selfimproving/issues.py:1"):
    """九欄觀察列；ID 由 `fx.obs_id(n)` 產生。"""
    return [obs_id(n), time, "夾具", symptom or f"症狀 {n}", evidence, cat, sev, disp, marks]


def def_row(n, sev="P2", status="open", date="2026-10-18", evidence=None):
    """缺陷主檔的七欄列；ID＝`def999(n)`。"""
    return [def999(n), date, "夾具", evidence or f"現象 {n}", sev, "-", status]


def sib_row(n, unlock="夾具解鎖條件", review="2026-10-20"):
    """姊妹軌的五欄列；ID＝`def999(n)`。"""
    return [def999(n), "Windows 實機", "2026-10-01", unlock, review]


def def_text(rows) -> str:
    return "\n".join([fx.DEF_HDR, DEF_SEP, *[fx.line(r) for r in rows]]) + "\n"


def sib_text(rows) -> str:
    return SIB_HEAD + "".join(fx.line(r) + "\n" for r in rows)


def git_template() -> Path:
    """只含一個空 commit 的 `.git`（每個測試檔建一次；各夾具以複製代替三次 git 子行程）。"""
    if "ic_git" not in fx._CACHE:
        tpl = fx.new_dir("gtpl")
        tpl.mkdir()
        fx.git(tpl, "init", "-q")
        fx.commit_all(tpl, "C1")
        fx._CACHE["ic_git"] = tpl / ".git"
    return fx._CACHE["ic_git"]


def issue_repo(tmp, *, obs=(), defs=(), sib_blocked=(), sib_debt=(), events=(), obs_archive=None,
               def_archive=None, git=True) -> Path:
    """hermetic tmp repo：觀察帳本、缺陷主檔、兩姊妹軌、事件帳本、真 `params.json`；某帳本參數給
    `None`＝缺檔（事件帳本預設為空 jsonl）；`git=True` 帶一個空 commit 的 `.git`。"""
    tmp.mkdir(parents=True)
    if obs is not None:
        fx.put(tmp, fx.LEDGER, fx.render_ledger(obs))
    if defs is not None:
        fx.put(tmp, fx.DEFLOG, def_text(defs))
    for rel, rows in ((SIB_BLOCKED, sib_blocked), (SIB_DEBT, sib_debt)):
        if rows is not None:
            fx.put(tmp, rel, sib_text(rows))
    if obs_archive is not None:
        fx.put(tmp, OBS_ARCHIVE, fx.render_ledger(obs_archive))
    if def_archive is not None:
        fx.put(tmp, DEF_ARCHIVE, def_text(def_archive))
    fx.putb(tmp, fx.PARAMS, fx.REAL_PARAMS.read_bytes())
    if git:
        shutil.copytree(git_template(), tmp / ".git")
    if events is not None:
        fx.write_events(tmp, list(events))
    return tmp


def build_obj(repo, **kw) -> dict:
    """in-process 呼叫 `issues.build`（注入縫只在此路徑可用）。"""
    return issues.build(repo, Git(repo), si_check.params_for(repo, "export_limit_max"), **kw)


def run_raw(repo, *argv):
    """子行程跑 `tools/selfimproving.py`（任意 cwd、不設任何編碼環境變數）；回 (rc, stdout 位元組,
    stderr 位元組)。"""
    cp = subprocess.run([sys.executable, str(ENTRY), *argv, "--repo", str(repo)], cwd=str(repo),
                        capture_output=True, check=False)
    return cp.returncode, cp.stdout, cp.stderr


def run_issues(repo, *argv):
    """同 `run_raw` 但以 UTF-8 解碼；回 (rc, 標準輸出, 標準錯誤)。"""
    rc, out, err = run_raw(repo, "issues", *argv)
    return rc, out.decode("utf-8"), err.decode("utf-8")


def by_id(obj) -> dict:
    return {i["id"]: i for i in obj["items"]}


def notes(obj) -> list:
    return [(n["field"], n["reason"]) for n in obj["ne"]]


def problems(obj, code=None) -> list:
    return [(p["subject"], p["code"], p["detail"]) for p in obj["problems"]
            if code is None or p["code"] == code]


def run_events() -> list:
    """提案事件所需的運轉：開（未關）運轉 1 與其免掃事件。"""
    return [fx.run_open_ev(1), fx.skip_ev(1)]


def verified_steps(n, verdict="PASS") -> list:
    return [fx.dec_ev(n, "approve"), fx.freeze_ev(n), fx.sandbox_ev(n), fx.verify_ev(n, verdict)]


def promoted_steps(n) -> list:
    return [*verified_steps(n), fx.dec_ev(n, "promote"), fx.promote_ev(n)]


def closed_steps(n, result, **close) -> list:
    """晉升後開窗、關窗（`result`＝clean、recurred、rolled-back、pending）。"""
    return [*promoted_steps(n), fx.ev("mea.open", prop=pid(n)),
            fx.ev("mea.close", prop=pid(n), result=result, **close)]


def prop_events(n, state, **kw) -> list:
    """提案 `n` 走到某態的事件鏈（不含運轉事件）；`kw` 轉給 `fx.prop_ev`。"""
    steps = {
        "proposed": [],
        "approved": [fx.dec_ev(n, "approve")],
        "returned": [fx.dec_ev(n, "return")],
        "rejected": [fx.dec_ev(n, "reject")],
        "sandboxed": [fx.dec_ev(n, "approve"), fx.freeze_ev(n), fx.sandbox_ev(n)],
        "verified": verified_steps(n),
        "promoted": promoted_steps(n),
        "measuring": [*promoted_steps(n), fx.ev("mea.open", prop=pid(n))],
    }[state]
    return [fx.prop_ev(n, 1, **kw), *steps]


def english_hits(text: str) -> list:
    """句中的英文狀態詞（先剔除議題 ID 形態；整詞比對：前後字元不屬英數與 `-`）。"""
    text = ID_FORM.sub(" ", text)
    return [w for w in ENGLISH_STATE_WORDS
            if re.search(rf"(?<![A-Za-z0-9-]){re.escape(w)}(?![A-Za-z0-9-])", text)]


def display_width(text: str) -> int:
    """顯示寬度（全形與寬字元算 2）；與 `card.width` 各寫一份，互相對拍。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


class IssueCase(f3.P3TestCase):
    """`tools/lib/selfimproving/issues.py` 測試基底：隔離家目錄、逐字稿根與 git 環境。"""

    def new(self, **kw) -> Path:
        return issue_repo(fx.new_dir("ic"), **kw)

    def items_of(self, repo, **kw) -> dict:
        """整本帳（一頁取完）的議題 ID → 議題。"""
        return by_id(build_obj(repo, limit=500, **kw))

    def cli(self, repo, *argv):
        """in-process 的 `issues` 動詞（可疊注入縫）；回 (rc, 標準輸出, 標準錯誤)。"""
        return self.M(repo, "issues", *argv)

    def cli_json(self, repo, *argv) -> dict:
        rc, out, err = self.cli(repo, "--json", *argv)
        self.assertEqual(rc, 0, out + err)
        return json.loads(out)


def zombie(*prop_ids):
    """注入縫 S1：包裝真 `fold`，把指定 PROP 的 `state` 改成 zombie（事件帳本產不出此值）。"""
    real = si_fold.fold

    def wrapped(*a, **k):
        folded = real(*a, **k)
        for prop_id in prop_ids:
            folded.props[prop_id].state = "zombie"
        return folded

    return mock.patch.object(issues.si_fold, "fold", wrapped)


def windows_as(effective):
    """注入縫 S2：`effective_windows` 回 `[]`（None），或把各窗的 `effective` 換成給定值。"""
    real = si_fold.effective_windows
    if effective is None:
        fake = lambda f: []  # noqa: E731
    else:
        fake = lambda f: [dict(w, effective=effective) for w in real(f)]  # noqa: E731
    return mock.patch.object(issues.si_fold, "effective_windows", fake)


class TestFailLoud(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的 fail-loud 與終態對照
    （AC-IC-01-2、01-3、01-6、01-10）。"""

    def test_AT_IC_01_2_1_unmapped_values_fail_loud(self):
        repo = self.new(obs=[obs_row(1, disp="later")], defs=[def_row(1, status="later")],
                        events=[*run_events(), *prop_events(1, "proposed", sources=[def999(1)])])
        with zombie(pid(1)):
            rc, out, err = self.cli(repo, "--json")
            self.assertEqual(rc, 0, err)
            obj = json.loads(out)
            for flt in ("待處理", "待您決定", "已完成", "候選", "延後"):
                kept = build_obj(repo, statuses=[flt])["items"]
                self.assertEqual([i["id"] for i in kept if im.is_unmapped(i["status"])], [], flt)
        got = by_id(obj)
        for ident, raw in ((obs_id(1), "later"), (def999(1), "later"), (pid(1), "zombie")):
            self.assertEqual(got[ident]["status"], f"未歸類：{raw}", ident)
            self.assertIn((ident, "UNMAPPED", f"狀態：{raw}"), problems(obj))
            self.assertFalse(got[ident]["rankable"])
            self.assertIsNone(got[ident]["action"])
        self.assertEqual(len(problems(obj, "UNMAPPED")), 3)
        self.assertEqual(obj["summary"]["unmapped"], 3)

    def test_AT_IC_01_2_E_1_legit_issues_are_not_dragged_along(self):
        legit = [obs_row(2), obs_row(3, disp="fixed@abc1234")]
        clean = self.items_of(self.new(obs=legit, defs=[def_row(2)]))
        mixed = self.new(obs=[obs_row(1, disp="later"), *legit],
                         defs=[def_row(1, status="later"), def_row(2)])
        got = self.items_of(mixed)
        for ident in (obs_id(2), obs_id(3), def999(2)):
            drop = lambda item: {k: v for k, v in item.items() if k != "origin"}  # noqa: E731
            self.assertEqual(drop(got[ident]), drop(clean[ident]), ident)
        kept = build_obj(mixed, statuses=["待處理"])["items"]
        self.assertEqual([i["id"] for i in kept], [def999(2)])
        self.assertFalse({obs_id(1), def999(1)} & {i["id"] for i in kept})

    def test_AT_IC_01_3_1_terminal_states_map_to_the_eight_results(self):
        obs = [obs_row(1), obs_row(2, disp="fixed@abc1234"), obs_row(3, disp="decided：掌舵者裁決"),
               obs_row(4, disp="retired；依據 tools/notes/x.md:3"),
               obs_row(5, disp="merged@" + obs_id(2)), obs_row(6, disp=def999(1)),
               obs_row(7, disp="proposed@" + pid(1))]
        defs = [def_row(1, status="fixed@abc1234"), def_row(2, status="wontfix"),
                def_row(3, status="closed-by-decision")]
        events = [*run_events(), *prop_events(1, "rejected"), fx.prop_ev(2, 1, route="handoff:T1"),
                  fx.dec_ev(2, "ack-handoff"), fx.prop_ev(3, 1), *closed_steps(3, "clean"),
                  fx.prop_ev(4, 1), *closed_steps(4, "rolled-back"), fx.prop_ev(5, 1),
                  *closed_steps(5, "recurred"), fx.dec_ev(5, "rollback"), fx.rollback_ev(5)]
        got = self.items_of(self.new(obs=obs, defs=defs, events=events))
        want = {obs_id(2): "已修復", obs_id(3): "已裁決", obs_id(4): "已退役", obs_id(5): "已合併",
                obs_id(6): "已轉交", obs_id(7): "已轉交", def999(1): "已修復", def999(2): "已否決",
                def999(3): "已裁決", pid(1): "已否決", pid(2): "已轉交", pid(3): "已採納",
                pid(4): "已回滾", pid(5): "已回滾"}
        for ident, result in want.items():
            item = got[ident]
            self.assertEqual((item["status"], item["result"]), ("已完成", result), ident)
            self.assertEqual(got[ident]["next_step"].split("）")[0], f"已結案（{result}", ident)

    def test_AT_IC_01_3_2_non_final_states_have_no_result(self):
        events = [*run_events(), *prop_events(1, "proposed"), *prop_events(2, "measuring")]
        got = self.items_of(self.new(obs=[obs_row(1), obs_row(2, disp="deferred；再開症狀：再發")],
                                     defs=[def_row(1), def_row(2, status="routed")], events=events))
        want = {obs_id(1): "候選", obs_id(2): "延後", def999(1): "待解", def999(2): "進行中",
                pid(1): "待您決定", pid(2): "觀察中"}
        for ident, status in want.items():
            self.assertEqual((got[ident]["status"], got[ident]["result"]), (status, None), ident)
        self.assertEqual(set(want.values()), set(im.STATUSES) - {"已完成"})  # 六個非終態各一個

    def test_AT_IC_01_3_E_1_closed_without_a_measurable_window_is_unmapped(self):
        events = [*run_events(), fx.prop_ev(1, 1), *closed_steps(1, "recurred"), fx.prop_ev(2, 1),
                  *closed_steps(2, "recurred"), fx.dec_ev(2, "rollback"), fx.rollback_ev(2)]
        repo = self.new(obs=[obs_row(1)], events=events)
        for label, patch in (("無窗", windows_as(None)), ("窗為 pending", windows_as("pending"))):
            with patch:
                obj = build_obj(repo)
            got = by_id(obj)
            with self.subTest(label):
                self.assertEqual((got[pid(1)]["status"], got[pid(1)]["result"]),
                                 ("已完成", "未歸類：closed"))
                self.assertEqual(problems(obj, "UNMAPPED"), [(pid(1), "UNMAPPED", "結果：closed")])
                self.assertEqual(got[pid(1)]["next_step"], im.NEXT_STEPS["N19"])
                self.assertFalse(got[pid(1)]["rankable"])
                rolled = got[pid(2)]
                self.assertEqual((rolled["status"], rolled["result"]), ("已完成", "已回滾"))
        self.assertEqual(sum(1 for i in got.values() if i["status"] == "待您決定"), 0)

    def test_AT_IC_01_6_1_each_unmapped_value_is_its_own_problem(self):
        obs = [obs_row(1, disp="later"), obs_row(2, disp="later"), obs_row(3, disp="soon")]
        obj = build_obj(self.new(obs=obs))
        got = by_id(obj)
        self.assertEqual([got[obs_id(n)]["status"] for n in (1, 2, 3)],
                         ["未歸類：later", "未歸類：later", "未歸類：soon"])
        self.assertEqual(problems(obj), [(obs_id(1), "UNMAPPED", "狀態：later"),
                                         (obs_id(2), "UNMAPPED", "狀態：later"),
                                         (obs_id(3), "UNMAPPED", "狀態：soon")])

    def test_AT_IC_01_6_E_1_summary_counts_the_unmapped_apart(self):
        obs = [obs_row(1, disp="later"), obs_row(2, disp="later"), obs_row(3, disp="soon"),
               obs_row(4), obs_row(5, disp="fixed@abc1234")]
        obj = build_obj(self.new(obs=obs))
        s = obj["summary"]
        self.assertEqual(s["unmapped"], 3)
        self.assertEqual(s["total"], sum(s["by_status"].values()) + 3)
        self.assertEqual(s["total"], 5)
        self.assertEqual(len(obj["problems"]), 3)
        self.assertEqual(s["by_status"]["候選"] + s["by_status"]["已完成"], 2)

    def test_AT_IC_01_10_1_long_unmapped_values_are_cut_for_display_only(self):
        raw = "字" * 98 + "😀" * 2
        obj = build_obj(self.new(obs=[obs_row(1, disp=raw)]))
        item = by_id(obj)[obs_id(1)]
        self.assertEqual(item["status"], "未歸類：" + raw[:80] + "…")
        self.assertEqual(problems(obj), [(obs_id(1), "UNMAPPED", f"狀態：{raw}")])
        self.assertEqual(len(problems(obj, "UNMAPPED")), 1)

    def test_AT_IC_01_10_E_1_the_limit_counts_code_points_not_units_or_graphemes(self):
        raws = ["😀" * 80, "😀" * 81, "é" * 40, "é" * 40 + "x"]
        obs = [obs_row(n, disp=raw) for n, raw in enumerate(raws, start=1)]
        obj = build_obj(self.new(obs=obs))
        got = by_id(obj)
        self.assertEqual(got[obs_id(1)]["status"], "未歸類：" + raws[0])
        self.assertEqual(got[obs_id(2)]["status"], "未歸類：" + "😀" * 80 + "…")
        self.assertEqual(got[obs_id(3)]["status"], "未歸類：" + raws[2])
        self.assertEqual(got[obs_id(4)]["status"], "未歸類：" + raws[3][:80] + "…")
        for ident in (obs_id(2), obs_id(4)):
            self.assertNotEqual(got[ident]["status"][-2], "\ud83d")  # 不被截成孤立代理
        self.assertEqual(len(problems(obj, "UNMAPPED")), 4)
        self.assertEqual([p[2] for p in problems(obj)], [f"狀態：{r}" for r in raws])


def card_ok(symptom="夾具症狀"):
    """注入縫 S4 的反面：`card.build` 一律成功（夾具的占位內容檔會引出 CARD-UNAVAILABLE 雜訊，
    與本測試要驗的事無關時用它壓掉）。"""
    card = si_card.CardResult("P", 1, "d", "卡面全文", 0, {}, {"symptom": symptom})
    return mock.patch.object(issues.si_card, "build", lambda *a, **k: card)


def coverage_gap(produced, table) -> list:
    """封閉自證：產出 ⊆ 表 且 表 ⊆ 產出（回缺口說明；空＝兩向皆封閉）。"""
    return ([f"產出有而表無：{c}" for c in sorted(set(produced) - set(table))]
            + [f"表有而夾具未觸發：{c}" for c in sorted(set(table) - set(produced))])


def as_dir(repo, rel) -> None:
    """把帳本檔換成同名目錄（跨平台的「不可讀」構造，不依賴 chmod）。"""
    path = repo / rel
    path.unlink()
    path.mkdir()


class TestSeverityLegendLedgers(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的嚴重度、legend 與帳本缺檔
    （AC-IC-01-4、01-5、01-7～01-9）。"""

    def full_kw(self, **over) -> dict:
        kw = dict(obs=[obs_row(1), obs_row(2, disp="fixed@abc1234")],
                  defs=[def_row(1), def_row(2)], sib_blocked=[sib_row(2)], sib_debt=[],
                  events=[*run_events(), *prop_events(1, "proposed", sources=[obs_id(1)])])
        return {**kw, **over}

    def test_AT_IC_01_4_3_a_proposal_takes_its_most_severe_source(self):
        events = [*run_events(), *prop_events(1, "proposed",
                                              sources=[obs_id(1), obs_id(2), def999(1)])]
        repo = self.new(obs=[obs_row(1, sev="P3"), obs_row(2, sev="P2")],
                        defs=[def_row(1, sev="P0")], events=events)
        with card_ok():
            got = self.items_of(repo)
        self.assertEqual((got[pid(1)]["severity"], got[pid(1)]["severity_rank"]), ("緊急", 1))
        self.assertEqual(got[obs_id(1)]["severity"], "中")
        self.assertEqual((got[def999(1)]["severity"], got[def999(1)]["severity_rank"]), ("緊急", 1))

    def test_AT_IC_01_4_E_1_defect_severity_outside_the_constant_is_unmapped(self):
        cells = ["—（流程紀錄）", "P5", "P10"]
        obj = build_obj(self.new(defs=[def_row(n, sev=s) for n, s in enumerate(cells, start=1)]))
        got = by_id(obj)
        for n, raw in enumerate(cells, start=1):
            item = got[def999(n)]
            self.assertEqual((item["severity"], item["severity_rank"]), (f"未歸類：{raw}", None))
            self.assertIn((def999(n), "UNMAPPED", f"嚴重度：{raw}"), problems(obj))
        self.assertEqual(len(problems(obj, "UNMAPPED")), 3)

    def test_AT_IC_01_4_E_2_unknown_severity_shows_a_dash_not_low(self):
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(8), obs_id(9)])]
        with card_ok():
            obj = build_obj(self.new(events=events))
        item = by_id(obj)[pid(1)]
        self.assertEqual((item["severity"], item["severity_rank"]), (None, None))
        self.assertEqual(notes(obj), [(f"issues.{pid(1)}.severity", "SEVERITY-UNAVAILABLE")])

    def test_AT_IC_01_5_1_legend_content_counts_and_order(self):
        for kw in ({}, dict(obs=[], defs=[], sib_blocked=[], sib_debt=[], events=[])):
            legend = build_obj(self.new(**kw))["legend"]
            self.assertEqual(list(legend), ["statuses", "results", "sources", "severities",
                                            "problem_codes", "ne_reasons", "unmapped_label",
                                            "updated_at_note"])
            tabs = {"候選": None, "待您決定": "待您決定", "待解": "待處理", "進行中": "待處理",
                    "觀察中": "待處理", "延後": None, "已完成": "已完成"}
            got_tabs = [(s["name"], s["tab"]) for s in legend["statuses"]]
            self.assertEqual(got_tabs, list(tabs.items()))
            self.assertEqual([s["name"] for s in legend["statuses"] if s["rankable"]],
                             ["待您決定", "待解", "進行中"])
            self.assertEqual([r["name"] for r in legend["results"]],
                             ["已修復", "已採納", "已否決", "已退役", "已裁決", "已轉交", "已合併",
                              "已回滾"])
            self.assertEqual([s["name"] for s in legend["sources"]],
                             ["使用者提案", "系統缺陷", "研究提案", "系統改善"])
            self.assertEqual([(s["name"], s["rank"]) for s in legend["severities"]],
                             [("緊急", 1), ("高", 2), ("中", 3), ("低", 4)])
            self.assertEqual([c["code"] for c in legend["problem_codes"]],
                             ["ROW-ARITY", "ID-DUP", "UNMAPPED", "EVENT-PARSE", "EVENT-UNSOUND"])
            self.assertEqual(len(legend["ne_reasons"]), 9)
            for key in ("statuses", "results", "sources", "severities", "problem_codes",
                        "ne_reasons"):
                self.assertTrue(all(x["meaning"].strip() for x in legend[key]), key)
            self.assertEqual(legend["unmapped_label"], "未歸類")
            self.assertIn("最後已知動靜", legend["updated_at_note"])
            self.assertIn("游標", legend["problem_codes"][0]["meaning"])

    def test_AT_IC_01_7_1_every_code_and_reason_is_in_the_table_and_vice_versa(self):
        seen_codes, seen_reasons = set(), set()

        def harvest(obj):
            seen_codes.update(p["code"] for p in obj["problems"])
            seen_reasons.update(n["reason"] for n in obj["ne"])

        bad_arity = obs_row(1)[:8]
        obs = [bad_arity, obs_row(2), obs_row(2), obs_row(3, disp="later"),
               obs_row(4, time="昨天")]
        repo = self.new(obs=obs, defs=[def_row(1)], sib_blocked=[sib_row(9)],
                        events=[*run_events(), *prop_events(1, "proposed"),
                                *prop_events(2, "measuring")])
        with (repo / fx.EVL).open("ab") as fh:
            fh.write("這不是 JSON\n".encode() + b'{"kind": "run.open"}\n')
        with mock.patch.object(issues.si_status, "measure_value",
                               lambda *a: {"status": "NOT-EVALUABLE", "reason": "x"}):
            harvest(build_obj(repo))
        for kw in (dict(obs=None), dict(defs=None), dict(sib_blocked=None),
                   dict(events=None), dict(git=False)):
            harvest(build_obj(self.new(**kw)))
        repo = self.new(obs=[obs_row(1)])
        with mock.patch.dict(os.environ, {"PATH": ""}):  # PATH 無 git：head 取不到、其餘照常
            obj = build_obj(repo)
        self.assertIsNone(obj["head_sha"])
        self.assertEqual(notes(obj), [("head_sha", "git-unavailable")])
        self.assertEqual(obj["summary"]["total"], 1)
        harvest(obj)
        self.assertEqual(coverage_gap(seen_codes, im.PROBLEM_CODES), [])
        self.assertEqual(coverage_gap(seen_reasons, im.NE_REASONS), [])
        legend = im.labels()
        for key, names in (("problem_codes", "code"), ("ne_reasons", "reason")):
            self.assertTrue(all(x["meaning"].strip() for x in legend[key]), key)
            self.assertEqual(len({x[names] for x in legend[key]}), len(legend[key]))

    def test_AT_IC_01_7_E_1_the_closure_self_proof_has_teeth_in_both_directions(self):
        self.assertEqual(coverage_gap(im.PROBLEM_CODES, im.PROBLEM_CODES), [])
        missing_fixture = coverage_gap(set(im.NE_REASONS) - {"TIME-UNPARSEABLE"}, im.NE_REASONS)
        self.assertEqual(len(missing_fixture), 1)
        self.assertIn("TIME-UNPARSEABLE", missing_fixture[0])
        table_has_more = coverage_gap(im.PROBLEM_CODES, (*im.PROBLEM_CODES, "NEW-CODE"))
        self.assertTrue(table_has_more and "NEW-CODE" in table_has_more[0])
        output_has_more = coverage_gap({*im.PROBLEM_CODES, "FOO"}, im.PROBLEM_CODES)
        self.assertTrue(output_has_more and "FOO" in output_has_more[0])

    def test_AT_IC_01_8_1_missing_observation_ledger(self):
        with card_ok():
            base = build_obj(self.new(**self.full_kw()))
            repo = self.new(**self.full_kw(obs=None))
            obj = build_obj(repo)
            rc, out, err = self.cli(repo, "--json")
        self.assertEqual(notes(base), [])
        self.assertEqual(notes(obj), [("ledger.observation", "OBS-LEDGER-UNAVAILABLE")])
        self.assertEqual(rc, 0, err)
        self.assertEqual(set(by_id(base)) - set(by_id(obj)), {obs_id(1), obs_id(2)})
        self.assertEqual(obj["summary"]["by_tab"], dict.fromkeys(im.TABS))
        self.assertEqual(obj["summary"]["total"], len(obj["items"]))

    def test_AT_IC_01_8_2_missing_defect_ledger(self):
        with card_ok():
            obj = build_obj(self.new(**self.full_kw(defs=None)))
        self.assertEqual(notes(obj), [("ledger.defect", "DEFECT-LEDGER-UNAVAILABLE")])
        self.assertEqual(set(by_id(obj)), {obs_id(1), obs_id(2), pid(1)})
        tab = obj["summary"]["by_tab"]
        self.assertEqual((tab["待處理"], tab["已完成"]), (None, None))
        self.assertEqual(tab["待您決定"], 1)

    def test_AT_IC_01_8_3_missing_sibling_ledger(self):
        with card_ok():
            obj = build_obj(self.new(**self.full_kw(sib_debt=None)))
        name = "AutoSDD_Structural_Debt_Log.md"
        self.assertEqual(notes(obj), [(f"ledger.sibling.{name}", "SIBLING-LEDGER-UNAVAILABLE")])
        tab = obj["summary"]["by_tab"]
        self.assertEqual((tab["待處理"], tab["已完成"], tab["待您決定"]), (None, None, 1))
        self.assertIn(def999(1), by_id(obj))

    def test_AT_IC_01_8_4_missing_event_ledger(self):
        with card_ok():
            obj = build_obj(self.new(**self.full_kw(events=None)))
        self.assertEqual(notes(obj), [("ledger.events", "EVENT-LEDGER-UNAVAILABLE")])
        self.assertNotIn("carrier-not-established", [r for _, r in notes(obj)])
        self.assertEqual(set(by_id(obj)), {obs_id(1), obs_id(2), def999(1), def999(2)})
        self.assertEqual(obj["summary"]["by_tab"], dict.fromkeys(im.TABS))

    def test_AT_IC_01_8_E_1_unreadable_ledgers_report_exactly_their_own_reason(self):
        cases = (
            (fx.LEDGER, "ledger.observation", "OBS-LEDGER-UNAVAILABLE"),
            (fx.DEFLOG, "ledger.defect", "DEFECT-LEDGER-UNAVAILABLE"),
            (SIB_BLOCKED, "ledger.sibling.AutoSDD_External_Blocked_Log.md",
             "SIBLING-LEDGER-UNAVAILABLE"),
            (fx.EVL, "ledger.events", "EVENT-LEDGER-UNAVAILABLE"),
        )
        for rel, field, reason in cases:
            with self.subTest(rel), card_ok():
                repo = self.new(**self.full_kw())
                as_dir(repo, rel)
                rc, out, err = self.cli(repo, "--json")
                self.assertEqual(rc, 0, err)
                self.assertEqual(notes(json.loads(out)), [(field, reason)])
        with card_ok():
            repo = self.new(**self.full_kw(obs_archive=[obs_row(9, disp="fixed@abc1234")]))
            as_dir(repo, OBS_ARCHIVE)
            obj = build_obj(repo)
        name = "SelfImproving_Observation_Ledger_archive_01.md"
        self.assertEqual(notes(obj), [(f"ledger.observation.{name}", "OBS-LEDGER-UNAVAILABLE")])
        self.assertIn(obs_id(1), by_id(obj))
        self.assertNotIn(obs_id(9), by_id(obj))

    def test_AT_IC_01_8_E_2_ledgers_without_a_proper_header_are_unavailable_not_empty(self):
        repo = self.new(**self.full_kw(events=[]))
        fx.put(repo, fx.DEFLOG, "| 編號 | 備註 |\n|---|---|\n| " + def999(1) + " | x |\n")
        fx.put(repo, SIB_DEBT, "# 無表頭\n\n| 欄位 | 說明 |\n|---|---|\n| a | b |\n")
        obj = build_obj(repo)
        self.assertCountEqual(notes(obj), [
            ("ledger.defect", "DEFECT-LEDGER-UNAVAILABLE"),
            ("ledger.sibling.AutoSDD_Structural_Debt_Log.md", "SIBLING-LEDGER-UNAVAILABLE")])
        tab = obj["summary"]["by_tab"]
        self.assertEqual((tab["待處理"], tab["已完成"]), (None, None))
        self.assertIsNotNone(tab["待您決定"])
        self.assertNotIn(def999(1), by_id(obj))


def event_lines(repo, events, extra=()):
    """把 `events` 合成事件行，與 `extra`（`(插入位置, 原始行)`，位置 0 起算）交錯寫成事件帳本。"""
    lines = [fx.dumps_line(o) for o in fx.compose(events, fx.head(repo))]
    for pos, raw in sorted(extra):
        lines.insert(pos, raw)
    fx.put(repo, fx.EVL, "".join(ln + "\n" for ln in lines))


def attr_root(n, obs_ids, by="SA"):
    return fx.ev("attr", by, id=aid(n), type="root", obs=list(obs_ids),
                 items=[["DOC", f"{QUALITY}/"]], root_cause="docs/stale-note")


def attr_link(n, frm, reopens, by="SA"):
    return fx.ev("attr", by, id=aid(n), type="link", **{"from": frm}, reopens=reopens)


def confirm(n, by="QA"):
    return fx.ev("attr.confirm", by, att=aid(n))


def reject(n):
    return fx.ev("attr.reject", "QA", att=aid(n), note="夾具駁回")


class TestEventLedgerAndLinkage(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的事件帳本結構問題與帳本缺檔連帶規則
    （AC-IC-01-9、01-11）。"""

    def test_AT_IC_01_9_1_unparseable_and_unsound_lines_are_reported_by_line(self):
        repo = self.new(obs=[obs_row(1)], events=None)
        event_lines(repo, [*run_events(), *prop_events(1, "proposed")],
                    extra=[(2, "這不是 JSON"), (4, '{"kind": "run.open", "by": "main"}')])
        with card_ok():
            rc, out, err = self.cli(repo, "--json")
        obj = json.loads(out)
        self.assertEqual(rc, 0, err)
        self.assertEqual([(s, c) for s, c, _ in problems(obj)],
                         [("L3", "EVENT-PARSE"), ("L5", "EVENT-UNSOUND")])
        self.assertEqual(by_id(obj)[pid(1)]["status"], "待您決定")

    def test_AT_IC_01_9_E_1_unsound_events_never_reach_the_fold(self):
        broken = {"seq": 4, "t": "2026-10-18T10:00:00+08:00", "kind": "dec", "by": "掌舵者",
                  "id": "DEC-SI-004", "dkind": "approve", "prop": pid(1)}
        repo = self.new(obs=[obs_row(1)], events=None)
        event_lines(repo, [*run_events(), *prop_events(1, "proposed")],
                    extra=[(2, fx.dumps_line(broken)), (3, ""), (4, fx.dumps_line(broken))])
        with card_ok():
            obj = build_obj(repo)
        self.assertEqual([(s, c) for s, c, _ in problems(obj)],
                         [("L3", "EVENT-UNSOUND"), ("L4", "EVENT-PARSE"), ("L5", "EVENT-UNSOUND")])
        self.assertEqual(by_id(obj)[pid(1)]["status"], "待您決定")  # approve 若被折疊就是進行中

    def test_AT_IC_01_11_1_missing_observation_ledger_blanks_the_proposal_source(self):
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(1), obs_id(2)])]
        with card_ok():
            obj = build_obj(self.new(obs=None, events=events))
        item = by_id(obj)[pid(1)]
        blanks = (item["source"], item["severity"], item["severity_rank"])
        self.assertEqual(blanks, (None, None, None))
        self.assertEqual(notes(obj), [("ledger.observation", "OBS-LEDGER-UNAVAILABLE")])
        self.assertEqual(problems(obj), [])

    def test_AT_IC_01_11_2_missing_event_ledger_keeps_unconfirmed_rows_as_candidates(self):
        repo = self.new(obs=[obs_row(1)], events=None)
        obj = build_obj(repo)
        self.assertEqual(by_id(obj)[obs_id(1)]["status"], "候選")
        self.assertEqual(notes(obj), [("ledger.events", "EVENT-LEDGER-UNAVAILABLE")])

    def test_AT_IC_01_11_E_1_unaffected_rows_are_judged_as_usual(self):
        events = [*run_events(), *prop_events(1, "proposed", sources=[def999(1)])]
        with card_ok():
            got = by_id(build_obj(self.new(obs=None, defs=[def_row(1, sev="P1")], events=events)))
        self.assertEqual((got[pid(1)]["source"], got[pid(1)]["severity"]), ("系統缺陷", "緊急"))
        obs = [obs_row(1, cat="decision"), obs_row(2, cat="process", marks=USER_MARKS)]
        got = by_id(build_obj(self.new(obs=obs, events=None)))
        self.assertEqual((got[obs_id(1)]["status"], got[obs_id(2)]["status"]), ("待您決定", "待解"))


class TestSourceJudgement(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的四來源判定與順位（AC-IC-02-1～02-5）。"""

    RESEARCH = "面=產品;來源=工具;回報者=研究者;外部衍生=是;src=demo-src"

    def source_of(self, **row):
        got = self.items_of(self.new(obs=[obs_row(1, **row)]))
        return got[obs_id(1)]["source"]

    def test_AT_IC_02_1_1_user_marks_win_over_everything(self):
        console = f"面=流程;來源=代理;回報者=主控;carrier=console;audit_ref={fx.UUID}"
        self.assertEqual(self.source_of(marks=console), "使用者提案")
        self.assertEqual(self.source_of(marks="面=流程;來源=人;回報者=掌舵者"), "使用者提案")

    def test_AT_IC_02_1_E_1_agent_marks_alone_are_not_the_user(self):
        self.assertEqual(self.source_of(marks="面=產品;來源=代理;回報者=QA"), "系統缺陷")

    def test_AT_IC_02_2_1_researcher_reports_are_research_proposals(self):
        self.assertEqual(self.source_of(cat="tooling", marks=self.RESEARCH), "研究提案")

    def test_AT_IC_02_2_E_1_a_researcher_bug_is_still_a_system_defect(self):
        self.assertEqual(self.source_of(cat="bug", marks=self.RESEARCH), "系統缺陷")

    def test_AT_IC_02_2_E_2_the_researcher_test_is_equality_not_substring(self):
        marks = "面=文件;來源=代理;回報者=研究員"
        self.assertEqual(self.source_of(cat="doc", marks=marks), "系統改善")

    def test_AT_IC_02_3_1_defect_rows_and_bug_observations_are_system_defects(self):
        got = self.items_of(self.new(obs=[obs_row(1, cat="bug"),
                                          obs_row(2, cat="bug", marks=self.RESEARCH)],
                                     defs=[def_row(1, status="fixed@abc1234")]))
        sources = {got[i]["source"] for i in (obs_id(1), obs_id(2), def999(1))}
        self.assertEqual(sources, {"系統缺陷"})

    def test_AT_IC_02_3_E_1_a_tooling_observation_is_not_a_defect(self):
        self.assertEqual(self.source_of(cat="tooling"), "系統改善")

    def test_AT_IC_02_4_1_improvement_categories_are_system_improvements(self):
        cats = ("process", "tooling", "doc", "decision")
        got = self.items_of(self.new(obs=[obs_row(n, cat=c) for n, c in enumerate(cats, start=1)]))
        self.assertEqual({got[obs_id(n)]["source"] for n in range(1, 5)}, {"系統改善"})

    def test_AT_IC_02_4_E_1_a_bug_is_not_an_improvement(self):
        self.assertNotEqual(self.source_of(cat="bug"), "系統改善")

    def test_AT_IC_02_5_1_a_proposal_takes_the_first_ranked_source(self):
        obs = [obs_row(1, marks=USER_MARKS), obs_row(2, cat="doc", marks=self.RESEARCH)]
        events = [*run_events(), *prop_events(1, "proposed", sources=[def999(1), obs_id(1)]),
                  *prop_events(2, "proposed", sources=[obs_id(2), def999(2)])]
        with card_ok():
            got = self.items_of(self.new(obs=obs, defs=[def_row(1), def_row(2)], events=events))
        self.assertEqual((got[pid(1)]["source"], got[pid(2)]["source"]), ("使用者提案", "系統缺陷"))

    def test_AT_IC_02_5_E_1_unknown_sources_are_skipped_or_reported_by_id(self):
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(8), obs_id(1)]),
                  *prop_events(2, "proposed", sources=[obs_id(8), obs_id(9)])]
        with card_ok():
            obj = build_obj(self.new(obs=[obs_row(1, cat="doc")], events=events))
        got = by_id(obj)
        self.assertEqual(got[pid(1)]["source"], "系統改善")
        self.assertEqual(got[pid(2)]["source"], f"未歸類：{obs_id(8)}、{obs_id(9)}")
        self.assertEqual(problems(obj, "UNMAPPED"),
                         [(pid(2), "UNMAPPED", f"來源：{obs_id(8)}、{obs_id(9)}")])


USER_MARKS = "面=流程;來源=人;回報者=掌舵者"


class TestFormalIssues(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的「成為正式議題」規則與待您決定的成員
    （AC-IC-03-1～03-7）。"""

    def test_AT_IC_03_1_1_an_unsupported_open_row_stays_a_candidate(self):
        repo = self.new(obs=[obs_row(1)])
        item = by_id(build_obj(repo))[obs_id(1)]
        self.assertEqual((item["status"], item["rankable"]), ("候選", False))
        for flt in ("待處理", "待您決定"):
            self.assertEqual(build_obj(repo, statuses=[flt])["items"], [], flt)

    def test_AT_IC_03_1_E_1_candidates_are_outside_every_tab(self):
        summary = build_obj(self.new(obs=[obs_row(1)]))["summary"]
        self.assertEqual(summary["by_status"]["候選"], 1)
        self.assertEqual(summary["by_tab"], {"待處理": 0, "待您決定": 0, "已完成": 0})

    def test_AT_IC_03_2_1_a_confirmed_attr_makes_the_row_established(self):
        events = [*run_events(), attr_root(1, [obs_id(1)]), confirm(1),
                  attr_link(2, obs_id(2), obs_id(1)), confirm(2)]
        got = self.items_of(self.new(obs=[obs_row(1), obs_row(2)], events=events))
        self.assertEqual([got[obs_id(1)]["status"], got[obs_id(2)]["status"]], ["待解", "待解"])

    def test_AT_IC_03_2_E_1_unconfirmed_or_rejected_attrs_do_not_count(self):
        events = [*run_events(), attr_root(1, [obs_id(1)]), attr_root(2, [obs_id(2)]), reject(2),
                  attr_root(3, [obs_id(3)]), confirm(3, by="SA")]  # 確認者等於提出者
        got = self.items_of(self.new(obs=[obs_row(n) for n in (1, 2, 3)], events=events))
        self.assertEqual([got[obs_id(n)]["status"] for n in (1, 2, 3)], ["候選", "候選", "待解"])

    def test_AT_IC_03_3_1_a_user_mark_is_enough_without_any_attr(self):
        marks = f"面=產品;來源=代理;回報者=主控;carrier=console;audit_ref={fx.UUID}"
        obs = [obs_row(1, cat="process", marks=USER_MARKS), obs_row(2, cat="process", marks=marks)]
        got = self.items_of(self.new(obs=obs))
        self.assertEqual([got[obs_id(1)]["status"], got[obs_id(2)]["status"]], ["待解", "待解"])

    def test_AT_IC_03_3_2_decision_rows_go_to_the_decision_tab_on_either_path(self):
        obs = [obs_row(1, cat="decision"), obs_row(2, cat="decision", marks=USER_MARKS)]
        got = self.items_of(self.new(obs=obs))
        for n in (1, 2):
            item = got[obs_id(n)]
            self.assertEqual((item["status"], item["action"], item["rankable"]),
                             ("待您決定", "close-observation", True), n)

    def test_AT_IC_03_3_E_1_looking_like_an_improvement_does_not_establish_a_row(self):
        got = self.items_of(self.new(obs=[obs_row(1, cat="process")]))
        self.assertEqual(got[obs_id(1)]["status"], "候選")

    def test_AT_IC_03_4_1_final_and_deferred_rows_are_never_candidates(self):
        obs = [obs_row(1, disp="fixed@abc1234"), obs_row(2, disp="decided：裁決"),
               obs_row(3, disp="retired；依據 tools/notes/x.md:3"),
               obs_row(4, disp="merged@" + obs_id(1)), obs_row(5, disp=def999(1)),
               obs_row(6, disp="proposed@" + pid(1)), obs_row(7, disp="deferred；再開症狀：再發")]
        events = [*run_events(), *prop_events(1, "proposed")]
        with card_ok():
            got = self.items_of(self.new(obs=obs, defs=[def_row(1)], events=events))
        self.assertNotIn("候選", {got[obs_id(n)]["status"] for n in range(1, 8)})
        self.assertEqual((got[def999(1)]["status"], got[pid(1)]["status"]), ("待解", "待您決定"))

    def test_AT_IC_03_4_E_1_an_established_deferred_row_stays_deferred(self):
        events = [*run_events(), attr_root(1, [obs_id(1)]), confirm(1)]
        row = obs_row(1, disp="deferred；再開症狀：再發", marks=USER_MARKS)
        got = self.items_of(self.new(obs=[row], events=events))
        self.assertEqual(got[obs_id(1)]["status"], "延後")

    def test_AT_IC_03_5_1_unbooked_console_audit_files_are_not_issues(self):
        audit = self.home / "console_audit"
        audit.mkdir()
        body = json.dumps({"kind": "obs-add", "audit_ref": fx.UUID})
        (audit / f"{fx.UUID}.json").write_text(body, encoding="utf-8")
        repo = self.new(obs=[obs_row(1)])
        env = {"HOME": str(self.home), "USERPROFILE": str(self.home)}
        with mock.patch.dict(os.environ, env), mock.patch.object(
                Path, "home", side_effect=AssertionError("不得讀家目錄")):
            rc, out, err = self.cli(repo, "--json")
            rc2, out2, err2 = self.M(repo, "export", "--json", "--kind", "issues")
        self.assertEqual((rc, rc2), (0, 0), err + err2)
        for text in (out, out2):
            self.assertEqual([i["id"] for i in json.loads(text)["items"]], [obs_id(1)])
        self.assertEqual([p.name for p in audit.iterdir()], [f"{fx.UUID}.json"])

    def test_AT_IC_03_5_E_1_the_row_becomes_an_issue_only_once_it_is_booked(self):
        marks = f"面=產品;來源=人;回報者=掌舵者;carrier=console;audit_ref={fx.UUID}"
        before = self.items_of(self.new(obs=[obs_row(1)]))
        after = self.items_of(self.new(obs=[obs_row(1), obs_row(2, cat="process", marks=marks)]))
        self.assertEqual(set(after) - set(before), {obs_id(2)})
        booked = after[obs_id(2)]
        self.assertEqual((booked["source"], booked["status"]), ("使用者提案", "待解"))
        self.assertEqual(before[obs_id(1)]["status"], after[obs_id(1)]["status"])

    def test_AT_IC_03_6_1_established_improvements_go_to_pending_not_to_decision(self):
        obs = [obs_row(1, cat="process"), obs_row(2, cat="tooling", marks=USER_MARKS),
               obs_row(3, cat="doc")]
        events = [*run_events(), attr_root(1, [obs_id(1), obs_id(3)]), confirm(1)]
        repo = self.new(obs=obs, events=events)
        got = self.items_of(repo)
        for n in (1, 2, 3):
            item = got[obs_id(n)]
            self.assertEqual((item["status"], item["action"]), ("待解", None), n)
        self.assertEqual(build_obj(repo, statuses=["待您決定"])["items"], [])

    def all_status_repo(self) -> Path:
        obs = [obs_row(1), obs_row(2, cat="decision"), obs_row(3, cat="process", marks=USER_MARKS),
               obs_row(4, disp="deferred；再開症狀：再發"), obs_row(5, disp="fixed@abc1234")]
        events = [*run_events(), fx.prop_ev(1, 1), *prop_events(2, "verified"), fx.prop_ev(3, 1),
                  *closed_steps(3, "recurred"), *prop_events(4, "approved"),
                  *prop_events(5, "measuring"), fx.prop_ev(6, 1), *closed_steps(6, "clean")]
        return self.new(obs=obs, defs=[def_row(1), def_row(2, status="routed")], events=events)

    def test_AT_IC_03_6_E_1_the_decision_tab_has_exactly_four_kinds_of_members(self):
        with card_ok():
            got = self.items_of(self.all_status_repo())
        members = {i for i, item in got.items() if item["status"] == "待您決定"}
        self.assertEqual(members, {obs_id(2), pid(1), pid(2), pid(3)})
        rest = (pid(4), pid(5), pid(6), def999(2), obs_id(1))
        self.assertEqual({i: got[i]["status"] for i in rest},
                         {pid(4): "進行中", pid(5): "觀察中", pid(6): "已完成", def999(2): "進行中",
                          obs_id(1): "候選"})

    def test_AT_IC_03_7_1_closed_proposals_follow_the_rollback_ledger(self):
        events = [*run_events(), fx.prop_ev(1, 1), *closed_steps(1, "recurred"),
                  fx.prop_ev(2, 1), *closed_steps(2, "clean"), fx.dec_ev(2, "rollback"),
                  fx.prop_ev(3, 1), *closed_steps(3, "recurred"), fx.dec_ev(3, "rollback"),
                  fx.prop_ev(4, 1), *closed_steps(4, "recurred"), fx.dec_ev(4, "rollback"),
                  fx.rollback_ev(4), fx.prop_ev(5, 1), *closed_steps(5, "clean"),
                  fx.prop_ev(6, 1), *promoted_steps(6), fx.dec_ev(6, "rollback"),
                  *prop_events(7, "measuring"), fx.dec_ev(7, "rollback")]
        with card_ok():
            got = self.items_of(self.new(obs=[obs_row(1)], events=events))
        self.assertEqual((got[pid(1)]["status"], got[pid(1)]["rankable"]), ("待您決定", True))
        self.assertEqual(got[pid(1)]["next_step"],
                         "量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞）")
        self.assertEqual(got[pid(1)]["action"], "decide-proposal")
        for n in (2, 3, 6, 7):
            self.assertEqual(got[pid(n)]["status"], "進行中", n)
            self.assertEqual(got[pid(n)]["next_step"], "已決定回滾，等執行回滾", n)
        self.assertEqual((got[pid(4)]["status"], got[pid(4)]["result"]), ("已完成", "已回滾"))
        self.assertEqual((got[pid(5)]["status"], got[pid(5)]["result"]), ("已完成", "已採納"))

    def rollback_repo(self) -> Path:
        events = [*run_events(), fx.prop_ev(1, 1), *closed_steps(1, "recurred"),
                  fx.prop_ev(2, 1), *closed_steps(2, "recurred"), fx.dec_ev(2, "rollback"),
                  fx.prop_ev(3, 1), *closed_steps(3, "clean"), fx.prop_ev(4, 1),
                  *closed_steps(4, "recurred"), fx.prop_ev(5, 1), *closed_steps(5, "rolled-back")]
        return self.new(obs=[obs_row(1)], events=events)

    def test_AT_IC_03_7_2_the_decision_members_match_meaplan_rollback_pending(self):
        repo = self.rollback_repo()
        events = si_events.load_sound_events(repo / si_events.LEDGER_REL)
        params = si_check.params_for(repo, "export_limit_max")
        ctx = si_mea.build_ctx(repo, Git(repo), params, events)
        want = set(si_meaplan.rollback_pending(ctx))
        self.assertEqual(want, {pid(1), pid(4)})
        with card_ok():
            got = self.items_of(repo)
        closed = {i for i, p in si_fold.fold(events).props.items() if p.state == "closed"}
        deciding = {i for i, x in got.items() if x["status"] == "待您決定" and i in closed}
        self.assertEqual(deciding, want)

    def test_AT_IC_03_7_E_1_a_rollback_decided_before_the_promotion_is_not_counted(self):
        events = [*run_events(), fx.prop_ev(1, 1), fx.dec_ev(1, "rollback"),
                  *closed_steps(1, "recurred")]
        repo = self.new(obs=[obs_row(1)], events=events)
        loaded = si_events.load_sound_events(repo / si_events.LEDGER_REL)
        self.assertIn("TRANSITION-ILLEGAL", {c for c, _, _ in si_fold.fold(loaded).problems})
        with card_ok():
            self.assertEqual(self.items_of(repo)[pid(1)]["status"], "待您決定")
        params = si_check.params_for(repo, "export_limit_max")
        ctx = si_mea.build_ctx(repo, Git(repo), params, loaded)
        self.assertEqual(si_meaplan.rollback_pending(ctx), [])  # 不判事件合法性，與議題中心刻意不同


def measure_as(result):
    """注入縫 S5：`status.measure_value` 回給定結果。"""
    return mock.patch.object(issues.si_status, "measure_value", lambda *a: result)


def s_read(prop_id, n_opp):
    return {"status": "read", "windows": [{"prop": prop_id, "state": "measuring",
                                           "result": None, "n_opp": n_opp}]}


def line_of(repo, rel, ident) -> int:
    """帳本檔內以 `| <ident> |` 起頭的那一行的 1 起算行號（獨立於被測碼的算法）。"""
    lines = fx.read(repo, rel).replace("\r\n", "\n").split("\n")
    return next(i for i, ln in enumerate(lines, start=1) if ln.startswith(f"| {ident} |"))


class TestNextStepAndFields(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的下一步句型、標題、最後更新日與 rankable、action
    （AC-IC-04-1～04-3、04-10）。"""

    NEXT = {
        obs_id(1): "等歸因確認（歸因者提出、審查者確認），或由掌舵者簽核成立",
        obs_id(2): "等掌舵者決定：在此關閉並寫下裁決",
        obs_id(3): "已成立，尚無人接手",
        obs_id(4): "等再開症狀出現：第二次出現同一症狀",
        obs_id(5): "已結案（已修復）",
        obs_id(6): "已結案（已轉交），見 " + def999(1),
        def999(1): "尚未分流，等待修復",
        def999(2): "已分流待修",
        def999(3): "等解鎖條件：等外部帳務重置後再看（最近複查 2026-10-20）",
        def999(4): "已結案（已修復）",
        pid(1): "等掌舵者決定：核准、否決或退回",
        pid(2): "等掌舵者決定：轉交、不轉交或退回（通道：掌舵者指令）",
        pid(3): "驗證已有結果，等掌舵者決定（可選的決定依驗證結果而定，見「決定」對話框）",
        pid(4): "量測窗內復發，等您決定是否回滾（目前只有「回滾」動詞）",
        pid(5): "已核准，等沙盒套用",
        pid(6): "已退回，等提案者修訂（第 1 版）",
        pid(7): "沙盒已套用，等驗證",
        pid(8): "已決定回滾，等執行回滾",
        pid(9): "已晉升，等量測窗開啟",
        pid(10): "量測窗 0／5",
        pid(11): "已結案（已轉交），通道：掌舵者指令",
        pid(12): "已結案（已否決）；同型冷卻中",
        pid(13): "已結案（已否決）；冷卻已解除",
        pid(14): "已結案（已採納）",
        pid(15): "帳本值不在對照表內，請查原列",
    }

    def next_step_repo(self) -> Path:
        """PRD §5.2 十九情境的夾具（TCS §5.3 的 N01～N19；N19 由注入縫 S1 構造）。"""
        obs = [obs_row(1), obs_row(2, cat="decision"), obs_row(3, cat="process", marks=USER_MARKS),
               obs_row(4, disp="deferred；再開症狀：第二次出現同一症狀"),
               obs_row(5, disp="fixed@abc1234"), obs_row(6, disp=def999(1))]
        defs = [def_row(1), def_row(2, status="routed"), def_row(3),
                def_row(4, status="fixed@abc1234")]
        events = [*run_events(), fx.prop_ev(1, 1), fx.prop_ev(2, 1, route="handoff:T1"),
                  *prop_events(3, "verified"), fx.prop_ev(4, 1), *closed_steps(4, "recurred"),
                  *prop_events(5, "approved"), *prop_events(6, "returned"),
                  *prop_events(7, "sandboxed"), fx.prop_ev(8, 1), *promoted_steps(8),
                  fx.dec_ev(8, "rollback"), fx.prop_ev(9, 1), *promoted_steps(9),
                  *prop_events(10, "measuring"), fx.prop_ev(11, 1, route="handoff:T1"),
                  fx.dec_ev(11, "ack-handoff"), *prop_events(12, "rejected"),
                  *prop_events(13, "rejected"), fx.dec_ev(13, "unblock"), fx.prop_ev(14, 1),
                  *closed_steps(14, "clean"), fx.prop_ev(15, 1)]
        blocked = [sib_row(3, unlock="等外部帳務重置後再看", review="2026-10-20")]
        return self.new(obs=obs, defs=defs, events=events, sib_blocked=blocked)

    def stubbed(self, repo, **kw) -> dict:
        """帶三個注入縫（卡面成功、量測窗 0／5、N19 的 zombie）建整本帳。"""
        with card_ok(), measure_as(s_read(pid(10), 0)), zombie(pid(15)):
            return build_obj(repo, limit=500, **kw)

    def test_AT_IC_04_1_1_every_scenario_has_exactly_its_sentence(self):
        obj = self.stubbed(self.next_step_repo())
        got = by_id(obj)
        for ident, want in self.NEXT.items():
            step = got[ident]["next_step"]
            self.assertEqual(step, want, ident)
            self.assertTrue(step and len(step) <= 80, (ident, len(step)))
            self.assertEqual(english_hits(step), [], (ident, step))
        self.assertNotIn("通過", got[pid(3)]["next_step"])  # verified 句型不預設驗證結果
        self.assertEqual(sorted(got), sorted(self.NEXT))

    def test_AT_IC_04_1_E_1_the_english_word_detector_has_teeth(self):
        for word in ("open", "fixed@abc", "measuring", "closed-by-decision", "handed-off"):
            self.assertEqual(english_hits(f"狀態 {word} 之後"), [word.split("@")[0]], word)
        for clean in ("PROP-SI-004", "DEF-999-001", "通道：掌舵者指令", "等歸因確認"):
            self.assertEqual(english_hits(clean), [], clean)
        self.assertEqual(english_hits("closed-by-decision"), ["closed-by-decision"])  # 不算 closed

    def test_AT_IC_04_1_E_2_deferred_excerpts_are_cut_at_forty_and_may_be_empty(self):
        long_en = "open again after the symptom shows up twice in the nightly CI logs"
        obs = [obs_row(1, disp=f"deferred；再開症狀：{long_en}"), obs_row(2, disp="deferred"),
               obs_row(3, disp="deferred；再開症狀：")]
        got = self.items_of(self.new(obs=obs))
        self.assertEqual(got[obs_id(1)]["next_step"], "等再開症狀出現：" + long_en[:40])
        self.assertEqual(len(long_en[:40]), 40)
        for n in (2, 3):
            self.assertEqual(got[obs_id(n)]["next_step"], "等再開症狀出現：（帳本未寫明）", n)
        for item in got.values():
            self.assertEqual(english_hits(item["next_step"].split("：", 1)[0]), [])

    def test_AT_IC_04_2_1_a_measuring_proposal_shows_the_window_progress(self):
        repo = f3.p3_base()
        prop = f3.promoted(repo)
        f3.mea_chain(repo, prop, "recurred", stop_at="open")
        self.assertEqual(si_fold.fold(si_events.load_sound_events(repo / fx.EVL)).props[prop].state,
                         "measuring")
        with card_ok():
            real = by_id(build_obj(repo))[prop]
        self.assertEqual((real["status"], real["next_step"]), ("觀察中", "量測窗 0／5"))
        with card_ok(), measure_as(s_read(prop, 3)):
            self.assertEqual(by_id(build_obj(repo))[prop]["next_step"], "量測窗 3／5")

    def test_AT_IC_04_2_E_1_unmeasurable_progress_is_a_dash_with_a_note(self):
        events = [*run_events(), *prop_events(1, "measuring")]
        repo = self.new(obs=[obs_row(1)], events=events)
        invalid = {"status": "NOT-EVALUABLE", "reason": "params-invalid"}
        for label, result in (("NOT-EVALUABLE", invalid), ("查無該窗", s_read(pid(9), 0))):
            with self.subTest(label), card_ok(), measure_as(result):
                obj = build_obj(repo)
            self.assertEqual(by_id(obj)[pid(1)]["next_step"], "量測窗進度量不到")
            self.assertEqual(notes(obj), [(f"issues.{pid(1)}.next_step", "MEASURE-UNAVAILABLE")])
            self.assertNotIn("0／5", by_id(obj)[pid(1)]["next_step"])

    def test_AT_IC_04_2_E_2_the_aggregator_never_calls_the_window_row_helper(self):
        import ast

        for name in ("issues.py", "issues_items.py"):
            text = (PKG / name).read_text(encoding="utf-8")
            lines = enumerate(text.splitlines(), start=1)
            literal = [no for no, ln in lines if "window_rows" in ln]
            self.assertEqual(literal, [], name)  # 字面逐行判定（不拿整份原始碼當 haystack）
            names = {n.id for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Name)}
            attrs = {n.attr for n in ast.walk(ast.parse(text)) if isinstance(n, ast.Attribute)}
            self.assertFalse({"window_rows"} & (names | attrs), name)

    def test_AT_IC_04_3_1_titles_lose_markup_and_are_cut_at_eighty_code_points(self):
        raw = ("**粗**__底__~~刪~~`碼` 內容\t多  空白 <script>x</script> a \\| b "
               + "字" * 30 + "😀" * 40)
        repo = self.new(obs=[obs_row(1, symptom=raw), obs_row(2, symptom="短 `標題`")])
        obj = build_obj(repo, ident=obs_id(1))
        plain = " ".join(raw.replace("**", "").replace("__", "").replace("~~", "")
                         .replace("`", "").replace("\\|", "|").split())
        self.assertEqual(len(plain) > 80, True)
        item = obj["items"][0]
        self.assertEqual(item["title"], plain[:80] + "…")
        self.assertIn("<script>", item["title"])
        self.assertNotEqual(item["title"][-2], "\ud83d")
        self.assertEqual(json.loads(json.dumps(item["title"])), item["title"])
        symptom = next(r["value"] for r in item["raw"] if r["label"] == "症狀")
        self.assertEqual(symptom, raw.replace("\\|", "|"))  # 原文逐字在單筆的 raw
        self.assertEqual(by_id(build_obj(repo))[obs_id(2)]["title"], "短 標題")

    def test_AT_IC_04_3_2_updated_at_takes_the_date_part_of_the_last_known_sign(self):
        obs = [obs_row(1, time="2026-10-18 22:47～10-19 02:20"),
               obs_row(2, time="2026-10-18 10:00 +08:00"),
               obs_row(3, time="2026-10-18 23:30 +08:00")]
        events = [*run_events(), fx.prop_ev(1, 1, t="2026-10-18T23:30:00+08:00"),
                  fx.obs_close_ev(obs=obs_id(2), t="2026-10-20T09:00:00+08:00")]
        with card_ok():
            got = self.items_of(self.new(obs=obs, defs=[def_row(1, date="2026-10-17")],
                                         events=events))
        self.assertEqual([got[obs_id(n)]["updated_at"] for n in (1, 2, 3)],
                         ["2026-10-18", "2026-10-20", "2026-10-18"])
        self.assertEqual(got[def999(1)]["updated_at"], "2026-10-17")
        self.assertEqual(got[pid(1)]["updated_at"], "2026-10-18")

    def test_AT_IC_04_3_E_1_unparseable_times_are_null_and_an_early_close_never_wins(self):
        obs = [obs_row(1, time="昨天"), obs_row(2, time="2026-10-18 10:00 +08:00")]
        events = [fx.obs_close_ev(obs=obs_id(2), t="2026-10-10T09:00:00+08:00")]
        obj = build_obj(self.new(obs=obs, events=events))
        got = by_id(obj)
        self.assertIsNone(got[obs_id(1)]["updated_at"])
        self.assertEqual(notes(obj), [(f"issues.{obs_id(1)}.updated_at", "TIME-UNPARSEABLE")])
        self.assertEqual(got[obs_id(2)]["updated_at"], "2026-10-18")

    def test_AT_IC_04_10_1_only_actionable_states_are_rankable_and_carry_an_action(self):
        got = by_id(self.stubbed(self.next_step_repo()))
        self.assertEqual({i["status"] for i in got.values() if not im.is_unmapped(i["status"])},
                         set(im.STATUSES))
        for ident, item in got.items():
            actionable = item["status"] in ("待您決定", "待解", "進行中")
            self.assertEqual(item["rankable"], actionable, ident)
            want = None
            if item["status"] == "待您決定":
                want = "decide-proposal" if ident.startswith("PROP") else "close-observation"
            self.assertEqual(item["action"], want, ident)
        asked = got[pid(4)]
        self.assertEqual((asked["status"], asked["action"]), ("待您決定", "decide-proposal"))
        self.assertEqual(got[obs_id(2)]["action"], "close-observation")

    def test_AT_IC_04_10_E_1_the_rest_are_neither_rankable_nor_actionable(self):
        got = by_id(self.stubbed(self.next_step_repo()))
        quiet = [i for i in got.values() if i["status"] in ("觀察中", "延後", "候選", "已完成")
                 or im.is_unmapped(i["status"])]
        self.assertTrue(any(im.is_unmapped(i["status"]) for i in quiet))
        self.assertGreaterEqual(len(quiet), 12)
        for item in quiet:
            self.assertEqual((item["rankable"], item["action"]), (False, None), item["id"])


def to_crlf_bom(repo, *rels) -> None:
    """把帳本檔改寫成 Windows 形態：CRLF 行尾並前置 UTF-8 BOM。"""
    for rel in rels:
        text = (repo / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
        (repo / rel).write_bytes(b"\xef\xbb\xbf" + text.replace("\n", "\r\n").encode("utf-8"))


def stable(obj) -> dict:
    """去掉唯一隨時間變動的 `generated_at`。"""
    return {k: v for k, v in obj.items() if k != "generated_at"}


class TestLinksOriginAndRows(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的關聯、延後與孤列、卡面、來源座標與壞列
    （AC-IC-04-4～04-9）。"""

    def test_AT_IC_04_4_1_two_way_links_list_each_other_sorted_and_deduplicated(self):
        obs = [obs_row(1, disp="merged@" + obs_id(2)), obs_row(2), obs_row(3, disp=def999(1)),
               obs_row(4, disp="proposed@" + pid(1))]
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(2), obs_id(2)])]
        with card_ok():
            got = self.items_of(self.new(obs=obs, defs=[def_row(1)], events=events))
        self.assertEqual(got[obs_id(1)]["links"], [obs_id(2)])
        self.assertEqual(got[obs_id(2)]["links"], sorted([obs_id(1), pid(1)]))
        self.assertEqual(got[obs_id(3)]["links"], [def999(1)])
        self.assertEqual(got[def999(1)]["links"], [obs_id(3)])
        self.assertEqual(got[obs_id(4)]["links"], [pid(1)])
        self.assertEqual(got[pid(1)]["links"], sorted([obs_id(2), obs_id(4)]))

    def test_AT_IC_04_4_2_one_way_links_only_list_the_target_from_the_origin(self):
        obs = [obs_row(1, marks=f"{MARKS};rel=corrects:{obs_id(2)}"), obs_row(2),
               obs_row(3, marks=f"{MARKS};rel=recurs:{obs_id(2)}"), obs_row(4),
               obs_row(5, marks=f"{MARKS};reopens={obs_id(2)}")]
        events = [*run_events(), attr_link(1, obs_id(4), obs_id(2))]
        got = self.items_of(self.new(obs=obs, events=events))
        for n in (1, 3, 4, 5):
            self.assertEqual(got[obs_id(n)]["links"], [obs_id(2)], n)
        self.assertEqual(got[obs_id(2)]["links"], [])

    def test_AT_IC_04_4_E_1_links_may_point_outside_and_two_way_ones_are_symmetric(self):
        obs = [obs_row(1, disp=def999(77)), obs_row(2, disp=def999(1)),
               obs_row(3, disp="merged@" + obs_id(4)), obs_row(4),
               obs_row(5, marks=f"{MARKS};rel=corrects:{obs_id(4)}")]
        got = self.items_of(self.new(obs=obs, defs=[def_row(1)]))
        self.assertEqual(got[obs_id(1)]["links"], [def999(77)])  # 主檔以外的 DEF 仍列入
        for a, b in ((obs_id(2), def999(1)), (obs_id(3), obs_id(4))):
            self.assertEqual((a in got[b]["links"], b in got[a]["links"]), (True, True), (a, b))
        self.assertIn(obs_id(4), got[obs_id(5)]["links"])
        self.assertNotIn(obs_id(5), got[obs_id(4)]["links"])  # 單向類不對稱

    def test_AT_IC_04_5_1_deferred_rows_say_what_would_bring_them_back(self):
        obs = [obs_row(1, disp="deferred；再開症狀：第三次出現")]
        blocked = [sib_row(1, "等上游修好", "2026-10-20")]
        repo = self.new(obs=obs, defs=[def_row(1)], sib_blocked=blocked)
        got = self.items_of(repo)
        self.assertEqual(got[obs_id(1)]["status"], "延後")
        self.assertIn("第三次出現", got[obs_id(1)]["next_step"])
        self.assertEqual(got[def999(1)]["status"], "延後")
        self.assertIn("等上游修好", got[def999(1)]["next_step"])
        self.assertTrue(got[def999(1)]["next_step"].endswith("（最近複查 2026-10-20）"))

    def test_AT_IC_04_5_E_1_a_sibling_row_without_a_main_row_is_an_orphan_issue(self):
        obj = build_obj(self.new(sib_debt=[sib_row(7, "等長債解掉", "2026-10-21")]))
        item = by_id(obj)[def999(7)]
        self.assertEqual((item["source"], item["status"], item["title"]),
                         ("系統缺陷", "延後", "（主帳本列已歸檔）"))
        self.assertEqual((item["severity"], item["severity_rank"]), (None, None))
        self.assertEqual(item["updated_at"], "2026-10-21")
        self.assertEqual(notes(obj), [(f"issues.{def999(7)}.severity", "SEVERITY-UNAVAILABLE")])
        self.assertEqual(problems(obj), [])
        self.assertEqual(item["origin"]["file"], SIB_DEBT)

    def test_AT_IC_04_5_E_2_sibling_rows_with_the_wrong_arity_or_duplicates_are_reported(self):
        repo = self.new(sib_blocked=[sib_row(5), ["只有", "兩欄"]], sib_debt=[sib_row(5)])
        obj = build_obj(repo)
        text = fx.read(repo, SIB_BLOCKED).split("\n")
        bad_line = next(i for i, ln in enumerate(text, start=1) if "只有" in ln)
        self.assertEqual(problems(obj, "ROW-ARITY"), [(
            f"AutoSDD_External_Blocked_Log.md:L{bad_line}", "ROW-ARITY", "欄數與表頭不符")])
        self.assertEqual([(s, c) for s, c, _ in problems(obj, "ID-DUP")], [(def999(5), "ID-DUP")])
        self.assertEqual(list(by_id(obj)), [def999(5)])  # 「格式定義」的兩欄表不是資料表
        self.assertEqual(by_id(obj)[def999(5)]["origin"]["file"], SIB_BLOCKED)  # 先中者勝

    def two_card_repo(self):
        repo = fx2.p2_base()
        return repo, fx2.new_prop(repo), fx2.new_prop(repo, target="docs/notes/other.md")

    def test_AT_IC_04_7_1_the_title_is_the_card_symptom_or_says_it_cannot_be_built(self):
        repo, good, bad = self.two_card_repo()
        real = si_card.build

        def selective(repo_, git, events, f, prop_id, params):
            if prop_id == bad:
                raise si_card.CardError("PROP-FILE-MISSING", "r1.md")
            return real(repo_, git, events, f, prop_id, params)

        with mock.patch.object(issues.si_card, "build", selective):
            obj = build_obj(repo)
        got = by_id(obj)
        self.assertEqual(got[good]["title"], "卡面症狀一句")
        self.assertEqual(got[bad]["title"], f"（提案 {bad}：卡面量不到）")
        self.assertIn((f"issues.{bad}.title", "CARD-UNAVAILABLE"), notes(obj))
        self.assertNotIn((f"issues.{good}.title", "CARD-UNAVAILABLE"), notes(obj))

    def test_AT_IC_04_7_E_1_an_unbuildable_card_affects_nothing_else(self):
        repo, good, bad = self.two_card_repo()
        base = build_obj(repo)
        real = si_card.build

        def selective(repo_, git, events, f, prop_id, params):
            if prop_id == bad:
                raise si_card.CardError("PROP-FILE-MISSING", "r1.md")
            return real(repo_, git, events, f, prop_id, params)

        with mock.patch.object(issues.si_card, "build", selective):
            obj = build_obj(repo)
            single = build_obj(repo, ident=bad)["items"][0]
        for ident, item in by_id(base).items():
            if ident != bad:
                self.assertEqual(by_id(obj)[ident], item, ident)
        self.assertEqual(problems(obj), problems(base))
        labels = [r["label"] for r in single["raw"]]
        self.assertNotIn("提案卡", labels)
        self.assertEqual(labels, ["狀態", "路由", "類別", "動作", "修訂", "摘要碼", "來源項目"])

    def test_AT_IC_04_8_1_origin_points_at_the_row_the_issue_came_from(self):
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(2)])]
        repo = self.new(obs=[obs_row(1), obs_row(2)], defs=[def_row(1), def_row(2)], events=events)
        with card_ok():
            got = self.items_of(repo)
        for n in (1, 2):
            self.assertEqual(got[obs_id(n)]["origin"], {
                "ledger": "觀察帳本", "file": f"{QUALITY}/SelfImproving_Observation_Ledger.md",
                "line": line_of(repo, fx.LEDGER, obs_id(n))})
            self.assertEqual(got[def999(n)]["origin"], {
                "ledger": "缺陷帳本", "file": f"{QUALITY}/AutoSDD_Defect_Log.md",
                "line": line_of(repo, fx.DEFLOG, def999(n))})
        created = next(e["seq"] for e in fx.EV(repo) if e["kind"] == "prop" and e["id"] == pid(1))
        self.assertEqual(got[pid(1)]["origin"], {
            "ledger": "事件帳本", "file": f"{QUALITY}/SelfImproving_Event_Ledger.jsonl",
            "seq": created})

    def test_AT_IC_04_8_E_1_windows_line_endings_and_bom_change_nothing(self):
        kw = dict(obs=[obs_row(1), obs_row(2)], defs=[def_row(1)], sib_blocked=[sib_row(7)],
                  obs_archive=[obs_row(9, disp="fixed@abc1234")],
                  events=[*run_events(), *prop_events(1, "proposed", sources=[obs_id(1)])])
        lf, crlf = self.new(**kw), self.new(**kw)
        to_crlf_bom(crlf, fx.LEDGER, fx.DEFLOG, SIB_BLOCKED, OBS_ARCHIVE, fx.EVL)
        with card_ok():
            want, got = build_obj(lf), build_obj(crlf)
        self.assertEqual(stable(got), stable(want))
        by = by_id(got)
        self.assertEqual(by[obs_id(9)]["origin"]["file"], OBS_ARCHIVE)
        self.assertEqual(by[obs_id(9)]["origin"]["line"], line_of(lf, OBS_ARCHIVE, obs_id(9)))
        self.assertEqual(by[def999(7)]["origin"]["file"], SIB_BLOCKED)
        for item in got["items"]:
            self.assertNotIn("\\", item["origin"]["file"])

    def test_AT_IC_04_9_1_broken_and_duplicate_rows_never_become_issues(self):
        short_id = "OBS" + "-SI-" + "12"
        obs = [obs_row(1), obs_row(2)[:8], ["obs-si-001", *obs_row(3)[1:]],
               [short_id, *obs_row(4)[1:]], obs_row(1), obs_row(5)]
        defs = [def_row(1), def_row(2)[:6], def_row(1), def_row(3)]
        obj = build_obj(self.new(obs=obs, defs=defs))
        self.assertEqual(sorted(by_id(obj)), sorted([obs_id(1), obs_id(5), def999(1), def999(3)]))
        arity = [s for s, c, d in problems(obj, "ROW-ARITY")]
        self.assertEqual(len(arity), 4, arity)  # 欄數不符、兩種近似 ID（各一）、缺陷欄數不符
        self.assertEqual(sorted(s for s, _, _ in problems(obj, "ID-DUP")),
                         sorted([obs_id(1), def999(1)]))
        self.assertEqual({d for _, c, d in problems(obj, "ROW-ARITY")},
                         {"欄數與表頭不符", "ID 欄不合 OBS-SI-NNN"})
        self.assertEqual(len(obj["problems"]), 6)

    def test_AT_IC_04_9_E_1_problems_and_notes_are_one_per_ledger_not_per_page(self):
        obs = [obs_row(n) for n in range(1, 9)] + [obs_row(9)[:8], obs_row(9, time="昨天")]
        repo = self.new(obs=obs, defs=[def_row(1)[:6]])
        pages = [build_obj(repo, since=s, limit=lim, statuses=flt)
                 for s, lim, flt in ((None, 2, None), (3, 3, None), (None, None, ["候選"]),
                                     (None, 1, ["已完成"]))]
        for obj in pages[1:]:
            self.assertEqual((obj["problems"], obj["ne"]), (pages[0]["problems"], pages[0]["ne"]))
        self.assertTrue(pages[0]["problems"] and pages[0]["ne"])


def timeline_events() -> list:
    """時間線夾具：各事件動作與各決定動詞（`resume` 除外）各見於某議題；另有免掃與 `resume`。
    `seq` 即位置（從 1 起）；提案 1 走完晉升、量測、更正、回滾，2～5 各走一條決定路徑。"""
    ev = fx.ev
    return [
        fx.run_open_ev(1), fx.skip_ev(1),
        attr_root(1, [obs_id(1)]), confirm(1), attr_root(2, [obs_id(1)]), reject(2),
        fx.obs_add_ev(obs=obs_id(1)), fx.obs_close_ev(obs=obs_id(1)),
        fx.prop_ev(1, 1, sources=[obs_id(1)]), fx.card_ev(1), fx.dec_ev(1, "approve"),
        fx.freeze_ev(1), fx.sandbox_ev(1), fx.verify_ev(1, "PASS"), fx.dec_ev(1, "promote"),
        fx.promote_ev(1), ev("mea.report", prop=pid(1), report="baseline", promote_seq=16),
        ev("mea.open", prop=pid(1), promote_seq=16), ev("mea.close", prop=pid(1), result="pending"),
        ev("mea.amend", prop=pid(1), window=19, cause=19, **{"from": "pending", "to": "recurred"}),
        fx.dec_ev(1, "rollback"), fx.rollback_ev(1),
        fx.prop_ev(2, 1, sources=[obs_id(2)]), fx.dec_ev(2, "reject"), fx.dec_ev(2, "unblock"),
        fx.prop_ev(3, 1, route="handoff:T1", sources=[obs_id(2)]), fx.dec_ev(3, "ack-handoff"),
        fx.prop_ev(4, 1, sources=[obs_id(2)]), *verified_steps(4), fx.dec_ev(4, "decline-promote"),
        fx.prop_ev(5, 1, sources=[obs_id(2)]), fx.dec_ev(5, "return"),
        ev("dec", "掌舵者", run=fx.rid(1), dkind="resume"),
        ev("run.close", run=fx.rid(1), no_event=True),
    ]


class TestTimeline(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的單筆時間線（AC-IC-04-11）。"""

    def timeline_repo(self) -> Path:
        return self.new(obs=[obs_row(1), obs_row(2)], events=timeline_events())

    def line(self, repo, ident) -> list:
        with card_ok():
            return build_obj(repo, ident=ident)["items"][0]["timeline"]

    def test_AT_IC_04_11_1_every_action_reads_in_chinese_in_sequence_order(self):
        repo = self.timeline_repo()
        want = {
            obs_id(1): [(3, "歸因"), (4, "確認歸因"), (5, "歸因"), (6, "駁回歸因"), (7, "新增觀察"),
                        (8, "關閉觀察"), (9, "提案")],
            pid(1): [(1, "開運轉"), (9, "提案"), (10, "出卡"), (11, "決定：核准"),
                     (12, "凍結評估集"), (13, "沙盒套用"), (14, "驗證"), (15, "決定：晉升"),
                     (16, "晉升"), (17, "量測報告"), (18, "開量測窗"), (19, "關量測窗"),
                     (20, "更正量測"), (21, "決定：回滾"), (22, "回滾"), (37, "關運轉")],
            pid(2): [(1, "開運轉"), (23, "提案"), (24, "決定：否決"), (25, "決定：解除冷卻"),
                     (37, "關運轉")],
            pid(3): [(1, "開運轉"), (26, "提案"), (27, "決定：確認轉交"), (37, "關運轉")],
            pid(4): [(1, "開運轉"), (28, "提案"), (29, "決定：核准"), (30, "凍結評估集"),
                     (31, "沙盒套用"), (32, "驗證"), (33, "決定：不晉升"), (37, "關運轉")],
            pid(5): [(1, "開運轉"), (34, "提案"), (35, "決定：退回"), (37, "關運轉")],
        }
        seen = set()
        for ident, steps in want.items():
            tl = self.line(repo, ident)
            self.assertEqual([(t["seq"], t["action"]) for t in tl], steps, ident)
            self.assertEqual([t["seq"] for t in tl], sorted(t["seq"] for t in tl))
            for t in tl:
                self.assertEqual(sorted(t), ["action", "by", "seq", "t"])
                seen.add(t["action"])
        self.assertEqual(len(seen), 26)  # 18 個事件動作加 8 個決定動詞
        # 研究類與 resume 不掛任何議題
        self.assertFalse({"免掃", "研究掃描", "決定：恢復運轉"} & seen)

    def test_AT_IC_04_11_E_1_unknown_actions_and_verbs_read_unmapped_and_are_counted(self):
        extra = [{"seq": 90, "t": "2026-10-18T10:00:00+08:00", "kind": "zombie.act", "by": "m",
                  "prop": pid(1)},
                 {"seq": 91, "t": "2026-10-18T10:01:00+08:00", "kind": "dec", "by": "m",
                  "id": "DEC-SI-091", "dkind": "zombie", "prop": pid(1)}]
        real = si_events.load_sound_events

        def injected(path):
            loaded = real(path)
            return None if loaded is None else [*loaded, *extra]

        repo = self.timeline_repo()
        with mock.patch.object(issues.si_events, "load_sound_events", injected), card_ok():
            obj = build_obj(repo, ident=pid(1))
        tl = obj["items"][0]["timeline"]
        self.assertEqual([(t["seq"], t["action"]) for t in tl][-3:],
                         [(37, "關運轉"), (90, "未歸類：zombie.act"), (91, "決定：未歸類：zombie")])
        self.assertEqual(problems(obj, "UNMAPPED"), [(pid(1), "UNMAPPED", "時間線動作：zombie.act"),
                                                     (pid(1), "UNMAPPED", "決定動詞：zombie")])
        self.assertFalse({2, 36} & {t["seq"] for t in tl})  # 免掃與 resume 不在任何時間線


def sort_item(ident, sev, day, rankable=True) -> dict:
    return {"id": ident, "severity_rank": sev, "updated_at": day, "rankable": rankable}


class TestOrderPagingFilters(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的顯示序、游標分頁、篩選、摘要與文字表
    （AC-IC-05-1～05-6）。"""

    PENDING = ((1, "2026-10-10"), (1, "2026-10-05"), (2, "2026-10-01"), (None, "2026-10-02"),
               (3, None), (3, "2026-10-20"), (1, "2026-10-05"))  # TCS §5.5 規則一的七項

    def test_AT_IC_05_1_1_the_two_display_orders_on_the_shared_example_table(self):
        one = [sort_item(def999(n), s, d) for n, (s, d) in enumerate(self.PENDING, start=1)]
        snapshot = [dict(i) for i in one]
        got = issues.sort_for_display(one, "pending")
        self.assertEqual([i["id"] for i in got], [def999(n) for n in (2, 7, 1, 3, 6, 5, 4)])
        self.assertEqual(one, snapshot)  # 不改動輸入
        days = ("2026-10-20", "2026-10-20", "2026-10-25", None, "2026-09-30")
        done = [sort_item(def999(10 + n), None, d, False) for n, d in enumerate(days, start=1)]
        got = issues.sort_for_display(done, "done")
        self.assertEqual([i["id"] for i in got], [def999(n) for n in (13, 11, 12, 15, 14)])

    def test_AT_IC_05_1_E_1_null_keys_sort_last_under_both_rules(self):
        a, b = sort_item(def999(1), None, None), sort_item(def999(2), 1, None)
        c = sort_item(def999(3), None, "2026-10-01")
        d = sort_item(def999(4), 1, "2026-10-02")
        got = issues.sort_for_display([a, b, c, d], "pending")
        self.assertEqual([i["id"] for i in got], [def999(n) for n in (4, 2, 3, 1)])
        got = issues.sort_for_display([a, b, c, d], "done")
        self.assertEqual([i["id"] for i in got], [def999(n) for n in (4, 3, 1, 2)])

    def test_AT_IC_05_2_1_cursor_paging_is_complete_unique_and_deterministic(self):
        repo = self.new(obs=[obs_row(n) for n in range(1, 31)])

        def walk():
            seen, since, pages = [], None, 0
            while True:
                obj = build_obj(repo, since=since, limit=7)
                pages += 1
                seen += [i["id"] for i in obj["items"]]
                if not obj["truncated"]:
                    self.assertEqual((obj["next_since"], pages), (None, 5))
                    return seen
                self.assertEqual(obj["next_since"], int(obj["items"][-1]["id"].rsplit("-", 1)[1]))
                since = obj["next_since"]

        first = walk()
        self.assertEqual(first, [obs_id(n) for n in range(1, 31)])
        self.assertEqual(walk(), first)
        page = self.cli_json(repo, "--limit", "7", "--since", "14")
        self.assertEqual([i["id"] for i in page["items"]], [obs_id(n) for n in range(15, 22)])
        self.assertEqual((page["truncated"], page["next_since"]), (True, 21))

    def test_AT_IC_05_2_E_1_range_errors_are_usage_errors_and_the_edges_are_accepted(self):
        repo = self.new(obs=[obs_row(1), obs_row(2)])
        for argv in (("--limit", "0"), ("--limit", "501"), ("--since", "-1"), ("--since", "abc"),
                     ("--limit", "x")):
            with self.subTest(argv):
                self.usage_error(*self.cli(repo, *argv), msg=str(argv))
        for argv in (("--limit", "500"), ("--since", "0"), ("--limit", "1")):
            with self.subTest(argv):
                self.assertEqual(self.cli(repo, "--json", *argv)[0], 0)
        far = self.cli_json(repo, "--since", "999999")
        self.assertEqual((far["items"], far["truncated"], far["next_since"]), ([], False, None))

    def test_AT_IC_05_3_1_an_old_cursor_still_resumes_after_new_rows_arrive(self):
        obs = [obs_row(n) for n in range(1, 6)]
        repo = self.new(obs=obs, defs=[def_row(n) for n in range(1, 4)], events=run_events())
        first = build_obj(repo, limit=4)
        self.assertEqual([i["id"] for i in first["items"]], [obs_id(n) for n in range(1, 5)])
        newer_def = ["DEF" + "-998-001", "2026-10-19", "夾具", "後來新增的缺陷", "P2", "-", "open"]
        fx.put(repo, fx.LEDGER, fx.render_ledger([obs_row(n) for n in range(1, 7)]))
        fx.put(repo, fx.DEFLOG, def_text([*(def_row(n) for n in range(1, 4)), newer_def]))
        fx.append_events(repo, [fx.prop_ev(1, 1, sources=[obs_id(1)])])
        with card_ok():
            second = build_obj(repo, since=first["next_since"])
        ids = [i["id"] for i in second["items"]]
        self.assertFalse(set(ids) & {i["id"] for i in first["items"]})
        self.assertEqual(ids, [obs_id(5), obs_id(6), def999(1), def999(2), def999(3),
                               "DEF" + "-998-001", pid(1)])

    def test_AT_IC_05_3_E_1_cursor_bases_do_not_overlap_and_oversized_ids_are_rejected(self):
        big = "OBS" + "-SI-" + str(10_000_000)
        repo = self.new(obs=[obs_row(5), [big, *obs_row(6)[1:]]], defs=[def_row(1)],
                        sib_blocked=[sib_row(7)], sib_debt=[sib_row(8)],
                        events=[*run_events(), fx.prop_ev(3, 1, sources=[obs_id(5)])])
        s, cursors = 10_000_000, {}
        with card_ok():
            since = None
            for _ in range(10):
                obj = build_obj(repo, since=since, limit=1)
                if not obj["items"]:
                    break
                cursors[obj["items"][0]["id"]] = (obj["next_since"] if obj["truncated"] else None)
                since = obj["next_since"]
                if not obj["truncated"]:
                    break
            legend = build_obj(repo)["legend"]
        self.assertEqual(list(cursors), [obs_id(5), def999(1), pid(3), def999(7), def999(8)])
        want = [5, s + line_of(repo, fx.DEFLOG, def999(1)), 2 * s + 3,
                3 * s + line_of(repo, SIB_BLOCKED, def999(7))]
        self.assertEqual([cursors[i] for i in list(cursors)[:4]], want)
        self.assertEqual(sorted(want), want)
        self.assertEqual(problems(build_obj(repo), "ROW-ARITY"),
                         [(big, "ROW-ARITY", "編號或行號過大，游標無法編碼")])
        self.assertIn("游標", legend["problem_codes"][0]["meaning"])

    def filter_repo(self) -> Path:
        research = "面=產品;來源=工具;回報者=研究者;外部衍生=是;src=demo-src"
        obs = [obs_row(1), obs_row(2, cat="process", marks=USER_MARKS),
               obs_row(3, cat="tooling", marks=research),
               obs_row(4, disp="deferred；再開症狀：再發"),
               obs_row(5, disp="fixed@abc1234"), obs_row(6, disp="later")]
        events = [*run_events(), *prop_events(1, "proposed", sources=[obs_id(2)])]
        return self.new(obs=obs, defs=[def_row(1), def_row(2, status="routed")], events=events)

    def test_AT_IC_05_4_1_status_and_source_filters_union_intersect_and_precede_paging(self):
        repo = self.filter_repo()
        with card_ok():
            full = by_id(build_obj(repo, limit=500))

            def ids(*argv, **kw):
                return {i["id"] for i in self.cli_json(repo, *argv, **kw)["items"]}

            pending = {i for i, x in full.items() if x["status"] in ("待解", "進行中", "觀察中")}
            self.assertEqual(ids("--status", "待處理"), pending)
            self.assertEqual(ids("--status", "待解,進行中,觀察中"), pending)
            self.assertEqual(ids("--status", "待處理,待解"), pending)  # 別名與其成員並列＝別名本身
            self.assertEqual(ids("--status", "待解,待解"), ids("--status", "待解"))
            both = {i for i, x in full.items() if x["status"] in ("待您決定", "延後")}
            self.assertEqual(ids("--status", "待您決定,延後"), both)
            research = {i for i, x in full.items() if x["source"] == "研究提案"}
            self.assertEqual(ids("--source", "研究提案"), research)
            self.assertEqual(research, {obs_id(3)})
            self.assertEqual(ids("--status", "待處理", "--source", "系統缺陷"),
                             {i for i in pending if full[i]["source"] == "系統缺陷"})
            page = self.cli_json(repo, "--status", "待處理", "--limit", "1")
            self.assertEqual(len(pending), 3)
            self.assertEqual([i["id"] for i in page["items"]], [obs_id(2)])
            self.assertEqual((page["truncated"], page["next_since"]), (True, 2))  # 取自篩選後

    def test_AT_IC_05_4_E_1_bad_filter_values_are_usage_errors_listing_the_legal_ones(self):
        repo = self.filter_repo()
        bad = ["未知", "待解,,延後", " 待解", "待解 ", "待解，延後", ""]
        for value in bad:
            with self.subTest(status=value):
                rc, out, err = self.cli(repo, f"--status={value}")
                self.usage_error(rc, out, err, msg=repr(value))
                self.assertTrue(all(name in err for name in (*im.STATUSES, "待處理")), err)
        rc, out, err = self.cli(repo, "--source", "路人")
        self.usage_error(rc, out, err)
        self.assertTrue(all(name in err for name in im.SOURCES), err)
        export = ("export", "--json", "--kind")
        for ident in ("obs-si-001", "OBS" + "-SI-12", "PROP" + "-SI-4", "DEF-x-y"):
            with self.subTest(ident=ident):
                self.usage_error(*self.M(repo, *export, "issues", "--id", ident))
        legal_id = obs_id(1)
        for argv in (("--id", legal_id, "--status", "待解"),
                     ("--id", legal_id, "--source", "系統缺陷")):
            self.usage_error(*self.M(repo, *export, "issues", *argv))
        self.usage_error(*self.M(repo, *export, "observations", "--status", "待解"))
        self.usage_error(*self.M(repo, *export, "events", "--source", "系統缺陷"))
        self.assertEqual(self.M(repo, *export, "issues", "--id", legal_id)[0], 0)
        unfiltered = [i["status"] for i in self.cli_json(repo)["items"]]
        self.assertIn("未歸類：later", unfiltered)
        for flt in ("待處理", "待您決定", "候選", "延後", "已完成"):
            kept = self.cli_json(repo, "--status", flt)["items"]
            self.assertFalse([i for i in kept if im.is_unmapped(i["status"])], flt)

    def test_AT_IC_05_5_1_the_summary_is_the_whole_ledger_whatever_the_page(self):
        repo = self.filter_repo()
        with card_ok():
            whole = build_obj(repo)["summary"]
            for kw in (dict(statuses=["待解"]), dict(sources=["系統缺陷"], limit=1),
                       dict(since=3), dict(since=999999),
                       dict(statuses=["已完成"], sources=["系統改善"], limit=2)):
                with self.subTest(kw):
                    self.assertEqual(build_obj(repo, **kw)["summary"], whole)
        self.assertEqual(whole["total"], sum(whole["by_status"].values()) + whole["unmapped"])
        self.assertEqual(whole["unmapped"], 1)

    def test_AT_IC_05_5_E_1_all_seven_keys_are_always_present_and_empty_ledgers_count_zero(self):
        with card_ok():
            s = build_obj(self.filter_repo())["summary"]
        self.assertEqual(list(s["by_status"]), list(im.STATUSES))
        self.assertEqual(s["by_tab"]["待處理"], s["by_status"]["待解"] + s["by_status"]["進行中"]
                         + s["by_status"]["觀察中"])
        empty = self.new(obs=[], defs=[], sib_blocked=[], sib_debt=[], events=[])
        rc, out, err = self.cli(empty, "--json")
        obj = json.loads(out)
        self.assertEqual(rc, 0, err)
        self.assertEqual((obj["items"], obj["problems"], obj["ne"]), ([], [], []))
        self.assertEqual(obj["summary"], {"total": 0, "by_status": dict.fromkeys(im.STATUSES, 0),
                                          "by_tab": {"待處理": 0, "待您決定": 0, "已完成": 0},
                                          "unmapped": 0})
        self.assertEqual(obj["legend"], im.labels())

    def table_repo(self) -> Path:
        obs = [obs_row(1, disp="fixed@abc1234", time="2026-10-20 09:00 +08:00",
                       symptom="完成的中文症狀"),
               obs_row(2, disp="fixed@abc1234", time="2026-10-18 09:00 +08:00")]
        defs = [def_row(1, sev="P3", date="2026-10-10"), def_row(2, sev="P1", date="2026-10-12"),
                def_row(3, sev="P1", date="2026-10-05", evidence="全形標題")]
        return self.new(obs=obs, defs=defs)

    def expected_lines(self, items) -> list:
        """獨立於被測碼的文字表：前五欄依顯示寬度補空白、欄間兩空白、最後一欄標題→下一步。"""
        cells = [[i["id"], i["source"], i["severity"],
                  i["status"] + (f"・{i['result']}" if i["result"] else ""), i["updated_at"]]
                 for i in items]
        wide = [max(display_width(r[c]) for r in cells) for c in range(5)]
        return ["  ".join(v + " " * (w - display_width(v)) for v, w in zip(r, wide))
                + f"  {i['title']}→{i['next_step']}" for r, i in zip(cells, items)]

    def test_AT_IC_05_6_1_the_text_table_is_chinese_aligned_and_ordered_by_the_page_rule(self):
        repo = self.table_repo()
        rc, out, err = self.cli(repo, "--status", "待處理")
        self.assertEqual(rc, 0, err)
        pending = by_id(self.cli_json(repo, "--status", "待處理"))
        order = [def999(3), def999(2), def999(1)]  # 緊急較久沒動 → 緊急 → 中
        self.assertEqual(out.split("\n")[:-2], self.expected_lines([pending[i] for i in order]))
        self.assertEqual(out.split("\n")[-2], "共 3 件；問題 0 筆")
        rc, out, err = self.cli(repo)
        full = by_id(self.cli_json(repo))
        order = [obs_id(1), obs_id(2), def999(2), def999(1), def999(3)]  # 最後更新新→舊
        self.assertEqual(out.split("\n")[:-2], self.expected_lines([full[i] for i in order]))
        for line in out.split("\n")[:-2]:
            self.assertEqual(english_hits(line.split("  ")[-1].split("→", 1)[1]), [], line)
        self.assertEqual(self.cli(repo, "--limit", "2")[1].split("\n")[-2],
                         "共 2 件；問題 0 筆；尚有更多，--since 2")

    def test_AT_IC_05_6_E_1_complete_pages_empty_pages_and_null_columns(self):
        repo = self.table_repo()
        tail = self.cli(repo)[1].split("\n")[-2]
        self.assertEqual(tail, "共 5 件；問題 0 筆")
        self.assertEqual(self.cli(self.new(obs=[], defs=[]))[1], "共 0 件；問題 0 筆\n")
        events = [*run_events(), *prop_events(1, "proposed")]
        with card_ok():
            rc, out, err = self.cli(self.new(obs=None, events=events))
        self.assertEqual(rc, 0, err)
        row = out.split("\n")[0]
        self.assertIn("—", row)  # 來源、嚴重度量不到（觀察帳本讀不到）顯示破折號
        self.assertEqual((row.split()[1], row.split()[2]), ("—", "—"))
        self.assertNotIn("\r", out)


def state_key_hits(text: str, keys) -> set:
    """文字內出現的不同狀態鍵（整詞比對：前後字元不屬英數、`_` 與 `-`）。"""
    return {k for k in keys
            if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(k)}(?![A-Za-z0-9_-])", text)}


def vocabulary_violation(text: str, keys, limit: int = 4) -> bool:
    """TCS R-IC-73：新檔不得含 ≥4 個不同的 `issuemap` 狀態鍵（同一個鍵重複不算）。"""
    return len(state_key_hits(text, keys)) >= limit


def guard(real):
    """包裝 `open`：寫入模式一律拋例外，唯讀照常。"""
    def wrapped(file, mode="r", *a, **k):
        if set(mode) & set("wax+"):
            raise AssertionError(f"寫入原語被呼叫：{file!r} {mode!r}")
        return real(file, mode, *a, **k)

    return wrapped


def refuse(*a, **k):
    raise AssertionError("寫入原語被呼叫")


class TestZeroWriteAndSingleSource(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的零寫入、單一真相、能力登記與歸檔檔處置
    （AC-IC-06-1～06-5）。"""

    def rich_repo(self) -> Path:
        events = [*run_events(), *prop_events(1, "proposed")]
        return self.new(obs=[obs_row(1), obs_row(2, cat="decision")], defs=[def_row(1)],
                        sib_blocked=[sib_row(3)], events=events)

    def test_AT_IC_06_1_1_the_verbs_leave_ledgers_the_tree_and_the_home_untouched(self):
        repo = self.rich_repo()
        before = fx.snap(repo)
        runs = [("issues",), ("issues", "--json"),
                ("issues", "--status", "待處理", "--source", "系統缺陷"),
                ("export", "--json", "--kind", "issues"),
                ("export", "--json", "--kind", "issues", "--id", obs_id(1)),
                ("export", "--json", "--kind", "issues", "--status", "待解")]
        for argv in runs:
            rc, out, err = run_raw(repo, *argv)
            self.assertEqual(rc, 0, (argv, err))
        self.assertEqual(fx.snap(repo), before)
        self.assertEqual(list(self.home.rglob("*")), [])

    def test_AT_IC_06_1_E_1_no_write_primitive_is_ever_reached(self):
        repo = self.rich_repo()
        with mock.patch.object(builtins, "open", guard(builtins.open)), \
                mock.patch("io.open", guard(io.open)), \
                mock.patch.object(Path, "write_text", refuse), \
                mock.patch.object(Path, "write_bytes", refuse), \
                mock.patch.object(Path, "mkdir", refuse), mock.patch("os.replace", refuse):
            rc, out, err = self.cli(repo, "--json")
            rc2, out2, err2 = self.M(repo, "export", "--json", "--kind", "issues",
                                     "--id", obs_id(1))
        self.assertEqual((rc, rc2), (0, 0), err + err2)
        self.assertEqual(json.loads(out2)["items"][0]["id"], obs_id(1))

    def test_AT_IC_06_2_2_the_aggregator_files_hold_no_status_vocabulary_of_their_own(self):
        table = im.real_table()
        keys = table["prop_states"] | table["def_labels"] | table["disp_tokens"]
        self.assertGreater(len(keys), 15)
        for name in ("issues.py", "issues_items.py"):
            hits = state_key_hits((PKG / name).read_text(encoding="utf-8"), keys)
            self.assertLess(len(hits), 4, (name, hits))
        home = state_key_hits((PKG / "issuemap.py").read_text(encoding="utf-8"), keys)
        self.assertGreaterEqual(len(home), 15)  # 對照：詞表住所自己含幾乎全部鍵（掃描器有鑑別力）

    def test_AT_IC_06_2_E_1_the_scanner_counts_distinct_keys_only(self):
        table = im.real_table()
        keys = table["prop_states"] | table["def_labels"] | table["disp_tokens"]
        self.assertTrue(vocabulary_violation('x = ["open", "routed", "wontfix", "verified"]', keys))
        self.assertFalse(vocabulary_violation('x = ["open", "routed", "wontfix"]', keys))
        self.assertFalse(vocabulary_violation('x = ["open", "open", "open", "open", "open"]', keys))
        self.assertFalse(vocabulary_violation("DEF-999-001 與 PROP-SI-004 是編號、不是詞表", keys))

    def test_AT_IC_06_3_1_one_more_verb_and_the_new_modules_are_registered_ro(self):
        import test_selfimproving_capability as cap

        verbs = set(selfimproving._build_parser()._subparsers._group_actions[0].choices)
        self.assertEqual(len(verbs), 24)
        self.assertEqual(verbs, {*LEGAL_VERBS, "issues"})
        cp = subprocess.run([sys.executable, str(ENTRY), "--help"], capture_output=True,
                            check=False)
        text = cp.stdout.decode("utf-8")
        self.assertEqual(cp.returncode, 0)
        self.assertTrue(all(v in text for v in verbs), [v for v in verbs if v not in text])
        for name in ("issuemap.py", "issues.py", "issues_items.py"):
            self.assertEqual(cap.CAPABILITY[name], "ro", name)
        self.assertEqual(cap.capability_problems(cap.PKG, cap.CAPABILITY, cap.ENTRY), [])
        self.assertEqual({p.name for p in PKG.glob("*.py")}, set(cap.CAPABILITY))

    def test_AT_IC_06_3_E_1_a_write_a_child_process_a_socket_or_an_rw_import_is_caught(self):
        import test_selfimproving_capability as cap

        mutations = {"寫檔": 'open("x", "w")\n', "子行程": "import subprocess\n",
                     "網路": "import socket\n", "rw 模組": "from . import writeverbs\n"}
        control = fx.new_dir("pkgc")
        shutil.copytree(PKG, control)
        self.assertEqual(cap.capability_problems(control, cap.CAPABILITY, cap.ENTRY), [])
        for label, line in mutations.items():
            with self.subTest(label):
                dest = fx.new_dir("pkgm")
                shutil.copytree(PKG, dest)
                with (dest / "issues.py").open("a", encoding="utf-8") as fh:
                    fh.write("\n" + line)
                found = cap.capability_problems(dest, cap.CAPABILITY, cap.ENTRY)
                self.assertTrue(any("issues.py" in p for p in found), (label, found))

    def test_AT_IC_06_4_1_si_check_on_the_real_repo_still_passes_all_33_items(self):
        rc, out, err = run_raw(fx.ROOT, "check", "--json")
        res = json.loads(out.decode("utf-8"))
        failed = [(i["id"], [(f["subject"], f["code"]) for f in i["findings"]])
                  for i in res["items"] if i["status"] == "FAIL"]
        self.assertEqual((rc, len(res["items"]), failed), (0, 33, []), err.decode("utf-8"))

    def test_AT_IC_06_5_1_the_defect_archive_files_are_never_opened(self):
        archive = [def_row(1)[:6], def_row(2), def_row(2)]  # 欄數不符與重複 ID
        repo = self.new(defs=[def_row(9)], def_archive=archive)
        opened, real = [], Path.open

        def recording(self_, *a, **k):
            opened.append(self_.name)
            return real(self_, *a, **k)

        with mock.patch.object(Path, "open", recording):
            obj = build_obj(repo)
        self.assertEqual(list(by_id(obj)), [def999(9)])
        self.assertEqual(obj["problems"], [])
        self.assertIn("AutoSDD_Defect_Log.md", opened)
        self.assertNotIn("AutoSDD_Defect_Log_archive_01.md", opened)

    def test_AT_IC_06_5_E_1_observation_archive_files_are_read_and_the_main_file_wins(self):
        archive = [obs_row(1, disp="fixed@abc1234"), obs_row(9, disp="fixed@abc1234")]
        repo = self.new(obs=[obs_row(1)], obs_archive=archive)
        obj = build_obj(repo)
        got = by_id(obj)
        self.assertEqual((got[obs_id(9)]["status"], got[obs_id(9)]["result"]), ("已完成", "已修復"))
        self.assertEqual(got[obs_id(9)]["origin"]["file"], OBS_ARCHIVE)
        self.assertEqual((got[obs_id(1)]["status"], got[obs_id(1)]["origin"]["file"]),
                         ("候選", f"{QUALITY}/SelfImproving_Observation_Ledger.md"))
        self.assertEqual([(s, c) for s, c, _ in problems(obj)], [(obs_id(1), "ID-DUP")])


def make_scale_repo(tmp, obs=5000, defs=2000, events=500, symptom=None) -> Path:
    """規模夾具（AC-IC-12-1）：觀察、缺陷各以模板迴圈產生、事件為合法的提案鏈（卡面內容檔
    不存在屬預期，只驗效能與形狀）。`symptom` 給定則第一列觀察的症狀欄用它。"""
    cats, disps = ("bug", "process", "tooling"), ("open", "fixed@abc1234", "decided：夾具")
    rows = [obs_row(n, cat=cats[n % 3], disp=disps[n % 3], sev=("P1", "P2", "P3", "P4")[n % 4])
            for n in range(1, obs + 1)]
    if symptom is not None:
        rows[0] = obs_row(1, symptom=symptom)
    stats = ("open", "routed", "fixed@abc1234", "wontfix")
    sevs = ("P0", "P1", "P2", "P3")
    drows = [def_row(n, sev=sevs[n % 4], status=stats[n % 4]) for n in range(1, defs + 1)]
    evs = run_events()
    for k in range(1, (events - 2) // 5 + 1):
        evs += [fx.prop_ev(k, 1, sources=[obs_id(1 + k)]), *verified_steps(k)]
    return issue_repo(tmp, obs=rows, defs=drows, events=evs)


class TestPerformanceAndEncoding(IssueCase):
    """`tools/lib/selfimproving/issues.py` 的效能、輸出大小與跨平台編碼（AC-IC-12-1、12-2）。"""

    def timed_export(self, repo, *extra):
        start = time.monotonic()
        rc, out, err = run_raw(repo, "export", "--json", "--kind", "issues", *extra)
        took = time.monotonic() - start
        self.assertEqual(rc, 0, err.decode("utf-8"))
        return took, out

    def test_AT_IC_12_1_1_the_real_ledgers_answer_in_two_seconds_and_under_a_megabyte(self):
        for run in range(5):
            took, out = self.timed_export(fx.ROOT)
            self.assertLess(took, 2.0, f"第 {run + 1} 次 {took:.2f} 秒")
            self.assertLess(len(out), 1_000_000)
        obj = json.loads(out.decode("utf-8"))
        self.assertEqual(len(obj["items"]), min(obj["summary"]["total"], 500))

    def test_AT_IC_12_1_2_a_synthetic_ledger_of_many_thousands_answers_in_two_seconds(self):
        repo = make_scale_repo(fx.new_dir("scale"))
        took, out = self.timed_export(repo)
        self.assertLess(took, 2.0, f"{took:.2f} 秒")
        obj = json.loads(out.decode("utf-8"))
        self.assertEqual(obj["summary"]["total"], 5000 + 2000 + 99)
        self.assertEqual((len(obj["items"]), obj["truncated"]), (500, True))

    def test_AT_IC_12_1_E_1_one_huge_cell_does_not_bloat_the_page_or_change_its_shape(self):
        small = build_obj(self.new(obs=[obs_row(1)]), ident=obs_id(1))["items"][0]
        huge = "長" * 10_240
        repo = make_scale_repo(fx.new_dir("scale"), obs=600, defs=100, events=100, symptom=huge)
        took, out = self.timed_export(repo, "--limit", "500")
        self.assertLess(took, 2.0)
        self.assertLess(len(out), 1_000_000)
        page = json.loads(out.decode("utf-8"))
        first = page["items"][0]
        self.assertEqual(first["title"], huge[:80] + "…")
        self.assertEqual(list(first), [k for k in small if k not in ("raw", "timeline")])
        self.assertTrue(all("raw" not in i and "timeline" not in i for i in page["items"]))
        rc, one, err = run_raw(repo, "export", "--json", "--kind", "issues", "--id", obs_id(1))
        entry = json.loads(one.decode("utf-8"))["items"][0]
        self.assertEqual(list(entry), list(small))
        self.assertEqual(next(r["value"] for r in entry["raw"] if r["label"] == "症狀"), huge)

    def test_AT_IC_12_2_1_stdout_is_utf_eight_without_bom_and_with_lf_only(self):
        repo = self.rich_repo()
        rc, out, err = run_raw(repo, "issues", "--status", "待處理", "--json")
        self.assertEqual(rc, 0, err)
        self.assertFalse(out.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", out)
        self.assertTrue(out.endswith(b"}\n") and out.count(b"\n") == 1)
        obj = json.loads(out.decode("utf-8"))
        self.assertTrue(obj["items"])
        self.assertTrue(all(i["status"] in ("待解", "進行中", "觀察中") for i in obj["items"]))

    def rich_repo(self) -> Path:
        obs = [obs_row(1, cat="process", marks=USER_MARKS, symptom="中文症狀"),
               obs_row(2, disp="fixed@abc1234")]
        return self.new(obs=obs, defs=[def_row(1)])

    def test_AT_IC_12_2_E_1_both_flag_spellings_agree_and_the_text_table_is_clean(self):
        repo = self.rich_repo()
        a = run_raw(repo, "issues", "--status", "待處理", "--json")
        b = run_raw(repo, "issues", "--status=待處理", "--json")
        self.assertEqual((a[0], b[0], a[2], b[2]), (0, 0, b"", b""))
        left, right = json.loads(a[1].decode("utf-8")), json.loads(b[1].decode("utf-8"))
        self.assertEqual(stable(left), stable(right))
        rc, table, err = run_raw(repo, "issues")
        self.assertEqual((rc, err), (0, b""))
        self.assertFalse(table.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", table)
        self.assertTrue(table.decode("utf-8").endswith("問題 0 筆\n"))


if __name__ == "__main__":
    unittest.main()
