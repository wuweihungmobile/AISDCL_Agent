"""tools/mutmut_exit_code.py 單元測試（SD_09 W1 QA #4 紀律 #4）。

驗證鏡子自身被驗證：bitmask classifier 對所有合法 mutmut 2.4.x exit code
（0~15）都有明確語義，且 CLI 行為與 ps1 / sh 呼叫端期望一致。
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from tools.mutmut_exit_code import (
    BIT_EXCEPTION,
    BIT_SURVIVED,
    BIT_SUSPICIOUS,
    BIT_TIMEOUT,
    MutmutExitStatus,
    classify,
    is_real_failure,
    main,
)


class TestBitmaskConstants:
    """SSOT 鎖定：bit 值對齊 mutmut 2.4.x 文件。"""

    def test_bit_exception_is_1(self):
        assert BIT_EXCEPTION == 1

    def test_bit_survived_is_2(self):
        assert BIT_SURVIVED == 2

    def test_bit_timeout_is_4(self):
        assert BIT_TIMEOUT == 4

    def test_bit_suspicious_is_8(self):
        assert BIT_SUSPICIOUS == 8


class TestClassifyRcZero:
    """rc=0 → 全綠（無 mutant survived / timeout / suspicious / exception）。"""

    def test_zero_is_not_real_failure(self):
        status = classify(0)
        assert status.real_fail is False

    def test_zero_no_flags_set(self):
        status = classify(0)
        assert status.survived is False
        assert status.timeout is False
        assert status.suspicious is False


class TestClassifyRcBit0Exception:
    """bit 0 set → 真實失敗。"""

    def test_rc_1_is_real_failure(self):
        assert is_real_failure(1) is True

    def test_rc_3_bit0_plus_survived_still_real_failure(self):
        # 3 = bit0|bit1 → 既 exception 又有 survived → 仍視為 real_fail
        status = classify(3)
        assert status.real_fail is True
        assert status.survived is True

    def test_rc_15_all_bits_real_failure(self):
        status = classify(15)
        assert status.real_fail is True
        assert status.survived is True
        assert status.timeout is True
        assert status.suspicious is True


class TestClassifyRcSurvivedOnly:
    """bit 1 set only（rc=2）→ 觀察期預期，非 real_fail。"""

    def test_rc_2_is_not_real_failure(self):
        assert is_real_failure(2) is False

    def test_rc_2_has_survived_flag(self):
        status = classify(2)
        assert status.survived is True
        assert status.timeout is False
        assert status.suspicious is False
        assert status.real_fail is False


class TestClassifyRcTimeoutOnly:
    """bit 2 set only（rc=4）→ 容忍，非 real_fail。"""

    def test_rc_4_is_not_real_failure(self):
        assert is_real_failure(4) is False

    def test_rc_4_has_timeout_flag(self):
        status = classify(4)
        assert status.timeout is True
        assert status.survived is False


class TestClassifyRcSuspiciousOnly:
    """bit 3 set only（rc=8）→ 容忍，非 real_fail。"""

    def test_rc_8_is_not_real_failure(self):
        assert is_real_failure(8) is False

    def test_rc_8_has_suspicious_flag(self):
        status = classify(8)
        assert status.suspicious is True


class TestClassifyMixedRc:
    """組合 bit set → 各 flag 反映正確。"""

    def test_rc_6_timeout_plus_survived(self):
        # 6 = bit1|bit2
        status = classify(6)
        assert status.survived is True
        assert status.timeout is True
        assert status.suspicious is False
        assert status.real_fail is False  # bit0=0

    def test_rc_14_survived_timeout_suspicious(self):
        # 14 = bit1|bit2|bit3
        status = classify(14)
        assert status.survived is True
        assert status.timeout is True
        assert status.suspicious is True
        assert status.real_fail is False  # bit0=0

    def test_rc_10_survived_plus_suspicious(self):
        # 10 = bit1|bit3
        status = classify(10)
        assert status.survived is True
        assert status.suspicious is True
        assert status.timeout is False
        assert status.real_fail is False


class TestNegativeRc:
    """signal kill（如 -9）→ 視為真實失敗，避免誤通過。"""

    def test_negative_rc_is_real_failure(self):
        assert is_real_failure(-1) is True

    def test_negative_sigkill(self):
        status = classify(-9)
        assert status.real_fail is True
        # 其他 flag 預設 False
        assert status.survived is False
        assert status.timeout is False
        assert status.suspicious is False


class TestExhaustiveBitmaskValues:
    """覆蓋 0~15 所有合法 mutmut bitmask 值。"""

    @pytest.mark.parametrize("rc", list(range(16)))
    def test_real_fail_iff_bit0(self, rc):
        """real_fail 為 True iff (rc & 1) != 0。"""
        status = classify(rc)
        expected = (rc & 1) != 0
        assert status.real_fail is expected, f"rc={rc} mismatch"

    @pytest.mark.parametrize("rc", list(range(16)))
    def test_survived_iff_bit1(self, rc):
        status = classify(rc)
        assert status.survived is bool(rc & 2)

    @pytest.mark.parametrize("rc", list(range(16)))
    def test_timeout_iff_bit2(self, rc):
        status = classify(rc)
        assert status.timeout is bool(rc & 4)

    @pytest.mark.parametrize("rc", list(range(16)))
    def test_suspicious_iff_bit3(self, rc):
        status = classify(rc)
        assert status.suspicious is bool(rc & 8)


class TestMutmutExitStatusDataclass:
    def test_to_dict_contains_all_fields(self):
        status = MutmutExitStatus(
            rc=6, real_fail=False, survived=True, timeout=True, suspicious=False,
        )
        d = status.to_dict()
        assert d == {
            "rc": 6, "real_fail": False, "survived": True,
            "timeout": True, "suspicious": False,
        }

    def test_dataclass_is_frozen(self):
        status = classify(0)
        with pytest.raises(Exception):
            status.real_fail = True  # type: ignore[misc]


class TestCli:
    """CLI 行為（給 ps1 / sh 呼叫）— 退出碼 + stdout JSON。"""

    def test_classify_rc_zero_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "tools/mutmut_exit_code.py", "classify", "0"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["real_fail"] is False
        assert data["rc"] == 0

    def test_classify_rc_one_exits_one(self):
        """bit0 set → CLI 退出碼=1（給 stage 判 fail 用）。"""
        result = subprocess.run(
            [sys.executable, "tools/mutmut_exit_code.py", "classify", "1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 1
        data = json.loads(result.stdout)
        assert data["real_fail"] is True

    def test_classify_rc_two_exits_zero_with_survived_flag(self):
        """bit1 only（survived）→ 退出碼=0（觀察期預期），但 JSON 留 survived=True。"""
        result = subprocess.run(
            [sys.executable, "tools/mutmut_exit_code.py", "classify", "2"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["real_fail"] is False
        assert data["survived"] is True

    def test_classify_rc_six_exits_zero(self):
        """survived+timeout → 仍非 real_fail。"""
        result = subprocess.run(
            [sys.executable, "tools/mutmut_exit_code.py", "classify", "6"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        assert result.returncode == 0


class TestMainFunction:
    """直接 call main() 確認 exit 行為（不經 subprocess）。"""

    def test_main_zero_returns_zero(self, capsys):
        rc = main(["classify", "0"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["real_fail"] is False

    def test_main_one_returns_one(self, capsys):
        rc = main(["classify", "1"])
        assert rc == 1

    def test_main_negative_returns_one(self, capsys):
        rc = main(["classify", "-9"])
        assert rc == 1
