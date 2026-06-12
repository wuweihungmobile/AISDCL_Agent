import sys, io, inspect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import importlinter.cli as cli
src = inspect.getsource(cli)
print(src[:3000])
