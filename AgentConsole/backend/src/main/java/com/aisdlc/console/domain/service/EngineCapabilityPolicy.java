package com.aisdlc.console.domain.service;

import com.aisdlc.console.domain.model.execution.EngineCapabilities;
import com.aisdlc.console.domain.model.execution.EngineCapabilityState;

/**
 * 自治等級與旗標 → 引擎能力的決策表（契約 §3.4.2「物化決策」；D-11）。純 Java。
 *
 * <pre>
 * effAutoMutation  = agent.enableAutoMutation  ∨ level ≥ 6
 * effSelfEvolution = agent.enableSelfEvolution ∨ level ≥ 7
 * brainRequested   = model.enableKernelBrain   ∨ effAutoMutation
 * hasKey           = model.apiKey 解密後非空
 * </pre>
 * 有金鑰：{@code autoMutation = brainRequested ? ENABLED : OFF}（並明確送 {@code enable_kernel_brain=true|false}），
 * {@code selfEvolution = ENABLED}（引擎沒有演化開關，有金鑰就會在失敗型 ESCALATION 外呼 Brain 提案，與旗標和等級都無關）。
 * 沒有金鑰：Console 不送 {@code minimax.*}（引擎對「{@code enable_kernel_brain=true} 但沒有金鑰」是啟動即失敗，不是忽略），
 * 有人要求的報 {@code UNAVAILABLE_NO_API_KEY}、沒人要求的報 {@code OFF}。
 *
 * <p>回傳值同時是「Console 送進引擎的」與「落庫、回給前端的」：有金鑰時送出的 {@code enable_kernel_brain} 恆等於
 * {@code autoMutation == ENABLED}，兩者不可能各說各話。
 */
public final class EngineCapabilityPolicy {

    /** 自治等級 ≥ 此值視為要求自動突變（PRD §5.3.2：6～10 含自動突變）。 */
    public static final int AUTO_MUTATION_FROM_LEVEL = 6;
    /** 自治等級 ≥ 此值視為要求自演化（PRD §5.3.2：7～10 含自演化）。 */
    public static final int SELF_EVOLUTION_FROM_LEVEL = 7;

    private EngineCapabilityPolicy() {
    }

    public static EngineCapabilities decide(int autonomyLevel, boolean autoMutationFlag, boolean selfEvolutionFlag,
                                            boolean kernelBrainFlag, boolean hasApiKey) {
        boolean effAutoMutation = autoMutationFlag || autonomyLevel >= AUTO_MUTATION_FROM_LEVEL;
        boolean effSelfEvolution = selfEvolutionFlag || autonomyLevel >= SELF_EVOLUTION_FROM_LEVEL;
        boolean brainRequested = kernelBrainFlag || effAutoMutation;
        if (hasApiKey) {
            return new EngineCapabilities(brainRequested ? EngineCapabilityState.ENABLED : EngineCapabilityState.OFF,
                    EngineCapabilityState.ENABLED);
        }
        return new EngineCapabilities(
                brainRequested ? EngineCapabilityState.UNAVAILABLE_NO_API_KEY : EngineCapabilityState.OFF,
                effSelfEvolution ? EngineCapabilityState.UNAVAILABLE_NO_API_KEY : EngineCapabilityState.OFF);
    }
}
