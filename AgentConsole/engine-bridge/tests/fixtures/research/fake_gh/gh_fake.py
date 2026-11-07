"""假 gh（ResearchToPRD P1 的 hermetic 夾具；`gh.cmd`／`gh` 薄殼呼叫它）。

行為由環境變數切換（TCS §5.2、IFACE §9.2）：
  FAKE_GH_MODE   ok（預設）｜unauth（`auth status` rc 1）｜
                 fail-create（`repo create` rc 1、權限不足）｜
                 leak（刻意把 GH_TOKEN 的值印到 stdout 與 stderr，模擬 gh 洩漏）
  FAKE_GH_LOG    每次呼叫追加一行 JSON：argv（不含 token）、環境鍵名單、是否有 GH_TOKEN、cwd
  FAKE_GH_REQUIRE_TOKEN=1  沒有 GH_TOKEN 時 `auth status` 失敗（模擬「無 token」）
只用標準庫、不連網。
"""
from __future__ import annotations

import json
import os
import sys


def main(argv: list[str]) -> int:
    mode = os.environ.get("FAKE_GH_MODE", "ok")
    token = os.environ.get("GH_TOKEN")
    log = os.environ.get("FAKE_GH_LOG")
    if log:
        with open(log, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps({"argv": argv, "env_keys": sorted(os.environ),
                                 "has_gh_token": token is not None, "cwd": os.getcwd()},
                                ensure_ascii=False) + "\n")
    if mode == "leak" and token:
        print(f"debug token={token}")
        print(f"debug token={token}", file=sys.stderr)
    if argv[:2] == ["auth", "status"]:
        if mode == "unauth" or (os.environ.get("FAKE_GH_REQUIRE_TOKEN") == "1" and not token):
            print("You are not logged into any GitHub hosts.", file=sys.stderr)
            return 1
        print("Logged in to github.com account fake-user")
        return 0
    if argv[:2] == ["repo", "create"] and len(argv) >= 3:
        if mode == "fail-create":
            print("HTTP 403: Resource not accessible by personal access token (permission denied)",
                  file=sys.stderr)
            return 1
        print(f"https://github.com/{argv[2]}")
        return 0
    print(f"fake gh: unsupported {argv}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
