"""FileTranslationLearningSink — ITranslationLearningSink 檔案實作（improving_60, adapter ≤400）。

沿用 FileRtmFeedbackSource/FileRtmSink 先例（A 軌 File-only，無 PG 後端）：
  寫出：record_proposal → PROPOSALS-{project}.jsonl（append-only，跨 session 累積）
  讀回：list_proposals  ← PROPOSALS-{project}.jsonl（per-line fail-soft）

fail-soft 紀律（提議為輔助諮詢功能，絕不阻斷主流程）：
  目錄不存在自動建立；讀回時檔案不存在 / JSON 畸形 / 非 dict 一律回空、不 raise；
  read 採 per-line fail-soft（畸形行跳過，不丟整檔）。

project 基名消毒與 FileRtmFeedbackSource._sanitize 對稱，防 project 名挾帶路徑穿越
（../、絕對路徑）寫到 / 讀到 base_dir 外的檔。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ...core.ports.translation_learning import (
    ITranslationLearningSink,
    TranslationProposal,
)

logger = logging.getLogger("autoclaude.infra.translation_learning")


class FileTranslationLearningSink(ITranslationLearningSink):
    """轉譯策略提議落地（append-only JSONL；符合 ITranslationLearningSink Protocol）。"""

    def __init__(self, base_dir: str) -> None:
        self._base = Path(base_dir)

    def _path(self, project: str) -> Path:
        return self._base / f"{_sanitize(f'PROPOSALS-{project}')}.jsonl"

    def record_proposal(self, project: str, proposal: TranslationProposal) -> None:
        """append 一筆 proposed 提議（fail-soft：寫入失敗僅 warn，不阻斷主流程）。"""
        target = self._path(project)
        try:
            self._base.mkdir(parents=True, exist_ok=True)
            line = json.dumps(
                {
                    "at_id": proposal.at_id,
                    "failing_runs": proposal.failing_runs,
                    "total_runs": proposal.total_runs,
                    "rationale": proposal.rationale,
                    "status": proposal.status,
                },
                ensure_ascii=False,
            )
            with target.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as exc:  # noqa: BLE001 — fail-soft（諮詢功能不得阻斷）
            logger.warning("record_proposal fail-soft for %s: %s", project, exc)

    def list_proposals(self, project: str) -> tuple[TranslationProposal, ...]:
        """讀回既有提議（最舊→最新）；fail-soft 回 ()。"""
        target = self._path(project)
        try:
            if not target.is_file():
                return ()
            out: list[TranslationProposal] = []
            for raw in target.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line:
                    continue
                try:
                    doc = json.loads(line)
                except json.JSONDecodeError:
                    continue  # per-line fail-soft：畸形行跳過，不丟整檔
                if not isinstance(doc, dict) or "at_id" not in doc:
                    continue
                out.append(TranslationProposal(
                    at_id=str(doc.get("at_id", "")),
                    failing_runs=int(doc.get("failing_runs", 0)),
                    total_runs=int(doc.get("total_runs", 0)),
                    rationale=str(doc.get("rationale", "")),
                    status=str(doc.get("status", "proposed")),
                ))
            return tuple(out)
        except Exception as exc:  # noqa: BLE001 — fail-soft
            logger.warning("list_proposals fail-soft for %s: %s", project, exc)
            return ()


def _sanitize(name: str) -> str:
    """與 FileRtmFeedbackSource._sanitize 對稱：報告基名消毒，防路徑穿越。

    與先例完全對齊：去除前後 `.`/`_`（防 `.`/`..` 起頭挾帶）並提供空字串兜底。
    本檔基名恆有固定前綴 `PROPOSALS-`，理論上不會空/dot-起頭，兜底為防禦冗餘。
    """
    cleaned = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name)
    return cleaned.strip("._") or "proposals-report"


__all__ = ["FileTranslationLearningSink"]
