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
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path, PurePosixPath, PureWindowsPath

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


if __name__ == "__main__":
    unittest.main()
