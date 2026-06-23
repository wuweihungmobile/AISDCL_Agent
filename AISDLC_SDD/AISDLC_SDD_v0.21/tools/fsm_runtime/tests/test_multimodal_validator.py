# enforces (governance rules): R-9.13
"""ACT-031 Phase F M4 D-31.15: tests for multimodal validator + 4 adapters.

Covers:
  - LLM Backend abstraction (Protocol + 3 backends)
  - 4 modality adapters (UI, API↔UI, DB Schema, C4)
  - Unified multimodal_validator entry
  - Acceptance scenarios A-31.1 ~ A-31.9
  - 3-backend regression (A-31.8)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.fsm_runtime import multimodal_validator as mv
from tools.fsm_runtime.modality import (
    api_ui_adapter,
    c4_adapter,
    db_schema_adapter,
    llm_backend as bk_mod,
    ui_adapter,
)


# ─────────────────────────────────────────────
# Fixtures (filesystem layout under tests/fixtures/multimodal/)
# ─────────────────────────────────────────────
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "multimodal"
FIXTURE_DOCS = FIXTURE_ROOT / "docs"
FIXTURE_DOCS_NO_EMAIL = FIXTURE_ROOT / "docs_no_email"


@pytest.fixture
def session_backend():
    return bk_mod.ClaudeCodeSessionBackend()


@pytest.fixture
def media_root(tmp_path: Path) -> Path:
    """Symlink-free copy of the fixture media tree so adapters can find it."""
    return FIXTURE_DOCS / "99_media"


# ─────────────────────────────────────────────
# Backend abstraction
# ─────────────────────────────────────────────
class TestBackends:
    def test_factory_default_session(self, monkeypatch):
        monkeypatch.delenv("SDD_MULTIMODAL_BACKEND", raising=False)
        bk = bk_mod.get_backend()
        assert bk.name == "session"
        assert isinstance(bk, bk_mod.ClaudeCodeSessionBackend)

    def test_factory_env_selection(self, monkeypatch):
        monkeypatch.setenv("SDD_MULTIMODAL_BACKEND", "claude-api")
        bk = bk_mod.get_backend()
        assert bk.name == "claude-api"

    def test_factory_unknown_raises(self):
        with pytest.raises(ValueError):
            bk_mod.get_backend("nope")

    def test_list_backends(self):
        names = bk_mod.list_backends()
        assert set(names) >= {"session", "claude-api", "minimax", "mock", "local"}

    def test_claude_api_stub_raises(self):
        bk = bk_mod.ClaudeAPIBackend()
        with pytest.raises(NotImplementedError):
            bk.extract_widget_tree(Path("/tmp/x.png"))

    def test_minimax_stub_raises(self):
        bk = bk_mod.MinimaxAPIBackend()
        with pytest.raises(NotImplementedError):
            bk.extract_widget_tree(Path("/tmp/x.png"))

    # approach 4-1 — 高擬真本地 Mock：確定性、零外連
    def test_mock_backend_canned_deterministic(self):
        bk = bk_mod.MockBackend()
        tree = bk_mod.WidgetTree(source="canned", widgets=[
            bk_mod.WidgetSignature(kind="button", name="登入"),
        ])
        bk.set_canned(tree=tree)
        # 多次呼叫回傳一致；不論輸入 artifact 路徑
        assert bk.extract_widget_tree(Path("/nonexistent/a.png")) is tree
        assert bk.extract_widget_tree(Path("/other/b.html")) is tree
        res = bk.compare_widgets_to_ac(tree, "需要「登入」按鈕")
        assert res.consistent and res.backend_name == "mock"

    def test_mock_backend_default_empty(self):
        bk = bk_mod.get_backend("mock")
        assert bk.name == "mock"
        tree = bk.extract_widget_tree(Path("/whatever.html"))
        assert tree.widgets == []

    # approach 4-2 — 地端 LLM：預設 OFF、不可達拋清楚錯誤（不靜默退化）
    def test_local_backend_registered_and_configurable(self, monkeypatch):
        monkeypatch.setenv("SDD_MULTIMODAL_BACKEND", "local")
        bk = bk_mod.get_backend()
        assert bk.name == "local"

    def test_local_backend_unreachable_raises(self, tmp_path):
        # 指向必然關閉的埠 → 連線失敗應拋 RuntimeError（清楚指示，不靜默）
        art = tmp_path / "ui.html"
        art.write_text("<button>登入</button>", encoding="utf-8")
        bk = bk_mod.LocalOpenAIBackend(base_url="http://127.0.0.1:1", timeout=1.0)
        with pytest.raises(RuntimeError):
            bk.extract_widget_tree(art)

    def test_parse_widgets_json_lenient(self):
        raw = "```json\n[{\"kind\":\"button\",\"name\":\"登入\"},{\"name\":\"Email\"}]\n```"
        widgets = bk_mod._parse_widgets_json(raw)
        names = {w.name for w in widgets}
        assert names == {"登入", "Email"}
        # 壞 JSON → 空 list（不崩潰）
        assert bk_mod._parse_widgets_json("not json at all") == []

    def test_session_extract_html(self, session_backend, media_root):
        tree = session_backend.extract_widget_tree(media_root / "ui" / "login-screen.html")
        names_lower = {w.name.strip().lower() for w in tree.widgets}
        # email / password / 登入 should all be present in some widget signature
        assert any("email" in n for n in names_lower)
        assert any("password" in n or "密碼" in n for n in names_lower)
        assert any("登入" in n or "login" in n for n in names_lower)


# ─────────────────────────────────────────────
# UI adapter (D-31.2) + A-31.1 / A-31.2
# ─────────────────────────────────────────────
class TestUIAdapter:
    def test_a31_1_ui_positive(self, session_backend):
        rep = ui_adapter.validate_anchor(
            ac_text="用戶輸入 Email + 密碼，點擊「登入」後導向首頁",
            anchor_id="LoginScreen",
            backend=session_backend,
            media_root=FIXTURE_DOCS / "99_media",
        )
        assert rep.consistent is True, f"missing={rep.missing_widgets} error={rep.error}"
        assert rep.target_path is not None and rep.target_path.exists()
        assert rep.error is None

    def test_a31_2_ui_negative_missing_button(self, session_backend, tmp_path):
        # Use the no-button variant by symlinking to the negative fixture.
        media = tmp_path / "99_media" / "ui"
        media.mkdir(parents=True)
        (media / "login-screen.html").write_text(
            (FIXTURE_DOCS / "99_media" / "ui" / "login-screen-no-button.html").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        rep = ui_adapter.validate_anchor(
            ac_text="用戶輸入 Email + 密碼，點擊「登入」後導向首頁",
            anchor_id="LoginScreen",
            backend=session_backend,
            media_root=tmp_path / "99_media",
        )
        assert rep.consistent is False
        # "登入" should be reported as missing.
        assert any("登入" in w for w in rep.missing_widgets), (
            f"expected 登入 in missing_widgets={rep.missing_widgets}"
        )

    def test_a31_7_missing_anchor_target(self, session_backend, tmp_path):
        # Empty media_root → target unresolvable.
        (tmp_path / "ui").mkdir()
        rep = ui_adapter.validate_anchor(
            ac_text="any AC text",
            anchor_id="DoesNotExist",
            backend=session_backend,
            media_root=tmp_path,
        )
        assert rep.error == "missing_anchor_target"
        assert rep.target_path is None
        assert rep.consistent is False


# ─────────────────────────────────────────────
# OpenAPI ↔ UI adapter (D-31.3) + A-31.3 / A-31.4
# ─────────────────────────────────────────────
class TestAPIUIAdapter:
    def test_a31_3_api_positive(self, session_backend, tmp_path):
        # Isolate the api_root so the broken auth-no-password.yaml fixture
        # doesn't shadow the positive one (rglob iteration is FS-dependent).
        api_root = tmp_path / "api"
        api_root.mkdir()
        (api_root / "auth.yaml").write_text(
            (FIXTURE_DOCS / "02_architecture" / "api" / "auth.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        ui_tree = session_backend.extract_widget_tree(
            FIXTURE_DOCS / "99_media" / "ui" / "login-screen.html"
        )
        rep = api_ui_adapter.validate_anchor(
            method="POST", path="/auth/login",
            ui_widgets=ui_tree,
            api_root=api_root,
            ac_text="login flow",
        )
        assert rep.consistent is True
        assert rep.error is None
        assert rep.yaml_path is not None and rep.yaml_path.name == "auth.yaml"

    def test_a31_4_api_negative_missing_password(self, session_backend, tmp_path):
        # Stage just the broken auth.yaml in an isolated api root.
        api_root = tmp_path / "api"
        api_root.mkdir()
        (api_root / "auth.yaml").write_text(
            (FIXTURE_DOCS / "02_architecture" / "api" / "auth-no-password.yaml").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        ui_tree = session_backend.extract_widget_tree(
            FIXTURE_DOCS / "99_media" / "ui" / "login-screen.html"
        )
        rep = api_ui_adapter.validate_anchor(
            method="POST", path="/auth/login",
            ui_widgets=ui_tree, api_root=api_root,
        )
        # auth-no-password.yaml only requires [email]; UI has both → consistent
        # for *missing_request_fields*. So we need the *opposite* check:
        # the broken case is when UI lacks a field that API requires. Build it.
        api2 = tmp_path / "api2"
        api2.mkdir()
        (api2 / "auth.yaml").write_text(
            (FIXTURE_DOCS / "02_architecture" / "api" / "auth.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        # UI without password
        ui_tree_no_pw = session_backend.extract_widget_tree(
            FIXTURE_DOCS / "99_media" / "ui" / "login-screen-no-button.html"
        )
        # Strip password from the tree to simulate UI gap on a required field.
        ui_tree_no_pw.widgets = [
            w for w in ui_tree_no_pw.widgets
            if "password" not in w.name.lower() and "密碼" not in w.name
        ]
        rep2 = api_ui_adapter.validate_anchor(
            method="POST", path="/auth/login",
            ui_widgets=ui_tree_no_pw, api_root=api2,
        )
        assert rep2.consistent is False
        assert "password" in rep2.missing_request_fields

    def test_api_anchor_unknown_endpoint(self, session_backend, tmp_path):
        api_root = tmp_path / "api"
        api_root.mkdir()
        rep = api_ui_adapter.validate_anchor(
            method="GET", path="/nope",
            ui_widgets=None, api_root=api_root,
        )
        assert rep.error == "missing_anchor_target"
        assert rep.consistent is False


# ─────────────────────────────────────────────
# DB Schema adapter (D-31.4) + A-31.5
# ─────────────────────────────────────────────
class TestDBAdapter:
    def test_a31_5_db_positive(self):
        rep = db_schema_adapter.validate_anchor(
            table_name="users",
            frd_text="使用者欄位 `email` `password` `created_at`",
            db_root=FIXTURE_DOCS / "07_design" / "db",
        )
        assert rep.consistent is True
        assert "email" in rep.columns
        assert rep.missing_columns == []

    def test_a31_5_db_negative_missing_email(self):
        rep = db_schema_adapter.validate_anchor(
            table_name="users",
            frd_text="使用者欄位 `email` `password`",
            db_root=FIXTURE_DOCS_NO_EMAIL / "07_design" / "db",
        )
        assert rep.consistent is False
        assert rep.error == "schema_mismatch"
        assert "email" in rep.missing_columns

    def test_db_anchor_missing_table(self, tmp_path):
        rep = db_schema_adapter.validate_anchor(
            table_name="ghost",
            frd_text="some text",
            db_root=tmp_path,
        )
        assert rep.error == "missing_anchor_target"


# ─────────────────────────────────────────────
# C4 Diagram adapter (D-31.5) + A-31.6
# ─────────────────────────────────────────────
class TestC4Adapter:
    def test_a31_6_c4_positive(self):
        srd_text = "本系統包含 OrderService 與 PaymentGateway 兩大元件。"
        rep = c4_adapter.validate_anchor(
            component="OrderService",
            srd_text=srd_text,
            c4_root=FIXTURE_DOCS / "02_architecture",
        )
        assert rep.consistent is True
        assert rep.matched_in_srd is True

    def test_a31_6_c4_orphan_component(self):
        rep = c4_adapter.validate_anchor(
            component="GhostService",
            srd_text="something",
            c4_root=FIXTURE_DOCS / "02_architecture",
        )
        assert rep.consistent is False
        assert rep.error == "orphan_component"

    def test_c4_srd_missing_reference(self):
        # Component exists in C4 but SRD has no mention.
        rep = c4_adapter.validate_anchor(
            component="PaymentGateway",
            srd_text="(SRD does not name this component)",
            c4_root=FIXTURE_DOCS / "02_architecture",
        )
        assert rep.consistent is False
        assert rep.error == "srd_missing_module_reference"


# ─────────────────────────────────────────────
# Unified validator (D-31.1) + A-31.7 / A-31.9
# ─────────────────────────────────────────────
class TestMultimodalValidator:
    def test_anchor_extraction(self):
        anchors = mv._extract_anchors(FIXTURE_ROOT / "frd-positive.md")
        modalities = sorted(a.modality for a in anchors)
        assert modalities == ["api", "db", "ui"]

    def test_validate_specs_all_consistent(self, session_backend):
        report = mv.validate_specs(
            [FIXTURE_ROOT / "frd-positive.md"],
            project_root=FIXTURE_ROOT,
            backend=session_backend,
        )
        assert report.consistent, [
            (o.anchor.modality, o.error, o.detail) for o in report.outcomes if not o.consistent
        ]
        assert report.issue_count == 0
        assert len(report.outcomes) == 3

    def test_a31_7_missing_anchor_via_validator(self, session_backend, tmp_path):
        # Stage a spec with an anchor but no UI artifact at the target path.
        spec = tmp_path / "frd.md"
        spec.write_text(
            "# FRD\n\nAC-X: anything.\n\n<!-- anchor:ui:NeverScreen -->\n",
            encoding="utf-8",
        )
        # project_root has empty docs/99_media.
        (tmp_path / "docs" / "99_media" / "ui").mkdir(parents=True)
        report = mv.validate_specs(
            [spec], project_root=tmp_path, backend=session_backend,
        )
        assert report.consistent is False
        assert report.outcomes[0].error == "missing_anchor_target"

    def test_a31_9_strict_mode_blocks_inconsistency(self, session_backend, tmp_path):
        """A-31.9: CI uses --strict, validator returns issue_count > 0 on negative."""
        spec = tmp_path / "frd.md"
        spec.write_text(
            "AC: 用戶輸入 Email 與密碼後點擊「登入」。\n\n"
            "<!-- anchor:ui:LoginScreen -->\n",
            encoding="utf-8",
        )
        # Stage broken UI
        (tmp_path / "docs" / "99_media" / "ui").mkdir(parents=True)
        (tmp_path / "docs" / "99_media" / "ui" / "login-screen.html").write_text(
            (FIXTURE_DOCS / "99_media" / "ui" / "login-screen-no-button.html").read_text(
                encoding="utf-8"
            ),
            encoding="utf-8",
        )
        report = mv.validate_specs([spec], project_root=tmp_path, backend=session_backend)
        assert report.issue_count >= 1
        # Verify report serialises cleanly (CI consumer)
        serial = report.to_dict()
        assert serial["issue_count"] >= 1
        assert serial["consistent"] is False


# ─────────────────────────────────────────────
# A-31.8 — 3-backend regression
# ─────────────────────────────────────────────
class TestBackendRegression:
    def test_a31_8_session_backend_succeeds(self, session_backend):
        report = mv.validate_specs(
            [FIXTURE_ROOT / "frd-positive.md"],
            project_root=FIXTURE_ROOT,
            backend=session_backend,
        )
        assert report.consistent is True
        assert report.backend_name == "session"

    def test_a31_8_claude_api_backend_surfaces_stub(self):
        bk = bk_mod.ClaudeAPIBackend()
        report = mv.validate_specs(
            [FIXTURE_ROOT / "frd-positive.md"],
            project_root=FIXTURE_ROOT,
            backend=bk,
        )
        # claude-api stub raises on extract; UI dispatch reports it as error.
        ui_outcomes = [o for o in report.outcomes if o.anchor.modality == "ui"]
        assert ui_outcomes, "expected at least one UI anchor"
        assert any(
            o.error and "backend_not_implemented" in o.error for o in ui_outcomes
        ), [o.error for o in ui_outcomes]
        assert report.backend_name == "claude-api"

    def test_a31_8_minimax_backend_surfaces_stub(self):
        bk = bk_mod.MinimaxAPIBackend()
        report = mv.validate_specs(
            [FIXTURE_ROOT / "frd-positive.md"],
            project_root=FIXTURE_ROOT,
            backend=bk,
        )
        ui_outcomes = [o for o in report.outcomes if o.anchor.modality == "ui"]
        assert any(
            o.error and "backend_not_implemented" in o.error for o in ui_outcomes
        )
        assert report.backend_name == "minimax"


# ─────────────────────────────────────────────
# SLV rule schema sanity (avoid regression on the 4 new rule files)
# ─────────────────────────────────────────────
class TestSLVRules:
    @pytest.fixture
    def rules_dir(self) -> Path:
        return Path(__file__).resolve().parents[3] / ".claude" / "skills" / "spec-logical-validator" / "rules"

    @pytest.mark.parametrize("rule_id", ["SLV-008", "SLV-009", "SLV-010", "SLV-011"])
    def test_rule_yaml_loads_and_proposed(self, rules_dir, rule_id):
        import yaml
        path = rules_dir / f"{rule_id}.yaml"
        assert path.exists(), f"{rule_id}.yaml missing"
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert doc["id"] == rule_id
        # Per Rule 9.11.3: M3/M4 multimodal rules ship as proposed (advisory).
        assert doc["trust_level"] == "proposed", (
            f"{rule_id} must be proposed at M3/M4; promote requires human review"
        )
        # blocks_scg must be False for proposed rules.
        assert doc.get("blocks_scg", False) is False
        # anchor_type required for multimodal rules.
        assert doc.get("anchor_type") in {"ui", "api", "db", "c4"}
