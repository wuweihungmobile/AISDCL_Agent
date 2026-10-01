"""DEF-200-447／449：提醒型 hook 不佔結束碼，且「出聲」必須落在 CC 真的會呈現的通道。

意圖（Rule 9）：官方契約＝exit 0 下 stderr 與純文字 stdout 都只進 debug log（靜默）；
只有 stdout 的單一 JSON（`systemMessage`／`hookSpecificOutput.additionalContext`）才被呈現。
所以「rc==0」這個斷言單獨成立時，把 `return 1` 悄悄改成 `return 0` 也會綠——本檔每條都
同時釘 ① rc ② stdout JSON 的通道與事件名 ③ 訊息內容，缺一不可。

DEF-200-449：`check_lang` 的資料源曾只讀 `transcript_path`，而 Stop 當下逐字稿不保證含本回合
最後訊息（`claude -p` 實測零 assistant 事件）⇒ 活體恆 fail-open、從沒真正啟動過；外觀與
「回覆全是繁中」完全相同，所以必須有測試把「資料源」本身釘住。
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOKS = PROJECT_ROOT / "tools" / "hooks"


@pytest.fixture(autouse=True)
def _clean_model_buffer():
    """`emit_to_model` 的緩衝是 platform_utils 的模組全域；前一個測試殘留會污染下一個。"""

    def _drain() -> None:
        pu = sys.modules.get("platform_utils")
        if pu is not None:
            pu.flush_to_model()

    _drain()
    yield
    _drain()


def _load(name: str):
    """以 importlib 載入 hook 模組；每次一份新模組＝乾淨的 `_ADVISORIES`。"""
    spec = importlib.util.spec_from_file_location(f"_hook_{name}_447", HOOKS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(script: str, payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )


def _transcript(tmp_path: Path, text: str | None) -> Path:
    """`text=None` ⇒ 零 assistant 事件的逐字稿（`claude -p` 在 Stop 當下實測的形態）。"""
    events: list[dict] = [{"type": "user", "message": {"content": "你好"}}]
    if text is not None:
        events.append(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}
        )
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in events), encoding="utf-8")
    return path


def _single_json(stdout: str) -> dict:
    """stdout 必須恰為『一個』JSON 物件（兩份相接＝CC parse 失敗＝兩則一起消失）。"""
    doc = json.loads(stdout)
    assert isinstance(doc, dict), stdout
    return doc


def _drive_main(mod, payload: dict, monkeypatch, capsys):
    """in-process 跑 `main()`，再顯式 flush（production 由 atexit 做）取出 stdout／stderr。"""
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    rc = mod.main()
    sys.modules["platform_utils"].flush_to_model()
    captured = capsys.readouterr()
    return rc, captured.out, captured.err


# ── check_lang（Stop）：systemMessage，只給人看、不續回合 ───────────────────────────

_FAIL_OPEN_BREADCRUMB = (
    "[check_lang] 無可判定文字（payload 無 last_assistant_message、逐字稿無 assistant 事件）⇒ 略過"
)


@pytest.mark.parametrize(
    ("text", "marker"),
    [
        ("안녕하세요 — 修復完成。", "韓文"),
        ("这个修复方案为 W0 设计。", "簡體中文"),
        ("ありがとう — 修復完成。", "日文"),
    ],
)
def test_check_lang_warns_via_system_message_with_rc0(tmp_path, text, marker):
    """非繁中 ⇒ rc=0 ＋ stdout 單一 JSON 的 `systemMessage`（不夾 additionalContext）。

    WHY：CC 只認 0／2；rc=1 被顯示成 hook error，而 rc=0 下 stderr 只進 debug log。提醒要被
    看到，只剩 stdout JSON 這條通道——這條測試對「靜默翻 rc」變異體必須是紅的。只用
    `systemMessage`（不是 additionalContext）是刻意的：Stop+additionalContext 會讓模型多跑
    一回合，語言提醒誤報時那是純噪音回合。

    兩條衍生鎖：① stdout 必須純 ASCII（`ensure_ascii=True`，中文以 \\uXXXX 跳脫）——
    stdout 重設為 UTF-8 的保護失效、遇 cp1252／cp950 管線時，直寫 CJK 會 UnicodeEncodeError
    而靜默失聲（platform_utils 約束②）；② 受話者是使用者（`systemMessage` 只給人看、模型
    讀不到），措辭要告訴人「怎麼辦」，不能對著讀不到的模型喊「請自我修正」。
    """
    payload = {
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "transcript_path": str(_transcript(tmp_path, text)),
    }
    result = _run("check_lang.py", payload)
    assert result.returncode == 0, result.stderr
    assert result.stdout.isascii(), result.stdout
    doc = _single_json(result.stdout)
    assert set(doc) == {"systemMessage"}, doc
    assert marker in doc["systemMessage"], doc
    assert "請要求模型改用繁體中文重述" in doc["systemMessage"], doc
    assert "自我修正" not in doc["systemMessage"], doc
    assert marker in result.stderr  # debug-log 留底（exit 0 下不呈現，僅供查）


def test_check_lang_clean_text_is_silent_rc0(tmp_path):
    """繁中乾淨文字 ⇒ rc=0 且 stdout 完全空白（沒有違規就不得出聲，否則每回合都吵）。"""
    payload = {
        "hook_event_name": "Stop",
        "transcript_path": str(_transcript(tmp_path, "全部使用繁體中文")),
    }
    result = _run("check_lang.py", payload)
    assert (result.returncode, result.stdout.strip()) == (0, "")
    assert _FAIL_OPEN_BREADCRUMB not in result.stderr  # 有文字可判定就不是 fail-open


def test_check_lang_reads_last_assistant_message_when_transcript_has_no_assistant(tmp_path):
    """DEF-200-449：資料源是 payload 的 `last_assistant_message`；逐字稿零 assistant 也要抓到。

    WHY：官方明載 Stop 當下逐字稿「不保證含本回合最後訊息」，`claude -p` 實測零 assistant
    事件。只讀逐字稿的版本在活體恆 fail-open（rc=0、無聲）——外觀與「全是繁中」完全相同，
    hook 從沒真正啟動過卻無人察覺。
    """
    payload = {
        "hook_event_name": "Stop",
        "stop_hook_active": False,
        "last_assistant_message": "안녕하세요",
        "transcript_path": str(_transcript(tmp_path, None)),
    }
    result = _run("check_lang.py", payload)
    assert result.returncode == 0, result.stderr
    assert "韓文" in _single_json(result.stdout)["systemMessage"]


def test_check_lang_without_message_and_without_assistant_event_is_silent(tmp_path):
    """兩個資料源都沒有可判定的文字 ⇒ fail-open：rc=0 且 stdout 空（不得亂報、不得崩潰）。

    WHY 還要 stderr 麵包屑：DEF-200-449 的教訓是「資料源缺席」的外觀與「回覆全是繁中」逐位元
    相同（rc=0、stdout 空），hook 從沒真正啟動過卻無人察覺。stderr 在 exit 0 下只進 debug
    log、不吵人，但出事時是唯一能把兩種「安靜」分開的證據。
    """
    payload = {
        "hook_event_name": "Stop",
        "transcript_path": str(_transcript(tmp_path, None)),
    }
    result = _run("check_lang.py", payload)
    assert (result.returncode, result.stdout.strip()) == (0, "")
    assert _FAIL_OPEN_BREADCRUMB in result.stderr, result.stderr


def test_check_lang_empty_payload_is_silent_and_leaves_the_breadcrumb():
    """連 transcript_path 都沒有（payload 為空物件）⇒ 同一條 fail-open 出口、同一句麵包屑。"""
    result = _run("check_lang.py", {})
    assert (result.returncode, result.stdout.strip()) == (0, "")
    assert _FAIL_OPEN_BREADCRUMB in result.stderr, result.stderr


def test_check_lang_payload_message_beats_a_stale_transcript(tmp_path):
    """payload 為準：逐字稿殘留的舊韓文，不得讓「本回合乾淨的最後訊息」被誤報。

    WHY：逐字稿非同步寫入、可能落後也可能含更早的訊息；`last_assistant_message` 才是本回合
    最後一則的權威。若實作退成「兩邊都掃」，舊的違規會在每個後續回合被反覆唸。
    """
    payload = {
        "hook_event_name": "Stop",
        "last_assistant_message": "已完成修復。",
        "transcript_path": str(_transcript(tmp_path, "안녕하세요")),
    }
    result = _run("check_lang.py", payload)
    assert (result.returncode, result.stdout.strip()) == (0, "")


def test_check_lang_is_not_clamped_by_stop_hook_active(tmp_path):
    """`systemMessage` 不續回合 ⇒ 不需要（也不該）夾 `stop_hook_active`。

    WHY：freshness 的 additionalContext 會讓模型多跑一回合，必須夾閂鎖防自燒額度；check_lang
    走 systemMessage，沒有迴圈風險。若有人把閂鎖抄過來，續跑回合內的非繁中回覆會無聲過關。
    """
    payload = {
        "hook_event_name": "Stop",
        "stop_hook_active": True,
        "last_assistant_message": "안녕하세요",
    }
    result = _run("check_lang.py", payload)
    assert result.returncode == 0, result.stderr
    assert "韓文" in _single_json(result.stdout)["systemMessage"]


# ── loc_budget_check（PostToolUse）：additionalContext，進模型 context、不續跑 ───────


def _warn_unparseable(mod, tmp_path, monkeypatch):
    (tmp_path / "target.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    return tmp_path / "target.py", "無法計價"


def _warn_over_tier_budget(mod, tmp_path, monkeypatch):
    (tmp_path / "target.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    monkeypatch.setattr(mod, "classify_file", lambda rel: ("data", 1), raising=True)
    return tmp_path / "target.py", "超 tier"


def _warn_over_absolute_limit(mod, tmp_path, monkeypatch):
    (tmp_path / "target.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    monkeypatch.setattr(mod, "ABSOLUTE_LIMIT", 1, raising=True)
    return tmp_path / "target.py", "絕對紅線"


def _warn_claude_md_band(mod, tmp_path, monkeypatch):
    (tmp_path / "CLAUDE.md").write_text("\n".join(f"l{i}" for i in range(390)), encoding="utf-8")
    monkeypatch.setattr(mod, "SPECIAL_FILES", {"CLAUDE.md": 400}, raising=True)
    return tmp_path / "CLAUDE.md", "預警閾值"


@pytest.mark.parametrize(
    "build",
    [_warn_unparseable, _warn_over_tier_budget, _warn_over_absolute_limit, _warn_claude_md_band],
)
def test_loc_budget_every_warn_site_is_rc0_and_still_speaks(build, tmp_path, monkeypatch, capsys):
    """四個提醒站點（無法計價／超 tier／超絕對紅線／CLAUDE.md 預警帶）⇒ rc=0 ＋ JSON 說話。

    WHY：ADR-XPLAT-013 §2.3——剛被寫壞或剛超標的檔若沒有任何訊號，等於零成本；rc=1 又被 CC
    顯示成 hook error。出聲必須落在 JSON 通道，事件名取 payload 原值（不符時 CC 整段丟掉，
    約束①）。severity 1 只是 helper 的內部值，不得流進結束碼。
    """
    mod = _load("loc_budget_check")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    target, marker = build(mod, tmp_path, monkeypatch)
    payload = {"hook_event_name": "PostToolUse", "tool_input": {"file_path": str(target)}}
    rc, out, err = _drive_main(mod, payload, monkeypatch, capsys)
    assert rc == 0
    ho = _single_json(out)["hookSpecificOutput"]
    assert ho["hookEventName"] == "PostToolUse"
    assert marker in ho["additionalContext"] and "WARN" in ho["additionalContext"], ho
    assert marker in err  # debug-log 留底


def test_loc_budget_clean_file_is_silent_rc0(tmp_path, monkeypatch, capsys):
    """沒超標 ⇒ rc=0 且 stdout 空（提醒只在真的有事時出聲）。"""
    mod = _load("loc_budget_check")
    (tmp_path / "ok.py").write_text("a = 1\n", encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_input": {"file_path": str(tmp_path / "ok.py")},
    }
    assert _drive_main(mod, payload, monkeypatch, capsys)[:2] == (0, "")


def test_loc_budget_block_stays_rc2(tmp_path, monkeypatch, capsys):
    """CLAUDE.md > 400 行仍是 rc=2 阻斷，且阻斷級不走 JSON 通道（ADR-SD08-001 硬線）。"""
    mod = _load("loc_budget_check")
    (tmp_path / "CLAUDE.md").write_text("\n".join(f"l{i}" for i in range(401)), encoding="utf-8")
    monkeypatch.setattr(mod, "PROJECT_ROOT", tmp_path, raising=True)
    monkeypatch.setattr(mod, "SPECIAL_FILES", {"CLAUDE.md": 400}, raising=True)
    payload = {
        "hook_event_name": "PostToolUse",
        "tool_input": {"file_path": str(tmp_path / "CLAUDE.md")},
    }
    rc, out, err = _drive_main(mod, payload, monkeypatch, capsys)
    assert (rc, out.strip()) == (2, "")
    assert "BLOCK" in err


# ── claude_md_freshness（Stop）：additionalContext，並夾 stop_hook_active ────────────


def _freshness_fixture(tmp_path: Path, *, drift: bool, lines: int = 10) -> tuple[Path, Path]:
    """合成 CLAUDE.md（可控行數）與假 snapshot 工具（drift=True 時 exit 1），不碰真實檔。"""
    claude = tmp_path / "CLAUDE.md"
    claude.write_text("\n".join(f"l{i}" for i in range(lines)), encoding="utf-8")
    tool = tmp_path / "snapshot_tool.py"
    tool.write_text(
        f"import sys\nprint('DRIFT', file=sys.stderr)\nsys.exit({1 if drift else 0})\n",
        encoding="utf-8",
    )
    return claude, tool


def _patched_freshness(tmp_path, monkeypatch, *, drift: bool, lines: int = 10):
    mod = _load("claude_md_freshness")
    claude, tool = _freshness_fixture(tmp_path, drift=drift, lines=lines)
    monkeypatch.setattr(mod, "CLAUDE_MD", claude, raising=True)
    monkeypatch.setattr(mod, "SNAPSHOT_TOOL", tool, raising=True)
    return mod


def test_freshness_drift_is_rc0_and_speaks_through_additional_context(
    tmp_path, monkeypatch, capsys
):
    """Snapshot 漂移 ⇒ rc=0 ＋ Stop additionalContext（模型可據以跑 snapshot_sync）。"""
    mod = _patched_freshness(tmp_path, monkeypatch, drift=True)
    payload = {"hook_event_name": "Stop", "stop_hook_active": False}
    rc, out, err = _drive_main(mod, payload, monkeypatch, capsys)
    assert rc == 0
    ho = _single_json(out)["hookSpecificOutput"]
    assert ho["hookEventName"] == "Stop"
    assert "漂移" in ho["additionalContext"], ho
    assert "漂移" in err  # debug-log 留底


def test_freshness_drift_is_clamped_while_a_stop_hook_continuation_is_running(
    tmp_path, monkeypatch, capsys
):
    """`stop_hook_active` 為真 ⇒ 不再發射（stdout 空）、rc 仍 0、stderr 仍留底。

    WHY：Stop+additionalContext 會讓模型多跑一回合，那一回合結束又觸發 Stop；不夾住就是
    自己燒額度（check_claim_provenance 實測：一個 prompt 9 次 Stop、9 則零內容 assistant）。
    """
    mod = _patched_freshness(tmp_path, monkeypatch, drift=True)
    payload = {"hook_event_name": "Stop", "stop_hook_active": True}
    rc, out, err = _drive_main(mod, payload, monkeypatch, capsys)
    assert (rc, out.strip()) == (0, "")
    assert "漂移" in err


def test_freshness_no_drift_is_silent_rc0(tmp_path, monkeypatch, capsys):
    """沒有漂移 ⇒ rc=0 且 stdout 空。"""
    mod = _patched_freshness(tmp_path, monkeypatch, drift=False)
    rc, out, _err = _drive_main(mod, {"hook_event_name": "Stop"}, monkeypatch, capsys)
    assert (rc, out.strip()) == (0, "")


def test_freshness_oversized_claude_md_stays_rc2(tmp_path, monkeypatch, capsys):
    """CLAUDE.md > 400 行仍是 rc=2（Stop exit 2＝阻止停止），阻斷級不走 JSON 通道。"""
    mod = _patched_freshness(tmp_path, monkeypatch, drift=True, lines=401)
    rc, out, err = _drive_main(mod, {"hook_event_name": "Stop"}, monkeypatch, capsys)
    assert (rc, out.strip()) == (2, "")
    assert "BLOCK" in err


def test_the_json_is_flushed_when_a_real_process_exits(tmp_path):
    """真行程：`sys.exit(main())` 之後 atexit 仍要把 JSON 寫出（in-process 測試看不到這一段）。

    WHY：`emit_to_model` 只累積、不輸出，真正的輸出由 atexit 單點 flush（platform_utils 約束
    ③）。若有人把 hook 改成 `os._exit()` 或在 main() 裡提前結束，in-process 測試仍綠，但
    活體提醒整個消失；只有跨行程的這一條抓得到。
    """
    claude, tool = _freshness_fixture(tmp_path, drift=True)
    hook = str(HOOKS / "claude_md_freshness.py")
    wrapper = tmp_path / "wrapper.py"
    wrapper.write_text(
        "import importlib.util, sys\n"
        "from pathlib import Path\n"
        f"spec = importlib.util.spec_from_file_location('h', {hook!r})\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n"
        f"mod.CLAUDE_MD = Path({str(claude)!r})\n"
        f"mod.SNAPSHOT_TOOL = Path({str(tool)!r})\n"
        "sys.exit(mod.main())\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(wrapper)],
        input=json.dumps({"hook_event_name": "Stop", "stop_hook_active": False}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    ho = _single_json(result.stdout)["hookSpecificOutput"]
    assert ho["hookEventName"] == "Stop" and "漂移" in ho["additionalContext"], ho
