/**
 * ResearchToPRD P0 前端夾具的共用常數（TCS-ResearchToPRD-P0-20261102 §5.2「frontend 夾具」）：
 * `tests/fixtures/research/**` 是型別化的 camelCase DTO 黃金資料（沿契約 API_Contract_ResearchToPRD.md §1.3），由 `tests/helpers/research.tsx` 的假後端回放；
 * 三個面板包（FE-A 骨架、FE-B 研究面板、FE-C 工作室）共用同一份，改欄位時 tsc 會在這裡先紅。
 * 不被 vitest 收集、不在 design-rules 掃描面（tests/ 目錄；沿 tests/helpers 先例）。
 */

/** 研究中的專案（topic 步、引擎在跑）。 */
export const R1 = "11111111-1111-4111-8111-111111111111";
/** 規格工作室的專案（studio 步）。 */
export const R2 = "22222222-2222-4222-8222-222222222222";
/** 已凍結的專案（Gate 0 已核准、游標在 route 步；有關聯的 Console 專案）。 */
export const R3 = "33333333-3333-4333-8333-333333333333";

export const CONSOLE_PROJECT_ID = "c0c0c0c0-c0c0-4c0c-8c0c-c0c0c0c0c0c0";
export const CONSOLE_PROJECT_NAME = "Alpha 產品線";

/** 夾具的時間基準（帶 offset；ISO-8601）。 */
export const T0 = "2026-11-02T10:00:00+08:00";
export const T1 = "2026-11-02T10:30:00+08:00";
export const T2 = "2026-11-02T11:00:00+08:00";

/** 64 位十六進位的假雜湊（每個字元一種，方便在斷言裡一眼認出）。 */
export const sha = (char: string): string => char.repeat(64);
