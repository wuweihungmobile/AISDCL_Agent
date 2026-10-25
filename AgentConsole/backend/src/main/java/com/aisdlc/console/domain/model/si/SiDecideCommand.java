package com.aisdlc.console.domain.model.si;

import java.util.List;

/**
 * 通過輸入閘的決定命令（TCS-SelfImprovingDecide-P2b W12、表 M-D）：欄位已 trim、值域已驗、「禁止欄」已確認為空；
 * 稽核 body 的鍵序與哪些鍵會出現由簽章器決定（{@code digest} 只在六種動詞、{@code reason_class} 只在三種、{@code reason} 只在五種）。
 *
 * @param subject     PROP 號；{@code resume} 為 RUN 號（稽核 body 的 {@code prop}／{@code run} 與外層 {@code subject}）
 * @param dkind       九種動詞之一
 * @param digest      卡面 digest（{@code sha256:} 接 64 位小寫十六進位）；rollback、unblock、resume 為 {@code null}
 * @param reasonClass 理由類別（七值之一）；只有 reject、decline-promote、return 非 {@code null}
 * @param reason      理由（1～500 個 code point）；只有 reject、decline-promote、return、rollback、resume 非 {@code null}
 * @param flags       恆在；只有 promote 可含 {@code unverified_ack}（晉升後式）
 */
public record SiDecideCommand(String subject, String dkind, String digest, String reasonClass, String reason,
                              List<String> flags) {

    public SiDecideCommand {
        flags = flags == null ? List.of() : List.copyOf(flags);
    }
}
