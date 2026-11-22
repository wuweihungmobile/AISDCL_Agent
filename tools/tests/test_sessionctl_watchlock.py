"""tools/lib/sessionctl/watchlock.py：監督單例與心跳 pid 化（W6-W2；Control_Handover_Design §5）。

受測：`watchlock`（單例鎖）、`watch.run` 入口 duplicate 判決與心跳只刪自己的檔、
`supervise.read_heartbeat` 取「任一新鮮」；含真子行程 smoke（兩支 `sessionctl.py watch`）。
痕跡／心跳目錄一律以 `AUTOSDD_TRACE_DIR` 圍到暫存。
"""
from __future__ import annotations

import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import quota_meter  # noqa: E402
import sentinel_lifecycle as SL  # noqa: E402

from lib.sessionctl import holder, supervise, watch, watchlock  # noqa: E402

_FENCES: list[dict] = []


def _kill(pid: int) -> None:
    """結束真 watch 直譯器（Windows 的 venv 啟動器下，Popen 句柄不是它）；已死不拋。"""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
SID = "11111111-2222-3333-4444-555555555555"


def setUpModule() -> None:
    _FENCES.append(SL.fence_enter())


def tearDownModule() -> None:
    SL.fence_exit(_FENCES.pop())


def _beat(pid: int, age_s: float) -> dict:
    now = datetime.now().astimezone()
    return {"schema": "autosdd.watch/1", "pid": pid,
            "started_at": (now - timedelta(minutes=5)).isoformat(timespec="seconds"),
            "heartbeat_at": (now - timedelta(seconds=age_s)).isoformat(timespec="seconds"),
            "keepwarm_at": (now + timedelta(minutes=40)).isoformat(timespec="seconds"),
            "stall_min": 15, "wall_min": 120, "ctx_max": 700000}


class _Fence(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory(prefix="w6w2-")
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        patcher = mock.patch.dict(os.environ, {
            "AUTOSDD_TRACE_DIR": str(self.tmp / "trace"),
            "AUTOSDD_HANDOFF_DIR": str(self.tmp / "handoff"),
            "AUTOSDD_QUOTA_CACHE_DIR": str(self.tmp / "quota")})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("AUTOSDD_UNATTENDED", None)
        (self.tmp / "trace" / "watch").mkdir(parents=True)

    def put_beat(self, name: str, pid: int, age_s: float) -> Path:
        path = self.tmp / "trace" / "watch" / name
        path.write_text(json.dumps(_beat(pid, age_s)), encoding="utf-8")
        return path


class WatchLockTests(_Fence):
    """tools/lib/sessionctl/watchlock.py：同 sid 單例（AT：第二支被拒、陳舊可接手、只釋放自己）。"""

    def test_second_acquirer_is_refused_while_first_lives(self) -> None:
        """WHY：兩支 watch 同時掛＝一次 TaskStop 停兩支、先結束者動共用狀態（A3 真事故）。"""
        alive = lambda pid: True  # noqa: E731
        self.assertTrue(watchlock.acquire(SID, 100, alive=alive, token=lambda p: "t"))
        self.assertFalse(watchlock.acquire(SID, 200, alive=alive, token=lambda p: "t"))
        self.assertEqual(watchlock.read(SID)["pid"], 100)

    def test_stale_or_pid_reused_holder_is_taken_over(self) -> None:
        """WHY：持有者死亡或 pid 被別的行程重用（建立時間不同）時，鎖不能永遠卡住監督。"""
        self.assertTrue(watchlock.acquire(SID, 100, alive=lambda p: True, token=lambda p: "old"))
        self.assertTrue(watchlock.acquire(SID, 200, alive=lambda p: p != 100, token=lambda p: "n"))
        self.assertEqual(watchlock.read(SID)["pid"], 200)
        self.assertTrue(watchlock.acquire(SID, 300, alive=lambda p: True, token=lambda p: "reused"))
        self.assertEqual(watchlock.read(SID)["pid"], 300)

    def test_release_only_drops_own_record(self) -> None:
        """WHY：別人接手後，我們遲到的收尾不得刪掉對方的鎖。"""
        watchlock.acquire(SID, 100, alive=lambda p: True, token=lambda p: "t")
        watchlock.release(SID, 999)
        self.assertIsNotNone(watchlock.read(SID))
        watchlock.release(SID, 100)
        self.assertIsNone(watchlock.read(SID))

    def test_unwritable_lock_dir_does_not_block_supervision(self) -> None:
        """WHY：互斥是優化不是前提；鎖檔被目錄佔住（寫不進）時 watch 仍要能跑。"""
        watchlock.path(SID, write=True).mkdir()
        self.assertTrue(watchlock.acquire(SID, 100))


class RunDuplicateTests(_Fence):
    """tools/lib/sessionctl/watch.py：入口 duplicate 判決（rc 0、末行 WATCH_VERDICT=duplicate）。"""

    def test_run_exits_duplicate_when_live_other_holds_the_lock(self) -> None:
        """WHY：判決一律 rc 0（DEF-200-622）；不得動到持有者的鎖與心跳。"""
        me = os.getpid()
        self.assertTrue(watchlock.acquire(SID, me))
        beat = self.put_beat(f"{SID}.{me}.json", me, 1)
        out = io.StringIO()
        rc = watch.run(SID, watch.Cfg(), sleep_fn=lambda s: self.fail("不該進輪詢"), out=out,
                       pid=me + 100000, roster_fn=lambda: [], quota_fn=lambda: None,
                       anchor_fn=lambda: None)
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().strip().splitlines()[-1], "WATCH_VERDICT=duplicate n=0")
        self.assertEqual(watchlock.read(SID)["pid"], me)
        self.assertTrue(beat.exists())

    def test_normal_exit_releases_lock_and_only_own_heartbeat(self) -> None:
        """WHY：先結束者只刪自己的心跳（`<sid>.<pid>.json`），別人的心跳不得被帶走。"""
        other = self.put_beat(f"{SID}.31337.json", 31337, 1)
        clock = [1_800_000_000.0]

        def sleep(sec: float) -> None:
            self.assertTrue(watch.heartbeat_path(SID, 4242).exists())
            clock[0] += 3600

        out = io.StringIO()
        rc = watch.run(SID, watch.Cfg(keepwarm_min=1, wall_min=9999), now_fn=lambda: clock[0],
                       sleep_fn=sleep, out=out, pid=4242, roster_fn=lambda: [],
                       quota_fn=lambda: None, anchor_fn=lambda: None,
                       budget=mock.Mock(check=lambda: ("", 0, 9, 1), charge=lambda *a, **k: True))
        self.assertEqual(rc, 0)
        self.assertFalse(watch.heartbeat_path(SID, 4242).exists())
        self.assertTrue(other.exists())
        self.assertIsNone(watchlock.read(SID))
        names = [p.name for p in (self.tmp / "trace" / "watch").glob(f"{SID}.*json")]
        self.assertEqual(names, [f"{SID}.31337.json"])  # 寫出只有新格式


class ReadHeartbeatTests(_Fence):
    """tools/lib/sessionctl/supervise.py：`read_heartbeat` 取任一新鮮、相容舊格式。"""

    def test_any_fresh_beat_wins_over_newer_stale_looking_one(self) -> None:
        """WHY：一支結束、另一支還在跑時，外界不得因讀到死者殘檔而誤判「無監督」。"""
        self.put_beat(f"{SID}.1.json", 1, 3600)
        self.put_beat(f"{SID}.2.json", 2, 5)
        self.assertEqual(supervise.read_heartbeat(SID)["pid"], 2)

    def test_all_stale_returns_newest_so_caller_judges_stuck(self) -> None:
        """WHY：全部過期仍回最新一份，讓 credential 判 stuck 而不是 none。"""
        self.put_beat(f"{SID}.1.json", 1, 9000)
        self.put_beat(f"{SID}.2.json", 2, 4000)
        self.assertEqual(supervise.read_heartbeat(SID)["pid"], 2)

    def test_legacy_format_still_read_and_none_when_absent(self) -> None:
        """WHY：升級當下仍在跑的舊 watch 只有 `<sid>.json`，相容讀取一輪。"""
        self.assertIsNone(supervise.read_heartbeat(SID))
        self.put_beat(f"{SID}.json", 7, 5)
        self.assertEqual(supervise.read_heartbeat(SID)["pid"], 7)

    def test_corrupt_only_raises_but_corrupt_beside_good_is_skipped(self) -> None:
        """WHY：壞檔單獨存在維持舊契約（拋、呼叫端 fail-open）；有好檔時不被壞檔拖累。"""
        bad = self.tmp / "trace" / "watch" / f"{SID}.9.json"
        bad.write_text("{not json", encoding="utf-8")
        with self.assertRaises(ValueError):
            supervise.read_heartbeat(SID)
        self.put_beat(f"{SID}.2.json", 2, 5)
        self.assertEqual(supervise.read_heartbeat(SID)["pid"], 2)

    def test_other_sid_prefix_is_not_mixed_in(self) -> None:
        """WHY：glob 以 sid＋點分隔，別的 sid 的心跳不得被讀進來。"""
        self.put_beat(f"{SID}x.5.json", 5, 5)
        self.assertIsNone(supervise.read_heartbeat(SID))


class RealProcessSmoke(_Fence):
    """真子行程 smoke：兩支 `tools/sessionctl.py watch`（單例、接手、不刪對方心跳）。"""

    def _seed_low_quota(self) -> None:
        now = datetime.now().astimezone()
        (self.tmp / "quota").mkdir(exist_ok=True)
        axis = {"kind": "five_hour", "pct": 1.0, "via": "test", "resets_at":
                datetime.fromtimestamp(now.timestamp() + 7200).astimezone().isoformat()}
        self.assertTrue(quota_meter.write_cache({"schema": quota_meter.SCHEMA, "axes": [axis],
            "measured_at": now.isoformat(timespec="seconds")}, quota_meter.cache_path()))

    def _spawn(self) -> subprocess.Popen:
        (self.tmp / "projects").mkdir(exist_ok=True)
        env = {**os.environ, "PYTHONUTF8": "1"}
        return subprocess.Popen(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "watch", "--sid", SID,
             "--projects-dir", str(self.tmp / "projects"), "--poll-sec", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)

    def _wait_beat(self, after: set[int], secs: float = 40) -> int:
        """等到出現一支不在 `after` 的 watch 心跳，回其真 pid（venv 啟動器下 Popen.pid 不是
        實際直譯器 pid，所以以心跳檔名為準）。"""
        folder = watch.heartbeat_path(SID, 1).parent
        end = time.time() + secs
        while time.time() < end:
            for path in folder.glob(f"{SID}.*.json"):
                pid = int(path.name.split(".")[-2])
                if pid not in after:
                    return pid
            time.sleep(0.3)
        self.fail("watch 沒在時限內寫出自己的心跳")

    def test_two_real_watches_single_instance_and_takeover(self) -> None:
        """WHY：端到端驗 A3——第二支 rc 0＋duplicate、第一支心跳不受影響；殺第一支後可接手。"""
        self._seed_low_quota()
        first = self._spawn()
        self.addCleanup(lambda: first.poll() is None and first.kill())
        first_pid = self._wait_beat(set())
        self.addCleanup(_kill, first_pid)
        second = subprocess.run(
            [sys.executable, str(_REPO_ROOT / "tools" / "sessionctl.py"), "watch", "--sid", SID,
             "--projects-dir", str(self.tmp / "projects"), "--poll-sec", "1"],
            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
            env={**os.environ, "PYTHONUTF8": "1"})
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(second.stdout.strip().splitlines()[-1], "WATCH_VERDICT=duplicate n=0")
        self.assertTrue(watch.heartbeat_path(SID, first_pid).exists())  # 第二支沒刪第一支的心跳
        self.assertEqual(watchlock.read(SID)["pid"], first_pid)
        first.kill()
        _kill(first_pid)
        first.wait(timeout=20)
        end = time.time() + 20
        while time.time() < end and holder.pid_alive(first_pid):
            time.sleep(0.2)
        third = self._spawn()
        self.addCleanup(lambda: third.poll() is None and third.kill())
        third_pid = self._wait_beat({first_pid})  # 第一支被殺（鎖陳舊）後，新的一支可正常運作
        self.addCleanup(_kill, third_pid)
        self.assertEqual(watchlock.read(SID)["pid"], third_pid)
        self.assertEqual(supervise.read_heartbeat(SID)["pid"], third_pid)


if __name__ == "__main__":
    unittest.main()
