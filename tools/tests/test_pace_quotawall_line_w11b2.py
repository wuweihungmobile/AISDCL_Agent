"""AT-QW-93／MU-QW-62／E2E-QW-36（W11b 後半）：`--pace` 的 `QUOTAWALL_PLAN=` 行（REQ-QW-79）。"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from lib.sessionctl import qw_cli, qw_plan  # noqa: E402

PLANNER = ROOT / "tools" / "session_resume_planner.py"
SID = "7e57ab1e-0000-4000-8000-00000000b93a"
NOW = datetime(2026, 11, 23, 10, 2, tzinfo=UTC)


def _axes(five=80.0, five_min=38, week=58.0, week_min=8233):
    return [{"kind": "five_hour", "pct": five, "resets_at": (NOW + timedelta(minutes=five_min)).isoformat()},
            {"kind": "seven_day", "pct": week, "resets_at": (NOW + timedelta(minutes=week_min)).isoformat()}]


class TestPaceLineSeam(unittest.TestCase):
    """AT-QW-93：`qw_cli.pace_line`（planner 唯一呼叫者）的判準——量不到不印、不報錯。"""

    def _state(self):
        import quota_policy as Q
        axes = tuple(Q.Axis(a["kind"], a["pct"], a["resets_at"]) for a in _axes())
        return Q.QuotaState(axes, NOW.isoformat(), "cache")

    def test_prints_the_machine_line_when_measurable(self) -> None:
        line = qw_cli.pace_line(SID, None, {}, now=NOW, read_quota=lambda n: self._state(),
                                refresh=lambda n: None, live_fn=lambda s, t: (0, True))
        self.assertTrue(line.startswith("QUOTAWALL_PLAN=stage="), line)
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(line.count("\n"), 1, "只印一行（機器行）")

    def test_unmeasurable_prints_nothing(self) -> None:
        """無 sid、無人窗口（stage=none）、讀數例外 ⇒ 空字串、不拋。"""
        self.assertEqual(qw_cli.pace_line(None, None, {}, now=NOW), "")
        self.assertEqual(qw_cli.pace_line(SID, None, {"AUTOSDD_UNATTENDED": "1"}, now=NOW), "")

        def boom(_n):
            raise RuntimeError("x")
        self.assertEqual(qw_cli.pace_line(SID, None, {}, now=NOW, read_quota=boom, refresh=boom), "")

    def test_quota_gate_never_imports_sessionctl(self) -> None:
        """MU-QW-62 後半：`quota_gate*` 不得 import `sessionctl`（依賴成環；AST 鎖）。"""
        hits = []
        for p in sorted((ROOT / "tools" / "lib").glob("quota_gate*.py")):
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [(node.module or "")] + [a.name for a in node.names]
                hits += [f"{p.name}:{n}" for n in names if "sessionctl" in n]
        self.assertEqual(hits, [])

    def test_planner_calls_pace_line_in_the_pace_branch(self) -> None:
        """MU-QW-62 前半：planner 的 `--pace` 分支必須呼叫 `qw_cli.pace_line`（缺席即紅）。"""
        src = PLANNER.read_text(encoding="utf-8")
        branch = src[src.index("    if args.pace:"):src.index("# 這三個模式不需要逐字稿")]
        self.assertIn("qw_cli.pace_line(", branch)


class TestPaceRealProcess(unittest.TestCase):
    """E2E-QW-36：真子行程 `session_resume_planner.py --pace`，沙盒快取＝10:00:02 讀數形。"""

    def _run(self, extra_env=None, *, quota=True) -> subprocess.CompletedProcess:
        tmp = Path(tempfile.mkdtemp(prefix="w11b2_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        real = datetime.now().astimezone()
        qdir = tmp / "qcache"
        qdir.mkdir()
        if quota:
            axes = [{"kind": "five_hour", "pct": 80, "via": "t",
                     "resets_at": (real + timedelta(minutes=38)).isoformat(timespec="seconds")},
                    {"kind": "seven_day", "pct": 58, "via": "t",
                     "resets_at": (real + timedelta(minutes=8233)).isoformat(timespec="seconds")}]
            (qdir / "autosdd_quota.json").write_text(json.dumps(
                {"schema": "autosdd.quota/2", "source": "endpoint", "http_status": 200,
                 "measured_at": real.isoformat(timespec="seconds"), "axes": axes}), encoding="utf-8")
        tr = tmp / f"{SID}.jsonl"
        tr.write_text(json.dumps({"type": "user", "sessionId": SID, "timestamp": real.isoformat(),
                                  "message": {"role": "user", "content": "hi"}}) + "\n", encoding="utf-8")
        env = {**os.environ, "AUTOSDD_QUOTA_CACHE_DIR": str(qdir), "AUTOSDD_TRACE_DIR": str(tmp / "traces"),
               "TEMP": str(tmp), "TMP": str(tmp), "TMPDIR": str(tmp), "PYTHONDONTWRITEBYTECODE": "1",
               "AUTOSDD_SESSION_SWITCH_MODE": "auto", "AUTOSDD_QUOTA_PACE_FLOOR_OFF": "1"}
        env.pop("AUTOSDD_UNATTENDED", None)
        env.update(extra_env or {})
        return subprocess.run([sys.executable, str(PLANNER), "--pace", "--model", "sonnet",
                               "--transcript", str(tr)], cwd=str(tmp), env=env, capture_output=True,
                              timeout=120, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def test_pace_prints_short_window_and_quotawall_lines(self) -> None:
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("短窗=converge five_hour 80%", r.stdout)
        plan = [ln for ln in r.stdout.splitlines() if ln.startswith("QUOTAWALL_PLAN=")]
        self.assertEqual(len(plan), 1, r.stdout + r.stderr)
        self.assertNotIn(qw_plan.NONE + " reason", plan[0])

    def test_unmeasurable_prints_no_line_and_same_rc(self) -> None:
        """無額度快取＋無人窗口（plan 自判 none）⇒ 不出 QW 行、rc 與 r8 相同（0）。"""
        r = self._run({"AUTOSDD_UNATTENDED": "1"}, quota=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("QUOTAWALL_PLAN=", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


if __name__ == "__main__":
    unittest.main()
