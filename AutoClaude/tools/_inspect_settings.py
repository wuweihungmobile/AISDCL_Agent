import sys, io, inspect
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import importlinter.adapters.user_options as ua
src = inspect.getsource(ua)
print(src[:1200])
