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
import os
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


def _real_known_models() -> tuple[dict[str, int], str, dict[str, int], str]:
    """兩側查表資料，各自經自己的 `known_model_windows_path()`／`KNOWN_MODEL_WINDOWS_PATH`
    解析同一份 `known_model_windows.json`（D27／ARCH-A4-01：資料唯一的家）。"""
    known_root, note_root = guard.load_known_model_windows(guard.known_model_windows_path())
    known_sdd, note_sdd = cw.load_known_model_windows()
    return known_root, note_root, known_sdd, note_sdd


#: (peak, observed_model, 期望來源字串裡要出現的分類字)。`claude-mystery-9` 不在表裡，
#: 落下界推論——與 `_WINDOW_CASES` 的既有 `known_models={}` 中和案例互補，不取代：
#: 那組證明「沒有 ⑥ 這一階時兩側同構」，這組證明「有 ⑥ 這一階時兩側也同構」。
_LOOKUP_STAGE_CASES = [
    (0, "claude-fable-5-1", "查表"),
    (0, "claude-haiku-4-5", "查表"),
    (0, "claude-mystery-9", "推斷"),
]


def known_model_lookup_problems(
    known_root: dict[str, int], note_root: str, known_sdd: dict[str, int], note_sdd: str,
) -> list[str]:
    """D27：⑥ 查表階 parity 判準（純函式，紅綠由 bug-injection 自證）。"""
    problems: list[str] = []
    if known_root != known_sdd:
        problems.append(f"known_models tables differ：root={len(known_root)} keys，"
                         f"sdd={len(known_sdd)} keys")
    for peak, observed, category in _LOOKUP_STAGE_CASES:
        g_window, g_source = guard.resolve_window(
            peak, observed_model=observed, known_models=known_root,
            known_models_note=note_root)
        s_window, s_source = cw.resolve_window(
            peak, observed_model=observed, known_models=known_sdd,
            known_models_note=note_sdd)
        if g_window != s_window:
            problems.append(f"lookup[{observed}] window: {g_window} vs {s_window}")
        if category not in g_source:
            problems.append(f"lookup[{observed}] root source 缺 {category!r}：{g_source}")
        if category not in s_source:
            problems.append(f"lookup[{observed}] sdd source 缺 {category!r}：{s_source}")
        if guard.may_block(g_source) != cw.may_block(s_source):
            problems.append(f"lookup[{observed}] may_block mismatch")
    # 查表階本身兩側會用同一份資料＋同一個 note 組字串，來源說明應逐字相等
    # （不同於下面「有釘值不收斂」那格——根層 D21／SD-09 在那格多附一段稽核註記，
    # SDD 側沒有，這是既有已知差異，非本輪 ARCH-A4-01 射程）。
    for observed in ("claude-fable-5-1", "claude-haiku-4-5"):
        _, g_source = guard.resolve_window(0, observed_model=observed, known_models=known_root,
                                            known_models_note=note_root)
        _, s_source = cw.resolve_window(0, observed_model=observed, known_models=known_sdd,
                                         known_models_note=note_sdd)
        if g_source != s_source:
            problems.append(f"lookup[{observed}] 來源字串未逐字相等：{g_source!r} vs {s_source!r}")
    # 有釘值 967000＋fable：兩側皆 967000、不收斂（window／may_block 相等）。
    g_window, g_source = guard.resolve_window(
        0, "967000", observed_model="claude-fable-5-1", known_models=known_root,
        known_models_note=note_root)
    s_window, s_source = cw.resolve_window(
        0, autosdd_raw="967000", observed_model="claude-fable-5-1", known_models=known_sdd,
        known_models_note=note_sdd)
    if (g_window, guard.may_block(g_source)) != (s_window, cw.may_block(s_source)):
        problems.append(f"pinned+fable: {(g_window, guard.may_block(g_source))} vs "
                         f"{(s_window, cw.may_block(s_source))}")
    if g_window != 967_000 or "不收斂" not in g_source:
        problems.append(f"pinned+fable root 不收斂形狀不對：{g_source!r}")
    return problems


class KnownModelLookupStageParityTest(unittest.TestCase):
    """D27（DEF-200-275 第七輪，ARCH-A4-01）：⑥ 查表階的 parity，用真實
    `known_model_windows.json` 內容同時餵兩側——四方複審判定 D21「只在有 pin 時才查表」
    的捷徑本身就是缺陷根因（沒有釘值的機器上兩側對同一份逐字稿算出不同答案，差可達
    5 倍）。全文與端到端量測見 `docs/06_quality/CrossPlatform_DEF200275_Context_
    Metering_Evidence.md`〈第七輪〉。"""

    def test_no_pin_lookup_and_pinned_unconverged_shapes_match(self) -> None:
        self.assertEqual(known_model_lookup_problems(*_real_known_models()), [])

    def test_bug_injection_on_the_lookup_stage_turns_red(self) -> None:
        """自證：弄壞 SDD `known_model_window()`，判準必須抓到——否則這支鎖沒有鑑別力。"""
        real_known = _real_known_models()
        with mock.patch.object(cw, "known_model_window", lambda *a, **k: None):
            self.assertTrue(known_model_lookup_problems(*real_known),
                            msg="injected known_model_window but parity stayed green")


#: D32-5：harness 回報階（⓪／⓪′）的 parity 案例——`known_models={}` 中和，聚焦
#: `harness_window`／`harness_note` 這一階本身。
_HARNESS_CASES = [
    # (peak, autosdd_raw, harness_window, harness_note)
    (0, None, 1_000_000, ""),
    (0, "967000", 1_000_000, "model=claude-fable-5-1"),
    (0, "1000000", 1_000_000, "model=claude-fable-5-1"),
    (999_999, "200000", None, ""),  # 沒有 harness ⇒ 兩側都落回既有五階
]


def harness_stage_problems() -> list[str]:
    """D32-5：純函式，紅綠由 bug-injection 自證（見下方測試）。"""
    problems: list[str] = []
    for peak, autosdd_raw, harness_window, harness_note in _HARNESS_CASES:
        g_window, g_source = guard.resolve_window(
            peak, autosdd_raw, harness_window=harness_window, harness_note=harness_note)
        s_window, s_source = cw.resolve_window(
            peak, autosdd_raw=autosdd_raw, harness_window=harness_window,
            harness_note=harness_note)
        got = (g_window, guard.may_block(g_source)), (s_window, cw.may_block(s_source))
        if got[0] != got[1]:
            case = (peak, autosdd_raw, harness_window, harness_note)
            problems.append(f"resolve_window[harness]{case}: {got[0]} vs {got[1]}")
        if harness_window and ("harness" not in g_source or "harness" not in s_source):
            problems.append(f"harness stage source 未標 harness：{g_source!r} vs {s_source!r}")
    return problems


class HarnessStageParityTest(unittest.TestCase):
    """D32-3：兩側 resolve_window 的 harness 回報階（root ⓪／SDD ⓪′）逐項相等。"""

    def test_cases_agree(self) -> None:
        self.assertEqual(harness_stage_problems(), [])

    def test_bug_injection_turns_it_red(self) -> None:
        with mock.patch.object(cw, "SOURCE_HARNESS", "壞掉的來源字串"):
            self.assertTrue(harness_stage_problems(),
                            msg="injected SOURCE_HARNESS but parity stayed green")

    def test_context_feed_path_matches_across_root_sdd_and_the_status_line_writer(self) -> None:
        """D32-2：三份逐字同構的 `context_feed_path()`（本檔另兩份見根層／SDD 各自的
        `context_budget_guard.py`／`context_window.py`；status line 寫入端另有一份，
        由 `tools/statusline_context_feed.py` 自己的單元測試守）。一字之差都要在此現形。
        """
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(
                os.environ, {"AUTOSDD_CONTEXT_FEED_DIR": td}, clear=False):
            for sid in ("abc-123", "sess.with.dots", "17e2da67-e140-43a8-9817-d1b6f61f3f7a"):
                self.assertEqual(guard.context_feed_path(sid), cw.context_feed_path(sid))


if __name__ == "__main__":
    unittest.main()
