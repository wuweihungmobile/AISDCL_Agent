# enforces (governance rules): R-9.2
"""`tools/fsm_runtime/context_window.py` 的回歸鎖（DEF-200-275 第四輪）。

被守的性質（Rule 9：每條都寫得出「壞掉會怎樣」）：
1. 分子算式＝`input + cache_creation + cache_read`，`output_tokens` 不計、`<synthetic>` 整筆跳過、
   半截行跳過——任一壞掉，水位就會高估／掉零／整支 hook 崩潰。
2. 分母鏈的順序與「指定 vs 推斷」的可辨識性；未確認來源不得硬擋（`may_block`）；查表阻止對
   200K 模型猜大；`claude-opus-4-1` 不得被 1m 標記誤判。
3. 量不到就放行：無路徑／不存在／boundary 在最後 usage 之後 ⇒ `used=None`。
4. 效能：每次工具呼叫都會全掃逐字稿，5MB 必須遠低於 hook 8s timeout。
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import context_window as cw  # noqa: E402


def _rec(kind: str, **kw) -> str:
    return json.dumps({"type": kind, **kw})


def _assistant(model: str, inp: int, cc: int = 0, cr: int = 0, out: int = 0) -> str:
    return _rec("assistant", message={
        "model": model,
        "usage": {"input_tokens": inp, "cache_creation_input_tokens": cc,
                  "cache_read_input_tokens": cr, "output_tokens": out},
    })


def _write(tmp: Path, lines: list[str], name: str = "s.jsonl") -> Path:
    p = tmp / name
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


class UsedOfTests(unittest.TestCase):
    def test_sums_three_fields_and_ignores_output(self) -> None:
        self.assertEqual(cw.used_of({"input_tokens": 1, "cache_creation_input_tokens": 2,
                                     "cache_read_input_tokens": 3, "output_tokens": 999}), 6)

    def test_bool_is_not_a_count(self) -> None:
        self.assertEqual(cw.used_of({"input_tokens": True, "cache_read_input_tokens": 5}), 5)

    def test_missing_all_fields_is_none_not_zero(self) -> None:
        self.assertIsNone(cw.used_of({"output_tokens": 5}))
        self.assertIsNone(cw.used_of("not a dict"))
        self.assertEqual(cw.used_of({"input_tokens": 0}), 0)


class PositiveIntTests(unittest.TestCase):
    def test_bad_values_are_zero(self) -> None:
        for bad in ("abc", "1.5", "12k", "", "0", "-5", None):
            self.assertEqual(cw.positive_int(bad), 0, msg=repr(bad))

    def test_good_value_kept(self) -> None:
        self.assertEqual(cw.positive_int("200000"), 200000)
        self.assertEqual(cw.positive_int(" 1000000 "), 1000000)


class ScanTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_last_peak_model_and_skips(self) -> None:
        p = _write(self.tmp, [
            _rec("user", message={"content": "hi"}),
            _assistant("claude-sonnet-5", 100, 50, 0, out=5000),
            _assistant("<synthetic>", 0, 0, 0),
            '{"type":"assistant","message":{"usage":{"input_tokens":',  # 半截行
            _rec("system", subtype="other", message={"usage": {"input_tokens": 999999}}),
            _assistant("claude-fable-5-1", 400, 0, 300),
        ])
        last, peak, model = cw.scan_transcript(p)
        self.assertEqual((last, peak, model), (700, 700, "claude-fable-5-1"))
        m = cw.measure(str(p))
        self.assertEqual((m.used, m.peak, m.model, m.compact_boundaries, m.stale_after_compact),
                         (700, 700, "claude-fable-5-1", 0, False))

    def test_peak_is_historical_max_not_last(self) -> None:
        p = _write(self.tmp, [_assistant("m", 900_000), _assistant("m", 100)])
        self.assertEqual(cw.scan_transcript(p), (100, 900_000, "m"))

    def test_compact_boundary_count_only_system_subtype(self) -> None:
        p = _write(self.tmp, [
            _rec("system", subtype="compact_boundary", compactMetadata={"preTokens": 1}),
            _rec("user", subtype="compact_boundary"),
            _rec("system", subtype="compact_boundary"),
        ])
        self.assertEqual(cw.compact_boundary_count(p), 2)

    def test_boundary_after_last_usage_is_stale(self) -> None:
        p = _write(self.tmp, [_assistant("m", 950_000),
                              _rec("system", subtype="compact_boundary")])
        m = cw.measure(p)
        self.assertTrue(m.stale_after_compact)
        self.assertIsNone(m.used)
        self.assertEqual(m.compact_boundaries, 1)

    def test_boundary_before_last_usage_is_fresh(self) -> None:
        p = _write(self.tmp, [_assistant("m", 950_000), _rec("system", subtype="compact_boundary"),
                              _assistant("m", 120_000)])
        m = cw.measure(p)
        self.assertFalse(m.stale_after_compact)
        self.assertEqual(m.used, 120_000)

    def test_unmetered_paths_return_none(self) -> None:
        self.assertIsNone(cw.measure(None))
        self.assertIsNone(cw.measure(""))
        self.assertIsNone(cw.measure(123))
        self.assertIsNone(cw.measure(str(self.tmp / "nope.jsonl")))
        self.assertEqual(cw.scan_transcript(self.tmp / "nope.jsonl"), (None, 0, None))
        self.assertEqual(cw.compact_boundary_count(self.tmp / "nope.jsonl"), 0)

    def test_all_synthetic_yields_used_none(self) -> None:
        p = _write(self.tmp, [_assistant("<synthetic>", 0), _assistant("<synthetic>", 0)])
        m = cw.measure(p)
        self.assertIsNotNone(m)
        self.assertIsNone(m.used)

    def test_5mb_transcript_scans_well_under_hook_timeout(self) -> None:
        filler = _rec("user", message={"content": "x" * 2000})
        lines = []
        for i in range(2600):  # ≈ 5MB
            lines.append(filler)
            if i % 10 == 0:
                lines.append(_assistant("claude-fable-5-1", 1000 + i))
        p = _write(self.tmp, lines)
        self.assertGreater(p.stat().st_size, 5_000_000)
        t0 = time.perf_counter()
        m = cw.measure(p)
        elapsed = time.perf_counter() - t0
        self.assertIsNotNone(m.used)
        self.assertLess(elapsed, 2.0, msg=f"5MB 全掃 {elapsed:.3f}s（寬鬆上界 2s；hook timeout 8s）")


class ResolveWindowTests(unittest.TestCase):
    _KNOWN = {"claude-fable-5-1": 1_000_000, "claude-haiku-4-5": 200_000}

    def test_each_tier_wins_when_earlier_tiers_are_absent(self) -> None:
        cases = [
            (dict(sdd_raw="123456"), 123456, cw.SOURCE_PINNED_SDD),
            (dict(autosdd_raw="967000"), 967000, cw.SOURCE_PINNED_AUTOSDD),
            (dict(cc_env_raw="500000"), 500000, cw.SOURCE_PINNED_CC_ENV),
            (dict(settings_window=400000), 400000, cw.SOURCE_PINNED_CC_SETTING),
            (dict(model_hint="claude-fable-5-1[1m]"), 1_000_000, cw.SOURCE_MODEL_MARKER),
        ]
        for kw, want_window, want_source in cases:
            window, source = cw.resolve_window(0, **kw)
            self.assertEqual((window, source), (want_window, want_source), msg=repr(kw))
            self.assertTrue(cw.may_block(source))

    def test_bad_pinned_values_fall_through(self) -> None:
        window, source = cw.resolve_window(0, sdd_raw="abc", autosdd_raw="0", cc_env_raw="-5",
                                           settings_window="1.5")
        self.assertEqual((window, source), (cw.CONSERVATIVE_DEFAULT_MAX_CONTEXT,
                                            cw.SOURCE_INFERRED_FLOOR))
        self.assertFalse(cw.may_block(source))

    def test_priority_order_sdd_before_autosdd(self) -> None:
        window, source = cw.resolve_window(0, sdd_raw="111111", autosdd_raw="967000")
        self.assertEqual((window, source), (111111, cw.SOURCE_PINNED_SDD))

    def test_cross_family_veto_falls_to_next_tier(self) -> None:
        window, source = cw.resolve_window(
            0, model_hint="claude-fable-5-1[1m]", observed_model="claude-sonnet-5",
            known_models={"claude-sonnet-5": 777_777})
        self.assertEqual(window, 777_777)
        self.assertTrue(source.startswith(cw.SOURCE_KNOWN_MODEL_PREFIX))

    def test_known_table_hits_and_normalization(self) -> None:
        w, s = cw.resolve_window(0, observed_model="claude-haiku-4-5", known_models=self._KNOWN)
        self.assertEqual(w, 200_000)
        self.assertTrue(cw.may_block(s))
        self.assertIn("model=claude-haiku-4-5", s)
        w, s = cw.resolve_window(0, observed_model="claude-fable-5-1", known_models=self._KNOWN)
        self.assertEqual(w, 1_000_000)
        w, s = cw.resolve_window(0, model_hint="Claude-Fable-5-1-20260601",
                                 known_models=self._KNOWN)
        self.assertEqual(w, 1_000_000)
        w, s = cw.resolve_window(0, observed_model="claude-fable-5-1-20260601[1m]".replace(
            "[1m]", ""), known_models=self._KNOWN, known_models_note="refreshed_at=2026-09-10")
        self.assertIn("refreshed_at=2026-09-10", s)

    def test_known_table_prevents_guessing_wide_for_haiku_even_past_floor(self) -> None:
        """方向鎖：haiku 4.5 是 200K；即使 peak 已 250K（不可能但假設）也不得因下界推論猜成 1M。"""
        w, s = cw.resolve_window(250_000, observed_model="claude-haiku-4-5", known_models=self._KNOWN)
        self.assertEqual(w, 200_000)

    def test_unknown_model_goes_to_inference(self) -> None:
        w, s = cw.resolve_window(150_000, observed_model="claude-unknown-9", known_models=self._KNOWN)
        self.assertEqual((w, s), (cw.CONSERVATIVE_DEFAULT_MAX_CONTEXT, cw.SOURCE_INFERRED_FLOOR))
        self.assertFalse(cw.may_block(s))
        w, s = cw.resolve_window(250_000, observed_model="claude-unknown-9", known_models=self._KNOWN)
        self.assertEqual((w, s), (cw.WIDE_MAX_CONTEXT, cw.SOURCE_INFERRED_WIDE))
        self.assertTrue(cw.may_block(s))

    def test_opus_4_1_is_not_a_wide_marker(self) -> None:
        self.assertFalse(cw.carries_wide_marker("claude-opus-4-1"))
        self.assertTrue(cw.carries_wide_marker("opus[1m]"))
        self.assertTrue(cw.carries_wide_marker("claude-opus-4-6-1m"))
        self.assertIsNone(cw.window_from_model("claude-opus-4-1"))

    def test_sources_distinguish_pinned_table_inferred(self) -> None:
        self.assertTrue(cw.SOURCE_PINNED_SDD.startswith("指定值"))
        self.assertTrue(cw.SOURCE_KNOWN_MODEL_PREFIX.startswith("查表值"))
        self.assertTrue(cw.SOURCE_INFERRED_WIDE.startswith("推斷值"))
        self.assertTrue(cw.SOURCE_INFERRED_FLOOR.startswith("推斷值"))
        self.assertIn("不硬擋", cw.SOURCE_INFERRED_FLOOR)

    def test_normalize_model_id(self) -> None:
        self.assertEqual(cw.normalize_model_id("Claude-Fable-5-1[1m]"), "claude-fable-5-1")
        self.assertEqual(cw.normalize_model_id("claude-sonnet-4-6-20260601"), "claude-sonnet-4-6")
        self.assertEqual(cw.normalize_model_id("claude-opus-4-6-1m"), "claude-opus-4-6")
        self.assertEqual(cw.normalize_model_id(None), "")

    def test_shipped_table_loads_and_has_expected_entries(self) -> None:
        table, note = cw.load_known_model_windows()
        self.assertEqual(table.get("claude-fable-5-1"), 1_000_000)
        self.assertEqual(table.get("claude-haiku-4-5"), 200_000)
        self.assertIn("seeded_from", note + "refreshed_at")

    def test_corrupt_or_missing_table_is_empty_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            self.assertEqual(cw.load_known_model_windows(bad), ({}, "無表"))
            self.assertEqual(cw.load_known_model_windows(Path(td) / "nope.json"), ({}, "無表"))


class ConvergePinnedToKnownModelTests(unittest.TestCase):
    """D14：②③④ 階（AUTOSDD_CONTEXT_WINDOW／CC env／settings autoCompactWindow）的釘值，
    若大於 observed_model 查表得到的上限，收斂到表值；① SDD_MAX_CONTEXT 永不收斂。"""
    _KNOWN = {"claude-fable-5-1": 1_000_000, "claude-haiku-4-5": 200_000}

    def test_autosdd_converges_to_smaller_table_value_for_haiku(self) -> None:
        window, source = cw.resolve_window(
            0, autosdd_raw="967000", observed_model="claude-haiku-4-5",
            known_models=self._KNOWN)
        self.assertEqual(window, 200_000)
        self.assertIn("已收斂", source)
        self.assertTrue(cw.may_block(source))

    def test_autosdd_keeps_pinned_when_table_value_is_larger_for_fable(self) -> None:
        window, source = cw.resolve_window(
            0, autosdd_raw="967000", observed_model="claude-fable-5-1",
            known_models=self._KNOWN)
        self.assertEqual((window, source), (967000, cw.SOURCE_PINNED_AUTOSDD))
        self.assertNotIn("已收斂", source)

    def test_sdd_raw_pinned_value_never_converges(self) -> None:
        window, source = cw.resolve_window(
            0, sdd_raw="967000", observed_model="claude-haiku-4-5",
            known_models=self._KNOWN)
        self.assertEqual((window, source), (967000, cw.SOURCE_PINNED_SDD))
        self.assertNotIn("已收斂", source)

    def test_observed_none_keeps_pinned(self) -> None:
        window, source = cw.resolve_window(
            0, autosdd_raw="967000", observed_model=None, known_models=self._KNOWN)
        self.assertEqual((window, source), (967000, cw.SOURCE_PINNED_AUTOSDD))

    def test_cc_env_raw_converges_same_as_autosdd(self) -> None:
        window, source = cw.resolve_window(
            0, cc_env_raw="967000", observed_model="claude-haiku-4-5",
            known_models=self._KNOWN)
        self.assertEqual(window, 200_000)
        self.assertIn("已收斂", source)

    def test_settings_window_converges_same_as_autosdd(self) -> None:
        window, source = cw.resolve_window(
            0, settings_window=967000, observed_model="claude-haiku-4-5",
            known_models=self._KNOWN)
        self.assertEqual(window, 200_000)
        self.assertIn("已收斂", source)


class TierAndExitTests(unittest.TestCase):
    def test_ratio_tier_table(self) -> None:
        self.assertIsNone(cw.ratio_tier(None, 1000))
        self.assertIsNone(cw.ratio_tier(500, 0))
        self.assertIsNone(cw.ratio_tier(690, 1000))
        self.assertEqual(cw.ratio_tier(700, 1000), "soft")
        self.assertEqual(cw.ratio_tier(850, 1000), "warn")
        self.assertEqual(cw.ratio_tier(900, 1000), "auto_compact")
        self.assertEqual(cw.ratio_tier(950, 1000), "crit")

    def test_auto_compact_exit_truth_table(self) -> None:
        self.assertFalse(cw.auto_compact_exit_due(None, 1_000_000))
        self.assertFalse(cw.auto_compact_exit_due(850_000, 1_000_000))
        self.assertFalse(cw.auto_compact_exit_due(890_000, 1_000_000))
        self.assertTrue(cw.auto_compact_exit_due(849_999, 1_000_000))
        self.assertTrue(cw.auto_compact_exit_due(120_000, 1_000_000))
        self.assertFalse(cw.auto_compact_exit_due(100, 0))

    def test_unconfirmed_notice_mentions_source_and_no_block(self) -> None:
        text = cw.unconfirmed_notice(195_000, 0.975, "CRIT", cw.SOURCE_INFERRED_FLOOR)
        self.assertIn("UNCONFIRMED-DENOM", text)
        self.assertIn("來源=", text)
        self.assertIn("不硬擋", text)


class EvidenceIoTests(unittest.TestCase):
    def test_window_evidence_reads_injected_env_and_settings_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "proj"
            home = Path(td) / "home"
            (root / ".claude").mkdir(parents=True)
            (home / ".claude").mkdir(parents=True)
            (home / ".claude" / "settings.json").write_text(
                json.dumps({"model": "claude-fable-5-1[1m]", "autoCompactWindow": 967000}),
                encoding="utf-8")
            ev = cw.window_evidence("claude-fable-5-1", env={"SDD_MAX_CONTEXT": "5"},
                                    root=root, home=home)
            self.assertEqual(ev["sdd_raw"], "5")
            self.assertIsNone(ev["autosdd_raw"])
            self.assertEqual(ev["settings_window"], 967000)
            self.assertEqual(ev["model_hint"], "claude-fable-5-1[1m]")
            self.assertIn("claude-fable-5-1", ev["known_models"])
            # 空 root／空 home ⇒ settings 值缺席，不 crash
            ev2 = cw.window_evidence(None, env={}, root=Path(td) / "empty", home=Path(td) / "empty")
            self.assertIsNone(ev2["settings_window"])
            self.assertIsNone(ev2["model_hint"])


class RefreshKnownModelWindowsTests(unittest.TestCase):
    """`refresh_known_model_windows.py`：`apply_models` 純函式；SDK 缺席 rc=2 且不寫檔（fail-loud）。
    住在本檔而非另開測試檔：LATEST fsm_runtime/tests 的檔數下限棘輪（`_TREE_FILE_FLOORS`）本輪已重釘 62，
    再加一支檔就得再釘一次——而這組測試本來就是 context_window 分母鏈查表階的一部分。"""

    def test_apply_models_merges_only_positive_int_windows(self) -> None:
        from tools.fsm_runtime.refresh_known_model_windows import apply_models
        from types import SimpleNamespace as NS
        table = {"claude-haiku-4-5": 200_000}
        models = [NS(id="claude-fable-5-1", max_input_tokens=1_000_000),
                  {"id": "claude-sonnet-5-20260601", "max_input_tokens": 1_000_000},
                  NS(id="bad-bool", max_input_tokens=True), NS(id="bad-zero", max_input_tokens=0),
                  NS(id="no-field"), NS(id="", max_input_tokens=5)]
        out = apply_models(table, models)
        self.assertEqual(out, {"claude-fable-5-1": 1_000_000, "claude-haiku-4-5": 200_000,
                               "claude-sonnet-5": 1_000_000})
        self.assertEqual(table, {"claude-haiku-4-5": 200_000}, msg="純函式不得改輸入")

    def test_sdk_absent_returns_2_and_writes_nothing(self) -> None:
        import builtins
        from unittest.mock import patch
        from tools.fsm_runtime import refresh_known_model_windows as rk
        real_import = builtins.__import__

        def _no_anthropic(name, *a, **k):
            if name == "anthropic":
                raise ImportError("simulated: anthropic not installed")
            return real_import(name, *a, **k)

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "kmw.json"
            with patch.object(builtins, "__import__", _no_anthropic):
                rc = rk.main(["--path", str(target)])
            self.assertEqual(rc, 2)
            self.assertFalse(target.exists(), msg="SDK 缺席不得寫檔")

    def test_api_failure_returns_3_and_writes_nothing(self) -> None:
        import sys as _sys
        from types import ModuleType, SimpleNamespace as NS
        from unittest.mock import patch
        from tools.fsm_runtime import refresh_known_model_windows as rk

        class _Boom:
            def __init__(self):
                self.models = NS(list=lambda: (_ for _ in ()).throw(RuntimeError("401 no credentials")))
        fake = ModuleType("anthropic")
        fake.Anthropic = _Boom
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "kmw.json"
            with patch.dict(_sys.modules, {"anthropic": fake}):
                rc = rk.main(["--path", str(target)])
            self.assertEqual(rc, 3)
            self.assertFalse(target.exists())

    def test_success_writes_table_with_refreshed_at(self) -> None:
        import sys as _sys
        from types import ModuleType, SimpleNamespace as NS
        from unittest.mock import patch
        from tools.fsm_runtime import refresh_known_model_windows as rk

        class _Ok:
            def __init__(self):
                self.models = NS(list=lambda: [NS(id="claude-fable-5-1", max_input_tokens=1_000_000)])
        fake = ModuleType("anthropic")
        fake.Anthropic = _Ok
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "kmw.json"
            with patch.dict(_sys.modules, {"anthropic": fake}):
                rc = rk.main(["--path", str(target)])
            self.assertEqual(rc, 0)
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc["models"], {"claude-fable-5-1": 1_000_000})
            self.assertTrue(doc["refreshed_at"].endswith("+00:00"))
            self.assertIsNone(doc["seeded_from"])
            self.assertFalse(list(Path(td).glob("*.part.*")))


if __name__ == "__main__":
    unittest.main()
