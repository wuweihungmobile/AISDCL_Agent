"""共享 CI infra：跨版 pytest 同跑 fail-loud guard（DEF-02-001）.

位於 ``AISDLC_SDD/`` 根（versioned 目錄之外，非任一 ``AISDLC_SDD_v0.0X`` 凍結本體，
免 Copy-on-Evolve）。僅薄包裝 ``scripts/cross_version_guard.py`` 的純偵測邏輯。

載入時機（AutoSDD_improving_05 §2.5 實證）：
- ``cd vX && pytest``（官方 gate）→ rootdir=vX，本 conftest 在 confcutdir 之上，**不載入/不干擾**。
- ``cd AISDLC_SDD && pytest``（bare，最常見 footgun）→ rootdir=AISDLC_SDD，本 conftest 載入。

為何用 ``pytest_configure`` 而非 ``pytest_load_initial_conftests``：後者有 chicken-and-egg
——rootdir conftest 是在該 hook 的 default 實作*之內*才被載入，自身實作不會被回呼（真 repo
實證不 fire）。``pytest_configure`` 時本 conftest 必已註冊，且版本目錄的 ``ImportPathMismatchError``
發生於其後的 collection 階段 → configure 先 raise，攔在碰撞之前。
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
from cross_version_guard import build_guard_message, versions_touched  # noqa: E402


def pytest_configure(config):
    raw_args = list(config.invocation_params.args)
    cwd = str(config.invocation_params.dir)
    versions = versions_touched(raw_args, cwd)
    if len(versions) > 1:
        raise pytest.UsageError(build_guard_message(versions))
