"""Router hook 覆蓋 lint 意圖鎖（DEF-43-008 / DEF-B）.

每個 case 編碼「為何此行為重要」（Rule 9）：lint 的價值＝機械守護「最新演化版宣告的 CC hook
event 必同時被根 router ``_HOOK_MAP`` 涵蓋且被根 settings wire」，取代「人工記得雙改根 settings
+ router」。故正例（不可達→硬閘擋）與負例（全可達→放行）對稱覆蓋，並鎖死「router 缺映射」「根
settings 缺 wire」「兩者皆缺」三種不可達來源——任一退化都會讓某版治理 hook 在 monorepo 根
session 下靜默失效卻無人察覺。
"""
from __future__ import annotations

import json
import os

from scripts import router_hook_coverage_lint as lint


# ── 純邏輯：unreachable_events ───────────────────────────────────────────────

def test_subset_all_reachable():
    """版本 event 全在 router ∩ 根 settings → 無不可達。"""
    three = {"SessionStart", "PreToolUse", "PostToolUse"}
    assert lint.unreachable_events(three, three, three) == []


def test_event_missing_in_router():
    """版本新增 Stop，但 router _HOOK_MAP 未映射 → Stop 不可達（即使根 settings 有 wire）。"""
    ver = {"SessionStart", "Stop"}
    router = {"SessionStart", "PreToolUse", "PostToolUse"}
    root = {"SessionStart", "Stop"}
    assert lint.unreachable_events(ver, router, root) == ["Stop"]


def test_event_missing_in_root_settings():
    """router 有映射 Stop，但根 settings 未 wire → Stop 仍不可達（二者缺一即不可達）。"""
    ver = {"SessionStart", "Stop"}
    router = {"SessionStart", "Stop"}
    root = {"SessionStart"}
    assert lint.unreachable_events(ver, router, root) == ["Stop"]


def test_event_missing_in_both():
    """router 與根 settings 皆無 → 不可達。"""
    ver = {"SessionStart", "UserPromptSubmit"}
    both = {"SessionStart"}
    assert lint.unreachable_events(ver, both, both) == ["UserPromptSubmit"]


# ── IO 解析 ─────────────────────────────────────────────────────────────────

# 根側 settings 的 hook command 須含 router basename 才被 router_wired_events 認可（DEF-43-012）。
_ROUTER_CMD = 'python "${CLAUDE_PROJECT_DIR}/.claude/hooks/sdd_hook_router.py" h'


def _write_settings(path: str, events: list[str], command: str = "x") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    hooks = {e: [{"hooks": [{"type": "command", "command": command}]}] for e in events}
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"hooks": hooks}, f)


def _write_router(path: str, events: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    items = ",\n".join(f'    "h{i}": ("h{i}.py", "{e}")' for i, e in enumerate(events))
    with open(path, "w", encoding="utf-8") as f:
        f.write("_HOOK_MAP = {\n" + items + ",\n}\n")


def test_settings_hook_events_parse(tmp_path):
    p = str(tmp_path / ".claude" / "settings.json")
    _write_settings(p, ["SessionStart", "PreToolUse"])
    assert lint.settings_hook_events(p) == {"SessionStart", "PreToolUse"}


def test_settings_hook_events_missing_file(tmp_path):
    """無 settings 檔 → 空集（不拋例外）。"""
    assert lint.settings_hook_events(str(tmp_path / "nope.json")) == set()


def test_router_mapped_events_parse(tmp_path):
    """ast 解析 _HOOK_MAP 取 event 名（tuple 第 2 元素），不執行 router。"""
    p = str(tmp_path / "sdd_hook_router.py")
    _write_router(p, ["SessionStart", "PreToolUse", "PostToolUse"])
    assert lint.router_mapped_events(p) == {"SessionStart", "PreToolUse", "PostToolUse"}


# ── router_wired_events：DEF-43-012 假綠縫意圖鎖 ─────────────────────────────

def test_router_wired_events_accepts_router_command(tmp_path):
    """command 含 sdd_hook_router.py → 該 event 算 router-wired（可達）。"""
    p = str(tmp_path / ".claude" / "settings.json")
    _write_settings(p, ["SessionStart", "PreToolUse"], command=_ROUTER_CMD)
    assert lint.router_wired_events(p) == {"SessionStart", "PreToolUse"}


def test_router_wired_events_rejects_non_router_command(tmp_path):
    """為何重要（DEF-43-012）：event 宣告卻 wire 到別的腳本 → 不算 router-wired，杜絕假綠。

    舊 settings_hook_events 僅取 keys 會誤判此 event 可達；router_wired_events 須回空集。
    移除 command 指向檢查（退回只取 keys）即此 case 紅。
    """
    p = str(tmp_path / ".claude" / "settings.json")
    _write_settings(p, ["SessionStart"], command="python some_other_hook.py")
    assert lint.router_wired_events(p) == set()
    # 對照：舊 keys-only 解析仍會把它當宣告了 SessionStart（證明兩函式語意確有別）
    assert lint.settings_hook_events(p) == {"SessionStart"}


def test_router_wired_events_missing_file(tmp_path):
    assert lint.router_wired_events(str(tmp_path / "nope.json")) == set()


def test_analyze_false_green_seam_caught(tmp_path):
    """整合鎖（DEF-43-012）：版本宣告 SessionStart、router 有映射，但根 settings 把該 event
    wire 到非 router 腳本 → analyze 須判不可達（治理 hook 實際不會經 router 觸發）。"""
    three = ["SessionStart", "PreToolUse", "PostToolUse"]
    repo = str(tmp_path)
    _write_router(
        os.path.join(repo, ".claude", "hooks", "sdd_hook_router.py"), three
    )
    # 根 settings 宣告了 SessionStart 卻 wire 到別的腳本（假綠來源）
    _write_settings(
        os.path.join(repo, ".claude", "settings.json"),
        ["SessionStart"],
        command="python not_the_router.py",
    )
    _write_settings(
        os.path.join(repo, "AISDLC_SDD_v0.20", ".claude", "settings.json"), ["SessionStart"]
    )
    res = lint.analyze(repo)
    assert res["unreachable"] == ["SessionStart"]


# ── analyze 整合（合成 monorepo 佈局）─────────────────────────────────────────

def _mk_monorepo(tmp_path, version: str, ver_events, router_events, root_events) -> str:
    """建假 monorepo：root .claude（router + settings）+ 版本目錄 .claude/settings。

    repo_root 回傳 tmp_path 自身（analyze 的 _monorepo_root fallback 會認 repo_root 內的 .claude）。
    """
    repo = str(tmp_path)
    _write_router(os.path.join(repo, ".claude", "hooks", "sdd_hook_router.py"), list(router_events))
    # 根 settings 須 wire 到 router（DEF-43-012）才算可達；版本 settings 只看宣告 keys。
    _write_settings(
        os.path.join(repo, ".claude", "settings.json"), list(root_events), command=_ROUTER_CMD
    )
    _write_settings(
        os.path.join(repo, version, ".claude", "settings.json"), list(ver_events)
    )
    return repo


def test_analyze_all_reachable(tmp_path):
    three = ["SessionStart", "PreToolUse", "PostToolUse"]
    repo = _mk_monorepo(tmp_path, "AISDLC_SDD_v0.20", three, three, three)
    res = lint.analyze(repo)
    assert res["latest"] == "AISDLC_SDD_v0.20"
    assert res["unreachable"] == []


def test_analyze_detects_unreachable(tmp_path):
    """版本宣告 Stop 但 router/root 未涵蓋 → analyze 回報不可達（DEF-B 本體）。"""
    repo = _mk_monorepo(
        tmp_path,
        "AISDLC_SDD_v0.20",
        ver_events=["SessionStart", "Stop"],
        router_events=["SessionStart", "PreToolUse", "PostToolUse"],
        root_events=["SessionStart", "PreToolUse", "PostToolUse"],
    )
    res = lint.analyze(repo)
    assert res["unreachable"] == ["Stop"]


def test_analyze_scans_only_latest(tmp_path):
    """只掃最新版（語意版本 v0.10 > v0.9）：舊版宣告 Stop 不影響，最新版乾淨 → 放行。"""
    three = ["SessionStart", "PreToolUse", "PostToolUse"]
    repo = _mk_monorepo(tmp_path, "AISDLC_SDD_v0.10", three, three, three)
    _write_settings(
        os.path.join(repo, "AISDLC_SDD_v0.9", ".claude", "settings.json"),
        ["SessionStart", "Stop"],  # 舊版有不可達 event，但非最新版 → 不檢
    )
    res = lint.analyze(repo)
    assert res["latest"] == "AISDLC_SDD_v0.10" and res["unreachable"] == []


def test_analyze_no_versions(tmp_path):
    res = lint.analyze(str(tmp_path))
    assert res["latest"] is None


# ── CLI 硬閘 ─────────────────────────────────────────────────────────────────

def test_main_clean_exits_zero(tmp_path, capsys):
    three = ["SessionStart", "PreToolUse", "PostToolUse"]
    repo = _mk_monorepo(tmp_path, "AISDLC_SDD_v0.20", three, three, three)
    assert lint.main([repo]) == 0
    assert "全部可達" in capsys.readouterr().out


def test_main_unreachable_exits_one(tmp_path, capsys):
    """不可達 event → 印 ::error:: + DEF-43-008 且 **exit 1**（硬閘，非 advisory）。

    為何重要：不可達治理 hook 是真正正確性破口（hook 靜默失效），須 fail-loud 阻擋 CI（Rule 12），
    與 gitignore advisory（exit 0）刻意不同。移除硬閘語意（改 return 0）即此 case 紅。
    """
    repo = _mk_monorepo(
        tmp_path, "AISDLC_SDD_v0.20",
        ["SessionStart", "Stop"], ["SessionStart"], ["SessionStart"],
    )
    assert lint.main([repo]) == 1
    err = capsys.readouterr().err
    assert "::error::" in err and "DEF-43-008" in err and "Stop" in err


def test_main_no_version_exits_nonzero(tmp_path, capsys):
    """AGT-12（R85）：定位不到任何演化版 ⇒ 硬閘非零。

    🔴 被訂正的原意圖逐字保留（訂正協議：禁止靜默覆寫）——本 case 原名
    ``test_main_no_version_exits_zero``，斷言 ``lint.main([str(tmp_path)]) == 0``
    且輸出含「略過」，即**把 fail-open 釘成契約**。

    為何原意圖是錯的：本 lint 守的是「LATEST 宣告的 CC hook event 是否可達」。定位不到
    LATEST 時它一個 event 都沒看過，回 0 等於宣稱「全部可達」——而下一個 case
    ``test_main_router_not_found_exits_one`` 的 docstring 逐字寫著「無法驗證＝不可放行，
    fail-loud」。**同一支檔同時住著這條紀律與它的反例，相隔兩行**，而測試全綠：
    有鎖在守假話，比沒有鎖更難看見。兩者是同一類「輸入不可用」，必須走同一個出口。
    """
    assert lint.main([str(tmp_path)]) == 1
    assert "::error::" in capsys.readouterr().err


def test_main_router_not_found_exits_one(tmp_path, capsys):
    """有版本但找不到根 router → 硬閘 exit 1（無法驗證＝不可放行，fail-loud）。"""
    repo = str(tmp_path)
    _write_settings(
        os.path.join(repo, "AISDLC_SDD_v0.20", ".claude", "settings.json"), ["SessionStart"]
    )
    # 不建 .claude/hooks/sdd_hook_router.py
    assert lint.main([repo]) == 1
    assert "::error::" in capsys.readouterr().err


# ── 真實 repo 回歸鎖 ─────────────────────────────────────────────────────────

def test_real_repo_latest_fully_reachable():
    """真實 repo 鎖：當前最新演化版宣告的 CC hook event 全部可達（router ∩ 根 settings）。

    為何重要：(1) 證 lint 對真實佈局不誤報；(2) 此鎖在未來某輪新版 settings.json 新增 CC hook
    event 卻忘改根 router/settings 時會轉紅（unreachable 非空），即 DEF-43-008 機械守護落地點。
    """
    # test 檔在 AISDLC_SDD/scripts/tests/ → 三層 dirname = AISDLC_SDD/
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    res = lint.analyze(repo_root)
    assert res["latest"] is not None
    assert not res.get("error"), res.get("error")
    assert res["unreachable"] == [], (
        f"最新版 {res['latest']} 有不可達 CC hook event：{res['unreachable']}"
    )
