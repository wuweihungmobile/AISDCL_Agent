#!/usr/bin/env python3
"""tools/git-hooks/pre-commit dispatcher 的 SIGPIPE 回歸鎖（SA 四方複審 P2 發現）。

先前 dispatcher 曾用 `printf | grep -q` 判斷分流：暫存變更清單 >64KB 且命中字串
出現在前段時，grep -q 提早關閉讀端令 printf 收到 SIGPIPE，`set -o pipefail` 下整條
管線視為非零 → 分流判定失敗、子專案閘門靜默漏跑。修復已改用純 bash case 前綴比對
（見 tools/git-hooks/pre-commit 檔頭同款註解），但先前只有程式碼註解防護、缺乏
自動化測試——本檔補上，避免未來被「簡化」改回 grep -q 寫法而無聲復發。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCHER = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


class TestPreCommitDispatcherSigpipe(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(DISPATCHER.is_file(), f"dispatcher 不存在：{DISPATCHER}")

        self.tmp = Path(tempfile.mkdtemp(prefix="pc_dispatcher_sigpipe_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        init = _git("init", "-q", cwd=self.repo)
        self.assertEqual(init.returncode, 0, init.stderr)

        hooks_dir = self.repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(DISPATCHER, hooks_dir / "pre-commit")
        os.chmod(hooks_dir / "pre-commit", 0o755)

        # 子 hook 只需存在＋可執行，內容為留下一個 marker 檔證明真的被執行到。
        sub_dir = self.repo / "AutoClaude" / "tools" / "git-hooks"
        sub_dir.mkdir(parents=True)
        self.marker = self.tmp / "AUTOCLAUDE_SUBHOOK_RAN"
        (sub_dir / "pre-commit").write_text(
            f'#!/usr/bin/env bash\n: > "{self.marker.as_posix()}"\nexit 0\n',
            encoding="utf-8",
        )
        os.chmod(sub_dir / "pre-commit", 0o755)

        _git("config", "core.hooksPath", str(hooks_dir), cwd=self.repo)
        _git("config", "user.email", "test@example.com", cwd=self.repo)
        _git("config", "user.name", "Test", cwd=self.repo)

    def test_large_diff_with_early_match_still_routes_to_autoclaude(self):
        """>64KB 暫存變更清單、命中字串在最前段，dispatcher 仍須正確分流不漏跑。

        兩階段 commit：第一階段（AUTOCLAUDE_SKIP_HOOKS=1 略過 hook）先建立 4000 個
        filler 檔並 commit，避免本測試的重點（case 分流判定的 SIGPIPE 抗性）被
        dispatcher 另一段邏輯（NTFS 檔名閘對「新增」檔逐一 grep 比對大小寫碰撞）
        的 O(n) 效能拖慢。第二階段修改全部 filler 檔＋新增一個 AutoClaude/ 檔——
        `git diff --cached --name-only`（case 分流判定讀的清單）仍 >64KB 且命中
        字串在最前段，但 `--diff-filter=AC`（NTFS 閘讀的清單）只有新增的那一個檔，
        NTFS 逐一比對迴圈僅跑一次，測試才能在合理時間內完成。
        """
        filler_dir = self.repo / "filler"
        filler_dir.mkdir()
        for i in range(4000):
            (filler_dir / f"f{i:05d}.txt").write_text("0", encoding="utf-8")

        env_skip = dict(os.environ, AUTOCLAUDE_SKIP_HOOKS="1")
        add1 = subprocess.run(
            ["git", "add", "-A"], cwd=str(self.repo), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60
        )
        self.assertEqual(add1.returncode, 0, add1.stderr)
        commit1 = subprocess.run(
            ["git", "commit", "-q", "-m", "setup filler files"],
            cwd=str(self.repo),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env_skip,
            timeout=60,
        )
        self.assertEqual(commit1.returncode, 0, commit1.stderr)

        # "AutoClaude/..."（大寫 A）依 git 預設字典序排序必然先於 "filler/..."（小寫
        # f）——重現原始 bug「命中字串出現在變更清單前段」的觸發條件，而非依賴巧合。
        (self.repo / "AutoClaude" / "x.txt").write_text("x", encoding="utf-8")
        for i in range(4000):
            (filler_dir / f"f{i:05d}.txt").write_text("1", encoding="utf-8")

        add2 = _git("add", "-A", cwd=self.repo)
        self.assertEqual(add2.returncode, 0, add2.stderr)

        diff = _git("diff", "--cached", "--name-only", cwd=self.repo)
        self.assertGreater(
            len(diff.stdout.encode("utf-8")),
            64_000,
            "測試前提未成立：暫存變更清單需 >64KB 才能重現原始 SIGPIPE 觸發條件",
        )

        commit2 = _git("commit", "-q", "-m", "large diff sigpipe regression test", cwd=self.repo)
        self.assertEqual(
            commit2.returncode,
            0,
            f"commit 應成功（dispatcher 不應在大型變更清單下誤判失敗）：\n"
            f"stdout={commit2.stdout}\nstderr={commit2.stderr}",
        )
        self.assertTrue(
            self.marker.exists(),
            "AutoClaude 子 hook 未被執行——分流判定在大型變更清單下靜默漏跑（SIGPIPE 回歸）",
        )


if __name__ == "__main__":
    unittest.main()
