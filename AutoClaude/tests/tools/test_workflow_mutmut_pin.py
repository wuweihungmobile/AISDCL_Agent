"""tests/tools/test_workflow_mutmut_pin.py — DEF-200-356 mutmut CI 版本鎖回歸鎖。

WHY（Rule 9 測意圖非僅行為）：
`.github/workflows/*.yml` 內以裸 `pip install mutmut` 安裝、未鎖版；`AutoClaude/pyproject.toml`
的 `mutation` extra 已鎖 `mutmut==2.4.3` 並註明 mutmut 3.x 的 CLI 重寫拿掉了
`--paths-to-mutate` / `--tests-dir`（與 `tools/run_mutmut_in_docker.sh` 一致）。
2026-09-21 排程 run 35579774973（headSha ad88dbd7，job「Mutation Test - TokenGuardPlugin
(active pilot)」28 秒 success）log 逐字：
    Downloading mutmut-3.8.0-py3-none-any.whl
    ...
    FileNotFoundError: Could not figure out where the code to mutate is
被 `|| true` 吞掉、job 仍回 success；08-31 排程 run 同型 —— CI 的 mutation testing
至少自 08-31 起是假綠：改 token_guard 源碼即便真的沒被任何 mutant 殺掉，job 依然全綠。

本測試鎖：
  1. 每一個 workflow 內含 `pip install` 且含 `mutmut` 的非註解行，都必須含
     `mutmut==<SSOT 版本>`（SSOT＝`AutoClaude/pyproject.toml` 的
     `[project.optional-dependencies].mutation`，不手抄字面 2.4.3）。
  2. 命中數 >= 4 —— 若掃描形態日後改壞（例如 workflow 改寫成不含這兩個關鍵字的
     安裝方式）導致 0 命中，本測試仍必須是紅，不能因為「掃不到東西」而悄悄綠掉。
  3. `AutoClaude/tools/run_mutmut_in_docker.sh` 自身的鎖版與 SSOT 一致（該檔已鎖版，
     見其 `pip install --quiet ... "mutmut==2.4.3"` 行）。
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_MUTMUT_PIN_RE = re.compile(r"mutmut==([0-9]+(?:\.[0-9]+)*)")


def _ssot_version() -> str:
    """SSOT：`AutoClaude/pyproject.toml` 的 `[project.optional-dependencies].mutation`。

    不手抄 2.4.3 常數——直接從 toml 抽出，SSOT 改版本時本測試的期望值同步改。
    """
    pyproject = _REPO_ROOT / "AutoClaude" / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    mutation_deps = data["project"]["optional-dependencies"]["mutation"]
    for dep in mutation_deps:
        m = _MUTMUT_PIN_RE.search(dep)
        if m:
            return m.group(1)
    raise AssertionError(
        "AutoClaude/pyproject.toml 的 `mutation` extra 找不到 `mutmut==<版本>` "
        f"字串（可能已改版或改名，需回頭改本測試的抽取邏輯）：{mutation_deps!r}"
    )


def _uncommented(text: str) -> list[str]:
    return [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]


def _strip_unquoted_trailing_comment(line: str) -> str:
    """去掉行尾的 `# ...` inline 註解，但不動雙引號內的 `#`（本檔用不到，防呆保留）。"""
    in_quotes = False
    for i, ch in enumerate(line):
        if ch == '"':
            in_quotes = not in_quotes
        elif ch == "#" and not in_quotes:
            return line[:i]
    return line


def _mutmut_run_segments(text: str) -> list[str]:
    """從 workflow 原始文字擷取每一段 `mutmut run ...` 指令（含反斜線續行合併成單行）。

    DEF-200-357：`mutmut run` 段落慣例用 `\\` 續多行（--paths-to-mutate / --tests-dir /
    --runner / --no-progress ... 各占一行），逐行掃會漏判「裸 -p no:xdist 出現在
    --runner 引號外」這種跨行違規，故先合併續行、剝掉行尾 inline 註解後再判。
    """
    lines = _uncommented(text)
    segments: list[str] = []
    current: list[str] = []
    in_segment = False
    for raw_ln in lines:
        stripped = _strip_unquoted_trailing_comment(raw_ln).strip()
        if not in_segment:
            if stripped.startswith("mutmut run"):
                in_segment = True
                current = [stripped]
                if not stripped.endswith("\\"):
                    segments.append(current[0].rstrip("\\").strip())
                    in_segment = False
                    current = []
            continue
        current.append(stripped)
        if stripped.endswith("\\"):
            continue
        segments.append(" ".join(part.rstrip("\\").strip() for part in current))
        in_segment = False
        current = []
    return segments


def _strip_quoted_runner_arg(segment: str) -> str:
    """移除 `--runner="..."` 引號內文字，只留段落其餘部分供裸旗標掃描。"""
    return re.sub(r'--runner="[^"]*"', "--runner=<quoted>", segment)


def test_ssot_version_is_parseable() -> None:
    """紀律 #4「驗證鏡子自身要被驗證」：SSOT 抽取本身要先能拿到合法版本字串。"""
    version = _ssot_version()
    assert re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version), (
        f"抽出的 SSOT 版本格式不像合法版號：{version!r}"
    )


def test_every_workflow_pip_install_mutmut_line_is_pinned_to_ssot() -> None:
    """DEF-200-356 主斷言：所有 workflow 的 `pip install ... mutmut ...` 行皆鎖版。"""
    ssot = _ssot_version()
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    hits: list[str] = []
    unpinned: list[str] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for lineno, ln in enumerate(text.splitlines(), start=1):
            if ln.lstrip().startswith("#"):
                continue
            if "pip install" not in ln or "mutmut" not in ln:
                continue
            coord = f"{wf.relative_to(_REPO_ROOT)}:{lineno}"
            hits.append(coord)
            if f"mutmut=={ssot}" not in ln:
                unpinned.append(f"{coord} -> {ln.strip()!r}")

    assert not unpinned, (
        "以下 workflow 行安裝 mutmut 卻未鎖版對齊 SSOT (mutmut=="
        f"{ssot})，DEF-200-356 復發：\n" + "\n".join(unpinned)
    )
    assert len(hits) >= 4, (
        "命中數 < 4 —— 掃描形態可能已失效（0 命中假綠會被誤判為『全部鎖好』），"
        f"現查座標：{hits}"
    )


def test_run_mutmut_in_docker_sh_is_pinned_to_ssot() -> None:
    """`tools/run_mutmut_in_docker.sh` 的隔離樹安裝行同樣要對齊 SSOT，不得各鎖各的版本。"""
    ssot = _ssot_version()
    script = _REPO_ROOT / "AutoClaude" / "tools" / "run_mutmut_in_docker.sh"
    assert script.is_file(), script
    pin_lines = [
        ln for ln in _uncommented(script.read_text(encoding="utf-8"))
        if "pip install" in ln and "mutmut==" in ln
    ]
    assert pin_lines, (
        "run_mutmut_in_docker.sh 找不到 `pip install ... mutmut==<版本>` 鎖版行"
        "——若該檔已改成不鎖版，需回頭改寫本測試（只保留 workflow 斷言），"
        "不可直接刪掉本測試"
    )
    for ln in pin_lines:
        assert f"mutmut=={ssot}" in ln, (
            f"run_mutmut_in_docker.sh 鎖版與 SSOT (mutmut=={ssot}) 不一致：{ln.strip()!r}"
        )


def _segment_violations(segment: str) -> list[str]:
    """回傳一段 `mutmut run ...`（已合併續行）違反 DEF-200-357 契約之處；空 list＝合格。

    契約（本輪修復 DEF-200-357：`mutmut run … -p no:xdist -o addopts= || true` 這兩個
    pytest 專屬旗標是裸傳給 `mutmut` 本身，2.4.3 直接 `Error: No such option '-p'`，
    被 `|| true` 吞掉使 job 假綠——見 AutoClaude/tools/run_mutmut_in_docker.sh 早已用
    `--runner="..."` 包住同類 pytest 旗標的既有形態）：
      (a) 不得在 `--runner="..."` 引號**外**出現裸 `-p no:xdist` 或 `-o addopts=`；
      (b) 必須含 `--runner`（pytest 旗標的唯一合法棲身處）；
      (c) 必須含 `--CI`（讓 fatal error 回 exit 1、survived/timeout 等『正常結束』回 0）；
      (d) 不得再含 `|| true`（`--CI` 已提供正確的 fail-loud 語意，`|| true` 只會把
          真崩潰重新吞回假綠，兩者不能並存）。
    """
    problems: list[str] = []
    unquoted = _strip_quoted_runner_arg(segment)
    if re.search(r"(?:^|\s)-p\s+no:xdist", unquoted):
        problems.append("裸 -p no:xdist 出現在 --runner 引號外")
    if re.search(r"(?:^|\s)-o\s+addopts=", unquoted):
        problems.append("裸 -o addopts= 出現在 --runner 引號外")
    if "--runner" not in segment:
        problems.append("缺少 --runner")
    if "--CI" not in segment:
        problems.append("缺少 --CI")
    if "|| true" in segment:
        problems.append("仍含 || true（應以 --CI fail-loud 取代）")
    return problems


def test_every_mutmut_run_segment_uses_runner_and_ci_not_bare_flags() -> None:
    """DEF-200-357 主斷言：所有 workflow 的 `mutmut run` 段皆用 --runner 包住 pytest 旗標、
    帶 --CI、不含 || true；且命中段數 >= 4（掃描形態失效不得悄悄綠掉，同紀律 #2 手法）。
    """
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    hits: list[tuple[str, str]] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        for seg in _mutmut_run_segments(text):
            hits.append((str(wf.relative_to(_REPO_ROOT)), seg))

    violations = [
        f"{wf_rel}: {'; '.join(problems)} -> {seg!r}"
        for wf_rel, seg in hits
        if (problems := _segment_violations(seg))
    ]
    assert not violations, (
        "以下 mutmut run 段落違反 DEF-200-357 契約：\n" + "\n".join(violations)
    )
    assert len(hits) >= 4, (
        "命中的 `mutmut run` 段數 < 4 —— 掃描形態可能已失效（0 命中假綠會被誤判為"
        f"『全部合規』），現查座標：{[wf for wf, _ in hits]}"
    )


def _mutmut_results_segments(text: str) -> list[tuple[str, str]]:
    """DEF-200-365：擷取每個 `mutmut results | tee <log>` 行與其後第一個非空白指令行。

    對稱於 `_mutmut_run_segments`——後者合併 `mutmut run` 的續行段落，本函式則配對
    「`mutmut results | tee` 這一行」與「緊接在後的下一個非空白指令行」（跨過空行，
    `_uncommented` 已先濾掉整行註解；行尾 inline 註解另以 `_strip_unquoted_trailing_comment`
    剝除，不影響比對）。

    回傳 `(tee_line, next_line)` tuples；`next_line` 找不到時為空字串（該段落沒有
    後續指令，本身就是一種違規，由呼叫端判定）。
    """
    lines = _uncommented(text)
    segments: list[tuple[str, str]] = []
    n = len(lines)
    for i, raw_ln in enumerate(lines):
        stripped = _strip_unquoted_trailing_comment(raw_ln).strip()
        if not re.match(r"mutmut results \| tee\s+\S+", stripped):
            continue
        next_line = ""
        for j in range(i + 1, n):
            candidate = _strip_unquoted_trailing_comment(lines[j]).strip()
            if not candidate:
                continue
            next_line = candidate
            break
        segments.append((stripped, next_line))
    return segments


def _cache_counts_violations(text: str) -> list[str]:
    """DEF-200-365 主契約：每個 `mutmut results | tee <log>` 段的下一行必須是
    `python tools/mutmut_cache_counts.py >> <同一 log>`（`mutmut results` 結構上永不印
    Killed，需從 `.mutmut-cache` 補上 marker 段給 `mutation_baseline_lock.py` 讀，
    見 `AutoClaude/tools/mutmut_cache_counts.py` 檔頭）。回傳違規訊息 list；空 list＝合格。
    """
    problems: list[str] = []
    for tee_line, next_line in _mutmut_results_segments(text):
        m = re.search(r"mutmut results \| tee\s+(\S+)", tee_line)
        log_name = m.group(1) if m else None
        if not next_line:
            problems.append(f"{tee_line!r} 後面沒有任何後續指令行（缺 cache-counts 補丁）")
            continue
        if "tools/mutmut_cache_counts.py" not in next_line:
            problems.append(
                f"{tee_line!r} 後一行不是 mutmut_cache_counts.py 補丁：{next_line!r}"
            )
            continue
        if log_name and f">> {log_name}" not in next_line:
            problems.append(
                f"{tee_line!r} 後一行未 append 回同一 log（{log_name}）：{next_line!r}"
            )
    return problems


def test_every_mutmut_results_tee_is_followed_by_cache_counts_append_to_same_log() -> None:
    """DEF-200-365 主斷言：所有 workflow 的 `mutmut results | tee <log>` 行後緊接
    `python tools/mutmut_cache_counts.py >> <同一 log>`；且命中段數 >= 4（掃描形態失效
    不得悄悄綠掉，同紀律 #2／DEF-200-357 手法）。
    """
    workflows_dir = _REPO_ROOT / ".github" / "workflows"
    hits: list[tuple[str, str]] = []
    violations: list[str] = []
    for wf in sorted(workflows_dir.glob("*.yml")):
        text = wf.read_text(encoding="utf-8")
        rel = str(wf.relative_to(_REPO_ROOT))
        for tee_line, _next_line in _mutmut_results_segments(text):
            hits.append((rel, tee_line))
        violations.extend(f"{rel}: {p}" for p in _cache_counts_violations(text))

    assert not violations, (
        "以下 `mutmut results | tee` 段落缺少 DEF-200-365 cache-counts 補丁：\n"
        + "\n".join(violations)
    )
    assert len(hits) >= 4, (
        "命中的 `mutmut results | tee` 段數 < 4 —— 掃描形態可能已失效（0 命中假綠會被"
        f"誤判為『全部合規』），現查座標：{[wf for wf, _ in hits]}"
    )


def test_cache_counts_append_detector_has_red_green_self_proof() -> None:
    """mirror 紅綠自證（紀律 #4「驗證鏡子自身要被驗證」）：合成一段缺 helper 行的假 yml
    文字必須被判至少 1 個 violation；真檔（含正確補丁行）必須零違規。
    """
    good = (
        "          mutmut run --paths-to-mutate=x --runner=\"y\" --no-progress --CI\n"
        "          mutmut results | tee mutation_token_guard.log\n"
        "          python tools/mutmut_cache_counts.py >> mutation_token_guard.log"
        "  # DEF-200-365：results 不印 Killed，從 .mutmut-cache 補 marker 段給"
        " mutation_baseline_lock\n"
    )
    assert _cache_counts_violations(good) == [], (
        f"正確形態不應被判違規：{_cache_counts_violations(good)}"
    )

    missing_patch = (
        "          mutmut results | tee mutation_token_guard.log\n"
        "          python tools/mutation_baseline_lock.py token_guard"
        " --log mutation_token_guard.log\n"
    )
    problems_missing = _cache_counts_violations(missing_patch)
    assert problems_missing, "缺 cache_counts 補丁行應被判違規，卻沒有 finding"

    wrong_log = (
        "          mutmut results | tee mutation_token_guard.log\n"
        "          python tools/mutmut_cache_counts.py >> mutation_goal_synthesis.log\n"
    )
    problems_wrong_log = _cache_counts_violations(wrong_log)
    assert problems_wrong_log, "append 到錯誤 log 檔名應被判違規，卻沒有 finding"


def test_segment_violation_detector_has_red_green_self_proof() -> None:
    """mirror 紅綠自證（紀律 #4「驗證鏡子自身要被驗證」）：
    正確形態必須判 0 violation；拿掉 --runner 退回裸旗標 + || true、或在引號外多出裸旗標，
    都必須被判至少 1 個 violation。
    """
    good = (
        'mutmut run --paths-to-mutate=autoclaude/plugins/token_guard '
        '--tests-dir=tests/plugins/token_guard '
        '--runner="python -m pytest -x -q -p no:xdist -o addopts= tests/plugins/token_guard" '
        '--no-progress --CI'
    )
    assert _segment_violations(good) == [], (
        f"正確形態不應被判違規：{_segment_violations(good)}"
    )

    reverted = (
        'mutmut run --paths-to-mutate=autoclaude/plugins/token_guard '
        '--tests-dir=tests/plugins/token_guard '
        '--no-progress -p no:xdist -o addopts= || true'
    )
    problems_reverted = _segment_violations(reverted)
    assert problems_reverted, (
        "退回 DEF-200-356 舊形態（無 --runner／--CI，仍 || true）應被判違規，卻沒有 finding"
    )

    bare_flag_outside_runner = good + " -p no:xdist"
    problems_leak = _segment_violations(bare_flag_outside_runner)
    assert problems_leak, "引號外多出裸 -p no:xdist 應被判違規，卻沒有 finding"
