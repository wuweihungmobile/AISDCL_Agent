"""Minimax embo-01 embedding API probe — 一次性實測工具。

用途（SD_Improving_06 W3 前置）：
  1. 確認 Minimax embedding API 端點可達
  2. 取得 embo-01 實際維度（未在公開文件明列）
  3. 驗證 response 格式（用於 MinimaxEmbedderAdapter 實作）
  4. 量測單次呼叫延遲

使用方式：
  方式 A（從 .env 讀，推薦）：
      python tools/probe_minimax_embedding.py

  方式 B（從環境變數讀）：
      export MINIMAX_API_KEY=sk-...
      python tools/probe_minimax_embedding.py

  方式 C（手動指定）：
      python tools/probe_minimax_embedding.py --api-key sk-... --text "測試文字"

輸出範例：
  ✅ Minimax embedding API 連線成功
  Endpoint  : https://api.minimax.chat/v1/embeddings
  Model     : embo-01
  Latency   : 187 ms
  Dimensions: 1536
  Vector[:5]: [-0.0234, 0.0891, ...]

請將輸出的 Dimensions 填入 .env 的 MINIMAX_EMBED_DIMENSIONS=
並更新 docs/04_planning/SD_Improving_05.md §10 第 1 項。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def _load_env_file(env_path: Path) -> dict[str, str]:
    """簡易 .env parser（不依賴 python-dotenv）。"""
    if not env_path.exists():
        return {}
    out: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def probe(
    api_key: str,
    group_id: str,
    base_url: str,
    model: str,
    text: str,
    timeout: int = 30,
) -> dict:
    """呼叫 Minimax embedding API。

    URL 格式（依 LangChain MinimaxEmbeddings 原始碼確認）：
        POST {base_url}?GroupId={group_id}

    Body：
        {"model": "embo-01", "type": "db" | "query", "texts": ["..."]}

    Response：
        {"vectors": [[...]], "base_resp": {...}}
    """
    payload = json.dumps({
        "model": model,
        "type": "query",
        "texts": [text],
    }).encode("utf-8")

    # GroupId 必須以 query parameter 傳遞（不是 header / body）
    url = f"{base_url}?GroupId={urllib.parse.quote(group_id)}"

    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    return {"body": body, "latency_ms": elapsed_ms, "http_status": resp.status, "url": url}


def list_models(api_key: str, region_base: str = "https://api.minimax.io", timeout: int = 15) -> int:
    """呼叫 GET /v1/models 列出可用模型，用於確認 key 有效性與 embo-01 訂閱狀態。"""
    url = f"{region_base}/v1/models"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"❌ HTTP {e.code} {e.reason}", file=sys.stderr)
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"❌ 連線失敗：{e.reason}", file=sys.stderr)
        return 1

    models = body.get("data", [])
    print(f"✅ GET {url} → {len(models)} 個模型")
    embed_found = False
    for m in models:
        mid = m.get("id", "")
        marker = "  ← 嵌入模型" if "emb" in mid.lower() or "embed" in mid.lower() else ""
        if marker:
            embed_found = True
        print(f"  {mid}{marker}")
    if not embed_found:
        print()
        print("⚠️  未找到 embedding 模型（embo-01 未訂閱，或此 endpoint 不列出）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimax embo-01 API probe")
    parser.add_argument("--api-key", help="覆寫 MINIMAX_API_KEY")
    parser.add_argument("--group-id", help="覆寫 MINIMAX_GROUP_ID（必填）")
    parser.add_argument(
        "--base-url",
        help="覆寫 MINIMAX_EMBED_BASE_URL（預設 https://api.minimax.io/v1/embeddings）",
    )
    parser.add_argument("--model", help="覆寫 MINIMAX_EMBED_MODEL（預設 embo-01）")
    parser.add_argument(
        "--text",
        default="AutoClaude 是一套多步驟 Playbook 自動執行引擎。",
        help="用於測試的字串",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="只列出帳號可用模型（不測試 embedding）；用 --region-base 指定區域",
    )
    parser.add_argument(
        "--region-base",
        default="https://api.minimax.io",
        help="list-models 用的區域 base URL（預設 https://api.minimax.io；中國版改 https://api.minimaxi.com）",
    )
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[1]
    env = _load_env_file(project_root / ".env")

    api_key = args.api_key or env.get("MINIMAX_API_KEY") or os.environ.get("MINIMAX_API_KEY", "")

    if args.list_models:
        if not api_key or api_key == "your_minimax_api_key_here":
            print("❌ 找不到 MINIMAX_API_KEY", file=sys.stderr)
            return 2
        return list_models(api_key, region_base=args.region_base)
    group_id = (
        args.group_id
        or env.get("MINIMAX_GROUP_ID")
        or os.environ.get("MINIMAX_GROUP_ID", "")
    )
    base_url = (
        args.base_url
        or env.get("MINIMAX_EMBED_BASE_URL")
        or os.environ.get("MINIMAX_EMBED_BASE_URL")
        or "https://api.minimax.io/v1/embeddings"
    )
    model = (
        args.model
        or env.get("MINIMAX_EMBED_MODEL")
        or os.environ.get("MINIMAX_EMBED_MODEL")
        or "embo-01"
    )

    if not api_key or api_key == "your_minimax_api_key_here":
        print("❌ 找不到 MINIMAX_API_KEY；請先 cp .env.example .env 並填入 API key", file=sys.stderr)
        return 2
    if not group_id or group_id == "your_minimax_group_id_here":
        print(
            "❌ 找不到 MINIMAX_GROUP_ID；embedding API 必填\n"
            "   從 https://platform.minimax.io 帳號頁取得 Group ID 後填入 .env",
            file=sys.stderr,
        )
        return 2

    print(f"→ 呼叫 {base_url}?GroupId={group_id[:6]}***")
    print(f"  Model: {model}")
    print(f"  Text : {args.text!r}")
    print()

    try:
        result = probe(api_key, group_id, base_url, model, args.text)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP {e.code} {e.reason}", file=sys.stderr)
        print(body, file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"❌ 連線失敗：{e.reason}", file=sys.stderr)
        return 1

    body = result["body"]

    # 先檢查 base_resp 是否有錯誤（即使 HTTP 200，Minimax 仍以此欄位回報業務錯誤）
    base_resp = body.get("base_resp") or {}
    status_code = base_resp.get("status_code", 0)
    status_msg = base_resp.get("status_msg", "")
    if status_code != 0:
        print(f"❌ Minimax 業務錯誤：status_code={status_code}", file=sys.stderr)
        print(f"   status_msg: {status_msg}", file=sys.stderr)
        print(f"   完整 response: {json.dumps(body, ensure_ascii=False, indent=2)}", file=sys.stderr)
        print()
        print("常見錯誤對照：", file=sys.stderr)
        print("  1002 → API key 無效或過期", file=sys.stderr)
        print("  1004 → 帳號餘額不足", file=sys.stderr)
        print("  1008 → 模型不存在或未訂閱（請於 platform 訂閱 embo-01）", file=sys.stderr)
        print("  1013 → request 格式錯誤（payload 欄位遺漏）", file=sys.stderr)
        print("  2013 → GroupId 無效", file=sys.stderr)
        print("  2049 → invalid api key — **常見原因：endpoint 區域不匹配**", file=sys.stderr)
        print("         國際版 key（platform.minimax.io 取得）→ 用 api.minimax.io", file=sys.stderr)
        print("         中國版 key（platform.minimaxi.com 取得）→ 用 api.minimaxi.com", file=sys.stderr)
        return 1

    vectors = body.get("vectors") or body.get("data") or body.get("embeddings") or []
    if vectors and isinstance(vectors[0], dict):
        vec = vectors[0].get("embedding") or vectors[0].get("vector") or []
    elif vectors:
        vec = vectors[0]
    else:
        vec = []

    print("✅ Minimax embedding API 連線成功")
    print(f"Endpoint  : {base_url}")
    print(f"Model     : {model}")
    print(f"HTTP      : {result['http_status']}")
    print(f"Latency   : {result['latency_ms']} ms")
    print(f"Dimensions: {len(vec)}")
    if vec:
        preview = ", ".join(f"{v:.4f}" for v in vec[:5])
        print(f"Vector[:5]: [{preview}, ...]")
    print()
    print("Response keys:", list(body.keys()))
    if "usage" in body:
        print("Usage      :", body["usage"])
    print()
    print("─" * 60)
    print("📋 後續動作：")
    print(f"  1. 將 Dimensions={len(vec)} 填入 .env 的 MINIMAX_EMBED_DIMENSIONS=")
    print( "  2. 更新 docs/04_planning/SD_Improving_05.md §10 第 1 項")
    print( "  3. 若維度 != 1024，SD_06 alembic 0007 需 ALTER COLUMN 對應維度")

    return 0


if __name__ == "__main__":
    sys.exit(main())
