import sys, io, inspect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from importlinter.application import use_cases
src = inspect.getsource(use_cases.lint_imports)
print(src[:3500])
