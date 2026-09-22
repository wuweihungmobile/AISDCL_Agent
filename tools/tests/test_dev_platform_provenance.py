#!/usr/bin/env python3
"""test_dev_platform_provenance — 意圖（Rule 9）：守住「dev_start [1/7] 回報
『專案上次在哪開發』必須來自 git、不能來自本機狀態檔」這件事（DEF-200-358，
2026-09-22）。讀端 `tools/lib/dev_platform_provenance.py` 與寫端
`tools/git-hooks/prepare-commit-msg` 任一端悄悄漂移，都會讓 [1/7] 的訊息退化回
「本機 state 檔恆等於 Now」的老錯誤；本檔用真 git 沙盒鎖住讀寫兩端契約。

執行：python -m unittest discover -s tools/tests -p "test_dev_platform_provenance.py" -v
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import dev_platform_provenance as m  # noqa: E402
import platform_utils  # noqa: E402

sys.path.insert(0, str(_REPO_ROOT / "tools"))
import check_hooks_liveness  # noqa: E402
import git_hooks_install_common  # noqa: E402

_HOOK_SRC = _REPO_ROOT / "tools" / "git-hooks" / "prepare-commit-msg"
_COMMIT_MSG_SRC = _REPO_ROOT / "tools" / "git-hooks" / "commit-msg"
_CLI_MODULE = _REPO_ROOT / "tools" / "lib" / "dev_platform_provenance.py"
_PY_EXE = sys.executable


def _git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    """跑一個 git 子指令；encoding 顯式 utf-8（zh-TW Windows 終端預設 cp950 會炸中文）。"""
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=60, env=env)


def _verdict(label, method, *, commit="abcd123", depth=1, commits_scanned=1,
             host=None, evidence=None) -> m.Verdict:
    return m.Verdict(label, method, commit, depth, commits_scanned, host=host,
                      evidence=evidence or ["dummy evidence"])


class _SandboxMixin:
    """建一個乾淨的臨時 git repo（不設 core.hooksPath）供 D／E／J 三組測試共用。"""

    def _make_repo(self) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="devplat_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        repo = tmp / "repo"
        repo.mkdir()
        self._git_ok("init", "-q", cwd=repo)
        self._git_ok("config", "user.email", "t@example.com", cwd=repo)
        self._git_ok("config", "user.name", "Tester", cwd=repo)
        self._git_ok("config", "commit.gpgsign", "false", cwd=repo)
        return repo

    def _git_ok(self, *args: str, cwd: Path, env: dict[str, str] | None = None):
        res = _git(*args, cwd=cwd, env=env)
        self.assertEqual(res.returncode, 0, res.stderr)
        return res

    def _write_and_commit(self, repo: Path, relpath: str, content: str, subject: str) -> None:
        path = repo / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self._git_ok("add", relpath, cwd=repo)
        self._git_ok("commit", "-m", subject, cwd=repo)

    def _commit_with_trailer(self, repo: Path, subject: str, label: str, host: str) -> None:
        msg = f"{subject}\n\nDev-Platform: {label}\nDev-Host: {host}"
        self._git_ok("commit", "--allow-empty", "-m", msg, cwd=repo)

    def _commit_unrelated(self, repo: Path, index: int) -> None:
        self._write_and_commit(repo, f"unrelated_{index}.txt", f"noise {index}\n",
                                f"chore: unrelated {index}")

    def _install_hook(self, repo: Path) -> None:
        """裝 prepare-commit-msg＋commit-msg 兩支（沙盒無 tools/lib ⇒ 走 uname 退回路徑）。"""
        hooks_dir = repo / "tools" / "git-hooks"
        hooks_dir.mkdir(parents=True)
        for src in (_HOOK_SRC, _COMMIT_MSG_SRC):
            dest = hooks_dir / src.name
            shutil.copy(src, dest)
            os.chmod(dest, 0o755)
        self._git_ok("config", "core.hooksPath", str(hooks_dir), cwd=repo)

    def _install_python_main_path(self, repo: Path, host_marker: str) -> None:
        """讓沙盒走 hook 的 python 主路徑：複製 guard 與模組、建真 venv 供 pick_repo_python 解析。

        複製進沙盒的模組尾端覆寫 current_host 為 marker——trailer 帶 marker 即證明走的是
        python 主路徑而非 uname 退回路徑（退回路徑用的是 hostname）。
        """
        lib = repo / "tools" / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        for name in ("windowsapps_guard.sh", "platform_utils.py", "dev_platform_provenance.py"):
            shutil.copy(_REPO_ROOT / "tools" / "lib" / name, lib / name)
        mod = lib / "dev_platform_provenance.py"
        guard = 'if __name__ == "__main__":'
        src = mod.read_text(encoding="utf-8")
        self.assertIn(guard, src)
        mod.write_text(src.replace(guard, f"current_host = lambda: {host_marker!r}\n{guard}"),
                       encoding="utf-8")
        res = subprocess.run(
            [_PY_EXE, "-m", "venv", "--without-pip", str(repo / ".venv")],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
        self.assertEqual(res.returncode, 0, res.stderr)

    def _editor_env(self, repo: Path, subject: str) -> dict[str, str]:
        """模擬互動式編輯器：把樣板第一行（空白 subject 佔位）填成 subject 後存檔。"""
        editor = repo.parent / "editor.py"
        editor.write_text(
            "import pathlib, sys\np = pathlib.Path(sys.argv[1])\n"
            "lines = p.read_text(encoding='utf-8').splitlines()\n"
            f"lines[0] = {subject!r}\n"
            "p.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')\n", encoding="utf-8")
        cmd = f'"{Path(_PY_EXE).as_posix()}" "{editor.as_posix()}"'
        return {**os.environ, "GIT_EDITOR": cmd}


class PureFunctionTests(unittest.TestCase):
    """純函式（無 git／無子行程）：平台映射同構、trailer 格式、diff 啟發式抽取。"""

    def test_label_for_sys_platform_maps_known_and_unknown_values(self):
        self.assertEqual(m.label_for_sys_platform("win32"), "windows")
        self.assertEqual(m.label_for_sys_platform("darwin"), "mac")
        self.assertEqual(m.label_for_sys_platform("linux"), "linux")
        self.assertEqual(m.label_for_sys_platform("freebsd"), "linux")

    def test_label_for_sys_platform_matches_platform_utils_os_label(self):
        for sp in ("win32", "darwin", "linux"):
            with mock.patch.object(sys, "platform", sp):
                self.assertEqual(platform_utils.os_label(), m.label_for_sys_platform(sp), sp)

    def test_trailer_lines_default_to_current_label_and_host(self):
        lines = m.trailer_lines()
        expected = [f"Dev-Platform: {m.current_label()}", f"Dev-Host: {m.current_host()}"]
        self.assertEqual(lines, expected)

    def test_trailer_lines_with_explicit_values(self):
        self.assertEqual(m.trailer_lines("mac", "mbp"), ["Dev-Platform: mac", "Dev-Host: mbp"])

    def test_current_host_falls_back_to_unknown_when_node_is_blank(self):
        with mock.patch.object(m._platform, "node", return_value=""):
            self.assertEqual(m.current_host(), "unknown")

    def test_current_host_strips_embedded_newlines(self):
        with mock.patch.object(m._platform, "node", return_value="host\r\nname"):
            host = m.current_host()
        self.assertNotIn("\n", host)
        self.assertNotIn("\r", host)

    def test_darwin_anchor_line_is_detected(self):
        diff = "+<!-- snapshot-fingerprints-darwin: v001=abc -->\n"
        labels, evidence = m.heuristic_labels_from_diff(diff)
        self.assertEqual(labels, {"mac"})
        self.assertTrue(evidence)

    def test_win32_anchor_line_is_detected(self):
        labels, _ = m.heuristic_labels_from_diff("+<!-- snapshot-fingerprints-win32: v=1 -->\n")
        self.assertEqual(labels, {"windows"})

    def test_perf_baseline_darwin_environment_is_detected(self):
        labels, _ = m.heuristic_labels_from_diff('+environment = "darwin-local"\n')
        self.assertEqual(labels, {"mac"})

    def test_both_anchors_in_one_diff_yield_two_labels(self):
        diff = ("+<!-- snapshot-fingerprints-darwin: v=a -->\n"
                "+<!-- snapshot-fingerprints-win32: v=b -->\n")
        labels, _ = m.heuristic_labels_from_diff(diff)
        self.assertEqual(labels, {"mac", "windows"})

    def test_diff_header_and_deletion_lines_are_not_counted(self):
        diff = "+++ b/ONBOARDING.md\n-<!-- snapshot-fingerprints-darwin: v001=old -->\n"
        labels, evidence = m.heuristic_labels_from_diff(diff)
        self.assertEqual(labels, set())
        self.assertEqual(evidence, [])


class InferRecentPlatformTests(_SandboxMixin, unittest.TestCase):
    """守 tools/lib/dev_platform_provenance.py 讀端：trailer 優先、矛盾／未知不猜。"""

    def test_trailer_commit_is_decisive_over_heuristics(self):
        repo = self._make_repo()
        self._commit_with_trailer(repo, "feat: root", "mac", "mbp")
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.label, v.method, v.depth, v.host), ("mac", "trailer", 1, "mbp"))

    def test_duplicate_platform_trailers_resolve_to_the_last_one(self):
        """同鍵多列取最後一列（hook 以最後一列為本機值），並在 evidence 留註記。"""
        repo = self._make_repo()
        msg = "s\n\nDev-Platform: mac\nDev-Host: old\nDev-Platform: linux\nDev-Host: new"
        self._git_ok("commit", "--allow-empty", "-m", msg, cwd=repo)
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.label, v.host), ("linux", "new"))
        self.assertTrue(any("多列" in e for e in v.evidence), v.evidence)

    def test_onboarding_darwin_anchor_is_heuristic_signal(self):
        repo = self._make_repo()
        content = "docs\n<!-- snapshot-fingerprints-darwin: v001=abc -->\n"
        self._write_and_commit(repo, "ONBOARDING.md", content, "docs: fingerprint")
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.label, v.method), ("mac", "heuristic"))
        self.assertIn("darwin", v.evidence[0])

    def test_perf_baseline_win32_environment_is_heuristic_signal(self):
        repo = self._make_repo()
        self._write_and_commit(repo, "AutoClaude/.perf_baseline.toml",
                               'environment = "win32-local"\n', "chore: perf baseline")
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.label, v.method), ("windows", "heuristic"))

    def test_signal_less_head_falls_through_to_parent_trailer(self):
        repo = self._make_repo()
        self._commit_with_trailer(repo, "feat: root", "mac", "mbp")
        self._commit_unrelated(repo, 0)
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.label, v.depth, v.commits_scanned), ("mac", 2, 2))

    def test_all_signal_less_commits_report_unknown_with_scan_count(self):
        repo = self._make_repo()
        for i in range(3):
            self._commit_unrelated(repo, i)
        v = m.infer_recent_platform(repo)
        self.assertIsNone(v.label)
        self.assertEqual((v.method, v.commits_scanned), ("unknown", 3))
        self.assertIn("3 個 commit", v.evidence[0])

    def test_contradictory_signals_in_one_commit_are_skipped(self):
        repo = self._make_repo()
        content = ("docs\n<!-- snapshot-fingerprints-darwin: v001=a -->\n"
                    "<!-- snapshot-fingerprints-win32: v001=b -->\n")
        self._write_and_commit(repo, "ONBOARDING.md", content, "docs: both anchors")
        v = m.infer_recent_platform(repo)
        self.assertIsNone(v.label)
        self.assertTrue(any("矛盾" in e for e in v.evidence))

    def test_unknown_trailer_value_is_not_trusted(self):
        repo = self._make_repo()
        self._commit_with_trailer(repo, "feat: root", "amiga", "somehost")
        v = m.infer_recent_platform(repo)
        self.assertIsNone(v.label)
        self.assertTrue(any("amiga" in e for e in v.evidence))

    def test_max_commits_bounds_the_scan_depth(self):
        repo = self._make_repo()
        self._commit_with_trailer(repo, "feat: root", "mac", "mbp")
        self._commit_unrelated(repo, 0)
        v = m.infer_recent_platform(repo, max_commits=1)
        self.assertIsNone(v.label)
        self.assertEqual(v.commits_scanned, 1)

    def test_non_git_directory_reports_unknown_with_zero_scanned(self):
        tmp = Path(tempfile.mkdtemp(prefix="devplat_notrepo_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        v = m.infer_recent_platform(tmp)
        self.assertIsNone(v.label)
        self.assertEqual(v.commits_scanned, 0)
        self.assertIn("rev-list", v.evidence[0])


class HookBehaviorTests(_SandboxMixin, unittest.TestCase):
    """prepare-commit-msg 寫端契約：--no-verify 仍寫入、SKIP_HOOKS 才略過、amend 取代舊值。"""

    def test_normal_commit_gets_platform_and_host_trailers(self):
        repo = self._make_repo()
        self._install_hook(repo)
        self._git_ok("commit", "--allow-empty", "-m", "feat: normal", cwd=repo)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        self.assertIn(f"Dev-Platform: {m.current_label()}", msg)
        self.assertRegex(msg, r"Dev-Host: \S+")

    def test_no_verify_still_gets_trailer_because_git_never_skips_this_hook(self):
        repo = self._make_repo()
        self._install_hook(repo)
        self._git_ok("commit", "--allow-empty", "--no-verify", "-m", "chore: nv", cwd=repo)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        self.assertIn(f"Dev-Platform: {m.current_label()}", msg)

    def test_skip_hooks_env_var_suppresses_the_trailer(self):
        repo = self._make_repo()
        self._install_hook(repo)
        env = {**os.environ, "AUTOCLAUDE_SKIP_HOOKS": "1"}
        self._git_ok("commit", "--allow-empty", "-m", "chore: skip", cwd=repo, env=env)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        self.assertNotIn("Dev-Platform", msg)

    def test_amend_replaces_stale_trailer_with_local_value(self):
        repo = self._make_repo()
        self._install_hook(repo)
        env = {**os.environ, "AUTOCLAUDE_SKIP_HOOKS": "1"}
        stale = "chore: fake\n\nDev-Platform: amiga\nDev-Host: nowhere"
        self._git_ok("commit", "--allow-empty", "-m", stale, cwd=repo, env=env)
        self._git_ok("commit", "--amend", "--allow-empty", "--no-edit", cwd=repo)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        lines = [ln for ln in msg.splitlines() if ln.startswith("Dev-Platform:")]
        self.assertEqual(lines, [f"Dev-Platform: {m.current_label()}"])

    def test_two_commits_each_get_exactly_one_platform_line(self):
        repo = self._make_repo()
        self._install_hook(repo)
        self._git_ok("commit", "--allow-empty", "-m", "first", cwd=repo)
        self._git_ok("commit", "--allow-empty", "-m", "second", cwd=repo)
        for rev in ("HEAD", "HEAD~1"):
            msg = self._git_ok("log", "-1", "--format=%B", rev, cwd=repo).stdout
            lines = [ln for ln in msg.splitlines() if ln.startswith("Dev-Platform:")]
            self.assertEqual(len(lines), 1, msg)

    def test_written_trailer_round_trips_through_infer_recent_platform(self):
        repo = self._make_repo()
        self._install_hook(repo)
        self._git_ok("commit", "--allow-empty", "-m", "feat: round-trip", cwd=repo)
        v = m.infer_recent_platform(repo)
        self.assertEqual((v.method, v.label), ("trailer", m.current_label()))

    def test_interactive_editor_commit_gets_a_parsable_trailer_block(self):
        """互動式 commit（樣板 subject 空白→編輯器填入）：trailer 必須成獨立段落，git 才認得。

        複審實測：prepare-commit-msg 若在編輯器開啟前就插 trailer，會與之後填的 subject 黏成
        同一段落而 `%(trailers)` 回空——本鎖直接以 git 自己的 trailer 解析為判準。
        """
        repo = self._make_repo()
        self._install_hook(repo)
        env = self._editor_env(repo, "feat: typed in editor")
        self._git_ok("commit", "--allow-empty", cwd=repo, env=env)
        fmt = "--format=%(trailers:key=Dev-Platform,valueonly)"
        got = self._git_ok("log", "-1", fmt, cwd=repo).stdout.strip()
        self.assertEqual(got, m.current_label())

    def test_allow_empty_message_commit_is_left_alone_without_crashing(self):
        repo = self._make_repo()
        self._install_hook(repo)
        self._git_ok("commit", "--allow-empty", "--allow-empty-message", "-m", "", cwd=repo)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        self.assertNotIn("Dev-Platform", msg)

    def test_existing_trailers_stay_recognised_after_ours_are_added(self):
        repo = self._make_repo()
        self._install_hook(repo)
        body = "feat: coauthored\n\nbody line\n\nCo-Authored-By: Pair <pair@example.com>"
        self._git_ok("commit", "--allow-empty", "-m", body, cwd=repo)
        fmt = ("--format=%(trailers:key=Co-Authored-By,valueonly)%n"
               "%(trailers:key=Dev-Platform,valueonly)")
        out = self._git_ok("log", "-1", fmt, cwd=repo).stdout.split()
        self.assertEqual(out, ["Pair", "<pair@example.com>", m.current_label()])

    def test_python_main_path_is_taken_when_repo_venv_and_module_exist(self):
        """主路徑鎖：沙盒有根層 .venv 與 tools/lib 時，hook 必須走 python SSOT 而非 uname 退回。"""
        repo = self._make_repo()
        self._install_hook(repo)
        self._install_python_main_path(repo, "MAIN-PATH-MARKER")
        self._git_ok("commit", "--allow-empty", "-m", "feat: main path", cwd=repo)
        msg = self._git_ok("log", "-1", "--format=%B", cwd=repo).stdout
        self.assertIn("Dev-Host: MAIN-PATH-MARKER", msg)
        self.assertIn(f"Dev-Platform: {m.current_label()}", msg)


class ApplyTrailersTests(unittest.TestCase):
    """apply_trailers()：樣板延後、註解區塊保留、同鍵剝除、既有 trailer 段落併入。"""

    def _run(self, content: str, **kw) -> tuple[str, str]:
        tmp = Path(tempfile.mkdtemp(prefix="devplat_msg_"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "COMMIT_EDITMSG"
        path.write_text(content, encoding="utf-8")
        status = m.apply_trailers(path, label="mac", host="mbp", **kw)
        return status, path.read_text(encoding="utf-8")

    def test_blank_template_is_deferred_and_left_untouched(self):
        tpl = "\n# Please enter the commit message\n#\n"
        self.assertEqual(self._run(tpl, defer_if_blank=True), ("deferred", tpl))

    def test_blank_final_message_gets_no_trailer(self):
        self.assertEqual(self._run("\n"), ("blank", "\n"))

    def test_comment_block_stays_after_the_trailer_paragraph(self):
        status, text = self._run("feat: x\n\n# Please enter\n# more\n")
        self.assertEqual(status, "applied")
        self.assertEqual(text.splitlines(), ["feat: x", "", "Dev-Platform: mac", "Dev-Host: mbp",
                                             "", "# Please enter", "# more"])

    def test_stale_duplicate_keys_are_stripped_before_rewrite(self):
        _, text = self._run("s\n\nDev-Platform: amiga\nDev-Host: z\nDev-Platform: linux\n")
        own = [ln for ln in text.splitlines() if ln.startswith("Dev-")]
        self.assertEqual(own, ["Dev-Platform: mac", "Dev-Host: mbp"])

    def test_existing_trailer_paragraph_is_extended_not_split(self):
        _, text = self._run("s\n\nbody\n\nCo-Authored-By: A <a@x>\n")
        self.assertEqual(text.splitlines()[-3:],
                         ["Co-Authored-By: A <a@x>", "Dev-Platform: mac", "Dev-Host: mbp"])

    def test_subject_that_looks_like_a_trailer_is_not_merged_with(self):
        _, text = self._run("Fix: subject only\n")
        self.assertEqual(text.splitlines(),
                         ["Fix: subject only", "", "Dev-Platform: mac", "Dev-Host: mbp"])


class StaticAndWiringLockTests(unittest.TestCase):
    """hook 檔本身與其消費端的靜態契約：fail-open、五支 dispatcher 佈線一致、舊字面已移除。"""

    def test_hook_file_exists(self):
        self.assertTrue(_HOOK_SRC.is_file())

    def test_hook_is_tracked_as_executable_100755(self):
        res = _git("ls-files", "-s", "tools/git-hooks/prepare-commit-msg", cwd=_REPO_ROOT)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(res.stdout.startswith("100755"), res.stdout)

    def test_hook_has_bash_shebang_and_no_cr(self):
        text = _HOOK_SRC.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertEqual([i for i, ln in enumerate(text.splitlines(True), 1) if "\r" in ln], [])

    def test_hook_contains_required_tokens(self):
        text = _HOOK_SRC.read_text(encoding="utf-8")
        for token in ("AUTOCLAUDE_SKIP_HOOKS", "interpret-trailers", "--if-exists replace",
                      "Dev-Platform", "Dev-Host", "pick_repo_python",
                      "dev_platform_provenance.py", "--apply-trailers", "--defer-if-blank",
                      "commit-msg-final"):
            self.assertIn(token, text)

    def test_commit_msg_shim_exists_executable_and_delegates(self):
        res = _git("ls-files", "-s", "tools/git-hooks/commit-msg", cwd=_REPO_ROOT)
        self.assertTrue(res.stdout.startswith("100755"), res.stdout)
        text = _COMMIT_MSG_SRC.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("#!/usr/bin/env bash\n"))
        self.assertEqual([i for i, ln in enumerate(text.splitlines(True), 1) if "\r" in ln], [])
        for token in ("AUTOCLAUDE_SKIP_HOOKS", "prepare-commit-msg", "commit-msg-final"):
            self.assertIn(token, text)

    def test_every_non_comment_exit_is_exit_0(self):
        text = _HOOK_SRC.read_text(encoding="utf-8")
        for line in text.splitlines():
            code = line.split("#", 1)[0]
            for hit in re.finditer(r"\bexit\s+(\S+)", code):
                self.assertEqual(hit.group(1), "0", line)

    def test_hook_filenames_are_shared_across_liveness_and_installer(self):
        self.assertEqual(check_hooks_liveness.HOOK_FILENAMES,
                          git_hooks_install_common.HOOK_FILENAMES)
        self.assertIn("prepare-commit-msg", check_hooks_liveness.HOOK_FILENAMES)
        self.assertIn("commit-msg", check_hooks_liveness.HOOK_FILENAMES)
        for name in check_hooks_liveness.HOOK_FILENAMES:
            self.assertTrue((_REPO_ROOT / "tools" / "git-hooks" / name).is_file(), name)

    def test_dev_start_wires_into_git_provenance_not_local_state_only(self):
        text = (_REPO_ROOT / "tools" / "dev_start.py").read_text(encoding="utf-8")
        self.assertIn("dev_platform_provenance.report_env_detection(", text)
        self.assertIn("import dev_platform_provenance", text)
        old = "Developing（上次開發）"
        printed = [ln for ln in text.splitlines() if "print(" in ln and old in ln]
        self.assertEqual(printed, [])


class ReportEnvDetectionTests(unittest.TestCase):
    """report_env_detection() 三行報告與摘要句：本機切換與 git 判定的優先序不得覆蓋。"""

    def _run(self, *, now, developing, is_repo, verdict):
        lines: list[str] = []
        warn = mock.Mock()
        with mock.patch.object(m, "infer_recent_platform", return_value=verdict) as infer:
            summary = m.report_env_detection(
                Path("."), now=now, developing=developing, host="h",
                is_repo=is_repo, print_fn=lines.append, warn=warn)
        return summary, lines, warn, infer

    def test_git_says_mac_now_windows_reports_cross_machine_switch(self):
        v = _verdict("mac", "trailer", commit="abc1234", host="mbp",
                      evidence=["Dev-Platform trailer=mac"])
        summary, lines, warn, _ = self._run(now="windows", developing="windows",
                                             is_repo=True, verdict=v)
        self.assertTrue(any("→ 跨機切換（依 git）：mac → windows" in ln for ln in lines))
        self.assertEqual(summary, "mac → windows（跨機切換，git 判定）")
        warn.assert_not_called()

    def test_git_and_now_agree_reports_no_switch(self):
        summary, *_ = self._run(now="windows", developing="windows", is_repo=True,
                                 verdict=_verdict("windows", "trailer"))
        self.assertEqual(summary, "windows（無切換；git 最近 commit 亦為 windows）")

    def test_unknown_verdict_warns_and_says_undeterminable(self):
        v = _verdict(None, "unknown", evidence=["3 個 commit 皆無 trailer 且無內容線索"])
        summary, _, warn, _ = self._run(now="windows", developing="windows",
                                         is_repo=True, verdict=v)
        warn.assert_called_once()
        self.assertIn("無法從 git 判定", warn.call_args[0][0])
        self.assertIn("git 無法判定", summary)

    def test_local_state_switch_takes_precedence_in_summary(self):
        summary, lines, *_ = self._run(now="windows", developing="mac", is_repo=True,
                                        verdict=_verdict("windows", "trailer"))
        self.assertTrue(any("本機跨平台切換" in ln for ln in lines))
        self.assertEqual(summary, "mac → windows（本機已切換）")

    def test_non_repo_skips_git_inference_entirely(self):
        summary, lines, _, infer = self._run(
            now="windows", developing="windows", is_repo=False,
            verdict=_verdict("windows", "trailer"))
        self.assertTrue(any("非 git repo" in ln for ln in lines))
        self.assertEqual(summary, "windows（無切換）")
        infer.assert_not_called()

    def test_first_run_with_no_local_state_notes_first_record(self):
        summary, *_ = self._run(now="windows", developing=None, is_repo=True,
                                 verdict=_verdict("windows", "trailer"))
        self.assertIn("首次紀錄", summary)

    def test_heuristic_depth_is_surfaced_in_output(self):
        v = _verdict("mac", "heuristic", commit="abcd123", depth=2, commits_scanned=2,
                      evidence=["ONBOARDING snapshot-fingerprints-darwin 錨變動"])
        _, lines, *_ = self._run(now="mac", developing="mac", is_repo=True, verdict=v)
        self.assertTrue(any("往回第 2 個 commit" in ln for ln in lines))


class CliTests(_SandboxMixin, unittest.TestCase):
    """CLI 三種模式的行為契約：--trailers 給 hook 消費、--json 給人／機器讀、rc 反映判定。"""

    def _run_cli(self, *extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [_PY_EXE, str(_CLI_MODULE), *extra],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)

    def test_trailers_flag_prints_exactly_two_prefixed_lines(self):
        res = self._run_cli("--trailers")
        self.assertEqual(res.returncode, 0, res.stderr)
        lines = res.stdout.strip("\n").splitlines()
        self.assertEqual(len(lines), 2, res.stdout)
        self.assertTrue(lines[0].startswith("Dev-Platform: "), lines[0])
        self.assertTrue(lines[1].startswith("Dev-Host: "), lines[1])

    def test_json_mode_reports_the_trailer_backed_label(self):
        repo = self._make_repo()
        self._commit_with_trailer(repo, "root", "mac", "mbp")
        res = self._run_cli("--json", "--repo-root", str(repo))
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(json.loads(res.stdout)["label"], "mac")

    def test_undeterminable_repo_exits_nonzero(self):
        repo = self._make_repo()
        for i in range(3):
            self._commit_unrelated(repo, i)
        res = self._run_cli("--repo-root", str(repo))
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)


if __name__ == "__main__":
    unittest.main()
