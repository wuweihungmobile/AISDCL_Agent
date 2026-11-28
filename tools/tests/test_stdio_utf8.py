#!/usr/bin/env python3
"""tools/_stdio_utf8.py 的單元測試（R4 複審 QA P3：補齊零測試覆蓋缺口）。

背景：`reconfigure_stdio_utf8()` 是 `dev_start.py` / `check_ntfs_paths.py` /
`check_script_parity.py` 三支根層 CLI 工具共用的 Windows 非 UTF-8 終端崩潰防護
（DEF-101-069），卻從未有任何單元測試鎖住其行為契約：
  1. 對沒有 `reconfigure` 屬性的 stream（如測試用 `io.StringIO()`）必須安全跳過，
     不可拋 AttributeError。
  2. `reconfigure()` 拋 `OSError`/`ValueError` 時必須被吞掉，不可向外傳播（例如被導向
     的 stdout 在某些平台上 reconfigure 會失敗）。
  3. 正常情況下（stream 有 `reconfigure` 且成功）必須真的呼叫到，且帶正確參數
     （`encoding="utf-8", errors="replace"`）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _stdio_utf8 as m  # noqa: E402


class TestReconfigureStdioUtf8(unittest.TestCase):
    def test_stream_without_reconfigure_skipped_safely(self) -> None:
        """StringIO 沒有 reconfigure 屬性 —— hasattr 守門必須讓函式安全跳過，零副作用、
        不拋 AttributeError（docstring 明文承諾的守門行為）。"""
        fake_stdout = io.StringIO()
        fake_stderr = io.StringIO()
        self.assertFalse(hasattr(fake_stdout, "reconfigure"))
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外

    def test_reconfigure_oserror_swallowed(self) -> None:
        """reconfigure() 拋 OSError 時必須被吞掉，不向外傳播。"""
        fake_stdout = mock.Mock()
        fake_stdout.reconfigure.side_effect = OSError("boom")
        fake_stderr = mock.Mock()
        fake_stderr.reconfigure.side_effect = OSError("boom")
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()

    def test_reconfigure_valueerror_swallowed(self) -> None:
        """reconfigure() 拋 ValueError 時同樣必須被吞掉，不向外傳播。"""
        fake_stdout = mock.Mock()
        fake_stdout.reconfigure.side_effect = ValueError("boom")
        fake_stderr = mock.Mock()
        fake_stderr.reconfigure.side_effect = ValueError("boom")
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()  # 不應拋例外
        fake_stdout.reconfigure.assert_called_once()
        fake_stderr.reconfigure.assert_called_once()

    def test_reconfigure_called_with_utf8_when_available(self) -> None:
        """正常情況（stream 有 reconfigure 且成功）必須真的呼叫到，且帶
        encoding="utf-8", errors="replace"（防未來重構悄悄改掉參數）。"""
        fake_stdout = mock.Mock()
        fake_stderr = mock.Mock()
        with mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.reconfigure_stdio_utf8()
        fake_stdout.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")
        fake_stderr.reconfigure.assert_called_once_with(encoding="utf-8", errors="replace")


# ───────────────── WP-SW REQ-CTL-49（AT-CTL-93～96）：pythonw 沒有 std handle ⇒ 綁 devnull
def _old_reconfigure() -> None:
    """修前 `reconfigure_stdio_utf8` 的 None 分支逐字複本（oracle，先證夾具確實觸發舊行為）。"""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            continue


class _StdioNone:
    """`STDIO` 縫：把 sys.stdout／sys.stderr 設為 None（pythonw 的真實形狀）。"""

    def __init__(self) -> None:
        self._ctx = [mock.patch.object(sys, "stdout", None), mock.patch.object(sys, "stderr", None)]

    def __enter__(self):
        for c in self._ctx:
            c.__enter__()
        return self

    def __exit__(self, *exc):
        for c in reversed(self._ctx):
            c.__exit__(*exc)


class WpSwStdioNoneTest(unittest.TestCase):
    def test_at93_none_streams_become_writable_utf8(self) -> None:
        """AT-CTL-93：兩串流皆 None ⇒ 變成可 write／flush 的 utf-8 文字串流；oracle 證舊版會炸。"""
        with _StdioNone():
            _old_reconfigure()
            with self.assertRaises(AttributeError):
                sys.stderr.write("x")  # type: ignore[union-attr]
            m.reconfigure_stdio_utf8()
            for name in ("stdout", "stderr"):
                stream = getattr(sys, name)
                self.assertEqual(stream.encoding, "utf-8")
                stream.write("中文✅\n")
                stream.flush()

    def test_at94_idempotent_one_devnull_object_and_replicas_untouched(self) -> None:
        """AT-CTL-94：連呼兩次同一物件（不重複開檔）；StringIO 替身 no-op。"""
        with _StdioNone():
            m.reconfigure_stdio_utf8()
            first = (sys.stdout, sys.stderr)
            m.reconfigure_stdio_utf8()
            self.assertIs(first[0], sys.stdout)
            self.assertIs(first[1], sys.stderr)
        fake = io.StringIO()
        with mock.patch.object(sys, "stdout", fake), mock.patch.object(sys, "stderr", fake):
            m.reconfigure_stdio_utf8()
            self.assertIs(sys.stdout, fake)

    def test_at95_acctswitch_reconcile_survives_pythonw_stderr(self) -> None:
        """AT-CTL-95：重現 406454ea 10:21:52——舊帳號標記＋新帳號讀數 ⇒ reconcile 作廢標記時
        `sys.stderr.write` 在 pythonw 下不得拋；voided 與 last_switch 已存檔。"""
        import json  # noqa: PLC0415
        import shutil  # noqa: PLC0415
        import tempfile  # noqa: PLC0415
        from datetime import datetime  # noqa: PLC0415
        from types import SimpleNamespace  # noqa: PLC0415

        lib = str(Path(__file__).resolve().parents[1] / "lib")
        tools = str(Path(__file__).resolve().parents[1])
        for p in (tools, lib):
            if p not in sys.path:
                sys.path.insert(0, p)
        import quota_halt_marker  # noqa: PLC0415

        from lib.sessionctl import acctswitch  # noqa: PLC0415

        tmp = Path(tempfile.mkdtemp(prefix="wpsw95_"))
        self.addCleanup(shutil.rmtree, tmp, True)
        env = {"AUTOSDD_TRACE_DIR": str(tmp / "traces"), "TEMP": str(tmp), "TMP": str(tmp),
               "TMPDIR": str(tmp), "AUTOSDD_QUOTA_CACHE_DIR": str(tmp / "cache"),
               "CLAUDE_CONFIG_DIR": str(tmp / "claude"), "AUTOSDD_SESSION_SWITCH_MODE": "auto"}
        sid = "406454ea-91fc-4481-9c11-b28ed7d9e95f"
        now = datetime.now().astimezone()
        policy = SimpleNamespace(halt_pct=100.0)
        state = SimpleNamespace(account_key="34cd3507237f", measured_at=now.isoformat(),
                                axes=(), usable=lambda: False)
        with mock.patch.dict("os.environ", env):
            (tmp / "traces").mkdir(parents=True)
            marker_path = quota_halt_marker.halt_marker_path(sid)
            marker_path.parent.mkdir(parents=True, exist_ok=True)
            marker = {"sid": sid, "band": "halt", "binding": "seven_day", "account": "eaf5241f6fe2"}
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            with _StdioNone():
                m.reconfigure_stdio_utf8()
                voided = acctswitch.reconcile(sid, state, policy, now, halt_marker=marker)
            self.assertEqual(voided, 1)
            probe = acctswitch.load_probe()
            self.assertTrue(probe.get("voiced"))
            self.assertEqual(probe["last_switch"]["new"], "34cd3507237f")
            # oracle：舊 None 分支下同夾具拋 AttributeError 且 voiced 未存
            marker_path.write_text(json.dumps(marker), encoding="utf-8")
            acctswitch.save_probe({})
            with _StdioNone():
                _old_reconfigure()
                with self.assertRaises(AttributeError):
                    acctswitch.reconcile(sid, state, policy, now, halt_marker=marker)
            self.assertFalse(acctswitch.load_probe().get("voiced"))

    def test_at96_every_raw_std_write_site_in_scheduler_closure_resolves(self) -> None:
        """AT-CTL-96：AST 掃排程入口會 import 的模組，所有 `sys.stderr|stdout.write/flush` 與
        `sys.std* is (not) None` 站點；STDIO 縫下 SSOT 讓每個站點的屬性鏈可解（新增站點自動納入）。"""
        import ast  # noqa: PLC0415

        tools = Path(__file__).resolve().parents[1]
        files = [tools / "lib" / n for n in ("quota_gate.py", "pace_contract.py", "quota_availability.py",
                                             "apply_lock.py")]
        files += [tools / "lib" / "sessionctl" / "acctswitch.py", tools / "lib" / "openitems" / "verbs.py",
                  tools / "selfimproving.py"]
        sites = []
        for path in files:
            if not path.is_file():
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (isinstance(node, ast.Attribute) and node.attr in ("write", "flush")
                        and isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name)
                        and node.value.value.id == "sys" and node.value.attr in ("stdout", "stderr")):
                    sites.append((path.name, node.lineno, node.value.attr, node.attr))
        self.assertGreaterEqual(len(sites), 8, "掃描面失明：quota_gate 等站點應有數十處")
        with _StdioNone():
            m.reconfigure_stdio_utf8()
            for _file, _line, stream, attr in sites:
                self.assertTrue(callable(getattr(getattr(sys, stream), attr)), (_file, _line))
            self.assertIsNotNone(sys.stdout)  # `is not None` 分支站點：改綁後走「寫進 devnull」，rc 不變


if __name__ == "__main__":
    unittest.main()
