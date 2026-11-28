"""交接包第 12／13 欄與接續資訊（Control_Handover W4；TCS-Control AT-CTL-30～38、MU-CTL-22～24、
REQ-CTL-17～19、21）。

受測模組：`tools/lib/sessionctl/agentbrief.py`（第 12 欄、`cut_kind`、`render_cut`）、
`tools/lib/sessionctl/promptchain.py`（第 13 欄、鏈走法）、`handoff_build.py`（13 欄接線）、
`seal.py`（`render_prompts` 帶鏈上路徑）、`controlfacts.py`（`_agent_facts` 的被切來源）。
全用 tmp 居所與注入縫；不讀真實 `~/.claude`／`~/.autosdd`、不起排程、不開視窗。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

from lib.sessionctl import (  # noqa: E402
    agentbrief,
    controlfacts,
    handoff,
    promptchain,
    seal,
)
from lib.sessionctl import handoff_build as build  # noqa: E402

SID = "aaaaaaaa-1111-2222-3333-444444444444"
NOW = datetime(2026, 11, 23, 6, 0, 0, tzinfo=UTC)
SECRET = "TOOL_RESULT_SECRET_DO_NOT_LEAK"


def _iso(minutes_ago: float = 0.0) -> str:
    return (datetime.now(UTC) - timedelta(minutes=minutes_ago)).isoformat()


def _jsonl(path: Path, recs: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n",
                    encoding="utf-8", newline="\n")
    return path


def _task(text: str, ts: str = "") -> dict:
    return {"type": "user", "timestamp": ts or _iso(30),
            "message": {"role": "user", "content": text}}


def _say(text: str, ts: str = "", model: str = "sonnet") -> dict:
    return {"type": "assistant", "timestamp": ts or _iso(20),
            "message": {"id": f"m-{abs(hash(text))}", "model": model,
                        "usage": {"input_tokens": 1, "cache_read_input_tokens": 9,
                                  "cache_creation_input_tokens": 0},
                        "content": [{"type": "text", "text": text}]}}


def _write_use(path: str, name: str = "Write") -> dict:
    return {"type": "assistant", "timestamp": _iso(25), "message": {
        "model": "sonnet", "content": [{"type": "tool_use", "id": "t", "name": name,
                                        "input": {"file_path": path, "content": "x"}}]}}


def _tool_result(text: str) -> dict:
    return {"type": "user", "timestamp": _iso(24), "message": {
        "content": [{"type": "tool_result", "tool_use_id": "t", "content": text}]}}


def _cut(ts: str = "", api_error: bool = True) -> dict:
    rec = {"type": "assistant", "timestamp": ts or _iso(5), "message": {
        "model": "<synthetic>", "content": [{"type": "text", "text":
                                             "You've hit your 5-hour limit · resets 5:40am"}]}}
    if api_error:
        rec["apiError"] = "usage_limit_reached"
    return rec


class _Fence(unittest.TestCase):
    """tmp 居所：主逐字稿在 `proj/<SID>.jsonl`、代理在 `proj/<SID>/subagents/`。"""

    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="ab-w4-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.proj = self.tmp / "proj"
        self.hdir = self.tmp / "handoff"
        self.hdir.mkdir()
        patch = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "traces"), "AUTOSDD_HANDOFF_DIR": str(self.hdir),
            "CLAUDE_CONFIG_DIR": str(self.tmp / ".claude")})
        patch.start()
        self.addCleanup(patch.stop)
        self.main = _jsonl(self.proj / f"{SID}.jsonl",
                           [_task("hi"), _say("ok", model="claude-fable-5")])

    def agent(self, aid: str, recs: list[dict], *, finished: bool | None = None,
              sid: str = SID) -> Path:
        folder = self.proj / sid / "subagents"
        meta = {"description": f"代理 {aid}", "model": "sonnet"}
        if finished is not None:
            meta["finished"] = finished
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"agent-{aid}.meta.json").write_text(json.dumps(meta), encoding="utf-8")
        return _jsonl(folder / f"agent-{aid}.jsonl", recs)

    @staticmethod
    def row(aid: str, state: str = "running", **kw) -> dict:
        return {"id": aid, "owner_sid": SID, "description": f"代理 {aid}", "model": "sonnet",
                "state": state, "ctx_tokens": 1234, "last_at": _iso(10), **kw}

    def kill(self, *ids: str) -> None:
        """主逐字稿追加 harness 的 `<status>killed</status>` 任務通知（`rosterscan` 認的形態）。"""
        with self.main.open("a", encoding="utf-8", newline="\n") as handle:
            for aid in ids:
                note = f"<task-notification><task-id>{aid}</task-id><status>killed</status>"
                handle.write(json.dumps({"type": "queue-operation", "content": note}) + "\n")


class CutKindTest(_Fence):
    """tools/lib/sessionctl/agentbrief.py::cut_kind（AT-CTL-32）：被切判準單一家。"""

    def test_usage_limit_by_api_error_or_synthetic_text(self) -> None:
        a = self.agent("cut1", [_task("t"), _cut()])
        b = self.agent("cut2", [_task("t"), _cut(api_error=False)])
        self.assertEqual(agentbrief.cut_kind(a), "usage_limit")
        self.assertEqual(agentbrief.cut_kind(b), "usage_limit")  # 末筆 <synthetic> 含 hit your

    def test_synthetic_without_limit_words_is_not_cut(self) -> None:
        rec = _cut(api_error=False)
        rec["message"]["content"][0]["text"] = "No response requested."
        self.assertIsNone(agentbrief.cut_kind(self.agent("x", [_task("t"), rec])))

    def test_stopped_residue_and_precedence(self) -> None:
        ok = self.agent("ok1", [_task("t"), _say("做中")])
        self.assertIsNone(agentbrief.cut_kind(ok, agent_id="ok1", state="running"))
        self.assertEqual(agentbrief.cut_kind(ok, killed={"ok1"}, agent_id="ok1"), "stopped")
        self.assertEqual(agentbrief.cut_kind(ok, agent_id="ok1", state="residue"), "residue")
        cut = self.agent("cutk", [_task("t"), _cut()])  # 同時被 killed：usage_limit 優先
        self.assertEqual(agentbrief.cut_kind(cut, killed={"cutk"}, agent_id="cutk"), "usage_limit")

    def test_only_the_last_record_counts_and_unreadable_is_not_a_guess(self) -> None:
        old_cut = self.agent("old", [_task("t"), _cut(), _say("後來又做了")])
        self.assertIsNone(agentbrief.cut_kind(old_cut))
        self.assertIsNone(agentbrief.cut_kind(self.tmp / "nope.jsonl"))
        self.assertIsNone(agentbrief.cut_kind(None))


class Column12Test(_Fence):
    """tools/lib/sessionctl/agentbrief.py::column12（AT-CTL-31／33／36、MU-CTL-23）。"""

    def test_five_states_each_have_all_fields(self) -> None:
        brief = str(self.tmp / "claude" / "x" / "s1" / "scratchpad" / "w4_brief.md")
        out_dir = self.tmp / "out"
        long_task = f"你是 Dev。任務書在 `{brief}`。" + "任務內容。" * 200
        files = [str(out_dir / f"f{i}.py") for i in range(12)]
        self.agent("run1", [_task(long_task), *[_write_use(f) for f in files],
                            _tool_result(SECRET), _say("甲"), _say("乙"), _say("丙"), _say("丁")])
        self.agent("qui1", [_task("安靜的任務"), _say("等人")])
        self.agent("res1", [_task("殘局任務"), _say("沒收尾")])
        self.agent("cut1", [_task("被切任務"), _say("做到一半"), _cut()])
        self.agent("stp1", [_task("被停任務"), _say("被 TaskStop")])
        self.kill("stp1")
        agents = [self.row("run1"), self.row("qui1", "quiet"), self.row("res1", "residue"),
                  self.row("cut1", "running")]
        text = agentbrief.column12(agents, SID, self.main, oi_fn=lambda: "")
        for aid, status in (("run1", "running"), ("qui1", "quiet"), ("res1", "residue"),
                            ("cut1", "cut（usage_limit）"), ("stp1", "stopped")):
            line = next(ln for ln in text.splitlines() if ln.startswith(f"- {aid}｜"))
            self.assertIn(f"｜{status}｜", line, line)
            self.assertIn("｜sonnet｜", line)
        self.assertIn(f"代理逐字稿：{self.proj / SID / 'subagents' / 'agent-run1.jsonl'}", text)
        # 任務書指標＝首筆 user 前 600 字（引文），其餘被截並標原文字數
        self.assertIn("…（已截斷，原文", text)
        self.assertIn(brief, text)
        # 輸出落點去重至多 8 個（保留最近）；最後 3 則 assistant（乙丙丁），不含甲
        self.assertEqual(text.count(str(out_dir / "f")), 8)
        self.assertIn(str(out_dir / "f11.py"), text)
        self.assertNotIn(str(out_dir / "f3.py"), text)
        self.assertIn("> 丁", text)
        self.assertNotIn("> 甲", text)
        # 建議處置兩類字面
        self.assertGreaterEqual(text.count("排空後換（pending_switch）"), 2)
        # res／cut／stp 各一句，加 quiet 的備援句
        self.assertEqual(text.count("重派：新代理＋短任務書"), 3 + 1)

    def test_tool_result_content_never_leaks(self) -> None:
        self.agent("run1", [_task("t"), _write_use(str(self.tmp / "a.py")), _tool_result(SECRET),
                            _say("好")])
        text = agentbrief.column12([self.row("run1")], SID, self.main, oi_fn=lambda: "")
        self.assertNotIn(SECRET, text)

    def test_unreadable_agent_transcript_is_said_and_others_unaffected(self) -> None:
        self.agent("good", [_task("好任務"), _say("好")])
        text = agentbrief.column12([self.row("ghost"), self.row("good")], SID, self.main,
                                   oi_fn=lambda: "")
        self.assertIn("量不到：找不到代理逐字稿", text)
        self.assertIn("好任務", text)
        empty = self.agent("empty", [])
        empty.write_text("", encoding="utf-8")
        text2 = agentbrief.column12([self.row("empty")], SID, self.main, oi_fn=lambda: "")
        self.assertIn("量不到：代理逐字稿空或讀不到", text2)

    def test_roster_unavailable_and_no_agents(self) -> None:
        down = agentbrief.column12(None, SID, self.main, why="名冊不可用（X）", oi_fn=lambda: "")
        self.assertIn("量不到：名冊不可用（X）", down)
        none = agentbrief.column12([], SID, self.main, oi_fn=lambda: "")
        self.assertIn("無在飛／被切代理", none)

    def test_size_cap_drops_oldest_rows_and_says_how_many(self) -> None:
        agents = []
        for i in range(30):
            self.agent(f"big{i:02d}", [_task("任務" * 400), _say("結論" * 100)])
            agents.append(self.row(f"big{i:02d}", last_at=_iso(100 - i)))
        text = agentbrief.column12(agents, SID, self.main, oi_fn=lambda: "")
        body = text.split("\n\n未結 OI：")[0]
        self.assertLessEqual(len(body), agentbrief.COL12_MAX_CHARS + 200)
        self.assertRegex(body, r"已截斷 \d+ 列")
        self.assertIn("big29", body)       # 最新的留下
        self.assertNotIn("big00｜", body)  # 最舊的先被截

    def test_oi_line_reuses_summary_and_says_unknown_when_missing(self) -> None:
        ok = agentbrief.column12([], SID, self.main,
                                 oi_fn=lambda: " 掌舵者目視清單（OIR）：OI-1；OI-2。")
        self.assertIn("未結 OI：掌舵者目視清單（OIR）：OI-1；OI-2。", ok)
        miss = agentbrief.column12([], SID, self.main, oi_fn=lambda: "")
        self.assertIn("未結 OI：量不到：OIR 目視清單無資料", miss)

        def boom() -> str:
            raise RuntimeError("x")
        self.assertIn("量不到：OIR 目視清單讀不到（RuntimeError）",
                      agentbrief.column12([], SID, self.main, oi_fn=boom))

    def test_render_cut_lists_only_cut_kinds_and_never_redispatches(self) -> None:
        self.agent("run1", [_task("t"), _say("做")])
        self.agent("cut1", [_task("被切"), _cut()])
        rows = agentbrief.collect([self.row("run1"), self.row("cut1", "running")], SID, self.main)
        text = agentbrief.render_cut(rows)
        self.assertIn("cut1", text)
        self.assertNotIn("- run1｜", text)
        self.assertIn("不自動重派", text)
        self.assertEqual(agentbrief.render_cut([r for r in rows if r["id"] == "run1"]), "")


class ControlFactsCutSourceTest(_Fence):
    """tools/lib/sessionctl/controlfacts.py::_agent_facts：被切來源改用 `agentbrief.cut_kind`。"""

    def facts(self) -> tuple[int, int, list]:
        payload = {"session_id": SID, "transcript_path": str(self.main)}
        return controlfacts._agent_facts(payload, SID, {})

    def test_usage_limit_agent_is_cut_not_running(self) -> None:
        self.agent("live", [_task("t"), _say("做中", ts=_iso(0.2))])
        self.agent("cutx", [_task("t"), _say("x", ts=_iso(1)), _cut(ts=_iso(0.5))])
        running, quiet, cut = self.facts()
        self.assertEqual((running, quiet), (1, 0))
        self.assertEqual(cut, [{"id": "cutx", "kind": "usage_limit"}])

    def test_recently_taskstopped_agent_is_listed_as_stopped(self) -> None:
        self.agent("stp", [_task("t"), _say("被停", ts=_iso(3))])
        self.kill("stp")
        _running, _quiet, cut = self.facts()
        self.assertEqual(cut, [{"id": "stp", "kind": "stopped"}])

    def test_residue_still_reported(self) -> None:
        self.agent("old", [_task("t"), _say("舊", ts=_iso(300))])
        with mock.patch.object(controlfacts.seal, "handed_over", return_value=Path("x")), \
                mock.patch.object(controlfacts.roster, "_handed_over", return_value=True):
            _running, _quiet, cut = self.facts()
        self.assertEqual(cut, [{"id": "old", "kind": "residue"}])


def _package(base: Path, owner: str, stamp: str, *, acker: str | None = None,
             ack_at: str | None = None, prompts: list[str] | None = None,
             sealed: str | None = "2026-11-22T10:00:00+08:00") -> Path:
    pkg = base / f"{owner}_{stamp}.md"
    pkg.write_text(
        f"# 交接包 <!-- sessionctl-handoff sid={owner} at=2026-11-22T00:00:00+08:00 -->\n",
        encoding="utf-8")
    if acker is not None:
        pkg.with_suffix(".ack").write_text(
            f"acked {ack_at or '2026-11-22T12:00:00+08:00'} sid={acker}\n", encoding="utf-8")
    if sealed:
        pkg.with_suffix(".sealed").write_text(sealed + "\n", encoding="utf-8")
    if prompts is not None:
        body = "\n".join(f"## 提示 {i + 1}（2026-11-22，逐字稿第 {i + 1} 行）\n\n{t}\n"
                         for i, t in enumerate(prompts))
        seal.sidecar_path(pkg).write_text(f"# 真人提示全文\n\n{body}", encoding="utf-8")
    return pkg


class PromptChainTest(_Fence):
    """tools/lib/sessionctl/promptchain.py（AT-CTL-34／35、MU-CTL-24）。"""

    def test_three_leg_chain_is_listed_with_paths_prompts_and_stars(self) -> None:
        a, b, c, d = "sid-a", "sid-b", "sid-c", "sid-d"
        _package(self.hdir, a, "20261120T000000Z", acker=b, ack_at="2026-11-20T01:00:00+08:00",
                 prompts=["A的話"])
        _package(self.hdir, b, "20261121T000000Z", acker=c, ack_at="2026-11-21T01:00:00+08:00",
                 prompts=[f"B話{i}" + "長" * 300 for i in range(5)])
        _package(self.hdir, c, "20261122T000000Z", acker=d, ack_at="2026-11-22T01:00:00+08:00",
                 prompts=["C的話"])
        pad = self.tmp / "claude" / "h" / c / "scratchpad"
        pad.mkdir(parents=True)
        for i in range(15):
            (pad / f"w{i}_report.md").write_text("x", encoding="utf-8")
        (pad / "RESTART_POINT.md").write_text("x", encoding="utf-8")
        (pad / "other.txt").write_text("x", encoding="utf-8")
        text = promptchain.column13(d, self.hdir, lambda s: build.star_files(s, self.tmp))
        self.assertIn("前 1 棒 sid sid-c", text)
        self.assertIn("前 2 棒 sid sid-b", text)
        self.assertIn("前 3 棒 sid sid-a", text)
        self.assertIn("sid-c_20261122T000000Z.prompts.md", text)
        self.assertIn("> C的話", text)
        self.assertIn("鏈止於 sid-a：無包記錄其接手", text)
        # 每棒 prompts 至多 3 則、每則 ≤200 字（含截斷標示）、★檔至多 12
        leg_b = text.split("前 2 棒")[1].split("前 3 棒")[0]
        self.assertEqual(leg_b.count("> B話"), 3)
        self.assertNotIn("> B話1", leg_b)
        self.assertIn("已截斷，原文", leg_b)
        leg_c = text.split("前 1 棒")[1].split("前 2 棒")[0]
        self.assertEqual(sum(1 for ln in leg_c.splitlines() if ln.startswith("    - ")), 12)
        self.assertIn("RESTART_POINT.md", leg_c)
        self.assertNotIn("other.txt", leg_c)

    def test_no_chain_when_sid_never_took_over_a_package(self) -> None:
        _package(self.hdir, "sid-a", "20261120T000000Z", acker="sid-b")
        self.assertEqual(promptchain.column13("sid-z", self.hdir), promptchain.NO_CHAIN)
        self.assertEqual(promptchain.column13("sid-b", self.hdir.parent / "empty"),
                         promptchain.NO_CHAIN)
        self.assertIn("量不到", promptchain.column13("sid-z", None))

    def test_depth_is_capped_and_cycles_do_not_loop(self) -> None:
        for i in range(8):  # s0 被 s1 接手…s7（共 8 包）
            _package(self.hdir, f"s{i}", f"2026112{i}T000000Z", acker=f"s{i + 1}")
        legs, note = promptchain.walk("s8", self.hdir)
        self.assertEqual(len(legs), promptchain.CHAIN_DEPTH)
        self.assertIn("深度上限", note)
        loop = self.tmp / "loop"
        loop.mkdir()
        _package(loop, "x", "20261120T000000Z", acker="y")
        _package(loop, "y", "20261121T000000Z", acker="x")
        legs, note = promptchain.walk("x", loop)
        self.assertLessEqual(len(legs), 2)
        self.assertIn("成環", note)

    def test_same_sid_with_several_packages_takes_the_earliest_ack(self) -> None:
        """4a45bc75 形狀：同一 sid 有兩個包；被下一棒 ack 的只取 `.ack` 最早者，另註記。"""
        _package(self.hdir, "owner", "20261120T000000Z", acker="me",
                 ack_at="2026-11-20T09:00:00+08:00")
        _package(self.hdir, "owner", "20261121T000000Z", acker="me",
                 ack_at="2026-11-21T09:00:00+08:00")
        legs, _ = promptchain.walk("me", self.hdir)
        self.assertEqual(legs[0]["package"].name, "owner_20261120T000000Z.md")
        self.assertEqual(legs[0]["others"], 1)
        self.assertIn("另有 1 個包同接手者", promptchain.column13("me", self.hdir))

    def test_missing_prompts_sidecar_is_said(self) -> None:
        _package(self.hdir, "sid-a", "20261120T000000Z", acker="me", prompts=None)
        text = promptchain.column13("me", self.hdir)
        self.assertIn("prompts 全文：缺（", text)
        self.assertIn("量不到：prompts sidecar 缺或讀不到", text)

    def test_column_cap_drops_oldest_legs(self) -> None:
        for i in range(5):
            _package(self.hdir, f"s{i}", f"2026112{i}T000000Z", acker=f"s{i + 1}",
                     prompts=["話" * 190] * 3)
        pad = self.tmp / "claude" / "h"
        files = []
        for i in range(5):
            folder = pad / f"s{i}" / "scratchpad"
            folder.mkdir(parents=True)
            files += [folder / f"{'長' * 60}_{j}_report.md" for j in range(12)]
        for path in files:
            path.write_text("x", encoding="utf-8")
        text = promptchain.column13("s5", self.hdir, lambda s: build.star_files(s, self.tmp))
        self.assertLessEqual(len(text.split("（已截斷")[0]), promptchain.COL13_MAX_CHARS + 50)
        self.assertRegex(text, r"已截斷 \d+ 列較舊的棒")
        self.assertIn("前 1 棒", text)

    def test_prompt_paths_for_sidecar_only_existing(self) -> None:
        _package(self.hdir, "sid-a", "20261120T000000Z", acker="me", prompts=["x"])
        _package(self.hdir, "sid-b", "20261121T000000Z", acker="sid-a", prompts=None)
        paths = promptchain.prompt_paths("me", self.hdir)
        self.assertEqual([p.name for p in paths], ["sid-a_20261120T000000Z.prompts.md"])


class BuildMechanicalWiringTest(_Fence):
    """tools/lib/sessionctl/handoff_build.py：13 欄接線（AT-CTL-30／33／37、REQ-CTL-21）。"""

    class _Runner:
        def __call__(self, argv, **_kw):
            return (0, "", None) if argv[0] != "git" else (0, "x\n", None)

    class _Roster:
        def __init__(self, agents):
            self.agents = agents

        def snapshot(self, sid=None, **_kw):
            return {"agents": self.agents}

        def render_snapshot(self, _snap):
            return "（假名冊）"

    def mech(self, agents=None, roster=None, package=None) -> str:
        def no_quota(_now):
            raise RuntimeError("no")

        return build.build_mechanical(
            SID, self.main, repo=self.tmp, now=NOW, runner=self._Runner(),
            roster_mod=roster or self._Roster(agents or []), quota_fn=no_quota,
            temp_root=self.tmp / "none", package=package,
            oi_fn=lambda: " 掌舵者目視清單（OIR）：OI-9。")

    def test_thirteen_numbered_sections_and_model_and_worktree(self) -> None:
        text = self.mech()
        self.assertEqual(text.count("\n### ") + 1, 13)
        self.assertIn("### 12 在飛／被切代理\n", text)
        self.assertIn("### 13 鏈上前幾棒\n量不到：未給交接包目錄", text)  # 沒給 package／chain_base
        self.assertIn("- 主控模型：claude-fable-5", text)
        self.assertIn("worktree（`git worktree list`）", text)
        self.assertIn("未結 OI：掌舵者目視清單（OIR）：OI-9。", text)

    def test_package_without_a_predecessor_says_no_chain(self) -> None:
        text = self.mech(package=self.hdir / f"{SID}_20261121T000000Z.md")
        self.assertIn("### 13 鏈上前幾棒\n（無前鏈）", text)

    def test_chain_base_comes_from_the_package_directory(self) -> None:
        _package(self.hdir, "prev", "20261120T000000Z", acker=SID, prompts=["前棒原話"])
        text = self.mech(package=self.hdir / f"{SID}_20261121T000000Z.md")
        self.assertIn("前 1 棒 sid prev", text)
        self.assertIn("> 前棒原話", text)

    def test_roster_failure_keeps_other_columns(self) -> None:
        class Boom:
            def snapshot(self, *_a, **_k):
                raise RuntimeError("x")

        text = self.mech(roster=Boom())
        self.assertIn("### 12 在飛／被切代理\n量不到：名冊不可用（RuntimeError）", text)
        self.assertIn("### 13 鏈上前幾棒", text)

    def test_cut_agent_appears_in_the_built_package(self) -> None:
        self.agent("cut1", [_task("被切任務書"), _cut()])
        text = self.mech(agents=[self.row("cut1", "running")])
        self.assertIn("- cut1｜", text)
        self.assertIn("cut（usage_limit）", text)

    def test_legacy_eleven_column_package_is_tolerated(self) -> None:
        """AT-CTL-37／REQ-CTL-21：舊包（只有 11 欄）finalize／ack／list／announce 不受影響；
        「已驗證：（無）」仍通過 finalize（不加內容檢查）。"""
        legacy = self.hdir / f"{SID}_20261101T000000Z.md"
        main = "\n\n".join(f"{h}\n（無）" for h in handoff.SECTIONS)
        head = f"# 交接包 <!-- sessionctl-handoff sid={SID} at=2026-11-01T00:00:00+08:00 -->"
        legacy.write_text(f"{head}\n\n## 機械層\n\n### 1 來源與時刻\nx\n\n### 11 逐字稿路徑\ny\n\n"
                          f"{handoff.MAIN_MARK}\n\n{main}\n", encoding="utf-8")
        self.assertEqual(handoff.finalize(legacy)[0], 0)
        self.assertEqual(handoff.list_handoffs(self.hdir)[0]["sid"], SID)
        self.assertEqual(promptchain.column13("someone", self.hdir), promptchain.NO_CHAIN)


class RenderPromptsChainTest(_Fence):
    """tools/lib/sessionctl/seal.py::render_prompts 帶鏈上路徑，且不給時逐字不變。"""

    PROMPTS = [{"text": "你好", "at": "2026-11-23T00:00:00Z", "line": 1}]

    def test_chain_paths_listed_and_default_output_unchanged(self) -> None:
        plain = seal.render_prompts(SID, self.PROMPTS, NOW)
        self.assertNotIn("鏈上前幾棒", plain)
        prev = self.tmp / "p" / "a.prompts.md"
        chained = seal.render_prompts(SID, self.PROMPTS, NOW, [prev])
        self.assertIn("鏈上前幾棒的真人提示全文", chained)
        self.assertIn(f"- {prev}", chained)
        self.assertIn("## 提示 1（2026-11-23T00:00:00Z，逐字稿第 1 行）", chained)

    def test_refresh_prompts_writes_chain_into_the_sidecar(self) -> None:
        _package(self.hdir, "prev", "20261120T000000Z", acker=SID, prompts=["前棒原話"])
        mine = self.hdir / f"{SID}_20261121T000000Z.md"
        mine.write_text(f"# 交接包 <!-- sessionctl-handoff sid={SID} at=x -->\n", encoding="utf-8")
        target = seal.refresh_prompts(mine, transcript=self.main, now=NOW, repo=self.tmp, env={})
        self.assertIsNotNone(target)
        self.assertIn("prev_20261120T000000Z.prompts.md", target.read_text(encoding="utf-8"))


class SourceContractTest(unittest.TestCase):
    """tools/lib/sessionctl/{agentbrief,promptchain}.py 的原始碼契約（MU-CTL-22／24）。"""

    def test_new_columns_are_appended_not_inserted(self) -> None:
        self.assertEqual(build.MECH_HEADINGS[-2:], ("在飛／被切代理", "鏈上前幾棒"))
        self.assertEqual(build.MECH_HEADINGS.index("逐字稿路徑"), 10)

    def test_size_caps_match_the_frozen_design(self) -> None:
        self.assertEqual(
            (agentbrief.BRIEF_CHARS, agentbrief.LAST_TEXTS, agentbrief.COL12_MAX_CHARS),
            (300, 3, 12000))
        self.assertEqual((promptchain.PROMPT_EXCERPT_CHARS, promptchain.LAST_PROMPTS,
                          promptchain.COL13_MAX_CHARS, promptchain.CHAIN_DEPTH), (200, 3, 8000, 5))


# ───────────────────────────── WP-SW REQ-CTL-55（AT-CTL-123～128）：名冊訊息三段式
def _wrow(aid: str, status: str, desc: str, **over) -> dict:
    kind = {"cut": "usage_limit", "stopped": "stopped", "residue": "residue"}[status]
    return {"id": aid, "description": desc, "model": "sonnet", "state": "quiet", "kind": kind, "ctx": 5000,
            "last_at": "2026-11-26T23:46:36+08:00", "path": None, "error": "量不到：找不到代理逐字稿",
            "status": status, **over}


_PKG_HEAD = "# 交接包 <!-- sessionctl-handoff sid=406454ea-91fc-4481-9c11-b28ed7d9e95f at=x -->\n\n## 機械層\n\n"
_AGENT_ID = "aee3d937b179d8639"


class WpSwThreeSectionTest(unittest.TestCase):
    """WHY：406454ea 逐字稿第 10412 行把 cut／stopped／residue 併成一句「由主控決定」，而同稿第 10306 行已
    TaskStop、包第 284／288 行已記處置——掌舵者據此重提問題 3。三段標題＋看主控層才不再誤導。"""

    ROWS = [_wrow("cutcutcut0000001", "cut", "額度切斷者"), _wrow(_AGENT_ID, "stopped", "FLK5 mac 修復"),
            _wrow("resresres0000002", "residue", "殘局者")]

    def render(self, rows=None, **kw) -> str:
        return agentbrief.render_cut(rows or self.ROWS, **kw)

    def test_at_ctl_123_three_headings_in_fixed_order_and_no_old_phrase(self) -> None:
        text = self.render()
        heads = ("被額度切斷", "主控已停止（TaskStop）", "殘局（擁有者已不在、非燒額度中）")
        at = [text.index(h) for h in heads]
        self.assertEqual(at, sorted(at))
        for h in heads:
            self.assertEqual(text.count(f"{h}（"), 1)
        self.assertNotIn("由主控決定", text)
        only = self.render([self.ROWS[1]])
        self.assertIn("主控已停止（TaskStop）", only)
        self.assertNotIn("被額度切斷", only)
        self.assertNotIn("殘局（擁有者", only)

    def test_at_ctl_124_stopped_recorded_by_id_prefix_or_first_description_token(self) -> None:
        by_id = _PKG_HEAD + f"- 第 12 欄略\n\n## 主控層\n\n## 未完成\n- 代理 {_AGENT_ID[:8]} 已停\n"
        self.assertIn("主控已停止並已記入交接包 X.md", self.render(pkg_text=by_id, pkg_path="X.md"))
        # 406454ea 形狀：id 只在機械層第 12 欄、主控層只寫「FLK5」
        real = _PKG_HEAD + f"## 12. 背景代理\n- {_AGENT_ID}｜FLK5 mac 修復\n\n## 主控層\n\n## 未完成\n- FLK5 已 TaskStop、半成品已保全\n"
        self.assertIn("主控已停止並已記入交接包 X.md", self.render(pkg_text=real, pkg_path="X.md"))

    def test_at_ctl_125_stopped_without_record_or_machine_layer_mention_only(self) -> None:
        machine_only = _PKG_HEAD + f"## 12. 背景代理\n- {_AGENT_ID}｜FLK5 mac 修復\n\n## 主控層\n\n## 未完成\n- 別的事\n"
        for pkg in (machine_only, None, ""):
            with self.subTest(pkg=str(pkg)[:12]):
                text = self.render(pkg_text=pkg, pkg_path="X.md")
                self.assertIn("交接包未記處置 ⇒ 下一棒依第 12 欄重派", text)
                self.assertNotIn("已記入交接包", text)

    def test_at_ctl_126_cut_and_residue_actions_and_column12_unchanged(self) -> None:
        text = self.render()
        self.assertIn(f"建議處置：{agentbrief._ACTIONS['cut']}", text)  # noqa: SLF001
        self.assertIn(f"建議處置：{agentbrief._ACTIONS['residue']}", text)  # noqa: SLF001
        col12 = agentbrief.render_rows([self.ROWS[1]])
        self.assertIn(f"建議處置：{agentbrief._ACTIONS['stopped']}", col12)  # noqa: SLF001
        self.assertNotIn("處置：主控已停止", col12, "第 12 欄是交接包本身，建議處置逐字不變")

    def test_at_ctl_127_no_new_pushback_decision_field(self) -> None:
        src =(_REPO_ROOT / "tools" / "lib" / "sessionctl" / "agentbrief.py").read_text(encoding="utf-8")
        self.assertNotIn('"decision"', src)
        self.assertNotIn("decision:block", src)

    def test_at_ctl_128_old_phrase_absent_from_all_session_tests_and_sources(self) -> None:
        for name in ("agentbrief.py", "cutvoice.py", "roster.py", "briefline.py", "watch.py"):
            path = _REPO_ROOT / "tools" / "lib" / "sessionctl" / name
            self.assertNotIn("由主控決定", path.read_text(encoding="utf-8"), name)


if __name__ == "__main__":
    unittest.main()
