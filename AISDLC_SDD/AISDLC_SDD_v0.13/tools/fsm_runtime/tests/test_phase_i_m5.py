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
