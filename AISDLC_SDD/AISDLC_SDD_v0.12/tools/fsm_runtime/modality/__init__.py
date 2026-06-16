"""Multimodal Spec validation adapters (ACT-031, Phase F M3-M4).

Adapters convert non-textual artifacts (UI mockup / OpenAPI / DB schema /
C4 diagram) into structured signatures, then verify them against textual
specs (FRD / SRD).

LLM Backend abstraction lets the same adapter run against:
  - session backend (default, zero-cost local parsing)
  - claude-api backend (vision-capable, opt-in)
  - minimax backend (drop-in placeholder, OPEN-F.3 RESOLVED reserve slot)

Public sub-modules:
  llm_backend          — backend Protocol + 3 implementations
  ui_adapter           — D-31.2 UI mockup ↔ FRD AC
  api_ui_adapter       — D-31.3 OpenAPI endpoint ↔ UI form
  db_schema_adapter    — D-31.4 DB schema ↔ FRD data model
  c4_adapter           — D-31.5 C4 component ↔ SRD module
"""
from __future__ import annotations
