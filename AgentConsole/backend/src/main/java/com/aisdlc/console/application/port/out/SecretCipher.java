package com.aisdlc.console.application.port.out;

/**
 * 敏感參數的加解密埠（NFR-9.2「API Key 等使用 AES-256 加密儲存」）。密文字串格式
 * {@code v1:<iv base64>:<ciphertext base64>}（AES-256-GCM）；金鑰來自 {@code CONSOLE_ENCRYPTION_KEY}。
 * 明文只存在於記憶體：絕不寫日誌、不放進回應（除 ADMIN 的 {@code reveal=true}）。
 */
public interface SecretCipher {

    /** 明文 → {@code v1:<iv>:<密文>}；每次呼叫用新的隨機 IV。 */
    String encrypt(String plainText);

    /** {@code v1:<iv>:<密文>} → 明文；格式不符、被竄改或金鑰不對一律丟 {@link IllegalStateException}。 */
    String decrypt(String stored);
}
