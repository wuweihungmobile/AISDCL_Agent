package com.aisdlc.console.application.service;

import com.aisdlc.console.application.port.in.ExecutionStreamUseCase.Frame;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * {@code Last-Event-ID} 的解析（契約 §2.3 第 1 點）。為什麼重要：瀏覽器與代理會原樣回送上次收到的 id，也可能被使用者或腳本亂填；
 * 格式不合必須「當作沒帶」（從頭重播）而不是 400 或 500——重連失敗的串流使用者看不到任何錯誤，只會覺得即時畫面壞了。
 * 順序鍵必須與 {@link Frame#order()} 同一套（{@code 41 < 41.1 < 41.2 < 42}），否則重播的切點會差一個框架。
 */
class StreamServiceTest {

    @Test
    void aBridgeSeqAndAConsoleSubSequenceBothParseIntoTheSameOrderKeyAsTheFramesUse() {
        assertThat(StreamService.parseLastEventId("41")).isEqualTo(Frame.orderOf(41, 0));
        assertThat(StreamService.parseLastEventId("41.2")).isEqualTo(Frame.orderOf(41, 2));
        assertThat(StreamService.parseLastEventId("0")).isEqualTo(0L);
        assertThat(StreamService.parseLastEventId("41")).isLessThan(StreamService.parseLastEventId("41.1"));
        assertThat(StreamService.parseLastEventId("41.2")).isLessThan(StreamService.parseLastEventId("42"));
    }

    @Test
    void surroundingWhitespaceIsIgnored() {
        assertThat(StreamService.parseLastEventId("  41.2  ")).isEqualTo(Frame.orderOf(41, 2));
    }

    @Test
    void anythingThatIsNotAnIdIsTreatedAsNotSent() {
        for (String bad : new String[] {"", " ", "abc", "41.", ".2", "-1", "41.-2", "41.2.3", "4 1", "0x10", "41,2",
                "１２", "99999999999", "41.99999999999", "41.2abc"}) {
            assertThat(StreamService.parseLastEventId(bad)).as("「%s」", bad).isNull();
        }
        assertThat(StreamService.parseLastEventId(null)).isNull();
    }
}
