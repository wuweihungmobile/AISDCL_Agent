"""improving_113 W2：resume_cost（喚醒成本落帳）的回歸鎖——首個請求的三個 usage 欄與 model 取自
同一筆真 assistant 且不互混；量不到一律 measured 為假、數值欄是 None 而不是 0；痕跡只在 claude
真的跑過才長、append 不掉行；settle_window 接線；被測模組不得 import 額度閘（防成環）。
"""
from __future__ import annotations

import ast
import contextlib
import json
import os
import sys
import tempfile
import types
import unittest
import unittest.mock
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import endurance_env  # noqa: E402
import quota_policy  # noqa: E402
import relay_machine  # noqa: E402
import resume_cost  # noqa: E402

import session_resume_planner as planner  # noqa: E402

_NUM = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
_RESET = datetime(2026, 10, 10, 3, 0, tzinfo=timezone(timedelta(hours=8)))


def _row(minutes: float, usage: dict | None, model: object = "claude-sonnet-5-5") -> str:
    """reset 前後 minutes 分鐘的一行 assistant 記錄（時間戳走 UTC 的 Z 後綴，同真逐字稿）。"""
    when = (_RESET + timedelta(minutes=minutes)).astimezone(UTC)
    message = {**({} if model is None else {"model": model}),
               **({} if usage is None else {"usage": usage})}
    return json.dumps({"type": "assistant", "message": message,
                       "timestamp": when.strftime("%Y-%m-%dT%H:%M:%S.000Z")})


def _use(i: int, cc: int, cr: int) -> dict:
    return {**dict(zip(_NUM, (i, cc, cr))), "output_tokens": 9}


#: 兩筆窗前真請求 → 半截壞行 → 撞線合成訊息（零 usage）→ 非 assistant → 本窗首筆 → 本窗次筆。
_LINES = [_row(-120, _use(7, 1, 1)), _row(-90, _use(5, 100, 1000)), "{半截尾行",
          _row(-60, _use(0, 0, 0), "<synthetic>"),
          json.dumps({"type": "user", "timestamp": "2026-10-09T19:01:00.000Z"}),
          _row(5, _use(3, 70000, 111), "claude-fable-5-1"), _row(9, _use(4, 1, 2))]


class ResumeCostTest(unittest.TestCase):
    def _tmp(self) -> Path:
        holder = tempfile.TemporaryDirectory(prefix="resume-cost-")
        self.addCleanup(holder.cleanup)
        return Path(holder.name)

    def test_first_request_after_the_last_pre_reset_assistant_is_measured(self) -> None:
        """錨＝最後一筆早於 reset 的真 assistant（合成撞線訊息不算錨）；三欄與 model 取自同一筆。"""
        anchor = resume_cost.last_assistant_before(_LINES, _RESET.isoformat())
        self.assertEqual(anchor, "2026-10-09T17:30:00.000Z", "合成訊息被當成錨了")
        path = self._tmp() / "t.jsonl"
        path.write_text("\n".join(_LINES) + "\n", encoding="utf-8", newline="\n")
        for source in (_LINES, path):  # lines_or_path 兩種入口同一答案
            usage = resume_cost.first_assistant_usage_after(source, anchor)
            rec = resume_cost.build_record("sid", 2, usage, recorded_at="t")
            self.assertEqual([rec[k] for k in _NUM], [3, 70000, 111], "cache 欄互混或被加總")
            self.assertEqual(rec["first_assistant_ts"], "2026-10-09T19:05:00.000Z")
            self.assertEqual([rec[k] for k in ("measured", "session_id", "relay_seq", "model")],
                             [True, "sid", 2, "claude-fable-5-1"])  # model 取自同一筆，非旁筆
        for odd in (None, "", 7):  # 缺鍵／空字串／非字串：取不到 ⇒ None，不猜、不拿空字串頂替
            rows = [_row(-90, _use(5, 100, 1000)), _row(5, _use(3, 70000, 111), odd)]
            bare = resume_cost.first_assistant_usage_after(rows, anchor)
            rec = resume_cost.build_record("sid", 2, bare)
            self.assertEqual([rec["measured"], rec["model"]], [True, None], repr(odd))

    def test_unmeasurable_windows_say_so_and_never_write_zero(self) -> None:
        """無 usage／逐字稿缺席／無 assistant／全零佔位 ⇒ measured 為假，數值欄是 None。"""
        tmp, state = self._tmp(), {"session_id": "s", "reset_at": _RESET.isoformat()}
        out, late = tmp / "out.jsonl", tmp / "late.jsonl"  # late：窗前沒有任何真請求可當錨
        late.write_text(_row(5, _use(3, 7, 9)) + "\n", encoding="utf-8", newline="\n")
        junk = resume_cost.first_assistant_usage_after(
            [_row(5, None), _row(6, _use(0, 0, 0), "<synthetic>")], None)
        recs = [resume_cost.build_record("s", 0, None),
                resume_cost.build_record("s", 0, {"ts": "t", **dict.fromkeys(_NUM, 0)}),
                resume_cost.build_record("s", 0, junk),
                resume_cost.build_record("s", 0, {"ts": "t", "input_tokens": True}),
                resume_cost.record_window({**state, "transcript": str(tmp / "x")}, out),
                resume_cost.record_window({**state, "transcript": str(late)}, out),
                resume_cost.record_window({**state, "transcript": ""}, out),
                resume_cost.record_window({**state, "transcript": str(late), "reset_at": ""}, out)]
        with unittest.mock.patch.object(resume_cost, "_locate", side_effect=RuntimeError("boom")):
            recs.append(resume_cost.record_window(state, out))  # 例外必須被吞並留下說明
        self.assertIsNone(junk)
        self.assertEqual([r["reason"] for r in recs][4:8],
                         ["transcript-missing", "no-anchor", "transcript-missing", "no-anchor"])
        self.assertEqual(recs[-1]["reason"], "error:RuntimeError")
        for rec in recs:
            self.assertIs(rec["measured"], False, rec)
            self.assertEqual([rec[k] for k in (*_NUM, "model")], [None] * 4, "量不到被寫成 0")
            self.assertTrue(rec["reason"], "量不到必須說明原因")
        self.assertEqual(len(out.read_text(encoding="utf-8").splitlines()), 5)
        half = resume_cost.build_record("s", 0, {"ts": "t", "input_tokens": 1}, pct_before=3.0)
        self.assertEqual([half[k] for k in ("pct_before", "pct_after", *_NUM[1:])], [None] * 4)

    def test_sequential_appends_keep_every_line_parseable(self) -> None:
        path = self._tmp() / "deep" / "dir" / "cost.jsonl"  # 父目錄不存在也要寫得進去
        recs = [resume_cost.build_record(f"s{i}", i, None, reason=f"原因{i}") for i in range(20)]
        for rec in recs:
            self.assertTrue(resume_cost.append_cost_record(rec, path))
        raw = path.read_bytes()
        self.assertTrue(raw.endswith(b"\n") and b"\r" not in raw)
        self.assertEqual([json.loads(ln) for ln in raw.decode("utf-8").splitlines()], recs)

    def _settle(self, tmp: Path, next_step: str = "", **extra) -> int:
        """跑真的 settle_window：planner 的排程／告警／重掛換成替身，接線與 resume_cost 照跑。"""
        plan, hb = tmp / "plan.md", tmp / "hb.md"
        hb.write_text(f"## 下一步指令\n{next_step}\n", encoding="utf-8", newline="\n")  # 空⇒DONE
        state = {"session_id": "sid-w2", "relay_seq": 0, "task_name": "T", "plan_path": str(plan),
                 "transcript": str(tmp / "t.jsonl"), "reset_at": _RESET.isoformat(),
                 "handback_verdict": "written", "handback_path": str(hb),
                 "files_changed": 1, **extra}
        patch, env = unittest.mock.patch.object, {endurance_env.TRACE_DIR_ENV: str(tmp / "tr")}
        with contextlib.ExitStack() as stack:
            for name, ret in (("append_log", None), ("write_relay", None), ("_schtasks_remove", 0),
                              ("_arm_sentinel", 0), ("_register_and_record", (0, "ok"))):
                stack.enter_context(patch(planner, name, return_value=ret))
            stack.enter_context(patch(planner.escalation, "alert", return_value={}))
            stack.enter_context(patch(relay_machine, "current_band",
                                      return_value=quota_policy.BAND_FREE))
            stack.enter_context(unittest.mock.patch.dict(os.environ, env))
            return relay_machine.settle_window(types.SimpleNamespace(task_name="T"), state,
                                               plan, tmp / "log.jsonl", 0)

    def test_settle_window_logs_one_row_per_real_wake_and_nothing_otherwise(self) -> None:
        tmp = self._tmp()
        (tmp / "t.jsonl").write_text("\n".join(_LINES) + "\n", encoding="utf-8", newline="\n")
        trace = tmp / "tr" / resume_cost.RECORD_NAME

        def rows() -> list[dict]:
            return [json.loads(ln) for ln in trace.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(self._settle(tmp, state="resume_failed"), 0, "既有回傳契約被接線改壞")
        self.assertFalse(trace.exists(), "claude 沒跑（零喚醒）卻長出了痕跡")
        self.assertEqual(self._settle(tmp, state="resumed"), 0)
        (r,) = rows()  # 恰一行
        self.assertEqual([r[k] for k in ("session_id", "relay_seq", "measured", *_NUM, "model")],
                         ["sid-w2", 0, True, 3, 70000, 111, "claude-fable-5-1"])
        size = trace.stat().st_size
        self._settle(tmp, state="resume_failed")
        self.assertEqual(trace.stat().st_size, size, "零喚醒讓痕跡檔位元組數變了")
        self._settle(tmp, state="resumed", relay_seq=1)  # 接力窗：reset 錨會抓到第一窗首筆
        chained = rows()[1]
        self.assertEqual([chained["measured"], chained["reason"]], [False, "relay-chain-anchor"])
        self.assertEqual([chained[k] for k in (*_NUM, "model")], [None] * 4)
        self._settle(tmp, next_step="還有第 4 步", state="resumed")  # RELAY_NEXT：序號會 +1
        self.assertEqual([rows()[2]["relay_seq"], rows()[2]["measured"]], [0, True], "序號取晚了")

    def test_a_relay_window_is_measured_from_its_own_spawn_not_from_reset_at(self) -> None:
        """接力窗（relay_seq=1）的首請求從本窗 spawn 時刻起算（planner 在 subprocess.run 前落的
        relay_snapshot_before 的 at），不是 reset_at——reset 錨會抓到第一窗首筆（3, 70000, 111）。"""
        tmp = self._tmp()
        (tmp / "t.jsonl").write_text("\n".join(_LINES) + "\n", encoding="utf-8", newline="\n")
        at = (_RESET + timedelta(minutes=7)).isoformat(timespec="seconds")  # 兩筆請求之間
        event = {"event": "relay_snapshot_before", "at": at}
        (tmp / "log.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8", newline="\n")
        self._settle(tmp, state="resumed", relay_seq=1)
        (row,) = [json.loads(ln) for ln in
                  (tmp / "tr" / resume_cost.RECORD_NAME).read_text(encoding="utf-8").splitlines()]
        self.assertEqual([row["measured"], *(row[k] for k in _NUM)], [True, 4, 1, 2],
                         "接力窗仍以 reset_at 為錨（spawn 錨沒接上）")

    def test_resume_cost_never_imports_the_quota_gate_family(self) -> None:
        """AST 防成環鎖（含函式內延遲 import 與字串動態載入）；先證判準有牙再判真檔。"""
        def banned(src: str) -> list[str]:
            names = set()
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, ast.Import):
                    names.update(a.name for a in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names.update([node.module or "", *(a.name for a in node.names)])
                elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                    names.add(node.value)
            return sorted({seg for n in names for seg in n.split(".")}
                          & {"quota_gate", "quota_escalation"})

        for bad in ("import quota_gate", "from lib import quota_escalation",
                    "def f():\n    from quota_escalation import x",
                    "import importlib\nimportlib.import_module('quota_gate')"):
            self.assertTrue(banned(bad), f"判準沒有牙：{bad!r}")
        source = Path(resume_cost.__file__).read_text(encoding="utf-8")
        self.assertEqual(banned(source), [], "resume_cost 反向依賴額度閘＝成環風險")


if __name__ == "__main__":
    unittest.main()
