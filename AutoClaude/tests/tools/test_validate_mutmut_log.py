"""tests/tools/test_validate_mutmut_log.py — mutmut log 真實性驗證 helper 測試。

SD_Improving_09 觀察期 #2 殘留缺陷修復配套：
驗證 `tools/validate_mutmut_log.py` 對五種 log 情境的判定行為，
確保 `run_local_nightly.ps1` 在 mutmut 未跑 / cache 空時不會假 pass。

涵蓋 case：
    (a) 真實 Killed/Survived 統計 → exit 0
    (b) help fallback（mutant cache 空）→ exit 2
    (c) empty file → exit 2
    (d) 含 Killed 但無括號數字（legend 描述）→ exit 2
    (e) 缺檔 → exit 2
    (f) `N out of M` 變體格式 → exit 0
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).resolve().parent.parent.parent / "tools"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

from validate_mutmut_log import has_version_marker, is_real_mutmut_run, main  # noqa: E402

# --- is_real_mutmut_run() unit tests ---

def test_real_summary_lines_pass(tmp_path: Path) -> None:
    """(a) 標準 mutmut 2.4.x summary 行（含括號內整數）→ True。"""
    log = tmp_path / "real.log"
    log.write_text(
        "Legend for output:\n"
        "Killed (5)\n"
        "Survived (2)\n"
        "Timeout (0)\n"
        "Suspicious (1)\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is True


def test_help_fallback_rejected(tmp_path: Path) -> None:
    """(b) mutmut results 在 mutant cache 為空時的 help 文字 → False。"""
    log = tmp_path / "help_fallback.log"
    log.write_text(
        "To apply a mutant on disk:\n"
        "    mutmut apply <id>\n"
        "\n"
        "To show a mutant:\n"
        "    mutmut show <id>\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is False


def test_empty_file_rejected(tmp_path: Path) -> None:
    """(c) 空 log（mutmut crash / 環境問題）→ False。"""
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    assert is_real_mutmut_run(log) is False


def test_whitespace_only_rejected(tmp_path: Path) -> None:
    """(c-2) 只有空白字元的 log → False。"""
    log = tmp_path / "ws.log"
    log.write_text("   \n\t\n   \n", encoding="utf-8")
    assert is_real_mutmut_run(log) is False


def test_legend_without_counts_rejected(tmp_path: Path) -> None:
    """(d) 含 Killed/Survived 字樣但無括號內數字（legend 描述）→ False。"""
    log = tmp_path / "legend.log"
    log.write_text(
        "Legend:\n"
        "Killed mutants are those caught by tests.\n"
        "Survived mutants escaped the test suite.\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is False


def test_missing_file_rejected(tmp_path: Path) -> None:
    """(e) log 檔不存在 → False。"""
    log = tmp_path / "does_not_exist.log"
    assert is_real_mutmut_run(log) is False


def test_out_of_format_pass(tmp_path: Path) -> None:
    """(f) mutmut 變體 `N out of M` 輸出格式 → True。"""
    log = tmp_path / "out_of.log"
    log.write_text(
        "mutation testing complete\n"
        "5 out of 12 mutants killed\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is True


def test_mixed_real_summary_with_help_pass(tmp_path: Path) -> None:
    """real summary + 附加 help 文字 → True（只要有真實 summary 即可）。"""
    log = tmp_path / "mixed.log"
    log.write_text(
        "Killed (3)\n"
        "Survived (7)\n"
        "\n"
        "To apply a mutant on disk:\n"
        "    mutmut apply <id>\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is True


# --- main() CLI exit code tests ---

def test_main_exit_0_on_real_log(tmp_path: Path) -> None:
    log = tmp_path / "real.log"
    log.write_text("Killed (5)\nSurvived (2)\n", encoding="utf-8")
    assert main([str(log)]) == 0


def test_main_exit_2_on_help_fallback(tmp_path: Path) -> None:
    """模擬殘留缺陷情境：help fallback 90 bytes 必須回 exit=2。"""
    log = tmp_path / "help.log"
    log.write_text(
        "To apply a mutant on disk:\n"
        "    mutmut apply <id>\n"
        "\n"
        "To show a mutant:\n"
        "    mutmut show <id>\n",
        encoding="utf-8",
    )
    assert main([str(log)]) == 2


def test_main_exit_2_on_missing(tmp_path: Path) -> None:
    assert main([str(tmp_path / "nope.log")]) == 2


def test_main_exit_2_on_empty(tmp_path: Path) -> None:
    log = tmp_path / "empty.log"
    log.write_text("", encoding="utf-8")
    assert main([str(log)]) == 2


def test_main_exit_2_on_no_args() -> None:
    """無參數時應印 usage 並 exit=2。"""
    assert main([]) == 2


def test_real_summary_with_emoji_pass(tmp_path: Path) -> None:
    """(g) mutmut 2.4.3 帶 emoji 的真實 summary 行：

    `Killed 🎉 (12)` / `Survived 🙁 (64)` / `Timeout ⏰ (0)` / `Suspicious 🤔 (1)` /
    `Skipped 🔇 (3)` — 必須判為真實 run（觀察期 #3 修補）。
    """
    log = tmp_path / "emoji.log"
    log.write_text(
        "To apply a mutant on disk:\n"
        "    mutmut apply <id>\n"
        "\n"
        "Survived \U0001f641 (64)\n"
        "\n"
        "---- autoclaude/plugins/token_guard/compactor.py (24) ----\n",
        encoding="utf-8",
    )
    assert is_real_mutmut_run(log) is True


def test_real_existing_repo_log_is_real_run() -> None:
    """整合驗證：repo 內現存的 mutation_token_guard.log 應被判為真實 run。

    觀察期 #3 修復後（pyproject extras 補齊 + mutmut runner 限制範圍），
    repo 內 mutation_token_guard.log 已是真實 mutmut 輸出（含
    `Survived 🙁 (N)` summary 行 + per-file 細節）。若本測試 fail，
    表示 helper regex 對 mutmut 2.4.3 emoji 格式不相容、或 log 又退回 fallback。

    SD_09 W3 Round 10 audit P1-R10-1 修復（紀律 #4「驗證鏡子自身要被驗證」延伸）：
    並行跑 nightly mutation-test stage 與 pytest 時，會踩 race condition —
    [tools/run_local_nightly.ps1:275] 先 `Remove-Item $MutLog -Force` 然後
    [tools/run_mutmut_in_docker.sh] 寫入 wrapper preamble（3 行 `[run_mutmut_in_docker] ...`）
    再執行 mutmut（~5 分鐘），完成才寫入 `--- mutmut full counts (end) ---` marker。
    期間 log 處於 partial state（含 wrapper preamble 但缺 Killed/Survived 統計行）→
    `is_real_mutmut_run` 回 False → 假陽性 fail。

    修法：偵測 partial state（log 含 `[run_mutmut_in_docker]` preamble 但缺
    `--- mutmut full counts (end) ---` end marker）→ skip with reason。
    """
    repo_log = (
        Path(__file__).resolve().parent.parent.parent
        / "mutation_token_guard.log"
    )
    if not repo_log.exists():
        pytest.skip("mutation_token_guard.log not present in repo root")
    # P1-R10-1：partial state 偵測 — wrapper preamble 已寫但 mutmut 仍在跑（end marker 未到）
    text = repo_log.read_text(encoding="utf-8", errors="replace")
    has_wrapper_preamble = "[run_mutmut_in_docker]" in text
    has_end_marker = "--- mutmut full counts (end) ---" in text
    if has_wrapper_preamble and not has_end_marker:
        pytest.skip(
            "mutation_token_guard.log appears to be in partial state "
            "(wrapper preamble written but mutmut end marker missing) — "
            "nightly mutation-test stage likely in progress; skipping race condition"
        )
    # mutmut 2.4.3 真實輸出格式 `Survived 🙁 (N)` 必須被識別為 True。
    assert is_real_mutmut_run(repo_log) is True, (
        "Repo mutation_token_guard.log should be a real mutmut run "
        "(observation #3 fixed Docker extras + runner scope). If False, "
        "either regex regressed (emoji not handled) or nightly fell back to help text."
    )


# --- --require-version-marker（TD-N02，2026-06-12）---------------------------
# 意圖：版本守門標記行由 run_mutmut_in_docker.sh 在 mutmut 版本檢查通過後寫入；
# 開啟 flag 時「統計真實但缺標記」必須 fail（exit=3），防 mutmut 換版格式漂移假 pass。
# 預設關閉（向下相容）：無 flag 時行為與舊版完全一致。

def test_version_marker_present_with_flag_passes(tmp_path: Path) -> None:
    """(h) 統計真實 + 含版本標記行 + flag 開啟 → exit 0。"""
    log = tmp_path / "with_marker.log"
    log.write_text(
        "[run_mutmut_in_docker] mutmut version check: mutmut version 2.4.3\n"
        "[run_mutmut_in_docker] mutmut version OK: 2.4.3\n"
        "Killed (5)\nSurvived (2)\n",
        encoding="utf-8",
    )
    assert has_version_marker(log) is True
    assert main([str(log), "--require-version-marker"]) == 0


def test_version_marker_missing_with_flag_fails_exit_3(tmp_path: Path) -> None:
    """(i) 統計真實但缺版本標記 + flag 開啟 → exit 3（與「非真實 run」exit 2 可區分）。

    注意：`version check:` 行（檢查前回報）不可被當成標記 — 標記必須是檢查
    **通過後**寫入的 `mutmut version OK:` 行，否則版本不符（exit 4 提前終止）
    的 log 也會帶 `version check:` 行而誤判通過。
    """
    log = tmp_path / "no_marker.log"
    log.write_text(
        "[run_mutmut_in_docker] mutmut version check: mutmut version 9.9.9\n"
        "Killed (5)\nSurvived (2)\n",
        encoding="utf-8",
    )
    assert has_version_marker(log) is False
    assert main([str(log), "--require-version-marker"]) == 3


def test_version_marker_flag_off_backward_compatible(tmp_path: Path) -> None:
    """(j) flag 關閉（預設）時缺標記不影響判定 → exit 0（既有呼叫端零破壞）。"""
    log = tmp_path / "legacy.log"
    log.write_text("Killed (5)\nSurvived (2)\n", encoding="utf-8")
    assert main([str(log)]) == 0


def test_version_marker_flag_on_not_real_run_still_exit_2(tmp_path: Path) -> None:
    """(k) flag 開啟但 log 非真實 run → 仍回 exit 2（真實性檢查優先於版本標記）。"""
    log = tmp_path / "help.log"
    log.write_text(
        "[run_mutmut_in_docker] mutmut version OK: 2.4.3\n"
        "To apply a mutant on disk:\n    mutmut apply <id>\n",
        encoding="utf-8",
    )
    assert main([str(log), "--require-version-marker"]) == 2


def test_partial_state_skip_when_wrapper_preamble_only(tmp_path: Path) -> None:
    """P1-R10-1 修復配套單元測試：partial state 應 skip 而非 assert fail。

    模擬 nightly mutation-test stage 進行中 — log 含 wrapper preamble 但缺 end marker。
    is_real_mutmut_run 對此回 False（沒有 Killed/Survived 統計行），
    但測試應檢測 partial state 並 skip with reason，而非斷言 fail。
    """
    log = tmp_path / "mutation_token_guard.log"
    log.write_text(
        "[run_mutmut_in_docker] 2026-05-25T06:06:46Z module=autoclaude/plugins/token_guard"
        " tests=tests/plugins/token_guard\n"
        "[run_mutmut_in_docker] mutmut version check: mutmut version 2.4.3\n"
        "[run_mutmut_in_docker] cache cleared (.mutmut-cache + .pytest_cache)"
        " — forcing fresh baseline\n",
        encoding="utf-8",
    )
    text = log.read_text(encoding="utf-8")
    has_wrapper_preamble = "[run_mutmut_in_docker]" in text
    has_end_marker = "--- mutmut full counts (end) ---" in text
    # 模擬偵測邏輯：應為 partial state（preamble 有，end marker 無）
    assert has_wrapper_preamble is True
    assert has_end_marker is False
    # 對應實際斷言：is_real_mutmut_run 確實回 False（這是 partial state 的本質）
    assert is_real_mutmut_run(log) is False


def test_complete_state_with_end_marker_passes(tmp_path: Path) -> None:
    """P1-R10-1 修復配套單元測試：完整 state（preamble + end marker + 統計）應 pass。

    模擬 nightly mutation-test stage 完成 — log 含 wrapper preamble + Killed/Survived
    統計 + end marker。is_real_mutmut_run 應回 True；partial state 偵測不觸發。
    """
    log = tmp_path / "mutation_token_guard.log"
    log.write_text(
        "[run_mutmut_in_docker] 2026-05-25T06:06:46Z module=...\n"
        "--- mutmut full counts (from cache; SD_09 P0-G) ---\n"
        "Killed (107)\n"
        "Survived (38)\n"
        "Timeout (0)\n"
        "Suspicious (4)\n"
        "Skipped (0)\n"
        "--- mutmut full counts (end) ---\n"
        "[run_mutmut_in_docker] log written exit=0 log_bytes=1275\n",
        encoding="utf-8",
    )
    text = log.read_text(encoding="utf-8")
    assert "[run_mutmut_in_docker]" in text
    assert "--- mutmut full counts (end) ---" in text
    assert is_real_mutmut_run(log) is True
