"""SD_09 W3 Round 9 audit P2-R9-1 修復測試（紀律 #4 / #10 fallback 取證可區分）。

對應 tools/ac4_nightly_alert_parser.py — ps1 line 415-441 F2 區塊 4 條分支單元測試覆蓋。
Round 9 audit 指出 ps1 F2 邏輯複雜（stderr/JSON 拆分 + ready_for_labeled_pr 判定 +
exception 捕捉）但無對應 ps1 端單元測試；本 helper 提供同構樣板 + 4 條分支單元測試。
"""

from __future__ import annotations

import json

import pytest

from tools.ac4_nightly_alert_parser import parse, split_stdout_stderr

# ---------------------------------------------------------------------------
# split_stdout_stderr — JSON 起點偵測 + stderr 攔截
# ---------------------------------------------------------------------------


def test_split_pure_json_no_stderr() -> None:
    raw = '{"status": "observing", "ready_for_labeled_pr": false}\n'
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert stderr_lines == []
    assert "".join(json_lines).strip().startswith("{")


def test_split_stderr_warning_before_json() -> None:
    raw = (
        "[ac4_progress_check] WARN: dropped 2 records with unparseable timestamp\n"
        '{"status": "observing"}\n'
    )
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert len(stderr_lines) == 1
    assert "dropped 2 records" in stderr_lines[0]
    assert "".join(json_lines).strip().startswith("{")


def test_split_multi_line_stderr_then_json_dict() -> None:
    """多行 stderr warning（含 `[xxx]` 字面）後接 dict JSON — ac4_progress_check 永遠回 dict"""
    raw = (
        "[ac4_progress_check] WARN line 1\n"
        "[ac4_progress_check] WARN line 2\n"
        "\n"
        '{"k": "v"}\n'
    )
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert stderr_lines == [
        "[ac4_progress_check] WARN line 1",
        "[ac4_progress_check] WARN line 2",
    ]
    assert "".join(json_lines).strip().startswith("{")


def test_split_bracket_warning_not_misidentified_as_json_array() -> None:
    """ps1 stderr warning 常以 `[ac4_progress_check] WARN:` 開頭 → 不應誤判為 JSON array 起點"""
    raw = "[ac4_progress_check] WARN: just a stderr line\n"
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert stderr_lines == ["[ac4_progress_check] WARN: just a stderr line"]
    assert json_lines == []


def test_split_empty_lines_before_json_are_skipped() -> None:
    raw = '\n\n\n{"k": "v"}\n'
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert stderr_lines == []
    assert "".join(json_lines).strip() == '{"k": "v"}'


# ---------------------------------------------------------------------------
# parse — 4 條分支 (OK / ALERT / WARN / OK + stderr 並存)
# ---------------------------------------------------------------------------


def test_parse_f2_ok_observing_without_stderr() -> None:
    """F2 OK：ready_for_labeled_pr=False（觀察期累計中）。

    SD_09 W3 Round 12 P0-R12-1（ADR-SD09-008 v0.4 ACCEPTED 拍板實作落地）：
    message 已改用 tolerant<60ms streak + observation<50ms streak 雙欄位。
    """
    raw = json.dumps(
        {
            "status": "observing",
            "observation_days": 4,
            "tolerant_streak": 0,
            "observation_streak": 0,
            "green_streak": 0,
            "ready_for_labeled_pr": False,
            "reasons": ["連續全綠不足（0/14 天）"],
        },
        ensure_ascii=False,
    )
    decision = parse(raw)
    assert decision.level == "OK"
    assert "觀察期 #2 累計中" in decision.log_message
    assert "status=observing" in decision.log_message
    assert "tolerant<60ms streak=0" in decision.log_message
    assert "observation<50ms streak=0" in decision.log_message
    assert "days=4" in decision.log_message
    assert "連續全綠不足" in decision.log_message
    assert decision.stderr_lines == ()
    assert decision.parsed_json is not None
    assert decision.parsed_json["ready_for_labeled_pr"] is False


def test_parse_f2_alert_ready_for_labeled_pr() -> None:
    """F2 ALERT：ready_for_labeled_pr=True（需 PM 確認）。

    Round 12：message 改 tolerant + observation 雙 streak 欄位 + ADR v0.4 ACCEPTED 引用。
    """
    raw = json.dumps(
        {
            "status": "ready",
            "observation_days": 14,
            "tolerant_streak": 14,
            "observation_streak": 0,
            "green_streak": 14,
            "ready_for_labeled_pr": True,
            "reasons": [],
        }
    )
    decision = parse(raw)
    assert decision.level == "ALERT"
    assert "已達標" in decision.log_message
    assert "ready_for_labeled_pr=true" in decision.log_message
    assert "tolerant<60ms streak=14/14" in decision.log_message
    assert "observation<50ms streak=0/14" in decision.log_message
    assert "ADR-SD09-008 v0.4 ACCEPTED" in decision.log_message
    assert "需 PM 確認" in decision.log_message
    assert "SD09_AC4_Activation_Approval.md" in decision.log_message
    assert decision.parsed_json is not None
    assert decision.parsed_json["ready_for_labeled_pr"] is True


def test_parse_f2_ok_with_stderr_warning_interleaved() -> None:
    """F2 OK + F2 stderr 並存：stderr warning 應同步寫入 nightly_latest.log。

    Round 12：fallback 路徑（缺 tolerant_streak）→ 使用 green_streak。
    """
    raw = (
        "[ac4_progress_check] WARN: dropped 1 records with unparseable timestamp\n"
        + json.dumps({"status": "observing", "ready_for_labeled_pr": False, "green_streak": 2})
        + "\n"
    )
    decision = parse(raw)
    assert decision.level == "OK"
    assert decision.stderr_lines == (
        "[ac4_progress_check] WARN: dropped 1 records with unparseable timestamp",
    )
    assert "status=observing" in decision.log_message
    # 向下相容 fallback：缺 tolerant_streak 時用 green_streak（=2）
    assert "tolerant<60ms streak=2" in decision.log_message


def test_parse_f2_warn_json_decode_error() -> None:
    """F2 WARN：JSON 解析失敗 — ConvertFrom-Json 對應 PS try/catch"""
    raw = "this is not json at all\n"
    decision = parse(raw)
    assert decision.level == "WARN"
    assert "AC4 readiness 解析失敗" in decision.log_message
    assert decision.parsed_json is None


def test_parse_f2_warn_empty_output() -> None:
    """F2 WARN：完全空輸出（ac4_progress_check 異常 silent exit）"""
    decision = parse("")
    assert decision.level == "WARN"
    assert "empty JSON output" in decision.log_message
    assert decision.parsed_json is None


def test_parse_f2_warn_malformed_json_with_stderr() -> None:
    """F2 WARN + stderr：JSON 起點之前有 stderr，JSON 本身壞掉"""
    raw = "WARN: malformed run\n{not valid json}\n"
    decision = parse(raw)
    assert decision.level == "WARN"
    assert "JSONDecodeError" in decision.log_message or "ValueError" in decision.log_message
    assert decision.stderr_lines == ("WARN: malformed run",)
    assert decision.parsed_json is None


def test_parse_f2_warn_top_level_array_rejected() -> None:
    """F2 WARN：top-level 非 dict（`{...}` 包裹 array → 仍是 dict-shaped JSON 但值為 list）

    註：JSON 起點偵測只認 `{` → top-level array `[1,2,3]` 不會被視為 JSON 起點，
    而會被 stderr 攔截 → 解析空 JSON → empty JSON output WARN。
    本案改為「dict-shaped 但 value 為非預期型別」場景：解析成功但 ready 為非 bool 仍 OK。
    """
    raw = "[1, 2, 3]\n"  # 不會被偵測為 JSON
    decision = parse(raw)
    assert decision.level == "WARN"
    assert "empty JSON output" in decision.log_message
    assert decision.parsed_json is None


def test_parse_f2_ok_with_non_list_reasons_fallback() -> None:
    """F2 OK：reasons 為字串而非 list 時應 fallback 為單元素 list（向下相容）"""
    raw = json.dumps(
        {
            "status": "observing",
            "ready_for_labeled_pr": False,
            "reasons": "single string reason",
        }
    )
    decision = parse(raw)
    assert decision.level == "OK"
    assert "reasons=single string reason" in decision.log_message


def test_parse_real_nightly_122635_output_legacy_schema() -> None:
    """以真實 nightly_2026-05-25_122635.log line 199-201 的 ac4_progress_check 輸出回歸測試。

    Round 12：原 schema 含 tolerant_streak=None（向下相容 fallback 應用 green_streak）；
    且 reasons 為舊 PROPOSED 文案 — 對應的是 Round 11 之前的歷史紀錄；helper 應原樣傳遞。
    """
    raw = json.dumps(
        {
            "status": "observing",
            "observation_days": 4,
            "green_streak": 0,
            "strict_streak": 0,
            "tolerant_streak": None,
            "tolerant_p95_ms": None,
            "consecutive_failures": 0,
            "recall_sigma": 0.0,
            "ready_for_labeled_pr": False,
            "reasons": [
                "p95 卡嚴格門檻 50ms~60ms neutral 區（60ms = P95_MAX_MS × 1.2 內部 neutral buffer，非 ADR-SD09-008 PROPOSED tolerant 軌拍板門檻；雙軌設計觀察等待，非 X1 阻塞；需採集寬鬆→升級嚴格分軌持續累積）"  # noqa: E501  # 逐字保全 nightly 真實輸出，斷行會失去對照價值
            ],
        },
        ensure_ascii=False,
    )
    decision = parse(raw)
    assert decision.level == "OK"
    # tolerant_streak=None → fallback 使用本層 None；缺 observation_streak → 0
    assert "tolerant<60ms streak=None" in decision.log_message
    assert "observation<50ms streak=0" in decision.log_message
    assert "days=4" in decision.log_message
    # P1-NEW-2 歷史 reasons 應原樣傳遞至 log（向下相容讀舊紀錄）
    assert "P95_MAX_MS × 1.2 內部 neutral buffer" in decision.log_message
    assert "非 ADR-SD09-008 PROPOSED tolerant 軌拍板門檻" in decision.log_message


def test_parse_round12_real_nightly_v03_accepted_schema() -> None:
    """Round 12 新增：v0.4 ACCEPTED 拍板後新 schema 真實 nightly 輸出回歸測試。

    對應 ADR-SD09-008 v0.4 ACCEPTED schema：含 tolerant_streak + observation_streak
    + observation_p95_ms 欄位。
    """
    raw = json.dumps(
        {
            "status": "observing",
            "observation_days": 4,
            "green_streak": 4,
            "tolerant_streak": 4,
            "observation_streak": 0,
            "strict_streak": 4,
            "tolerant_p95_ms": 60.0,
            "observation_p95_ms": 50.0,
            "consecutive_failures": 0,
            "recall_sigma": 0.0,
            "ready_for_labeled_pr": False,
            "reasons": ["觀察期未滿（4/14 天）"],
        },
        ensure_ascii=False,
    )
    decision = parse(raw)
    assert decision.level == "OK"
    assert "tolerant<60ms streak=4" in decision.log_message
    assert "observation<50ms streak=0" in decision.log_message
    assert "days=4" in decision.log_message
    assert "觀察期未滿" in decision.log_message


# ---------------------------------------------------------------------------
# AlertDecision dataclass 結構保證（immutable + 4 必填欄位）
# ---------------------------------------------------------------------------


def test_alert_decision_is_frozen_dataclass() -> None:
    decision = parse('{"ready_for_labeled_pr": false}')
    with pytest.raises((AttributeError, Exception)):
        decision.level = "ALERT"  # type: ignore[misc]


def test_alert_decision_stderr_lines_is_tuple_not_list() -> None:
    """stderr_lines 必須是 tuple（immutable）— 防 caller 意外修改影響其他 caller"""
    decision = parse('WARN line\n{"ready_for_labeled_pr": false}')
    assert isinstance(decision.stderr_lines, tuple)


# ---------------------------------------------------------------------------
# P2-R10-1 配套：ps1 與 helper SSOT 同構嚴格對齊 — 拒絕 `[` 為 JSON 起點
# ---------------------------------------------------------------------------


def test_ps1_helper_alignment_legitimate_json_array_treated_as_stderr() -> None:
    """P2-R10-1 修復配套：即使是合法 JSON array `[1, 2, 3]`，也應被視為 stderr
    而非 JSON 起點。理由：ac4_progress_check.py --json 永遠回 dict，且 stderr warning
    常以 `[ac4_progress_check] WARN:` 開頭。helper 與 ps1 必須一致拒絕 `[` 起點。
    """
    json_lines, stderr_lines = split_stdout_stderr("[1, 2, 3]\n")
    assert json_lines == []
    assert stderr_lines == ["[1, 2, 3]"]


def test_stderr_after_complete_json_does_not_break_parsing() -> None:
    """🔴 R73 回歸鎖（DEF-101-783）：JSON **之後**的 stderr 行不得毀掉解析。

    意圖（Rule 9）：本鎖存在的理由不是「JSON 要能解析」，而是**方向**——舊實作
    「JSON 起點之後的所有行都收」會把尾隨的 `[ac4_progress_check] WARN:` 接進
    json_lines，`json.loads` 拋 `Extra data` ⇒ 判 F2 WARN（解析失敗），而真值是
    F2 ALERT（**已達標**）。真達標被讀成「量不出來」，與 ps1 側 DEF-101-775
    完全同型；本檔是那條缺陷的 SSOT 鏡像，R73 首版只修了 ps1 側。

    第二個斷言同樣重要：那行 WARN 必須**還在 stderr_lines 裡**。舊實作把它吞進
    json_lines ⇒ `stderr_lines=()` ⇒ 連取證都掉了（Architect 二審實測），
    而 ps1 側修法特意保住了 `[F2 stderr]` 記錄能力。取證不得因修 bug 而縮水。
    """
    raw = '{"ready_for_labeled_pr": true, "status": "green"}\n[ac4_progress_check] WARN: legacy\n'
    decision = parse(raw)
    assert decision.level == "ALERT", f"真值為 ready 卻被讀成 {decision.level}：{decision}"
    assert decision.parsed_json is not None
    assert decision.parsed_json["ready_for_labeled_pr"] is True
    assert decision.stderr_lines == ("[ac4_progress_check] WARN: legacy",), (
        f"尾隨的 stderr 行必須仍被攔截記錄，不得被吞進 JSON：{decision.stderr_lines}"
    )


def test_truncated_json_still_fails_closed() -> None:
    """fail-closed：JSON 起了頭卻永遠解析不完 ⇒ 判 F2 WARN，絕不可猜成 OK/ALERT。

    意圖（Rule 9）：R73 把「收到所有行」改為「解析成功即停」，必須確認這個改動
    **沒有**把「輸出被截斷」誤判成某個確定結論——截斷代表工具壞了，唯一安全的
    答案是「量不出來」。
    """
    decision = parse('{"ready_for_labeled_pr": true,\n')
    assert decision.level == "WARN", f"截斷的 JSON 必須判解析失敗：{decision}"
    assert decision.parsed_json is None


def test_ps1_helper_alignment_bracket_at_end_after_json_is_kept_as_json() -> None:
    """P2-R10-1 修復配套：一旦 JSON 起點（`{`）已被偵測，後續以 `[` 開頭的行
    應被視為 JSON 內容（如 multi-line JSON 內含 array），不再進 stderr。
    對應 ps1 F2 區塊的 `$ac4JsonLines.Count -gt 0` 條件。
    🔴 R73（DEF-101-783）：「JSON started 後**全收**」已改為「解析成功即停」，
    本 case 的 multi-line JSON 因此仍全數被收（頂層 `{` 閉合前任何前綴都不合法，
    不可能提早停在半截物件上）——行為不變，故本 case 原樣保留為對照組。
    """
    raw = '{"reasons":\n[\n"a",\n"b"\n]\n}\n'
    json_lines, stderr_lines = split_stdout_stderr(raw)
    assert stderr_lines == []
    assert any("[" in line for line in json_lines)
    parsed = parse(raw)
    assert parsed.level == "OK"  # ready_for_labeled_pr 預設 False
    assert parsed.parsed_json is not None
    assert parsed.parsed_json["reasons"] == ["a", "b"]
