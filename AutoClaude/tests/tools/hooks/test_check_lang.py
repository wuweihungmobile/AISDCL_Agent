"""tools/hooks/check_lang.py 單元測試 — SD_09 W0 §4「驗證鏡子自身要被驗證」紀律。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
HOOK_SCRIPT = PROJECT_ROOT / "tools" / "hooks" / "check_lang.py"


def _make_transcript(tmp_path: Path, assistant_text: str) -> Path:
    """產一個最小 transcript.jsonl，含一則 assistant 訊息。"""
    transcript = tmp_path / "transcript.jsonl"
    events = [
        {"type": "user", "message": {"content": "你好"}},
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": assistant_text}],
            },
        },
    ]
    transcript.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in events),
        encoding="utf-8",
    )
    return transcript


def _run(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )


def _system_message(result: subprocess.CompletedProcess) -> str:
    """stdout 必須恰為『一個』JSON 物件（兩份相接＝CC parse 失敗＝兩則一起消失）。"""
    doc = json.loads(result.stdout)
    assert isinstance(doc, dict), result.stdout
    return doc["systemMessage"]


def test_pure_traditional_chinese_passes(tmp_path):
    """純繁中應 exit 0 且無 stderr 警示。"""
    transcript = _make_transcript(
        tmp_path, "已完成 Phase A 路徑修正，所有連結改至 AISDLC_v0.09 目錄。"
    )
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 0, f"stderr={result.stderr}"


def test_korean_triggers_warning(tmp_path):
    """含韓文應 exit 0，且 stdout 單一 JSON 的 systemMessage 含「韓文」標記。

    WHY（DEF-200-447）：CC 只認 exit 0／2，exit 1 會被顯示成 hook error；但 exit 0 下
    stderr 與純文字 stdout 只進 debug log（使用者與模型都看不到）。所以提醒必須走 stdout
    JSON——只釘 rc==0 的話，把 `return 1` 悄悄改成 `return 0` 也會綠（提醒整個消失）。
    """
    transcript = _make_transcript(tmp_path, "안녕하세요 — 修復完成。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 0, result.stderr
    assert "韓文" in _system_message(result)
    assert "韓文" in result.stderr  # debug-log 留底


def test_simplified_chinese_triggers_warning(tmp_path):
    """含簡體高頻字（这个为）應 exit 0，stdout 單一 JSON 的 systemMessage 含「簡體中文」。"""
    transcript = _make_transcript(tmp_path, "这个修复方案为 SD_09 W0 设计。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 0, result.stderr
    assert "簡體中文" in _system_message(result)
    assert "簡體中文" in result.stderr


def test_no_transcript_path_fail_open(tmp_path):
    """payload 缺 transcript_path → fail-open exit 0。"""
    result = _run({})
    assert result.returncode == 0


def test_japanese_hiragana_triggers_warning(tmp_path):
    """含日文 hiragana 應 exit 0，stdout 單一 JSON 的 systemMessage 含「日文」。"""
    transcript = _make_transcript(tmp_path, "ありがとう — 修復完成。")
    result = _run({"transcript_path": str(transcript)})
    assert result.returncode == 0, result.stderr
    assert "日文" in _system_message(result)
    assert "日文" in result.stderr


@pytest.mark.parametrize(
    ("text", "flag"),
    [
        # U+30FB「・」是繁中人名／外來語的分隔符，單獨出現不是日文。
        ("愛因斯坦・阿爾伯特說相對論", None),
        ("ありがとう", "日文"),
        # 片假名本體照報：「・」被排除，不等於「含 ・ 的整段文字都放行」。
        ("アインシュタイン・アルベルト", "日文"),
        # 排除範圍只有 U+30FB 一個碼位：緊鄰的 U+30FA「ヺ」與 U+30FC「ー」（長音符）仍報。
        ("ヺ", "日文"),
        ("ー", "日文"),
    ],
)
def test_katakana_middle_dot_alone_is_not_japanese(text, flag):
    """繁中人名分隔符「・」（U+30FB）不得被報成日文，真的日文仍要報。

    WHY：U+30FB 落在片假名區塊（U+30A0~U+30FF）內，舊判準 `[゠-ヿ]` 因此把「愛因斯坦・阿爾
    伯特」這類正常繁中報成日文。誤報會訓練使用者無視這則提醒（狼來了）——真的混入日文時
    反而漏看；所以排除要精確到單一碼位，而不是把整個片假名區塊從判準拿掉。
    """
    result = _run({"hook_event_name": "Stop", "last_assistant_message": text})
    assert result.returncode == 0, result.stderr
    if flag is None:
        assert result.stdout.strip() == "", result.stdout
        assert "日文" not in result.stderr
    else:
        assert result.stdout.strip(), f"{text!r} 應被報成{flag}，stdout 卻是空的"
        assert flag in _system_message(result)
