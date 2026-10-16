package com.aisdlc.console.domain.model.execution;

/**
 * 一個批次的引擎能力狀態（契約 §3.4.2；{@code execution_runs.engine_capabilities}、{@code ExecutionRunResponse.engineCapabilities}）。
 *
 * <ul>
 *   <li>{@code autoMutation}：對映引擎的 {@code minimax.enable_kernel_brain}（Brain 逐步校正：失敗步驟尚有重試次數時先由 Brain 改寫
 *       prompt 再重試；Brain 呼叫失敗則該步驟直接升級）；</li>
 *   <li>{@code selfEvolution}：引擎沒有演化開關，<b>有金鑰就是 {@code ENABLED}</b>（失敗型 ESCALATION 時由 Brain 產生演化「提案」，
 *       只寫引擎日誌、不套用）；沒有金鑰時只決定報 {@code OFF} 還是 {@code UNAVAILABLE_NO_API_KEY}。</li>
 * </ul>
 * 由 {@link com.aisdlc.console.domain.service.EngineCapabilityPolicy} 產生時兩個欄位一定有值；任一欄位為 null 只發生在讀回資料庫時
 * 該鍵缺席或值不認得（前向相容，不猜測）。整個物件為 null＝V10 之前建立的批次（當時送了什麼已不可考，不回填）。
 */
public record EngineCapabilities(EngineCapabilityState autoMutation, EngineCapabilityState selfEvolution) {
}
