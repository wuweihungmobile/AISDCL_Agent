#!/usr/bin/env python3
"""tools/git-hooks/pre-commit dispatcher 的行為級回歸鎖（真 git 沙盒、真 commit 觸發）。

本檔收容兩組判準，共用同一套「臨時 repo ＋ core.hooksPath 指向 dispatcher」沙盒：

  (1) **SIGPIPE 分流回歸**（SA 四方複審 P2 發現）——先前 dispatcher 曾用
      `printf | grep -q` 判斷分流：暫存變更清單 >64KB 且命中字串出現在前段時，
      grep -q 提早關閉讀端令 printf 收到 SIGPIPE，`set -o pipefail` 下整條管線視為
      非零 → 分流判定失敗、子專案閘門靜默漏跑。修復已改用純 bash case 前綴比對
      （見 dispatcher 檔頭同款註解），但先前只有程式碼註解防護、缺乏自動化測試。

  (2) **行尾閘（R74）**——進 commit 的 `.sh`／無副檔名 hook 檔不得含 CR。

🔴 為何 (2) 併進本檔而非另立新檔：`tools/tests/test_adr_xplat001_c1c2_lock.py` 的
`_FROZEN_GUARD_FILE_COUNT` 是 **shrink-only 棘輪**，`DEF-101-561③` 明文裁決「禁止新增
鎖檔、只准合併／刪除」。本檔是最貼近的家——它已經備好「真 git repo ＋ 真 commit
觸發 dispatcher」這套沙盒（行尾閘唯一能被行為級驗證的方式就是真的 commit 一次），
新開一支等於把同一套 fixture 抄第二份，還會撞上那條裁決。

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


class TestPreCommitBlocksCrOnShellScripts(unittest.TestCase):
    """R74 行尾閘：帶 CR 的 `.sh`／無副檔名 hook 檔不得進 commit。

    WHY 這件事在 Windows 上完全沒有訊號（本輪同機實測，這是本閘存在的全部理由）：
      · Git Bash 對 CRLF **完全容忍**——`bash -n` 對 CRLF 腳本 rc=0，直接執行也 rc=0
        並正常印出結果；於是 dispatcher 既有的根層基建 `bash -n` 那道閘看不到它。
      · 同一份位元組在 POSIX bash（mac/Linux/Docker/act）上是 `$'\\r': command not
        found` ＋ syntax error。⇒「在 Windows 開發、在 mac 才爆」的最直接來源。

    WHY 閘門看**暫存區 blob** 而不是工作樹檔案：決定 mac 那邊拿到什麼位元組的是入庫
    內容，不是本機 checkout。本 repo 現況正是這個區分的活教材——Windows checkout 上有
    相當數量的 tracked `.sh` 工作樹是 CRLF，而 index 全部是 LF（`.gitattributes` 的
    `*.sh text eol=lf` 正在生效）⇒ clone 到 mac 拿到 LF、無危害，工作樹那批只是本機
    checkout 的殘跡。若閘門改看工作樹，那批檔會讓它天天假紅；看 blob 才對得上危害。
    （筆數刻意不寫死成本檔的常數——那是會漂移的量測值。現查：
     `git ls-files --eol -- '*.sh'`，`i/` 欄才是入庫行尾，`w/` 欄只是本機 checkout。）

    WHY 有 `.gitattributes` 還要這道閘：那是一份**設定**。設定被削弱時（新增子樹自帶
    `.gitattributes` 少了這條、或有人寫成 `*.sh -text`）CRLF 會無聲進 index，而 Windows
    側從頭到尾零訊號——沒有任何人會發現，直到 mac/CI 那邊爆。內容級斷言不依賴設定是否
    正確，這是它與 `.gitattributes` 的分工，不是重複。
    本測試的沙盒**刻意**用 `*.sh -text` ＋ `core.autocrlf=false` 製造那個被削弱的世界，
    否則 `git add` 會先把 CRLF 正規化掉，閘門根本沒機會被考。
    """

    def setUp(self) -> None:
        self.assertTrue(DISPATCHER.is_file(), f"dispatcher 不存在：{DISPATCHER}")
        self.tmp = Path(tempfile.mkdtemp(prefix="pc_dispatcher_eol_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.assertEqual(_git("init", "-q", cwd=self.repo).returncode, 0)

        hooks_dir = self.repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(DISPATCHER, hooks_dir / "pre-commit")
        os.chmod(hooks_dir / "pre-commit", 0o755)

        _git("config", "core.hooksPath", str(hooks_dir), cwd=self.repo)
        _git("config", "core.autocrlf", "false", cwd=self.repo)
        _git("config", "user.email", "test@example.com", cwd=self.repo)
        _git("config", "user.name", "Test", cwd=self.repo)
        # 見類 docstring：刻意關掉正規化，讓 CR 真的能進 index。
        (self.repo / ".gitattributes").write_text("*.sh -text\n", encoding="utf-8", newline="\n")

    def _stage(self, rel: str, raw: bytes) -> None:
        target = self.repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        add = _git("add", "--", rel, cwd=self.repo)
        self.assertEqual(add.returncode, 0, add.stderr)

    def _assert_blob_has_cr(self, rel: str) -> None:
        """測試前提自檢：沙盒真的把 CR 送進了 index。

        少了這條，`.gitattributes` 語意哪天改變、CR 被 add 期正規化掉之後，下面的
        「commit 被擋」就會變成無法區分「閘門有牙」與「根本沒 CR 可擋」。
        """
        blob = subprocess.run(
            ["git", "show", f":{rel}"], cwd=str(self.repo),
            capture_output=True, timeout=60,
        )
        self.assertEqual(blob.returncode, 0, blob.stderr)
        self.assertIn(b"\r", blob.stdout, f"測試前提未成立：{rel} 的暫存 blob 不含 CR")

    def test_crlf_shell_script_is_blocked(self) -> None:
        self._stage("scripts/thing.sh", b"#!/usr/bin/env bash\r\necho hi\r\n")
        self._assert_blob_has_cr("scripts/thing.sh")
        commit = _git("commit", "-q", "-m", "crlf sh", cwd=self.repo)
        self.assertNotEqual(
            commit.returncode, 0,
            "帶 CRLF 的 .sh 進了 commit——mac/Linux/Docker 上該檔即 syntax error，"
            f"而 Windows 側 bash -n 與實跑皆 rc=0（本輪實測）＝零訊號。\n"
            f"stdout={commit.stdout}\nstderr={commit.stderr}",
        )
        self.assertIn(
            "scripts/thing.sh", commit.stdout + commit.stderr,
            "擋下時必須逐字指名是哪一支檔，否則使用者不知道要修什麼",
        )

    def test_crlf_extensionless_hook_file_is_blocked(self) -> None:
        """無副檔名的 hook 檔同樣要守：它們由 git／dispatcher 以 bash 執行，
        且**沒有 `.sh` 副檔名可供比對**——只鎖 `*.sh` 就是鎖射程只圈一半。
        本例的內容語法完全合法 ⇒ 唯一的失敗成因只能是行尾閘（bash -n 那道會放行）。"""
        self._stage("tools/git-hooks/zzz-extra-hook", b"#!/usr/bin/env bash\r\nexit 0\r\n")
        self._assert_blob_has_cr("tools/git-hooks/zzz-extra-hook")
        commit = _git("commit", "-q", "-m", "crlf hook", cwd=self.repo)
        self.assertNotEqual(
            commit.returncode, 0,
            "帶 CRLF 的無副檔名 hook 檔進了 commit（bash -n 對 CRLF rc=0，攔不到）：\n"
            f"stdout={commit.stdout}\nstderr={commit.stderr}",
        )

    def test_lf_shell_script_still_commits(self) -> None:
        """🔴 鑑別力對照組：把閘門寫成「一律擋 .sh」也能讓上面兩條全綠——那是把缺陷
        修成一個更嚴重的缺陷（誰都不能再 commit 任何 shell script）。"""
        self._stage("scripts/clean.sh", b"#!/usr/bin/env bash\necho hi\n")
        commit = _git("commit", "-q", "-m", "lf sh", cwd=self.repo)
        self.assertEqual(
            commit.returncode, 0,
            f"純 LF 的 .sh 被誤擋（閘門過度攔截）：\nstdout={commit.stdout}\n"
            f"stderr={commit.stderr}",
        )

    def test_deleting_a_shell_script_still_commits(self) -> None:
        """對照組：刪除 `.sh` 時暫存區已無該 blob，閘門不得因取不到內容就擋下
        （`git show :<已刪路徑>` 必然失敗——把它讀成「驗不過」等於誰都不能刪腳本）。"""
        self._stage("scripts/doomed.sh", b"#!/usr/bin/env bash\necho hi\n")
        first = _git("commit", "-q", "-m", "add", cwd=self.repo)
        self.assertEqual(first.returncode, 0, first.stderr)
        rm = _git("rm", "-q", "--", "scripts/doomed.sh", cwd=self.repo)
        self.assertEqual(rm.returncode, 0, rm.stderr)
        commit = _git("commit", "-q", "-m", "delete", cwd=self.repo)
        self.assertEqual(
            commit.returncode, 0,
            f"刪除 .sh 被誤擋：\nstdout={commit.stdout}\nstderr={commit.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
