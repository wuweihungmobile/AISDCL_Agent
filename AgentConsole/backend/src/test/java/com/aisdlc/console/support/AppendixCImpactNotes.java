package com.aisdlc.console.support;

/**
 * 契約附錄 C.1／C.2 三個鍵的 {@code impactNote} 原文（v1.3，D-11）。V10 以 {@code (category, key)} 對位逐字寫進
 * {@code system_configs.impact_note}（契約 §0.5 V10 寫入規則④）；{@code SchemaMigrationIT}（全新資料庫）、
 * {@code V5UpgradeMigrationIT}（升級帶資料）與 {@code SettingsReadApiIT}（從 API 看到的）都拿這裡的字串比對。
 * 改動任一邊（契約、V10、本檔）都要三邊一起改。
 */
public final class AppendixCImpactNotes {

    /** C.1 {@code model.enableKernelBrain}。 */
    public static final String ENABLE_KERNEL_BRAIN = "有金鑰時，引擎的 Brain 會在步驟失敗且尚有重試次數時先改寫 prompt 再重試；"
            + "Brain 呼叫失敗則該步驟直接升級。與 agent.enableAutoMutation 及自治等級 ≥6 共用引擎鍵 minimax.enable_kernel_brain"
            + "（任一為真即開）；沒有金鑰時 Console 不送（送了引擎會啟動失敗）；新批次起生效";

    /** C.2 {@code agent.enableAutoMutation}。 */
    public static final String ENABLE_AUTO_MUTATION = "對映引擎 minimax.enable_kernel_brain（Brain 逐步校正：失敗步驟先改寫 prompt 再重試），"
            + "與 model.enableKernelBrain 任一為真即開；自治等級 ≥6 一律視為開啟。需要 model.apiKey：沒有金鑰時不送，"
            + "批次回報 UNAVAILABLE_NO_API_KEY；新批次起生效（§3.4.2）";

    /** C.2 {@code agent.enableSelfEvolution}。 */
    public static final String ENABLE_SELF_EVOLUTION = "引擎沒有演化開關：有金鑰時失敗型 ESCALATION 一律由 Brain 產生演化提案，"
            + "只寫引擎日誌、不套用也不重載（max_evolutions／require_evolution_signoff 在引擎執行路徑上沒有讀者，Console 不送）。"
            + "本鍵只影響沒有金鑰時批次回報 OFF 或 UNAVAILABLE_NO_API_KEY（§3.4.2；E2E 以 model.apiKey 為空關閉演化，§5.0.2）";

    private AppendixCImpactNotes() {
    }
}
