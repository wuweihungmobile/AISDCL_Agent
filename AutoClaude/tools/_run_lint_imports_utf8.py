"""Run importlinter contracts via API with UTF-8 stdout (bypass cp950 banner+config crash)."""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Monkey-patch print_title to no-op (banner uses box drawings → cp950 crash)
from importlinter.application import rendering
rendering.print_title = lambda: None

# Patch FILE_SYSTEM.read to force UTF-8 (cp950 default on zh-TW Windows)
from importlinter.adapters import filesystem as _fs

class Utf8FileSystem(_fs.FileSystem):
    def read(self, file_name):
        with open(file_name, 'r', encoding='utf-8') as f:
            return f.read()

from importlinter import configuration
configuration.configure()
# Patch the configured settings (app_config holds FILE_SYSTEM)
from importlinter.application.app_config import settings as _settings
_settings.FILE_SYSTEM = Utf8FileSystem()

from importlinter.application import use_cases
result = use_cases.lint_imports(
    config_filename='.importlinter',
    limit_to_contracts=(),
    is_debug_mode=False,
    show_timings=False,
    verbose=False,
)
print('---')
print('result_bool:', result)
print('PASSED' if result else 'FAILED')
