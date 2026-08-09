#!/usr/bin/env python3
"""tools/git-hooks/pre-commit dispatcher 的行為級回歸鎖（真 git 沙盒、真 commit 觸發）。

本檔收容兩組判準，共用同一套「臨時 repo ＋ core.hooksPath 指向 dispatcher」沙盒：

  (1) **SIGPIPE 分流回歸**（SA 四方複審 P2 發現）——先前 dispatcher 曾用
      `printf | grep -q` 判斷分流：暫存變更清單 >64KB 且命中字串出現在前段時，
      grep -q 提早關閉讀端令 printf 收到 SIGPIPE，`set -o pipefail` 下整條管線視為
      非零 → 分流判定失敗、子專案閘門靜默漏跑。修復已改用純 bash case 前綴比對
      （見 dispatcher 檔頭同款註解），但先前只有程式碼註解防護、缺乏自動化測試。

  (2) **行尾閘（R74）**——進 commit 的 `.sh`／無副檔名 hook 檔不得含 CR。

🔴 為何 (2) 併進本檔而非另立新檔：`tools/tests/` 有一道護欄層 shrink-only 棘輪
（`DEF-101-561③`；R74 當時量的是檔數。🔴 R78 ARCH-03 訂正：R77 起接手者是
`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet` 的逐檔行數表，現行語意是
**淨行數不得上升**、不是「禁止新增檔案」）。本檔是最貼近的家——它已經備好「真 git repo ＋ 真 commit
觸發 dispatcher」這套沙盒（行尾閘唯一能被行為級驗證的方式就是真的 commit 一次），
新開一支等於把同一套 fixture 抄第二份，還會撞上那條裁決。

執行：python3 -m unittest discover -s tools/tests -p "test_*.py" -v
"""
from __future__ import annotations

import ast
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[2]
DISPATCHER = REPO_ROOT / "tools" / "git-hooks" / "pre-commit"
_BLOCKING_HOOKS_DIR = REPO_ROOT / "AutoClaude" / "tools" / "hooks"


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


def _load_hook_path_scope():
    """載入 `AutoClaude/tools/hooks/hook_path_scope.py`（兩支阻斷級 hook 的共用正規化層）。

    以檔案路徑載入而非 import：該目錄不是套件、且生產路徑本身也是被
    `runpy.run_path()` 以絕對路徑叫起來的。
    """
    path = _BLOCKING_HOOKS_DIR / "hook_path_scope.py"
    spec = importlib.util.spec_from_file_location("_root_test_hook_path_scope", path)
    assert spec is not None and spec.loader is not None, f"無法載入 {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestHookPathScopeFlavourParity(unittest.TestCase):
    """R77-50：兩支 exit-2 阻斷級 hook 的路徑正規化，兩種 flavour 必須同判決。

    WHY 這件事重要（Rule 9 — 測的是「為什麼」，不是「是什麼」）：
    `enforce_docs_path.py` 與 `check_sh_eol.py` 都是 exit 2 硬阻斷。它們此前各自靠
    `Path.resolve().relative_to(PROJECT_ROOT)` 取相對路徑，而**那條路的大小寫語意由
    flavour 決定**（見下方 `test_stdlib_relative_to_is_the_divergence_being_absorbed`
    的實測）。同一份判準因此在兩個平台壞向相反的兩邊：
      · POSIX 上 `enforce_docs_path` 對大小寫變體**假陽性硬擋**——使用者當場撞到，
        卻只會以為是自己路徑打錯（本輪 Windows 真機 rc 矩陣：改前 rc=2、改後 rc=0）；
      · POSIX 上 `check_sh_eol` 的 `relative_to` 拋 ValueError → 回 None → main 直接
        return 0 ⇒ **CRLF 守衛整支靜默略過**，fail-open，沒有人會發現。
    「壞的方向依平台而反轉」正是單一平台實測抓不到的那一類——Windows 真機把兩個錯都
    蓋住了。所以判準必須是**純字面**、可對兩種 flavour 直接對拍，而不是問檔案系統。
    """

    def setUp(self) -> None:
        self.mod = _load_hook_path_scope()

    #: (情境, Windows 形式的絕對路徑, POSIX 形式的絕對路徑, 期望相對路徑)
    #: 兩欄描述的是「同一件事」在兩個平台的寫法；期望值只有一個。
    CASES = (
        ("root 前綴大小寫相同",
         r"D:\p\AISDCL_Agent\tools\x.sh", "/h/u/AISDCL_Agent/tools/x.sh",  # platform-ok: 對拍語料
         "tools/x.sh"),
        ("root 前綴大小寫不同（舊實作在 POSIX 回 None ⇒ 守衛整支略過）",
         r"D:\P\AISDCL_AGENT\tools\x.sh", "/h/U/aisdcl_agent/tools/x.sh",  # platform-ok: 對拍語料
         "tools/x.sh"),
        ("尾段大小寫不同（原樣保留，交給 under_prefix 做不分大小寫比對）",
         r"D:\p\AISDCL_Agent\DOCS\06_QUALITY\a.md",  # platform-ok: 對拍語料
         "/h/u/AISDCL_Agent/DOCS/06_QUALITY/a.md",
         "DOCS/06_QUALITY/a.md"),
        ("路徑中含 . 與 ..（必須先收斂再比對）",
         r"D:\p\AISDCL_Agent\tools\.\sub\..\x.sh",  # platform-ok: 對拍語料
         "/h/u/AISDCL_Agent/tools/./sub/../x.sh",
         "tools/x.sh"),
        ("以 .. 跳出 root（不歸我管，兩種 flavour 都必須是 None）",
         r"D:\p\AISDCL_Agent\..\outside\x.sh",  # platform-ok: 對拍語料
         "/h/u/AISDCL_Agent/../outside/x.sh",
         None),
        ("完全在樹外", r"D:\other\x.sh", "/var/other/x.sh", None),  # platform-ok: 對拍語料
    )

    def test_same_verdict_under_both_flavours(self) -> None:
        win_root = PureWindowsPath(r"D:\p\AISDCL_Agent")
        posix_root = PurePosixPath("/h/u/AISDCL_Agent")
        for label, win, posix, expected in self.CASES:
            with self.subTest(label):
                got_win = self.mod.relative_within(PureWindowsPath(win), win_root)
                got_posix = self.mod.relative_within(PurePosixPath(posix), posix_root)
                self.assertEqual(
                    got_win, got_posix,
                    f"同一件事在兩個平台判決不同（{label}）："
                    f"Windows={got_win!r} POSIX={got_posix!r}——"
                    "阻斷級 hook 的判決不得隨 flavour 反轉",
                )
                self.assertEqual(got_win, expected, f"{label}：判決與規格不符")

    def test_stdlib_relative_to_is_the_divergence_being_absorbed(self) -> None:
        """本 shim 為何不能直接用 `PurePath.relative_to`——把成因釘成可執行的事實。

        這一條刻意斷言**標準庫現況**：哪天 `relative_to` 兩種 flavour 語意統一了，
        本條會紅，而那正是「這層 shim 可以退場」的訊號。沒有這條的話，上一條全綠只
        證明 shim 自己前後一致，證不出它在吸收一個真實存在的分歧。
        """
        win = PureWindowsPath(r"D:\PROJ\AISDCL_AGENT\tools\x.sh")
        self.assertEqual(
            win.relative_to(PureWindowsPath(r"D:\proj\AISDCL_Agent")).as_posix(),
            "tools/x.sh", "relative_to 應大小寫不敏感",  # path-key-ok: 上一行已 as_posix
        )
        with self.assertRaises(ValueError):
            PurePosixPath("/home/U/aisdcl_agent/tools/x.sh").relative_to(
                PurePosixPath("/home/u/AISDCL_Agent")
            )


class TestHookPathScopeDirectoryBoundary(unittest.TestCase):
    """R77-50 附帶：白名單前綴比對必須帶目錄邊界。

    WHY：舊實作是裸 `str.startswith(prefix)`，於是與白名單目錄**同前綴的另一個目錄**
    會被整片收下。本輪實測改前逐字：`is_allowed_md('docs/06_qualityEXTRA/a.md')` → True。
    這一格與平台無關，兩個平台一起錯。
    """

    def setUp(self) -> None:
        self.mod = _load_hook_path_scope()

    def test_sibling_directory_sharing_the_prefix_is_not_under_it(self) -> None:
        for rel in ("docs/06_qualityEXTRA/a.md", "docs/06_quality_backup/a.md",
                    "docs/06_qualityX", "testsX/a.md"):
            with self.subTest(rel):
                self.assertFalse(
                    any(self.mod.under_prefix(rel, p)
                        for p in ("docs/06_quality", "tests/")),
                    f"{rel} 與白名單目錄只是前綴相同，不在它底下",
                )

    def test_real_members_and_case_variants_are_under_it(self) -> None:
        for rel in ("docs/06_quality/a.md", "docs/06_quality/sub/a.md",
                    "DOCS/06_QUALITY/a.md", "tests/a.md"):
            with self.subTest(rel):
                self.assertTrue(
                    any(self.mod.under_prefix(rel, p)
                        for p in ("docs/06_quality", "tests/")),
                    f"{rel} 應被視為在白名單目錄底下（大小寫不敏感是刻意選的方向）",
                )


# 具名排除（不納入單一實作約束）＋逐筆理由。形狀照抄
# `tools/check_script_parity.py` 的 `_AC_EXCLUDED_REGISTRIES`：排除是**決策**，必須寫
# 下來被複審看見；同目錄新增一支而不表態就會落進掃描面並轉紅。
_PATH_SCOPE_EXCLUDED: dict[str, str] = {
    "hook_path_scope.py":
        "共用層本身——它就是被委派的那一份實作，不是消費者；納入即自我指涉",
    "check_ps1_encoding.py":
        "不做「repo 相對路徑」轉換：`resolve_path()` 只把 payload 路徑補成絕對路徑後"
        "直接讀寫該檔，判決不問「這個檔在不在某棵樹底下」⇒ 沒有 root 前綴大小寫分歧"
        "這個成因。且它 best-effort 永遠 exit 0，非阻斷級",
    "check_lang.py":
        "Stop 事件，payload 只有 transcript_path，全檔零 `file_path` 處理"
        "（Grep 實查：該識別字在本檔零命中）⇒ 不在本判準的射程內",
    "claude_md_freshness.py":
        "目標路徑是寫死的模組層常數 `PROJECT_ROOT / \"CLAUDE.md\"`，不從 payload 取"
        "路徑（同上 Grep 實查零命中）⇒ 無正規化面",
}


def _path_scope_consumers() -> list[str]:
    """`AutoClaude/tools/hooks/*.py` 扣掉具名排除——本鎖的掃描面（列舉，非白名單）。"""
    return sorted(
        p.name for p in _BLOCKING_HOOKS_DIR.glob("*.py")
        if p.name not in _PATH_SCOPE_EXCLUDED
    )


class TestBlockingHooksShareOnePathNormalizer(unittest.TestCase):
    """R77-50 的**單一實作**約束：hook 不得再各自長出一份路徑正規化。

    WHY：本缺陷的成因不是「某一行寫錯」，而是同一份知識住兩個家而只有一個家被想過
    （R73 `DEF-101-778` 同型）。只修那兩行、不釘「別再分家」，下一個人照樣會在其中
    一支就地補一段 `resolve().relative_to(...)`，而分歧會再度只在對面平台顯形。

    🔴 R78／ARCH-06：本鎖此前是**寫死兩項的白名單** `("enforce_docs_path.py",
    "check_sh_eol.py")`，於是同目錄第三支 `loc_budget_check.py`（保留了逐字相同的舊
    寫法）與**任何未來新增者**都在射程外——R77 的 commit message 逐字寫「收斂到單一
    實作並補 parity 測試」，收斂是真的，但鎖只擋在當初被想到的那兩個站點上。這正是
    本 repo 反覆出現的「白名單型的鎖對未來新增者失明」。改成「列舉整個目錄 − 具名
    排除表」後，掃描面隨磁碟走，漏掉一支就是紅。
    """

    @property
    def HOOKS(self) -> tuple[str, ...]:  # noqa: N802 — 沿用原常數名，呼叫端不變
        return tuple(_path_scope_consumers())

    def test_enrolment_is_exactly_listing_minus_named_exclusions(self) -> None:
        """掃描面的**推導式**本身：納管面 ≡ 目錄列舉 − 具名排除，中間不得有過濾器。

        🔴 本條取代初稿裡一條**恆真**的斷言（`on_disk − 納管 − 排除 == []`——在
        「納管 ≡ 列舉 − 排除」的定義下結構上永遠是空集）。那正是本包在修的
        「鎖存在但沒有鑑別力」，寫在自己身上格外難看，故改成真的會被改壞的性質：
        日後有人為了消一個紅而在 `_path_scope_consumers()` 裡加一道隱形過濾
        （例如「只收檔名含 `check_` 的」），掃描面就會悄悄縮回白名單，而排除表上
        一個字都不用改、複審也看不到。新增者「必須委派或必須具名排除」這件事本身
        由下面兩條負責（實測：目錄裡放一支未表態的 hook → 立刻紅）。
        """
        on_disk = {p.name for p in _BLOCKING_HOOKS_DIR.glob("*.py")}
        self.assertTrue(on_disk, f"掃不到任何 hook：{_BLOCKING_HOOKS_DIR} ⇒ 本鎖恆綠")
        self.assertEqual(
            set(self.HOOKS), on_disk - set(_PATH_SCOPE_EXCLUDED),
            "納管面不等於「目錄列舉 − 具名排除」⇒ 兩者之間多了一道隱形過濾器，"
            "掃描面已悄悄縮小而排除表看不出來",
        )
        # 反空轉下限：掃描面若塌到剩一支，下面兩條斷言幾乎恆真。現況 3 支
        # （enforce_docs_path／check_sh_eol／loc_budget_check）。
        self.assertGreaterEqual(
            len(self.HOOKS), 3,
            f"納管數 {len(self.HOOKS)} < 3——刻意移除消費者請同步下修本下限並寫理由",
        )

    def test_excluded_names_all_exist(self) -> None:
        """反向 stale：排除表指向已不存在的檔 ⇒ 紅（防清單腐化後悄悄放寬射程）。"""
        on_disk = {p.name for p in _BLOCKING_HOOKS_DIR.glob("*.py")}
        stale = sorted(set(_PATH_SCOPE_EXCLUDED) - on_disk)
        self.assertEqual(stale, [], f"排除表指向不存在的 hook：{stale}")

    def _tree(self, name: str) -> ast.Module:
        """以 AST 檢視，而不是字串搜尋。

        判準看的是**程式碼**：兩支 hook 的 docstring 必須能自由引述被取代的舊寫法
        （那是訂正註記的價值所在），字面掃描會把那些說明本身判成違規。
        """
        return ast.parse((_BLOCKING_HOOKS_DIR / name).read_text(encoding="utf-8"))

    def test_shared_module_exists_and_is_imported_by_all_consumers(self) -> None:
        shared = _BLOCKING_HOOKS_DIR / "hook_path_scope.py"
        self.assertTrue(shared.is_file(), f"共用正規化層不存在：{shared}")
        for name in self.HOOKS:
            with self.subTest(name):
                imported = any(
                    isinstance(n, ast.ImportFrom) and n.module == "hook_path_scope"
                    for n in ast.walk(self._tree(name))
                )
                self.assertTrue(
                    imported, f"{name} 未取用共用正規化層——判決會再度依平台分歧",
                )

    def test_neither_hook_keeps_a_private_relative_to_implementation(self) -> None:
        for name in self.HOOKS:
            with self.subTest(name):
                hits = [
                    n for n in ast.walk(self._tree(name))
                    if isinstance(n, ast.Attribute) and n.attr == "relative_to"
                ]
                self.assertFalse(
                    hits,
                    f"{name} 又自帶了一份 relative_to 正規化（行 "
                    f"{[n.lineno for n in hits]}）：那正是本鎖要擋的第二個家",
                )


#: 准許自己碰 `sys.stdin` 的 hook。**每一筆都要有結構理由**（「還沒改到」不算）：
#: block_bash＝fail-closed 且 docstring 明載零外部相依（退化分支不能依賴 import）；
#: sdd_hook_router＝原樣轉發 stdin、不解析 payload；_hook_launcher＝pythonw 無管線時
#: 補 devnull。
#: 🔴 收尾者移除 `context_budget_guard.py`：該筆的理由逐字是「R81 包 A 正在改，本包
#: 不得動 ⇒ 交棒收尾接上共用層」——那是**排程理由不是結構理由**，而本表檔頭要求每筆
#: 都要有結構理由。收尾窗口既然獨佔整棵樹，交棒條件就已滿足：該檔已改走
#: `from platform_utils import read_payload`（退化分支同 `lint_powershell_command.py`），
#: 本地那份 21 行手抄本已刪除 ⇒ 它不再碰 `sys.stdin`，排除自然到期。留著會讓射程
#: 悄悄比宣稱小一格，而反向 stale 判準只抓「指向不存在的檔」、抓不到「已不需要」。
_STDIN_OWN_READER_ALLOWED = (
    "block_bash_on_windows.py", "sdd_hook_router.py", "_hook_launcher.py",
)


class TestHookPayloadSingleHome(unittest.TestCase):
    """R81／SUB-S1-04：hook 的 stdin payload 讀取只能有**一個家**。

    WHY：這 7 份「逐字相同」的手抄本實測已漂移成 3 種行為（4 份原樣回傳
    `json.loads` 的結果／1 份回 `{}`／2 份回 `None`）。代價是 `enforce_docs_path.py`
    （**阻斷級** PreToolUse）餵 `[1,2,3]` 或 `null` 時 rc=1 AttributeError——守衛還在，
    判定卻沒產出。全 repo 零判準會因為這種漂移轉紅。
    """

    _SSOT = REPO_ROOT / "tools" / "lib" / "platform_utils.py"
    _DIRS = (_BLOCKING_HOOKS_DIR, REPO_ROOT / ".claude" / "hooks")

    def _ssot(self):
        spec = importlib.util.spec_from_file_location("hook_payload_ssot", self._SSOT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_no_hook_reads_stdin_itself(self) -> None:
        """長出第二個家的**唯一入口**就是自己碰 stdin ⇒ 掃它，具名排除須有理由。"""
        offenders = []
        for directory in self._DIRS:
            scanned = sorted(directory.glob("*.py"))
            self.assertTrue(scanned, f"{directory} 掃不到 hook ⇒ 本鎖恆綠")
            offenders += [
                p.name for p in scanned
                if p.name not in _STDIN_OWN_READER_ALLOWED
                and any(isinstance(n, ast.Attribute) and n.attr == "stdin"
                        for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))))
            ]
        self.assertEqual(
            offenders, [],
            f"這些 hook 又自己讀起 stdin：{offenders}——payload 讀取的唯一家是 "
            f"{self._SSOT.name}；真有結構理由請登記進 _STDIN_OWN_READER_ALLOWED 並寫明",
        )

    def test_the_exclusion_table_is_not_stale(self) -> None:
        """反向 stale：排除表指向已不存在的 hook ⇒ 紅（防清單腐化後悄悄放寬射程）。"""
        on_disk = {p.name for d in self._DIRS for p in d.glob("*.py")}
        self.assertEqual(sorted(set(_STDIN_OWN_READER_ALLOWED) - on_disk), [])

    def test_both_contracts_survive_and_the_reader_never_raises(self) -> None:
        """兩個回傳型別**都要在**（`lint_powershell_command` 靠 `None` vs `{}` 分流出

        兩種不同的 stderr 與 rc 分支），且任何輸入都不得拋例外——hook 崩潰會讓阻斷級
        守衛的判定靜默消失（`.claude/settings.json` 記載過的 P0）。
        """
        mod = self._ssot()

        class Exploding(io.StringIO):
            def read(self, *_a: object) -> str:
                raise OSError("stdin 壞了")

        cases = [('{"a": 1}', {"a": 1}), ("[1,2,3]", None), ("null", None),
                 ("", None), ("{oops", None), ("{}", {}), (Exploding, None)]
        for raw, expected in cases:
            with self.subTest(raw=raw):
                # 每次呼叫都要一份**新的** stdin：串流讀完就空了，共用一份會讓第二個
                # 斷言變成在測「空輸入」——恰好是恆綠的方向（初稿實測踩到過）。
                for fn, want in ((mod.read_payload, expected),
                                 (mod.read_hook_payload, expected or {})):
                    stub = raw() if raw is Exploding else io.StringIO(raw)
                    with mock.patch.object(mod.sys, "stdin", stub):
                        self.assertEqual(fn(), want)


# ═══════════════════════════════════════════════════════════════════════════
# R82 機密外洩防線（三層）的回歸鎖
#
# 🔴 掌舵者當場下的安全紅線：「`.env` 有私密 KEY，請不要推上 GitHub」。
# 三層各自守不同的失效形態，缺一層就有一條實際可走的外洩路徑：
#   ① `tools/git-hooks/pre-commit` 的路徑形態閘 —— 擋 `git add -f .env`；
#   ② `tools/lib/secret_scan.py` 的內容判準 —— 擋「真 key 被貼進**已追蹤**的
#      `.env.example`」（檔名層對它結構上失明）；
#   ③ 本節的不變式 —— 擋「哪天有人把上面兩層拆了 / 忽略規則被改壞」。
#
# 為何併進本檔而非另開新檔：`tools/tests/` 有 shrink-only 淨行數棘輪
# （`test_adr_xplat001_c1c2_lock.py::TestGuardLayerRatchet`），且本檔已備好
# 「真 git repo ＋ 真 commit 觸發 dispatcher」那套沙盒——層 ① 唯一能被行為級驗證
# 的方式就是真的 commit 一次，抄第二份 fixture 沒有意義。
# ═══════════════════════════════════════════════════════════════════════════

sys.path.insert(0, str(REPO_ROOT / "tools" / "lib"))
import secret_scan  # noqa: E402  # 內容判準的 SSOT（見該檔檔頭的射程與假紅實測）

_LIB_DIR = REPO_ROOT / "tools" / "lib"


class TestEnvFilesAreNeverTracked(unittest.TestCase):
    """不變式①：tracked 清單裡永遠沒有 `.env`（`.env.example` 除外）。

    WHY 這條要現查 `git ls-files` 而不是讀 `.gitignore`：忽略規則寫得再對，都擋不住
    一個**已經被追蹤**的檔案——`.gitignore` 對 tracked 檔完全不生效。真正要斷言的
    不變式是「index 裡沒有那種東西」，而那只能問 index。
    """

    def _tracked(self) -> list[str]:
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "-c", "core.quotepath=false", "ls-files"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
        )
        self.assertEqual(proc.returncode, 0, f"git ls-files 失敗：{proc.stderr}")
        return [line for line in proc.stdout.splitlines() if line]

    def test_no_env_shaped_path_is_tracked_except_the_template(self) -> None:
        tracked = self._tracked()
        # 反空轉：清單塌成空集合時，下面的「零命中」會恆真通過＝靜默失效。
        self.assertGreater(
            len(tracked), 1000,
            f"tracked 清單只有 {len(tracked)} 條 ⇒ 取數管道壞了，本鎖恆綠",
        )
        offenders = [
            rel for rel in tracked
            if secret_scan.is_env_shaped(rel) and PurePosixPath(rel).name != ".env.example"
        ]
        self.assertEqual(
            offenders, [],
            f"這些 .env 形態的檔已被 git 追蹤：{offenders}\n"
            "一旦 push 就是不可逆的外洩。修法：git rm --cached -- <檔>，"
            "並確認該路徑真的被 .gitignore 排除（見同類的 check-ignore 測試）",
        )

    def test_the_template_itself_is_tracked(self) -> None:
        """反向對照：`.env.example` **必須**在追蹤清單裡。

        少了這條，把 `.env.example` 一起刪掉／一起忽略掉也能讓上一條全綠——那是把
        缺陷修成另一個缺陷（使用者拿不到範本，只好自己憑空造 .env）。
        """
        self.assertIn(
            "AutoClaude/.env.example", self._tracked(),
            "範本 AutoClaude/.env.example 不在追蹤清單 ⇒ 上一條的「零命中」失去鑑別力",
        )


class TestGitignoreActuallyIgnoresEnvFiles(unittest.TestCase):
    """不變式②：忽略規則**實際生效**——憑證是 `git check-ignore` 的 rc，不是規則字面。

    WHY 不讀 `.gitignore` 的文字：本 repo 的既有紀律是「憑證是那個『值』，不是規則
    長什麼樣」。`.env` 這一族的規則橫跨根層與子專案兩份 `.gitignore`、還帶一條
    `!.env.example` 反向規則，規則字面對不對與「git 到底怎麼判」是兩件事——順序、
    negation、子目錄覆寫任一個寫錯，字面掃描都看不出來，而 rc 一定看得出來。
    """

    def _check_ignore(self, rel: str) -> int:
        return subprocess.run(
            ["git", "-C", str(REPO_ROOT), "check-ignore", "-q", "--", rel],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60,
        ).returncode

    def test_env_shapes_are_ignored(self) -> None:
        """rc=0＝真的被忽略。涵蓋根層、子專案、任意深度子目錄與帶後綴的變體。"""
        for rel in (
            ".env", ".env.local", ".env.production", ".env.anything",
            "AutoClaude/.env", "AutoClaude/.env.local",
            "some/deep/nested/dir/.env", "tools/.env.staging",
        ):
            with self.subTest(rel):
                self.assertEqual(
                    self._check_ignore(rel), 0,
                    f"{rel} **沒有**被 .gitignore 排除 ⇒ 它會出現在 git status 裡，"
                    "而下一個 `git add -A` 就會把真實憑證帶進 index",
                )

    def test_the_template_is_not_ignored(self) -> None:
        """🔴 鑑別力對照組：`.env.example` 必須 **不** 被忽略（rc≠0）。

        少了這條，把 `.gitignore` 寫成「連 .env.example 一起吃掉」也能讓上一條全綠，
        而那會讓範本永遠進不了 repo——正是本 repo 反覆記載的「把缺陷修成更嚴重的缺陷」。
        """
        for rel in (".env.example", "AutoClaude/.env.example"):
            with self.subTest(rel):
                self.assertNotEqual(
                    self._check_ignore(rel), 0,
                    f"{rel} 被 .gitignore 排除了——範本本來就該入庫"
                    "（根 .gitignore 的 `!.env.example`）",
                )


class TestSecretScanCriterion(unittest.TestCase):
    """層②的判準紅綠自證（純函式，餵合成語料——不在 repo 內留下任何違規樣本）。

    WHY 每一條綠側都寫出來：這道判準的**設計方向是寧可漏報也不要假報**，因為一道
    天天假紅的守衛會被整個關掉＝零防護。綠側就是那個方向的規格，少了它，下一個人
    「順手把判準收嚴一點」就會讓守衛在第一天被關掉，而沒有任何東西會轉紅。
    """

    #: (語料, 是否應命中, 這一條在守什麼)
    CASES = (
        ("MINIMAX_API_KEY=sk-abcdefghij0123456789ABCDEFGHIJ0123456789",  # secret-scan-ok: 合成語料
         True, "真 key 形態（sk- ＋ 長字串）"),
        ("MINIMAX_API_KEY=your_minimax_api_key_here", False, "佔位符必須放行"),
        ("POSTGRES_PASSWORD=autoclaude", False, "本機 dev 容器密碼（短、單字）必須放行"),
        ("#   國際版 key（sk-... from platform.minimax.io）", False,
         "註解裡的格式說明（sk- 後面是刪節號）必須放行"),
        ("#   中國版 key（sk-cp... from platform.minimaxi.com）", False,
         "同上，帶區域前綴的格式說明"),
        ("AUTOCLAUDE_DB_DSN=postgresql+asyncpg://autoclaude:autoclaude@localhost:5432/ac",
         False, "指向 localhost 的 DSN＝本機 dev，不是會外洩的憑證"),
        ("DSN=postgresql://admin:hunter2@db.prod.acme-corp.net/app",  # secret-scan-ok: 合成語料
         True, "指向外部主機且帶密碼的 DSN"),
        ("DSN=postgresql://admin:your_password_here@db.prod.acme-corp.net/app", False,
         "外部主機但密碼是佔位符 → 放行"),
        ("DSN=postgresql://admin:whatever@db.prod.example.com/app", False,
         "example.com 是 RFC 2606 保留的文件用網域 → 視為佔位符放行"),
        ("url = postgres://user:pass@postgres:5432/db", False,
         "裸主機名＝docker-compose 服務名，不是 production 端點"),
        ("token: ghp_0123456789abcdefghij0123456789abcdef",  # secret-scan-ok: 合成語料
         True, "GitHub token 前綴"),
        ("AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE", False,
         "AWS 官方文件的示範 key，字面含 EXAMPLE → 佔位符放行"),
        ("MY_TOKEN=<your-token>", False, "角括號佔位符"),
        ("SECRET_KEY=${SECRET_FROM_VAULT}", False, "shell/CI 插值不是機密本身"),
        ("PASSWORD=", False, "空值＝還沒填"),
    )

    def test_each_case_lands_on_the_intended_side(self) -> None:
        for line, should_hit, why in self.CASES:
            with self.subTest(why):
                hits = secret_scan.scan_line(line, env_shaped=True)
                self.assertEqual(
                    bool(hits), should_hit,
                    f"{why}：期望{'命中' if should_hit else '放行'}，實得 {hits}",
                )

    def test_the_high_entropy_rule_is_scoped_to_env_shaped_files(self) -> None:
        """🔴 射程鎖：`NAME=<高熵值>` 這一條**只**在 `.env` 形態的檔上生效。

        WHY（落地當回合的實測，不是假設）：把它套在全 repo 27,541 支檔上得到 **1,525 筆**
        命中，壓倒性多數是**文件裡的範例程式碼**（Markdown code block 裡的 `password=`／
        `token=`／`apiKey=`），再被 30 個凍結版本樹各複製一份放大。那種守衛第一天就會被
        關掉。收窄後全 repo 剩 158 筆、收斂到 5 個相異站點形態，且**活躍開發面零命中**。
        這一條就是那個收窄的規格：拿掉 `env_shaped` 條件會讓它當場紅。
        """
        line = "hashedPassword = a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
        self.assertEqual(
            secret_scan.scan_line(line, env_shaped=False), [],
            "非 .env 檔的高熵賦值不得命中——那是文件範例程式碼的形態，判紅即假紅海嘯",
        )
        self.assertTrue(
            secret_scan.scan_line(line, env_shaped=True),
            "同一行在 .env 形態的檔裡必須命中，否則收窄過頭＝這條判準等於不存在",
        )

    def test_a_pem_header_alone_is_not_a_private_key(self) -> None:
        """標頭不等於私鑰：安全基線**模板**裡的示意字串不得判紅（實測 30 個凍結樹各一次）。"""
        template = "-----BEGIN PRIVATE KEY-----\n<在此貼上你的私鑰>\n"
        self.assertEqual(
            secret_scan.scan_text(template, "doc.md"), [],
            "只有 PEM 標頭、沒有 key material ⇒ 是模板示意，不是私鑰",
        )
        body = "MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQ" * 2
        real = f"-----BEGIN PRIVATE KEY-----\n{body}\n"
        self.assertTrue(
            secret_scan.scan_text(real, "leaked.pem"),
            "標頭 ＋ 真的 key material ⇒ 必須命中",
        )

    def test_the_exemption_marker_is_line_end_only(self) -> None:
        """行尾豁免出口存在（否則本檔自己的合成語料無法入庫），但只認同一行。"""
        leaked = "KEY=sk-abcdefghij0123456789ABCDEFGHIJ"  # secret-scan-ok: 合成語料
        self.assertTrue(secret_scan.scan_line(leaked, env_shaped=True))
        exempted = f"{leaked}  # {secret_scan.EXEMPT_MARKER} 測試語料"
        self.assertEqual(secret_scan.scan_line(exempted, env_shaped=True), [])

    def test_findings_never_echo_the_secret_itself(self) -> None:
        """🔴 診斷訊息不得成為第二個外洩管道。

        WHY：這道守衛的失敗會被寫進 hook 輸出、CI log 與終端 scrollback。若訊息逐字印出
        命中的字串，守衛自己就把 key 又抄了一份到別的地方——而使用者以為自己被保護了。
        """
        secret = "sk-abcdefghij0123456789ABCDEFGHIJ0123456789"  # secret-scan-ok: 合成語料
        findings = secret_scan.scan_line(f"KEY={secret}", env_shaped=True)
        self.assertTrue(findings)
        for _rule, excerpt in findings:
            self.assertNotIn(secret, excerpt, "命中摘要逐字印出了機密本身")
            self.assertLess(len(excerpt), len(secret), "摘要沒有被遮蔽")


class TestRealTemplatesAreClean(unittest.TestCase):
    """層②套在**真檔案**上：repo 內每一支 tracked 的 `.env.example` 都必須是乾淨的。

    WHY 這條分開寫：上面那組是合成語料（證明判準有牙），這一條才是「今天這個 repo
    真的沒有把 key 貼進範本」。兩者不能互相取代——判準有牙不蘊含現況乾淨。
    """

    def test_every_tracked_env_template_has_no_secret(self) -> None:
        result = secret_scan.scan_tracked(REPO_ROOT, ".env.example", "*/.env.example")
        self.assertIsNone(result.error, f"取數管道壞掉：{result.error}")
        # 反空轉：一支都沒掃到時「零命中」沒有鑑別力。
        self.assertGreater(
            result.scanned, 0,
            "一支 .env.example 都沒進到掃描面 ⇒ pathspec 寫壞了，本鎖恆綠",
        )
        self.assertEqual(
            [f.render() for f in result.findings], [],
            "被追蹤的 .env 範本裡出現疑似真實機密——範本只能放佔位符",
        )


class TestPreCommitBlocksEnvFiles(unittest.TestCase):
    """層①的**行為級**證明：真 repo、真 `git add -f`、真 commit。

    WHY 一定要行為級：判準寫在 bash 裡，任何「讀 hook 原始碼找關鍵字」的測試都證明
    不了它真的會擋（本 repo 判例：`test_ps1_bom.py` 曾被指名為行尾守衛，實際零判準）。
    唯一算數的證據是 commit 真的失敗、且訊息指名了那支檔。
    """

    def setUp(self) -> None:
        self.assertTrue(DISPATCHER.is_file(), f"dispatcher 不存在：{DISPATCHER}")
        self.tmp = Path(tempfile.mkdtemp(prefix="pc_dispatcher_env_"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.assertEqual(_git("init", "-q", cwd=self.repo).returncode, 0)

        hooks_dir = self.repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        shutil.copy(DISPATCHER, hooks_dir / "pre-commit")
        os.chmod(hooks_dir / "pre-commit", 0o755)

        # 層②的機械物一併搬進沙盒，讓 hook 內的內容掃描這一段也真的被執行到
        # （不搬的話 hook 會走「缺件 → 出聲跳過」那條路，本類就只驗到層①）。
        lib_dir = self.repo / "tools" / "lib"
        lib_dir.mkdir(parents=True)
        for name in ("secret_scan.py", "windowsapps_guard.sh"):
            shutil.copy(_LIB_DIR / name, lib_dir / name)

        # AutoClaude 子 hook 存根：巢狀路徑的對照組需要它，否則 commit 會因為
        # 「子 hook 缺失」而失敗，測到的就不是本閘。
        sub_dir = self.repo / "AutoClaude" / "tools" / "git-hooks"
        sub_dir.mkdir(parents=True)
        (sub_dir / "pre-commit").write_text(
            "#!/usr/bin/env bash\nexit 0\n", encoding="utf-8", newline="\n")
        os.chmod(sub_dir / "pre-commit", 0o755)

        _git("config", "core.hooksPath", str(hooks_dir), cwd=self.repo)
        _git("config", "user.email", "test@example.com", cwd=self.repo)
        _git("config", "user.name", "Test", cwd=self.repo)

    def _stage(self, rel: str, text: str, force: bool = True) -> None:
        target = self.repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
        args = ["add", "-f", "--", rel] if force else ["add", "--", rel]
        add = _git(*args, cwd=self.repo)
        self.assertEqual(add.returncode, 0, add.stderr)

    def _commit(self, message: str, env: dict | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "commit", "-q", "-m", message],
            cwd=str(self.repo), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            env=dict(os.environ, **(env or {})), timeout=120,
        )

    def test_force_added_env_file_is_blocked(self) -> None:
        """🔴 主判準：`git add -f .env` 硬塞進 index 也要擋得住。

        `-f` 正是繞過 `.gitignore` 的那條路——忽略規則對「已明示暫存」完全不生效，
        所以只有讀 index 的守衛看得到它。
        """
        leak = "MINIMAX_API_KEY=sk-realkey0123456789abcdefghij\n"  # secret-scan-ok: 合成語料
        self._stage(".env", leak)
        commit = self._commit("try to leak .env")
        self.assertNotEqual(
            commit.returncode, 0,
            f"`.env` 進了 commit：\n{commit.stdout}\n{commit.stderr}",
        )
        blob = commit.stdout + commit.stderr
        self.assertIn(".env", blob, "擋下時必須指名是哪一支檔")
        self.assertIn("git rm --cached", blob, "訊息必須教人怎麼修，不能只說被擋下")

    def test_nested_env_file_is_blocked(self) -> None:
        """任意深度的子目錄同樣要守——真正住著憑證的就是 `AutoClaude/.env`。"""
        self._stage("AutoClaude/.env", "POSTGRES_PASSWORD=whatever\n")
        commit = self._commit("try to leak nested .env")
        self.assertNotEqual(commit.returncode, 0, f"巢狀 .env 進了 commit：\n{commit.stderr}")
        self.assertIn("AutoClaude/.env", commit.stdout + commit.stderr)

    def test_suffixed_env_variants_are_blocked(self) -> None:
        for rel in (".env.local", ".env.production", "sub/dir/.env.staging"):
            with self.subTest(rel):
                self._stage(rel, "SECRET=whatever\n")
                commit = self._commit(f"try {rel}")
                self.assertNotEqual(commit.returncode, 0, f"{rel} 進了 commit")
                _git("reset", "-q", "HEAD", "--", rel, cwd=self.repo)

    def test_the_skip_hooks_escape_hatch_does_not_bypass_this_gate(self) -> None:
        """🔴 這一條是本閘與其他閘門的**分界**。

        WHY：`AUTOCLAUDE_SKIP_HOOKS=1` 對其餘閘門是合理的緊急出口——那些擋的是
        「會壞掉但可以修」的東西。機密外洩不可逆：key 進了 object store 就再也拿不
        回來，push 出去更是只能去供應商後台輪替。對不可逆的後果留一個順手按得到的
        出口，等於沒有這道閘。故本閘刻意排在 SKIP 判定**之前**。
        """
        leak = "MINIMAX_API_KEY=sk-realkey0123456789abcdefghij\n"  # secret-scan-ok: 合成語料
        self._stage(".env", leak)
        commit = self._commit("skip hooks and leak", env={"AUTOCLAUDE_SKIP_HOOKS": "1"})
        self.assertNotEqual(
            commit.returncode, 0,
            f"AUTOCLAUDE_SKIP_HOOKS=1 繞過了機密外洩閘：\n{commit.stdout}\n{commit.stderr}",
        )

    def test_env_example_still_commits(self) -> None:
        """🔴 鑑別力對照組：把閘門寫成「一律擋含 .env 字樣的檔」也能讓上面全綠——

        那會讓範本永遠進不了 repo，使用者第一次 commit 就撞紅，守衛隨即被整個關掉。
        `.env.example` 必須通行無阻。
        """
        self._stage(".env.example", "MINIMAX_API_KEY=your_minimax_api_key_here\n", force=False)
        commit = self._commit("add template")
        self.assertEqual(
            commit.returncode, 0,
            f".env.example 被誤擋（守衛過度攔截）：\n{commit.stdout}\n{commit.stderr}",
        )

    def test_removing_a_tracked_env_file_is_allowed(self) -> None:
        """對照組：`git rm --cached` 正是本閘教人做的修法——它自己必須跑得過。

        少了這條，訊息教的修法會在執行時被同一道閘再擋一次，使用者無路可走。
        """
        self._stage(".env", "SECRET=whatever\n")
        # 先繞過閘門把它弄進歷史（模擬「已經被追蹤」的既成狀態）
        subprocess.run(["git", "commit", "-q", "-m", "seed", "--no-verify"],
                       cwd=str(self.repo), capture_output=True, timeout=120)
        rm = _git("rm", "-q", "--cached", "--", ".env", cwd=self.repo)
        self.assertEqual(rm.returncode, 0, rm.stderr)
        commit = self._commit("untrack .env")
        self.assertEqual(
            commit.returncode, 0,
            "`git rm --cached .env` 之後的 commit 被擋下——本閘教的修法自己走不通："
            f"\n{commit.stderr}",
        )

    def test_a_secret_pasted_into_a_tracked_template_is_blocked(self) -> None:
        """層②的端到端證明：檔名合法（`.env.example`）、內容是真 key ⇒ 仍須擋下。

        這是層①結構上看不到的那條路——範本本來就該入庫，任何以檔名為判準的守衛
        對它完全失明。
        """
        pasted = "MINIMAX_API_KEY=sk-abcdefghij0123456789ABCDEFGHIJ01\n"  # secret-scan-ok: 合成語料
        self._stage(".env.example", pasted, force=False)
        commit = self._commit("paste real key into template")
        self.assertNotEqual(
            commit.returncode, 0,
            f"真 key 被貼進 .env.example 卻放行了：\n{commit.stdout}\n{commit.stderr}",
        )


if __name__ == "__main__":
    unittest.main()
