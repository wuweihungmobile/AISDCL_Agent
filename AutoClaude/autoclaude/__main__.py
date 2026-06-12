"""讓 `python -m autoclaude ...` 可直接執行。"""
from .main import main

if __name__ == "__main__":
    raise SystemExit(main())
