"""Phase I M5 / ACT-070~072 — Fleet parallel autonomy tests.

ACT-070 track-dimensioned state key + sandbox namespacing；
ACT-071 SpecDependencyLock 全域鎖序防死鎖 + MergeArbiter textual/semantic + join。
ACT-072 的 parametric FLEET_FSM.tla 由 run_tlc.sh 驗（CI/本機 java）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


# ==================== ACT-070：track 維度 state key ====================

def test_track_state_path_single_vs_multi():
    from tools.fsm_runtime.state_loader import track_state_path, _default_state_path
    # 單軌（track_id=None）向後相容
    assert track_state_path("proj") == _default_state_path("proj")
    # 多軌各自獨立檔
    pa = track_state_path("proj", "feat-a")
    pb = track_state_path("proj", "feat-b")
    assert pa != pb
    assert pa.name == "FSM-STATE-proj-feat-a.yaml"


# ==================== R38：_sanitize_component 跨平台淨化強化 ====================
# DEF-101 系列同缺陷類別姊妹未覆蓋位置：project（project_from_env，讀 SDD_PROJECT
# 環境變數）與 track_id（TrackRegistry.register，外部可控）皆流入 track_state_path
# 組出 FSM-STATE-{project}-{track_id}.yaml，此檔是 FSM 治理閉環的 SSOT 狀態檔。

def test_sanitize_component_strips_windows_forbidden_chars():
    from tools.fsm_runtime.state_loader import _sanitize_component
    for ch in '<>:"|?*\\':
        sanitized = _sanitize_component(f"proj{ch}name")
        assert ch not in sanitized, f"未淨化禁用字元 {ch!r}：{sanitized!r}"


def test_sanitize_component_strips_control_chars():
    from tools.fsm_runtime.state_loader import _sanitize_component
    for code in list(range(0x00, 0x20)) + [0x7F]:
        ch = chr(code)
        sanitized = _sanitize_component(f"proj{ch}name")
        assert ch not in sanitized, f"未淨化控制字元 {code:#x}：{sanitized!r}"


def test_sanitize_component_escapes_reserved_device_names():
    from tools.fsm_runtime.state_loader import _sanitize_component
    for name in ("CON", "PRN", "AUX", "NUL", "COM1", "COM9", "LPT1", "LPT9", "con", "Com3"):
        sanitized = _sanitize_component(name)
        assert sanitized.startswith("_"), f"未攔下保留裝置名 {name!r}：{sanitized!r}"


def test_sanitize_component_does_not_flag_non_reserved_names():
    from tools.fsm_runtime.state_loader import _sanitize_component
    for name in ("CONSOLE", "PRINTER", "COM10", "LPTX", "hello"):
        sanitized = _sanitize_component(name)
        assert sanitized == name


def test_sanitize_component_neutralizes_path_traversal():
    from tools.fsm_runtime.state_loader import _sanitize_component
    # 路徑分隔符已被淨化為 "_"，不再構成多層路徑
    assert "/" not in _sanitize_component("../../etc/passwd")
    assert "\\" not in _sanitize_component("..\\..\\windows\\system32")
    # 純句點片段（穿越 token 本身）被 rstrip(" .") 整段吃光，回退安全預設值，
    # 不殘留任何具穿越意義的字面 ".."／"."
    assert _sanitize_component("..") == "untitled"
    assert _sanitize_component(".") == "untitled"
    assert _sanitize_component("...") == "untitled"


def test_sanitize_component_truncates_overlong_strings():
    from tools.fsm_runtime.state_loader import _sanitize_component, _MAX_COMPONENT_LEN
    sanitized = _sanitize_component("A" * 5000)
    assert len(sanitized) <= _MAX_COMPONENT_LEN


def test_sanitize_component_reserved_name_padding_bypass_regression():
    """R38 四方複審 SD bug-injection 揪出的順序缺口回歸鎖。

    舊實作順序為「淨化禁用字元 → 保留裝置名檢查 → 截斷 → 第二次獨立 rstrip」：
    保留名檢查發生在截斷之前，若輸入是「保留名 + 大量空格（非句點）+ 一個不會
    被 rstrip(" .") 剝除的字元」且總長超過 `_MAX_COMPONENT_LEN`，截斷前 rstrip
    因結尾非空白不觸發、保留名檢查因此誤判「不是保留名」而放行；截斷把那個
    阻擋字元切掉後，第二次 rstrip 才把露出的空格清除，卻不再重跑保留名檢查，
    讓保留名裸露輸出（guard 被繞過）。修復後「淨化 → 截斷 → 最終 rstrip →
    保留名檢查」只執行一輪，必須正確攔下。
    """
    from tools.fsm_runtime.state_loader import _sanitize_component

    for reserved in ("CON", "PRN", "AUX", "NUL", "COM1"):
        padded = reserved + " " * 77 + "X"  # 總長 81 > _MAX_COMPONENT_LEN(80)
        sanitized = _sanitize_component(padded)
        assert sanitized.startswith("_"), (
            f"padding-bypass 未被攔下：{reserved!r} -> {sanitized!r}"
        )

    assert _sanitize_component("CON" + " " * 77 + "X") == "_CON"


def test_track_state_path_survives_hostile_project_and_track_id(tmp_path):
    """組合驗證：即便 project/track_id 同時夾帶禁用字元/保留名/穿越/超長，
    track_state_path 產生的最終路徑仍是單層平坦檔名，落在 DEFAULT_STATE_DIR 下
    （不會逃逸出目錄，也不會拋例外）。"""
    from tools.fsm_runtime import state_loader as sl
    hostile_project = 'CON<>:"|?*' + "X" * 300
    hostile_track = "../../etc/passwd"
    p = sl.track_state_path(hostile_project, hostile_track)
    assert p.parent == sl.DEFAULT_STATE_DIR
    assert p.name.startswith("FSM-STATE-")
    for ch in '<>:"|?*\\':
        assert ch not in p.name


def test_track_state_isolation(tmp_path):
    from tools.fsm_runtime.state_loader import load_track_state, save_state
    # 兩軌獨立狀態，互不污染
    import tools.fsm_runtime.state_loader as sl
    orig = sl.DEFAULT_STATE_DIR
    sl.DEFAULT_STATE_DIR = tmp_path
    try:
        a = load_track_state("proj", "a")
        a.root["current_state"] = "IMPLEMENTATION"
        save_state(a)
        b = load_track_state("proj", "b")
        b.root["current_state"] = "SPEC_DRAFTING"
        save_state(b)
        a2 = load_track_state("proj", "a")
        assert a2.current == "IMPLEMENTATION"  # 未被 b 污染
    finally:
        sl.DEFAULT_STATE_DIR = orig


def test_sandbox_track_namespacing():
    from tools.fsm_runtime.sandbox_runner import track_container_name, track_port
    assert track_container_name("app", "a") != track_container_name("app", "b")
    assert track_container_name("app", None) == "sdd-app"
    # port 決定性、不同 track 不同（高機率）
    assert track_port(8000, None) == 8000
    assert track_port(8000, "a") != track_port(8000, "b")
    assert track_port(8000, "a") == track_port(8000, "a")  # 確定性


# ==================== ACT-070/071：TrackRegistry ====================

def test_track_registry():
    from tools.fsm_runtime.fleet_orchestrator import TrackRegistry
    reg = TrackRegistry("proj")
    reg.register("a"); reg.register("b")
    assert len(reg.active()) == 2
    reg._tracks["a"].status = "merged"
    assert len(reg.active()) == 1


# ==================== ACT-071：全域鎖序防死鎖 ====================

def test_spec_dependency_lock_mutex():
    from tools.fsm_runtime.fleet_orchestrator import SpecDependencyLock
    lock = SpecDependencyLock()
    ok, conf = lock.acquire_all("track-a", ["FRD-1", "SRD-2"])
    assert ok and not conf
    # 另一軌要同一把鎖 → 衝突，all-or-nothing 不取
    ok2, conf2 = lock.acquire_all("track-b", ["SRD-2", "FRD-9"])
    assert not ok2 and "SRD-2" in conf2
    assert lock.holder("FRD-9") is None  # 未部分持有
    # a 釋放後 b 可取得
    lock.release_all("track-a")
    ok3, _ = lock.acquire_all("track-b", ["SRD-2", "FRD-9"])
    assert ok3


def test_global_lock_ordering_no_circular_wait():
    from tools.fsm_runtime.fleet_orchestrator import SpecDependencyLock
    # 經典死鎖場景：a 想要 {X,Y}、b 想要 {Y,X}。全域排序 + all-or-nothing
    # 保證不會「a 持 X 等 Y、b 持 Y 等 X」的循環等待。
    lock = SpecDependencyLock()
    ok_a, _ = lock.acquire_all("a", ["X", "Y"])
    ok_b, conf_b = lock.acquire_all("b", ["Y", "X"])
    assert ok_a is True
    assert ok_b is False           # b 整批失敗（不部分持有）→ 無循環等待
    assert lock.held_by("a") == {"X", "Y"}
    assert lock.held_by("b") == set()


# ==================== ACT-071：Merge Arbitration ====================

def test_merge_arbitration_clean():
    from tools.fsm_runtime.fleet_orchestrator import arbitrate_merge
    r = arbitrate_merge("a")
    assert r.verdict == "clean" and r.target_state == "RELEASE_READY"


def test_merge_arbitration_textual_to_implementation():
    from tools.fsm_runtime.fleet_orchestrator import arbitrate_merge
    r = arbitrate_merge("a", textual_conflicts=["src/util.py"])
    assert r.verdict == "textual" and r.target_state == "IMPLEMENTATION"


def test_merge_arbitration_semantic_to_audit():
    from tools.fsm_runtime.fleet_orchestrator import arbitrate_merge
    r = arbitrate_merge("a", textual_conflicts=["src/util.py"],
                        semantic_conflicts=["docs/02_architecture/api/openapi.yaml"])
    # semantic 優先於 textual
    assert r.verdict == "semantic" and r.target_state == "SPEC_AUDIT"


def test_classify_conflict_paths():
    from tools.fsm_runtime.fleet_orchestrator import classify_conflict_paths
    sem, txt = classify_conflict_paths([
        "src/handler.py", "docs/openapi.yaml", "README.md", "spec/INV-3.md",
    ])
    assert "docs/openapi.yaml" in sem and "spec/INV-3.md" in sem
    assert "src/handler.py" in txt and "README.md" in txt


def test_parallel_track_join():
    from tools.fsm_runtime.fleet_orchestrator import TrackRegistry, all_joined
    reg = TrackRegistry("proj")
    reg.register("a"); reg.register("b")
    assert not all_joined(reg)
    reg._tracks["a"].status = "joined"
    reg._tracks["b"].status = "merged"
    assert all_joined(reg)
