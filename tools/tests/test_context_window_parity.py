#!/usr/bin/env python3
"""根層守衛 `context_budget_guard.py` ↔ SDD LATEST `context_window.py` 的 parity 鎖
（DEF-200-275 第四輪 D9）。

WHY：兩子專案刻意不跨 import，SDD 側是「複製一份」，而複製的知識只有一份會被改。
本檔以同一組夾具比對分子算式、model 判定與分母鏈（SDD 專屬階中和後的 (window, may_block)）；
任一邊單獨改動即紅。附 bug-injection 自證；LATEST 走 `tools/lib/sdd_latest.py`，解不出即
fail（不 skip）。
"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(_REPO_ROOT / "tools" / "lib"))
import context_budget_guard as guard  # noqa: E402
import sdd_latest  # noqa: E402


def _load_sdd_context_window():
    latest = sdd_latest.resolve_latest_root(_REPO_ROOT / "AISDLC_SDD")
    path = latest / "tools" / "fsm_runtime" / "context_window.py"
    assert path.is_file(), f"SDD LATEST 缺 context_window.py：{path}"
    spec = importlib.util.spec_from_file_location("sdd_context_window_parity", path)
    mod = importlib.util.module_from_spec(spec)
    # `@dataclass` 在 `from __future__ import annotations` 下需要 sys.modules[cls.__module__]
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


cw = _load_sdd_context_window()


def _rec(kind: str, **kw) -> str:
    return json.dumps({"type": kind, **kw})


def _asst(model: str, inp: int, cc: int = 0, cr: int = 0, out: int = 0) -> str:
    usage = {"input_tokens": inp, "cache_creation_input_tokens": cc,
             "cache_read_input_tokens": cr, "output_tokens": out}
    return _rec("assistant", message={"model": model, "usage": usage})


_BOUNDARY = _rec("system", subtype="compact_boundary")
_HALF_LINE = '{"type":"assistant","message":{"usage":{"input_tokens":'
_TRANSCRIPTS: dict[str, list[str]] = {
    "normal": [_asst("claude-fable-5-1", 100, 50, 25, out=9000),
               _asst("claude-fable-5-1", 400, 0, 300)],
    "synthetic": [_asst("claude-opus-5", 500), _asst("<synthetic>", 0)],
    "half_line": [_asst("claude-sonnet-5", 700), _HALF_LINE],
    "non_assistant": [_rec("system", message={"usage": {"input_tokens": 999}}),
                      _asst("claude-haiku-4-5", 5)],
    "output_only": [_rec("assistant", message={"model": "m", "usage": {"output_tokens": 5}})],
    "boundaries": [_asst("m", 1), _BOUNDARY, _rec("user", subtype="compact_boundary"),
                   _BOUNDARY, _asst("m", 2)],
    "empty": [],
}
_USAGES = [
    {"input_tokens": 1, "cache_creation_input_tokens": 2, "cache_read_input_tokens": 3,
     "output_tokens": 9},
    {"input_tokens": True, "cache_read_input_tokens": 5}, {"output_tokens": 5}, "x", None, {},
]
_MODELS = ["claude-fable-5-1[1m]", "opus[1m]", "claude-opus-4-6-1m", "claude-opus-4-1",
           "claude-sonnet-5", "claude-haiku-4-5", "<synthetic>", "", None, "CLAUDE-OPUS-5"]
# (peak, env_raw, cc_raw, settings_window, model_hint, observed_model)
_WINDOW_CASES = [
    (0, None, None, None, None, None),
    (250_000, None, None, None, None, None),
    (0, "967000", None, None, None, None),
    (0, "abc", "500000", None, None, None),
    (0, "0", "-5", 400000, None, None),
    (0, None, None, "1.5", "claude-fable-5-1[1m]", "claude-fable-5-1"),
    (0, None, None, None, "claude-fable-5-1[1m]", "claude-sonnet-5"),
    (300_000, None, None, None, "opus[1m]", "<synthetic>"),
    (0, None, None, None, "claude-opus-4-1", None),
    (199_999, None, None, None, None, "claude-haiku-4-5"),
]


def parity_problems(tmp: Path) -> list[str]:
    problems = [f"used_of({u!r})" for u in _USAGES if guard.used_of(u) != cw.used_of(u)]
    for name, lines in list(_TRANSCRIPTS.items()) + [("missing", None)]:
        p = tmp / f"{name}.jsonl"
        if lines is not None:
            p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        g, s = guard.scan_transcript(p), cw.scan_transcript(p)
        if g != s:
            problems.append(f"scan_transcript[{name}]: {g} vs {s}")
        if guard.compact_boundary_count(p) != cw.compact_boundary_count(p):
            problems.append(f"compact_boundary_count[{name}]")
    for m in _MODELS:
        if guard.carries_wide_marker(m) != cw.carries_wide_marker(m):
            problems.append(f"carries_wide_marker({m!r})")
        if guard.model_family(m) != cw.model_family(m):
            problems.append(f"model_family({m!r})")
        problems += [f"window_from_model({m!r}, {o!r})" for o in _MODELS
                     if guard.window_from_model(m, o) != cw.window_from_model(m, o)]
    for peak, env_raw, cc_raw, settings_window, hint, observed in _WINDOW_CASES:
        g_window, g_source = guard.resolve_window(
            peak, env_raw, cc_window_raw=cc_raw, settings_window=settings_window,
            model_hint=hint, observed_model=observed)
        s_window, s_source = cw.resolve_window(
            peak, sdd_raw=None, autosdd_raw=env_raw, cc_env_raw=cc_raw,
            settings_window=settings_window, model_hint=hint, observed_model=observed,
            known_models={})
        got = (g_window, guard.may_block(g_source)), (s_window, cw.may_block(s_source))
        if got[0] != got[1]:
            case = (peak, env_raw, cc_raw, settings_window, hint, observed)
            problems.append(f"resolve_window{case}: {got[0]} vs {got[1]}")
    return problems


class ContextWindowParityTest(unittest.TestCase):
    def test_sdd_copy_matches_root_guard_on_shared_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(parity_problems(Path(td)), [])

    def test_constants_agree(self) -> None:
        self.assertEqual((guard.CONSERVATIVE_WINDOW, guard.WIDE_WINDOW),
                         (cw.CONSERVATIVE_DEFAULT_MAX_CONTEXT, cw.WIDE_MAX_CONTEXT))
        self.assertEqual((guard.USAGE_FIELDS, guard.SYNTHETIC_MODEL),
                         (cw.USAGE_FIELDS, cw.SYNTHETIC_MODEL))

    def test_bug_injection_turns_the_criterion_red(self) -> None:
        """自證：弄壞 SDD 任一函式，判準必須抓到——否則這支鎖沒有鑑別力。"""
        injections = [("used_of", lambda usage: 0),
                      ("carries_wide_marker", lambda model: False),
                      ("model_family", lambda model: ""),
                      ("may_block", lambda source: True)]
        for name, broken in injections:
            with tempfile.TemporaryDirectory() as td, mock.patch.object(cw, name, broken):
                self.assertTrue(parity_problems(Path(td)),
                                msg=f"injected {name} but parity stayed green")


if __name__ == "__main__":
    unittest.main()
