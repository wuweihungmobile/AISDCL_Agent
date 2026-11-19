#!/usr/bin/env python3
"""交接包第二版（封存）與逐字稿判準函式的驗收測試（R3 WP-A；ARCH §2.6、FR-S2／FR-S3、AT-S3～S5）。

守的判準：
- 封存＝重建機械層（主控層逐字保留）＋全部真人提示 sidecar＋通過才寫封存戳；驗不過什麼都不寫；
- 純驗證 `handoff.finalize` 不得有寫檔副作用（converge／park 靠它判「寫完了沒」）；
- 逐字稿判準單一家：機器提示、全部真人提示、最後提示時刻、封存後「有沒有工作」（唯讀工具不算）。
縫：FS（tmp 目錄）、NOW、假 runner／名冊／額度。不碰真實 ~/.autosdd 與 ~/.claude。
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import context_budget_guard as guard  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402
import transcript_activity as ta  # noqa: E402

from lib.sessionctl import handoff, seal  # noqa: E402

_FENCES: list[dict] = []


def setUpModule() -> None:
    _FENCES.append(SL.fence_enter())
    os.environ[guard.SENTINEL_OFF_ENV] = "1"


def tearDownModule() -> None:
    SL.fence_exit(_FENCES.pop())


SID = "bbbbbbbb-1111-2222-3333-444444444444"
NOW = datetime(2026, 11, 17, 3, 0, 0, tzinfo=UTC)
FULL_MAIN = "\n\n".join(f"{h}\n內容 {i}" for i, h in enumerate(handoff.SECTIONS))


def _rec(kind: str, text, ts: str, **extra) -> dict:
    rec = {"type": "user", "timestamp": ts, "message": {"role": "user", "content": text}, **extra}
    if kind:
        rec["origin"] = {"kind": kind}
    return rec


def _tool(name: str, ts: str, **extra) -> dict:
    return {"type": "assistant", "timestamp": ts,
            "message": {"model": "m", "content": [{"type": "tool_use", "name": name, "input": {}}]},
            **extra}


def _write_jsonl(path: Path, records: list) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for rec in records:
            handle.write((rec if isinstance(rec, str) else json.dumps(rec,
            ensure_ascii=False)) + "\n")
    return path


class _Runner:
    def __call__(self, argv, *, cwd=None, env=None, creationflags=0, wait=True):
        return (0, "main\n" if "--abbrev-ref" in argv else "", None)


class _Roster:
    def snapshot(self, session_id=None, **_kw):
        return {"session": session_id}

    def render_snapshot(self, snap) -> str:
        return f"（假名冊 {snap['session']}）"


def _quota(_now):
    axis = types.SimpleNamespace(kind="five_hour", pct=1.0, resets_at="x")
    return types.SimpleNamespace(axes=(axis,), measured_at="m", source="s")


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="seal-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.base = self.tmp / "handoff"
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.transcript = _write_jsonl(self.tmp / f"{SID}.jsonl", [
            _rec("human", "第一則：請做 A", "2026-11-17T01:00:00Z"),
            _rec("human", "<task-notification>x</task-notification>", "2026-11-17T01:01:00Z"),
            _rec("human", "第二則\n## 已驗證\n夾帶標題行", "2026-11-17T01:02:00Z"),
        ])

    def package(self, main: str = FULL_MAIN) -> Path:
        path = handoff.ensure_mechanical(
            SID, self.transcript, repo=self.repo, now=NOW - timedelta(hours=5), env={},
            base=self.base, runner=_Runner(), roster_mod=_Roster(), quota_fn=_quota,
            temp_root=self.tmp / "none")
        head = path.read_text(encoding="utf-8").split(handoff.MAIN_MARK)[0]
        path.write_text(f"{head}{handoff.MAIN_MARK}\n\n{main}\n", encoding="utf-8")
        return path

    def do_seal(self, path: Path, now: datetime = NOW):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            return seal.seal(path, transcript=self.transcript, repo=self.repo, now=now, env={},
                             runner=_Runner(), roster_mod=_Roster(), quota_fn=_quota,
                             temp_root=self.tmp / "none")


class TranscriptCriteriaTest(unittest.TestCase):
    def test_is_machine_prompt_table(self) -> None:
        """機器注入只認具名的 harness 包裝；掌舵者貼上的長指令（`<pasted_content …>` 開頭，
        2026-11-16 sid 70f1bbb5 的本輪任務書即此形態）、帶圖提示、slash 指令都是人的意圖，
        交接包不得漏收——把它們當機器提示＝接續時掉資訊。"""
        for text in ("", "   \n", "<task-notification>x", "  <system-reminder>", "<command-name>x",
                     "<local-command-stdout>x"):
            self.assertTrue(ta.is_machine_prompt(text), repr(text))
        for text in ("請繼續", "a < b 的問題", "說明 /compact 是什麼", "/compact",
                     '<pasted_content id="cdda">\n以 AISDLC 的程序…', "看這張 [Image #1]",
                     "<div>這段 HTML 壞了</div>"):
            self.assertFalse(ta.is_machine_prompt(text), repr(text))

    def test_is_forwardable_prompt_passes_through_whatever_it_cannot_judge(self) -> None:
        """轉送會擋下人的輸入，所以方向相反：判不出來就不轉送。貼上內容可轉（純文字）；
        其他 `<` 開頭（可能是未知包裝）、slash 指令、圖片（檔案帶不走）、機器注入皆不轉。"""
        for text in ("請繼續", '<pasted_content id="x">\n長指令', "說明 /compact 是什麼"):
            self.assertTrue(ta.is_forwardable_prompt(text), repr(text))
        for text in ("", "<task-notification>x", "<未知包裝>y", "/compact", "看這張 [Image #1]",
                     "[Pasted image 2] 這個"):
            self.assertFalse(ta.is_forwardable_prompt(text), repr(text))

    def test_all_human_prompts_full_text_in_order_with_lines(self) -> None:
        """封存要收「全部」真人提示且不截斷（舊版只收最後 3 則、每則 2,000 字）；帶行號供回頭追。"""
        tmp = tempfile.TemporaryDirectory(prefix="ta-")
        self.addCleanup(tmp.cleanup)
        long = "長" * 5000
        path = _write_jsonl(Path(tmp.name) / "t.jsonl", [
            _rec("human", "一", "2026-11-17T01:00:00Z"),
            "{半截壞行",
            _rec("human", "<system-reminder>x", "2026-11-17T01:01:00Z"),
            _rec("human", long, "2026-11-17T01:02:00Z"),
            _rec("human", "meta", "2026-11-17T01:03:00Z", isMeta=True),
            _rec("agent", "非真人", "2026-11-17T01:04:00Z"),
            _rec("human", "[Image #1] 圖", "2026-11-17T01:05:00Z"),
        ])
        got = ta.all_human_prompts(path)
        self.assertEqual([p["text"] for p in got], ["一", long, "[Image #1] 圖"])
        self.assertEqual([p["line"] for p in got], [1, 4, 7])
        self.assertEqual(got[0]["at"], "2026-11-17T01:00:00Z")
        self.assertEqual(ta.all_human_prompts(Path(tmp.name) / "none.jsonl"), [])
        self.assertEqual(ta.all_human_prompts(None), [])

    def test_last_prompt_at_counts_task_notification_but_not_tool_results(self) -> None:
        """背景任務回報也會開新回合 ⇒ 算提示；tool_result 型 user 與 isMeta 不算。"""
        tmp = tempfile.TemporaryDirectory(prefix="ta-")
        self.addCleanup(tmp.cleanup)
        path = _write_jsonl(Path(tmp.name) / "t.jsonl", [
            _rec("human", "真人", "2026-11-17T01:00:00Z"),
            _rec("task-notification", "<task-notification>d</task-notification>",
                 "2026-11-17T02:00:00Z"),
            _rec("", [{"type": "tool_result", "content": "x"}], "2026-11-17T03:00:00Z"),
            _rec("human", "meta", "2026-11-17T04:00:00Z", isMeta=True),
        ])
        got = ta.last_prompt_at(path)
        self.assertEqual(got.timestamp(), datetime(2026, 11, 17, 2, 0, tzinfo=UTC).timestamp())
        self.assertIsNone(ta.last_prompt_at(Path(tmp.name) / "none.jsonl"))

    def test_worked_since_ignores_read_only_tools_and_old_and_sidechain(self) -> None:
        """A-1：封存後只做唯讀（回答追問）不算工作；改動型工具才算；封存前的不算；子代理記錄不算。
        """
        tmp = tempfile.TemporaryDirectory(prefix="ta-")
        self.addCleanup(tmp.cleanup)
        since = "2026-11-17T02:00:00Z"
        tdir = Path(tmp.name)
        only_read = _write_jsonl(tdir / "r.jsonl", [
            _tool("Edit", "2026-11-17T01:00:00Z"),  # 封存前
            _tool("Read", "2026-11-17T03:00:00Z"), _tool("Grep", "2026-11-17T03:01:00Z"),
            _tool("Glob", "2026-11-17T03:02:00Z"),
            _tool("Write", "2026-11-17T03:03:00Z", isSidechain=True)])
        self.assertFalse(ta.worked_since(only_read, since))
        edited = _write_jsonl(tdir / "e.jsonl", [_tool("Read", "2026-11-17T03:00:00Z"),
                                                _tool("PowerShell", "2026-11-17T03:05:00Z")])
        self.assertTrue(ta.worked_since(edited, since))
        self.assertTrue(ta.worked_since(
            _write_jsonl(tdir / "m.jsonl", [_tool("mcp__x__y", "2026-11-17T03:05:00Z")]), since))

    def test_worked_since_unreadable_or_bad_since_is_false_the_release_direction(self) -> None:
        """讀不到／since 壞 ⇒ False（偏放行：寧可少推回封存也不誤擋人）。"""
        tmp = tempfile.TemporaryDirectory(prefix="ta-")
        self.addCleanup(tmp.cleanup)
        path = _write_jsonl(Path(tmp.name) / "e.jsonl", [_tool("Edit", "2026-11-17T03:05:00Z")])
        self.assertFalse(ta.worked_since(Path(tmp.name) / "none.jsonl", "2026-11-17T02:00:00Z"))
        self.assertFalse(ta.worked_since(path, "not-a-time"))
        self.assertFalse(ta.worked_since(None, "2026-11-17T02:00:00Z"))


class SealTest(_Base):
    def test_seal_rebuilds_mechanical_keeps_main_and_writes_sidecar_and_stamp(self) -> None:
        """AT-S3：封存當下重建機械層（產生時刻＝本次，不是 5 小時前 advise 的舊快照）；
        主控層逐字不動；
        sidecar 收全部真人提示；封存戳最後寫、帶 offset。"""
        path = self.package()
        main_before = path.read_text(encoding="utf-8").split(handoff.MAIN_MARK, 1)[1]
        rc, problems = self.do_seal(path)
        self.assertEqual((rc, problems), (0, []))
        text = path.read_text(encoding="utf-8")
        self.assertIn(f"- 產生時刻：{NOW.astimezone().isoformat()}", text)
        self.assertEqual(text.split(handoff.MAIN_MARK, 1)[1], main_before, "主控層必須逐字保留")
        self.assertIn(f"全文見 {path.stem}.prompts.md", text)
        side = seal.sidecar_path(path).read_text(encoding="utf-8")
        self.assertIn("第一則：請做 A", side)
        self.assertIn("## 已驗證\n夾帶標題行", side)
        self.assertEqual([x for x in side.splitlines() if "task-notification" in x], [])
        self.assertIn("共 2 則", side)
        self.assertEqual(datetime.fromisoformat(
            seal.sealed_path(path).read_text(encoding="utf-8").strip()), NOW)

    def test_seal_with_todo_returns_rc1_and_writes_nothing(self) -> None:
        """AT-S5：主控層仍有 TODO ⇒ rc≠0、列缺項；`.sealed`、sidecar、機械層重建皆不得發生
        （半成品被誤認為已交棒，比沒有封存更糟）。"""
        path = self.package(FULL_MAIN.replace("內容 0", "TODO: 還沒寫"))
        before = path.read_text(encoding="utf-8")
        rc, problems = self.do_seal(path)
        self.assertEqual(rc, 1)
        self.assertTrue(any("TODO" in p for p in problems))
        self.assertFalse(seal.sealed_path(path).exists())
        self.assertFalse(seal.sidecar_path(path).exists())
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_finalize_stays_a_pure_check_with_no_side_effects(self) -> None:
        """`handoff.finalize` 是 converge／park／announce 的「寫完了沒」判準；不得因為升級產生寫檔
        副作用（否則公告或收斂閘每跑一次就重新封存）。"""
        path = self.package()
        snapshot = sorted(p.name for p in self.base.iterdir())
        self.assertEqual(handoff.finalize(path), (0, []))
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), snapshot)

    def test_cli_finalize_goes_through_seal(self) -> None:
        """CLI `--finalize` 走封存（否則封存戳永遠不會被寫）。"""
        with unittest.mock.patch.object(seal, "seal", return_value=(0, [])) as fake, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(handoff.cli(["--finalize", "x.md"]), 0)
        fake.assert_called_once_with("x.md")

    def test_sidecar_over_limit_keeps_first_and_last_ten_full_and_indexes_the_middle(self) -> None:
        """AT-S4：總字數 > 60,000 ⇒ 第一則＋最後 10 則全文，中段只列時刻＋前 200 字＋行號。"""
        prompts = [{"text": f"P{i}" + "字" * 6000, "at": f"T{i}", "line": i + 1} for i in range(15)]
        side = seal.render_prompts(SID, prompts, NOW)
        self.assertIn("字" * 6000, side.split("## 提示 2")[0], "第一則全文")
        for i in (0, 5, 14):  # 第一則、最後 10 則的最早一則（index 4 之後）、最後一則
            self.assertIn(f"P{i}" + "字" * 6000, side)
        self.assertNotIn("P1" + "字" * 6000, side, "中段不得全文")
        self.assertIn("P1" + "字" * (seal.MIDDLE_PREVIEW - 2) + "…", side)
        self.assertIn("逐字稿第 2 行", side)
        small = seal.render_prompts(SID, prompts[:3], NOW)
        self.assertNotIn("中段只列", small)

    def test_refresh_prompts_rewrites_only_the_sidecar(self) -> None:
        """A-2：轉送時補打的提示要進 sidecar，但不動交接包本體與封存戳。"""
        path = self.package()
        self.do_seal(path)
        body = path.read_text(encoding="utf-8")
        stamp = seal.sealed_path(path).read_text(encoding="utf-8")
        with self.transcript.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(_rec("human", "封存後才打的第三則", "2026-11-17T02:00:00Z"),
                                    ensure_ascii=False) + "\n")
        self.assertEqual(seal.refresh_prompts(path, transcript=self.transcript, now=NOW),
        seal.sidecar_path(path))
        self.assertIn("封存後才打的第三則", seal.sidecar_path(path).read_text(encoding="utf-8"))
        self.assertEqual(path.read_text(encoding="utf-8"), body)
        self.assertEqual(seal.sealed_path(path).read_text(encoding="utf-8"), stamp)


class IsSealedTest(_Base):
    def test_is_sealed_requires_stamp_on_latest_package_and_honors_since(self) -> None:
        """封存閘的判準輸入：最新包有封存戳，且戳 ≥ since（本回合起點之後才封存過才算）。"""
        env = {handoff.endurance_env.HANDOFF_DIR_ENV: str(self.base)}
        self.assertFalse(seal.is_sealed(SID, base=self.base, env=env), "沒有包")
        path = self.package()
        self.assertFalse(seal.is_sealed(SID, base=self.base, env=env), "有包沒戳")
        self.assertEqual(self.do_seal(path)[0], 0)
        self.assertTrue(seal.is_sealed(SID, base=self.base, env=env))
        self.assertTrue(seal.is_sealed(SID, NOW - timedelta(minutes=1), base=self.base, env=env))
        self.assertTrue(seal.is_sealed(SID, (NOW - timedelta(minutes=1)).isoformat(),
                                       base=self.base, env=env))
        self.assertFalse(seal.is_sealed(SID, NOW + timedelta(seconds=1), base=self.base, env=env))
        self.assertFalse(seal.is_sealed("other-sid", base=self.base, env=env))

    def test_is_sealed_corrupt_stamp_is_false(self) -> None:
        path = self.package()
        seal.sealed_path(path).write_text("garbage", encoding="utf-8")
        self.assertFalse(seal.is_sealed(SID, base=self.base, env={}))


class SelfResumeTest(_Base):
    """tools/lib/sessionctl/seal.py::mark_resumed／handed_over／wake_package：同一個 session 自己
    續跑不是交棒（R216 QA P2-1，暴露證據＝sid 31ea79d4 自續跑後 Stop 冷叫醒閘推回兩次）。

    WHY：交接包語意是「這個 session 交給別人」。舊版只看有沒有 `.ack`，原主人續跑後 handed_over
    恆真 ⇒ keepwarm 判 handed_over 失效、冷叫醒閘叫它 TaskStop 在飛代理、封存閘失效。"""

    def setUp(self) -> None:
        super().setUp()
        self.env = {handoff.endurance_env.HANDOFF_DIR_ENV: str(self.base)}
        patch = unittest.mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "traces"),
            handoff.endurance_env.HANDOFF_DIR_ENV: str(self.base)})
        patch.start()
        self.addCleanup(patch.stop)
        self.pkg = self.package()
        self.assertEqual(self.do_seal(self.pkg)[0], 0)
        self.assertEqual(seal.wake_package(SID, self.env), self.pkg, "前提：已封存的 live 包")

    def ack(self, text: str) -> None:
        self.pkg.with_suffix(".ack").write_text(text, encoding="utf-8")

    def test_an_ack_by_the_owner_is_not_a_hand_over_but_another_sid_or_legacy_is(self) -> None:
        """三格：自己的 sid ⇒ 否；別的 sid ⇒ 是；舊格式（沒記 sid）無從分辨 ⇒ 保守視為別人接手。"""
        self.ack(f"acked x sid={SID}\n")
        self.assertIsNone(seal.handed_over(SID, self.env))
        self.ack("acked x sid=other-sid\n")
        self.assertEqual(seal.handed_over(SID, self.env), self.pkg)
        self.ack("acked x\n")
        self.assertEqual(seal.handed_over(SID, self.env), self.pkg)

    def test_mark_resumed_voids_the_seal_and_every_consumer_sees_it(self) -> None:
        """續跑後：封存作廢（forward／封存閘的輸入）、包狀態 resumed（不再被公告、不是 live，所以
        冷叫醒閘的 wake_package 也不認）、handed_over 否。"""
        self.assertTrue(seal.is_sealed(SID, base=self.base, env=self.env))
        self.assertTrue(seal.mark_resumed(self.pkg))
        self.assertFalse(seal.is_sealed(SID, base=self.base, env=self.env))
        self.assertFalse(seal.sealed_path(self.pkg).exists())
        self.assertEqual(handoff.list_handoffs(self.base)[-1]["state"], "resumed")
        self.assertIsNone(seal.handed_over(SID, self.env))
        self.assertIsNone(seal.wake_package(SID, self.env))
        self.assertTrue(seal.mark_resumed(self.pkg), "冪等：重做一次不得出錯")

    def test_mark_resumed_clears_only_the_owners_own_ack(self) -> None:
        """R216 複審 P3-a：只清自己 sid 的 `.ack`；別的 sid 的 `.ack` 是真的被接手過、舊格式（沒記
        sid）無從分辨，兩者都保留——續跑不得抹掉真交棒的證據。WHY：舊版把舊格式也刪，而
        `handed_over` 對舊格式保守視為別人接手，兩處不一致 ⇒「先被別人舊格式 ack、原主人再自續跑」
        會被誤判未交棒＝雙駕駛。`handed_over` 與 `mark_resumed` 必須對同一種 ack 給同一個答案。"""
        for text, kept in ((f"acked x sid={SID}\n", False), ("acked x\n", True),
                           ("acked x sid=other-sid\n", True)):
            with self.subTest(text=text):
                self.ack(text)
                self.assertTrue(seal.mark_resumed(self.pkg))
                self.assertEqual(self.pkg.with_suffix(".ack").exists(), kept)
                self.assertEqual(seal.handed_over(SID, self.env) is not None, kept,
                                 "保留的 ack 就必須仍被判已交棒（兩處判準一致）")
                self.pkg.with_suffix(".ack").unlink(missing_ok=True)

    def test_legacy_ack_predicate_only_matches_an_ack_without_sid(self) -> None:
        """`seal.legacy_ack`（供 `--ack` 提示）：只認「有 .ack 沒記 sid」；有 sid／無 ack 皆否。"""
        self.ack("acked x\n")
        self.assertTrue(seal.legacy_ack(self.pkg))
        self.ack(f"acked x sid={SID}\n")
        self.assertFalse(seal.legacy_ack(self.pkg))
        self.pkg.with_suffix(".ack").unlink()
        self.assertFalse(seal.legacy_ack(self.pkg))

    def test_a_real_spawn_trace_stays_a_hand_over_even_after_a_resume_mark(self) -> None:
        """反向變體：spawn 痕跡＝新視窗真的開過，不因原 session 的續跑標記而消失。"""
        from lib.sessionctl import switch  # noqa: PLC0415
        switch.trace("session_switch_spawned", handoff=str(self.pkg), sid=SID, ok=True, pid=1)
        seal.mark_resumed(self.pkg)
        self.assertEqual(seal.handed_over(SID, self.env), self.pkg)

    def test_sealing_again_after_a_resume_rearms_the_package(self) -> None:
        """WHY：續跑後上下文再長到硬線會被封存閘推去重封存；`seal()` 寫戳時清掉 `.resumed`，
        包回到 live＋已封存，之後的冷叫醒／轉送照常運作。"""
        seal.mark_resumed(self.pkg)
        self.assertEqual(self.do_seal(self.pkg)[0], 0)
        self.assertFalse(seal.resumed_path(self.pkg).exists())
        self.assertEqual(seal.wake_package(SID, self.env), self.pkg)


if __name__ == "__main__":
    unittest.main()
