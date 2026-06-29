"""AutoSDD_improving_95 W-95-2 — PRD→playbook 橋接「端到端」harness（A 軌）。

對應規格：docs/04_planning/AutoSDD_improving_95.md §3.2 W-95-2 / §3.3 鏈路 / RTM-95-3~5。

職責（Rule 5：純編排 + 確定性解析，非 AI）：
  把 improving_94 留下的「靜態橋接構件」串成可真跑的一條鏈，並落標準化證據：

    three_tier plan YAML
      └─[compile：複用 W-94-2 compile_to_playbook（含 evaluator 白名單消毒）]
          └─→ playbook.yaml
              └─[run：subprocess `python -m autoclaude <pb> --config <cfg> --fresh`（真 Claude token）]
                  └─[parse：解析引擎 log（step ✓ / STEP_TOKEN_PEAK / KernelResult）]
                      └─→ evidence JSON（per-step：step_id/goal_task_id/success/evaluator/token_pct
                          + aggregate：steps/pass_rate/escalated/peak_token_pct）

安全（架構紅線：「從文件生成指令」一律走 compiler 白名單消毒，不繞過）：
  evaluator_command 的唯一生成關仍是 compile_to_playbook → sanitize_evaluator（黑名單字元 ⊇
  CONDITIONAL + 白名單首 token pytest/python + 禁 python -c，fail-closed）。harness 不自造指令。

可測性（RTM-95-3）：確定性純函式（compile_plan / parse_e2e_log / build_evidence）與真跑
  副作用（run_autoclaude subprocess）切開——單測餵 canned log 驗解析與證據 schema，不打真 LLM。

CLI 範例（於 AutoClaude/ 目錄）：
  # 端到端真跑（花真 Claude token；用 Brain off 的 ab_pty_config）：
  python tools/run_bridge_e2e.py --source scripts/bridge_e2e/strutils_prd_plan.yaml \\
      --config scripts/ab_configs/ab_pty_config.yaml --workdir <tmp> \\
      --out docs/03_testing/AutoSDD_improving_95_bridge_e2e_evidence.json
  # 只編譯不真跑（驗證鏈路前段，不花 token）：
  python tools/run_bridge_e2e.py --source <plan.yaml> --compile-only --out <pb.yaml>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click

# tools/ 內部互用（皆以 repo root 為基準，比照 three_tier_to_playbook.py / ab_compare_backends.py）
_THIS = Path(__file__).resolve()
_REPO_ROOT = _THIS.parent.parent
_TOOLS_DIR = _THIS.parent
for _p in (str(_REPO_ROOT), str(_TOOLS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from autoclaude.models.playbook import Playbook  # noqa: E402
from three_tier_to_playbook import compile_to_playbook, playbook_to_yaml  # noqa: E402

# --- 引擎 log 解析錨點（與 core/kernel.py 輸出對齊；同 ab_compare_backends 的真值來源）---
# 成功 step：kernel step_log `[E-IMPL-2] <name> ✓ (attempt N)`（kernel.py:_run_step）。
# 🔴 gap 用 `[^\[\n]*?`（不跨另一個 `[`）：否則同一行前綴的 log 等級標籤 `[INFO]` 會被當
#   step_id、非貪婪跨越吃掉真正的 `[E-SPEC-1] ... ✓`（W-95-3 真跑 zero-trust 揪出之解析 bug）。
_RE_STEP_OK = re.compile(r"\[([A-Za-z0-9_\-]+)\][^\[\n]*?✓ \(attempt (\d+)\)")
# 整輪權威成功步：kernel `completed_step_ids=['E-SPEC-1', 'E-IMPL-1', ...]`（success 真值來源，
# 優先於 ✓ 標記——ab_compare 紀律「KernelResult 權威」；✓ 僅補 first_pass/attempt）。
_RE_KR_COMPLETED_IDS = re.compile(r"completed_step_ids=\[([^\]]*)\]")
_RE_QUOTED_ID = re.compile(r"'([^']+)'")
# per-step token% 真值：`=== STEP_TOKEN_PEAK | step=E-IMPL-2 pct=12.3456 ===`（kernel.py W-86-1）。
_RE_STEP_TOKEN = re.compile(
    r"STEP_TOKEN_PEAK\s*\|\s*step=([A-Za-z0-9_\-]+)\s+pct=(\d+(?:\.\d+)?)")
# 整輪權威：`KernelResult(success=True, completed_steps=5, total_steps=5, ... escalated=False ...)`。
_RE_KERNEL_RESULT = re.compile(r"KernelResult\((.*)$")
_RE_KR_SUCCESS = re.compile(r"success=(True|False)")
_RE_KR_COMPLETED = re.compile(r"completed_steps=(\d+)")
_RE_KR_TOTAL = re.compile(r"total_steps=(\d+)")
_RE_KR_ESCALATED = re.compile(r"escalated=(True|False)")
_RE_KR_PEAK = re.compile(r"peak_token_pct=(\d+(?:\.\d+)?)")


class BridgeE2EError(RuntimeError):
    """harness 編排/解析失敗。"""


def compile_plan(
    source_path: Path,
    *,
    project_id: Optional[str] = None,
    workflow_type: str = "aisdlc_sdd",
) -> tuple[Playbook, str]:
    """three_tier plan YAML → (Playbook, 攤平 playbook YAML 文字)。複用 W-94-2 compiler。"""
    yaml_text = Path(source_path).read_text(encoding="utf-8")
    pb = compile_to_playbook(yaml_text, project_id=project_id, workflow_type=workflow_type)
    return pb, playbook_to_yaml(pb)


def parse_e2e_log(log_text: str) -> dict:
    """解析引擎 log → 結構化真值（確定性，純函式，可單測）。

    回傳：{
      ok_steps: {step_id: attempt}（首次 ✓ 的 attempt；供 first_pass 判定）,
      completed_ids: [step_id, ...]（kernel 權威成功步；空 list＝無 KernelResult/未完成）,
      step_token_pct: {step_id: max pct}（STEP_TOKEN_PEAK，無訊號則缺）,
      kernel_result: {success, completed_steps, total_steps, escalated, peak_token_pct} or None,
    }
    """
    ok_steps: dict[str, int] = {}
    for sid, attempt in _RE_STEP_OK.findall(log_text):
        ok_steps.setdefault(sid, int(attempt))  # 取首次成功的 attempt

    # kernel 權威成功步（取最後一個 completed_step_ids；無則空）
    completed_ids: list[str] = []
    cid_matches = _RE_KR_COMPLETED_IDS.findall(log_text)
    if cid_matches:
        completed_ids = _RE_QUOTED_ID.findall(cid_matches[-1])

    step_token: dict[str, float] = {}
    for sid, pct in _RE_STEP_TOKEN.findall(log_text):
        v = float(pct)
        step_token[sid] = max(step_token.get(sid, 0.0), v)

    kr: Optional[dict] = None
    kr_matches = _RE_KERNEL_RESULT.findall(log_text)
    if kr_matches:
        blob = kr_matches[-1]  # 取最後一個（最終態權威）
        kr = {}
        if (m := _RE_KR_SUCCESS.search(blob)):
            kr["success"] = m.group(1) == "True"
        if (m := _RE_KR_COMPLETED.search(blob)):
            kr["completed_steps"] = int(m.group(1))
        if (m := _RE_KR_TOTAL.search(blob)):
            kr["total_steps"] = int(m.group(1))
        if (m := _RE_KR_ESCALATED.search(blob)):
            kr["escalated"] = m.group(1) == "True"
        if (m := _RE_KR_PEAK.search(blob)):
            kr["peak_token_pct"] = float(m.group(1))

    return {"ok_steps": ok_steps, "completed_ids": completed_ids,
            "step_token_pct": step_token, "kernel_result": kr}


def build_evidence(pb: Playbook, parsed: dict, *, source: str, config: str) -> dict:
    """攤平 Playbook + log 解析 → 標準化證據 dict（per-step join goal_task_id + aggregate）。

    確定性，純函式，可單測（餵 canned parsed）。step 順序錨 playbook tasks 順序（權威）。
    """
    ok = parsed.get("ok_steps", {})
    tok = parsed.get("step_token_pct", {})
    # success 真值優先取 kernel 權威 completed_ids（有解析到才用）；否則退回 ✓ 標記（半途 log）。
    completed = set(parsed.get("completed_ids") or [])
    use_completed = bool(completed)

    def _is_ok(sid: str) -> bool:
        return sid in completed if use_completed else sid in ok

    per_step = []
    for t in pb.tasks:
        per_step.append({
            "step_id": t.step_id,
            "goal_task_id": t.goal_task_id,
            "name": t.name,
            "success": _is_ok(t.step_id),
            "first_pass": ok.get(t.step_id) == 1,
            "has_evaluator": bool(t.evaluator_command),
            "evaluator_command": t.evaluator_command,
            "token_pct": tok.get(t.step_id),  # None＝該步無 token 訊號（未撞門檻 / dry-run）
        })
    success_n = sum(1 for s in per_step if s["success"])
    total = len(per_step)
    # goal_task_id 分組計數（三層→扁平後的分組可追溯性）
    by_goal: dict[str, dict] = {}
    for s in per_step:
        g = by_goal.setdefault(s["goal_task_id"] or "(none)", {"steps": 0, "success": 0})
        g["steps"] += 1
        g["success"] += int(s["success"])
    kr = parsed.get("kernel_result")
    return {
        "schema": "autosdd_bridge_e2e_evidence/v1",
        "source_plan": source,
        "config": config,
        "project": pb.project,
        "aggregate": {
            "total_steps": total,
            "success_steps": success_n,
            "pass_rate": round(success_n / total, 4) if total else 0.0,
            "evaluator_steps": sum(1 for s in per_step if s["has_evaluator"]),
            "escalated": kr.get("escalated") if kr else None,
            "kernel_success": kr.get("success") if kr else None,
            "peak_token_pct": kr.get("peak_token_pct") if kr else None,
        },
        "by_goal_task": by_goal,
        "per_step": per_step,
        "kernel_result": kr,
    }


def run_autoclaude(
    playbook_path: Path, config_path: Path, workdir: Path, *, timeout: int = 1200
) -> str:
    """subprocess 真跑 `python -m autoclaude`（副作用——花真 token；不在單測覆蓋）。

    回傳引擎 utf-8 log 文字（`<workdir>/logs/autoclaude.log`）。playbook/config 須絕對路徑
    （cwd=workdir，相對路徑會解析失敗——DEF-77-001 紀律）。
    """
    workdir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "autoclaude", str(Path(playbook_path).resolve()),
           "--config", str(Path(config_path).resolve()), "--fresh"]
    subprocess.run(cmd, cwd=str(workdir), capture_output=True, text=True, timeout=timeout)
    log_file = workdir / "logs" / "autoclaude.log"
    if not log_file.exists():
        raise BridgeE2EError(f"引擎 log 未產生：{log_file}（subprocess 可能啟動即失敗）")
    return log_file.read_text(encoding="utf-8", errors="replace")


@click.command(name="run-bridge-e2e")
@click.option("--source", required=True, type=click.Path(path_type=Path),
              help="three_tier plan YAML（Archy 產物）")
@click.option("--config", type=click.Path(path_type=Path), default=None,
              help="AutoClaude config（真跑用；建議 scripts/ab_configs/ab_pty_config.yaml）")
@click.option("--workdir", type=click.Path(path_type=Path), default=None,
              help="真跑工作目錄（subprocess cwd；省略則僅編譯）")
@click.option("--out", type=click.Path(path_type=Path), default=None,
              help="證據 JSON 輸出（真跑）或 playbook YAML 輸出（--compile-only）")
@click.option("--project-id", default=None, help="多 project 來源時選定哪個")
@click.option("--workflow-type", default="aisdlc_sdd", help="auto | aisdlc | aisdlc_sdd")
@click.option("--compile-only", is_flag=True, default=False,
              help="只編譯不真跑（驗證鏈路前段，不花 token）")
@click.option("--timeout", default=1200, help="真跑 subprocess timeout 秒（預設 1200）")
def cli(source, config, workdir, out, project_id, workflow_type, compile_only, timeout):
    """W-95-2：PRD→playbook 橋接端到端 harness。"""
    try:
        pb, pb_yaml = compile_plan(source, project_id=project_id, workflow_type=workflow_type)
    except Exception as exc:  # noqa: BLE001
        click.echo(f"ERROR: compile 失敗 {type(exc).__name__}: {exc}", err=True)
        sys.exit(2)

    if compile_only or not workdir:
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(pb_yaml, encoding="utf-8")
            click.echo(f"OK(compile-only): {len(pb.tasks)} task → {out}")
        else:
            click.echo(pb_yaml)
        return

    if not config:
        click.echo("ERROR: 真跑須 --config", err=True)
        sys.exit(2)

    pb_path = Path(workdir) / "_compiled_playbook.yaml"
    pb_path.parent.mkdir(parents=True, exist_ok=True)
    pb_path.write_text(pb_yaml, encoding="utf-8")
    click.echo(f"[1/3] 編譯 {len(pb.tasks)} task → {pb_path}")
    click.echo(f"[2/3] 真跑 python -m autoclaude（cwd={workdir}，真 Claude token）…")
    log_text = run_autoclaude(pb_path, Path(config), Path(workdir), timeout=timeout)
    parsed = parse_e2e_log(log_text)
    evidence = build_evidence(pb, parsed, source=str(source), config=str(config))
    agg = evidence["aggregate"]
    click.echo(f"[3/3] 解析：{agg['success_steps']}/{agg['total_steps']} 步成功 "
               f"(pass_rate={agg['pass_rate']}, escalated={agg['escalated']}, "
               f"peak_token_pct={agg['peak_token_pct']})")
    if out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        click.echo(f"OK: 證據 → {out}")
    else:
        click.echo(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cli()
