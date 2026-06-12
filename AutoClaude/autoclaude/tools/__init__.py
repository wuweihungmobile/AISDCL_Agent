"""autoclaude.tools — CLI 薄殼工具子套件（AutoSDD_improving_01 §3.3，W4）。

定位：compile-then-run 兩段式的「第一段」工具群。本子套件不在 core-purity
contract 的 source_modules 內，import infra adapter 合法；不得被 core/ 反向
import（core 僅認識 ports）。
"""
