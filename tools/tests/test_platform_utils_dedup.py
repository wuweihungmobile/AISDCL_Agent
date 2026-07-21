#!/usr/bin/env python3
"""tools/lib/platform_utils.py 收斂止血鎖（R16 架構最佳化 — Architect 建議 A/E）。

背景：`_init_utf8_streams()` 曾被複製貼上到至少 8 個檔案，其中 6 份漏了
`sys.platform != "win32"` 守衛、2 份有。8 個呼叫點已收斂為統一 import
`tools/lib/platform_utils.init_utf8_streams`——但收斂當下誤判「有守衛的 2 份
才是正確版本」，實際上 `test_hooks_stdin_utf8.py` 證明「無條件包裝（原本
6 份的行為）」才是正確版本：呼叫端可在任何平台以 `PYTHONIOENCODING` 覆寫
編碼，POSIX 上不強制重新包裝會讓阻斷級 hook 的中文錯誤訊息讀成亂碼。
本測試機械鎖住兩件事：
  1. `platform_utils` 模組本身提供的 API 存在且行為正確（兩平台皆包裝 / 三態標籤）。
  2. 8 個已知呼叫點不再各自定義 `_init_utf8_streams()`（防未來復發第 9 份複製貼上）。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import platform_utils as m  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[2]

# 已知呼叫點（R16 收斂範圍）；新增第 9 份複製貼上時本清單需連同修復一併擴充，
# 檔案消失（改名/刪除）亦會被 test_known_call_sites_exist fail-loud 抓到。
_KNOWN_CALL_SITES = (
    "AutoClaude/tools/scaffold_sprint_section.py",
    "AutoClaude/tools/snapshot_sync.py",
    "AutoClaude/tools/hooks/check_lang.py",
    "AutoClaude/tools/hooks/loc_budget_check.py",
    "AutoClaude/tools/hooks/check_ps1_encoding.py",
    "AutoClaude/tools/hooks/check_sh_eol.py",
    "AutoClaude/tools/hooks/enforce_docs_path.py",
    "AutoClaude/tools/hooks/claude_md_freshness.py",
)

# 只比對「函式定義」而非呼叫（呼叫點理應保留 `_init_utf8_streams()` 這行）。
_DEF_RE = re.compile(r"^\s*def\s+_?init_utf8_streams\s*\(")

# R17 DEF-101-231 觀察點 1+2：同一輪新增的 tools/bootstrap_core.py /
# tools/integration_gate_core.py / AutoClaude/tools/run_act_core.py 三份核心，與
# 既有 tools/dev_start.py，全都各自重寫過一份 `os.name == "nt"` 判斷邏輯／
# 「Scripts/python.exe vs bin/python」判斷邏輯，從未 import platform_utils——
# 收斂為 is_windows() / os_label() / venv_python_path() 三個函式後，同款掃描
# 手法（機械掃描 `def <name>(` 是否第二次出現）追加鎖住這三個函式名。
_EXTRA_DEF_RES = {
    name: re.compile(rf"^\s*def\s+{re.escape(name)}\s*\(")
    for name in ("is_windows", "os_label", "venv_python_path")
}


class TestPlatformUtilsApi(unittest.TestCase):
    def test_os_label_three_states(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(m.os_label(), "windows")
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(m.os_label(), "mac")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(m.os_label(), "linux")

    def test_is_windows_is_macos_is_posix(self) -> None:
        with mock.patch.object(sys, "platform", "win32"):
            self.assertTrue(m.is_windows())
            self.assertFalse(m.is_macos())
            self.assertFalse(m.is_posix())
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertFalse(m.is_windows())
            self.assertTrue(m.is_macos())
            self.assertTrue(m.is_posix())

    def test_init_utf8_streams_wraps_on_posix(self) -> None:
        """R16 訂正：POSIX 上也必須重新包裝（不再是 no-op）——
        `test_hooks_stdin_utf8.py::test_enforce_docs_path_blocks_chinese_path_under_cp950`
        證明呼叫端可在任何平台以 PYTHONIOENCODING 覆寫預設編碼，POSIX 若不強制
        重新包裝，阻斷級 hook 的中文錯誤訊息會被以覆寫編碼寫出而讀成亂碼。
        用 mock 物件而非真實 sys.stdout/stderr，避免污染 pytest 自身的擷取機制。"""
        import io

        fake_stdout = mock.Mock()
        fake_stdout.buffer = io.BytesIO()
        fake_stderr = mock.Mock()
        fake_stderr.buffer = io.BytesIO()
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()
            self.assertIsInstance(sys.stdout, io.TextIOWrapper)
            self.assertIsInstance(sys.stderr, io.TextIOWrapper)

    def test_init_utf8_streams_wraps_on_windows(self) -> None:
        """Windows 上同樣重新包裝（有 `.buffer` 屬性時）。"""
        import io

        fake_stdout = mock.Mock()
        fake_stdout.buffer = io.BytesIO()
        fake_stderr = mock.Mock()
        fake_stderr.buffer = io.BytesIO()
        with mock.patch.object(sys, "platform", "win32"), \
                mock.patch.object(sys, "stdout", fake_stdout), \
                mock.patch.object(sys, "stderr", fake_stderr):
            m.init_utf8_streams()
            self.assertIsInstance(sys.stdout, io.TextIOWrapper)
            self.assertIsInstance(sys.stderr, io.TextIOWrapper)


class TestNoDuplicateDefinitions(unittest.TestCase):
    def test_known_call_sites_exist(self) -> None:
        """清單本身不得腐化（檔案消失須 fail-loud，不得靜默縮小掃描面）。"""
        for rel in _KNOWN_CALL_SITES:
            self.assertTrue(
                (_REPO_ROOT / rel).is_file(), f"{rel} 不存在——清單需同步更新"
            )

    def test_call_sites_no_longer_define_init_utf8_streams(self) -> None:
        """8 個已知呼叫點不得再各自定義 `_init_utf8_streams`/`init_utf8_streams`
        （只允許 import 唯一真相源）——防未來又複製貼上出第 9 份。"""
        offenders: list[str] = []
        for rel in _KNOWN_CALL_SITES:
            path = _REPO_ROOT / rel
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
            ):
                if _DEF_RE.match(line):
                    offenders.append(f"{rel}:{lineno}: {line.strip()}")
        self.assertEqual(
            offenders,
            [],
            "以下檔案復發自行定義 _init_utf8_streams()——請改為 import "
            "tools/lib/platform_utils.init_utf8_streams：\n" + "\n".join(offenders),
        )

    def test_definition_exists_only_in_platform_utils(self) -> None:
        """全 repo 機械掃描：`def init_utf8_streams(` 只應出現在唯一真相源一處
        （tools/lib/platform_utils.py）。掃描 AutoClaude/ 與根層 tools/，排除
        .venv/__pycache__ 等非原始碼目錄。只釘選「命中檔案清單」而非行號——
        行號會隨模組內部改寫漂移，非本測試守護的契約。"""
        offenders: list[str] = []
        for base in (_REPO_ROOT / "AutoClaude", _REPO_ROOT / "tools"):
            for py in base.rglob("*.py"):
                parts = py.parts
                if any(p in {".venv", "__pycache__", "node_modules"} for p in parts):
                    continue
                for line in py.read_text(encoding="utf-8", errors="replace").splitlines():
                    if _DEF_RE.match(line):
                        offenders.append(py.relative_to(_REPO_ROOT).as_posix())
                        break
        self.assertEqual(
            offenders,
            ["tools/lib/platform_utils.py"],
            "init_utf8_streams 的定義只應出現在 tools/lib/platform_utils.py 一處；"
            f"實際命中：{offenders}",
        )

    def test_platform_judgment_helpers_defined_only_in_platform_utils(self) -> None:
        """R17 DEF-101-231 觀察點 1+2：is_windows/os_label/venv_python_path 三個
        平台判斷 helper 同樣只應在 tools/lib/platform_utils.py 定義一處；
        tools/dev_start.py、tools/bootstrap_core.py、tools/integration_gate_core.py、
        AutoClaude/tools/run_act_core.py 四份核心改為 import 呼叫，不得各自重寫
        第二份。掃描手法與 test_definition_exists_only_in_platform_utils 相同
        （機械掃描 `def <name>(` 出現的檔案清單，非行號釘選）。"""
        for name, pattern in _EXTRA_DEF_RES.items():
            offenders: list[str] = []
            for base in (_REPO_ROOT / "AutoClaude", _REPO_ROOT / "tools"):
                for py in base.rglob("*.py"):
                    parts = py.parts
                    if any(p in {".venv", "__pycache__", "node_modules"} for p in parts):
                        continue
                    for line in py.read_text(encoding="utf-8", errors="replace").splitlines():
                        if pattern.match(line):
                            offenders.append(py.relative_to(_REPO_ROOT).as_posix())
                            break
            self.assertEqual(
                offenders,
                ["tools/lib/platform_utils.py"],
                f"{name} 的定義只應出現在 tools/lib/platform_utils.py 一處；"
                f"實際命中：{offenders}",
            )


if __name__ == "__main__":
    unittest.main()
