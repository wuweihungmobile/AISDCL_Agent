#!/usr/bin/env python3
"""DEF-200-398：LATEST `tlc_runner.py` subprocess.run 逾時保護回歸鎖。

WHY：TLC 卡住＝無界等待，現況零自動通道跑 TLC、本層 timeout 是唯一保護。鎖 (a) ast 靜態鎖
（帶 `timeout=` 且非 None）(b) `TimeoutExpired` bytes／None 形狀→exit=2 非 exit=1 (c) CLI 與
預設值真的到 subprocess.run (d) 真子行程端對端 (e) 0／負數／inf／nan fail-loud。LATEST 走
`tools/lib/sdd_latest.py` SSOT。複審沿革見證據檔〈收斂後複驗 II〉DEF-200-398 段。
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import unittest
from importlib import util as importlib_util
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "lib"))
import sdd_latest  # noqa: E402

SDD_ROOT = REPO_ROOT / "AISDLC_SDD"
TLC_RUNNER_PATH = (
    sdd_latest.resolve_latest_root(SDD_ROOT) / "tools" / "fsm_runtime" / "tlc_runner.py"
)


def _load_tlc_runner():
    """就地載入 LATEST tlc_runner.py（純 stdlib、無相對 import，不需動 sys.path）。"""
    assert TLC_RUNNER_PATH.is_file(), f"LATEST tlc_runner.py 不存在：{TLC_RUNNER_PATH}"
    spec = importlib_util.spec_from_file_location("tlc_runner_under_test", TLC_RUNNER_PATH)
    module = importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class StaticTimeoutLockTest(unittest.TestCase):
    """(a) 靜態鎖：原始碼中每一個 `subprocess.run(...)` 呼叫都必須帶
    `timeout=` kwarg，且其值不是字面 `None`。"""

    def test_subprocess_run_calls_all_have_timeout_kwarg(self):
        """WHY：ast 找 Call 節點防格式巧合；F-A-03：值為字面 None 等同無界等待，只認名稱會漏。"""
        tree = ast.parse(TLC_RUNNER_PATH.read_text(encoding="utf-8"))
        run_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "run"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
        ]
        self.assertTrue(run_calls, "找不到 subprocess.run(...) 呼叫——結構已變動，請同步本鎖")
        for call in run_calls:
            timeout_kw = next((kw for kw in call.keywords if kw.arg == "timeout"), None)
            self.assertIsNotNone(
                timeout_kw,
                f"第 {call.lineno} 行的 subprocess.run(...) 呼叫缺 timeout= kwarg（DEF-200-398）",
            )
            is_literal_none = (
                isinstance(timeout_kw.value, ast.Constant) and timeout_kw.value.value is None
            )
            self.assertFalse(
                is_literal_none,
                f"第 {call.lineno} 行的 timeout= 是字面 None——等同無界等待復發（DEF-200-398）",
            )


class BehaviorTimeoutLockTest(unittest.TestCase):
    """(b) 行為鎖：TimeoutExpired 映射到 exit=2，正常完成映射到既有 exit 語意不變。"""

    def setUp(self):
        self.module = _load_tlc_runner()
        # find_java()／jar_path() 皆 patch 掉，讓 run_tlc() 走到 subprocess.run(...)
        # 那一段而不被前置的環境檢查提前短路。
        self._java_patch = mock.patch.object(self.module, "find_java", return_value="/usr/bin/java")
        self._jar_patch = mock.patch.object(self.module, "jar_path", return_value=Path(__file__))
        self._java_patch.start()
        self._jar_patch.start()
        self.addCleanup(self._java_patch.stop)
        self.addCleanup(self._jar_patch.stop)

    def test_timeout_expired_bytes_partial_output_maps_to_exit_2(self):
        """WHY（F-A-01／02）：TimeoutExpired 輸出是 bytes（CPython 不解碼，即使 text=True）。"""
        timeout_err = subprocess.TimeoutExpired(
            cmd="java", timeout=1, output=b"partial-out\n", stderr=b"partial-err",
        )
        with mock.patch.object(self.module.subprocess, "run", side_effect=timeout_err):
            result = self.module.run_tlc(timeout_s=1)
        self.assertEqual(result["exit"], 2)
        self.assertNotEqual(result["exit"], 1)
        self.assertFalse(result["ok"])
        self.assertIn("逾時", result.get("error", ""))
        self.assertIn("partial-out", result.get("log_tail", ""))
        self.assertIn("partial-err", result.get("log_tail", ""))

    def test_timeout_expired_none_partial_output_maps_to_exit_2(self):
        """WHY：逾時前零輸出時 stdout/stderr 是 None，另一種真實形狀，與 bytes 分開測。"""
        timeout_err = subprocess.TimeoutExpired(cmd="java", timeout=1, output=None, stderr=None)
        with mock.patch.object(self.module.subprocess, "run", side_effect=timeout_err):
            result = self.module.run_tlc(timeout_s=1)
        self.assertEqual(result["exit"], 2)
        self.assertFalse(result["ok"])
        self.assertIn("逾時", result.get("error", ""))

    def test_normal_completion_still_uses_existing_exit_semantics(self):
        """WHY：紅綠自證——正常完成仍是 exit=0/ok=True，證明前兩支不是恆真。"""
        fake_out = (
            "No error has been found.\n"
            "123 states generated, 45 distinct states found.\n"
            "The depth of the complete state graph search is 7.\n"
        )
        completed = subprocess.CompletedProcess(
            args=["java"], returncode=0, stdout=fake_out, stderr=""
        )
        with mock.patch.object(self.module.subprocess, "run", return_value=completed):
            normal_result = self.module.run_tlc(timeout_s=1)
        self.assertEqual(normal_result["exit"], 0)
        self.assertTrue(normal_result["ok"])

    def test_real_subprocess_timeout_with_partial_stdout_does_not_raise(self):
        """WHY：真子行程端對端，讓 CPython 自己建例外；修法前炸 TypeError（str＋bytes）。"""
        real_run = subprocess.run

        def wrapper(cmd, **kwargs):
            # 忽略傳入的 cmd（假 java 命令），改跑一個真的會印 partial 輸出
            # 後睡著的 Python 子行程，讓 timeout kwargs 原樣透傳給真正的
            # subprocess.run，藉此讓 CPython 自己建構 TimeoutExpired。
            real_cmd = [
                sys.executable, "-c",
                "import sys,time; print('partial'); sys.stdout.flush(); time.sleep(5)",
            ]
            return real_run(real_cmd, **kwargs)

        with mock.patch.object(self.module.subprocess, "run", side_effect=wrapper):
            result = self.module.run_tlc(timeout_s=0.5)

        self.assertEqual(result["exit"], 2)
        self.assertFalse(result["ok"])
        self.assertIn("partial", result.get("log_tail", ""))


class DefaultTimeoutLockTest(unittest.TestCase):
    """(b') F-B-01：不顯式覆寫 timeout 時，預設值仍要一路傳到
    `subprocess.run` 的 `timeout=` kwarg（防「防退化的鎖只驗顯式覆寫」盲點）。"""

    def setUp(self):
        self.module = _load_tlc_runner()
        self._java_patch = mock.patch.object(self.module, "find_java", return_value="/usr/bin/java")
        self._jar_patch = mock.patch.object(self.module, "jar_path", return_value=Path(__file__))
        self._java_patch.start()
        self._jar_patch.start()
        self.addCleanup(self._java_patch.stop)
        self.addCleanup(self._jar_patch.stop)

    @staticmethod
    def _fake_run_capturing(captured: dict):
        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="No error has been found\n", stderr="",
            )
        return fake_run

    def test_run_tlc_default_timeout_reaches_subprocess_run(self):
        """WHY（F-B-01）：零參數呼叫是最易被忽略的路徑，預設值改壞成 None 時本測試必紅。"""
        captured: dict = {}
        with mock.patch.object(
            self.module.subprocess, "run", side_effect=self._fake_run_capturing(captured),
        ):
            self.module.run_tlc()
        self.assertEqual(captured.get("timeout"), self.module.DEFAULT_TLC_TIMEOUT_S)
        self.assertIsNotNone(captured.get("timeout"))

    def test_cli_default_timeout_reaches_subprocess_run_kwargs(self):
        """WHY：同上，CLI 路徑不帶 `--timeout` 時 argparse 的 `default=` 值也要
        真的一路傳到 `subprocess.run`；把預設值改壞成 `None` 時本測試必紅。"""
        captured: dict = {}
        with mock.patch.object(
            self.module.subprocess, "run", side_effect=self._fake_run_capturing(captured),
        ):
            rc = self.module.main(["tlc_runner.py"])
        self.assertEqual(rc, 0)
        self.assertEqual(captured.get("timeout"), self.module.DEFAULT_TLC_TIMEOUT_S)
        self.assertIsNotNone(captured.get("timeout"))


class CliTimeoutLockTest(unittest.TestCase):
    """(c) CLI 鎖：`--timeout 7` 解析後真的傳進 `subprocess.run` 的 `timeout=` kwarg。"""

    def setUp(self):
        self.module = _load_tlc_runner()
        self._java_patch = mock.patch.object(self.module, "find_java", return_value="/usr/bin/java")
        self._jar_patch = mock.patch.object(self.module, "jar_path", return_value=Path(__file__))
        self._java_patch.start()
        self._jar_patch.start()
        self.addCleanup(self._java_patch.stop)
        self.addCleanup(self._jar_patch.stop)

    def test_cli_timeout_flag_reaches_subprocess_run_kwargs(self):
        """WHY：只鎖 argparse 解析出正確型別/預設值不夠——真正防退化的是「這個值有
        沒有一路傳到底層 subprocess.run 呼叫」，故直接檢查該呼叫收到的 kwargs。"""
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured.update(kwargs)
            return subprocess.CompletedProcess(
                args=cmd, returncode=0, stdout="No error has been found\n", stderr="",
            )

        with mock.patch.object(self.module.subprocess, "run", side_effect=fake_run):
            rc = self.module.main(["tlc_runner.py", "--timeout", "7"])
        self.assertEqual(rc, 0)
        self.assertEqual(captured.get("timeout"), 7.0)


class NonPositiveTimeoutRejectionTest(unittest.TestCase):
    """(e) 0／負數／inf／nan 一律 fail-loud（F-B-04＋兩鏡交叉發現 F-A-R2-01／F-B-R2-01）。

    WHY：`value <= 0` 對 nan（所有比較恆 False）與 inf（字面 >0）形同虛設，`--timeout inf`
    會讓 subprocess.run 真的無界等待、繞過整輪修法；`1e400` overflow 成 inf 更隱蔽。"""

    def setUp(self):
        self.module = _load_tlc_runner()

    def test_positive_float_type_rejects_zero_and_negative(self):
        """WHY：timeout<=0 會瞬間拋 TimeoutExpired，被誤報成「TLC 逾時」而非參數打錯。"""
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("0")
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("-5")
        self.assertEqual(self.module._positive_float("7"), 7.0)

    def test_positive_float_type_rejects_inf(self):
        """WHY（R2-01）：inf 字面 >0 繞過 <=0 判準，subprocess.run(timeout=inf) 真的無界等待。"""
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("inf")

    def test_positive_float_type_rejects_negative_inf(self):
        """WHY：-inf 雖已被 <=0 擋下，補齊四種 IEEE-754／overflow 輸入覆蓋。"""
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("-inf")

    def test_positive_float_type_rejects_nan(self):
        """WHY（R2-01）：nan 與所有比較恆 False，<=0 判準看不見它。"""
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("nan")

    def test_positive_float_type_rejects_scientific_overflow_to_inf(self):
        """WHY：float("1e400") overflow 成 inf 不報錯，比字面 inf 更隱蔽。"""
        with self.assertRaises(argparse.ArgumentTypeError):
            self.module._positive_float("1e400")

    def test_cli_timeout_zero_or_negative_is_rejected_at_parse_time(self):
        """WHY：CLI 端對端確認——`--timeout 0`／`--timeout -5` 在 argparse 解析
        階段就 fail-loud（`SystemExit(2)`），不會進到 `run_tlc()` 才發現。"""
        for bad_value in ("0", "-5"):
            with self.assertRaises(SystemExit) as ctx:
                self.module.main(["tlc_runner.py", "--timeout", bad_value])
            self.assertEqual(ctx.exception.code, 2)

    def test_run_tlc_rejects_non_positive_timeout(self):
        """WHY：`run_tlc()` 本身（非只靠 CLI 層 argparse）也要 fail-loud 拒絕
        0／負數，因為它也可能被其他 Python 呼叫端（非 CLI）直接呼叫。"""
        with self.assertRaises(ValueError):
            self.module.run_tlc(timeout_s=0)
        with self.assertRaises(ValueError):
            self.module.run_tlc(timeout_s=-1)

    def test_run_tlc_rejects_inf(self):
        """WHY（R2-01）：run_tlc() 是比 CLI 更底層的入口，呼叫端可直接傳 inf，須獨立擋。"""
        with self.assertRaises(ValueError):
            self.module.run_tlc(timeout_s=float("inf"))

    def test_run_tlc_rejects_nan(self):
        """WHY（R2-01）：同上，nan 讓 <=0 判準失明，底層防線也要擋。"""
        with self.assertRaises(ValueError):
            self.module.run_tlc(timeout_s=float("nan"))

    def test_cli_timeout_inf_is_rejected_end_to_end_and_never_spawns_subprocess(self):
        """WHY（R2-01 端對端）：CLI 入口攔下、subprocess.run 從未被呼叫，無界等待到不了子行程。"""
        with mock.patch.object(self.module.subprocess, "run") as mocked_run:
            with self.assertRaises(SystemExit) as ctx:
                self.module.main(["tlc_runner.py", "--timeout", "inf"])
        self.assertNotEqual(ctx.exception.code, 0)
        mocked_run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
