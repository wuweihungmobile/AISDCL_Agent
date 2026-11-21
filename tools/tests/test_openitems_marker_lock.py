"""CI 鎖：git 追蹤文件出現待驗標記而該行沒有 OI id ⇒ 紅（A7；TCS-WorkProgress REQ-WP-23、
E2E-WP-22；設計 WorkProgress_Axis_Design §3.5）。

WHY：R217 起因是「待驗」只寫在散文裡、沒有人擁有它（ARC E6：143 處／61 檔）。掃描器（A1）只報告，
閘門在這裡：新增任何待驗標記都必須同時有 OIR 列（行內寫 OI id），否則 CI 紅。規格寫的是**零容忍**：
存量由 A8 種子歸零，之後不留棘輪、不留豁免名單（唯一例外＝`params.json` 的 `vocabulary_definers`，
即定義這套詞彙的文件本身）。所以 A8 種子之前本鎖在真 repo 上是紅的，這是設計、不是缺陷。

真樹判準：`OPENITEMS_LOCK_ROOT` 未設＝本 repo；設了＝該目錄（E2E-WP-22 的沙盒 git repo 以它當根，
並以子行程真跑本檔、驗 rc 與指名）。
受測：`tools/lib/openitems/scan.py`、`tools/lib/openitems/params.py`。
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO / "tools" / "lib"))

import _stdio_utf8  # noqa: E402,F401  # 子行程重跑本檔：UTF-8 stdio 保護（中文失敗訊息）
from lib.openitems import params, scan  # noqa: E402

ROOT_ENV = "OPENITEMS_LOCK_ROOT"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SHOW_MAX = 40
# ARC E6 的詞表（DES §3.5）：`params.json` 的 marker_regex 不得悄悄縮水
VOCABULARY = ("待真機", "待掌舵者目視", "待目視", "仍待真機", "待驗", "計未結")
DEFINERS = (
    "docs/02_architecture/WorkProgress_Axis_Design.md",
    "docs/03_testing/contracts/TCS-WorkProgress-20261119.md",
)


def lock_root() -> Path:
    return Path(os.environ.get(ROOT_ENV) or _REPO)


def unmapped_lines(root: Path) -> list[scan.Hit]:
    """鎖的判準本體：只吃掃描器（單一家），不另寫第二份正規式或 glob。"""
    return [h for h in scan.scan(root, params.load(root)) if not h.mapped]


def failure_message(hits: list[scan.Hit]) -> str:
    shown = "\n".join(f"  {h.path}:{h.line}  {h.text}" for h in hits[:SHOW_MAX])
    more = f"\n  …另有 {len(hits) - SHOW_MAX} 處" if len(hits) > SHOW_MAX else ""
    return (
        f"{len(hits)} 處待驗標記沒有 OI id（零容忍；定義文件除外）：\n{shown}{more}\n"
        "修法：python tools/openitems.py open 立案後，把 OI-YYYYMMDD-NNN 寫在該行；"
        "不屬待驗就改寫措辭。"
    )


def _rmtree(path: Path) -> None:
    def _force(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    shutil.rmtree(path, onerror=_force)


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, creationflags=NOWIN, capture_output=True
    )


class MarkerLockOnTheTreeTest(unittest.TestCase):
    """真鎖：對 `lock_root()` 判（預設本 repo；A8 種子前為紅，見檔頭）。"""

    def test_every_marker_line_has_an_oi_id(self):
        hits = unmapped_lines(lock_root())
        self.assertEqual([], hits, failure_message(hits))


class MarkerLockContractTest(unittest.TestCase):
    """鎖自己的行為與詞表（不依賴本 repo 現況，沙盒根）。受測：`tools/lib/openitems/scan.py`。"""

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="oi_lock_"))
        self.addCleanup(_rmtree, self.root)
        dest = self.root / params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        shutil.copyfile(_REPO / params.PARAMS_REL, dest)

    def test_unmapped_marker_is_reported_and_mapped_or_definer_is_not(self):
        # REQ-WP-23：無 id ⇒ 紅；帶 id、定義文件 ⇒ 不計
        _write(self.root, "docs/a.md", "待驗 OI-20261119-001\n待真機 沒有 id\n")
        _write(self.root, DEFINERS[0], "待驗 這裡是詞彙定義\n")
        got = unmapped_lines(self.root)
        self.assertEqual([(h.path, h.line) for h in got], [("docs/a.md", 2)])

    def test_failure_message_names_the_offending_line_and_the_fix(self):
        _write(self.root, "docs/b.md", "x\n待目視 這行沒有 id\n")
        text = failure_message(unmapped_lines(self.root))
        self.assertIn("docs/b.md:2", text)
        self.assertIn("openitems.py open", text)

    def test_vocabulary_cannot_be_shrunk_quietly(self):
        # MU：marker_regex 少掉任何一個詞，該詞的待驗標記就不再被鎖住
        marker = re.compile(params.load(_REPO)["marker_regex"])
        for word in VOCABULARY:
            self.assertTrue(
                marker.search(f"某項 {word} 之說明"), f"marker_regex 不再認得「{word}」"
            )

    def test_the_two_definition_documents_stay_exempt_and_only_they_are_named_here(self):
        # 兩份定義文件（DES／TCS）必須在豁免名單；否則它們自己的用字會讓鎖永遠紅
        definers = params.load(_REPO)["vocabulary_definers"]
        for rel in DEFINERS:
            self.assertIn(rel, definers)

    def test_one_marker_line_counts_once_even_with_several_words(self):
        _write(self.root, "docs/c.md", "待真機且待掌舵者目視，另外待驗\n")
        self.assertEqual(len(unmapped_lines(self.root)), 1)


class MarkerLockRealProcessTest(unittest.TestCase):
    """E2E-WP-22：沙盒 git repo 提交一份含待驗標記無 id 的 md，真跑本鎖（子行程）。受測：
    `tools/lib/openitems/scan.py`。"""

    def _run_lock(self, root: Path) -> subprocess.CompletedProcess:
        env = {**os.environ, ROOT_ENV: str(root)}
        return subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "-k", "test_every_marker_line"],
            env=env,
            text=True,
            capture_output=True,
            encoding="utf-8",
            timeout=180,
            creationflags=NOWIN,
            check=False,
        )

    def test_sandbox_repo_goes_red_naming_the_line_then_green_after_an_id_is_added(self):
        root = Path(tempfile.mkdtemp(prefix="oi_lock_e2e_"))
        self.addCleanup(_rmtree, root)
        dest = root / params.PARAMS_REL
        dest.parent.mkdir(parents=True)
        shutil.copyfile(_REPO / params.PARAMS_REL, dest)
        _git(root, "init", "-q")
        _git(root, "config", "user.email", "lock@example.invalid")
        _git(root, "config", "user.name", "lock")
        _write(root, "docs/x.md", "第一行\n仍待真機 這行沒有 id\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "seed")
        red = self._run_lock(root)
        self.assertNotEqual(red.returncode, 0, red.stdout + red.stderr)
        self.assertIn("docs/x.md:2", red.stdout + red.stderr)
        _write(root, "docs/x.md", "第一行\n仍待真機 OI-20261119-007 這行有 id\n")
        _git(root, "add", "-A")
        _git(root, "commit", "-q", "-m", "fix")
        green = self._run_lock(root)
        self.assertEqual(green.returncode, 0, green.stdout + green.stderr)


if __name__ == "__main__":
    unittest.main()
