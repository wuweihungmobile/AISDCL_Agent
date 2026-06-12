import sys
import io
import traceback

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Init importlinter settings via configure() — this is what the CLI does
from importlinter.configuration import configure
configure()

from importlinter.application import use_cases
try:
    res = use_cases.lint_imports(verbose=False, is_debug_mode=False)
    print(f"EXIT_CODE={res}")
except Exception:
    traceback.print_exc()
