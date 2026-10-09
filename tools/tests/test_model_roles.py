#!/usr/bin/env python3
"""模型角色三鍵（improving_113 W1）的回歸鎖：主控／子代理／降級三個角色的模型由 `.env` 設定。

被守的性質（argv 形狀判準與家族詞彙另帶合成注入的紅側，鑑別力不靠「現況剛好是綠」）：
1. `ENV_SPEC` 三列的位置與出廠預設（空／sonnet／haiku）；字串壞值不得連坐重設額度門檻。
2. `load_model_roles` 的值域：別名或含家族字的完整 id；壞值只退「該鍵」預設並出聲一次。
3. 喚醒 argv 的 `--model` 只准排在 `--settings <檔>` 之後、`--add-dir` 之前（變長旗標
   會吞掉它後面的位置參數）；子行程環境只加子代理預設，絕不設 FORCE 旗標。
4. 降級建議行的預設字面逐字不變；自訂角色改變字面；`--pace`／SessionStart 簡報印角色行。
5. `.env.example` 往返無損：`render → parse → load` 對新鍵與舊鍵都零問題。
"""
from __future__ import annotations

import ast
import inspect
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
sys.path.insert(0, str(_REPO_ROOT / "tools"))
import model_roles  # noqa: E402
import quota_gate  # noqa: E402
import quota_messages  # noqa: E402
import quota_policy  # noqa: E402
import resume_route  # noqa: E402
import session_brief  # noqa: E402

import session_resume_planner as planner  # noqa: E402

_HELM, _SUB, _DOWN = ("AUTOSDD_MODEL_HELMSMAN", "AUTOSDD_MODEL_SUBAGENT",
                      "AUTOSDD_MODEL_DOWNGRADE")
_ALL_KEYS = (_HELM, _SUB, _DOWN)
_FIELDS = {_HELM: "helmsman", _SUB: "subagent", _DOWN: "downgrade"}
_DEFAULTS = {_HELM: "", _SUB: "sonnet", _DOWN: "haiku"}
_CHILD_KEY = "CLAUDE_CODE_SUBAGENT_MODEL"
#: 改動前 `model_hint_line()` 在 kind=weekly_scoped 時的逐字輸出（預設字面不得漂移）。
_OLD_HINT = ("   🔻 降級建議：kind=weekly_scoped 已進收緊帶 ⇒ 建議派工帶 "
             "model: sonnet/haiku 續跑（只建議不自動改模型；cap 不受本行影響）。\n")


class _Sandbox(unittest.TestCase):
    """三鍵與子代理旗標先清空、handback 目錄指進沙箱；結束時環境原樣還原。"""

    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="model-roles-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.set_env({"AUTOSDD_HANDBACK_DIR": str(self.tmp / "hb")})
        for key in (*_ALL_KEYS, _CHILD_KEY, _CHILD_KEY + "_FORCE", "AUTOSDD_UNATTENDED"):
            os.environ.pop(key, None)

    def set_env(self, values: dict[str, str]) -> None:
        patcher = mock.patch.dict(os.environ, values)
        patcher.start()
        self.addCleanup(patcher.stop)


# ═══════════════════════════ 1. 規格表：三列、位置、不連坐 ═══════════════════════════
class EnvSpecDeclaresTheThreeRolesTest(unittest.TestCase):
    def _row(self, name: str):
        return next((s for s in quota_policy.ENV_SPEC if s.name == name), None)

    def test_each_key_is_a_string_row_that_stays_out_of_the_policy_dataclass(self) -> None:
        for name in _ALL_KEYS:
            with self.subTest(key=name):
                spec = self._row(name)
                self.assertIsNotNone(spec, f"{name} 沒進 ENV_SPEC")
                self.assertEqual((spec.attr, spec.default, spec.kind, spec.section),
                                 (None, _DEFAULTS[name], "model", "policy"))

    def test_the_rows_render_in_the_policy_region_not_under_the_escape_header(self) -> None:
        """渲染分區跟著 ENV_SPEC 的位置走：排在逃生口之後會被印在「既有逃生口」標題底下。"""
        text = quota_policy.render_env_example()
        escape_at = text.index("既有逃生口")
        for name in _ALL_KEYS:
            with self.subTest(key=name):
                self.assertLess(text.index(f"\n{name}="), escape_at)

    def test_a_bad_role_value_cannot_reset_the_quota_ladder(self) -> None:
        """不走 `load_policy` 的理由：它對壞值是整組退回預設，一個拼錯的模型名會連額度
        門檻一起重設（耦合方向錯）。"""
        env = {_SUB: "???", _HELM: "x y", "AUTOSDD_QUOTA_HALT_PCT": "88"}
        policy, problems = quota_policy.load_policy(env)
        self.assertEqual((problems, policy.halt_pct), ([], 88.0))

    def test_the_generated_example_round_trips_through_both_consumers(self) -> None:
        parsed = quota_policy.parse_env_text(quota_policy.render_env_example())
        self.assertEqual([parsed.get(k) for k in _ALL_KEYS], ["", "sonnet", "haiku"])
        self.assertEqual(quota_policy.load_policy(parsed)[1], [])
        self.assertEqual(model_roles.load_model_roles(parsed), (model_roles.DEFAULT_ROLES, []))

    def test_the_shipped_example_file_carries_the_three_keys(self) -> None:
        text = (_REPO_ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertEqual(quota_policy.env_example_problems(text), [])
        self.assertTrue(all(f"\n{k}=" in text for k in _ALL_KEYS))


# ═══════════════════════════ 2. 值域：別名／完整 id／壞值 ═══════════════════════════
class LoadModelRolesTest(unittest.TestCase):
    def test_nothing_set_gives_the_factory_roles_and_no_problems(self) -> None:
        roles, problems = model_roles.load_model_roles({})
        self.assertEqual(roles, model_roles.ModelRoles("", "sonnet", "haiku"))
        self.assertEqual((roles, problems), (model_roles.DEFAULT_ROLES, []))

    def test_every_alias_and_full_id_is_accepted_on_every_key(self) -> None:
        good = ("fable", "opus", "sonnet", "haiku", "claude-sonnet-5-5", "sonnet[1m]",
                "claude-fable-5-1[1m]")
        for key in _ALL_KEYS:
            for value in good:
                with self.subTest(key=key, value=value):
                    roles, problems = model_roles.load_model_roles({key: value})
                    self.assertEqual((getattr(roles, _FIELDS[key]), problems), (value, []))

    def test_surrounding_whitespace_is_stripped_and_blank_means_unset(self) -> None:
        roles, problems = model_roles.load_model_roles({_HELM: " fable ", _SUB: "  ", _DOWN: ""})
        self.assertEqual((roles, problems),
                         (model_roles.ModelRoles("fable", "sonnet", "haiku"), []))

    def test_a_bad_value_falls_back_to_that_keys_default_and_says_so_once(self) -> None:
        bad = ("gpt-4", "../x", "opus x", "sonnet;ls", "claude\nsonnet", "-sonnet",
               "--model=sonnet", "$(sonnet)", "mythos", "sonnet/../x")
        for key in _ALL_KEYS:
            for value in bad:
                with self.subTest(key=key, value=value):
                    roles, problems = model_roles.load_model_roles({key: value})
                    self.assertEqual(getattr(roles, _FIELDS[key]), _DEFAULTS[key])
                    self.assertEqual(len(problems), 1, problems)
                    self.assertIn(key, problems[0])
                    self.assertIn(repr(value), problems[0])

    def test_a_very_long_bad_value_is_quoted_with_a_bounded_length(self) -> None:
        """problems 會原樣進 SessionStart 簡報與 `--pace`：貼錯一大段文字不能撐爆它們。"""
        _, problems = model_roles.load_model_roles({_SUB: "x" * 500})
        self.assertEqual(len(problems), 1)
        self.assertLess(len(problems[0]), 300)

    def test_an_empty_default_is_named_as_empty_in_the_problem_text(self) -> None:
        _, problems = model_roles.load_model_roles({_HELM: "???"})
        self.assertIn("採用預設 （空）", problems[0])

    def test_one_bad_key_does_not_drag_the_other_keys_back_to_defaults(self) -> None:
        env = {_HELM: "???", _SUB: "opus", _DOWN: "fable"}
        roles, problems = model_roles.load_model_roles(env)
        self.assertEqual(roles, model_roles.ModelRoles("", "opus", "fable"))
        self.assertEqual(len(problems), 1)

    def test_two_bad_keys_are_reported_separately(self) -> None:
        _, problems = model_roles.load_model_roles({_SUB: "???", _DOWN: "!!!"})
        self.assertEqual(len(problems), 2)

    def test_the_family_vocabulary_has_exactly_one_home(self) -> None:
        """full id 認得出家族才收；家族詞彙外的 id 要先擴 `quota_policy.MODEL_FAMILIES`，
        不在這裡另開洞。合成注入：把詞彙表加一個字，同一個值就從壞值變合法。"""
        value = {_SUB: "claude-mythos-5-1"}
        self.assertEqual(len(model_roles.load_model_roles(value)[1]), 1)
        wider = (*quota_policy.MODEL_FAMILIES, "mythos")
        with mock.patch.object(quota_policy, "MODEL_FAMILIES", wider):
            roles, problems = model_roles.load_model_roles(value)
        self.assertEqual((roles.subagent, problems), ("claude-mythos-5-1", []))

    def test_the_loader_reads_the_mapping_not_the_process_environment(self) -> None:
        with mock.patch.dict(os.environ, {_SUB: "opus", _HELM: "fable"}):
            roles, _ = model_roles.load_model_roles({})
        self.assertEqual(roles, model_roles.DEFAULT_ROLES)

    def test_none_values_in_the_mapping_count_as_unset(self) -> None:
        roles, problems = model_roles.load_model_roles({_HELM: None, _SUB: None})
        self.assertEqual((roles, problems), (model_roles.DEFAULT_ROLES, []))

    def test_inherit_is_a_valid_subagent_value_in_exactly_that_spelling(self) -> None:
        """`inherit`＝顯式「不注入」；只認這個拼法，大小寫變體既不是別名也不是哨兵。"""
        for raw in ("inherit", "  inherit "):
            with self.subTest(raw=raw):
                roles, problems = model_roles.load_model_roles({_SUB: raw})
                self.assertEqual((roles.subagent, problems), ("inherit", []))
        for raw in ("Inherit", "INHERIT"):
            with self.subTest(raw=raw):
                roles, problems = model_roles.load_model_roles({_SUB: raw})
                self.assertEqual((roles.subagent, len(problems)), (_DEFAULTS[_SUB], 1))

    def test_inherit_is_refused_on_the_helmsman_and_downgrade_keys_out_loud(self) -> None:
        """`--model inherit`（主控）與探針 `--model inherit`（降級）都無意義；要沿用請留空。"""
        for key in (_HELM, _DOWN):
            with self.subTest(key=key):
                roles, problems = model_roles.load_model_roles({key: "inherit"})
                self.assertEqual(getattr(roles, _FIELDS[key]), _DEFAULTS[key])
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(key, problems[0])


# ═══════════════════════════ 3. 派生物：環境、旗標、人話行 ═══════════════════════════
class RoleDerivationsTest(unittest.TestCase):
    def test_child_env_carries_only_the_subagent_default_and_never_force(self) -> None:
        got = model_roles.child_env(model_roles.ModelRoles("fable", "opus", "haiku"))
        self.assertEqual(got, {_CHILD_KEY: "opus"})
        self.assertNotIn(_CHILD_KEY + "_FORCE", got, "FORCE 會讓 Agent 工具失去 model 參數")

    def test_child_env_is_empty_without_a_subagent_role(self) -> None:
        self.assertEqual(model_roles.child_env(model_roles.ModelRoles("fable", "", "haiku")), {})

    def test_model_argv_is_empty_for_an_empty_helmsman(self) -> None:
        self.assertEqual(model_roles.model_argv(model_roles.DEFAULT_ROLES), [])

    def test_model_argv_is_one_flag_value_pair(self) -> None:
        roles = model_roles.ModelRoles("fable", "sonnet", "haiku")
        self.assertEqual(model_roles.model_argv(roles), ["--model", "fable"])

    def test_the_line_names_all_three_roles_with_their_values_on_one_line(self) -> None:
        line = model_roles.roles_line(model_roles.ModelRoles("fable", "opus", "haiku"), [])
        self.assertNotIn("\n", line)
        for token in ("主控=fable", "子代理=opus", "降級=haiku"):
            self.assertIn(token, line)

    def test_an_empty_helmsman_reads_as_inherit_and_a_set_one_does_not(self) -> None:
        empty = model_roles.roles_line(model_roles.DEFAULT_ROLES, [])
        self.assertIn("沿用存檔／設定鏈", empty)
        set_line = model_roles.roles_line(model_roles.ModelRoles("fable", "opus", "haiku"), [])
        self.assertNotIn("沿用", set_line)

    def test_problems_ride_along_as_a_warning_and_a_clean_load_has_none(self) -> None:
        clean = model_roles.roles_line(model_roles.DEFAULT_ROLES, [])
        self.assertNotIn("⚠️", clean)
        warned = model_roles.roles_line(model_roles.DEFAULT_ROLES, ["AUTOSDD_MODEL_SUBAGENT='?'"])
        self.assertIn("⚠️", warned)
        self.assertIn("AUTOSDD_MODEL_SUBAGENT='?'", warned)
        self.assertNotIn("\n", warned)


# ═══════════════════════════ 4. 喚醒 argv：`--model` 的位置 ═══════════════════════════
def _argv_shape_problems(argv: list[str], sid: str | None, prompt: str) -> list[str]:
    """喚醒 argv 的形狀判準（與 `test_context_budget_guard.py` 的姊妹鎖同形；純函式，
    所以下面的紅側可以拿合成壞 argv 餵它）。`--model` 只准在 `--settings <檔>` 之後、
    `--add-dir` 之前：`--add-dir` 是變長旗標，位置不對會吞掉 prompt 或被當成目錄。"""
    head = ["claude", "-p", "-r", sid, prompt] if sid else ["claude", "-p", prompt]
    problems = []
    if argv[: len(head)] != head:
        problems.append(f"頭段不是 {head}：{argv[: len(head)]}")
    if "--add-dir" not in argv:
        return [*problems, "沒有 --add-dir"]
    tail = argv.index("--add-dir")
    if len(argv) - tail - 1 != 2:
        problems.append(f"--add-dir 之後不是恰兩個目錄值：{argv[tail:]}")
    if "--model" in argv:
        at = argv.index("--model")
        if not argv.index("--settings") + 1 < at < tail:
            problems.append(f"--model 不在 --settings 值之後、--add-dir 之前：{argv}")
    return problems


class ResumeRouteModelFlagTest(_Sandbox):
    _PROMPT = "讀 plan，照它第 3 節做。"

    def _resume(self) -> list[str]:
        return resume_route.resume_argv("claude", "sid-1", self._PROMPT, self.tmp / "plan")

    def _fresh(self) -> list[str]:
        return resume_route.fresh_argv("claude", self._PROMPT, self.tmp / "plan")

    def test_without_a_helmsman_neither_route_carries_a_model_flag(self) -> None:
        for argv, sid in ((self._resume(), "sid-1"), (self._fresh(), None)):
            self.assertNotIn("--model", argv)
            self.assertEqual(_argv_shape_problems(argv, sid, self._PROMPT), [])

    def test_a_helmsman_lands_right_after_the_settings_file_on_both_routes(self) -> None:
        self.set_env({_HELM: "fable"})
        for argv, sid in ((self._resume(), "sid-1"), (self._fresh(), None)):
            at = argv.index("--settings")
            self.assertEqual(argv[at + 1], str(resume_route.UNATTENDED_SETTINGS))
            self.assertEqual(argv[at + 2: at + 5], ["--model", "fable", "--add-dir"])
            self.assertEqual(_argv_shape_problems(argv, sid, self._PROMPT), [])

    def test_the_posture_flags_are_untouched_by_the_model_flag(self) -> None:
        plain = self._resume()
        self.set_env({_HELM: "claude-fable-5-1[1m]"})
        with_model = self._resume()
        self.assertEqual([a for a in with_model if a not in ("--model", "claude-fable-5-1[1m]")],
                         plain)

    def test_a_bad_helmsman_value_degrades_to_no_flag_not_to_a_broken_argv(self) -> None:
        self.set_env({_HELM: "gpt-4 --dangerously-skip-permissions"})
        argv = self._resume()
        self.assertNotIn("--model", argv)
        self.assertNotIn("--dangerously-skip-permissions", argv)

    def test_the_shape_checker_has_teeth_on_synthetic_bad_argv(self) -> None:
        good = self._resume()
        self.assertEqual(_argv_shape_problems(good, "sid-1", self._PROMPT), [])
        before_prompt = [*good[:2], "--model", "fable", *good[2:]]
        self.assertTrue(_argv_shape_problems(before_prompt, "sid-1", self._PROMPT))
        after_add_dir = [*good, "--model", "fable"]
        self.assertTrue(_argv_shape_problems(after_add_dir, "sid-1", self._PROMPT))
        before_settings = [*good[:5], "--model", "fable", *good[5:]]
        self.assertTrue(_argv_shape_problems(before_settings, "sid-1", self._PROMPT))


class ProbeArgvTest(_Sandbox):
    def test_the_shape_is_the_paid_probe_the_planner_used_to_hardcode(self) -> None:
        self.assertEqual(resume_route.probe_argv("claude", "haiku"),
                         ["claude", "-p", "ok", "--model", "haiku", "--output-format", "json"])

    def test_an_explicit_model_beats_the_downgrade_role(self) -> None:
        self.set_env({_DOWN: "opus"})
        self.assertEqual(resume_route.probe_argv("claude", "sonnet")[4], "sonnet")

    def test_without_a_model_the_downgrade_role_decides(self) -> None:
        self.assertEqual(resume_route.probe_argv("claude")[4], "haiku")
        self.set_env({_DOWN: "sonnet"})
        self.assertEqual(resume_route.probe_argv("claude")[4], "sonnet")


class RoleEnvTest(_Sandbox):
    def test_the_spawn_env_extra_is_the_subagent_default_from_the_process_env(self) -> None:
        self.assertEqual(resume_route.role_env(), {_CHILD_KEY: "sonnet"})
        self.set_env({_SUB: "opus"})
        self.assertEqual(resume_route.role_env(), {_CHILD_KEY: "opus"})


# ═══════════════════════════ 5. planner：spawn 的 argv／環境、付費探針 ═══════════════════════════
class WakeSpawnCarriesTheRolesTest(_Sandbox):
    """打真的 `_run_resume()`，只把 `subprocess.run` 換成錄影替身（計算面全程真跑）。"""

    def setUp(self) -> None:
        super().setUp()
        (self.tmp / "p.md").write_text("# 任務書", encoding="utf-8")
        self.transcript = self.tmp / "sid-1.jsonl"
        self.transcript.write_text('{"type":"assistant"}\n', encoding="utf-8")
        self.calls: list[dict] = []
        real = planner.subprocess.run

        class _Done:
            returncode, stdout, stderr = 0, "ok", ""

        def _fake_run(argv, **kwargs):
            if isinstance(argv, list) and argv[:1] == ["git"]:
                return real(argv, **kwargs)  # 唯讀快照照跑，self.calls 只留續跑那一次
            self.calls.append({"argv": argv, **kwargs})
            return _Done()

        for patcher in (mock.patch.object(planner.subprocess, "run", _fake_run),
                        mock.patch.object(resume_route, "handback_postcheck",
                                          return_value="written")):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _spawn(self, session_id: str = "sid-1") -> dict:
        args = planner.build_parser().parse_args(["--probe-command", "claude"])
        state = {"plan_path": str(self.tmp / "p.md"), "session_id": session_id,
                 "transcript": str(self.transcript) if session_id else ""}
        planner._run_resume(args, state, self.tmp / "log.jsonl")
        self.assertEqual(len(self.calls), 1, "續跑應該只 spawn 一次")
        return self.calls[0]

    def test_the_default_wake_window_gets_the_subagent_default_and_no_model_flag(self) -> None:
        call = self._spawn()
        self.assertNotIn("--model", call["argv"])
        self.assertEqual(call["env"].get(_CHILD_KEY), "sonnet")
        self.assertEqual(call["env"].get("AUTOSDD_UNATTENDED"), "1")

    def test_configured_roles_reach_the_resume_route(self) -> None:
        self.set_env({_HELM: "fable", _SUB: "opus"})
        call = self._spawn()
        at = call["argv"].index("--settings")
        self.assertEqual(call["argv"][at + 2: at + 5], ["--model", "fable", "--add-dir"])
        self.assertEqual(call["env"].get(_CHILD_KEY), "opus")
        self.assertNotIn(_CHILD_KEY + "_FORCE", call["env"])

    def test_configured_roles_reach_the_fresh_route_too(self) -> None:
        self.set_env({_HELM: "fable"})
        call = self._spawn(session_id="")
        self.assertNotIn("-r", call["argv"], "前提：這一跑走的是 FRESH 降級路")
        self.assertIn("--model", call["argv"])

    def test_the_parameter_file_wins_over_an_inherited_native_variable(self) -> None:
        """喚醒窗口的子代理預設只認參數檔：行程環境裡殘留的 Claude Code 原生變數會被蓋掉，
        要改就改 `AUTOSDD_MODEL_SUBAGENT`（真環境變數照樣贏過 `.env`）。"""
        self.set_env({_CHILD_KEY: "haiku"})
        self.assertEqual(self._spawn()["env"].get(_CHILD_KEY), "sonnet")

    def test_an_inherit_subagent_injects_nothing_and_spares_a_native_variable(self) -> None:
        """`inherit`＝不注入：參數檔不蓋掉行程裡既有的原生變數，也不把字面 inherit 寫進它。"""
        self.assertEqual(model_roles.child_env(model_roles.ModelRoles("", "inherit", "haiku")), {})
        self.set_env({_SUB: "inherit", _CHILD_KEY: "haiku"})
        self.assertEqual(resume_route.role_env(), {})
        self.assertEqual(self._spawn()["env"].get(_CHILD_KEY), "haiku")

    def test_the_rest_of_the_environment_survives_and_the_signal_stays(self) -> None:
        call = self._spawn()
        self.assertEqual([k for k in os.environ if k not in call["env"]], [])
        self.assertEqual(call["env"].get("AUTOSDD_UNATTENDED"), "1")


class ProbeQuotaModelTest(_Sandbox):
    def _argv_of_the_paid_probe(self, *args: str) -> list[str]:
        seen: list[list[str]] = []

        class _Done:
            returncode, stdout, stderr = 0, "{}", ""

        def _fake_run(argv, **_kwargs):
            seen.append(argv)
            return _Done()

        with mock.patch.object(planner.quota_gate, "endpoint_probe_verdict", return_value=None), \
             mock.patch.object(planner.subprocess, "run", _fake_run):
            planner.probe_quota(*args)
        self.assertEqual(len(seen), 1, "前提：免費端點沒答、互動回合，付費探針應 spawn 一次")
        return seen[0]

    def test_the_planner_no_longer_hardcodes_a_probe_model(self) -> None:
        self.assertIsNone(inspect.signature(planner.probe_quota).parameters["model"].default)

    def test_the_default_probe_uses_the_downgrade_role(self) -> None:
        self.assertEqual(self._argv_of_the_paid_probe("claude")[4], "haiku")
        self.set_env({_DOWN: "sonnet"})
        self.assertEqual(self._argv_of_the_paid_probe("claude")[4], "sonnet")

    def test_an_explicit_model_argument_still_wins(self) -> None:
        self.set_env({_DOWN: "sonnet"})
        self.assertEqual(self._argv_of_the_paid_probe("claude", "opus")[4], "opus")


# ═══════════════════════════ 6. 人話面：降級建議行、角色行、簡報 ═══════════════════════════
class ModelHintLineTest(unittest.TestCase):
    _TIGHT = types.SimpleNamespace(model_hint="weekly_scoped")
    _FREE = types.SimpleNamespace(model_hint="")

    def test_the_default_output_is_byte_identical_to_the_old_literal(self) -> None:
        self.assertEqual(quota_messages.model_hint_line(self._TIGHT), _OLD_HINT)
        self.assertEqual(quota_messages.model_hint_line(self._TIGHT, None), _OLD_HINT)
        self.assertEqual(quota_messages.model_hint_line(self._TIGHT, model_roles.DEFAULT_ROLES),
                         _OLD_HINT)

    def test_custom_roles_change_the_suggested_pair(self) -> None:
        roles = model_roles.ModelRoles("fable", "opus", "sonnet")
        got = quota_messages.model_hint_line(self._TIGHT, roles)
        self.assertIn("model: opus/sonnet", got)
        self.assertNotIn("sonnet/haiku", got)

    def test_an_inherit_subagent_is_not_offered_as_a_stage_to_dispatch_with(self) -> None:
        """`inherit/haiku` 不是可照抄的派工值：沿用視窗模型的子代理角色，建議行只留降級那一階；
        角色行照實印出 inherit 的語意。"""
        roles = model_roles.ModelRoles("", "inherit", "haiku")
        self.assertIn("model: haiku 續跑", quota_messages.model_hint_line(self._TIGHT, roles))
        both = quota_messages.model_lines(self._TIGHT, {_SUB: "inherit"})
        self.assertNotIn("inherit/", both)
        self.assertIn("子代理=inherit（不注入，沿用視窗模型）", both)

    def test_a_free_band_still_prints_no_hint_whatever_the_roles_are(self) -> None:
        roles = model_roles.ModelRoles("fable", "opus", "sonnet")
        self.assertEqual(quota_messages.model_hint_line(self._FREE, roles), "")

    def test_the_roles_line_is_one_indented_line_ending_in_a_newline(self) -> None:
        got = quota_messages.model_roles_line(model_roles.DEFAULT_ROLES, [])
        self.assertTrue(got.startswith("   ") and got.endswith("\n"))
        self.assertEqual(got.count("\n"), 1)
        self.assertIn(model_roles.roles_line(model_roles.DEFAULT_ROLES, []), got)

    def test_model_lines_prints_the_hint_only_when_tight_but_the_roles_always(self) -> None:
        env = {_SUB: "opus", _DOWN: "sonnet"}
        tight = quota_messages.model_lines(self._TIGHT, env)
        free = quota_messages.model_lines(self._FREE, env)
        self.assertIn("model: opus/sonnet", tight)
        self.assertNotIn("降級建議", free)
        for text in (tight, free):
            self.assertIn("子代理=opus", text)
            self.assertIn("降級=sonnet", text)

    def test_model_lines_says_a_bad_value_out_loud(self) -> None:
        got = quota_messages.model_lines(self._FREE, {_SUB: "???"})
        self.assertIn("⚠️", got)
        self.assertIn("子代理=sonnet", got, "壞值退回預設，行上顯示的是實際生效值")

    def test_pace_report_is_wired_to_the_model_lines(self) -> None:
        """接線鎖：`--pace` 的全文真的經 `model_lines`（`pace_report` 的取數面要打真快取，
        行為面由 `test_context_budget_guard.py` 既有的 pace 測試承擔，這裡只鎖接線）。"""
        self.assertIn("model_lines(", inspect.getsource(quota_gate.pace_report))
        self.assertIs(quota_gate.quota_messages, quota_messages)


class SessionBriefRolesTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(session_brief.platform_utils, "is_windows",
                                    return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _brief(self, policy_env) -> str:
        def _no_cache(_now, path=None):
            raise OSError("合成：無快取")

        gate = types.SimpleNamespace(quota_policy=quota_policy, read_quota=_no_cache,
                                     policy_env=policy_env)
        return session_brief.sessionstart_brief(
            {"transcript_path": None}, gate, scan_transcript=None, resolve_window=None,
            window_evidence=None, read_context_feed=None, now=None,
            check_statusline=lambda: {"installed": True})

    def test_the_brief_prints_the_configured_roles(self) -> None:
        got = self._brief(lambda: {_HELM: "fable", _SUB: "opus"})
        for token in ("主控=fable", "子代理=opus", "降級=haiku"):
            self.assertIn(token, got)

    def test_the_brief_with_nothing_configured_says_the_helmsman_is_inherited(self) -> None:
        got = self._brief(lambda: {})
        self.assertIn("沿用存檔／設定鏈", got)
        self.assertIn("子代理=sonnet", got)

    def test_a_bad_value_is_warned_in_the_brief(self) -> None:
        self.assertIn("⚠️", self._brief(lambda: {_SUB: "???"}))

    def test_a_failing_env_source_never_costs_the_brief_itself(self) -> None:
        def _boom():
            raise RuntimeError("合成：env 來源炸了")

        got = self._brief(_boom)
        self.assertIn("[SDD-CTX-GUARD]", got)
        self.assertNotIn("模型角色", got)


# ═══════════════════════════ 7. `.env` 到行程環境、讀者、純度 ═══════════════════════════
class DotenvReachesTheRolesTest(_Sandbox):
    def test_a_value_in_dotenv_is_filled_into_the_process_env_by_apply_env_defaults(self) -> None:
        """喚醒 tick 的環境只有 PATH，`.env` 值靠這條前置填充才到得了 planner。"""
        (self.tmp / ".env").write_text(f"{_HELM}=fable\n{_SUB}=opus\n", encoding="utf-8",
                                       newline="\n")
        env: dict[str, str] = {}
        filled = quota_gate.apply_env_defaults(env, root=self.tmp)
        self.assertTrue({_HELM, _SUB} <= set(filled), filled)
        self.assertEqual(model_roles.load_model_roles(env),
                         (model_roles.ModelRoles("fable", "opus", "haiku"), []))

    def test_a_real_environment_variable_beats_the_file(self) -> None:
        (self.tmp / ".env").write_text(f"{_SUB}=opus\n", encoding="utf-8", newline="\n")
        self.set_env({_SUB: "haiku"})
        merged = quota_gate.policy_env(self.tmp)
        self.assertEqual(model_roles.load_model_roles(merged)[0].subagent, "haiku")


class ModelRolesModuleShapeTest(unittest.TestCase):
    _SRC = _REPO_ROOT / "tools" / "lib" / "model_roles.py"

    def test_every_key_has_its_real_reader_in_the_roles_module(self) -> None:
        """讀者鎖的實質：三個 attr=None 的鍵由這支檔讀，字面必須真的住在這裡。"""
        text = self._SRC.read_text(encoding="utf-8")
        for key in _ALL_KEYS:
            self.assertIn(key, text)

    def test_the_module_is_pure_no_environment_reads_and_no_io(self) -> None:
        tree = ast.parse(self._SRC.read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree)
                    if isinstance(n, ast.Import) for a in n.names}
        imported |= {(n.module or "").split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imported & {"os", "subprocess", "pathlib", "tempfile", "shutil"}, set())

    def test_the_factory_defaults_are_derived_from_env_spec_not_copied(self) -> None:
        """出廠預設只有 `ENV_SPEC` 一個家：本檔的字串常數裡不得出現任何一個家族別名（有人
        把 `ModelRoles("", "sonnet", "haiku")` 抄進來，這條就紅）。"""
        tree = ast.parse(self._SRC.read_text(encoding="utf-8"))
        strings = {n.value for n in ast.walk(tree)
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)}
        self.assertEqual(strings & set(quota_policy.MODEL_FAMILIES), set())


if __name__ == "__main__":
    unittest.main()
