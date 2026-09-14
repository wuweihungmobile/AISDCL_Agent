#!/usr/bin/env python3
"""tools/lib/single_venv_identity.py 的單元測試（DEF-200-301）。

驗證鏡子自身要被驗證：`single_venv_identity_problems()` 是純函式，合成 settings
即可驗紅／驗綠，不需要真檔案（同鄰檔 test_check_hooks_liveness.py 的既有風格）；
另一半（`TestSingleVenvIdentityRealDisk`）是真磁碟回歸鎖，對每一份活躍 settings
用它自己的專案根跑一次判準，全部必空。

執行：python -m pytest tools/tests/test_single_venv_identity.py -q
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _identity():
    """延後 import 唯一真相源（同鄰檔 test_check_hooks_liveness.py 的既有慣例：
    不進 import 期路徑，且每次呼叫都重新解析，避免測試間 sys.path 順序互相干擾）。
    """
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import single_venv_identity  # noqa: PLC0415

    return single_venv_identity


def _hook_wiring():
    sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
    import hook_wiring  # noqa: PLC0415

    return hook_wiring


def _synthetic_settings(win_command: str) -> dict:
    """組一份最小 settings dict：一條 Windows 載具 + 對應 args[0] 啟動器。

    `win_carrier_kind()` 只認 `command` 字面，`args[0]` 內容對 identity 判準
    不重要（那是 hook_wiring.hook_form_problems 的職責），這裡填一個佔位值即可。
    """
    return {"hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": win_command,
         "args": ["${CLAUDE_PROJECT_DIR}/../.claude/hooks/_hook_launcher.py",
                  ".claude/hooks/x.py"]},
    ]}]}}


class TestSingleVenvIdentitySynthetic(unittest.TestCase):
    """合成注入：不碰磁碟，AutoClaude 深度（比 repo 根深一級）為固定情境。"""

    def test_zero_level_parent_prefix_is_red(self) -> None:
        """(a) 0 層 `../`（DEF-200-294 事故當時的字面）在 AutoClaude 深度下判紅——
        展開後落在 `AutoClaude/.venv/...`，不是 repo 唯一那一顆根層 `.venv`。
        """
        settings = _synthetic_settings("${CLAUDE_PROJECT_DIR}/.venv/Scripts/pythonw.exe")
        problems = _identity().single_venv_identity_problems(
            settings, project_dir="/repo/AutoClaude", repo_root="/repo")
        self.assertTrue(problems, "0 層 ../ 在子專案深度下應判紅，卻回空")

    def test_one_level_parent_prefix_is_green(self) -> None:
        """(b) 1 層 `../`（AutoClaude 只比 monorepo 根深一級，DEF-200-301 修法）
        展開後落在根層 `.venv` ⇒ 判準應放行。
        """
        settings = _synthetic_settings("${CLAUDE_PROJECT_DIR}/../.venv/Scripts/pythonw.exe")
        problems = _identity().single_venv_identity_problems(
            settings, project_dir="/repo/AutoClaude", repo_root="/repo")
        self.assertEqual(problems, [], problems)

    def test_path_carrier_is_out_of_scope(self) -> None:
        """(c) PATH 版載具（`pythonw.exe` 字面）的實況取決於 session 的 PATH，
        沒有固定身分可比 ⇒ 射程外，不觸發任何問題（同 hook_wiring 既有劃界）。
        """
        settings = _synthetic_settings("pythonw.exe")
        problems = _identity().single_venv_identity_problems(
            settings, project_dir="/repo/AutoClaude", repo_root="/repo")
        self.assertEqual(problems, [], problems)

    def test_over_correction_two_levels_is_still_red(self) -> None:
        """(d) 過度修正：AutoClaude 只需 1 層，卻寫成 2 層 `../../`——身分依然不對。

        本函式刻意不判「路徑存不存在」（那是 carrier_liveness_problems 的職責），
        只判「展開後是不是那唯一一顆」：2 層在 AutoClaude 深度下 normpath 落到
        repo 之外一層，即使那個路徑在某台機器上剛好真的存在，existence 判準會
        誤判通過，identity 判準必須抓到這裡身分不對。
        """
        settings = _synthetic_settings(
            "${CLAUDE_PROJECT_DIR}/../../.venv/Scripts/pythonw.exe")
        problems = _identity().single_venv_identity_problems(
            settings, project_dir="/repo/AutoClaude", repo_root="/repo")
        self.assertTrue(problems, "2 層 ../../ 在只需 1 層的深度下應判紅，卻回空")


class TestSingleVenvIdentityCaseFold(unittest.TestCase):
    """(g) QA-2（四方複審）：`single_venv_identity_problems()` 內部依賴
    `os.path.normcase()` 折疊大小寫，但先前零測試涵蓋這一步——拿掉它（例如誤改成
    只剩 `os.path.normpath()`）本支會紅：`repo_root` 與 `project_dir` 僅大小寫
    不同時（如磁碟機字母或目錄名大小寫飄移），canonical 與 resolved 兩條路徑逐
    位元組比較不相等，只有經過 normcase 折疊大小寫後才會相等。

    跨平台鑑別力：不用 `unittest.skipUnless(os.name == "nt", ...)`，改把
    `os.path.normcase` monkeypatch 成 `str.lower`——讓本斷言在 POSIX（原生
    case-sensitive、真正的 `os.path.normcase` 在該平台是 no-op）與 Windows
    （原生已折疊）三平台上都有鑑別力：拿掉判準函式內的 `os.path.normcase()`
    呼叫，本測試在三平台都會轉紅，而不是只在 Windows 才紅。
    """

    def test_case_only_difference_between_repo_root_and_project_dir_is_green(self) -> None:
        identity = _identity()
        with patch("os.path.normcase", new=str.lower):
            settings = _synthetic_settings(
                "${CLAUDE_PROJECT_DIR}/../.venv/Scripts/pythonw.exe")
            problems = identity.single_venv_identity_problems(
                settings, project_dir="/repo/AutoClaude", repo_root="/Repo")
        self.assertEqual(
            problems, [],
            "repo_root 與 project_dir 僅大小寫不同（/Repo vs /repo）時，經 "
            "normcase 折疊大小寫後應視為同一顆根層 .venv，卻判紅：" + str(problems))


class TestSingleVenvIdentityRealDisk(unittest.TestCase):
    """(e)(f) 真磁碟回歸鎖：對每一份活躍 settings，用它自己的專案根跑判準。

    修 `AutoClaude/.claude/settings.json` 六條 Windows command 前，本測試對該份
    settings 用 `project_dir=<repo>/AutoClaude` 跑會紅（0 層 `../` 在該深度下不等於
    canonical，見上方合成案 (a) 的等價數學）；DEF-200-301 落地後全部轉綠。
    """

    def test_every_active_settings_passes_identity(self) -> None:
        hook_wiring = _hook_wiring()
        identity = _identity()
        for rel in hook_wiring.discover_active_settings(_REPO_ROOT):
            settings_path = _REPO_ROOT / rel
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            project_dir = str(settings_path.parent.parent)
            problems = identity.single_venv_identity_problems(
                settings, project_dir, str(_REPO_ROOT))
            self.assertEqual(problems, [], f"{rel}：\n  " + "\n  ".join(problems))

    def test_the_sdd_latest_nested_depth_is_still_green(self) -> None:
        """SDD LATEST 用真實巢狀深度（`../../`）驗證仍判綠——防止未來
        Copy-on-Evolve 改變目錄深度時判準跟著漂移而不自知（比照鄰檔
        test_check_hooks_liveness.py::test_a_parent_relative_carrier_is_not_a_false_positive
        對 A2b 的既有正向自證手法）。
        """
        hook_wiring = _hook_wiring()
        latest = hook_wiring.latest_sdd_settings(_REPO_ROOT)
        self.assertIsNotNone(latest, "LATEST 解析不到 ⇒ 這格空轉")
        settings_path = _REPO_ROOT / latest
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        project_dir = str(settings_path.parent.parent)
        problems = _identity().single_venv_identity_problems(
            settings, project_dir, str(_REPO_ROOT))
        self.assertEqual(problems, [], problems)


if __name__ == "__main__":
    unittest.main()
