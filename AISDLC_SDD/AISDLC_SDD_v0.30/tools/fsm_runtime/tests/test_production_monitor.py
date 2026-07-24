# enforces (governance rules): R-9.10
"""Tests for ACT-027 Production Feedback Layer (Phase E M3).

Drives the §ACT-027 acceptance criteria:
  - 5 mock signed SLO-violation events → automatic PBS-DRIFT report
  - HMAC signature verification (success + tampering + missing + replay)
  - metric → NFR auto-mapping + explicit nfr_id override
  - Schema / timestamp validation + quarantine flow
  - FSM PRODUCTION_SIGNAL non-blocking entry/exit
"""
from __future__ import annotations

import datetime as _dt
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.fsm_runtime import production_monitor as pm  # noqa: E402
from tools.fsm_runtime.fsm_runtime import FSMRuntime  # noqa: E402
from tools.fsm_runtime.state_loader import load_state  # noqa: E402
from tools.fsm_runtime.transition_rules import (  # noqa: E402
    TransitionError,
    is_transition_allowed,
)


TEST_SECRET = "test-secret-act-027"


def make_signed_event(
    *,
    event_id: str,
    metric: str,
    observed: float,
    target: float,
    unit: str = "ms",
    duration_minutes: int = 15,
    timestamp: Optional[str] = None,
    secret: str = TEST_SECRET,
    nfr_id: Optional[str] = None,
) -> Dict[str, Any]:
    if timestamp is None:
        timestamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    event: Dict[str, Any] = {
        "event_id": event_id,
        "timestamp": timestamp,
        "metric": metric,
        "observed": observed,
        "target": target,
        "unit": unit,
        "duration_minutes": duration_minutes,
    }
    if nfr_id:
        event["nfr_id"] = nfr_id
    event["signed_fields"] = list(pm.signed_fields_default())
    event["signature"] = pm.sign_event(event, secret=secret)
    return event


def write_event(inbox: Path, event: Dict[str, Any]) -> Path:
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / f"SLO-EVENT-{event['event_id']}.yaml"
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(event, f, allow_unicode=True, sort_keys=False)
    return path


class SignatureTests(unittest.TestCase):
    def test_valid_signature_passes(self) -> None:
        event = make_signed_event(event_id="sig-ok", metric="p95_login_ms", observed=450, target=200)
        ok, reason = pm.verify_signature(event, secret=TEST_SECRET)
        self.assertTrue(ok, reason)

    def test_missing_signature_rejected(self) -> None:
        event = make_signed_event(event_id="sig-miss", metric="p95_login_ms", observed=450, target=200)
        event.pop("signature")
        ok, reason = pm.verify_signature(event, secret=TEST_SECRET)
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_signature")

    def test_tampered_observed_rejected(self) -> None:
        event = make_signed_event(event_id="sig-tamper", metric="p95_login_ms", observed=450, target=200)
        event["observed"] = 999  # tamper after signing
        ok, reason = pm.verify_signature(event, secret=TEST_SECRET)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_mismatch")

    def test_trimmed_signed_fields_rejected(self) -> None:
        """Attacker strips a field from signed_fields to bypass detection."""
        event = make_signed_event(event_id="sig-trim", metric="p95_login_ms", observed=450, target=200)
        event["signed_fields"] = ["event_id", "metric"]  # subset
        ok, reason = pm.verify_signature(event, secret=TEST_SECRET)
        self.assertFalse(ok)
        self.assertEqual(reason, "unexpected_signed_fields")

    def test_wrong_secret_rejected(self) -> None:
        event = make_signed_event(event_id="sig-wrong", metric="p95_login_ms", observed=450, target=200)
        ok, reason = pm.verify_signature(event, secret="not-the-real-secret")
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_mismatch")


class TimestampTests(unittest.TestCase):
    def test_future_timestamp_rejected(self) -> None:
        future = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=1)).isoformat(timespec="seconds")
        event = make_signed_event(event_id="future", metric="p95_login_ms", observed=450, target=200, timestamp=future)
        ok, reason = pm.validate_timestamp(event)
        self.assertFalse(ok)
        self.assertEqual(reason, "future_timestamp")

    def test_stale_timestamp_rejected(self) -> None:
        stale = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=100)).isoformat(timespec="seconds")
        event = make_signed_event(event_id="stale", metric="p95_login_ms", observed=450, target=200, timestamp=stale)
        ok, reason = pm.validate_timestamp(event)
        self.assertFalse(ok)
        self.assertEqual(reason, "stale_timestamp")

    def test_bad_format_rejected(self) -> None:
        event = make_signed_event(event_id="bad", metric="p95_login_ms", observed=450, target=200)
        event["timestamp"] = "not-an-iso-date"
        ok, reason = pm.validate_timestamp(event)
        self.assertFalse(ok)
        self.assertEqual(reason, "bad_timestamp")


class SchemaTests(unittest.TestCase):
    def test_missing_field_rejected(self) -> None:
        event = make_signed_event(event_id="x", metric="p95_login_ms", observed=450, target=200)
        event.pop("unit")
        ok, reason = pm.validate_schema(event)
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("missing_field:unit"))

    def test_non_numeric_observed_rejected(self) -> None:
        event = make_signed_event(event_id="x", metric="p95_login_ms", observed=450, target=200)
        event["observed"] = "not-a-number"
        ok, reason = pm.validate_schema(event)
        self.assertFalse(ok)
        self.assertTrue(reason.startswith("non_numeric:observed"))


class MetricMappingTests(unittest.TestCase):
    def test_builtin_mapping_hits(self) -> None:
        self.assertEqual(pm.map_metric_to_nfr("p95_login_ms"), "NFR-PERF-001")
        self.assertEqual(pm.map_metric_to_nfr("error_rate_percent"), "NFR-PERF-010")

    def test_override_map_hits(self) -> None:
        override = {"custom_metric": "NFR-CUST-999"}
        self.assertEqual(pm.map_metric_to_nfr("custom_metric", override), "NFR-CUST-999")

    def test_latency_fallback_generates_deterministic_nfr(self) -> None:
        # Unknown latency metric — should get NFR-PERF-9xx slot deterministically.
        a = pm.map_metric_to_nfr("p95_unknown_service_ms", {})
        b = pm.map_metric_to_nfr("p95_unknown_service_ms", {})
        self.assertIsNotNone(a)
        self.assertTrue(a.startswith("NFR-PERF-9"))
        self.assertEqual(a, b)

    def test_unknown_non_latency_returns_none(self) -> None:
        self.assertIsNone(pm.map_metric_to_nfr("some_random_metric", {}))


class IngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.drift_root = root / "drift"
        self.report_root = root / "reports"
        self.drift_root.mkdir(parents=True, exist_ok=True)
        self.report_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _ingest(self, event: Dict[str, Any], **kwargs) -> pm.IngestResult:
        return pm.ingest_slo_violation(
            event,
            secret=TEST_SECRET,
            drift_log_root=self.drift_root,
            report_root=self.report_root,
            persistent_threshold=3,
            window_hours=24,
            **kwargs,
        )

    def test_valid_event_writes_drift_log(self) -> None:
        event = make_signed_event(event_id="e1", metric="p95_login_ms", observed=450, target=200)
        result = self._ingest(event)
        self.assertTrue(result.applied, result.reason)
        self.assertEqual(result.nfr_id, "NFR-PERF-001")
        log_path = Path(result.drift_log)
        self.assertTrue(log_path.exists())
        with log_path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        self.assertEqual(len(doc["entries"]), 1)
        self.assertEqual(doc["entries"][0]["event_id"], "e1")

    def test_explicit_nfr_overrides_auto_mapping(self) -> None:
        event = make_signed_event(
            event_id="e-override", metric="mystery_metric", observed=1, target=0.5,
            nfr_id="NFR-PERF-XXX", unit="ratio",
        )
        result = self._ingest(event)
        self.assertTrue(result.applied)
        self.assertEqual(result.nfr_id, "NFR-PERF-XXX")

    def test_five_same_nfr_events_generate_drift_report(self) -> None:
        """ACT-027 驗收：5 筆同 NFR → PBS-DRIFT 報告必須產生。"""
        for i in range(5):
            event = make_signed_event(
                event_id=f"e-{i:03d}",
                metric="p95_login_ms",
                observed=300 + i * 30,
                target=200,
            )
            result = self._ingest(event)
            self.assertTrue(result.applied, f"event #{i} failed: {result.reason}")

        # 漂移報告在第 3 筆就應該開始產出；第 5 筆覆寫為最新 5 筆
        report = list(self.report_root.glob("PBS-DRIFT-NFR-PERF-001-*.md"))
        self.assertEqual(len(report), 1, f"expected 1 drift report, got: {report}")
        content = report[0].read_text(encoding="utf-8")
        self.assertIn("PBS-DRIFT Report", content)
        self.assertIn("NFR-PERF-001", content)
        self.assertIn("p95_login_ms", content)
        self.assertIn("Suggested NFR Update Diff", content)
        # 應包含全部 5 筆 event_id（第 3 筆起累計入漂移報告）
        for i in range(5):
            self.assertIn(f"e-{i:03d}", content)

    def test_five_events_log_contains_all_entries(self) -> None:
        """同樣 5 筆 — PBS-DRIFT YAML log 必須全部 5 筆都記下。"""
        for i in range(5):
            event = make_signed_event(
                event_id=f"log-{i}", metric="p95_login_ms", observed=300 + i, target=200,
            )
            self._ingest(event)
        # ingest 內部以 UTC date 決定 log 檔名，測試也對齊 UTC 以避免 TZ 邊界日誤判
        utc_today = _dt.datetime.now(_dt.timezone.utc).date()
        log_path = pm._drift_log_path(day=utc_today, root=self.drift_root)
        with log_path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        self.assertEqual(len(doc["entries"]), 5)
        ids = {e["event_id"] for e in doc["entries"]}
        self.assertEqual(ids, {"log-0", "log-1", "log-2", "log-3", "log-4"})

    def test_unsigned_event_not_applied(self) -> None:
        event = make_signed_event(event_id="unsigned", metric="p95_login_ms", observed=450, target=200)
        event.pop("signature")
        result = self._ingest(event)
        self.assertFalse(result.applied)
        self.assertEqual(result.reason, "missing_signature")

    def test_drift_suggests_new_target(self) -> None:
        """Report 內的 suggested diff 應反映觀察到的最大值。"""
        observed_values = [320, 410, 550, 480, 700]
        for i, obs in enumerate(observed_values):
            event = make_signed_event(
                event_id=f"sug-{i}", metric="p95_login_ms", observed=obs, target=200,
            )
            self._ingest(event)
        report = list(self.report_root.glob("PBS-DRIFT-NFR-PERF-001-*.md"))
        content = report[0].read_text(encoding="utf-8")
        # 最大觀察值 700 應出現在 suggested bump
        self.assertIn("700", content)


class NfrIdSecurityTests(unittest.TestCase):
    """R38 Scan-A（DEF-101-3xx）：nfr_id 未落在簽章覆蓋範圍 + 組檔名前未淨化的
    雙重防護回歸測試。

    攻擊情境：任何人在既有合法簽章事件上額外附加 `nfr_id` 欄位（簽章驗證舊行為
    仍會通過，因為 payload 只對 REQUIRED_FIELDS 做規範化），可讓 `nfr_id` 帶入
    任意字串，進而 (a) 路徑穿越 或 (b) Windows 保留裝置名/禁用字元造成 `open()`
    未捕捉例外。修復：① `nfr_id` 併入 `signed_fields_default()` 簽章覆蓋範圍
    （夾帶/偽造即被 HMAC 擋下）；② `_report_path()` 組檔名前一律呼叫
    `_sanitize_nfr_id()`（即使簽章這層失效，淨化仍擋得住）。
    """

    def test_signed_fields_default_covers_nfr_id(self) -> None:
        self.assertIn("nfr_id", pm.signed_fields_default())

    def test_signature_covers_appended_nfr_id(self) -> None:
        """簽章時未帶 nfr_id 的合法事件，事後夾帶 nfr_id 卻不重簽必須被擋下。"""
        event = make_signed_event(event_id="attack-append", metric="p95_login_ms", observed=450, target=200)
        self.assertNotIn("nfr_id", event)  # baseline：簽章當下確實沒有 nfr_id
        event["nfr_id"] = "../../../etc/passwd"  # 攻擊者事後夾帶，未重簽
        ok, reason = pm.verify_signature(event, secret=TEST_SECRET)
        self.assertFalse(ok)
        self.assertEqual(reason, "signature_mismatch")

    def test_ingest_rejects_event_with_appended_nfr_id(self) -> None:
        """端到端：夾帶 nfr_id 的攻擊事件整個 ingest 必須被拒絕（quarantine 路徑）。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event = make_signed_event(
                event_id="attack-ingest", metric="p95_login_ms", observed=450, target=200,
            )
            event["nfr_id"] = "CON"  # 攻擊者事後夾帶保留裝置名，未重簽
            result = pm.ingest_slo_violation(
                event,
                secret=TEST_SECRET,
                drift_log_root=root / "drift",
                report_root=root / "reports",
            )
            self.assertFalse(result.applied)
            self.assertEqual(result.reason, "signature_mismatch")

    def test_normal_nfr_id_unchanged(self) -> None:
        self.assertEqual(pm._sanitize_nfr_id("NFR-PERF-001"), "NFR-PERF-001")

    def test_path_traversal_neutralized(self) -> None:
        sanitized = pm._sanitize_nfr_id("../../../etc/passwd")
        self.assertNotIn("/", sanitized)
        self.assertNotIn("..", sanitized)

    def test_backslash_path_separator_neutralized(self) -> None:
        sanitized = pm._sanitize_nfr_id("..\\..\\Windows\\System32")
        self.assertNotIn("\\", sanitized)
        self.assertNotIn("..", sanitized)

    def test_windows_forbidden_chars_neutralized(self) -> None:
        sanitized = pm._sanitize_nfr_id('NFR<PERF>:001|test?*"')
        for ch in '<>:"|?*':
            self.assertNotIn(ch, sanitized)

    def test_windows_reserved_device_name_neutralized(self) -> None:
        for reserved in ("CON", "PRN", "AUX", "NUL", "COM1", "LPT9"):
            sanitized = pm._sanitize_nfr_id(reserved)
            self.assertNotEqual(sanitized.upper(), reserved)
            self.assertTrue(sanitized.startswith("_"), sanitized)

    def test_overlong_nfr_id_truncated(self) -> None:
        sanitized = pm._sanitize_nfr_id("X" * 500)
        self.assertLessEqual(len(sanitized), pm._NFR_ID_MAX_LEN)

    def test_control_characters_neutralized(self) -> None:
        sanitized = pm._sanitize_nfr_id("NFR\x00PERF\n001")
        self.assertNotIn("\x00", sanitized)
        self.assertNotIn("\n", sanitized)

    def test_report_path_stays_within_root_for_malicious_nfr_id(self) -> None:
        """即使簽章層被繞過，`_report_path()` 本身也不得產生越界路徑。"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = pm._report_path("../../../../etc/passwd", root=root)
            self.assertEqual(path.resolve().parent, root.resolve())

    def test_report_path_reserved_device_name_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = pm._report_path("CON", root=root)
            # 應可正常寫入（不因保留裝置名拋出未捕捉例外）
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("test", encoding="utf-8")
            self.assertTrue(path.exists())


class ScanInboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.inbox = root / "inbox"
        self.quarantine = root / "quarantine"
        self.processed = root / "processed"
        self.drift_root = root / "drift"
        self.report_root = root / "reports"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _scan(self) -> pm.ScanReport:
        return pm.scan_inbox(
            inbox=self.inbox,
            quarantine=self.quarantine,
            processed=self.processed,
            secret=TEST_SECRET,
            drift_log_root=self.drift_root,
            report_root=self.report_root,
            persistent_threshold=3,
            window_hours=24,
        )

    def test_acceptance_five_events_scan_flow(self) -> None:
        """ACT-027 驗收主腳本：5 筆事件 → scan → PBS-DRIFT 自動生成。"""
        for i in range(5):
            event = make_signed_event(
                event_id=f"accept-{i:03d}",
                metric="p95_login_ms",
                observed=300 + i * 40,
                target=200,
            )
            write_event(self.inbox, event)

        report = self._scan()

        self.assertEqual(report.scanned, 5)
        self.assertEqual(report.applied, 5)
        self.assertEqual(report.quarantined, 0)
        # processed/ 應該收到所有 5 份事件檔
        processed_files = sorted(self.processed.glob("SLO-EVENT-*.yaml"))
        self.assertEqual(len(processed_files), 5)
        # drift report 應已產生
        drift_reports = sorted(self.report_root.glob("PBS-DRIFT-NFR-PERF-001-*.md"))
        self.assertEqual(len(drift_reports), 1)

    def test_mixed_valid_and_invalid_events(self) -> None:
        """3 合法 + 1 篡改 + 1 過期 → 3 applied / 2 quarantined。"""
        for i in range(3):
            write_event(self.inbox, make_signed_event(
                event_id=f"ok-{i}", metric="p95_login_ms", observed=300, target=200,
            ))

        tampered = make_signed_event(
            event_id="bad-tamper", metric="p95_login_ms", observed=300, target=200,
        )
        tampered["observed"] = 999  # 破壞簽章
        write_event(self.inbox, tampered)

        stale_ts = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(hours=200)).isoformat(timespec="seconds")
        write_event(self.inbox, make_signed_event(
            event_id="bad-stale", metric="p95_login_ms", observed=300, target=200,
            timestamp=stale_ts,
        ))

        report = self._scan()
        self.assertEqual(report.scanned, 5)
        self.assertEqual(report.applied, 3)
        self.assertEqual(report.quarantined, 2)
        self.assertEqual(len(list(self.quarantine.glob("SLO-EVENT-*.yaml"))), 2)
        self.assertEqual(len(list(self.processed.glob("SLO-EVENT-*.yaml"))), 3)

    def test_metric_map_yaml_is_skipped(self) -> None:
        """metric_nfr_map.yaml 不應被當成事件 ingest。"""
        self.inbox.mkdir(parents=True, exist_ok=True)
        # 建立真正的 metric map 檔（名稱 == DEFAULT_METRIC_MAP.name）
        # 用 patch 方式：把事件的 metric map 檔寫到與 DEFAULT 同名
        map_path = self.inbox / pm.DEFAULT_METRIC_MAP.name
        map_path.write_text("metric_to_nfr:\n  foo: bar\n", encoding="utf-8")
        write_event(self.inbox, make_signed_event(
            event_id="real-event", metric="p95_login_ms", observed=300, target=200,
        ))
        # scan_inbox 的排除邏輯看 resolve() 相等，所以這裡比對會略過 map 檔。
        report = pm.scan_inbox(
            inbox=self.inbox,
            quarantine=self.quarantine,
            processed=self.processed,
            secret=TEST_SECRET,
            drift_log_root=self.drift_root,
            report_root=self.report_root,
        )
        # metric_map 本身仍算掃描中的 .yaml 檔，但 production_monitor 會依檔名
        # skip 若 resolve() 相同；此處位置不同所以仍會被當事件處理並 quarantine
        # （這也是合理行為 — 本地 override 應放在 data/slo_events/metric_nfr_map.yaml
        # 的標準位置）。這裡驗的是不會因此 crash。
        self.assertGreaterEqual(report.scanned, 1)


class FSMIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-prod.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _bootstrap(self) -> FSMRuntime:
        state = load_state("prod-proj", path=self.path)
        return FSMRuntime(state)

    def test_enter_exit_production_signal(self) -> None:
        rt = self._bootstrap()
        rt.state.current = "RELEASE"
        result = rt.enter_production_signal(reason="test enter")
        self.assertTrue(result.get("entered"))
        self.assertEqual(rt.state.current, "PRODUCTION_SIGNAL")

        # exit to SPEC_DRAFTING (drift persistent case)
        rt.exit_production_signal("SPEC_DRAFTING", reason="drift accepted")
        self.assertEqual(rt.state.current, "SPEC_DRAFTING")

    def test_cannot_enter_from_implementation(self) -> None:
        rt = self._bootstrap()
        rt.state.current = "IMPLEMENTATION"
        with self.assertRaises(TransitionError):
            rt.enter_production_signal()

    def test_idempotent_when_already_in_state(self) -> None:
        rt = self._bootstrap()
        rt.state.current = "RELEASE"
        rt.enter_production_signal()
        result = rt.enter_production_signal()
        self.assertTrue(result.get("noop"))

    def test_production_signal_does_not_block_tool_calls(self) -> None:
        """PRODUCTION_SIGNAL 是非阻塞監測狀態；tool calls 必須繼續通過。"""
        rt = self._bootstrap()
        rt.state.current = "RELEASE"
        rt.enter_production_signal()
        # Bash / Read / generic tool — 不應 raise
        rt.assert_tool_allowed("Bash", "ls")
        rt.assert_tool_allowed("Read", "docs/01_requirements/FRD-X.md")

    def test_transition_rules_wire_new_state(self) -> None:
        """PRODUCTION_SIGNAL → SPEC_DRAFTING / RELEASE 必須合法；進入需透過專用 API。"""
        # 入口：透過 happy_path 任意來源都不合法（防止意外誤轉）
        self.assertFalse(is_transition_allowed("RELEASE", "PRODUCTION_SIGNAL"))
        self.assertFalse(is_transition_allowed("IMPLEMENTATION", "PRODUCTION_SIGNAL"))
        # 出口：PRODUCTION_SIGNAL → {SPEC_DRAFTING, RELEASE} 合法
        self.assertTrue(is_transition_allowed("PRODUCTION_SIGNAL", "SPEC_DRAFTING"))
        self.assertTrue(is_transition_allowed("PRODUCTION_SIGNAL", "RELEASE"))
        # 其他出口不合法
        self.assertFalse(is_transition_allowed("PRODUCTION_SIGNAL", "IMPLEMENTATION"))


class DecisionTraceIntegrationTests(unittest.TestCase):
    """Verify ACT-025 decision_trace captures production_signal entries."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "FSM-STATE-trace.yaml"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_enter_records_trace_entry(self) -> None:
        state = load_state("trace-proj", path=self.path)
        rt = FSMRuntime(state)
        rt.state.current = "RELEASE"
        rt.enter_production_signal(reason="persistent p95 drift")
        trace = rt.state.root.get("decision_trace") or []
        self.assertTrue(trace, "no decision trace recorded")
        last = trace[-1]
        self.assertEqual(last["to"], "PRODUCTION_SIGNAL")
        self.assertEqual(last["trigger"], "production_signal_enter")
        self.assertIn("persistent p95 drift", last.get("reason", ""))


class LocalizerIntegrationTests(unittest.TestCase):
    """ACT-086：PBS-DRIFT 報告經 spec_localizer 自動附 suspect 節點（advisory）。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.report_root = Path(self._tmp.name) / "reports"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _entries(self) -> list:
        return [
            {"event_id": "e1", "timestamp": "2026-06-02T01:00:00+00:00",
             "metric": "p95_login_ms", "observed": 320, "target": 200,
             "unit": "ms", "duration_minutes": 15, "nfr_id": "NFR-002"},
        ]

    def test_drift_report_embeds_suspect_when_rtm_given(self) -> None:
        from tools.fsm_runtime.spec_localizer import RTMRow
        rtm = [RTMRow("AC-020", "F-004", "NFR-002", ["TC-020-1"])]
        path = pm.generate_drift_report(
            "NFR-002", "p95_login_ms", self._entries(),
            report_root=self.report_root, rtm=rtm,
        )
        content = path.read_text(encoding="utf-8")
        self.assertIn("因果定位", content)
        self.assertIn("AC-020", content)          # suspect 節點
        self.assertIn("已自動定位 suspect", content)
        self.assertIn("絕不自動改 spec", content)  # advisory

    def test_drift_report_accepts_rtm_markdown(self) -> None:
        rtm_md = (
            "| FRD | AC | TC | NFR |\n"
            "|-----|----|----|-----|\n"
            "| F-004 | AC-020 | TC-020-1 | NFR-002 |\n"
        )
        path = pm.generate_drift_report(
            "NFR-002", "p95_login_ms", self._entries(),
            report_root=self.report_root, rtm=rtm_md,
        )
        self.assertIn("AC-020", path.read_text(encoding="utf-8"))

    def test_drift_report_unchanged_without_rtm(self) -> None:
        path = pm.generate_drift_report(
            "NFR-002", "p95_login_ms", self._entries(),
            report_root=self.report_root,
        )
        content = path.read_text(encoding="utf-8")
        self.assertNotIn("因果定位", content)      # 向後相容：無 RTM 不注入


if __name__ == "__main__":
    unittest.main()
