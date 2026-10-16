package com.aisdlc.console.adapter.out.bridge;

import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Bridge 自由文字進入 Console 時去掉行程編號（契約 §1.2.3「不外露 pid」、E2E-14 第 8 列「回應與日誌沒有 pid」）。
 * 為什麼重要：Bridge 每個 run 一開始的狀態文字就是 {@code 引擎已啟動（pid=…，第 n 次 spawn）}；Console 若逐字轉成批次詳情的
 * {@code reason} 與 SSE 的 {@code status-change}，每一個執行中的批次都會把引擎行程編號洩給前端。
 */
class BridgeTextTest {

    @Test
    void theEngineStartedReasonLosesItsPidButKeepsTheRestOfTheSentence() {
        assertThat(BridgeText.withoutPid("引擎已啟動（pid=12345，第 1 次 spawn）")).isEqualTo("引擎已啟動（第 1 次 spawn）");
        assertThat(BridgeText.withoutPid("引擎已啟動（pid=7,第 12 次 spawn）")).isEqualTo("引擎已啟動（第 12 次 spawn）");
    }

    @Test
    void theForceKillAlertLosesTheListOfPids() {
        assertThat(BridgeText.withoutPid("終止訊號後 5s 仍未退出，已強制終止 pid=[4242, 4243]"))
                .isEqualTo("終止訊號後 5s 仍未退出，已強制終止");
        assertThat(BridgeText.withoutPid("已強制終止 pid=[]")).isEqualTo("已強制終止");
    }

    @Test
    void severalPidsAndOtherSpellingsAreAllRemoved() {
        assertThat(BridgeText.withoutPid("a pid=1，b PID: 22 c")).isEqualTo("a b c");
        assertThat(BridgeText.withoutPid("全形 pid：99，後面")).isEqualTo("全形 後面");
    }

    @Test
    void textWithoutAPidIsReturnedUnchangedIncludingWordsThatMerelyContainTheLetters() {
        for (String text : new String[] {"", "引擎正常結束", "引擎升級（ESCALATION）：任務「初始化」重試 1 次仍失敗",
                "rapid=3 and stupid=4", "pidgin 9", "pid", "pid=abc"}) {
            assertThat(BridgeText.withoutPid(text)).as(text).isEqualTo(text);
        }
        assertThat(BridgeText.withoutPid(null)).isNull();
    }
}
