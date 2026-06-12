"""SD_Improving_09 W0 / P0-04 / QA Minor #1：propagate_to_subprocess_env 邊界測試。

涵蓋（≥ 3 case，對應 ADR-SD09-004 §3.1 W3C TraceContext 過渡實作）：
  1. trace_id 已設定時注入 AUTOCLAUDE_TRACE_ID
  2. trace_id 未設定（None）時不污染 env（既有 key 不變、不新增 AUTOCLAUDE_TRACE_ID）
  3. env=None 預設拷貝 os.environ；env=dict 走顯式 input
  4. 不破壞 caller env dict（pure function）
  5. 巢狀 with_trace_id() 取最內層 tid（ContextVar 還原語意）

對應：ADR-SD09-004 §3.1 / SD09_Pre_W0_Audit_Findings.md P0-04 / M-04。
"""
from __future__ import annotations

import os

from autoclaude.utils.trace_context import (
    from_traceparent_header,
    propagate_to_subprocess_env,
    to_traceparent_header,
    with_trace_id,
)


# ──────────────────────────────────────────────────────────────
# Case 1：trace_id 已設定 → 注入 AUTOCLAUDE_TRACE_ID
# ──────────────────────────────────────────────────────────────
def test_propagate_injects_trace_id_when_set():
    base_env = {"PATH": "/usr/bin", "HOME": "/home/test"}
    with with_trace_id("test_tid_001"):
        result = propagate_to_subprocess_env(base_env)
    assert result["AUTOCLAUDE_TRACE_ID"] == "test_tid_001"
    assert result["PATH"] == "/usr/bin"
    assert result["HOME"] == "/home/test"


# ──────────────────────────────────────────────────────────────
# Case 2：trace_id 未設定 → env 不被污染
# ──────────────────────────────────────────────────────────────
def test_propagate_no_op_when_trace_id_unset():
    base_env = {"PATH": "/usr/bin", "EXISTING_KEY": "value"}
    result = propagate_to_subprocess_env(base_env)
    assert "AUTOCLAUDE_TRACE_ID" not in result
    assert result["PATH"] == "/usr/bin"
    assert result["EXISTING_KEY"] == "value"


# ──────────────────────────────────────────────────────────────
# Case 3：env=None 預設拷貝 os.environ，且 caller dict 不被改動
# ──────────────────────────────────────────────────────────────
def test_propagate_default_env_is_os_environ_copy():
    with with_trace_id("test_tid_002"):
        result = propagate_to_subprocess_env(env=None)
    assert result["AUTOCLAUDE_TRACE_ID"] == "test_tid_002"
    # os.environ 中既有 key 都被拷貝（PATH 在所有平台都存在）
    assert "PATH" in result or "Path" in result  # Windows 為 Path
    # 副作用檢查：os.environ 本身不被污染
    assert "AUTOCLAUDE_TRACE_ID" not in os.environ


# ──────────────────────────────────────────────────────────────
# Case 4：pure function — caller env dict 不被 mutate
# ──────────────────────────────────────────────────────────────
def test_propagate_does_not_mutate_caller_env():
    base_env = {"K1": "v1", "K2": "v2"}
    snapshot_before = dict(base_env)
    with with_trace_id("test_tid_003"):
        result = propagate_to_subprocess_env(base_env)
    # caller dict 完全不變
    assert base_env == snapshot_before
    # 但 result 是新 dict（含注入結果）
    assert result is not base_env
    assert result["AUTOCLAUDE_TRACE_ID"] == "test_tid_003"


# ──────────────────────────────────────────────────────────────
# Case 5：巢狀 with_trace_id() — 取最內層 tid（ContextVar 還原語意）
# ──────────────────────────────────────────────────────────────
def test_propagate_nested_with_trace_id_takes_innermost():
    with with_trace_id("outer"):
        result_outer = propagate_to_subprocess_env({})
        assert result_outer["AUTOCLAUDE_TRACE_ID"] == "outer"
        with with_trace_id("inner"):
            result_inner = propagate_to_subprocess_env({})
            assert result_inner["AUTOCLAUDE_TRACE_ID"] == "inner"
        # inner 退出後恢復 outer
        result_after_inner = propagate_to_subprocess_env({})
        assert result_after_inner["AUTOCLAUDE_TRACE_ID"] == "outer"


# ──────────────────────────────────────────────────────────────
# SD_09 W3 T3-F1b（ADR-SD09-004 §2.3 W3C TraceContext path-b 落地）
# ──────────────────────────────────────────────────────────────
def test_propagate_writes_traceparent_when_trace_id_set():
    """trace_id 已設定 → 同時注入 TRACEPARENT 與 AUTOCLAUDE_TRACE_ID。"""
    base_env: dict[str, str] = {}
    with with_trace_id("test_tid_w3c_01"):
        result = propagate_to_subprocess_env(base_env)
    assert "TRACEPARENT" in result, "W3C TRACEPARENT 必須注入"
    assert "AUTOCLAUDE_TRACE_ID" in result, "向下相容 key 必須保留"
    # W3C 格式校驗
    parts = result["TRACEPARENT"].split("-")
    assert len(parts) == 4
    assert parts[0] == "00"
    assert len(parts[1]) == 32  # trace-id 32 hex
    assert len(parts[2]) == 16  # span-id 16 hex
    assert len(parts[3]) == 2   # flags 2 hex


def test_propagate_no_traceparent_when_trace_id_unset():
    """trace_id 未設定 → TRACEPARENT 不被注入。"""
    base_env: dict[str, str] = {"K": "v"}
    result = propagate_to_subprocess_env(base_env)
    assert "TRACEPARENT" not in result


def test_propagate_respects_existing_traceparent():
    """caller env 已有 TRACEPARENT → 不覆蓋（W3C distributed tracing semantics）。"""
    existing = "00-deadbeefdeadbeefdeadbeefdeadbeef-cafebabecafebabe-01"
    base_env: dict[str, str] = {"TRACEPARENT": existing}
    with with_trace_id("would_overwrite"):
        result = propagate_to_subprocess_env(base_env)
    assert result["TRACEPARENT"] == existing, "caller 已設不可覆蓋"
    # 但 AUTOCLAUDE_TRACE_ID 仍以 contextvar 值寫入（路徑 a 兼容）
    assert result["AUTOCLAUDE_TRACE_ID"] == "would_overwrite"


# ──────────────────────────────────────────────────────────────
# to_traceparent_header / from_traceparent_header round-trip
# ──────────────────────────────────────────────────────────────
def test_to_traceparent_header_format_is_w3c_compliant():
    """to_traceparent_header 輸出符合 W3C 格式（`<v>-<32hex>-<16hex>-<2hex>`）。"""
    header = to_traceparent_header("abc123def456")
    parts = header.split("-")
    assert parts[0] == "00"
    assert len(parts[1]) == 32
    assert len(parts[2]) == 16
    assert parts[3] == "01"
    # 短 trace_id 左補 0
    assert parts[1].endswith("abc123def456")


def test_to_traceparent_header_truncates_long_input():
    """過長 trace_id → 截斷至 32 chars。"""
    long_tid = "a" * 100
    header = to_traceparent_header(long_tid)
    assert len(header.split("-")[1]) == 32


def test_from_traceparent_header_roundtrip():
    """組裝後可解析回原 trace_id。"""
    original_tid = "abc123def456"
    header = to_traceparent_header(original_tid)
    parsed = from_traceparent_header(header)
    assert parsed is not None
    # 解析回的是 32 hex（左補 0 後 normalized）
    assert parsed.endswith("abc123def456")
    assert len(parsed) == 32


def test_from_traceparent_header_rejects_malformed():
    """格式不符 → 回 None（不丟例外）。"""
    # 段數錯誤
    assert from_traceparent_header("00-abc") is None
    # version 錯誤
    assert from_traceparent_header("99-" + "a" * 32 + "-" + "b" * 16 + "-01") is None
    # trace-id 非 hex
    assert from_traceparent_header("00-" + "z" * 32 + "-" + "b" * 16 + "-01") is None
    # 空字串
    assert from_traceparent_header("") is None


def test_from_traceparent_header_accepts_valid_input():
    """合法 W3C header → 正確解析。"""
    valid = "00-deadbeefdeadbeefdeadbeefdeadbeef-cafebabecafebabe-01"
    parsed = from_traceparent_header(valid)
    assert parsed == "deadbeefdeadbeefdeadbeefdeadbeef"
