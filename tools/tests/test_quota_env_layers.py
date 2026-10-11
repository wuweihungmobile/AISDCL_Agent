"""額度參數檔分層載入（env.shared → .env → 行程 env）與 `--env-doctor` 的回歸鎖。

載入鏈：行程 env > AutoClaude/.env（引擎 3 鍵）> 根 .env > 根 env.shared > 出廠 ENV_SPEC。
兩側讀者（harness `quota_gate.policy_env`／引擎 `config._quota_env`）各寫各的序，鏡子破了要紅：
本檔以**同一組合成語料**雙邊對跑，並以 AST 對照檔名序與引擎鍵清單。
"""
from __future__ import annotations

import ast
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / "AutoClaude"))
import model_roles  # noqa: E402
import quota_env_layers as L  # noqa: E402
import quota_gate as qg  # noqa: E402
import quota_policy as Q  # noqa: E402
import secret_scan  # noqa: E402

_HALT = "AUTOSDD_QUOTA_HALT_PCT"
_HELM = "AUTOSDD_MODEL_HELMSMAN"
_CONFIG_SRC = _REPO_ROOT / "AutoClaude" / "autoclaude" / "utils" / "config.py"


def _root(files: dict[str, str | bytes]) -> Path:
    base = Path(tempfile.mkdtemp(prefix="autosdd_layers_"))
    unittest.addModuleCleanup(shutil.rmtree, base, ignore_errors=True)  # 單模組直跑也不留殘骸
    for rel, body in files.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body if isinstance(body, bytes) else body.encode("utf-8"))
    return base


class _CleanEnvCase(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        for spec in Q.ENV_SPEC:
            os.environ.pop(spec.name, None)


class TestHarnessChainOrder(_CleanEnvCase):
    """env.shared（低）→ .env → 行程 env；每一層都必須能被上一層覆寫。"""

    def test_each_layer_wins_over_the_one_below(self) -> None:
        root = _root({"env.shared": f"{_HALT}=98\n", ".env": f"{_HALT}=91\n"})
        self.assertEqual(qg.policy_env(root)[_HALT], "91")                    # 本機 > 共享
        (root / ".env").unlink()
        self.assertEqual(qg.policy_env(root)[_HALT], "98")                    # 共享 > 出廠
        with mock.patch.dict(os.environ, {_HALT: "77"}):
            self.assertEqual(qg.policy_env(root)[_HALT], "77")                # 行程 env 最高

    def test_the_factory_value_is_what_is_left_when_no_layer_speaks(self) -> None:
        policy, problems = Q.load_policy(qg.policy_env(_root({})))
        self.assertEqual((policy, problems), (Q.DEFAULT_POLICY, []))

    def test_a_blank_local_line_does_not_shadow_the_shared_value(self) -> None:
        """舊版 .env.example 複本滿是 `KEY=`（＝沒設）；它們不得把共享值蓋成空。"""
        root = _root({"env.shared": f"{_HELM}=fable\n{_HALT}=98\n",
                      ".env": f"{_HELM}=\n{_HALT}=   # 沒設\n"})
        merged = qg.policy_env(root)
        self.assertEqual((merged[_HELM], merged[_HALT]), ("fable", "98"))
        self.assertEqual(model_roles.load_model_roles(merged)[0].helmsman, "fable")

    def test_a_blank_only_key_is_still_listed(self) -> None:
        """鍵集合與舊版單檔 `parse_env_text` 一致（逃生口 `KEY=` 的填值語意不變）。"""
        merged = qg.policy_env(_root({".env": "AUTOSDD_QUOTA_GUARD_OFF=\n"}))
        self.assertEqual(merged["AUTOSDD_QUOTA_GUARD_OFF"], "")

    def test_the_engine_only_file_is_invisible_to_the_harness(self) -> None:
        root = _root({"AutoClaude/.env": f"{_HALT}=60\n", "env.shared": f"{_HALT}=98\n"})
        self.assertEqual(qg.policy_env(root)[_HALT], "98")

    def test_a_missing_or_undecodable_layer_is_fail_open(self) -> None:
        root = _root({".env": "\xff\xfe".encode("latin-1").decode("latin-1")})
        (root / ".env").write_bytes(b"\xff\xfe\x00bad")
        (root / "env.shared").write_text(f"{_HALT}=98\n", encoding="utf-8")
        self.assertEqual(qg.policy_env(root)[_HALT], "98")
        self.assertEqual(qg.policy_env(_root({})).get(_HALT), os.environ.get(_HALT))

    def test_apply_env_defaults_fills_from_the_shared_layer_only_when_absent(self) -> None:
        root = _root({"env.shared": f"{_HALT}=98\n{_HELM}=fable\n"})
        env = {_HALT: "60"}
        self.assertEqual(qg.apply_env_defaults(env, root=root), [_HELM])
        self.assertEqual(env, {_HALT: "60", _HELM: "fable"})

    def test_the_hermetic_module_pin_still_beats_the_real_shared_file(self) -> None:
        """出廠值 pin（env 勝檔案）也要蓋得住**真的** env.shared，否則 CI 讀共享值而本機 pin 綠。
        不寫死共享檔的內容：凡共享檔有、且出廠非空的鍵，一律以出廠值 pin 住再驗。"""
        text = (_REPO_ROOT / "env.shared").read_text(encoding="utf-8")
        real, factory = Q.parse_env_text(text), Q.parse_env_text(Q.render_env_example())
        pinned = {k: factory[k] for k in real if factory.get(k)}
        with mock.patch.dict(os.environ, pinned):  # 複本放 tmp 根：不被這台機器的本機 .env 干擾
            seen = Q.load_policy(qg.policy_env(_root({"env.shared": text})))
        self.assertEqual(seen, (Q.DEFAULT_POLICY, []))


class TestEngineMirrorsTheHarnessChain(_CleanEnvCase):
    """AutoClaude 不能 import tools/ ⇒ 兩邊各寫一份序；同一組語料雙邊對跑才釘得住。"""

    #: (標籤, {相對路徑: 內容}, 預期 HALT)；預期值由兩側**各自**算出來，必須都等於它。
    CASES = (
        ("只有共享", {"env.shared": f"{_HALT}=98\n"}, 98.0),
        ("本機蓋共享", {"env.shared": f"{_HALT}=98\n", ".env": f"{_HALT}=91   # x\n"}, 91.0),
        ("本機空白不蓋共享", {"env.shared": f"{_HALT}=98\n", ".env": f"{_HALT}=\n"}, 98.0),
        ("本機只有註解不蓋共享",
         {"env.shared": f"{_HALT}=98\n", ".env": f"{_HALT}=   # n\n"}, 98.0),
        ("cp950 本機層（中文註解＋ASCII 鍵值）",
         {"env.shared": f"{_HALT}=98\n", ".env": f"# 本機\n{_HALT}=91\n".encode("cp950")}, 91.0),
        ("全空＝出廠", {}, 95.0),
    )

    def _engine(self, root: Path) -> float:
        from autoclaude.utils import config as cfg
        files = (root / "AutoClaude" / ".env", root / ".env", root / "env.shared")
        with mock.patch.object(cfg, "_ENV_FILES", files):
            return cfg._quota_env(_HALT, 95.0)

    def _harness(self, root: Path) -> float:
        return Q.load_policy(qg.policy_env(root))[0].halt_pct

    def test_both_sides_agree_on_every_case(self) -> None:
        for label, files, want in self.CASES:
            with self.subTest(label):
                root = _root(files)
                self.assertEqual((self._engine(root), self._harness(root)), (want, want))

    def test_the_engine_layer_wins_for_the_engine_only(self) -> None:
        root = _root({"AutoClaude/.env": f"{_HALT}=93\n", ".env": f"{_HALT}=91\n",
                      "env.shared": f"{_HALT}=98\n"})
        with self.assertLogs("autoclaude.utils.config", "WARNING") as logged:  # 分歧必須出聲
            engine = self._engine(root)
        self.assertEqual((engine, self._harness(root)), (93.0, 91.0))
        self.assertIn("[env 分歧]", logged.output[0])

    def test_the_divergence_warning_follows_the_layer_the_harness_really_reads(self) -> None:
        """三層後 hits[-1] 不再是 harness 吃的那層：根 .env 與共享值不同並不是引擎≠harness。"""
        from autoclaude.utils import config as cfg
        cases = (({"AutoClaude/.env": f"{_HALT}=93\n", "env.shared": f"{_HALT}=98\n"}, True),
                 ({".env": f"{_HALT}=91\n", "env.shared": f"{_HALT}=98\n"}, False))
        for files, loud in cases:
            with self.subTest(loud=loud), mock.patch.object(cfg, "_LOG") as log:
                self._engine(_root(files))
                self.assertEqual(log.warning.called, loud)
                if loud:
                    self.assertEqual(Path(log.warning.call_args.args[4]).name, L.SHARED_NAME)

    def test_the_real_engine_file_order_is_the_documented_chain(self) -> None:
        """AST 對照：`_ENV_FILES` 的檔名序必須是 (AutoClaude/.env, 根 .env, 根 env.shared)。"""
        tree = ast.parse(_CONFIG_SRC.read_text(encoding="utf-8"))
        node = next(n for n in tree.body if isinstance(n, ast.Assign)
                    and getattr(n.targets[0], "id", "") == "_ENV_FILES")
        names = [c.value for sub in node.value.elts for c in ast.walk(sub)
                 if isinstance(c, ast.Constant) and isinstance(c.value, str)]
        self.assertEqual(names, [L.LOCAL_NAME, L.LOCAL_NAME, L.SHARED_NAME])

    def test_the_engine_key_list_and_the_override_mark_are_mirrored(self) -> None:
        tree = ast.parse(_CONFIG_SRC.read_text(encoding="utf-8"))
        called = {c.args[0].value for c in ast.walk(tree) if isinstance(c, ast.Call)
                  and getattr(c.func, "id", "") == "_quota_env"
                  and c.args and isinstance(c.args[0], ast.Constant)}
        self.assertEqual(called, set(L.ENGINE_KEYS), "doctor 的引擎鍵清單與 config.py 呼叫點不同步")
        src = _CONFIG_SRC.read_text(encoding="utf-8")
        self.assertIn(f'_OVERRIDE_MARK = "{L.OVERRIDE_MARK}"', src)


class TestSharedFileIsValidAndSecretFree(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (_REPO_ROOT / "env.shared").read_text(encoding="utf-8")
        self.parsed = Q.parse_env_text(self.text)

    def test_only_declared_keys_and_every_value_parses(self) -> None:
        declared = {s.name for s in Q.ENV_SPEC}
        self.assertEqual(set(self.parsed) - declared, set(), "共享檔只准放 ENV_SPEC 的鍵")
        policy_problems = Q.load_policy(self.parsed)[1]
        role_problems = model_roles.load_model_roles(self.parsed)[1]
        self.assertEqual((policy_problems, role_problems), ([], []))

    def test_no_duplicate_keys_no_bom_and_every_key_is_declared(self) -> None:
        """跨機追蹤檔：重複鍵時 harness 取最後行、引擎取第一行 ⇒ 兩側吃不同停機線；BOM 吃掉首鍵。"""
        keys = [k for line in self.text.splitlines() for k in Q.parse_env_text(line)]
        self.assertEqual(len(keys), len(set(keys)), f"env.shared 有重複鍵：{keys}")
        self.assertLessEqual(set(keys), {s.name for s in Q.ENV_SPEC})   # 逃生口也在 ENV_SPEC 內
        self.assertFalse(self.text.startswith("\ufeff"), "env.shared 不得帶 UTF-8 BOM")

    def test_every_key_line_is_preceded_by_a_why_comment(self) -> None:
        lines = self.text.splitlines()
        for i, line in enumerate(lines):
            if line.strip() and not line.lstrip().startswith("#"):
                self.assertTrue(lines[i - 1].lstrip().startswith("#"),
                                f"第 {i + 1} 行沒有 WHY：{line}")

    def test_the_secret_scanner_finds_nothing_in_it(self) -> None:
        self.assertEqual(secret_scan.scan_text(self.text, L.SHARED_NAME), [])

    def test_its_name_is_not_env_shaped(self) -> None:
        """`.env.*`／`*.env` 形態會撞 pre-commit 機密閘與「tracked 清單不得有 .env 形態」不變式。"""
        self.assertFalse(secret_scan.is_env_shaped(L.SHARED_NAME))


class TestEnvDoctor(_CleanEnvCase):
    def _run(self, files: dict[str, str], *extra: str) -> tuple[int, str, Path]:
        root = _root(files)
        out: list[str] = []
        with mock.patch("builtins.print", lambda *a, **k: out.append(" ".join(map(str, a)))):
            rc = L.doctor_cli(["--root", str(root), *extra])
        return rc, "\n".join(out), root

    def test_a_clean_tree_is_rc_0(self) -> None:
        rc, out, _ = self._run({"env.shared": f"# why\n{_HALT}=98\n"})
        self.assertEqual(rc, 0, out)
        self.assertIn("〔env.shared〕", out)

    def test_redundant_and_shadows_shared_are_distinct_flags(self) -> None:
        rc, out, _ = self._run({"env.shared": f"# why\n{_HALT}=98\n{_HELM}=fable\n",
                                ".env": f"{_HALT}=95\n{_HELM}=fable\nAUTOSDD_QUOTA_PACE_NEAR=2\n"})
        self.assertEqual(rc, 1)
        self.assertIn("[shadows-shared] .env:1", out)          # 95 ≠ 共享 98
        self.assertIn("[redundant] .env:2", out)               # 與共享相同
        self.assertIn("[redundant] .env:3", out)               # 與出廠相同

    def test_the_override_mark_turns_an_error_into_information(self) -> None:
        rc, out, _ = self._run({"env.shared": f"# why\n{_HALT}=98\n",
                                ".env": f"{_HALT}=95  # override-ok: 本機額度小\n"})
        self.assertEqual(rc, 0, out)
        self.assertIn("[override]", out)

    def test_unknown_names_only_the_own_namespace_and_never_prints_foreign_values(self) -> None:
        rc, out, _ = self._run({".env": "AUTOSDD_QUOTA_HALT_PCTT=90\nMINIMAX_API_KEY=sk-LEAK\n"})
        self.assertEqual(rc, 1)
        self.assertIn("[unknown] .env:1 AUTOSDD_QUOTA_HALT_PCTT", out)
        self.assertNotIn("sk-LEAK", out)
        self.assertNotIn("MINIMAX_API_KEY", out)
        self.assertIn("[foreign]", out)

    def test_engine_only_differences_are_flagged_and_dead_keys_too(self) -> None:
        rc, out, _ = self._run({"env.shared": f"# why\n{_HALT}=98\n",
                                "AutoClaude/.env": f"{_HALT}=95\nAUTOSDD_QUOTA_PACE_NEAR=3\n"})
        self.assertEqual(rc, 1)
        self.assertIn("[engine≠harness] AutoClaude/.env:1", out)
        self.assertIn("[dead] AutoClaude/.env:2", out)

    def test_duplicates_bom_and_undecodable_files_are_judged_not_crashed(self) -> None:
        rc, out, root = self._run({".env": f"{_HALT}=90\n{_HALT}=91\n"})
        self.assertIn("[duplicate]", out)
        (root / ".env").write_bytes(b"\xff\xfe\x00")
        with mock.patch("builtins.print", lambda *a, **k: None):
            self.assertEqual(L.doctor_cli(["--root", str(root)]), 1)
        (root / ".env").write_bytes(f"{_HALT}=95\n# 本機".encode("cp950"))  # 讀得進、修不得
        with mock.patch("builtins.print", lambda *a, **k: None):
            self.assertEqual(L.doctor_cli(["--root", str(root), "--fix"]), 2)  # 拒絕修、不崩
        shared = f"# why\n{_HALT}=98\n"
        for label, files, flag in (
                ("env.shared 重複鍵", {"env.shared": shared * 2}, "[duplicate] env.shared:4"),
                ("本機 BOM", {"env.shared": shared, ".env": f"\ufeff{_HALT}=91\n"}, "[bom] .env")):
            with self.subTest(label):
                rc, out, _ = self._run(files)
                self.assertEqual((rc, flag in out), (1, True))

    def test_bad_values_surface_as_bad_value(self) -> None:
        rc, out, _ = self._run({".env": f"{_HALT}=abc\n"})
        self.assertEqual(rc, 1)
        self.assertIn("[bad-value]", out)

    def test_fix_backs_up_removes_only_flagged_lines_and_preserves_everything_else(self) -> None:
        keep = "AUTOSDD_QUOTA_MAX_FANOUT=9  # 我自己要的\r\n"
        body = ("# 我的註解\r\nMINIMAX_API_KEY=sk-SECRET0123456789\r\n"
                f"{_HALT}=95\r\nAUTOSDD_QUOTA_PACE_NEAR=2\r\n{keep}")
        rc, out, root = self._run({"env.shared": f"# why\n{_HALT}=98\n", ".env": body}, "--fix")
        self.assertEqual(rc, 0, out)
        baks = sorted(p.name for p in root.glob(".env.bak.*"))
        self.assertEqual(len(baks), 1)
        self.assertEqual((root / baks[0]).read_bytes(), body.encode("utf-8"))  # 備份＝原檔
        after = (root / ".env").read_bytes().decode("utf-8")
        want = f"# 我的註解\r\nMINIMAX_API_KEY=sk-SECRET0123456789\r\n{keep}"
        self.assertEqual(after, want)                          # CRLF 與其餘行原樣
        self.assertNotIn("sk-SECRET0123456789", out, "diff 不得印出鄰近的機密行")
        self.assertIn("-AUTOSDD_QUOTA_HALT_PCT=95", out)

    def test_fix_is_idempotent_and_a_noop_on_a_clean_tree(self) -> None:
        files = {"env.shared": f"# why\n{_HALT}=98\n", ".env": f"{_HALT}=95\n"}
        rc, _out, root = self._run(files, "--fix")
        self.assertEqual(rc, 0)
        before = sorted(p.name for p in root.iterdir())
        with mock.patch("builtins.print", lambda *a, **k: None):
            self.assertEqual(L.doctor_cli(["--root", str(root), "--fix"]), 0)
        self.assertEqual(sorted(p.name for p in root.iterdir()), before, "第二次 --fix 不得再備份")

    def test_a_local_override_of_a_key_with_no_lower_layer_is_not_a_crash(self) -> None:
        """出廠為空的鍵（逃生口等）本機設了值、共享也沒有 ⇒ 沒有下一層可比，只能是 [local]。"""
        rc, out, _ = self._run({"env.shared": f"# why\n{_HALT}=98\n",
                                ".env": "AUTOSDD_QUOTA_GUARD_OFF=1\n"})
        self.assertEqual(rc, 0, out)
        self.assertIn("[local] .env:1 AUTOSDD_QUOTA_GUARD_OFF=1", out)

    def test_a_second_fix_pass_in_the_same_second_keeps_the_original_backup(self) -> None:
        """備份名只到秒：同秒第二輪修復不得用「已改過的檔」覆蓋第一輪那份原檔備份。"""
        original = f"{_HALT}=95\nAUTOSDD_QUOTA_PACE_NEAR=2\n"
        root = _root({".env": original})
        frozen = mock.Mock(now=lambda tz: datetime(2026, 10, 11, 1, 2, 3))
        with mock.patch.object(L, "datetime", frozen):
            L._fix_one(root / ".env", [1])
            L._fix_one(root / ".env", [1])
        (bak,) = root.glob(".env.bak.*")
        self.assertEqual(bak.read_text(encoding="utf-8"), original)

    def test_a_missing_shared_file_is_an_error_because_it_is_tracked(self) -> None:
        rc, out, _ = self._run({".env": f"{_HALT}=91  # override-ok: x\n"})
        self.assertEqual(rc, 1)
        self.assertIn("[missing-shared]", out)

    def test_unknown_cli_args_are_rejected_with_rc_2(self) -> None:
        with mock.patch("sys.stderr"):
            self.assertEqual(L.doctor_cli(["--bogus"]), 2)


if __name__ == "__main__":
    unittest.main()
