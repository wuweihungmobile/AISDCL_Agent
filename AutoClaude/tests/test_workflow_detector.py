"""WorkflowDetector 單元測試（AISDLC vs AISDLC_SDD 標記辨識）。"""
from autoclaude.execution.workflow_detector import WorkflowDetector, WorkflowType


def test_detector_unknown_path():
    d = WorkflowDetector()
    assert d.detect("/nonexistent/path/xyz") == WorkflowType.UNKNOWN


def test_detector_aisdlc_sdd(tmp_path):
    (tmp_path / "docs_template" / "sdd").mkdir(parents=True)
    d = WorkflowDetector()
    assert d.detect(str(tmp_path)) == WorkflowType.AISDLC_SDD


def test_detector_aisdlc(tmp_path):
    (tmp_path / "agent" / "core").mkdir(parents=True)
    d = WorkflowDetector()
    assert d.detect(str(tmp_path)) == WorkflowType.AISDLC


def test_detector_sdd_takes_priority(tmp_path):
    (tmp_path / "docs_template" / "sdd").mkdir(parents=True)
    (tmp_path / "agent" / "core").mkdir(parents=True)
    d = WorkflowDetector()
    assert d.detect(str(tmp_path)) == WorkflowType.AISDLC_SDD
