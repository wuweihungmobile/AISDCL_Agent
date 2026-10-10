"""F-LRS-001：`python -m autoclaude --last-run-summary` 驗收測試。

對應規格 docs/01_requirements/FRD_Last_Run_Summary.md §4.2 RTM；每條 AC 至少一支測試，
測試函式名以 `test_ac_lrs_<編號>_` 起頭。四個層次：
  * 純函式：format_summary／build_*_record／summary_problems／outcome_of
  * recorder：RunSummaryRecorder（直接餵可注入時鐘）
  * in-process main()：stub 掉 executor／AutoResumeService／開機自檢，其餘走真 parser、真接線
  * subprocess：`python -m autoclaude …`（真 argv、真 rc、真 stdout／stderr）
檔案副作用一律落 tmp_path，不寫進 AutoClaude/ 樹內。
"""
from __future__ import annotations

import contextlib
import json
import logging
import os
import subprocess
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from autoclaude import main as main_mod
from autoclaude.core.kernel_state import KernelResult
from autoclaude.execution import run_summary as rs

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TZ8 = timezone(timedelta(hours=8))
PLAYBOOK = "/work/proj/scripts/example_playbook.yaml"
STARTED_UTC = "2026-10-10T10:11:07+00:00"      # 在 UTC+8 顯示為 2026-10-10 18:11:07+08:00
FINISHED_UTC = "2026-10-10T10:11:10+00:00"
RESUME_UTC = "2026-10-10T15:40:00+00:00"       # 在 UTC+8 顯示為 2026-10-10 23:40:00+08:00

SCHEMA_KEYS = [
    "schema_version", "status", "playbook", "started_at", "finished_at", "duration_seconds",
    "outcome", "success", "escalated", "halted", "reason", "total_steps", "completed_steps",
    "halt_step_idx", "peak_token_pct", "scheduled_resume_at", "veto_reasons",
]


# ──────────────────────────────────────────────────────────────────────────
# 共用輔助
# ──────────────────────────────────────────────────────────────────────────
def _started(started_at: str = STARTED_UTC, playbook: str = PLAYBOOK) -> dict:
    return rs.build_started_record(playbook, started_at)


def _finished(
    result: KernelResult | None = None, *, started_at: str = STARTED_UTC,
    finished_at: str = FINISHED_UTC, duration: float = 3.2, **over,
) -> dict:
    """以 builder 組出合法 finished 記錄，再以 `over` 覆寫個別欄位（損毀案例用）。"""
    result = result or KernelResult.success_(3, 3, [], [], [], peak_token_pct=41.5)
    record = rs.build_finished_record(_started(started_at), result, finished_at, duration)
    record.update(over)
    return record


def _put(log_dir: Path, record_or_text: dict | str) -> Path:
    """把記錄（或原始字串，供損毀案例）寫成 log_dir 內的 last_run_summary.json。"""
    log_dir.mkdir(parents=True, exist_ok=True)
    text = (record_or_text if isinstance(record_or_text, str)
            else json.dumps(record_or_text, ensure_ascii=False, indent=2) + "\n")
    path = log_dir / rs.SUMMARY_FILENAME
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _read(log_dir: Path) -> dict:
    return json.loads((log_dir / rs.SUMMARY_FILENAME).read_text(encoding="utf-8"))


class _Clock:
    """依序吐出預先給定的值；用盡後重複最後一個。"""

    def __init__(self, *values):
        self._values = list(values)

    def __call__(self):
        return self._values.pop(0) if len(self._values) > 1 else self._values[0]


def _utc(text: str) -> datetime:
    return datetime.fromisoformat(text)


def _tmp_files(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir() if ".tmp" in p.name)


# json.loads 有兩種失敗不是 JSONDecodeError：超過位數上限的整數（純 ValueError）、極深巢狀
# （RecursionError）。兩者都必須被讀取端收成「損毀」而不是 traceback。
_OVERSIZED_INT_RECORD = '{"schema_version": ' + "9" * 5000 + "}"
_DEEPLY_NESTED_JSON = "[" * 200_000
_PATHOLOGICAL_JSON = [
    pytest.param(_OVERSIZED_INT_RECORD, id="integer_over_the_digit_limit"),
    pytest.param(_DEEPLY_NESTED_JSON, id="nesting_deep_enough_for_recursion_error"),
]


@contextlib.contextmanager
def _int_digit_limit(limit: int = 4300):
    """釘住「整數字串轉換位數上限」：環境以 PYTHONINTMAXSTRDIGITS 調過時，測試不得跟著漂。"""
    previous = sys.get_int_max_str_digits()
    sys.set_int_max_str_digits(limit)
    try:
        yield
    finally:
        sys.set_int_max_str_digits(previous)


# ══════════════════════════════════════════════════════════════════════════
# 步驟 1：落檔側（純函式 builder ＋ recorder）
# ══════════════════════════════════════════════════════════════════════════
_HALTED = KernelResult.halted_(1, 3, [], [], halt_step_idx=1, peak_token_pct=95.0)
_OUTCOME_SHAPES = [
    pytest.param(KernelResult.success_(3, 3, [], [], []), "success", id="success_"),
    pytest.param(KernelResult.escalated_(1, 3, [], [], "boom"), "escalation", id="escalated_"),
    pytest.param(_HALTED, "token_halt", id="halted_"),
    pytest.param(KernelResult.vetoed(3, ["SDD 規格指紋不符"]), "failed", id="vetoed"),
    # AutoResumeService 衍生形態一：halt 後拒絕行程內長睡（replace 沿用 halted 的欄位）
    pytest.param(
        replace(_HALTED, reason="external_resume_required", scheduled_resume_at=RESUME_UTC),
        "token_halt", id="derived_external_resume_required"),
    # 衍生形態二：checkpoint 續跑路徑等待中被中斷（halted_ 空殼＋replace 補 halt_step_idx）
    pytest.param(
        replace(KernelResult.halted_(2, 3, [], []), reason="interrupted_during_wait",
                scheduled_resume_at=RESUME_UTC, halt_step_idx=2),
        "token_halt", id="derived_interrupted_during_wait"),
]


@pytest.mark.parametrize(("result", "outcome"), _OUTCOME_SHAPES)
def test_ac_lrs_020_outcome_mapping_for_every_kernel_result_shape(result, outcome):
    """AC-LRS-020：四種 KernelResult 形態＋兩種衍生形態的 outcome 映射與欄位保留。"""
    assert rs.outcome_of(result) == outcome
    record = rs.build_finished_record(_started(), result, FINISHED_UTC, 3.24)
    assert record["outcome"] == outcome
    assert record["success"] is result.success
    assert record["escalated"] is result.escalated
    assert record["halted"] is result.halted
    assert record["halt_step_idx"] == result.halt_step_idx
    assert record["scheduled_resume_at"] == result.scheduled_resume_at
    assert record["veto_reasons"] == list(result.veto_reasons)
    assert record["total_steps"] == result.total_steps
    assert record["completed_steps"] == result.completed_steps
    assert record["duration_seconds"] == 3.2
    # 寫入端產出的記錄必須通過讀取端的 schema 驗證（兩端不得各說各話）
    assert rs.summary_problems(record) == []


def test_ac_lrs_020_judgement_order_is_success_escalated_halted_failed():
    """AC-LRS-020：判定順序＝success→escalated→halted→failed（旗標互相重疊時看順序）。"""
    both = replace(KernelResult.escalated_(1, 3, [], [], "x"), halted=True)
    assert rs.outcome_of(both) == "escalation"
    all_three = replace(both, success=True)
    assert rs.outcome_of(all_three) == "success"
    plain = KernelResult(success=False, completed_steps=0, total_steps=3, reason="weird")
    assert rs.outcome_of(plain) == "failed"


def test_ac_lrs_020_reason_is_single_line_and_capped():
    """AC-LRS-020：reason 單行化且 ≤500 字（超過以 `…` 收尾）；剛好 500 字不動。"""
    def reason_of(text: str) -> str:
        result = KernelResult.escalated_(1, 3, [], [], text)
        return rs.build_finished_record(_started(), result, FINISHED_UTC, 1.0)["reason"]

    assert reason_of("第一行\n第二行\r\n\t第三行   尾") == "第一行 第二行 第三行 尾"
    assert reason_of("x" * 500) == "x" * 500
    capped = reason_of("y" * 501)
    assert len(capped) == rs.REASON_MAX_CHARS == 500
    assert capped.endswith("…")
    assert capped[:-1] == "y" * 499


def test_ac_lrs_019_started_and_finished_records_share_the_full_schema_key_set():
    """AC-LRS-019（builder 層）：running 與 finished 共用 §3.2 全表的鍵，順序一致。"""
    running = _started()
    assert list(running) == SCHEMA_KEYS
    assert running["schema_version"] == 1
    assert running["status"] == "running"
    unknown = [k for k in SCHEMA_KEYS if k not in ("schema_version", "status", "playbook",
                                                   "started_at", "veto_reasons")]
    assert all(running[k] is None for k in unknown)
    assert running["veto_reasons"] == []
    done = _finished()
    assert list(done) == SCHEMA_KEYS
    assert done["status"] == "finished"
    assert done["playbook"] == PLAYBOOK and done["started_at"] == STARTED_UTC
    # builder 不得改動傳入的 started（recorder 會重複使用同一份）
    base = _started()
    rs.build_finished_record(base, KernelResult.success_(1, 1, [], [], []), FINISHED_UTC, 1.0)
    assert base == _started()


def test_ac_lrs_019_aware_datetimes_are_persisted_as_utc_offset_strings():
    """AC-LRS-019／鐵律三：持久化的時刻一律 aware UTC（不得是 naive 本地時間）。"""
    local = datetime(2026, 10, 10, 18, 11, 7, tzinfo=TZ8)
    record = rs.build_started_record(PLAYBOOK, local)
    assert record["started_at"] == "2026-10-10T10:11:07+00:00"
    parsed = datetime.fromisoformat(record["started_at"])
    assert parsed.utcoffset() == timedelta(0)


def test_recorder_construction_does_no_io_and_two_phase_write_uses_injected_clocks(tmp_path):
    """AC-LRS-021（recorder 層）：建構不碰磁碟；start 寫 running、finish 覆寫成 finished。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(
        log_dir, PLAYBOOK,
        now=_Clock(_utc(STARTED_UTC), _utc(FINISHED_UTC)),
        monotonic=_Clock(100.0, 103.24))
    assert not log_dir.exists(), "建構子不得做 I/O"

    assert recorder.start() is True
    running = _read(log_dir)
    assert running["status"] == "running"
    assert running["started_at"] == STARTED_UTC
    assert running["outcome"] is None and running["finished_at"] is None

    assert recorder.finish(KernelResult.success_(3, 3, [], [], [], peak_token_pct=41.5)) is True
    done = _read(log_dir)
    assert done["status"] == "finished" and done["outcome"] == "success"
    assert done["started_at"] == STARTED_UTC and done["finished_at"] == FINISHED_UTC
    assert done["duration_seconds"] == 3.2
    assert done["peak_token_pct"] == 41.5
    assert done["playbook"] == os.path.abspath(PLAYBOOK)
    assert _tmp_files(log_dir) == []


def test_recorder_playbook_is_stored_as_an_absolute_path_without_resolving_symlinks(tmp_path):
    """§3.2：playbook 欄＝os.path.abspath(輸入)（相對路徑以建構當下的 cwd 補齊）。"""
    origin = Path.cwd()
    os.chdir(tmp_path)
    try:
        recorder = rs.RunSummaryRecorder(tmp_path / "logs", "scripts/pb.yaml")
    finally:
        os.chdir(origin)
    assert recorder.start() is True
    assert _read(tmp_path / "logs")["playbook"] == os.path.abspath(
        str(tmp_path / "scripts" / "pb.yaml"))


def test_finish_without_a_prior_start_still_writes_a_valid_record(tmp_path):
    """recorder 韌性：start 沒呼叫（或建記錄前就失敗）時，finish 補建開始標記而不是拋錯。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    assert recorder.finish(KernelResult.escalated_(1, 3, [], [], "boom")) is True
    record = _read(log_dir)
    assert record["outcome"] == "escalation" and rs.summary_problems(record) == []


def test_ac_lrs_023_recorder_swallows_a_replace_failure_and_warns(tmp_path, caplog):
    """AC-LRS-023（recorder 層，型 a）：os.replace 拋 PermissionError ⇒ 回 False、不拋、記 WARN。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    with caplog.at_level(logging.WARNING, logger="autoclaude.execution.run_summary"), \
         patch("os.replace", side_effect=PermissionError("denied")):
        assert recorder.start() is False
        assert recorder.finish(KernelResult.success_(1, 1, [], [], [])) is False
    warnings = [r for r in caplog.records
                if r.levelno == logging.WARNING and "last_run_summary" in r.getMessage()]
    assert len(warnings) == 2, "start 與 finish 各失敗一次，各記一則含 last_run_summary 的 WARNING"
    assert "將顯示過期或缺少的紀錄" in warnings[0].getMessage()
    assert "Traceback" not in caplog.text
    assert not (log_dir / rs.SUMMARY_FILENAME).exists()
    assert _tmp_files(log_dir) == []


def test_ac_lrs_023_recorder_swallows_an_fsync_failure_and_cleans_its_tmp(tmp_path):
    """AC-LRS-023／024（recorder 層，型 b）：fsync 拋 OSError（磁碟滿）時 tmp 已建立，須被清除。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    with patch("os.fsync", side_effect=OSError(28, "No space left on device")):
        assert recorder.start() is False
    assert _tmp_files(log_dir) == []
    assert not (log_dir / rs.SUMMARY_FILENAME).exists()


def test_ac_lrs_023_recorder_never_raises_even_for_a_result_missing_fields(tmp_path):
    """AC-LRS-023：result 缺欄位的測試替身也不得讓 finish 拋出；先前的 running 標記保留。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    assert recorder.start() is True
    assert recorder.finish(object()) is False       # type: ignore[arg-type]
    assert _read(log_dir)["status"] == "running"
    assert _tmp_files(log_dir) == []


def test_ac_lrs_023_a_failed_start_does_not_prevent_a_later_finish(tmp_path):
    """start 寫失敗（例如目錄暫時不可寫）不得讓 finish 無法補寫 finished。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    with patch("os.replace", side_effect=PermissionError("denied")):
        assert recorder.start() is False
    assert recorder.finish(KernelResult.success_(2, 2, [], [], [])) is True
    assert _read(log_dir)["status"] == "finished"


def test_ac_lrs_024_no_tmp_orphans_for_a_lone_surrogate_in_reason(tmp_path):
    """reason／路徑夾帶 lone surrogate（subprocess 輸出常見）不得炸成孤兒 tmp 或寫入失敗。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    assert recorder.finish(KernelResult.escalated_(1, 3, [], [], "bad\udcffbyte")) is True
    assert _read(log_dir)["reason"] == "bad?byte"
    assert _tmp_files(log_dir) == []


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SystemExit],
                         ids=["ctrl_c", "system_exit"])
def test_ac_lrs_024_an_interrupt_during_fsync_propagates_and_leaves_no_tmp(
        tmp_path, interruption):
    """AC-LRS-024：Ctrl+C／SystemExit（BaseException）落在 fsync 時 tmp 已建立。

    必須照常往外傳（recorder 只吞 Exception），且不得留下孤兒 tmp。
    """
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    with patch("os.fsync", side_effect=interruption), pytest.raises(interruption):
        recorder.start()
    assert _tmp_files(log_dir) == []
    assert not (log_dir / rs.SUMMARY_FILENAME).exists()


def test_ac_lrs_024_an_interrupt_during_finish_keeps_the_running_marker_intact(tmp_path):
    """Ctrl+C 落在 finish 的 fsync：先前寫好的 running 標記原封不動（崩潰語意＝停在 running）。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    assert recorder.start() is True
    before = (log_dir / rs.SUMMARY_FILENAME).read_bytes()
    with patch("os.fsync", side_effect=KeyboardInterrupt), pytest.raises(KeyboardInterrupt):
        recorder.finish(KernelResult.success_(1, 1, [], [], []))
    assert (log_dir / rs.SUMMARY_FILENAME).read_bytes() == before
    assert _tmp_files(log_dir) == []


def test_written_file_is_utf8_lf_json_with_a_trailing_newline(tmp_path):
    """§3.5：UTF-8、LF 行尾（無 \\r）、ensure_ascii=False（中文原樣落檔）、尾端單一換行。"""
    log_dir = tmp_path / "logs"
    recorder = rs.RunSummaryRecorder(log_dir, PLAYBOOK)
    assert recorder.finish(KernelResult.escalated_(1, 3, [], [], "輸出未符合期望")) is True
    raw = (log_dir / rs.SUMMARY_FILENAME).read_bytes()
    assert b"\r" not in raw
    assert raw.endswith(b"}\n") and not raw.endswith(b"\n\n")
    assert "輸出未符合期望".encode() in raw


def _write_cfg(base: Path, name: str = "logs") -> tuple[Path, Path]:
    """寫一份最小 config（log_dir／checkpoint_dir 指向 base 之下）；回 (cfg 路徑, log_dir)。"""
    log_dir = base / name
    cfg = base / f"config_{name}.yaml"
    cfg.write_text(
        f"log_dir: {log_dir.as_posix()}\ncheckpoint_dir: {(base / 'ckpt').as_posix()}\n",
        encoding="utf-8", newline="\n")
    return cfg, log_dir


# ──────────────────────────────────────────────────────────────────────────
# FRD §2.6 逐字範例（由 FRD 原文機械抽出，非手抄；E7 的 log 路徑隨平台，另行組裝）
# ──────────────────────────────────────────────────────────────────────────
E1_SUCCESS = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:11:07+08:00（耗時 3.2 秒）",
    "結果：成功（SUCCESS）",
    "步驟：通過 3 / 共 3 步",
    "token 峰值：41.5%",
    "ESCALATION：否",
])

E2_ESCALATION = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:15:01+08:00（耗時 1.0 秒）",
    "結果：失敗（ESCALATION）；原因：[T02] 輸出未符合期望 regex: 'OK_T02'",
    "步驟：通過 1 / 共 3 步",
    "token 峰值：未記錄（此結果型態不攜帶 token 峰值）",
    "ESCALATION：是",
])

E3_HALT_NO_RESUME = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:11:08+08:00（耗時 0.8 秒）",
    "結果：暫停（TOKEN_HALT）；context 用量達 halt 門檻，已存檢查點；停在第 2 步",
    "步驟：通過 1 / 共 3 步",
    "token 峰值：95.0%",
    "ESCALATION：否",
])

E4_HALT_EXTERNAL_RESUME = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:11:08+08:00（耗時 0.8 秒）",
    ("結果：暫停（TOKEN_HALT）；等待時間超過行程內上限，需於可續跑時刻後由外部重啟"
     "；停在第 2 步"),
    "步驟：通過 1 / 共 3 步",
    "token 峰值：95.0%",
    "ESCALATION：否",
    "可續跑時刻：2026-10-10 23:40:00+08:00",
])

E5_FAILED_VETOED = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:20:00+08:00（耗時 0.1 秒）",
    "結果：失敗（FAILED）；原因：vetoed_at_pre_run；否決原因：SDD 規格指紋不符",
    "步驟：通過 0 / 共 3 步",
    "token 峰值：未記錄（此結果型態不攜帶 token 峰值）",
    "ESCALATION：否",
])

E6_RESUMED_SUCCESS = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:28:34+08:00（耗時 0.4 秒）",
    "結果：成功（SUCCESS）",
    "步驟：通過 2 / 共 3 步（本次為續跑：其餘 1 步已於先前執行完成）",
    "token 峰值：未觀測（本次無 token 訊號）",
    "ESCALATION：否",
])

E7_RUNNING = "\n".join([
    "最近一次執行摘要",
    "Playbook：/work/proj/scripts/example_playbook.yaml",
    "開始時間：2026-10-10 18:30:00+08:00",
    ("結果：未完成（本次執行未正常結束）；可能仍在執行、被中斷（Ctrl+C／kill），或"
     "行程崩潰；詳見 "
     + os.path.join("logs", "autoclaude.log")),
])



# ══════════════════════════════════════════════════════════════════════════
# 步驟 2：讀檔側（format_summary／summary_problems／load_summary／show_last_run_summary）
# ══════════════════════════════════════════════════════════════════════════
def _render(result: KernelResult, *, started_at: str, duration: float) -> str:
    return rs.format_summary(_finished(result, started_at=started_at, duration=duration), tz=TZ8)


def _line(text: str, prefix: str) -> str:
    """取出以 prefix 起頭的唯一一行。"""
    found = [ln for ln in text.split("\n") if ln.startswith(prefix)]
    assert len(found) == 1, f"{prefix!r} 應恰出現一次，實得 {found}"
    return found[0]


def test_ac_lrs_007_success_summary_verbatim():
    """AC-LRS-007：finished／success／3 of 3／peak 41.5 ⇒ 逐字等於範例 E1。"""
    result = KernelResult.success_(3, 3, [], [], [], peak_token_pct=41.5)
    assert _render(result, started_at="2026-10-10T10:11:07+00:00", duration=3.2) == E1_SUCCESS


def test_ac_lrs_008_escalation_summary_verbatim():
    """AC-LRS-008：ESCALATION、peak 0.0 ⇒ 逐字等於範例 E2（ESCALATION：是、token 為「未記錄」）。"""
    result = KernelResult.escalated_(1, 3, [], [], "[T02] 輸出未符合期望 regex: 'OK_T02'")
    assert _render(result, started_at="2026-10-10T10:15:01+00:00", duration=1.0) == E2_ESCALATION


def test_ac_lrs_009_token_halt_verbatim_examples():
    """AC-LRS-009：範例 E3（halted、無續跑時刻）與 E4（拒絕行程內長睡、有續跑時刻）。"""
    started = "2026-10-10T10:11:08+00:00"
    assert _render(_HALTED, started_at=started, duration=0.8) == E3_HALT_NO_RESUME
    derived = replace(_HALTED, reason="external_resume_required", scheduled_resume_at=RESUME_UTC)
    assert _render(derived, started_at=started, duration=0.8) == E4_HALT_EXTERNAL_RESUME


_HALT_NOTES = {
    "halted": "context 用量達 halt 門檻，已存檢查點",
    "external_resume_required": "等待時間超過行程內上限，需於可續跑時刻後由外部重啟",
    "interrupted_during_wait": "等待期間被中斷",
    "some_future_reason": "some_future_reason",       # 其他 reason ⇒ 原字串
}


@pytest.mark.parametrize("idx", [None, 2], ids=["no_halt_idx", "halt_idx_2"])
@pytest.mark.parametrize("resume", [None, RESUME_UTC], ids=["no_resume_at", "resume_at"])
@pytest.mark.parametrize("reason", sorted(_HALT_NOTES))
def test_ac_lrs_009_token_halt_variants(reason, resume, idx):
    """AC-LRS-009：reason 對照 × 有／無 scheduled_resume_at × 有／無 halt_step_idx。"""
    result = replace(_HALTED, reason=reason, scheduled_resume_at=resume, halt_step_idx=idx)
    text = rs.format_summary(_finished(result), tz=TZ8)
    expected = f"結果：暫停（TOKEN_HALT）；{_HALT_NOTES[reason]}"
    if idx is not None:
        expected += f"；停在第 {idx + 1} 步"
    assert _line(text, "結果：") == expected
    if resume is None:
        # 注意：external_resume_required 的說明文字本身就含「可續跑時刻」四字，故判專屬行前綴
        assert "可續跑時刻：" not in text
    else:
        assert text.split("\n")[-1] == "可續跑時刻：2026-10-10 23:40:00+08:00"


def test_ac_lrs_009_resume_line_only_appears_for_token_halt():
    """AC-LRS-009 反向：非 token_halt 即使帶 scheduled_resume_at 也不印「可續跑時刻」。"""
    leaked = replace(KernelResult.escalated_(1, 3, [], [], "boom"), scheduled_resume_at=RESUME_UTC)
    assert "可續跑時刻：" not in rs.format_summary(_finished(leaked), tz=TZ8)


def test_ac_lrs_010_failed_vetoed_summary_verbatim():
    """AC-LRS-010：vetoed（reason=vetoed_at_pre_run、否決原因一項）⇒ 逐字等於範例 E5。"""
    result = KernelResult.vetoed(3, ["SDD 規格指紋不符"])
    assert _render(result, started_at="2026-10-10T10:20:00+00:00", duration=0.1) == E5_FAILED_VETOED


def test_ac_lrs_010_multiple_veto_reasons_join_with_a_fullwidth_semicolon():
    """AC-LRS-010：否決原因多項以「；」相接；無否決原因時整段「；否決原因：…」不出現。"""
    many = KernelResult.vetoed(3, ["甲", "乙"])
    assert _line(rs.format_summary(_finished(many), tz=TZ8), "結果：") == (
        "結果：失敗（FAILED）；原因：vetoed_at_pre_run；否決原因：甲；乙")
    bare = KernelResult(success=False, completed_steps=0, total_steps=3, reason="weird")
    assert _line(rs.format_summary(_finished(bare), tz=TZ8), "結果：") == (
        "結果：失敗（FAILED）；原因：weird")


_SUCCESS = KernelResult.success_(3, 3, [], [], [])


@pytest.mark.parametrize(("result", "expected"), [
    pytest.param(replace(_SUCCESS, peak_token_pct=41.5), "41.5%", id="success_peak"),
    pytest.param(replace(_HALTED, peak_token_pct=95.0), "95.0%", id="halt_peak"),
    pytest.param(_SUCCESS, "未觀測（本次無 token 訊號）", id="success_no_signal"),
    pytest.param(replace(_HALTED, peak_token_pct=0.0), "未觀測（本次無 token 訊號）",
                 id="halt_no_signal"),
    pytest.param(KernelResult.escalated_(1, 3, [], [], "x"),
                 "未記錄（此結果型態不攜帶 token 峰值）", id="escalation_not_carried"),
    pytest.param(KernelResult.vetoed(3, ["x"]),
                 "未記錄（此結果型態不攜帶 token 峰值）", id="failed_not_carried"),
])
def test_ac_lrs_011_token_peak_three_states(result, expected):
    """AC-LRS-011：peak>0 ⇒ 一位小數＋%；peak<=0 依 outcome 分「未觀測」與「未記錄」。"""
    text = rs.format_summary(_finished(result), tz=TZ8)
    assert _line(text, "token 峰值：") == f"token 峰值：{expected}"


@pytest.mark.parametrize(("completed", "total", "noted"), [
    pytest.param(2, 3, True, id="2_of_3_resumed"),
    pytest.param(3, 3, False, id="3_of_3_full"),
    pytest.param(0, 0, False, id="0_of_0_empty"),
    pytest.param(5, 4, False, id="5_of_4_goto_redo"),
])
def test_ac_lrs_012_resume_note_only_for_partial_success(completed, total, noted):
    """AC-LRS-012：只有 0<=completed<total 的 success 才附續跑註記；GOTO 重做（5/4）不附。"""
    result = KernelResult.success_(completed, total, [], [], [])
    line = _line(rs.format_summary(_finished(result), tz=TZ8), "步驟：")
    base = f"步驟：通過 {completed} / 共 {total} 步"
    if noted:
        assert line == base + f"（本次為續跑：其餘 {total - completed} 步已於先前執行完成）"
    else:
        assert line == base


def test_ac_lrs_012_resumed_success_verbatim():
    """AC-LRS-012：範例 E6（續跑後成功；peak 0.0 ⇒「未觀測」）。"""
    result = KernelResult.success_(2, 3, [], [], [])
    assert _render(result, started_at="2026-10-10T10:28:34+00:00", duration=0.4) == (
        E6_RESUMED_SUCCESS)


def test_ac_lrs_012_a_failed_run_never_gets_the_resume_note():
    """AC-LRS-012 反向：註記只屬 success；halt／escalation 的 completed<total 不附。"""
    text = rs.format_summary(_finished(_HALTED), tz=TZ8)
    assert _line(text, "步驟：") == "步驟：通過 1 / 共 3 步"


def test_ac_lrs_013_running_record_verbatim():
    """AC-LRS-013：status=running ⇒ 逐字等於範例 E7（四行，不印步驟／token／ESCALATION）。"""
    text = rs.format_summary(_started("2026-10-10T10:30:00+00:00"), tz=TZ8)
    assert text == E7_RUNNING
    assert len(text.split("\n")) == 4
    for forbidden in ("步驟：", "token 峰值：", "ESCALATION："):
        assert forbidden not in text


def test_ac_lrs_013_running_record_points_at_the_given_log_dir():
    """AC-LRS-013：「詳見」的路徑由 os.path.join(log_dir, "autoclaude.log") 組出。"""
    text = rs.format_summary(_started(), tz=TZ8, log_dir="elsewhere")
    assert text.endswith("詳見 " + os.path.join("elsewhere", "autoclaude.log"))


def test_ac_lrs_014_times_render_in_requested_timezone():
    """AC-LRS-014：偏移逐字出現且時刻換算正確；tz=None＝本機時區；耗時一位小數。"""
    record = _finished(started_at=STARTED_UTC, duration=3.2)
    assert "開始時間：2026-10-10 10:11:07+00:00（耗時 3.2 秒）" in rs.format_summary(
        record, tz=UTC)
    assert "開始時間：2026-10-10 18:11:07+08:00（耗時 3.2 秒）" in rs.format_summary(
        record, tz=TZ8)
    local = datetime.fromisoformat(STARTED_UTC).astimezone().isoformat(
        sep=" ", timespec="seconds")
    assert f"開始時間：{local}（耗時 3.2 秒）" in rs.format_summary(record)
    assert "（耗時 3.0 秒）" in rs.format_summary(_finished(duration=3), tz=TZ8)
    # 紀錄裡存的不是 UTC（例如別的寫入端）也要換算對
    other = _finished(started_at="2026-10-10T19:11:07+09:00")
    assert "開始時間：2026-10-10 18:11:07+08:00" in rs.format_summary(other, tz=TZ8)


def test_ac_lrs_014_scheduled_resume_at_naive_or_garbled_is_still_shown():
    """scheduled_resume_at 可能是 naive 本地字串（舊 checkpoint 形態）或亂字串：不得拋錯。"""
    naive = replace(_HALTED, scheduled_resume_at="2026-10-10T23:40:00")
    shown = datetime.fromisoformat("2026-10-10T23:40:00").astimezone().isoformat(
        sep=" ", timespec="seconds")
    assert rs.format_summary(_finished(naive)).endswith(f"可續跑時刻：{shown}")
    garbled = replace(_HALTED, scheduled_resume_at="soon")
    assert rs.format_summary(_finished(garbled), tz=TZ8).endswith("可續跑時刻：soon")


# ── schema 驗證（AC-LRS-016 的純函式層）──────────────────────────────────
def test_ac_lrs_016_valid_records_have_no_problems_and_unknown_keys_are_ignored():
    assert rs.summary_problems(_finished()) == []
    assert rs.summary_problems(_started()) == []
    assert rs.summary_problems({**_finished(), "future_optional_field": [1, 2]}) == []


def _without(record: dict, key: str) -> dict:
    return {k: v for k, v in record.items() if k != key}


@pytest.mark.parametrize(("data", "needles"), [
    pytest.param([], ["根節點必須是物件", "list"], id="root_not_object"),
    pytest.param("text", ["根節點必須是物件", "str"], id="root_is_a_string"),
    pytest.param(_without(_finished(), "started_at"), ["缺少必要欄位：started_at"],
                 id="missing_started_at"),
    pytest.param(_without(_finished(), "outcome"), ["缺少必要欄位：outcome"],
                 id="finished_missing_outcome"),
    pytest.param(_finished(total_steps="3"), ["欄位型別錯誤：total_steps"],
                 id="total_steps_is_a_string"),
    pytest.param(_finished(total_steps=True), ["欄位型別錯誤：total_steps"],
                 id="bool_is_not_an_int"),
    pytest.param(_finished(total_steps=-1), ["欄位型別錯誤：total_steps"],
                 id="negative_total_steps"),
    pytest.param(_finished(outcome="weird"), ["欄位型別錯誤：outcome", "success"],
                 id="outcome_out_of_range"),
    pytest.param(_finished(duration_seconds=-0.1), ["欄位型別錯誤：duration_seconds"],
                 id="negative_duration"),
    pytest.param(_finished(peak_token_pct=-1), ["欄位型別錯誤：peak_token_pct"],
                 id="negative_peak"),
    pytest.param(_finished(success="yes"), ["欄位型別錯誤：success"], id="success_not_bool"),
    pytest.param(_finished(reason=5), ["欄位型別錯誤：reason"], id="reason_not_str"),
    pytest.param(_finished(halt_step_idx="1"), ["欄位型別錯誤：halt_step_idx"],
                 id="halt_idx_is_a_string"),
    pytest.param(_finished(veto_reasons=[1]), ["欄位型別錯誤：veto_reasons"],
                 id="veto_reasons_not_str_list"),
    pytest.param(_finished(started_at="2026-10-10T10:11:07"), ["欄位型別錯誤：started_at"],
                 id="naive_started_at"),
    pytest.param(_finished(started_at="yesterday"), ["欄位型別錯誤：started_at"],
                 id="garbled_started_at"),
    pytest.param(_finished(status="paused"), ["欄位型別錯誤：status"], id="unknown_status"),
    pytest.param(_finished(playbook=""), ["欄位型別錯誤：playbook"], id="empty_playbook"),
    pytest.param(_finished(schema_version="1"), ["欄位型別錯誤：schema_version"],
                 id="schema_version_is_a_string"),
    pytest.param(_finished(schema_version=True), ["欄位型別錯誤：schema_version"],
                 id="schema_version_is_a_bool"),
])
def test_ac_lrs_016_summary_problems_names_the_broken_field(data, needles):
    problems = rs.summary_problems(data)
    assert problems, "損毀記錄必須回報至少一個問題"
    joined = "；".join(problems)
    for needle in needles:
        assert needle in joined


def test_ac_lrs_016_unsupported_schema_version_short_circuits():
    """AC-LRS-016(e)：版本不符即短路，不再逐欄報一串誤導的型別錯誤（舊讀者明確拒絕新檔）。"""
    future = {**_finished(total_steps="three"), "schema_version": 2}
    assert rs.summary_problems(future) == ["schema_version=2 不受支援（本版只認 1）"]


def test_ac_lrs_016_running_records_do_not_require_the_finished_fields():
    running = _started()
    assert rs.summary_problems(_without(_without(running, "outcome"), "total_steps")) == []
    assert rs.summary_problems({**running, "status": "finished"}) != []


def test_ac_lrs_016_every_missing_field_is_reported_not_just_the_first():
    problems = rs.summary_problems(_without(_without(_finished(), "outcome"), "started_at"))
    assert "缺少必要欄位：started_at" in problems and "缺少必要欄位：outcome" in problems


# ── load_summary ────────────────────────────────────────────────────────
def test_load_summary_returns_the_parsed_record(tmp_path):
    path = _put(tmp_path / "logs", _finished())
    assert rs.load_summary(path) == _finished()
    assert rs.load_summary(str(path)) == _finished()          # str 路徑也收


def test_ac_lrs_015_load_summary_distinguishes_missing_from_corrupt(tmp_path):
    with pytest.raises(rs.RunSummaryMissingError):
        rs.load_summary(tmp_path / "logs" / rs.SUMMARY_FILENAME)
    assert not (tmp_path / "logs").exists(), "讀取不得建立目錄"


@pytest.mark.parametrize(("content", "needle"), [
    pytest.param("", "JSON 解析失敗：Expecting value: line 1 column 1 (char 0)", id="empty"),
    pytest.param("{not json", "JSON 解析失敗", id="not_json"),
    pytest.param("[]", "根節點必須是物件", id="root_list"),
    pytest.param(json.dumps(_without(_finished(), "started_at")), "started_at",
                 id="missing_started_at"),
    pytest.param(json.dumps(_finished(total_steps="3")), "total_steps", id="bad_total_steps"),
    pytest.param(json.dumps({**_finished(), "schema_version": 2}), "schema_version",
                 id="schema_v2"),
])
def test_ac_lrs_016_load_summary_raises_corrupt_with_a_readable_message(
        tmp_path, content, needle):
    path = _put(tmp_path / "logs", content)
    with pytest.raises(rs.RunSummaryCorruptError) as caught:
        rs.load_summary(path)
    assert needle in str(caught.value)


def test_ac_lrs_016_undecodable_bytes_and_directories_are_corrupt_not_a_traceback(tmp_path):
    bad_bytes = tmp_path / "a" / rs.SUMMARY_FILENAME
    bad_bytes.parent.mkdir()
    bad_bytes.write_bytes(b"\xff\xfe\x00garbage")
    with pytest.raises(rs.RunSummaryCorruptError, match="UTF-8"):
        rs.load_summary(bad_bytes)
    as_dir = tmp_path / "b" / rs.SUMMARY_FILENAME
    as_dir.mkdir(parents=True)
    with pytest.raises(rs.RunSummaryCorruptError, match="無法讀取"):
        rs.load_summary(as_dir)


@pytest.mark.parametrize("content", _PATHOLOGICAL_JSON)
def test_ac_lrs_016_json_failures_that_are_not_decode_errors_are_still_corrupt(
        tmp_path, content):
    """AC-LRS-016／§3.5「絕不 traceback」：只攔 JSONDecodeError 時這兩種會以 traceback 外洩。"""
    path = _put(tmp_path / "logs", content)
    with _int_digit_limit(), pytest.raises(rs.RunSummaryCorruptError) as caught:
        rs.load_summary(path)
    message = str(caught.value)
    assert message.startswith("JSON 解析失敗：")
    assert "\n" not in message, "訊息必須單行"


def test_ac_lrs_016_multiple_problems_are_joined_with_a_fullwidth_semicolon(tmp_path):
    broken = _without(_without(_finished(), "outcome"), "started_at")
    path = _put(tmp_path / "logs", json.dumps(broken))
    with pytest.raises(rs.RunSummaryCorruptError) as caught:
        rs.load_summary(path)
    assert str(caught.value) == "缺少必要欄位：started_at；缺少必要欄位：outcome"


# ── show_last_run_summary（in-process；subprocess 版本在步驟 3）─────────────
def test_ac_lrs_001_show_prints_the_summary_and_returns_zero(tmp_path, capsys):
    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _finished())
    assert rs.show_last_run_summary(str(cfg)) == 0
    captured = capsys.readouterr()
    assert captured.out == rs.format_summary(_finished(), log_dir=log_dir.as_posix()) + "\n"
    assert captured.out.split("\n")[0] == "最近一次執行摘要"


def test_ac_lrs_001_show_is_read_only(tmp_path, capsys):
    """AC-LRS-001：唯讀——不建目錄／log／checkpoint，也不改記錄檔本身。"""
    cfg, log_dir = _write_cfg(tmp_path)
    path = _put(log_dir, _finished())
    before = (sorted(p.name for p in tmp_path.iterdir()), sorted(p.name for p in log_dir.iterdir()),
              path.read_bytes())
    assert rs.show_last_run_summary(str(cfg)) == 0
    capsys.readouterr()
    after = (sorted(p.name for p in tmp_path.iterdir()), sorted(p.name for p in log_dir.iterdir()),
             path.read_bytes())
    assert before == after


def test_ac_lrs_013_show_returns_zero_for_a_running_record(tmp_path, capsys):
    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _started())
    assert rs.show_last_run_summary(str(cfg)) == 0
    out = capsys.readouterr().out
    assert out.split("\n")[3].startswith("結果：未完成（本次執行未正常結束）")
    assert out.endswith("詳見 " + os.path.join(log_dir.as_posix(), "autoclaude.log") + "\n")


def test_ac_lrs_015_show_reports_a_missing_record_with_the_full_path(tmp_path, capsys):
    """AC-LRS-015：rc=1；stderr＝範例 E8a（完整搜尋路徑）；stdout 空；不建立任何東西。"""
    cfg, log_dir = _write_cfg(tmp_path)
    before = sorted(p.name for p in tmp_path.iterdir())
    assert rs.show_last_run_summary(str(cfg)) == 1
    captured = capsys.readouterr()
    shown = os.path.abspath(str(log_dir / rs.SUMMARY_FILENAME))
    assert captured.out == ""
    assert captured.err == (
        f"錯誤：尚無執行紀錄：找不到 {shown}"
        "（請先執行過一次 playbook；紀錄位置由 --config 的 log_dir 決定）\n")
    assert not log_dir.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == before


def test_ac_lrs_016_show_reports_a_corrupt_record_like_example_e8b(tmp_path, capsys):
    cfg, log_dir = _write_cfg(tmp_path)
    path = _put(log_dir, "")
    assert rs.show_last_run_summary(str(cfg)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"錯誤：最近一次執行紀錄損毀或無法讀取：{os.path.abspath(str(path))}"
        "（JSON 解析失敗：Expecting value: line 1 column 1 (char 0)）。"
        "可刪除該檔，下次執行 playbook 會重建。\n")


@pytest.mark.parametrize("config_text", [
    pytest.param(":\n  not valid yaml\n: [", id="yaml_syntax_error"),
    pytest.param("log_dir: [1, 2]\n", id="pydantic_validation_error"),
    pytest.param("- just\n- a list\n", id="root_is_a_list"),
])
def test_ac_lrs_017_show_turns_an_unreadable_config_into_a_message(
        tmp_path, capsys, config_text):
    """AC-LRS-017：設定檔解析／驗證失敗 ⇒ rc=1、stderr 含「設定檔」且單行、不含 Traceback。"""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(config_text, encoding="utf-8", newline="\n")
    assert rs.show_last_run_summary(str(cfg)) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "設定檔" in captured.err and str(cfg) in captured.err
    assert "Traceback" not in captured.err
    assert len(captured.err.strip().split("\n")) == 1, "錯誤訊息必須單行"


def test_ac_lrs_017_show_handles_a_config_path_that_is_a_directory(tmp_path, capsys):
    assert rs.show_last_run_summary(str(tmp_path)) == 1
    assert "設定檔" in capsys.readouterr().err


def test_ac_lrs_006_a_missing_config_falls_back_to_default_logs_dir(tmp_path, capsys):
    """AC-LRS-006：config 檔不存在 ⇒ 預設 log_dir「logs」（相對 cwd），訊息印出實際搜尋路徑。"""
    origin = Path.cwd()
    os.chdir(tmp_path)
    try:
        assert rs.show_last_run_summary(str(tmp_path / "no_such_config.yaml")) == 1
        searched = os.path.abspath(os.path.join("logs", rs.SUMMARY_FILENAME))
    finally:
        os.chdir(origin)
    err = capsys.readouterr().err
    assert searched in err and "尚無執行紀錄" in err
    assert not (tmp_path / "logs").exists()


def test_ac_lrs_018_show_survives_a_strict_ascii_stdout(tmp_path, monkeypatch):
    """AC-LRS-018（in-process 版）：stdout 無法編碼中文時降級成 \\uXXXX 字面而不是崩潰。"""
    import io

    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _finished())
    raw = io.BytesIO()
    ascii_stdout = io.TextIOWrapper(raw, encoding="ascii", errors="strict", newline="\n")
    monkeypatch.setattr(sys, "stdout", ascii_stdout)
    assert rs.show_last_run_summary(str(cfg)) == 0
    ascii_stdout.flush()
    written = raw.getvalue().decode("ascii")
    assert "\\u6700\\u8fd1" in written, "「最近」應被轉義成 ASCII 字面"
    assert "Playbook" in written


def test_ac_lrs_018_escape_helper_only_changes_the_error_handler_and_never_raises():
    """AC-LRS-018：helper 只動 errors（不強制 encoding）；無 reconfigure 或已關閉的串流不拋。"""
    import io

    ascii_stream = io.TextIOWrapper(io.BytesIO(), encoding="ascii", errors="strict")
    rs._escape_unencodable(ascii_stream)
    assert ascii_stream.encoding == "ascii" and ascii_stream.errors == "backslashreplace"
    rs._escape_unencodable(io.StringIO())              # 無 reconfigure ⇒ AttributeError 被吞
    closed = io.TextIOWrapper(io.BytesIO(), encoding="ascii")
    closed.close()
    rs._escape_unencodable(closed)                     # 已關閉 ⇒ ValueError 被吞
    rs._escape_unencodable(None)                       # 連串流都不是也不得拋


# ══════════════════════════════════════════════════════════════════════════
# 步驟 3a：subprocess 層（真 argv、真 rc、真 stdout／stderr）
# ══════════════════════════════════════════════════════════════════════════
MINIMAL_PLAYBOOK = (
    'version: "1.0"\n'
    'project: "LrsTest"\n'
    "tasks:\n"
    '  - step_id: "T01"\n'
    '    name: "n"\n'
    '    prompt: "p"\n'
)
E8C = "__main__.py: error: --last-run-summary 為唯讀查詢，不可與 playbook 位置參數或 --fresh 並用"


def _run_cli(
    *args: str, env_extra: dict[str, str] | None = None, timeout: int = 60,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """以 subprocess 執行 `python -m autoclaude <args>`（匯入期較慢，timeout 取 60）。

    stderr 在非 Windows 會多一行 import 期 warning，所以呼叫端對 stderr 一律做子字串斷言。
    """
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    env.pop("MINIMAX_API_KEY", None)                  # 避免測試中真的初始化 Minimax
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(PROJECT_ROOT), env.get("PYTHONPATH")) if part)
    env.update(env_extra or {})
    return subprocess.run(
        [sys.executable, "-m", "autoclaude", *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        env=env, cwd=str(cwd or PROJECT_ROOT), timeout=timeout,
    )


def _write_playbook(base: Path, name: str = "pb.yaml") -> Path:
    path = base / name
    path.write_text(MINIMAL_PLAYBOOK, encoding="utf-8", newline="\n")
    return path


def _listing(*directories: Path) -> list[list[str]]:
    return [sorted(p.name for p in d.iterdir()) if d.exists() else ["<absent>"]
            for d in directories]


def test_ac_lrs_001_flag_alone_prints_summary_rc0_and_creates_nothing(tmp_path):
    """AC-LRS-001：rc=0、首行逐字、唯讀（log_dir 與其上層目錄的檔案清單前後相同）。"""
    cfg, log_dir = _write_cfg(tmp_path)
    record = _finished()
    _put(log_dir, record)
    before = _listing(tmp_path, log_dir)
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 0, result.stderr
    assert result.stdout.split("\n")[0] == "最近一次執行摘要"
    assert result.stdout == rs.format_summary(record, log_dir=log_dir.as_posix()) + "\n"
    assert _listing(tmp_path, log_dir) == before, "唯讀查詢不得建立 log／目錄／checkpoint"


@pytest.mark.parametrize("order", ["flag_first", "playbook_first"])
@pytest.mark.parametrize("exists", [True, False], ids=["playbook_exists", "playbook_missing"])
def test_ac_lrs_002_flag_with_playbook_is_rejected_rc2(tmp_path, exists, order):
    """AC-LRS-002：並用 ⇒ rc=2、訊息逐字（範例 E8c）、stdout 空、不產生 log_dir。"""
    cfg, log_dir = _write_cfg(tmp_path)
    playbook = _write_playbook(tmp_path) if exists else tmp_path / "missing.yaml"
    args = (["--last-run-summary", str(playbook)] if order == "flag_first"
            else [str(playbook), "--last-run-summary"])
    result = _run_cli(*args, "--config", str(cfg))
    assert result.returncode == 2
    assert "--last-run-summary" in result.stderr and "不可與" in result.stderr
    assert E8C in result.stderr
    assert result.stdout == ""
    assert not log_dir.exists(), "拒絕並用時不得執行 playbook（不得產生 log_dir）"


def test_ac_lrs_003_flag_with_fresh_is_rejected_rc2(tmp_path):
    """AC-LRS-003：`--last-run-summary --fresh` ⇒ 同 AC-LRS-002。"""
    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _finished())
    before = _listing(tmp_path, log_dir)
    result = _run_cli("--last-run-summary", "--fresh", "--config", str(cfg))
    assert result.returncode == 2
    assert E8C in result.stderr
    assert result.stdout == ""
    assert _listing(tmp_path, log_dir) == before


def test_ac_lrs_004a_no_args_keeps_the_original_message_rc2():
    """AC-LRS-004(a)：無任何引數 ⇒ rc=2，訊息與修前逐字相同（改 nargs 後由 main() 補回）。"""
    result = _run_cli()
    assert result.returncode == 2
    assert "__main__.py: error: the following arguments are required: playbook" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("form", [
    pytest.param([], id="playbook_only"),
    pytest.param(["--config", "CFG"], id="playbook_with_config"),
    pytest.param(["--fresh"], id="playbook_with_fresh"),
])
def test_ac_lrs_004b_playbook_forms_still_reach_validation(tmp_path, form):
    """AC-LRS-004(b)：既有三種呼叫形態仍走到 playbook 驗證（rc=1、含「找不到」），不觸發 rc=2。"""
    cfg, _ = _write_cfg(tmp_path)
    extra = [str(cfg) if token == "CFG" else token for token in form]
    result = _run_cli(str(tmp_path / "nonexistent.yaml"), *extra)
    assert result.returncode == 1, result.stderr
    assert "找不到" in result.stdout + result.stderr
    assert result.returncode != 2


def test_ac_lrs_005_help_lists_new_flag_and_keeps_old_ones():
    """AC-LRS-005：--help ⇒ rc=0，含 usage:／playbook／--config／--fresh／--last-run-summary。"""
    result = _run_cli("--help")
    assert result.returncode == 0
    for token in ("usage:", "playbook", "--config", "--fresh", "--last-run-summary"):
        assert token in result.stdout, f"--help 缺 {token}"


def test_ac_lrs_006_location_follows_config_log_dir(tmp_path):
    """AC-LRS-006：兩份 config 各讀各的 log_dir；config 不存在 ⇒ 預設 logs，且印完整路徑。"""
    cfg_a, log_a = _write_cfg(tmp_path, "logs_a")
    cfg_b, log_b = _write_cfg(tmp_path, "logs_b")
    _put(log_a, _finished(playbook="/work/alpha/pb.yaml"))
    _put(log_b, _finished(playbook="/work/beta/pb.yaml"))
    out_a = _run_cli("--last-run-summary", "--config", str(cfg_a))
    out_b = _run_cli("--last-run-summary", "--config", str(cfg_b))
    assert out_a.returncode == 0 and out_b.returncode == 0
    assert "Playbook：/work/alpha/pb.yaml" in out_a.stdout
    assert "Playbook：/work/beta/pb.yaml" in out_b.stdout

    workdir = tmp_path / "work"
    workdir.mkdir()
    missing_cfg = tmp_path / "does_not_exist.yaml"
    result = _run_cli("--last-run-summary", "--config", str(missing_cfg), cwd=workdir)
    assert result.returncode == 1
    searched = os.path.join(os.path.realpath(workdir), "logs", rs.SUMMARY_FILENAME)
    assert "尚無執行紀錄" in result.stderr and searched in result.stderr
    assert not (workdir / "logs").exists()


def test_ac_lrs_013_cli_prints_running_record_rc0(tmp_path):
    """AC-LRS-013（CLI 層）：running 記錄 ⇒ rc=0，輸出為四行（不印步驟／token／ESCALATION）。"""
    cfg, log_dir = _write_cfg(tmp_path)
    running = _started()
    _put(log_dir, running)
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 0, result.stderr
    assert result.stdout == rs.format_summary(running, log_dir=log_dir.as_posix()) + "\n"
    assert len(result.stdout.rstrip("\n").split("\n")) == 4
    assert "結果：未完成（本次執行未正常結束）" in result.stdout


def test_ac_lrs_015_no_record_rc1_names_path_and_creates_nothing(tmp_path):
    """AC-LRS-015：無記錄 ⇒ rc=1、stderr＝範例 E8a（完整路徑）、stdout 空、不建任何東西。"""
    cfg, log_dir = _write_cfg(tmp_path)
    before = _listing(tmp_path)
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 1
    assert result.stdout == ""
    shown = os.path.abspath(str(log_dir / rs.SUMMARY_FILENAME))
    assert (f"錯誤：尚無執行紀錄：找不到 {shown}"
            "（請先執行過一次 playbook；紀錄位置由 --config 的 log_dir 決定）") in result.stderr
    assert _listing(tmp_path) == before and not log_dir.exists()


_CORRUPT_CASES = [
    pytest.param("", "JSON", id="a_empty_file"),
    pytest.param("not json at all", "JSON", id="a_not_json"),
    pytest.param("[]", "物件", id="b_root_not_object"),
    pytest.param(json.dumps(_without(_finished(), "started_at")), "started_at",
                 id="c_missing_started_at"),
    pytest.param(json.dumps(_finished(total_steps="3")), "total_steps",
                 id="d_total_steps_is_a_string"),
    pytest.param(json.dumps(_without(_finished(), "outcome")), "outcome",
                 id="d_finished_missing_outcome"),
    pytest.param(json.dumps({**_finished(), "schema_version": 2}), "schema_version",
                 id="e_schema_version_2"),
]


@pytest.mark.parametrize(("content", "keyword"), _CORRUPT_CASES)
def test_ac_lrs_016_corrupt_record_rc1_without_traceback(tmp_path, content, keyword):
    """AC-LRS-016：損毀五型 ⇒ rc=1、stderr 含「損毀」＋路徑＋該型關鍵字、stdout 空、無 Trace。"""
    cfg, log_dir = _write_cfg(tmp_path)
    path = _put(log_dir, content)
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 1
    assert result.stdout == ""
    assert "損毀" in result.stderr
    assert os.path.abspath(str(path)) in result.stderr
    assert keyword in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("content", _PATHOLOGICAL_JSON)
def test_ac_lrs_016_pathological_json_rc1_without_traceback(tmp_path, content):
    """AC-LRS-016／§3.5：病態 JSON（5000 位整數、20 萬層巢狀）⇒ rc=1、有「損毀」、無 Traceback。"""
    cfg, log_dir = _write_cfg(tmp_path)
    path = _put(log_dir, content)
    result = _run_cli("--last-run-summary", "--config", str(cfg),
                      env_extra={"PYTHONINTMAXSTRDIGITS": "4300"})   # 釘住位數上限，環境調過也不漂
    assert result.returncode == 1
    assert result.stdout == ""
    assert "損毀" in result.stderr and os.path.abspath(str(path)) in result.stderr
    assert "JSON 解析失敗" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("config_text", [
    pytest.param(":\n  not valid yaml\n: [", id="yaml_syntax_error"),
    pytest.param("log_dir: [1, 2]\n", id="pydantic_validation_error"),
])
def test_ac_lrs_017_unreadable_config_rc1_without_traceback(tmp_path, config_text):
    """AC-LRS-017：設定檔無法解析／驗證失敗 ⇒ rc=1、stderr 含「設定檔」、無 Traceback。"""
    cfg = tmp_path / "bad.yaml"
    cfg.write_text(config_text, encoding="utf-8", newline="\n")
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 1
    assert "設定檔" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout == ""


def test_ac_lrs_018_stdout_survives_strict_ascii_console(tmp_path):
    """AC-LRS-018：嚴格 ASCII 主控台 ⇒ rc=0（不得 UnicodeEncodeError），中文降級為跳脫字面。"""
    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _finished())
    result = _run_cli("--last-run-summary", "--config", str(cfg),
                      env_extra={"PYTHONIOENCODING": "ascii", "PYTHONUTF8": "0"})
    assert result.returncode == 0, result.stderr
    assert "\\u6700\\u8fd1" in result.stdout, "「最近」應被轉義成 ASCII 字面"
    assert "UnicodeEncodeError" not in result.stderr


# ══════════════════════════════════════════════════════════════════════════
# 步驟 3b：in-process main()（stub 掉 executor／service／開機自檢；真 parser、真 recorder 接線）
# ══════════════════════════════════════════════════════════════════════════
class _NoopExecutor:
    def run(self, *args, **kwargs):
        raise AssertionError("不應該真的執行 playbook（AutoResumeService 已被替身取代）")


def _release_autoclaude_log_handles() -> None:
    """關閉並卸下 `autoclaude` logger 的 handler。

    兩個理由：(1) Windows 不允許刪除仍被開啟的檔，tmp 清理會 WinError 32；(2) setup_logger 在
    handler 已存在時直接早退——不卸下，下一次 main() 的 log 會落進上一個（已刪除的）tmp 目錄。
    本檔唯一一份實作，`_run_main` 於前後各呼叫一次。
    """
    log = logging.getLogger("autoclaude")
    for handler in list(log.handlers):
        handler.close()
        log.removeHandler(handler)


@pytest.fixture(autouse=True)
def _no_minimax_key(monkeypatch):
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)


def _service(outcome):
    """替身 AutoResumeService：outcome 為 KernelResult（回傳）、例外實例（拋出）或 callable。"""
    class _Service:
        def __init__(self, kernel, cfg, **kwargs):
            pass

        def run(self, path, fresh=False):
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome() if callable(outcome) else outcome

    return _Service


def _run_main(
    base: Path, service_cls, *, playbook: Path | None = None, boot_rc: int = 0,
    fresh: bool = True, extra: tuple = (),
) -> int:
    """在 base 內以真 main() 跑一次啟動流程；回 rc。log_dir 固定為 base/logs。"""
    cfg, _ = _write_cfg(base)
    pb = playbook or _write_playbook(base)
    argv = ["autoclaude", str(pb), "--config", str(cfg), *(["--fresh"] if fresh else [])]
    origin = Path.cwd()
    _release_autoclaude_log_handles()
    os.chdir(base)
    try:
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(
                main_mod, "build_executor", lambda *a, **k: _NoopExecutor()))
            stack.enter_context(patch.object(main_mod, "AutoResumeService", service_cls))
            stack.enter_context(patch.object(
                main_mod, "run_boot_self_check", lambda *a, **k: boot_rc))
            stack.enter_context(patch.object(sys, "argv", argv))
            for manager in extra:
                stack.enter_context(manager)
            return main_mod.main()
    finally:
        os.chdir(origin)
        _release_autoclaude_log_handles()


def _log_text(base: Path) -> str:
    return (base / "logs" / "autoclaude.log").read_text(encoding="utf-8")


_FULL_SUCCESS = KernelResult.success_(
    3, 3, ["T01 ok", "T02 ok", "T03 ok"], ["T01", "T02", "T03"], [], peak_token_pct=41.5)
_ESCALATION = KernelResult.escalated_(1, 3, ["T01 ok"], ["T01"], "[T02] 輸出未符合期望")


def test_ac_lrs_019_successful_run_leaves_a_valid_v1_record(tmp_path):
    """AC-LRS-019：成功 run ⇒ 記錄存在、欄位齊全且與 KernelResult 一致、aware 時刻、LF 行尾。"""
    playbook = _write_playbook(tmp_path)
    assert _run_main(tmp_path, _service(_FULL_SUCCESS), playbook=playbook) == 0
    raw = (tmp_path / "logs" / rs.SUMMARY_FILENAME).read_bytes()
    assert b"\r" not in raw, "記錄檔必須是 LF 行尾（Windows 不得被翻成 CRLF）"
    record = json.loads(raw.decode("utf-8"))
    assert list(record) == SCHEMA_KEYS
    assert record["schema_version"] == 1
    assert record["status"] == "finished" and record["outcome"] == "success"
    assert record["playbook"] == os.path.abspath(str(playbook))
    assert record["success"] is True and record["escalated"] is False
    assert record["halted"] is False
    assert record["reason"] == "success"
    assert (record["total_steps"], record["completed_steps"]) == (3, 3)
    assert record["halt_step_idx"] is None and record["scheduled_resume_at"] is None
    assert record["peak_token_pct"] == 41.5 and record["veto_reasons"] == []
    started = datetime.fromisoformat(record["started_at"])
    finished = datetime.fromisoformat(record["finished_at"])
    assert started.utcoffset() is not None and finished.utcoffset() is not None
    assert started <= finished and record["duration_seconds"] >= 0
    assert rs.summary_problems(record) == []


def test_ac_lrs_019_main_writes_the_record_next_to_the_log(tmp_path):
    """§3.1.4：記錄放在 cfg.log_dir（不是 checkpoint_dir）。"""
    assert _run_main(tmp_path, _service(_FULL_SUCCESS)) == 0
    assert (tmp_path / "logs" / rs.SUMMARY_FILENAME).is_file()
    assert not list((tmp_path / "ckpt").glob(f"*{rs.SUMMARY_FILENAME}*"))


def test_ac_lrs_021_start_marker_precedes_the_result(tmp_path):
    """AC-LRS-021：service.run() 被呼叫當下檔案已存在且 status=running、結果欄位皆 null。"""
    seen: dict = {}

    def run_probe():
        seen["record"] = _read(tmp_path / "logs")
        return _FULL_SUCCESS

    assert _run_main(tmp_path, _service(run_probe)) == 0
    running = seen["record"]
    assert running["status"] == "running" and running["schema_version"] == 1
    nulls = [k for k in SCHEMA_KEYS if k not in ("schema_version", "status", "playbook",
                                                 "started_at", "veto_reasons")]
    assert all(running[k] is None for k in nulls)
    assert running["veto_reasons"] == []
    assert datetime.fromisoformat(running["started_at"]).utcoffset() is not None
    assert _read(tmp_path / "logs")["status"] == "finished"


def test_ac_lrs_021_crash_leaves_running_and_propagates(tmp_path):
    """AC-LRS-021：run() 拋例外 ⇒ 例外照常往外傳、檔案停在 running、其後查詢符合 AC-LRS-013。"""
    boom = RuntimeError("引擎崩潰")
    with pytest.raises(RuntimeError, match="引擎崩潰"):
        _run_main(tmp_path, _service(boom))
    assert _read(tmp_path / "logs")["status"] == "running"
    assert _tmp_files(tmp_path / "logs") == []
    cfg, log_dir = _write_cfg(tmp_path)
    result = _run_cli("--last-run-summary", "--config", str(cfg))
    assert result.returncode == 0, result.stderr
    assert result.stdout == rs.format_summary(
        _read(log_dir), log_dir=log_dir.as_posix()) + "\n"
    assert "結果：未完成（本次執行未正常結束）" in result.stdout


def test_ac_lrs_021_keyboard_interrupt_also_leaves_running(tmp_path):
    """Ctrl+C（KeyboardInterrupt）時 finish 沒機會執行 ⇒ 同樣停在 running（開始標記是超集合）。"""
    with pytest.raises(KeyboardInterrupt):
        _run_main(tmp_path, _service(KeyboardInterrupt()))
    assert _read(tmp_path / "logs")["status"] == "running"


def test_ac_lrs_022_second_run_overwrites_the_first(tmp_path):
    """AC-LRS-022：同一 log_dir 連跑兩次（先失敗、後成功）⇒ 檔案只剩第二次的內容。"""
    assert _run_main(tmp_path, _service(_ESCALATION)) == 1
    first = _read(tmp_path / "logs")
    assert first["outcome"] == "escalation" and first["completed_steps"] == 1
    assert _run_main(tmp_path, _service(_FULL_SUCCESS)) == 0
    second = _read(tmp_path / "logs")
    assert second["outcome"] == "success" and second["completed_steps"] == 3
    assert second["reason"] == "success"
    assert second["started_at"] >= first["started_at"]


_DISK_FULL = OSError(28, "No space left on device")
_WRITE_FAILURES = {
    "replace_permission_error": lambda: patch("os.replace", side_effect=PermissionError("no")),
    "fsync_disk_full": lambda: patch("os.fsync", side_effect=_DISK_FULL),
}


@pytest.mark.parametrize(("result", "rc"), [
    pytest.param(_FULL_SUCCESS, 0, id="success"),
    pytest.param(_ESCALATION, 1, id="escalation"),
])
@pytest.mark.parametrize("failure", sorted(_WRITE_FAILURES))
def test_ac_lrs_023_write_failure_never_changes_the_run_rc(tmp_path, failure, result, rc):
    """AC-LRS-023：寫入失敗 ⇒ rc 與沒有此功能時相同；log 有含 last_run_summary 的 WARNING。"""
    assert _run_main(tmp_path, _service(result), extra=(_WRITE_FAILURES[failure](),)) == rc
    text = _log_text(tmp_path)
    warned = [ln for ln in text.splitlines() if "[WARNING]" in ln and "last_run_summary" in ln]
    assert warned, "寫入失敗必須以 WARNING 說出（含 last_run_summary）"
    assert "Traceback" not in text
    assert "Playbook 結束 | KernelResult(" in text, "既有的結束 log 不得受影響"


@pytest.mark.parametrize("failure", sorted(_WRITE_FAILURES))
def test_ac_lrs_024_no_tmp_orphans_after_success_or_failure(tmp_path, failure):
    """AC-LRS-024：成功後、以及兩型寫入失敗後，log_dir 下都沒有殘留 *.tmp。"""
    log_dir = tmp_path / "logs"
    assert _run_main(tmp_path, _service(_FULL_SUCCESS)) == 0
    assert _read(log_dir)["status"] == "finished", "成功 run 必須真的留下記錄（防空轉通過）"
    assert _tmp_files(log_dir) == []
    intact = (log_dir / rs.SUMMARY_FILENAME).read_bytes()
    assert _run_main(tmp_path, _service(_FULL_SUCCESS), extra=(_WRITE_FAILURES[failure](),)) == 0
    assert _tmp_files(log_dir) == []
    assert (log_dir / rs.SUMMARY_FILENAME).read_bytes() == intact, "寫入失敗不得破壞既有記錄"


@pytest.mark.parametrize("preexisting", [False, True], ids=["no_prior_record", "prior_record"])
@pytest.mark.parametrize("failure", ["boot_self_check_fails", "playbook_format_invalid"])
def test_ac_lrs_025_pre_start_failures_do_not_touch_the_record(tmp_path, failure, preexisting):
    """AC-LRS-025：啟動前失敗（開機自檢非零／playbook 格式壞）不碰記錄（start 緊貼 run 之前）。"""
    log_dir = tmp_path / "logs"
    original = _put(log_dir, _finished()).read_bytes() if preexisting else None
    untouched = _service(AssertionError("啟動前失敗時 service.run 不該被呼叫"))
    if failure == "boot_self_check_fails":
        assert _run_main(tmp_path, untouched, boot_rc=3) == 3
    else:
        bad = tmp_path / "bad.yaml"
        bad.write_text('version: "1.0"\n', encoding="utf-8", newline="\n")   # 缺 tasks
        with pytest.raises(SystemExit):
            _run_main(tmp_path, untouched, playbook=bad)
    path = log_dir / rs.SUMMARY_FILENAME
    if preexisting:
        assert path.read_bytes() == original
    else:
        assert not path.exists()


@pytest.mark.parametrize(("result", "rc", "outcome"), [
    pytest.param(_FULL_SUCCESS, 0, "success", id="success"),
    pytest.param(_ESCALATION, 1, "escalation", id="escalation"),
    pytest.param(KernelResult.halted_(1, 3, [], [], halt_step_idx=1, peak_token_pct=95.0),
                 1, "token_halt", id="halt"),
])
def test_ac_lrs_026_main_rc_semantics_unchanged(tmp_path, result, rc, outcome):
    """AC-LRS-026：main() 回 0／1／1（與既有語意相同），結束 log 仍在，記錄的 outcome 對得上。"""
    assert _run_main(tmp_path, _service(result)) == rc
    assert "Playbook 結束 | KernelResult(" in _log_text(tmp_path)
    assert _read(tmp_path / "logs")["outcome"] == outcome


def test_ac_lrs_001_main_query_mode_runs_nothing_and_opens_no_log(tmp_path, capsys):
    """AC-LRS-001（main 層）：--last-run-summary 不驗 playbook、不建 logger、不建 executor。"""
    cfg, log_dir = _write_cfg(tmp_path)
    _put(log_dir, _finished())

    def forbidden(*args, **kwargs):
        raise AssertionError("查詢模式不得走到執行路徑")

    with patch.object(main_mod, "setup_logger", forbidden), \
         patch.object(main_mod, "build_executor", forbidden), \
         patch.object(main_mod, "_validate_playbook_format", forbidden), \
         patch.object(main_mod, "AutoResumeService", forbidden), \
         patch.object(sys, "argv", ["autoclaude", "--last-run-summary", "--config", str(cfg)]):
        assert main_mod.main() == 0
    assert capsys.readouterr().out.split("\n")[0] == "最近一次執行摘要"


def test_ac_lrs_002_main_rejects_flag_plus_playbook_before_any_work(tmp_path):
    """AC-LRS-002（main 層）：衝突在任何工作之前就以 argparse 的 SystemExit(2) 拒絕。"""
    cfg, log_dir = _write_cfg(tmp_path)
    with patch.object(sys, "argv", ["autoclaude", "--last-run-summary", "pb.yaml",
                                    "--config", str(cfg)]), \
         pytest.raises(SystemExit) as caught:
        main_mod.main()
    assert caught.value.code == 2
    assert not log_dir.exists()
