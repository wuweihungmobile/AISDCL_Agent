"""mock_claude — 模擬 `claude -p <prompt> --output-format json` 的確定性替身（E2E／測試專用）。

為什麼 Bridge 自己帶一個，而不是用 AutoClaude/tests/fixtures/dummy_cli.py（2026-10-14 實測）：
  · AutoClaude 的 Kernel 路徑（`python -m autoclaude`）只呼叫
    `<claude.command> [旗標…] -p <prompt>`；`PlaybookTask.command` 欄位在該路徑上**零消費**。
    dummy_cli 卻是「讀 stdin 指令」的互動迴圈 ⇒ 每個步驟都會卡到 step_timeout。
  · `claude.command` 是**單一字串、不做 shlex 切分**：`python -u dummy_cli.py` 會被當成一個
    檔名而 FileNotFoundError（引擎 traceback、rc=1）⇒ 替身必須是一個**可執行檔**。
  ⇒ 本模組以 console script 形式安裝（`[project.scripts] aisdlc-mock-claude`）：
    POSIX 是 `.venv/bin/aisdlc-mock-claude`、Windows 是 `.venv\\Scripts\\aisdlc-mock-claude.exe`
    （pip／uv 產生的真 .exe 啟動器，不需要手寫 .sh／.cmd）。Docker 映像內它在 PATH 上，
    所以 `config_overrides.claude.command = "aisdlc-mock-claude"` 即可。

行為（全由環境變數控制；預設只有 0.2 秒的處理延遲，別無副作用）：
  MOCK_CLAUDE_DELAY        每次 `-p` 呼叫的處理秒數（預設 0.2）
  MOCK_CLAUDE_TRACE        若設定，每次 `-p` 呼叫 append 一行 JSON（pid／ts／prompt 頭尾／
                           keywords／sdd_env）到該檔，測試用它證明「哪些步驟真的被呼叫過」與
                           「引擎子行程的環境有沒有 SDD 寫入面的名字」，獨立於 Bridge 自己的帳
  MOCK_CLAUDE_FAIL_REGEX   prompt 命中此 regex 時輸出不含任何 `[KEYWORD]`（讓 evaluator 判失敗）
  MOCK_CLAUDE_IGNORE_TERM  設為 1 時忽略 SIGTERM（POSIX；用來驗證 SIGKILL 升級路徑）
  MOCK_CLAUDE_RESEARCH_SCRIPT
                           研究劇本模式（ResearchToPRD；TCS AT-960-22-1）。值＝劇本 JSON 的路徑，
                           格式 `{"schema": 1, "steps": [{"role": "<role>", "round": <k>,
                           "writes": [{"path": "<相對工作區>", "from": "<相對劇本目錄>"}]}]}`：
                           依 prompt 內 `.prompts/<role>.md` 與 `round=<k>` 查步驟，把 `from` 的
                           位元組原樣寫到工作區（目前目錄）的 `path`。缺步驟、壞劇本、越界路徑
                           （絕對路徑或含 `..`）＝rc 2 並在 stderr 說明（不靜默成功）。劇本內容
                           完全由夾具決定，本模組不內嵌任何評分或證據常數。
                           **未設此變數時行為與此前逐位元組相同**。
輸出：單行 JSON，形狀對齊真 claude 的 `--output-format json`（含 usage／modelUsage，使引擎
能推出 context%）；`result` 內回放 prompt 中所有 `[KEYWORD]` 字樣，滿足 expected_output_regex。
`--version` 立即回覆（引擎開機自檢會探測它），不延遲、不記 trace。
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
import time
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any

_KEYWORD_RE = re.compile(r"\[[A-Z][A-Z0-9_]*\]")
_ROLE_RE = re.compile(r"\.prompts/([a-z][a-z-]*)\.md")
_ROUND_RE = re.compile(r"\bround=(\d+)")
RESEARCH_SCRIPT_ENV = "MOCK_CLAUDE_RESEARCH_SCRIPT"
MOCK_VERSION = "0.0.0-mock"


class ScriptError(Exception):
    """研究劇本模式的確定性失敗：`run` 轉成 rc 2 與 stderr 說明。"""


def safe_relative(value: object, what: str) -> PurePosixPath:
    """劇本裡的路徑：非空字串、相對、不含 `..`（Windows 磁碟機代號與反斜線一併擋）。"""
    if not isinstance(value, str) or not value.strip():
        raise ScriptError(f"劇本的 {what} 必須是非空字串")
    posix = PurePosixPath(value.replace("\\", "/"))
    if posix.is_absolute() or re.match(r"^[A-Za-z]:", value) or ".." in posix.parts:
        raise ScriptError(f"劇本的 {what} 不得是絕對路徑或含 ..：{value}")
    return posix


def load_research_script(path: str) -> tuple[dict[str, Any], Path]:
    """讀劇本檔；回 `(內容, 劇本所在目錄)`。檔案不存在或不是合格的 JSON 劇本＝`ScriptError`。"""
    script = Path(path)
    try:
        doc = json.loads(script.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ScriptError(f"讀不到劇本檔 {path}（{type(exc).__name__}）") from exc
    except ValueError as exc:
        raise ScriptError(f"劇本檔不是 JSON：{path}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != 1 or not isinstance(
            doc.get("steps"), list):
        raise ScriptError('劇本格式錯誤：須為 {"schema": 1, "steps": [...]}')
    return doc, script.parent


def prompt_role_round(prompt: str) -> tuple[str, int]:
    """prompt 內 `.prompts/<role>.md` 的 role 與 `round=<k>` 的 k；缺任一＝`ScriptError`。"""
    role, round_no = _ROLE_RE.search(prompt), _ROUND_RE.search(prompt)
    if role is None or round_no is None:
        raise ScriptError("prompt 缺 .prompts/<role>.md 參照或 round=<k>")
    return role.group(1), int(round_no.group(1))


def find_step(doc: dict[str, Any], role: str, round_no: int) -> dict[str, Any]:
    for step in doc["steps"]:
        if isinstance(step, dict) and step.get("role") == role and step.get("round") == round_no:
            return step
    raise ScriptError(f"劇本沒有 (role={role}, round={round_no}) 的步驟")


def apply_writes(writes: object, script_dir: Path, workspace: Path) -> list[str]:
    """把劇本的每個 `from`（相對劇本目錄）位元組原樣寫到 `workspace/path`；回寫出的相對路徑。"""
    if not isinstance(writes, list):
        raise ScriptError("劇本步驟的 writes 必須是清單")
    done: list[str] = []
    for item in writes:
        if not isinstance(item, dict):
            raise ScriptError("writes 的每一項必須是 {path, from}")
        dest = safe_relative(item.get("path"), "path")
        src = safe_relative(item.get("from"), "from")
        try:
            data = script_dir.joinpath(*src.parts).read_bytes()
        except OSError as exc:
            raise ScriptError(f"劇本引用的檔案讀不到：{src}（{type(exc).__name__}）") from exc
        target = workspace.joinpath(*dest.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        done.append(dest.as_posix())
    return done


def _research_result(script: str, prompt: str) -> str:
    doc, script_dir = load_research_script(script)
    role, round_no = prompt_role_round(prompt)
    written = apply_writes(find_step(doc, role, round_no).get("writes", []), script_dir, Path.cwd())
    return f"mock claude 研究劇本完成（role={role} round={round_no}）：寫出 {len(written)} 個檔案。"


def result_payload(result: str) -> dict[str, Any]:
    """`--output-format json` 的單行輸出本體（形狀對齊真 claude；鍵序即輸出序）。"""
    return {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "num_turns": 1,
        "result": result,
        "session_id": "mock-session",
        "total_cost_usd": 0.0,
        "usage": {
            "input_tokens": 1200,
            "cache_read_input_tokens": 0,
            "cache_creation_input_tokens": 0,
            "output_tokens": 40,
        },
        "modelUsage": {"mock-model": {"contextWindow": 200000}},
    }


def _prompt_from_argv(argv: list[str]) -> str:
    # PtyExecutor 把 `-p`、prompt 放在 argv 最後：`-p` 之後的下一個引數就是 prompt。
    if "-p" in argv:
        idx = argv.index("-p")
        if idx + 1 < len(argv):
            return argv[idx + 1]
    return ""


def run(argv: list[str]) -> int:
    if "--version" in argv:
        sys.stdout.write(f"{MOCK_VERSION} (mock claude)\n")
        sys.stdout.flush()
        return 0
    if os.environ.get("MOCK_CLAUDE_IGNORE_TERM") == "1" and sys.platform != "win32":
        # Windows 行為＝終止即 TerminateProcess，本來就無法被忽略，故只在 POSIX 設。
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    prompt = _prompt_from_argv(argv)
    keywords = _KEYWORD_RE.findall(prompt)
    script = os.environ.get(RESEARCH_SCRIPT_ENV, "")
    trace = os.environ.get("MOCK_CLAUDE_TRACE", "")
    if trace:
        entry: dict[str, Any] = {
            "pid": os.getpid(),
            "ts": datetime.now(UTC).isoformat(),
            "prompt_head": prompt[:80],
            "prompt_tail": prompt[-120:],   # 引擎只會在前面加前綴：尾端必須原樣到達
            "keywords": keywords,   # 引擎可能在 prompt 前加 global_goal 前綴：認關鍵字最穩
            # 證明「引擎子行程的環境」長什麼樣（ADR-XPLAT-016 §9「剝除」列；F-7）：Bridge 自己
            # 的環境若帶權杖／狀態目錄／別的專案鍵，它們不得走到這裡。只記名稱是否存在與非機密
            # 值，絕不記權杖值。
            "sdd_env": {"SDD_PROJECT": os.environ.get("SDD_PROJECT"),
                        "SDD_STATE_DIR": os.environ.get("SDD_STATE_DIR"),
                        "has_write_token": "BRIDGE_SDD_WRITE_TOKEN" in os.environ},
        }
        if script:      # 研究劇本模式另記環境鍵名（只記名稱，不記值）：證明機密哨兵沒有走到這裡
            entry["env_keys"] = sorted(os.environ)
        with open(trace, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    delay = float(os.environ.get("MOCK_CLAUDE_DELAY", "0.2") or 0)
    if delay > 0:
        time.sleep(delay)
    fail_regex = os.environ.get("MOCK_CLAUDE_FAIL_REGEX", "")
    if fail_regex and re.search(fail_regex, prompt):
        keywords = []
    result = "mock claude 完成。" + " ".join(dict.fromkeys(keywords))
    if script:
        try:
            result = _research_result(script, prompt)
        except ScriptError as exc:
            sys.stderr.write(f"mock claude 研究劇本：{exc}\n")
            return 2
    sys.stdout.write(json.dumps(result_payload(result), ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return 0


def main() -> None:
    """console script 入口（`aisdlc-mock-claude`）。"""
    raise SystemExit(run(sys.argv[1:]))


if __name__ == "__main__":
    main()
