"""BGE-M3 model pre-downloader for TEI local cache.

用途：在 host 上下載 BGE-M3（~1.2GB），建立 HuggingFace hub cache 目錄結構，
再以 bind mount 方式掛給 TEI container，完全繞過 container 內 hf-hub 下載問題。

使用方式：
    python tools/download_bge_m3.py

下載目標：
    <repo>/AutoClaude/.model_cache/   （或由 --cache-dir 指定）

完成後更新 docker-compose.yml 的 tei_cache volume 為 bind mount，
或直接用：
    TEI_CACHE_DIR=<repo>/AutoClaude/.model_cache docker compose up -d embedder
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Download BGE-M3 for TEI local use")
    parser.add_argument(
        "--cache-dir",
        default=str(Path(__file__).resolve().parents[1] / ".model_cache"),
        help="本地快取目錄（預設：<project_root>/.model_cache）",
    )
    parser.add_argument(
        "--model-id",
        default="BAAI/bge-m3",
        help="HuggingFace model ID（預設：BAAI/bge-m3）",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("❌ 請先安裝：pip install huggingface_hub", file=sys.stderr)
        return 1

    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"→ 下載 {args.model_id} 到 {cache_dir}")
    print("  預計大小：~1.2GB，依網速需 1~10 分鐘")
    print("  下載完成後可重複使用（container 重建不需重下載）")
    print()

    try:
        local_path = snapshot_download(
            repo_id=args.model_id,
            cache_dir=str(cache_dir),
            local_files_only=False,
        )
    except Exception as e:
        print(f"❌ 下載失敗：{e}", file=sys.stderr)
        return 1

    print()
    print(f"✅ 下載完成：{local_path}")
    print()
    print("─" * 60)
    print("📋 後續動作：")
    print("  1. 在 docker-compose.yml 將 tei_cache volume 改為 bind mount：")
    print("       volumes:")
    print(f"         - {cache_dir}:/data")
    print("  2. 重啟 embedder：")
    print("       docker compose up -d --force-recreate embedder")
    print("  3. 驗證：")
    print("       curl http://localhost:8080/health")
    return 0


if __name__ == "__main__":
    sys.exit(main())
