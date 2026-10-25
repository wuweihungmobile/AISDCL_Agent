package com.aisdlc.console.domain.model.si;

/**
 * 通過輸入閘的關閉觀察命令（TCS-SelfImprovingDecide-P2b W12、表 M-C）。
 *
 * @param obsId       被關閉的 OBS 號（路徑 id；稽核 body 的 {@code obs_id} 與外層 {@code subject}）
 * @param disposition 由終值組成的處置終值全文（例：{@code fixed@2b2b0b3d}、{@code DEF-200-559}、{@code decided：夾具關閉}）
 */
public record SiCloseCommand(String obsId, String disposition) {
}
