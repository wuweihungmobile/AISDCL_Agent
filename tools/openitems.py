"""openitems 命令列入口（薄殼：只分派，判準全在 `lib/openitems/`；DES §12）。

用法：python tools/openitems.py [--root <根>] <動詞> [旗標]
  A1 動詞：open｜close｜convert｜retire｜list｜check｜scan；A2 動詞：drive｜run-driver
  （另有 list --verify、scan --stale-pass）
rc：0＝已執行；1＝check／close 的檢查不成立；2＝輸入被拒（帳本不變）；3＝params.json 讀不到；
4＝drive 的排程沒有成立（載具缺／憑證空，帳本不變）。
"""
from __future__ import annotations

import sys

import _stdio_utf8  # noqa: F401  # stdout／stderr 強制 UTF-8 的唯一實作，本檔不另寫
from lib.openitems import verbs

if __name__ == "__main__":
    sys.exit(verbs.main())
