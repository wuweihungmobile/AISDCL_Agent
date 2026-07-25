"""共用 AST 呼叫點掃描器（`component_sanitizer_callsite_scan.py`）回歸測試——
R46 新增（DEF-101-378）：直接鎖住 BoolOp／IfExp 遞迴拆解與別名追蹤這兩項新邏輯的
鑑別力，避免只靠 repo-wide 整合掃描（目前現存呼叫點皆已淨化，找不到真實違規、
對新邏輯零鑑別力）造成新修復本身完全沒有測試保護。

WHY（Rule 9）：DEF-101-378 修的兩個盲區，原本就是「日常重構就可能無意間觸發、
非需要刻意規避構造的邊界案例」（v0.30 舊 docstring 語氣）——如果只驗證「掃過現有
程式碼零 offender」，一旦這兩個新函式本身寫錯（例如 BoolOp 遞迴接反、別名循環
偵測失效造成無窮迴圈），現有測試套件不會有任何一個測試失敗。故本檔直接對這兩個
攻擊形狀構造 fixture，證明「有 bug 就抓得到」。
"""
from __future__ import annotations

import ast
import os
import sys

HERE = os.path.dirname(__file__)
SDD_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))  # AISDLC_SDD/
sys.path.insert(0, os.path.join(SDD_ROOT, "scripts"))

from component_sanitizer_callsite_scan import (  # noqa: E402
    build_alias_map,
    find_offenders,
    iter_module_files,
    raw_risky_reference,
    risky_identifier_names,
)

_RISKY = frozenset({"rule_id", "ac_id", "subagent", "classification"})


def _parse_expr(source: str) -> ast.expr:
    """解析單一運算式字串（如 `"rule_id or 'default'"`）為 ast.expr。"""
    return ast.parse(source, mode="eval").body


# ---------------------------------------------------------------------------
# ① BoolOp／IfExp 遞迴拆解（DEF-101-378 盲區①）
# ---------------------------------------------------------------------------
class TestBoolOpAndIfExpRecursion:
    def test_boolop_first_operand_risky_is_detected(self):
        expr = _parse_expr("rule_id or 'default'")
        assert raw_risky_reference(expr, _RISKY) == "rule_id"

    def test_boolop_second_operand_risky_is_detected(self):
        """`a or b` 第二個 operand 才是風險識別字也要抓到（不只檢查第一個）。"""
        expr = _parse_expr("unrelated_var or ac_id")
        assert raw_risky_reference(expr, _RISKY) == "ac_id"

    def test_boolop_neither_operand_risky_is_none(self):
        expr = _parse_expr("foo or bar")
        assert raw_risky_reference(expr, _RISKY) is None

    def test_nested_boolop_is_recursively_resolved(self):
        """`a or b or c` 巢狀 BoolOp（ast 對 3+ 個 operand 的 or 仍是單一 BoolOp
        node，values 為列表，非巢狀二元樹——確認多 operand 情境同樣正確解析）。"""
        expr = _parse_expr("foo or bar or subagent")
        assert raw_risky_reference(expr, _RISKY) == "subagent"

    def test_ifexp_body_risky_is_detected(self):
        expr = _parse_expr("rule_id if rule_id else 'default'")
        assert raw_risky_reference(expr, _RISKY) == "rule_id"

    def test_ifexp_orelse_risky_is_detected(self):
        expr = _parse_expr("'x' if flag else classification")
        assert raw_risky_reference(expr, _RISKY) == "classification"

    def test_ifexp_neither_branch_risky_is_none(self):
        expr = _parse_expr("'a' if flag else 'b'")
        assert raw_risky_reference(expr, _RISKY) is None


# ---------------------------------------------------------------------------
# ② 有界別名追蹤（DEF-101-378 盲區②）
# ---------------------------------------------------------------------------
class TestAliasTracking:
    def test_direct_name_alias_is_resolved(self):
        tree = ast.parse("_renamed_ac_id = ac_id\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert alias_map.get("_renamed_ac_id") == "ac_id"

    def test_attribute_alias_is_resolved(self):
        tree = ast.parse("verdict_rule_id = patch.rule_id\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert alias_map.get("verdict_rule_id") == "rule_id"

    def test_multi_hop_chain_within_bound_is_resolved(self):
        """a=b, b=c, c=rule_id：三跳，落在 5 層上限內，應解析成功。"""
        tree = ast.parse("a = b\nb = c\nc = rule_id\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert alias_map.get("a") == "rule_id"

    def test_chain_at_exact_five_hop_bound_is_resolved(self):
        """R46 QA 一審揪出的鑑別力缺口：「最多解 5 層」的邊界值本身原本沒有
        任何測試鎖住精確值（把 range(5) 改成 range(3) 也全數通過）。本測試鎖住
        恰好 5 跳（a=b,b=c,c=d,d=e,e=rule_id）必須解析成功。"""
        tree = ast.parse("a = b\nb = c\nc = d\nd = e\ne = rule_id\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert alias_map.get("a") == "rule_id"

    def test_chain_beyond_five_hop_bound_is_not_resolved(self):
        """六跳（多一層）超過 5 層上限，不應解析——鎖住邊界值本身，防止未來
        重構誤植（如打錯成 range(3)/range(10)）而不被任何測試發現。"""
        tree = ast.parse("a = b\nb = c\nc = d\nd = e\ne = f\nf = rule_id\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert "a" not in alias_map

    def test_cycle_does_not_infinite_loop(self):
        """a=b, b=a 互為別名成環，不指向任何風險識別字——必須在有限步數內
        跳出（環偵測），不解析出任何結果，且不得掛住測試行程。"""
        tree = ast.parse("a = b\nb = a\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert "a" not in alias_map
        assert "b" not in alias_map

    def test_non_risky_alias_is_not_resolved(self):
        tree = ast.parse("x = totally_unrelated\n")
        alias_map = build_alias_map(tree, _RISKY)
        assert "x" not in alias_map

    def test_raw_risky_reference_uses_alias_map(self):
        expr = _parse_expr("_renamed_ac_id")
        alias_map = {"_renamed_ac_id": "ac_id"}
        assert raw_risky_reference(expr, _RISKY, alias_map) == "ac_id"

    def test_raw_risky_reference_without_alias_map_is_none_for_alias_name(self):
        """不傳 alias_map（或風險名單本身沒有這個別名）時，別名變數本身裸引用
        不該被誤判為風險——確保別名解析是『加法』，不改變既有『直接命中風險
        名單』的判斷語意。"""
        expr = _parse_expr("_renamed_ac_id")
        assert raw_risky_reference(expr, _RISKY, alias_map=None) is None


# ---------------------------------------------------------------------------
# ③ find_offenders 整合測試：直接構造 DEF-101-378 兩個盲區的真實攻擊形狀
# ---------------------------------------------------------------------------
class TestFindOffendersCatchesBothBlindSpots:
    def test_boolop_fallback_pattern_in_filename_fstring_is_caught(self, tmp_path):
        """`f"VERDICT-{rule_id or 'unknown'}.yaml"`——R46 修復前，_raw_risky_reference
        對 BoolOp 回傳 None，這個裸用完全偵測不到。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'def emit(rule_id):\n'
            '    return f"VERDICT-{rule_id or \'unknown\'}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert any("rule_id" in o for o in offenders), offenders

    def test_two_stage_alias_indirection_in_filename_fstring_is_caught(self, tmp_path):
        """`_renamed_ac_id = ac_id` 後 `f"...{_renamed_ac_id}...yaml"`——R46 修復前，
        AST 節點的 `.id` 是 `_renamed_ac_id`，跟風險名單裡的 `ac_id` 對不上，
        完全漏放（v0.30 舊 docstring 明確記載的盲區②真實案例）。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'def emit(ac_id):\n'
            '    _renamed_ac_id = ac_id\n'
            '    return f"STATE-{_renamed_ac_id}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert any("ac_id" in o for o in offenders), offenders

    def test_cross_function_same_alias_name_does_not_collide(self, tmp_path):
        """R46 SD 一審揪出的真實缺陷（跨函式變數名碰撞）：兩個函式各自把不同來源
        別名到同一個變數名 `x`——`f()` 裡 `x` 別名一個安全的 `record.path`；`g()`
        裡 `x` 別名真正的風險識別字 `rule_id`。修復前用單一 flat dict 攤平全檔，
        後解析到的 `g()` 賦值會覆蓋 `f()` 的判斷結果，導致 `f()` 被誤判為
        offender（假陽性）。本測試鎖住兩者互不干擾：`f()` 乾淨、`g()` 正確被抓到。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'def f(record):\n'
            '    x = record.path\n'
            '    return f"SAFE-{x}.yaml"\n'
            '\n'
            'def g(rule_id):\n'
            '    x = rule_id\n'
            '    return f"RISKY-{x}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert not any("SAFE" in o or ("sample.py:3" in o) for o in offenders), offenders
        assert any("rule_id" in o for o in offenders), offenders

    def test_later_function_safe_alias_does_not_mask_earlier_function_risky_alias(self, tmp_path):
        """R46 SD 一審揪出的更嚴重情境（假陰性）：`f()` 裡 `x` 別名真正的風險
        識別字 `rule_id`（應被抓到），`g()`（定義在 f() 之後）裡同名變數 `x`
        別名安全值——修復前 `ast.walk` 依序訪問，`g()` 較晚寫入同一個 flat dict
        會把 `f()` 的判斷結果洗掉，導致 `f()` 裡真正未淨化的別名完全漏放。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'def f(rule_id):\n'
            '    x = rule_id\n'
            '    return f"OUT-{x}.yaml"\n'
            '\n'
            'def g(record):\n'
            '    x = record.path\n'
            '    return f"OUT2-{x}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert any("rule_id" in o for o in offenders), offenders

    def test_class_body_scope_does_not_collide_with_outer_module_scope(self, tmp_path):
        """R46 SD 二審揪出的真實缺陷（同構於一審的跨函式碰撞，換成 class body vs
        外層模組層級）：`_direct_children_in_scope` 初版只把 `FunctionDef`/
        `AsyncFunctionDef` 當作用域邊界，遺漏 `ClassDef`——class body 內的別名
        賦值會被當成外層模組層級的一部分，跟 class 定義之後的同名模組層級賦值
        互相碰撞。本測試鎖住「class body 內真正未淨化的別名」（更嚴重的假陰性）
        必須被抓到，不受 class 定義之後的同名安全賦值影響。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'class Foo:\n'
            '    x = rule_id\n'
            '    _fn = f"{x}.yaml"\n'
            'x = safe_source\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert any("rule_id" in o for o in offenders), offenders

    def test_class_body_safe_usage_not_masked_by_outer_risky_same_name(self, tmp_path):
        """同一缺陷的假陽性面向：class body 內安全的別名用法，不該因為 class
        定義之後模組頂層剛好也用同名變數指向風險識別字而被誤判。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'class Foo:\n'
            '    x = safe_source\n'
            '    _fn = f"{x}.yaml"\n'
            'x = rule_id\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert offenders == [], offenders

    def test_sanitized_call_site_is_not_flagged(self, tmp_path):
        """已正確呼叫 _sanitize_component() 的呼叫點不該被誤判——正向對照組。"""
        f = tmp_path / "sample.py"
        f.write_text(
            'def emit(rule_id):\n'
            '    return f"VERDICT-{_sanitize_component(rule_id)}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert offenders == []

    def test_known_exemption_is_not_flagged(self, tmp_path):
        """`_KNOWN_EXEMPTIONS` 以檔名比對——用登記過的檔名（slv_generator.py）
        重現同款裸用不該被回報。"""
        f = tmp_path / "slv_generator.py"
        f.write_text(
            'def _fpl_path(fpl_id):\n'
            '    return f"{fpl_id}.yaml"\n',
            encoding="utf-8",
        )
        offenders = find_offenders([f])
        assert offenders == []

    def test_unrelated_clean_file_yields_no_offenders(self, tmp_path):
        f = tmp_path / "clean.py"
        f.write_text('def noop():\n    return 1\n', encoding="utf-8")
        assert find_offenders([f]) == []


def test_risky_identifier_names_is_non_empty():
    assert risky_identifier_names(), "風險名單為空——凍結清單可能被誤清空"


def test_iter_module_files_excludes_tests_and_pycache(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "y.py").write_text("y = 1\n", encoding="utf-8")
    (tmp_path / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "real_module.py").write_text("z = 1\n", encoding="utf-8")

    files = iter_module_files(tmp_path)
    assert [p.name for p in files] == ["real_module.py"]
