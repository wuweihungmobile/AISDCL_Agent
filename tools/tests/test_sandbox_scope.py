#!/usr/bin/env python3
"""`tools/lib/sandbox_scope.py`＋`tools/lib/endurance_env.py` job 環境允許表
＋`tools/lib/engine_resume_job.py::expiry_ps` 的驗收測試。

規格：docs/03_testing/contracts/TCS-SideEffectIsolation-20261120.md（AT-SE-02／03／04／
05／06／07／08／09／11〔後端半〕／15〔job argv 半〕／16／35／37／40／45／48〔本棒可及的半〕
／49〔job_env_argv 半〕）；DES §3、§4.1、§5.4。
WHY（Rule 9）：2026-11-20 幽靈 session 57d0ccad——沙盒的 park 排程以登入者真環境到點開窗；
產品面沒有任何判準問「這個目標是不是驗證沙盒、主人還在不在」。這裡每條斷言都對應
「拿掉那個判準就會重演事故」的一種走法（MU-SE-01～06、18、21、22、29、30、32）。
判準自己不讀環境變數、不開行程，所以測試也不靠任何環境變數鉤：
主人存活用真本行程（pid＋真建立時間），死亡／錯位以 `proc_probe` 縫模擬。
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))

import endurance_env  # noqa: E402
import engine_resume_job as erj  # noqa: E402
import sandbox_scope as ss  # noqa: E402

NOW = datetime.now().astimezone().replace(microsecond=0)


def _sandbox(parent: Path, name: str = "AutoSDD_RV_sbx_t1") -> Path:
    home = parent / name
    (home / ".git").mkdir(parents=True)
    ss.write_identity(home, run_id="r1", sid="s1", owner_pid=os.getpid(), now=NOW)
    return home


def _pkg(parent: Path, repo: Path, name: str = "p.md") -> Path:
    path = parent / name
    path.write_text(f"# 交接包\n- 來源 session：s\n- repo 根：{repo}\n", encoding="utf-8")
    return path


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()


class IdentityAndHomeTest(_Tmp):
    def test_at_se_02_is_sandbox_main_proof_is_identity_file_and_fallback_is_name(self) -> None:
        """is_sandbox：身分檔主證、路徑段／slug 副證；上一層身分檔（worktree 的 wt）也算；
        一般 tmp 不算。"""
        plain = self.tmp / "plain_repo"
        (plain / ".git").mkdir(parents=True)
        self.assertFalse(ss.is_sandbox(plain))
        marked = self.tmp / "no_prefix_name"
        marked.mkdir()
        ss.write_identity(marked, run_id="r", sid="s", owner_pid=os.getpid(), now=NOW)
        self.assertTrue(ss.is_sandbox(marked))  # ①身分檔、名稱無前綴
        (marked / "wt").mkdir()
        self.assertTrue(ss.is_sandbox(marked / "wt"))  # ⑤身分檔在上一層
        # ②大小寫異、無身分檔：判準走 normcase＝只在大小寫不敏感檔案系統（Windows）才同名；
        # POSIX 上 `autosdd_rv_SBX_x` 是另一個目錄名，不得誤認為沙盒（那會把一般目錄鎖成唯讀）
        self.assertEqual(
            ss.is_sandbox(self.tmp / "autosdd_rv_SBX_x"), os.path.normcase("A") == "a"
        )
        self.assertTrue(ss.is_sandbox(self.tmp / "C--x-AutoSDD-RV-sbx-abc"))  # ③slug 段（原大小寫）
        self.assertEqual(
            ss.sandbox_home(self.tmp / "AutoSDD_RV_sbx_q" / "a" / "b").name.lower(),
            "autosdd_rv_sbx_q",
        )

    def test_at_se_04_grant_clamps_to_lease_max_and_cap_and_revoke_nulls(self) -> None:
        """grant：+120→+30；+400（max 600）→+300；+200（max 300）→+200；revoke→null（MU-SE-04）。"""
        home = _sandbox(self.tmp)

        def read():
            return json.loads((home / ss.IDENTITY_NAME).read_text(encoding="utf-8"))["allow_until"]

        self.assertEqual((ss.LEASE_MAX, ss.LEASE_CAP), (30, 300))
        self.assertEqual(
            ss.grant(home, until=NOW + timedelta(minutes=120), now=NOW), NOW + timedelta(minutes=30)
        )
        self.assertEqual(datetime.fromisoformat(read()), NOW + timedelta(minutes=30))
        ss.grant(home, until=NOW + timedelta(minutes=400), now=NOW, max_minutes=600)
        self.assertEqual(datetime.fromisoformat(read()), NOW + timedelta(minutes=300))
        ss.grant(home, until=NOW + timedelta(minutes=200), now=NOW, max_minutes=300)
        self.assertEqual(datetime.fromisoformat(read()), NOW + timedelta(minutes=200))
        ss.revoke(home)
        self.assertIsNone(read())
        self.assertEqual(list(home.glob("*.tmp")), [])  # 原子寫：不留暫存檔

    def test_git_root_walks_up_and_accepts_a_dot_git_file(self) -> None:
        """git_root：往上找 `.git`（worktree 的 `.git` 是檔案）；找不到回原路徑；
        形態不同的同一路徑相等。"""
        repo = self.tmp / "Repo"
        (repo / "a" / "b").mkdir(parents=True)
        (repo / ".git").write_text("gitdir: x\n", encoding="utf-8")
        self.assertEqual(
            ss.git_root(repo / "a" / "b"),
            ss.git_root(str(repo).upper() if os.name == "nt" else repo),
        )
        self.assertEqual(
            ss.git_root(self.tmp / "nowhere"), Path(os.path.normcase(str(self.tmp / "nowhere")))
        )


class VerdictTest(_Tmp):
    def test_at_se_03_job_in_sandbox_copy_without_lease_is_refused(self) -> None:
        """排程 job 跑沙盒內 tools 複本（cwd、pkg 檔頭 repo 根、slug 全是沙盒）卻無租約 ⇒
         sandbox_no_lease（MU-SE-03 的前提）。"""
        home = _sandbox(self.tmp)
        verdict = ss.target_verdict(cwd=home, pkg=_pkg(home, home), now=NOW)
        self.assertEqual((verdict.allow, verdict.reason), (False, "sandbox_no_lease"))

    def test_at_se_06_lease_needs_a_provably_living_owner(self) -> None:
        """主人活／未過期→allow；主人死→owner_dead；過期→lease_expired；null→no_lease；
        活但建立時間不符→owner_dead。"""
        home = _sandbox(self.tmp)
        kw = {"cwd": home, "now": NOW}
        ss.grant(home, until=NOW + timedelta(minutes=20), now=NOW)
        self.assertEqual(ss.target_verdict(**kw).reason, "sandbox_lease")
        with mock.patch.object(ss, "proc_probe", return_value=(False, None)):
            self.assertEqual(ss.target_verdict(**kw).reason, "sandbox_owner_dead")
        started = json.loads((home / ss.IDENTITY_NAME).read_text(encoding="utf-8"))["owner_started"]
        if started:  # 取得到建立時間的平台才有「pid 重用」這一格
            other = (datetime.fromisoformat(started) + timedelta(hours=1)).isoformat()
            with mock.patch.object(ss, "proc_probe", return_value=(True, other)):
                self.assertEqual(ss.target_verdict(**kw).reason, "sandbox_owner_dead")
        self.assertEqual(
            ss.target_verdict(cwd=home, now=NOW + timedelta(minutes=21)).reason,
            "sandbox_lease_expired",
        )
        ss.revoke(home)
        self.assertEqual(ss.target_verdict(**kw).reason, "sandbox_no_lease")

    def test_at_se_07_root_mismatch_and_normalised_production(self) -> None:
        """cwd 正式、pkg 的 repo 根是沙盒 ⇒ root_mismatch；兩者同為正式 repo（大小寫不同）⇒
         allow production；worktree `.git` 檔。"""
        home = _sandbox(self.tmp)
        prod = self.tmp / "Prod"
        (prod / "sub").mkdir(parents=True)
        (prod / ".git").mkdir()
        mismatch = ss.target_verdict(cwd=prod / "sub", pkg=_pkg(self.tmp, home), now=NOW)
        self.assertEqual(mismatch.reason, "root_mismatch")
        same = ss.target_verdict(
            cwd=prod / "sub",
            pkg=_pkg(self.tmp, Path(str(prod).swapcase()) if os.name == "nt" else prod, "q.md"),
            now=NOW,
        )
        self.assertEqual((same.allow, same.reason), (True, "production"))
        wt = self.tmp / "AutoSDD_RV_sbx_wt" / "wt"
        wt.mkdir(parents=True)
        (wt / ".git").write_text("gitdir: ../x\n", encoding="utf-8")
        self.assertEqual(
            ss.git_root(wt / "deep" if (wt / "deep").exists() else wt), ss.git_root(wt)
        )

    def test_at_se_08_missing_targets_only_matter_when_a_sandbox_is_flagged(self) -> None:
        """沙盒家已刪、pkg 指向它→target_missing；沙盒在而 pkg 檔已刪→target_missing；
        正式 pkg 已刪→allow production。"""
        gone = self.tmp / "AutoSDD_RV_sbx_gone"
        prod = self.tmp / "Prod"
        (prod / ".git").mkdir(parents=True)
        self.assertEqual(
            ss.target_verdict(cwd=prod, pkg=_pkg(self.tmp, gone), now=NOW).reason, "target_missing"
        )
        home = _sandbox(self.tmp, "AutoSDD_RV_sbx_ok")
        self.assertEqual(
            ss.target_verdict(cwd=home, pkg=home / "handoff" / "absent.md", now=NOW).reason,
            "target_missing",
        )
        self.assertEqual(
            ss.target_verdict(cwd=prod, pkg=self.tmp / "deleted_prod_pkg.md", now=NOW).reason,
            "production",
        )

    def test_at_se_09_unreadable_identity_fails_closed_with_the_exception_class(self) -> None:
        """身分檔亂碼／schema 2→sandbox_unreadable；
        讀取拋 PermissionError→error:PermissionError（不是放行）。"""
        home = _sandbox(self.tmp)
        ident = home / ss.IDENTITY_NAME
        ident.write_bytes(b"\xff\xfe\x00garbage")
        self.assertEqual(ss.target_verdict(cwd=home, now=NOW).reason, "sandbox_unreadable")
        ident.write_text(json.dumps({"schema": 2, "owner_pid": 1}), encoding="utf-8")
        self.assertEqual(ss.target_verdict(cwd=home, now=NOW).reason, "sandbox_unreadable")
        with mock.patch.object(Path, "read_text", side_effect=PermissionError("x")):
            verdict = ss.target_verdict(cwd=home, now=NOW)
        self.assertEqual((verdict.allow, verdict.reason), (False, "error:PermissionError"))

    def test_at_se_45_real_exe_matrix(self) -> None:
        """exe 矩陣（MU-SE-26）：非 spawn 類 allow；
        `claude`／家外／`..` 逃出且 window=false→sandbox_real_exe；window=true 皆 allow；
        家下 allow；不查 PATH。"""
        home = _sandbox(self.tmp)
        ss.grant(home, until=NOW + timedelta(minutes=20), now=NOW)
        inside, outside = home / "bin" / "claude.exe", self.tmp / "out" / "claude.exe"
        escape = home / "bin" / ".." / ".." / "out" / "claude.exe"
        verdict = lambda exe: ss.target_verdict(cwd=home, exe=exe, now=NOW).reason  # noqa: E731
        self.assertEqual(verdict(None), "sandbox_lease")
        for exe in ("claude", str(outside), str(escape)):
            self.assertEqual(verdict(exe), "sandbox_real_exe", exe)
        self.assertEqual(verdict(str(inside)), "sandbox_lease")
        self.assertEqual(
            verdict(str(inside).swapcase() if os.name == "nt" else str(inside)), "sandbox_lease"
        )
        with mock.patch.dict(
            os.environ, {"PATH": ""}
        ):  # 判準不查 PATH（此處改 PATH 只為證明判決相同）
            self.assertEqual(verdict("claude"), "sandbox_real_exe")
        ss.grant(home, until=NOW + timedelta(minutes=20), now=NOW, window=True)
        for exe in ("claude", str(outside), str(escape), str(inside)):
            self.assertEqual(verdict(exe), "sandbox_lease", exe)
        prod = self.tmp / "Prod"
        (prod / ".git").mkdir(parents=True)
        self.assertEqual(ss.target_verdict(cwd=prod, exe="claude", now=NOW).reason, "production")
        self.assertFalse(ss.exe_in_home("claude", home))

    def test_at_se_40_register_verdict_compares_fire_with_the_lease(self) -> None:
        """fire_at＝allow_until−1 分→allow；＋1 分→lease_shorter_than_fire（MU-SE-18）；job_expiry：
        正式 None／沙盒＝allow_until。"""
        home = _sandbox(self.tmp)
        until = ss.grant(home, until=NOW + timedelta(minutes=20), now=NOW)
        ok = ss.register_verdict(cwd=home, fire_at=until - timedelta(minutes=1), now=NOW)
        late = ss.register_verdict(cwd=home, fire_at=until + timedelta(minutes=1), now=NOW)
        self.assertEqual(
            (ok.allow, late.allow, late.reason), (True, False, "lease_shorter_than_fire")
        )
        self.assertEqual(ss.job_expiry(ss.sandbox_home(home), NOW), until)
        self.assertIsNone(ss.job_expiry(None, NOW))
        ss.revoke(home)
        self.assertIsNone(ss.job_expiry(ss.sandbox_home(home), NOW))


class PurityTest(unittest.TestCase):
    def test_at_se_05_module_reads_no_environment_and_opens_no_process(self) -> None:
        """AST：無 environ／getenv／subprocess（MU-SE-02：到點 job 看不到的 env 不得成為判準輸入）。
        AST：無 environ／getenv／subprocess（MU-SE-02：到點 job 看不到的 env 不得成為判準輸入）。"""
        tree = ast.parse(Path(ss.__file__).read_text(encoding="utf-8"))
        bad = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "environ",
                "getenv",
                "environb",
                "Popen",
                "run",
                "check_output",
            }:
                bad.append(node.attr)
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
                bad += [n for n in names if n.split(".")[0] == "subprocess"]
        self.assertEqual(bad, [])

    def test_decision_is_identical_with_hostile_environment(self) -> None:
        """同一輸入在 ENV 設 AUTOSDD_REALVERIFY／AUTOSDD_UNATTENDED／GIT_DIR 前後判決逐位元組相同。
        同一輸入在 ENV 設 AUTOSDD_REALVERIFY／AUTOSDD_UNATTENDED／GIT_DIR 前後判決逐位元組相同。"""
        with tempfile.TemporaryDirectory() as raw:
            home = _sandbox(Path(raw).resolve())
            before = ss.target_verdict(cwd=home, now=NOW)
            with mock.patch.dict(
                os.environ, {"AUTOSDD_REALVERIFY": "1", "AUTOSDD_UNATTENDED": "1", "GIT_DIR": raw}
            ):
                self.assertEqual(ss.target_verdict(cwd=home, now=NOW), before)

    def test_return_codes_are_pairwise_distinct(self) -> None:
        """RC_SIDEEFFECT_REFUSED＝10、RC_RESIDENCE_MISSING＝9 互異，
        且不與入口既有 rc 字面相等（AT-SE-48 本棒可及的一半）。"""
        self.assertEqual((ss.RC_SIDEEFFECT_REFUSED, endurance_env.RC_RESIDENCE_MISSING), (10, 9))
        taken: set[int] = set()
        hits: list[str] = []
        files = [
            _REPO_ROOT / "tools" / n
            for n in (
                "sessionctl.py",
                "session_resume_planner.py",
                "openitems.py",
                "selfimproving.py",
            )
        ]
        files += [_REPO_ROOT / "tools" / "lib" / "engine_resume_job.py"]
        files += sorted((_REPO_ROOT / "tools" / "lib" / "sessionctl").glob("*.py"))
        for path in files:
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                targets = []
                if isinstance(node, ast.Return) and node.value is not None:
                    targets.append(node.value)
                elif isinstance(node, ast.Call) and getattr(
                    node.func, "attr", getattr(node.func, "id", "")
                ) in {"exit", "SystemExit"}:
                    targets += node.args
                elif isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Name) and (t.id.startswith("_RC_") or t.id == "_USAGE_RC")
                    for t in node.targets
                ):
                    targets.append(node.value)
                for target in (
                    targets
                ):  # 只收「直接就是整數字面」的 rc（含 `return 9`、`sys.exit(9)`、`_RC_X = 9`）
                    if isinstance(target, ast.Constant) and type(target.value) is int:
                        taken.add(target.value)
                        if target.value in (9, 10):
                            hits.append(f"{path.name}:{target.lineno}")
        self.assertEqual(hits, [], "rc 9／10 已被入口使用")


class JobEnvTest(_Tmp):
    HOME_KEYS = {
        k: str(Path(tempfile.gettempdir()) / k.lower()) for k in endurance_env.RESIDENCE_KEYS
    }

    def test_at_se_15_residence_keys_and_stable_order(self) -> None:
        """設 3 個居所鍵→3 個旗標、鍵序固定；0 鍵→[]（正式環境 argv 逐字不變，REQ-SE-21）。"""
        env = {
            k: self.HOME_KEYS[k]
            for k in ("AUTOSDD_SI_DIR", "AUTOSDD_TRACE_DIR", "AUTOSDD_PLAN_DIR")
        }
        argv = endurance_env.job_env_argv(env, sandbox=True)
        self.assertEqual(argv[::2], ["--job-env"] * 3)
        self.assertEqual(
            [a.split("=")[0] for a in argv[1::2]],
            ["AUTOSDD_TRACE_DIR", "AUTOSDD_PLAN_DIR", "AUTOSDD_SI_DIR"],
        )
        self.assertEqual(endurance_env.job_env_argv({}, sandbox=True), [])
        self.assertEqual(
            endurance_env.job_env_argv(
                {"UNRELATED": "x", "AUTOSDD_UNATTENDED": "1"}, sandbox=False
            ),
            [],
        )

    def test_at_se_16_every_dir_key_literal_in_tools_lib_is_a_residence_key(self) -> None:
        """AST 普查：tools/lib/**/*.py 的 `AUTOSDD_[A-Z_]*_DIR` 字面 ⊆ RESIDENCE_KEYS；
        注入新字面即紅並點名檔案。"""
        import re

        pattern = re.compile(r"^AUTOSDD_[A-Z_]*_DIR$")

        def census(text: str) -> set[str]:
            return {
                n.value
                for n in ast.walk(ast.parse(text))
                if isinstance(n, ast.Constant)
                and isinstance(n.value, str)
                and pattern.match(n.value)
            }

        found: dict[str, set[str]] = {}
        for path in (_REPO_ROOT / "tools" / "lib").rglob("*.py"):
            keys = census(path.read_text(encoding="utf-8"))
            if keys:
                found[path.relative_to(_REPO_ROOT).as_posix()] = keys
        stray = {
            f: ks - set(endurance_env.RESIDENCE_KEYS)
            for f, ks in found.items()
            if ks - set(endurance_env.RESIDENCE_KEYS)
        }
        self.assertEqual(stray, {})
        self.assertEqual(
            census('X = "AUTOSDD_NEWTHING_DIR"\n') - set(endurance_env.RESIDENCE_KEYS),
            {"AUTOSDD_NEWTHING_DIR"},
        )

    def test_at_se_35_behaviour_switches_carry_only_off_values_and_never_unattended(self) -> None:
        """job_env_argv：模式 notify、通知空、哨兵 1 → 3 旗標且不含 UNATTENDED；apply：
        通知 1／哨兵 0／模式 xyz／UNATTENDED 皆 rc 2（MU-SE-15／21）。"""
        env = {
            "AUTOSDD_SESSION_SWITCH_MODE": "notify",
            "AUTOSDD_DESKTOP_NOTIFY": "",
            "AUTOSDD_SENTINEL_OFF": "1",
            "AUTOSDD_UNATTENDED": "1",
        }
        argv = endurance_env.job_env_argv(env, sandbox=True)
        self.assertEqual(
            argv[1::2],
            [
                "AUTOSDD_SESSION_SWITCH_MODE=notify",
                "AUTOSDD_DESKTOP_NOTIFY=",
                "AUTOSDD_SENTINEL_OFF=1",
            ],
        )
        for bad in (
            "AUTOSDD_DESKTOP_NOTIFY=1",
            "AUTOSDD_SENTINEL_OFF=0",
            "AUTOSDD_SESSION_SWITCH_MODE=xyz",
            "AUTOSDD_UNATTENDED=1",
            "FOO_DIR=x",
        ):
            with mock.patch.dict(os.environ, {}, clear=False), self.subTest(bad=bad):
                with self.assertRaises(endurance_env.JobEnvValueError) as ctx:
                    endurance_env.apply_job_env(["--job-env", bad])
                self.assertEqual(ctx.exception.rc, 2)

    def test_at_se_48_apply_stops_at_the_first_double_dash(self) -> None:
        """`--` 之後原樣保留（含第二個 --job-env，MU-SE-29）；之前的剝掉並寫進環境。"""
        target = str(self.tmp / "t")
        argv = [
            "--job-env",
            f"AUTOSDD_TRACE_DIR={target}",
            "runlong",
            "--",
            "x",
            "--job-env",
            "Y=1",
        ]
        with mock.patch.dict(os.environ, {}, clear=False):
            rest = endurance_env.apply_job_env(argv)
            self.assertEqual(os.environ["AUTOSDD_TRACE_DIR"], target)
        self.assertEqual(rest, ["runlong", "--", "x", "--job-env", "Y=1"])

    def test_at_se_49_official_target_never_raises_and_drops_disallowed_values(self) -> None:
        """正式目標：通知=1、哨兵=""（顯式空）、模式 xyz 皆不拋、不轉送（MU-SE-32）；沙盒目標①③拋、
        ②視同未設。"""
        for env in (
            {"AUTOSDD_DESKTOP_NOTIFY": "1"},
            {"AUTOSDD_SENTINEL_OFF": ""},
            {"AUTOSDD_SESSION_SWITCH_MODE": "xyz"},
            {},
        ):
            self.assertEqual(endurance_env.job_env_argv(env, sandbox=False), [], env)
        self.assertEqual(endurance_env.job_env_argv({"AUTOSDD_SENTINEL_OFF": ""}, sandbox=True), [])
        for env in ({"AUTOSDD_DESKTOP_NOTIFY": "1"}, {"AUTOSDD_SESSION_SWITCH_MODE": "xyz"}):
            with self.assertRaises(endurance_env.JobEnvValueError) as ctx:
                endurance_env.job_env_argv(env, sandbox=True)
            self.assertIn(next(iter(env)), str(ctx.exception))
        self.assertEqual(
            endurance_env.job_env_argv(
                {"AUTOSDD_DESKTOP_NOTIFY": "1", "AUTOSDD_SENTINEL_OFF": "1"}, sandbox=False
            ),
            ["--job-env", "AUTOSDD_SENTINEL_OFF=1"],
        )

    def test_at_se_37_missing_sandbox_home_applies_nothing_and_builds_nothing(self) -> None:
        """已刪沙盒家目錄下的居所 ⇒ ResidenceMissing(rc 9)；環境與目錄皆不動（MU-SE-22）。"""
        value = str(self.tmp / "AutoSDD_RV_sbx_gone" / "traces")
        before = sorted(p.name for p in self.tmp.rglob("*"))
        with mock.patch.dict(os.environ, {}, clear=False):
            for key in ("AUTOSDD_TRACE_DIR", "AUTOSDD_SENTINEL_OFF"):  # 後者＝runner 洩漏圍籬
                os.environ.pop(key, None)
            with self.assertRaises(endurance_env.ResidenceMissing) as ctx:
                endurance_env.apply_job_env(
                    [
                        "--job-env",
                        f"AUTOSDD_TRACE_DIR={value}",
                        "--job-env",
                        "AUTOSDD_SENTINEL_OFF=1",
                    ]
                )
            self.assertNotIn("AUTOSDD_TRACE_DIR", os.environ)
            self.assertNotIn("AUTOSDD_SENTINEL_OFF", os.environ)  # 全有或全無
        self.assertEqual(
            (ctx.exception.rc, sorted(p.name for p in self.tmp.rglob("*"))), (9, before)
        )

    def test_e2e_s1_01_real_process_exits_9_and_changes_nothing(self) -> None:
        """E2E-S1-01：真 python 行程呼叫 `apply_job_env_or_exit`。

        沙盒家已刪 ⇒ 真 rc 9、stderr 一行、目錄不被建；合法值 ⇒ 真 rc 0 且子行程環境收到值。"""
        script = (
            "import sys; sys.path.insert(0, sys.argv[1]); import endurance_env, os\n"
            "rest = endurance_env.apply_job_env_or_exit(sys.argv[2:])\n"
            "print('REST=' + repr(rest))\n"
            "print('TRACE=' + os.environ.get('AUTOSDD_TRACE_DIR', ''))\n"
        )
        lib = str(_REPO_ROOT / "tools" / "lib")
        gone = self.tmp / "AutoSDD_RV_sbx_gone" / "traces"
        proc = subprocess.run(
            [sys.executable, "-c", script, lib, "--job-env", f"AUTOSDD_TRACE_DIR={gone}"],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        self.assertEqual(proc.returncode, 9, proc.stderr)
        self.assertEqual(len(proc.stderr.strip().splitlines()), 1)
        self.assertFalse((self.tmp / "AutoSDD_RV_sbx_gone").exists())
        ok = subprocess.run(
            [
                sys.executable,
                "-c",
                script,
                lib,
                "--job-env",
                f"AUTOSDD_TRACE_DIR={self.tmp}",
                "keep",
                "--",
                "x",
            ],
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("REST=['keep', '--', 'x']", ok.stdout)
        self.assertIn(f"TRACE={self.tmp}", ok.stdout)


class _FakePlanner:
    _SCHTASKS_SETTINGS = "SETTINGS-SENTINEL"
    _SCHTASKS_PRINCIPAL = "PRINCIPAL-SENTINEL"
    _EVIDENCE_TEMPLATE = "EVIDENCE {task}"

    def __init__(self) -> None:
        self.scripts: list[str] = []

    @staticmethod
    def _ps_single_quote(text: str) -> str:
        return text.replace("'", "''")

    def run_powershell(self, script: str):
        self.scripts.append(script)
        return mock.Mock(stdout="NextRunTime = x\n", stderr="", returncode=0)

    @staticmethod
    def next_run_time(_out: str) -> str:
        return "x"


class ExpiryScriptTest(unittest.TestCase):
    FIRE = datetime(2026, 11, 21, 18, 0, tzinfo=NOW.tzinfo)

    def _script(self, **kw) -> str:
        planner = _FakePlanner()
        with (
            mock.patch.object(erj.win_spawn, "quiet_python", return_value="py/pythonw.exe"),
            mock.patch("builtins.print"),
        ):
            erj._arm_schtasks(planner, "L", ["pyw", "a.py"], "repo", self.FIRE, **kw)
        return planner.scripts[0]

    def test_at_se_11_official_target_script_is_unchanged_and_sandbox_gets_end_boundary(
        self,
    ) -> None:
        """正式（expire_at=None）腳本與未傳參數逐位元組相同（MU-SE-07）；
        沙盒帶 EndBoundary＝expire_at、DeleteExpiredTaskAfter=PT0S，且 EndBoundary 晚於觸發。"""
        plain = self._script()
        self.assertEqual(self._script(expire_at=None), plain)
        self.assertNotIn("EndBoundary", plain)
        self.assertNotIn("DeleteExpired", plain)
        until = self.FIRE + timedelta(minutes=25)
        script = self._script(expire_at=until)
        self.assertIn(f"$trigger.EndBoundary = '{until:%Y-%m-%dT%H:%M:%S}'", script)
        self.assertIn("$settings.DeleteExpiredTaskAfter = 'PT0S'", script)
        self.assertLess(script.index("-Once -At"), script.index("EndBoundary"))
        self.assertLess(script.index("$settings ="), script.index("DeleteExpiredTaskAfter"))
        self.assertLess(script.index("DeleteExpiredTaskAfter"), script.index("$common"))

    def test_expire_at_not_after_fire_is_refused_loudly(self) -> None:
        """EndBoundary 必須晚於 StartBoundary：expire_at ≤ fire ⇒ (1, "")、
        不呼叫排程器（D-15 登記站點應先攔，這裡是最後防線）。"""
        planner = _FakePlanner()
        with (
            mock.patch.object(erj.win_spawn, "quiet_python", return_value="py"),
            mock.patch("builtins.print"),
        ):
            self.assertEqual(
                erj._arm_schtasks(planner, "L", ["p"], "r", self.FIRE, expire_at=self.FIRE), (1, "")
            )
        self.assertEqual(planner.scripts, [])

    def test_arm_oneshot_threads_expire_at_to_schtasks_and_ignores_it_on_launchd(self) -> None:
        """arm_oneshot：schtasks 收到 expire_at；launchd 路徑呼叫簽章不變（誠實劃界：無對等物）。"""
        win, mac = mock.Mock(), mock.Mock()
        win.name, mac.name = "schtasks", "launchd"
        until = self.FIRE + timedelta(minutes=5)
        with (
            mock.patch.object(erj.sb, "select", return_value=win),
            mock.patch.object(erj.sb, "_planner", return_value=_FakePlanner()),
            mock.patch.object(erj, "_arm_schtasks", return_value=(0, "c")) as arm,
        ):
            erj.arm_oneshot("L", ["x"], ".", self.FIRE, expire_at=until)
        self.assertEqual(arm.call_args.kwargs["expire_at"], until)
        with (
            mock.patch.object(erj.sb, "select", return_value=mac),
            mock.patch.object(erj.sb, "_planner", return_value=_FakePlanner()),
            mock.patch.object(erj, "_arm_launchd", return_value=(0, "c")) as lau,
        ):
            erj.arm_oneshot("L", ["x"], ".", self.FIRE, expire_at=until)
        self.assertEqual(len(lau.call_args.args), 5)


if __name__ == "__main__":
    unittest.main()
