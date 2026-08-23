"""靜態詞彙掃描的共用判準（鐵律五 hook 的判準形態，用於 R100 的 D1／G9 兩格）。

🔴 為什麼一定要 AST 而不是行掃描：禁用動詞**必須**能出現在註解與 docstring 裡
（那些段落的工作就是解釋「為什麼不用它」），而字串掃描分不出「指令字面」與「在講它」。
本輪落地當回合就踩到一次：`reset --hard` 寫在 docstring 裡，行掃描版當場假紅。
判準＝「非 docstring 的字串常數」，那正好就是 argv 元素與拼出來的指令字串所在的位置。
"""
from __future__ import annotations

import ast
from pathlib import Path


def command_string_literals(module_file: str | Path) -> list[str]:
    tree = ast.parse(Path(module_file).read_text(encoding="utf-8"))
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            docstrings.add(id(node.value))
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and id(n) not in docstrings]


def forbidden_hits(module_file: str | Path, forbidden: tuple[str, ...]) -> list[str]:
    blob = "\n".join(command_string_literals(module_file))
    return [bad for bad in forbidden if bad in blob]
