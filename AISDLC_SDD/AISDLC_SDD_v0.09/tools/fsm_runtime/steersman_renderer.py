"""Phase H M6 / ACT-057 — Steersman Renderer.

把 DiagnosticAgent 的機讀 DiagnosticResult（外加 SPEC_AUDIT 的 SLV verdict）
轉成「人類舵手級」的交接訊息，落實 CLAUDE.md Rule 9.20.6：

  停機後，系統必須引導人類補上「AI 缺的工具 / 環境限制 / 修正後規格」，
  讓人類維持在「設計環境舵手」的高度，而非被降級成 bug 修碼員。

對應缺口：SDD_improving_Automation_08.md §G8。先前 DiagnosticResult 算得出
sub_type/category/rationale，卻從未進入 save_abort_report() — 人類只收到
「retry exhausted」。本模組補上 sub_type → 能力缺口 → 環境請求 的三段映射。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


# sub_type → (AI 缺什麼能力, 請哪個角色補什麼環境/工具/規格)
# 與 diagnostic.SUB_TYPES（ci_timeout/network_flap/rate_limit/spec_conflict/
# data_corruption/retry_exhausted/unknown）一一對應。
_CAPABILITY_GAP = {
    "spec_conflict": (
        "AI 缺「正確且自洽的規格」——目前的 AC 與 INV 相互矛盾，任何實作都無法同時滿足。",
        "sa-analyst",
        "請提供修正後的 AC（解除與 INV 的矛盾），或澄清此需求的真實意圖。",
    ),
    "data_corruption": (
        "AI 缺「完整且可解析的 FSM 狀態」——primary YAML 損毀，已嘗試 .bak 回復。",
        "human-operator",
        "請確認 .bak 是否可用，或提供最近一次有效的 CONTEXT-SNAPSHOT 以進入 RESUME_VERIFICATION。",
    ),
    "retry_exhausted": (
        "AI 缺「足夠的能力 / 預算 / 環境」——在既有條件下重試已達上限仍無法收斂。",
        "human-operator",
        "請提供更強的模型 / 缺失的工具 / 拆解任務範圍，或調整 budget 後再恢復。",
    ),
    "ci_timeout": (
        "AI 缺「穩定的 CI runner」——本屬 transient，但已逾自動復原界線。",
        "devops-engineer",
        "請確認 CI runner 健康狀態 / 重啟 runner，或提供可用的執行環境。",
    ),
    "network_flap": (
        "AI 缺「穩定的網路連線」——transient 連線抖動超出自動退避範圍。",
        "devops-engineer",
        "請確認網路 / DNS / proxy 設定，或提供離線可用的依賴鏡像。",
    ),
    "rate_limit": (
        "AI 缺「足夠的速率配額」——外部 API 持續 429 / throttled。",
        "human-operator",
        "請提高配額 / 提供備援金鑰，或同意延後重試。",
    ),
    "unknown": (
        "AI 缺「可辨識的根因」——無規則匹配，保守視為結構性問題。",
        "human-operator",
        "請人工判讀 abort 上下文，補充缺失的工具或環境限制後再恢復。",
    ),
}

_DEFAULT_GAP = _CAPABILITY_GAP["unknown"]


@dataclass
class SteersmanMessage:
    sub_type: str
    category: str
    capability_gap: str
    target_role: str
    environment_request: str
    contradiction: Optional[str]
    confidence: float
    localization: Optional[str] = None   # Phase K M-K3 / ACT-086：因果定位（advisory）

    def to_markdown(self) -> str:
        halt = (
            "🛑 系統已**優雅停機**（已證明非無限重試，token 已保全）。"
            if self.category == "structural"
            else "⏸️ 系統已停機等待人工（transient，已逾自動復原界線）。"
        )
        contradiction_block = (
            f"\n【具體矛盾】{self.contradiction}\n" if self.contradiction else ""
        )
        localization_block = (
            f"\n{self.localization.rstrip()}\n" if self.localization else ""
        )
        return (
            f"## 🧭 舵手交接（Steersman Handoff）\n\n"
            f"{halt}\n\n"
            f"【根因分類】`{self.sub_type}`（{self.category}"
            f"{'，不可自動修復' if self.category == 'structural' else '，可 transient 復原但已超界'}）"
            f"／信心 {self.confidence:.2f}\n"
            f"{contradiction_block}\n"
            f"【你是舵手，不是修碼員】系統缺的不是「再試一次」，而是：\n"
            f"  👉 **{self.capability_gap}**\n"
            f"  👉 請 **{self.target_role}**：{self.environment_request}\n\n"
            f"{localization_block}"
            f"【恢復路徑】補上上述環境/規格後，輸入「確認恢復」→ 進入 `RESUME_VERIFICATION`。\n"
        )


def render_steersman(
    diagnostic,
    *,
    slv_contradiction: Optional[str] = None,
    localization: Optional[str] = None,
) -> SteersmanMessage:
    """Build a SteersmanMessage from a DiagnosticResult (+ optional SLV verdict).

    Args:
        diagnostic: a diagnostic.DiagnosticResult (or any object exposing
            sub_type / category / confidence / spec_refs). May be None.
        slv_contradiction: optional human-readable AC↔INV contradiction string,
            e.g. "AC-003-1「P95 < 0ms」與 INV-002「延遲 > 0」物理矛盾（SLV-004）".
    """
    # ACT-056 §G8 wiring 容錯：FSM 結構性 ESCALATION_FINAL 傳入的是
    # DiagnosticResult.to_dict()（proposal.diagnostic = diag.to_dict()）。dict 對
    # 下方 getattr 永遠落回 default → sub_type 退化成 "unknown"、舵手映射
    # （spec_conflict→sa-analyst）消失。於此統一還原為物件，確保結構性停機
    # 輸出可行動的舵手請求，而非泛用 "retry exhausted"。
    if isinstance(diagnostic, dict):
        try:
            from .diagnostic import DiagnosticResult as _DR
            diagnostic = _DR(**{k: diagnostic.get(k) for k in _DR.__dataclass_fields__})
        except Exception:  # noqa: BLE001 — 還原失敗則沿用 duck-typed getattr fallback
            pass
    if diagnostic is None:
        sub_type, category, confidence = "unknown", "structural", 0.5
        spec_refs: List[str] = []
    else:
        sub_type = getattr(diagnostic, "sub_type", "unknown") or "unknown"
        category = getattr(diagnostic, "category", "structural") or "structural"
        # H-6 修：confidence 可能來自鴨子型別物件的髒欄位 → 轉型失敗 fallback 0.5，
        # 避免整段 steersman handoff 因單一欄位被上層 try/except 靜默吞掉。
        try:
            confidence = float(getattr(diagnostic, "confidence", 0.5) or 0.5)
        except (TypeError, ValueError):
            confidence = 0.5
        spec_refs = list(getattr(diagnostic, "spec_refs", []) or [])

    gap, role, request = _CAPABILITY_GAP.get(sub_type, _DEFAULT_GAP)

    # 若 caller 沒給 SLV 矛盾字串，但 diagnostic 帶 spec_refs，至少把 refs 附上。
    contradiction = slv_contradiction
    if contradiction is None and sub_type == "spec_conflict" and spec_refs:
        contradiction = "涉及規格 ID：" + ", ".join(spec_refs)

    return SteersmanMessage(
        sub_type=sub_type,
        category=category,
        capability_gap=gap,
        target_role=role,
        environment_request=request,
        contradiction=contradiction,
        confidence=confidence,
        localization=localization,
    )


def render_markdown(diagnostic, *, slv_contradiction: Optional[str] = None) -> str:
    """Convenience: render directly to the markdown block."""
    return render_steersman(diagnostic, slv_contradiction=slv_contradiction).to_markdown()


# ===== Phase L M-L3 / ACT-094 — 主動規格脆弱性熱圖（advisory 加掛）=====
def render_fragility(rtm, *, drift_counts=None, escalation_refs=None, top_k: int = 5) -> str:
    """凍結前舵手介面：渲染規格脆弱性熱圖 top-K（Rule 9.24.5，advisory）。

    加法式整合——不改既有 render_steersman / render_markdown，舵手可在凍結前
    額外取得「哪些 AC 最脆弱」的事前風險視圖，提前加強測試合約。
    """
    from tools.fsm_runtime.spec_fragility_scorer import score_fragility, fragility_report
    report = score_fragility(rtm, drift_counts=drift_counts, escalation_refs=escalation_refs)
    return fragility_report(report, top_k=top_k)


# ===== Phase M M-M3 / ACT-102 — 組合脆弱性熱圖 + 進步性軌跡警示（advisory 加掛）=====
def render_composition_blast(intents, *, single_fragility=None, top_k: int = 5) -> str:
    """組合凍結前舵手介面：渲染跨意圖組合脆弱性熱圖 top-K（Rule 9.25.6，advisory）。

    加法式整合——舵手在 BACKLOG_PRIORITIZED 後、艦隊並行前，即見「哪些共享節點是
    跨意圖定時炸彈」，據此決定序列化。絕不自動改 spec、絕不阻塞 SCG。
    """
    from tools.fsm_runtime.composition_blast_analyzer import analyze_blast, blast_markdown
    report = analyze_blast(intents, single_fragility=single_fragility)
    return blast_markdown(report, top_k=top_k)


def render_trajectory(samples, *, window=None) -> str:
    """進步性軌跡舵手介面：渲染自我演化是否真在進步（Rule 9.25.4/9.25.7，advisory）。

    plateau/regression 一律導人類舵手注入新工具/典範，**絕不自動處置**。
    """
    from tools.fsm_runtime.capability_trajectory_monitor import (
        classify_trajectory, trajectory_markdown,
    )
    report = classify_trajectory(samples, window=window)
    return trajectory_markdown(report)


# ===== Phase N / ACT-108 — 全域最優排程推薦（advisory 加掛）=====
def render_optimal_schedule(problem, *, node_budget=None) -> str:
    """BACKLOG_PRIORITIZED 前舵手介面：渲染全域最優組合排程建議（Rule 9.26.3，advisory）。

    只**推薦**排程供舵手 signoff，**絕不自動 commit**。預算內無可行解 → 顯示 OPT_ESCALATION
    並請人工放寬 budget / 拆問題 / 接受序列化。
    """
    from tools.fsm_runtime.composition_optimizer import optimize
    res = optimize(problem, node_budget=node_budget)
    lines = [
        "## 🎯 全域組合最優排程建議（Composition Optimization — advisory，Rule 9.26.3）",
        "",
        f"- 展開節點數：{res.nodes_expanded}（SearchBounded 有界）",
        f"- 最優性：{'已窮舉證明最優' if res.optimal else 'best-so-far（預算限制）'}；gap={res.gap}",
    ]
    if res.escalated:
        lines += ["",
                  "🛑 **OPT_ESCALATION**：預算內找不到可行排程——請人工放寬 K / 拆解問題 / 接受序列化。"]
    else:
        lines.append("")
        lines.append("| 批次 | 並行意圖 |")
        lines.append("|------|----------|")
        for i, batch in enumerate(res.schedule or [], 1):
            lines.append(f"| {i} | {', '.join(batch)} |")
    lines += ["",
              "> advisory：僅**推薦**排程；最終仍須 `BACKLOG_PRIORITIZED` 人工 signoff，**絕不自動 commit**。"]
    return "\n".join(lines) + "\n"


# ===== Phase O / ACT-114 — 元最佳化「價值觀層」調參提案渲染（advisory 加掛）=====
def render_objective_tuning_proposal(proposal, *, verdict=None) -> str:
    """元最佳化舵手介面：渲染「目標函式權重的新舊 diff + held-out 對抗證據」（Rule 9.27.3，advisory）。

    把人類舵手抬到**最高的價值觀層**——不必讀程式碼即可決定「系統用什麼權重評判一切」。
    **絕不自動 bump `OBJECTIVE_PROFILE_VERSION`、絕不自動 commit**；提案一律待人工 signoff。

    Args:
        proposal: objective_tuner.TuningProposal。
        verdict: 選用 objective_replay_oracle.OracleVerdict（held-out 勝率證據）。
    """
    inc = proposal.incumbent
    cand = proposal.candidate
    head = (
        "🟢 達 margin，**待人工 signoff**" if proposal.accepted
        else "⚪ 未達 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 目標函式調參提案（Meta-Optimization — advisory，Rule 9.27.3）",
        "",
        f"{head}｜候選指紋 `{cand.fingerprint()}`｜tier {proposal.tier}",
        "",
        "| 權重 | incumbent（現行凍結） | 候選 | Δ |",
        "|------|----------------------|------|---|",
        f"| batch_w | {inc.batch_w} | {cand.batch_w} | {round(cand.batch_w - inc.batch_w, 4)} |",
        f"| latency_w | {inc.latency_w} | {cand.latency_w} | {round(cand.latency_w - inc.latency_w, 4)} |",
        "",
        f"- held-out 真實品質：候選 {proposal.candidate_quality:.2f} vs incumbent "
        f"{proposal.incumbent_quality:.2f}（Δ={proposal.win_delta:+.2f}，margin {proposal.win_margin:.2f}）",
        f"- 判讀：{proposal.reason}",
    ]
    if verdict is not None:
        lines.append(f"- 對抗證據：{verdict.evidence_line()}")
        lines.append(f"- 語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`")
    lines += [
        "",
        "【你是價值觀舵手，不是調參工】系統只是**提案**「該用什麼權重評判排程」；",
        "  👉 採納須你確認 `OBJECTIVE_PROFILE_VERSION` bump（人工 gate，Rule 9.27.3）。",
        "  👉 tier 僅來自 tuner 看不到的 held-out 現實代理勝率，**非自評**（Rule 9.27.2/9.27.5）。",
        "",
        "> advisory：**絕不自動 bump、絕不自動 commit、絕不自動改 scorer 常數**。",
    ]
    return "\n".join(lines) + "\n"


# ===== Phase P / ACT-120 — 一體化校準「整體價值系統」diff 渲染（advisory 加掛）=====
def render_unified_calibration_proposal(round_, *, joint_verdict=None) -> str:
    """一體化舵手介面：渲染「**整體價值系統**這一輪的位移 diff + pipeline 級聯合 held-out 證據」
    （Rule 9.28.1/9.28.4，advisory）。

    把人類舵手抬到**最高的整體價值系統層**——不必讀程式碼即可決定「系統整套評判尺規
    這一輪往哪漂移」。**反 big-bang（Rule 9.28.4）**：本輪至多 K 個評分器進 proposed，渲染
    明示被順延者；**絕不自動 bump 任何 `*_PROFILE_VERSION`、絕不自動 commit**；每個 bump
    一律待人工逐項 signoff。

    Args:
        round_: scorer_calibration_registry.CalibrationRound（已套反 big-bang K 截斷）。
        joint_verdict: 選用 joint_calibration_oracle.JointVerdict（pipeline 級聯合勝率證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個評分器達 margin，**待人工逐項 signoff**"
        if selected else "⚪ 本輪無評分器達 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 整體價值系統校準提案（Unified Scorer Calibration — advisory，Rule 9.28）",
        "",
        f"{head}",
        f"- 反 big-bang：本輪上限 K={round_.k}（Rule 9.28.4，絕不一次改整套價值系統）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪價值系統位移 diff（哪幾把尺規動、往哪動）",
        "",
        "| 評分器 | 命名空間 | 權重 diff（incumbent → 候選） | win_delta | tier |",
        "|--------|----------|------------------------------|-----------|------|",
    ]
    for p in selected:
        inc = p.incumbent.as_dict()
        cand = p.candidate.as_dict()
        diffs = "；".join(
            f"{k} {inc.get(k)}→{cand.get(k)}" for k in sorted(cand)
        )
        lines.append(
            f"| {p.scorer_name} | `{p.candidate.namespace}` | {diffs} | "
            f"{p.win_delta:+.2f} | {p.tier} |"
        )
    if joint_verdict is not None:
        lines += [
            "",
            f"- 跨評分器**聯合**證據（攔接縫 Goodhart）：{joint_verdict.evidence_line()}",
            f"- 聯合語料指紋（凍結防竄改）：`{joint_verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以**聯合** tier 為準：per-scorer 各自通過 **不**代表聯合通過"
            f"（Rule 9.28.2）。",
        ]
    lines += [
        "",
        "【你是整體價值系統舵手】系統只是**提案**「整套評判尺規這一輪如何一致地、小步地漂移」；",
        "  👉 每個評分器採納須你確認對應 `*_PROFILE_VERSION` bump（人工逐項 gate，Rule 9.28.1/9.28.4）。",
        "  👉 capability tier 僅來自全體 tuner 看不到的 pipeline 級聯合 held-out 勝率，**非自評**（Rule 9.28.2）。",
        "",
        "> advisory：**絕不自動 bump、絕不自動 commit、絕不一次改整套價值系統（K 上限）、絕不自動改 scorer 常數**。",
    ]
    return "\n".join(lines) + "\n"


# ===== Phase Q / ACT-126 — 價值維度自我擴充「本體論」diff 渲染（advisory 加掛）=====
def render_ontology_expansion_proposal(round_, *, verdict=None) -> str:
    """本體論舵手介面：渲染「系統的**價值本體論**這一輪要長出哪條新軸、它憑什麼必要」
    （Rule 9.29.1/9.29.4，advisory）。

    把人類舵手抬到**最高的價值本體論層**——不必讀程式碼即可決定「系統現在『也在乎』什麼」。
    **反 big-bang 增維（Rule 9.29.4）**：本輪至多 K_dim 條新維度進 proposed，渲染明示被順延者；
    **絕不自動納入任何維度、絕不自動 commit**；每條新維度一律待人工 signoff。

    Args:
        round_: value_dimension_registry.ExpansionRound（已套反 big-bang K_dim 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 條新維度達必要性 margin，**待人工逐條 signoff**"
        if selected else "⚪ 本輪無候選維度達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 價值本體論擴充提案（Self-Expanding Value Dimensions — advisory，Rule 9.29）",
        "",
        f"{head}",
        f"- 反 big-bang 增維：本輪上限 K_dim={round_.k}（Rule 9.29.4，絕不一次劫持整個本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪本體論 diff（系統現在『也在乎』哪條新軸）",
        "",
        "| 候選新維度 | 它量什麼（probe） | 必要性（增量覆蓋） | tier |",
        "|------------|-------------------|--------------------|------|",
    ]
    for p in selected:
        probe = ", ".join(p.dimension.probe) or "（未宣告）"
        lines.append(
            f"| `{p.dimension.name}` | {probe} | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 維度必要性**對抗**證據（攔自利噪音軸/冗餘軸）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：proposer 自評必要 **不**代表真必要"
            f"（Rule 9.29.2）。",
        ]
    lines += [
        "",
        "【你是價值本體論舵手】系統只是**提案**「它的本體論這一輪該長出哪條新評判軸」；",
        "  👉 每條新維度納入須你 signoff（人工逐條 gate，Rule 9.29.1/9.29.4），且受維度基數天花板封死。",
        "  👉 necessity tier 僅來自 proposer 看不到的維度必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.29.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個本體論（K_dim 上限）、絕不自寫維度集合常數**。",
    ]
    return "\n".join(lines) + "\n"


def render_semantic_invention_proposal(round_, *, verdict=None) -> str:
    """候選池外本體論發明舵手介面：渲染「系統憑空**發明**了哪條選單外的新評判軸、它的
    **生成文法來源**（憑什麼有界）、它**非自指**（憑什麼非自利）、它憑什麼必要」
    （Rule 9.30.1/9.30.2/9.30.4，advisory）。

    把人類舵手抬到**最高的候選池外本體論發明層**——不必讀程式碼即可決定「系統憑空發明的這條
    軸要不要納入」。**反 big-bang 自我發明（Rule 9.30.4）**：本輪至多 K_dim 條發明維度進
    proposed，渲染明示被順延者；**絕不自動納入、絕不自動 commit**；每條一律待人工 signoff。

    Args:
        round_: dimension_semantics_synthesizer.InventionRound（已套反 big-bang K_dim 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-keyed 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 條候選池外發明維度達必要性 margin，**待人工逐條 signoff**"
        if selected else "⚪ 本輪無發明維度達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 候選池外價值維度自我發明提案（Self-Inventing Value Dimensions — advisory，Rule 9.30）",
        "",
        f"{head}",
        f"- 反 big-bang 自我發明：本輪上限 K_dim={round_.k}（Rule 9.30.4，絕不一次劫持整個本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪候選池外發明 diff（系統憑空發明哪條選單外的新軸）",
        "",
        "| 發明維度（候選池外） | 生成文法來源（op·特徵） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|----------------------|--------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        d = p.dimension
        op = getattr(d, "op", "?")
        probe = ", ".join(getattr(d, "probe", ())) or "（未宣告）"
        lines.append(
            f"| `{d.name}` | {op}({probe}) | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 維度必要性**對抗**證據（feature-keyed，攔候選池外噪音軸/冗餘軸）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：synthesizer 自評必要 **不**代表真必要（Rule 9.30.2）。",
        ]
    lines += [
        "",
        "【你是候選池外價值本體論舵手】系統只是**提案**「它憑空發明了哪條選單外的新評判軸」；",
        "  👉 每條發明維度納入須你 signoff（人工逐條 gate，Rule 9.30.1/9.30.4），且受維度基數天花板封死。",
        "  👉 生成被**有界文法**封住（候選池外≠無界，Rule 9.30.1）；自指 probe 已被 self-reference guard 結構性拒絕（Rule 9.30.2 反自利）。",
        "  👉 necessity tier 僅來自 synthesizer 看不到的 feature-keyed 必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.30.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個本體論（K_dim 上限）、絕不自寫維度集合常數**。",
    ]
    return "\n".join(lines) + "\n"


def render_dimension_swap_proposal(out_dimension, in_dimension, *,
                                   out_tier, in_tier, swap_state=None) -> str:
    """退役聯動舵手介面：渲染「達基數天花板時，系統提議**退役舊軸 Y 換新軸 Z、net 基數不變**、
    swap 速率窗狀態」（Rule 9.30.3，advisory）。

    Args:
        out_dimension / in_dimension: duck-typed 維度（需 `.name`）。
        out_tier / in_tier: 出/入軸 necessity tier（入軸須嚴格 > 出軸 + margin，單調價值棘輪）。
        swap_state: 選用 meta_halt_monitor.SwapGuardResult（swap 速率窗狀態）。
    """
    out_name = getattr(out_dimension, "name", str(out_dimension))
    in_name = getattr(in_dimension, "name", str(in_dimension))
    lines = [
        "## 🔁 價值維度退役聯動提案（Cardinality-Preserving Retirement-Swap — advisory，Rule 9.30.3）",
        "",
        "🟠 維度基數已達天花板，系統提議**退舊換新**（net 基數不變），**待人工 signoff**：",
        "",
        "### 本輪退役聯動 diff（系統如何在不膨脹基數下演化本體論）",
        "",
        "| 動作 | 維度 | necessity tier |",
        "|------|------|----------------|",
        f"| ⬇️ 退役（出軸） | `{out_name}` | {out_tier} |",
        f"| ⬆️ 換入（入軸） | `{in_name}` | {in_tier} |",
        "",
        f"- 單調價值棘輪：入軸 tier={in_tier} **須嚴格 >** 出軸 tier={out_tier} + margin（Rule 9.30.3，防 A↔B↔A 旋轉）",
        "- net cardinality：退 1 + 加 1 = **不變**（不膨脹本體論基數）",
    ]
    if swap_state is not None:
        lines.append(
            f"- swap 聚合速率窗：最近 {swap_state.window} 筆內 swap {swap_state.window_swaps} 次"
            f"（上限 SDD_DIM_SWAP_RATE_MAX={swap_state.rate_max}；觸頂 → MFSM_ESCALATION，Rule 9.30.3）"
        )
    lines += [
        "",
        "【你是候選池外價值本體論舵手】系統只是**提案**「退哪條舊軸、換哪條新軸」；",
        "  👉 swap 須你 signoff（人工 gate，Rule 9.30.1/9.30.4），受單調價值棘輪 + swap 速率窗雙鎖封死。",
        "",
        "> advisory：**絕不自動 swap、絕不自動 commit、絕不在天花板上定基數旋轉重寫本體論（swap 速率窗封死）**。",
    ]
    return "\n".join(lines) + "\n"


def render_vocab_genesis_proposal(round_, *, verdict=None) -> str:
    """詞彙外本體論發明舵手介面（meta⁴）：渲染「系統憑空**發明**了哪個 VOCAB 外的新原始特徵字、
    它的**詞彙生成文法來源**（憑什麼有界）、它**非自指**（憑什麼非自利）、它憑什麼必要」
    （Rule 9.31.1/9.31.2/9.31.4，advisory）。

    把人類舵手抬到**最高的詞彙外本體論發明層（meta⁴）**——不必讀程式碼即可決定「系統憑空發明的
    這個原始特徵字要不要納入 VOCAB」。**反 big-bang 詞彙發明（Rule 9.31.4）**：本輪至多 K_vocab 個
    發明字進 proposed，渲染明示被順延者；**絕不自動納入、絕不自動 commit**；每個一律待人工 signoff。

    Args:
        round_: vocabulary_genesis.GenesisRound（已套反 big-bang K_vocab 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-grounded 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個 VOCAB 外詞彙發明字達必要性 margin，**待人工逐個 signoff**"
        if selected else "⚪ 本輪無詞彙發明字達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 詞彙生成文法自我擴充提案（Self-Expanding Vocabulary — advisory，Rule 9.31，meta⁴）",
        "",
        f"{head}",
        f"- 反 big-bang 詞彙發明：本輪上限 K_vocab={round_.k}（Rule 9.31.4，絕不一次劫持整個詞彙本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪詞彙外發明 diff（系統憑空發明哪個 VOCAB 外的新原始特徵字）",
        "",
        "| 發明詞彙字（VOCAB 外） | 詞彙生成文法來源（source·transform） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|------------------------|--------------------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        gf = p.feature
        src = getattr(gf, "source", "?")
        tr = getattr(gf, "transform", "?")
        lines.append(
            f"| `{gf.name}` | source={src}·transform={tr} | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 詞彙必要性**對抗**證據（feature-grounded，攔 VOCAB 外噪音字/冗餘字）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：genesis 自評必要 **不**代表真必要（Rule 9.31.2）。",
        ]
    lines += [
        "",
        "【你是詞彙外價值本體論舵手（meta⁴）】系統只是**提案**「它憑空發明了哪個 VOCAB 外的新原始特徵字」；",
        "  👉 每個詞彙字納入 VOCAB 須你 signoff（人工逐個 gate，Rule 9.31.1/9.31.4），且受詞彙基數天花板封死。",
        "  👉 生成被**有界詞彙文法**封住（VOCAB 外≠無界，Rule 9.31.1）；自指 source/transform 已被 vocab self-reference guard 結構性拒絕（Rule 9.31.2 反自利）。",
        "  👉 necessity tier 僅來自 genesis 看不到的 feature-grounded 詞彙必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.31.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個詞彙本體論（K_vocab 上限）、絕不自寫詞彙集合常數**。",
    ]
    return "\n".join(lines) + "\n"


def render_batch_recomposition_proposal(out_dimensions, in_dimensions, *,
                                        out_tiers, in_tiers, batch_state=None) -> str:
    """多維度批次重構舵手介面（meta⁴）：渲染「達基數天花板時，系統提議**一次退 m 換 n 的批次本體論
    重構**、批次大小、net 基數 delta、批次聚合單調性、批次速率窗狀態」（Rule 9.31.3，advisory）。

    Args:
        out_dimensions / in_dimensions: duck-typed 維度集合（需 `.name`）。
        out_tiers / in_tiers: 出/入軸 necessity tier 集合（批次聚合棘輪 + 杜絕批次內互抵）。
        batch_state: 選用 meta_halt_monitor.BatchSwapGuardResult（批次三鎖狀態）。
    """
    out_dims = list(out_dimensions)
    in_dims = list(in_dimensions)
    out_t = [int(t) for t in out_tiers]
    in_t = [int(t) for t in in_tiers]
    out_names = [getattr(d, "name", str(d)) for d in out_dims]
    in_names = [getattr(d, "name", str(d)) for d in in_dims]
    net_delta = len(in_dims) - len(out_dims)
    lines = [
        "## 🔄 多維度批次退役重構提案（Batch Ontology Recomposition — advisory，Rule 9.31.3，meta⁴）",
        "",
        f"🟠 維度基數已達天花板，系統提議**一次退 {len(out_dims)} 換 {len(in_dims)}**"
        f"（net 基數 delta={net_delta:+d}，非增），**待人工 signoff**：",
        "",
        "### 本輪批次重構 diff（系統如何一次批次演化本體論）",
        "",
        "| 動作 | 維度集合 | tier 集合 |",
        "|------|----------|-----------|",
        f"| ⬇️ 批次退役（出軸） | {', '.join('`%s`' % n for n in out_names)} | {out_t} |",
        f"| ⬆️ 批次換入（入軸） | {', '.join('`%s`' % n for n in in_names)} | {in_t} |",
        "",
        f"- 批次大小：|out|={len(out_dims)}、|in|={len(in_dims)}（上限 SDD_DIM_BATCH_MAX，反 big-bang 本體論一次重寫，Rule 9.31.3）",
        f"- 批次聚合單調棘輪：sum(in)={sum(in_t)} **須嚴格 >** sum(out)={sum(out_t)} + margin **且** min(in)={min(in_t) if in_t else 0} **須 >** max(out)={max(out_t) if out_t else 0}（杜絕批次內高低互抵夾帶退步 swap）",
        f"- net cardinality：退 {len(out_dims)} + 加 {len(in_dims)} = delta {net_delta:+d}（不膨脹本體論基數）",
    ]
    if batch_state is not None:
        lines.append(
            f"- 批次操作聚合速率窗：最近 {batch_state.window} 筆內批次操作 {batch_state.window_batches} 次"
            f"（上限 SDD_DIM_BATCH_RATE_MAX={batch_state.rate_max}；觸頂 → MFSM_ESCALATION，Rule 9.31.3）"
        )
    lines += [
        "",
        "【你是詞彙外價值本體論舵手（meta⁴）】系統只是**提案**「批次退哪些舊軸、換哪些新軸」；",
        "  👉 批次 swap 須你 signoff（人工 gate，Rule 9.31.1/9.31.4），受批次大小界 + 批次聚合棘輪 + 批次速率窗三鎖封死。",
        "",
        "> advisory：**絕不自動批次 swap、絕不自動 commit、絕不一次批次劫持/旋轉重寫整個本體論（批次三鎖封死）**。",
    ]
    return "\n".join(lines) + "\n"


def render_operator_genesis_proposal(round_, *, verdict=None) -> str:
    """算子外計算本體論發明舵手介面（meta⁵）：渲染「系統憑空**發明**了哪個 TRANSFORMS/OPS 外的新算子、
    它的**算子生成文法來源**（憑什麼有界）、它的**可計算性證據**（憑什麼一定會停：全函式 + cost<=step_max）、
    它**非自指**（憑什麼非自利）、它憑什麼必要」（Rule 9.32.1/9.32.2/9.32.3/9.32.4，advisory）。

    把人類舵手抬到**最高的算子外計算本體論發明層（meta⁵）**——不必讀程式碼即可決定「系統憑空發明的
    這個算子要不要納入 OPS」。Phase T 特出：被發明物第一次是『可執行計算』，故渲染**必附可計算性證據**
    （全函式 ✅ + 計算步數 cost）——人類一眼看懂「這段被發明的計算一定會停」。**反 big-bang 算子發明
    （Rule 9.32.4）**：本輪至多 K_op 個發明算子進 proposed，渲染明示被順延者；**絕不自動納入、絕不自動
    commit**；每個一律待人工 signoff。

    Args:
        round_: operator_genesis.OperatorRound（已套反 big-bang K_op 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-grounded 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個 TRANSFORMS/OPS 外算子發明達必要性 margin，**待人工逐個 signoff**"
        if selected else "⚪ 本輪無算子發明達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 轉換算子文法自我擴充提案（Self-Expanding Operator Grammar — advisory，Rule 9.32，meta⁵）",
        "",
        f"{head}",
        f"- 反 big-bang 算子發明：本輪上限 K_op={round_.k}（Rule 9.32.4，絕不一次劫持整個算子本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪算子外發明 diff（系統憑空發明哪個 TRANSFORMS/OPS 外的新算子）",
        "",
        "| 發明算子（OPS 外） | 算子生成文法來源 | 可計算性（全函式 + 步數） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|--------------------|------------------|----------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        go = p.operator
        prim = getattr(go, "primary", "?")
        comb = getattr(go, "combinator", "?")
        sec = getattr(go, "secondary", "")
        src = f"primitive={prim}·combinator={comb}" + (f"·secondary={sec}" if sec else "")
        lines.append(
            f"| `{go.name}` | {src} | ✅ 全函式 · cost={p.cost}<=step_max | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 算子必要性**對抗**證據（feature-grounded，攔 OPS 外噪音算子/冗餘算子）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：genesis 自評必要 **不**代表真必要（Rule 9.32.2）。",
        ]
    lines += [
        "",
        "【你是算子外計算本體論舵手（meta⁵）】系統只是**提案**「它憑空發明了哪個 TRANSFORMS/OPS 外的新算子（=一段會被反覆執行的計算）」；",
        "  👉 每個算子納入 OPS 須你 signoff（人工逐個 gate，Rule 9.32.1/9.32.4），且受算子基數天花板封死。",
        "  👉 生成被**有界算子文法**封住（OPS 外≠無界，Rule 9.32.1）；自指 primitive/combinator/probe 已被 operator self-reference guard 結構性拒絕（Rule 9.32.2 反自利）。",
        "  👉 **可計算性紅線（Rule 9.32.3）**：每個被發明算子結構性**全函式 + 有界步數（cost<=SDD_DIM_OP_STEP_MAX）+ 零遞迴零迴圈**——『被發明的計算一定會停』（把停機問題釘進自我擴充產物本身）。",
        "  👉 necessity tier 僅來自 genesis 看不到的 feature-grounded 算子必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.32.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個算子本體論（K_op 上限）、絕不自寫算子集合常數、絕不採納非全函式/無界步數算子**。",
    ]
    return "\n".join(lines) + "\n"


def render_alphabet_genesis_proposal(round_, *, verdict=None) -> str:
    """字母表外計算生成本體論發明舵手介面（meta⁶）：渲染「系統憑空**發明**了哪個 PRIMITIVES/COMBINATORS 外的
    新運算字母、它的**字母表生成文法來源**（憑什麼有界）、它的**可計算性閉包證據**（憑什麼擴充後整個算子
    代數一定會停：G(A') total + max_cost<=step_max）、它**非自指**（憑什麼非自利）、它憑什麼必要」
    （Rule 9.33.1/9.33.2/9.33.3/9.33.4，advisory）。

    把人類舵手抬到**最高的字母表外計算生成本體論發明層（meta⁶）**——不必讀程式碼即可決定「系統憑空發明的
    這個運算字母要不要納入算子字母表」。Phase U 特出：被發明物是『會被算子生成文法用來生成整個算子代數的
    生成規則零件』，故渲染**必附可計算性閉包證據**（擴充後 G(A') 整代數全函式 ✅ + max_cost）——人類一眼看懂
    「這段被發明的生成規則生成的整個算子代數一定會停」。**反 big-bang 字母發明（Rule 9.33.4）**：本輪至多
    K_alpha 個發明字母進 proposed，渲染明示被順延者；**絕不自動納入、絕不自動 commit**；每個一律待人工 signoff。

    Args:
        round_: operator_alphabet_genesis.AlphabetRound（已套反 big-bang K_alpha 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-grounded 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個 PRIMITIVES/COMBINATORS 外字母發明達必要性 margin，**待人工逐個 signoff**"
        if selected else "⚪ 本輪無字母發明達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 組合算子文法自我擴充提案（Self-Expanding Operator Alphabet — advisory，Rule 9.33，meta⁶）",
        "",
        f"{head}",
        f"- 反 big-bang 字母發明：本輪上限 K_alpha={round_.k}（Rule 9.33.4，絕不一次劫持整個字母本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪字母表外發明 diff（系統憑空發明哪個 PRIMITIVES/COMBINATORS 外的新運算字母）",
        "",
        "| 發明字母（字母表外） | 字母生成文法來源 | 可計算性閉包（G(A') total + 步數） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|----------------------|------------------|------------------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        el = p.element
        kind = getattr(el, "kind", "?")
        if kind == "primitive":
            src = f"base_reducer={getattr(el, 'base_reducer', '?')}·post_map={getattr(el, 'post_map', '?')}"
        else:
            src = f"atom={getattr(el, 'atom', '?')}·arity={getattr(el, 'arity', '?')}"
        closure = ("✅ 閉包全函式" if p.closure_ok else "❌ 閉包破裂") + f" · max_cost={p.closure_max_cost}<=step_max"
        lines.append(
            f"| `{el.name}`（{kind}） | {src} | {closure} | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 字母必要性**對抗**證據（feature-grounded，攔字母表外噪音字母/冗餘字母）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：genesis 自評必要 **不**代表真必要（Rule 9.33.2）。",
        ]
    lines += [
        "",
        "【你是字母表外計算生成本體論舵手（meta⁶）】系統只是**提案**「它憑空發明了哪個 PRIMITIVES/COMBINATORS 外的新運算字母（=會被文法用來生成每一個算子的生成規則零件）」；",
        "  👉 每個字母納入算子字母表須你 signoff（人工逐個 gate，Rule 9.33.1/9.33.4），且受字母基數天花板封死。",
        "  👉 生成被**有界字母表文法**封住（字母表外≠無界，Rule 9.33.1）；自指 reducer/map/atom/probe 已被 alphabet self-reference guard 結構性拒絕（Rule 9.33.2 反自利）。",
        "  👉 **可計算性閉包紅線（Rule 9.33.3）**：被發明字母結構性使擴充後 G(A') **整個算子代數全函式 + 有界步數（max_cost<=SDD_DIM_OP_STEP_MAX）+ 零遞迴零迴圈**——『被發明的生成規則生成的整個算子代數一定會停』（把停機問題釘進自我擴充的生成規則本身）。",
        "  👉 necessity tier 僅來自 genesis 看不到的 feature-grounded 字母必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.33.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個字母本體論（K_alpha 上限）、絕不自寫字母集合常數、絕不採納破壞可計算性閉包的字母**。",
    ]
    return "\n".join(lines) + "\n"


def render_depth_genesis_proposal(round_, *, verdict=None) -> str:
    """深度外計算生成本體論發明舵手介面（meta⁷）：渲染「系統憑空**發明**了哪個組合深度 >2 的新複合算子、
    它的**深度生成文法來源**（憑什麼有界）、它的**深度可計算性閉包證據**（憑什麼擴充深度後整個深度算子代數
    一定會停：G(A,depth) total + max_cost==depth<=step_max，因 cost==depth 即「深度本身有硬上界」）、它**非自指**
    （憑什麼非自利）、它憑什麼必要」（Rule 9.34.1/9.34.2/9.34.3/9.34.4，advisory）。

    把人類舵手抬到**最深的深度外計算生成本體論發明層（meta⁷）**——不必讀程式碼即可決定「系統憑空發明的這個
    更深複合算子要不要納入算子本體論」。Phase V 特出：被自我擴充物是『文法的結構性深度參數 = 直接決定每算子
    cost 的步數參數』，故渲染**必附深度可計算性閉包證據**（擴充深度後 G(A,depth) 整代數全函式 ✅ + max_cost，
    且因 cost==depth 即「深度本身有硬上界」）——人類一眼看懂「這個被發明的更深算子（及其同深度整代數）一定會停」。
    **反 big-bang 深度發明（Rule 9.34.4）**：本輪至多 K_depth 個發明深度算子進 proposed，渲染明示被順延者；
    **絕不自動納入、絕不自動 commit**；每個一律待人工 signoff。

    Args:
        round_: operator_depth_genesis.DepthRound（已套反 big-bang K_depth 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-grounded 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個深度 >2 算子發明達必要性 margin，**待人工逐個 signoff**"
        if selected else "⚪ 本輪無深度發明達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 算子組合深度文法自我擴充提案（Self-Expanding Operator Depth — advisory，Rule 9.34，meta⁷）",
        "",
        f"{head}",
        f"- 反 big-bang 深度發明：本輪上限 K_depth={round_.k}（Rule 9.34.4，絕不一次劫持整個深度本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪深度外發明 diff（系統憑空發明哪個組合深度 >2 的新複合算子）",
        "",
        "| 發明深度算子（深度外） | 深度生成文法來源 | 深度可計算性閉包（G(A,depth) total + 步數） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|------------------------|------------------|---------------------------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        op = p.operator
        src = f"base={getattr(op.base, 'name', '?')}·chain={'∘'.join(reversed(op.chain)) or '（無）'}·depth={p.depth}"
        closure = ("✅ 閉包全函式" if p.closure_ok else "❌ 閉包破裂") + \
            f" · max_cost={p.closure_max_cost}<=step_max（cost==depth={p.depth}）"
        lines.append(
            f"| `{op.name}` | {src} | {closure} | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 深度必要性**對抗**證據（feature-grounded，攔深度外噪音算子/冗餘算子）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：genesis 自評必要 **不**代表真必要（Rule 9.34.2）。",
        ]
    lines += [
        "",
        "【你是深度外計算生成本體論舵手（meta⁷）】系統只是**提案**「它憑空發明了哪個組合深度 >2 的新複合算子（=一棵更深的運算式樹）」；",
        "  👉 每個深度算子納入算子本體論須你 signoff（人工逐個 gate，Rule 9.34.1/9.34.4），且受深度算子基數天花板封死。",
        "  👉 生成被**有界深度文法**封住（深度外≠無界，Rule 9.34.1）；自指 base/chain/probe 已被 depth self-reference guard 結構性拒絕（Rule 9.34.2 反自利）。",
        "  👉 **深度可計算性閉包紅線（Rule 9.34.3）**：被發明深度算子結構性使擴充深度後 G(A,depth) **整個深度算子代數全函式 + 有界步數（max_cost==depth<=SDD_DIM_OP_STEP_MAX）+ 零遞迴零迴圈**——『被自我擴充的組合深度（=計算步數）生成的整個算子代數一定會停』（把停機問題釘進自我擴充文法的結構性步數參數本身，因 cost==depth 而最直接）。",
        "  👉 necessity tier 僅來自 genesis 看不到的 feature-grounded 深度必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.34.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個深度本體論（K_depth 上限）、絕不自寫深度上界常數、絕不採納破壞深度可計算性閉包的算子**。",
    ]
    return "\n".join(lines) + "\n"


def render_recursion_genesis_proposal(round_, *, verdict=None) -> str:
    """互遞迴計算生成本體論發明舵手介面（meta⁸）：渲染「系統憑空**發明**了哪個會呼叫其他算子 / 自呼叫的互遞迴
    算子、它的**互遞迴生成文法來源**（呼叫圖節點/邊/rank/fuel，憑什麼有界）、它的**良基停機證書證據**（憑什麼
    可證良基終止：呼叫圖帶良基 ranking function〔每條呼叫邊嚴格遞減下有界 rank ⟹ 良基無環 ⟹ 終止〕 + fuel<=step_max，
    用全新 device「呼叫圖上的 ranking function」承載 Phase V 線性鏈表達不出的分支/共享呼叫圖、取代「有界運算式樹
    深度」）、它**非自指**（憑什麼非自利）、它憑什麼必要」（Rule 9.35.1/9.35.2/9.35.3/9.35.4，advisory）。

    把人類舵手抬到**最深的互遞迴計算生成本體論發明層（meta⁸）**——不必讀程式碼即可決定「系統憑空發明的這個
    互遞迴算子要不要納入算子本體論」。Phase W 特出：被自我擴充物是『算子是否可互相引用 / 自引用這個結構參數』，
    讓判定停機從可判定翻不可判定（判定任意含環圖停機 = 停機問題），故渲染**必附良基停機證書證據**（呼叫圖可證
    良基終止 ✅ + fuel<=step_max）——人類一眼看懂「這個被發明的互遞迴算子（及其同拓樸整代數）一定會停（良基測度
    而非有界步數）」。**反 big-bang 互遞迴發明（Rule 9.35.4）**：本輪至多 K_recur 個發明互遞迴算子進 proposed，
    渲染明示被順延者；**絕不自動納入、絕不自動 commit**；每個一律待人工 signoff。

    Args:
        round_: operator_recursion_genesis.RecursionRound（已套反 big-bang K_recur 截斷）。
        verdict: 選用 dimension_necessity_oracle.DimensionVerdict（feature-grounded 增量覆蓋 ∧ 非冗餘證據）。
    """
    selected = list(round_.selected)
    head = (
        f"🟢 本輪 {len(selected)} 個互遞迴算子發明達必要性 margin，**待人工逐個 signoff**"
        if selected else "⚪ 本輪無互遞迴發明達必要性 margin（不送 signoff，守反自評紀律）"
    )
    lines = [
        "## 🧭 算子間互遞迴文法自我擴充提案（Self-Expanding Operator Recursion — advisory，Rule 9.35，meta⁸）",
        "",
        f"{head}",
        f"- 反 big-bang 互遞迴發明：本輪上限 K_recur={round_.k}（Rule 9.35.4，絕不一次劫持整個互遞迴本體論）"
        f"｜順延：{', '.join(round_.deferred) or '（無）'}",
        "",
        "### 本輪互遞迴外發明 diff（系統憑空發明哪個會呼叫其他算子 / 自呼叫的互遞迴算子）",
        "",
        "| 發明互遞迴算子（互遞迴外） | 互遞迴生成文法來源（呼叫圖） | 良基停機證書（可證終止 + fuel） | 非自指 | 必要性（增量覆蓋） | tier |",
        "|----------------------------|------------------------------|---------------------------------|--------|--------------------|------|",
    ]
    for p in selected:
        op = p.operator
        src = (f"nodes={op.n_nodes()}·fold={op.combine}·ranks={op._ranks()}·fuel={p.fuel}")
        cert = ("✅ 可證良基終止（呼叫圖帶良基 ranking function：每條呼叫邊嚴格遞減下有界 rank ⟹ 良基無環 ⟹ 終止）"
                if p.terminating else
                "❌ 良基停機證書失敗（無 ranking function、即可能含環 → 可能不停機，拒絕）") + \
            f" · fuel={p.fuel}<=step_max"
        lines.append(
            f"| `{op.name}` | {src} | {cert} | ✅ 非自指 | {p.necessity:+.2f} | {p.tier} |"
        )
    if verdict is not None:
        lines += [
            "",
            f"- 互遞迴必要性**對抗**證據（feature-grounded，攔互遞迴外噪音算子/冗餘算子）：{verdict.evidence_line()}",
            f"- 必要性語料指紋（凍結防竄改）：`{verdict.corpus_fingerprint}`",
            f"- ⚖️ 採納以 **oracle** 判定為準：genesis 自評必要 **不**代表真必要（Rule 9.35.2）。",
        ]
    lines += [
        "",
        "【你是互遞迴計算生成本體論舵手（meta⁸）】系統只是**提案**「它憑空發明了哪個會呼叫其他算子 / 自呼叫的互遞迴算子（=一張帶 rank 的算子呼叫圖）」；",
        "  👉 每個互遞迴算子納入算子本體論須你 signoff（人工逐個 gate，Rule 9.35.1/9.35.4），且受互遞迴算子基數天花板封死。",
        "  👉 生成被**有界互遞迴文法**封住（互遞迴外≠無界，Rule 9.35.1）；自指 node base/probe 已被 recursion self-reference guard 結構性拒絕（Rule 9.35.2 反自利）。",
        "  👉 **互遞迴良基停機證書紅線（Rule 9.35.3）**：被發明互遞迴算子結構性附帶**良基停機證書（呼叫圖帶良基 ranking function：每條呼叫邊嚴格遞減下有界 rank ⟹ 良基無環 ⟹ 可證終止 + fuel<=SDD_DIM_OP_STEP_MAX + 整代數全函式 + 求值器零真遞迴零 while）**——『判定任意含環呼叫圖是否停機 = 停機問題（不可判定），故只收出示 ranking function 證書者（把可能含環的呼叫圖空間侷限到可證良基終止之全函式片段，Agda/Coq 結構遞迴邊界），fuel 為硬後盾；device 之新在於用「呼叫圖上的 ranking function」承載 Phase V 線性深度鏈表達不出的分支/共享/重匯聚呼叫圖』（把停機問題釘在可判定 vs 不可判定的臨界線本身；meta⁸ 不讓算子代數真正跨入圖靈完備）。",
        "  👉 necessity tier 僅來自 genesis 看不到的 feature-grounded 互遞迴必要性 held-out（增量覆蓋 ∧ 非冗餘）勝率，**非自評**（Rule 9.35.2）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不一次劫持整個互遞迴本體論（K_recur 上限）、絕不自寫互遞迴界常數、絕不採納無良基停機證書（含無證書環）的算子、絕不讓算子代數真正跨入圖靈完備而謊稱可證停機**。",
    ]
    return "\n".join(lines) + "\n"


def render_embodied_grounding_proposal(grounding, *, capability="自我發明能力") -> str:
    """具身接地舵手介面（Phase X / meta⁸ 接地）：渲染「自我發明能力被 META_FSM 納入前的**具身接地 diff**」——
    不只渲染合成勝率，還渲染「在真實沙箱基準上 OQS 變化 / 新增 runtime 錯誤 / 是否沙箱 timeout / grounded-verdict」，
    讓人類舵手一眼看懂「這個自我發明的東西在實跑環境裡到底有沒有用」（Rule 9.36，advisory，K=1 逐個 signoff）。

    把提示「賦予評估器實體操作能力（Playwright/隔離環境/客觀錯誤）」推到**元迴圈層**並呈現給人類舵手——元迴圈的
    自我演化判定不再只看合成語料勝率，而是看具身觀測。

    Args:
        grounding: embodied_grounding_oracle.GroundedVerdict（含 observation / grounded_verdict / oqs / baseline_oqs）。
    """
    gv = getattr(grounding, "grounded_verdict", "?")
    oqs = float(getattr(grounding, "oqs", 0.0))
    base = float(getattr(grounding, "baseline_oqs", 0.0))
    timed_out = bool(getattr(grounding, "sandbox_timed_out", False))
    obs = getattr(grounding, "observation", None)
    delta = oqs - base
    icon = "🟢" if gv == "grounded_pass" else ("🟠" if gv in ("grounded_fail", "spec_defect") else "⚪")
    runtime_errs = getattr(obs, "runtime_errors", "n/a") if obs is not None else "n/a"
    nonzero = getattr(obs, "nonzero_exit", "n/a") if obs is not None else "n/a"
    lines = [
        "## 🧭 具身接地提案（Embodied Grounding — advisory，Rule 9.36，meta⁸ 接地）",
        "",
        f"{icon} `{capability}` 具身 grounded-verdict = **{gv}**"
        + ("（沙箱硬 timeout → grounded_fail，FSM 不 wall-clock wait）" if timed_out else ""),
        "",
        "### 具身接地 diff（真實沙箱實跑客觀觀測，非合成語料勝率）",
        "",
        "| 指標 | baseline | candidate | Δ |",
        "|------|----------|-----------|---|",
        f"| OQS（輸出執行品質 0~1） | {base:.4f} | {oqs:.4f} | {delta:+.4f} |",
        f"| runtime 錯誤數 | — | {runtime_errs} | — |",
        f"| 非零 exit | — | {nonzero} | — |",
        f"| 沙箱 timeout | — | {timed_out} | — |",
        "",
        "【你是具身接地舵手（meta⁸ 接地）】系統只是**提案**「自我發明能力在真實沙箱裡的具身觀測」；",
        "  👉 納入須你 signoff（K=1 逐個 gate，Rule 9.36）；grounded_fail / 無具身增益者 REJECT 不 churn。",
        "  👉 **Fail-closed 紅線（Rule 9.36）**：缺客觀 ExecutionObservation（零觀測 false-green）→ guard_embodied_grounding"
        " 結構性拒絕 → MFSM_ESCALATION；沙箱硬 timeout → grounded_fail（FSM 不等沙箱），把「真實沙箱可能 hang」封死。",
        "  👉 grounded-verdict 由 genesis 看不到的具身 oracle（output_quality_scorer 接地）產出，**非合成自評**（對抗分離）。",
        "",
        "> advisory：**絕不自動納入、絕不自動 commit、絕不以零觀測 false-green 放行、絕不等沙箱 wall-clock（硬 timeout）**。",
    ]
    return "\n".join(lines) + "\n"


# ===== Phase Y / ACT-161 — 互遞迴呼叫圖可審批儀表板（Recursion Topology Dashboard，advisory）=====
def render_recursion_topology_dashboard(view, *, capability: str = "互遞迴自我發明能力") -> str:
    """Phase Y 舵手介面（meta⁸ 可解釋性轉向）：把 meta⁸ 良基終止互遞迴呼叫圖渲染為人類 K=1 signoff 儀表板
    （advisory，Rule 9.37）.

    GAP-Y1 解：Phase L~X 的停機證書一路 machine-verified、從未 human-auditable。本介面組合拓樸 / 終止 /
    接地三視圖為單一 Markdown 交接，把舵手抬到「**可審批 meta⁸ 終止證書**」的高度——不必讀程式碼即可看出：
    呼叫圖拓樸、哪算子吃最多 fuel（🔴 critical）、迴圈如何在 rank→0 ∧ fuel→0 被強制打斷、具身接地是否退步。

    沿用既有 render_* 合約：**純函式 → Markdown、advisory、絕不自動 signoff/commit/寫 FSM-STATE**。呈現前
    須過 `meta_halt_monitor.guard_visualization_bounded`（render budget + 拓樸同構防偽 + 接地 fail-closed）。

    Args:
        view: recursion_topology_view.TopologyView（extract_topology 產出，已有界截斷/分頁）。
    """
    from tools.fsm_runtime import recursion_topology_view as _v
    body = _v.render_dashboard_markdown(view)
    fp = getattr(view, "operator_fingerprint", "") or "（未宣告）"
    term = "✅ 可證良基終止" if getattr(view, "terminating", False) else "❌ 良基停機證書失敗"
    trunc = (f"（⚠️ 已有界截斷：顯示 {len(view.nodes)}/{view.n_total_nodes} 節點，page "
             f"{view.page_cursor + 1}/{view.total_pages}）" if getattr(view, "truncated", False) else "")
    lines = [
        "## 🧭 互遞迴呼叫圖可審批儀表板（Recursion Topology Dashboard — advisory，Rule 9.37，meta⁸ 可解釋性）",
        "",
        f"`{capability}` 指紋 `{fp}`｜{term}｜fuel={getattr(view, 'fuel', 0)}{trunc}",
        "",
        body,
        "",
        "【你是 meta⁸ 可審批性舵手】系統把抽象算子代數 + rank/fuel **有界、可稽核地**投影成你看得懂的拓樸；",
        "  👉 納入須你 K=1 signoff（Rule 9.37）；🔴 標的算子吃最多 fuel、⛔ 標處迴圈被計數器（fuel/rank）強制打斷。",
        "  👉 **拓樸防偽（PY-2）**：本圖已過 verify_topology_consistency 與 to_dict() 圖同構稽核——畫的圖 == 跑的圖（不容視覺欺騙）。",
        "  👉 **有界渲染（PY-3）**：render budget（node/edge/char）封死，輸入再大也截斷分頁，不卡死 / 不 token 爆炸。",
        "  👉 接地視圖無客觀 ExecutionObservation 一律灰佔位，**絕不 false-green**。",
        "",
        "> advisory：儀表板是 **read-only 純觀察者**，渲染不漂移 meta-loop 狀態；**絕不自動 signoff / commit / 寫 FSM-STATE**。",
    ]
    return "\n".join(lines) + "\n"
