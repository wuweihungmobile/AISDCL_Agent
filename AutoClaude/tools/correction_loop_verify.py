"""correction_loop_verify.py — self-correction 閉環「端到端真跑」驗證載具（improving_87 W-87-1/2）。

驗證「Brain 指揮 Claude Code」的 self-correction 閉環是否真的端到端串起來：
  ①真 Claude 執行失敗 → ②Kernel 呼叫 Brain（decide_correction）→ ③Brain 回 CORRECTION 修正
  prompt → ④Kernel 把修正 prompt 餵回 Executor（task.prompt 改寫）→ ⑤真 Claude 改行為重試 → 成功。

設計要點：
  - `parse_correction_evidence(log_text)` 為**純函式**（無副作用、可單元測，RTM-87-1/3）：
    從 autoclaude 執行 log 解析 correction marker 次數、最終 success/escalation 兩態。
  - `main` orchestration（真跑、耗 claude 額度，非單元測）：起 mock server（--mock）→ 臨時 workdir
    跑 autoclaude correction_loop_smoke.yaml → 讀 logs/autoclaude.log → 解析 + GET /stats → 報告。
    為避免 capture pipe 干擾 claude PTY，**不攔 autoclaude stdout**，改讀其 file handler 寫的 log。

用法（於 AutoClaude/ 目錄）：
  W-87-1（mock brain × 真 Claude）：
    python tools/correction_loop_verify.py --mock
  W-87-2（真 Minimax × 真 Claude，先把 .env 匯入環境）：
    set -a && . ./.env && set +a
    python tools/correction_loop_verify.py --config scripts/ab_configs/correction_real_config.yaml

退碼：0=閉環成立（correction≥1 且最終 success；mock 另需 /stats.post_count≥1）；1=未成立；≥2=載具錯誤。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

_RE_CORRECTION = re.compile(r"=== STATE: CORRECTION \| step=(\S+) attempt=(\d+) ===")
# improving_90 W-90-2：production Kernel `_preserve_output_contract` 實際附加 regex 約束時發此
# marker（kernel.py），用以驗 DEF-87-001 修復路徑在真模型 CORRECTION 迴圈中確被觸發。
_RE_REGEX_PRESERVED = re.compile(r"=== REGEX CONTRACT PRESERVED \| step=(\S+) ===")


def parse_correction_evidence(log_text: str) -> dict:
    """純函式：從 autoclaude 執行 log 解析 self-correction 閉環證據。

    回傳:
      correction_count: `=== STATE: CORRECTION | ... ===` marker 出現次數
                        （Brain 真被 Kernel 呼叫且回非空決策 → 唯一發此 marker 的路徑）。
      final_success:    末段（最後一筆 "Playbook 結束" 之後）的 result repr 是否 success=True；
                        success=False → False；無法判定 → None（誠實留 None，不臆測）。
      escalated:        最終 result 是否 escalated=True 或 reason 含 max_retries_exhausted。
      regex_contract_preserved: `=== REGEX CONTRACT PRESERVED | ... ===` marker 出現次數
                        （improving_90 W-90-2：Kernel 在 step 同掛 regex+evaluator 時，套用 Brain
                        CORRECTION 後仍把 expected_output_regex 約束保留回修正 prompt 的唯一路徑；
                        >=1 即證 DEF-87-001 修復在真模型迴圈中被觸發）。
    """
    correction_count = len(_RE_CORRECTION.findall(log_text))
    regex_contract_preserved = len(_RE_REGEX_PRESERVED.findall(log_text))

    idx = log_text.rfind("Playbook 結束")
    tail = log_text[idx:] if idx >= 0 else log_text
    final_success: bool | None = None
    if re.search(r"success=True", tail):
        final_success = True
    elif re.search(r"success=False", tail):
        final_success = False

    escalated = bool(re.search(r"escalated=True", tail) or re.search(r"max_retries_exhausted", tail))

    return {
        "correction_count": correction_count,
        "final_success": final_success,
        "escalated": escalated,
        "regex_contract_preserved": regex_contract_preserved,
    }


def _start_inproc_mock() -> tuple[ThreadingHTTPServer, int]:
    """於 carrier 程序內起 mock_brain_server（port 0 自動選埠），重置 _STATS。

    同程序 threaded server（非 subprocess）以根治：Windows subprocess terminate 殺不乾淨
    → 殘留 server 佔埠致後續真跑 /stats 對不上（W-87-1 首跑 DEF-87-003）。post_count 可
    直接從模組 _STATS 讀（autoclaude 子程序經 HTTP 連入本程序的 thread server）。
    """
    import tools.mock_brain_server as mbs

    mbs._STATS["post_count"] = 0
    mbs._STATS["decision_types"] = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), mbs._Handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def run_verification(
    *, mock: bool, config: str, playbook: str, repo_root: Path, timeout: int = 900
) -> int:
    """真跑 orchestration（耗 claude 額度）。回傳行程退碼。"""
    workdir = Path(tempfile.mkdtemp(prefix="corr_loop_"))
    env = dict(os.environ)
    srv: ThreadingHTTPServer | None = None
    try:
        if mock:
            srv, real_port = _start_inproc_mock()
            # 顯式覆蓋環境，確保即使殘留真 key 也走 mock（env 優先於 config，main.py:106）。
            env["MINIMAX_BASE_URL"] = f"http://127.0.0.1:{real_port}/v1/chat/completions"
            env["MINIMAX_API_KEY"] = "mock"
            env["MINIMAX_MODEL"] = "mock-brain"
        else:
            if not env.get("MINIMAX_API_KEY"):
                print("[verify] ❌ 非 mock 模式但環境無 MINIMAX_API_KEY（請先匯入 .env）",
                      file=sys.stderr)
                return 4

        cmd = [sys.executable, "-m", "autoclaude",
               str(repo_root / playbook), "--config", str(repo_root / config), "--fresh"]
        print(f"[verify] 真跑：{' '.join(cmd)} (cwd={workdir}, mock={mock})")
        # 不攔 stdout/stderr（PTY-safe）；證據改讀 autoclaude file handler 的 log。
        proc = subprocess.run(cmd, cwd=str(workdir), env=env, timeout=timeout)

        log_file = workdir / "logs" / "autoclaude.log"
        log_text = log_file.read_text(encoding="utf-8", errors="replace") if log_file.exists() else ""
        evidence = parse_correction_evidence(log_text)
        # post_count 直接讀本程序 mock 的 _STATS（同程序，免 HTTP 對埠失準）。
        post_count = 0
        decision_types: list = []
        if mock:
            import tools.mock_brain_server as mbs
            post_count = mbs._STATS["post_count"]
            decision_types = list(mbs._STATS["decision_types"])

        print("\n========== self-correction 閉環真跑證據 ==========")
        print(f"  autoclaude 退碼            : {proc.returncode}")
        print(f"  CORRECTION marker 次數     : {evidence['correction_count']}  (RTM-87-1, 需 >=1)")
        print(f"  REGEX CONTRACT PRESERVED   : {evidence['regex_contract_preserved']}  "
              f"(RTM-90-5, regex+evaluator 雙閘 playbook 需 >=1)")
        print(f"  最終 success               : {evidence['final_success']}  (RTM-87-3)")
        print(f"  escalated                  : {evidence['escalated']}")
        if mock:
            print(f"  mock _STATS.post_count     : {post_count}  "
                  f"(RTM-87-2, 需 >=1)  decision_types={decision_types}")
        print("==================================================\n")

        ok = evidence["correction_count"] >= 1 and evidence["final_success"] is True
        if mock:
            ok = ok and post_count >= 1
        if ok:
            print("[verify] OK 閉環成立：Brain 真被呼叫 -> 修正 prompt 餵回 -> 真 Claude 改對 -> 成功")
            return 0
        print("[verify] WARN 閉環未成立（見上方證據；誠實兩態：未成功或未觸發 CORRECTION）")
        return 1
    finally:
        if srv is not None:
            srv.shutdown()
            srv.server_close()
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="self-correction 閉環端到端真跑驗證")
    parser.add_argument("--mock", action="store_true",
                        help="於 carrier 程序內起 mock_brain_server 當指揮官（W-87-1）；不加則用環境中的真 MINIMAX_*（W-87-2）")
    parser.add_argument("--config", default="scripts/ab_configs/correction_mock_config.yaml")
    parser.add_argument("--playbook", default="scripts/correction_loop_smoke.yaml")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    # Windows console 預設 cp950 無法編碼報告中的非 ASCII（✅/≥）；強制 utf-8 避免載具自身崩潰。
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass
    repo_root = Path(__file__).resolve().parents[1]
    return run_verification(
        mock=args.mock, config=args.config,
        playbook=args.playbook, repo_root=repo_root, timeout=args.timeout,
    )


if __name__ == "__main__":
    raise SystemExit(main())
