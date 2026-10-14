"""引擎 stdout 解析與步驟狀態機。格式依據＝2026-10-14 對真引擎的實測輸出（見 app/logparse.py）。"""
from __future__ import annotations

import pytest

from app.logparse import LineParser, StepDef, StepTracker

TS = "2026-10-14 22:19:22"


def _start_line(prompt: str, *, cmd: str = "/x/aisdlc-mock-claude") -> str:
    argv = [cmd, "--continue", "--output-format", "json", "-p", prompt]
    return f"{TS} [INFO] autoclaude.perception: subprocess 模式啟動：{argv}"


class TestLineParser:
    def test_plain_info_and_levels(self) -> None:
        p = LineParser()
        assert p.parse(f"{TS} [WARNING] autoclaude: 未設定 MINIMAX_API_KEY").level == "WARNING"
        assert p.parse(f"{TS} [ERROR] autoclaude: 壞了").level == "ERROR"
        assert p.parse("keyboard 未安裝，ESC+F12 全域中斷將無法使用").level == "INFO"

    def test_traceback_lines_without_prefix_are_errors_until_the_next_prefixed_line(self) -> None:
        p = LineParser()
        assert p.parse("Traceback (most recent call last):").level == "ERROR"
        assert p.parse('  File "<frozen runpy>", line 198').level == "ERROR"
        assert p.parse("FileNotFoundError: [Errno 2] x").level == "ERROR"
        assert p.parse(f"{TS} [INFO] autoclaude: 後續").level == "INFO"
        assert p.parse("下一行無前綴").level == "INFO"

    @pytest.mark.parametrize("prompt", [
        "請執行初始化步驟並確認完成，完成後輸出 [INIT_DONE]",
        "含單引號 it's 與雙引號 \"x\" 與換行\n第二行\t與 Tab",
        "同時含 ' 和 \" 兩種：It's \"quoted\"",
        "反斜線 C:\\path\\to 與 \\n 字面",
    ])
    def test_the_prompt_is_recovered_exactly_from_the_argv_repr(self, prompt: str) -> None:
        parsed = LineParser().parse(_start_line(prompt))
        assert parsed.kind == "attempt_start"
        assert parsed.prompt == prompt

    def test_an_argv_without_dash_p_or_a_non_list_start_line_gives_no_prompt(self) -> None:
        line = f"{TS} [INFO] autoclaude.perception: subprocess 模式啟動：['x', '--version']"
        assert LineParser().parse(line).prompt is None
        shim = f"{TS} [INFO] autoclaude.perception: subprocess 模式啟動：cmd /d /s /c \"x -p y\""
        parsed = LineParser().parse(shim)
        assert (parsed.kind, parsed.prompt) == ("attempt_start", None)

    def test_wexpect_start_line_on_windows(self) -> None:
        # Windows 行為＝有 wexpect 時引擎改印 `wexpect 模式啟動：<exe> args=[…]`（Windows 未實測）。
        line = (f"{TS} [INFO] autoclaude.perception: wexpect 模式啟動：claude.exe "
                f"args={['--continue', '-p', '你好']!r}")
        assert LineParser().parse(line).prompt == "你好"

    def test_token_peak(self) -> None:
        line = f"{TS} [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=T01 pct=0.6000 ==="
        parsed = LineParser().parse(line)
        assert (parsed.kind, parsed.step_id, parsed.pct) == ("token_peak", "T01", 0.6)

    def test_step_ids_with_spaces_survive(self) -> None:
        line = f"{TS} [INFO] autoclaude.core.kernel: === STEP_TOKEN_PEAK | step=步驟 一 pct=12 ==="
        assert LineParser().parse(line).step_id == "步驟 一"

    def test_escalation_marker(self) -> None:
        line = (f"{TS} [ERROR] autoclaude.core.kernel: === STATE: ESCALATION | step=A2 | "
                "[A2] 輸出未符合期望 regex: '\\\\[TWO_DONE\\\\]' ===")
        parsed = LineParser().parse(line)
        assert (parsed.kind, parsed.state, parsed.step_id) == ("state", "ESCALATION", "A2")
        assert "輸出未符合期望 regex" in parsed.detail

    @pytest.mark.parametrize(("body", "name", "step"), [
        ("step=T02 attempt=1", "CORRECTION", "T02"),
        ("[T03] context 92% >= halt 門檻", "TOKEN_HALT", "T03"),
        ("[T04] 推論端 429（有 Retry-After）⇒ 退避 3.0s 後重跑同一個 attempt（本 step 第 1 次）",
         "LIMIT_RETRY", "T04"),
    ])
    def test_other_state_markers(self, body: str, name: str, step: str) -> None:
        line = f"{TS} [WARNING] autoclaude.core.kernel: === STATE: {name} | {body} ==="
        parsed = LineParser().parse(line)
        assert (parsed.state, parsed.step_id) == (name, step)

    def test_the_end_line_is_parsed_from_the_real_kernel_result_repr(self) -> None:
        # 以引擎自己的 dataclass 產生 repr，格式漂移時這支會紅（而不是靠手抄字串）。
        from autoclaude.core.kernel_state import KernelResult

        ok = KernelResult.success_(
            completed_steps=3, total_steps=3, step_log=["[T01] halted=True ✓"],
            completed_step_ids=["T01", "T02", "T03"], contributors=[], peak_token_pct=0.6)
        parsed = LineParser().parse(f"{TS} [INFO] autoclaude: Playbook 結束 | {ok}")
        assert parsed.kind == "run_end"
        assert (parsed.end.success, parsed.end.halted, parsed.end.escalated) == (True, False, False)
        assert (parsed.end.completed_steps, parsed.end.total_steps) == (3, 3)

        esc = KernelResult.escalated_(
            completed_steps=1, total_steps=2, step_log=["x"], completed_step_ids=["A1"],
            reason="[A2] 輸出未符合期望 regex: 'x'")
        end = LineParser().parse(f"{TS} [INFO] autoclaude: Playbook 結束 | {esc}").end
        assert (end.success, end.escalated, end.halted) == (False, True, False)

        halt = KernelResult.halted_(
            completed_steps=1, total_steps=2, step_log=[], completed_step_ids=["A1"],
            halt_step_idx=1, peak_token_pct=93.0)
        end = LineParser().parse(f"{TS} [INFO] autoclaude: Playbook 結束 | {halt}").end
        assert (end.success, end.halted) == (False, True)


STEPS = [
    StepDef("T01", "初始化", "請執行初始化步驟 [INIT_DONE]"),
    StepDef("T02", "建立測試", "請建立測試案例 [TEST_CREATED]"),
    StepDef("T03", "Ping", "請執行 ping 測試 [PONG]"),
]


class TestStepTracker:
    def test_sequential_run_completes_each_step_when_the_next_one_starts(self) -> None:
        t = StepTracker(STEPS)
        d1 = t.classify_start(STEPS[0].prompt)
        assert (d1.idx, d1.retry, d1.completes) == (0, False, None)
        t.begin(d1.idx)
        d2 = t.classify_start(STEPS[1].prompt)
        assert (d2.idx, d2.retry, d2.completes) == (1, False, 0)
        assert t.complete_current() == (0, 1)
        t.begin(d2.idx)
        assert t.completed == ["T01"]
        assert t.next_idx == 1

    def test_a_second_start_of_the_same_step_is_a_retry(self) -> None:
        t = StepTracker(STEPS)
        t.begin(t.classify_start(STEPS[0].prompt).idx)
        d = t.classify_start(STEPS[0].prompt)
        assert (d.idx, d.retry, d.completes) == (0, True, None)
        assert t.retry() == 2

    def test_a_global_goal_prefix_does_not_break_matching(self) -> None:
        t = StepTracker(STEPS)
        prefixed = "=== 總目標 ===\n示範\n=== 目前步驟 ===\n" + STEPS[0].prompt
        assert t.classify_start(prefixed).idx == 0

    def test_a_prompt_rewritten_by_the_brain_counts_as_a_retry_of_the_current_step(self) -> None:
        t = StepTracker(STEPS)
        t.begin(t.classify_start(STEPS[0].prompt).idx)
        d = t.classify_start("[mock correction #1] 請修正 line 21 的 assert")
        assert (d.idx, d.retry) == (0, True)

    def test_an_unparseable_prompt_falls_back_to_the_next_expected_step(self) -> None:
        t = StepTracker(STEPS)
        assert t.classify_start(None).idx == 0
        t.begin(0)
        # 目前步驟進行中、又來一個解析不到 prompt 的啟動行 ⇒ 保守視為重試
        assert t.classify_start(None).retry is True

    def test_resuming_after_a_checkpoint_starts_from_the_next_step(self) -> None:
        t = StepTracker(STEPS, completed_ids=["T01"])
        assert t.next_idx == 1
        d = t.classify_start(STEPS[1].prompt)
        assert (d.idx, d.completes) == (1, None)

    def test_the_longest_matching_prompt_wins_when_one_prompt_contains_another(self) -> None:
        steps = [StepDef("A", "短", "執行測試"), StepDef("B", "長", "執行測試並產出報告")]
        t = StepTracker(steps, completed_ids=["A"])
        t.begin(1)
        t.complete_current()
        assert t.classify_start("執行測試並產出報告").idx == 1

    def test_fail_current_clears_the_in_progress_step(self) -> None:
        t = StepTracker(STEPS)
        t.begin(0)
        assert t.fail_current() == (0, 1)
        assert t.fail_current() is None

    def test_an_empty_playbook_never_classifies(self) -> None:
        assert StepTracker([]).classify_start("x") is None
