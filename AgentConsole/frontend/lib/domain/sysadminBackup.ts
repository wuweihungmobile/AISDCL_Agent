/**
 * 系統管理／資料庫備份的純函式與詞表（TCS-SysAdminBackup-20261027 §5.3、R-BK-06、R-BK-10～13、R-BK-22、R-BK-26、R-BK-43、R-BK-44、R-BK-60；PRD §5 FR-BK-02～05、08）。
 * 元件（`components/domain/sysadmin/**`）只負責排版與互動，所有「文字長什麼樣、什麼時候是警示色」都在這裡，由 `sysadminBackup.test.ts` 逐筆釘住。
 *
 * 設計要點（為什麼這樣做）：
 *  - **前端不算時間、不判逾期**：`overdue`、`lastDueAt`、`nextRunAt` 一律是 console-api 以排程時區算好的結果，這裡只負責把它們寫成字（本檔沒有 cron 函式庫、沒有任何寬限分鐘的常數、
 *    沒有對 `lastDueAt` 的算術或比較）。cron 白話化（`humanizeCron`）只認三種形狀，其餘原字串退回——不猜、不丟例外。
 *  - **量不到絕不顯示成 0**：缺值一律「—」；整個區塊為 null（控制面未設定、匯出壞掉）由元件改顯示原因，不顯示空表、不顯示 0 份。
 *  - **詞表是單一份**：狀態、種類、儲存位置、工作狀態、repo 狀態碼、reason 訊息、排程工作名都在本檔；測試與元件引用同一份。日後 backend 新增的值（reason、warnings、狀態）
 *    原樣顯示，不崩潰、不吞掉。
 *  - 格式化沿用既有函式（`formatDateTime`、`formatClock`、`@/lib/domain/metrics` 的 `formatDuration`、`formatBytes`）：本檔只匯入、不自己再定義同名函式（靜態鎖 AT_BK_02_3_2）。
 */
import { formatDateTime } from "@/lib/format";
import type { BackupCard, BackupRepoRetention, BackupRetention, BackupRow, BackupWalArchive } from "@/lib/api/types";

/** 語意色階：元件把它對映成設計 token（ok＝成功、warn＝注意、danger＝失敗或警示、info＝進行中、muted＝沒有資料）。 */
export type BackupTone = "ok" | "warn" | "danger" | "info" | "muted";

const DASH = "—";

// ── 卡片狀態（D-BK-T9）──────────────────────────────────────────────────────────────────────────
/** 卡片狀態文字（UI 文字加 Lucide 圖示，不得只有顏色）；不認得的狀態原樣顯示。 */
export const CARD_STATUS_TEXT: Readonly<Record<string, string>> = {
  succeeded: "成功",
  failed: "失敗",
  running: "進行中",
  interrupted: "中斷",
  no_run: "從未執行",
};

/** 卡片狀態的色階：失敗與中斷同為警示色（中斷＝工作沒做完）；不認得的狀態用 warn（不假裝成功）。 */
export const CARD_STATUS_TONE: Readonly<Record<string, BackupTone>> = {
  succeeded: "ok",
  failed: "danger",
  running: "info",
  interrupted: "danger",
  no_run: "muted",
};

export const cardStatusText = (status: string): string => CARD_STATUS_TEXT[status] ?? status;
export const cardStatusTone = (status: string): BackupTone => CARD_STATUS_TONE[status] ?? "warn";

/** 最近一次執行的觸發：排程或手動；無狀態檔（null）顯示「—」。 */
export function triggerText(trigger: string | null | undefined): string {
  if (trigger === "scheduled") return "排程";
  if (trigger === "manual") return "手動";
  return trigger ?? DASH;
}

/** 「最近一次成功」那一行：失敗不覆蓋較早的成功；從未成功寫「從未成功」，不寫「—」也不寫時間。 */
export function lastSuccessText(card: Pick<BackupCard, "lastSuccessAt">): string {
  return card.lastSuccessAt ? `最近一次成功：${formatDateTime(card.lastSuccessAt)}` : "最近一次成功：從未成功";
}

// ── 備份清單（R-BK-04～09）──────────────────────────────────────────────────────────────────────
/** 備份種類：full、diff（專案的 `backup-incr.sh` 實為差異備份）、incr、logical。 */
export const BACKUP_KIND_TEXT: Readonly<Record<string, string>> = {
  full: "全備",
  diff: "增備（差異）",
  incr: "增量",
  logical: "邏輯備份",
};
export const backupKindText = (kind: string): string => BACKUP_KIND_TEXT[kind] ?? kind;

/** 儲存位置：repo1 為本地、repo2 為離站、logical 為離站邏輯備份；其他 repo 編號原樣顯示。 */
export function backupLocationText(location: string): string {
  if (location === "repo1") return "本地 repo1";
  if (location === "repo2") return "離站 repo2";
  if (location === "logical") return "離站邏輯";
  return location;
}

/** 備份結果：info 的 `error:true`（頁校驗錯誤）＝「成功，但有校驗錯誤」並帶警示色；清單只含成功建立的備份，所以沒有「失敗」。 */
export function backupResultText(result: string): { text: string; tone: BackupTone } {
  if (result === "ok") return { text: "成功", tone: "ok" };
  if (result === "ok_with_errors") return { text: "成功，但有校驗錯誤", tone: "warn" };
  return { text: result, tone: "warn" };
}

/** pgBackRest 的 repo 狀態碼（`info.repo[].status.code`）的中文說明。 */
export const REPO_STATUS_ZH: Readonly<Record<number, string>> = {
  0: "正常",
  1: "缺 stanza 路徑",
  2: "尚無有效備份",
  3: "缺 stanza 資料",
  4: "repo 之間不一致",
  5: "資料庫不符",
  6: "找不到備份",
  99: "其他",
};

/**
 * repo 狀態碼 → 一句中文：0＝「正常」；已知的非零碼取表；表外的碼（含非數字）退回含該值的「其他」兜底，不丟例外。
 * `message` 是 pgBackRest 的英文原文，只在表外的碼才附上（那是唯一沒有中文說明的情況）。
 */
export function repoStatusText(code: number, message?: string): string {
  const known = Object.hasOwn(REPO_STATUS_ZH, code) ? REPO_STATUS_ZH[code] : undefined;
  if (known !== undefined) return known;
  const original = message ? `，原文：${message}` : "";
  return `其他（狀態碼 ${String(code)}${original}）`;
}

/** repo 狀態列的一句話：0＝「正常」；已知的非零碼＝「狀態碼 N：<中文說明>」（例：狀態碼 99：其他）；表外的碼由 `repoStatusText` 的兜底文字帶出（已含狀態碼）。 */
export function repoStatusLine(code: number, message?: string): string {
  if (code === 0) return repoStatusText(0);
  return Object.hasOwn(REPO_STATUS_ZH, code) ? `狀態碼 ${code}：${repoStatusText(code)}` : repoStatusText(code, message);
}

/** 本機磁碟（posix）的 repo 沒有端點主機；有端點主機的是 S3 相容的離站 repo。 */
export const isOffsiteRepo = (repo: { endpointHost: string | null }): boolean => repo.endpointHost !== null;

/** 離站 repo 的位置徽章：本機 MinIO 與主機同碟（主機損毀時一併消失），否則是外部 S3。本機時任何處都不得稱「離站已安全」。 */
export const LOCAL_MINIO_NOTE = "本機 MinIO・與主機同碟，主機損毀時一併消失";
export const EXTERNAL_S3_NOTE = "外部 S3";
export const offsiteBadgeText = (local: boolean): string => (local ? LOCAL_MINIO_NOTE : EXTERNAL_S3_NOTE);
/** 離站 pg_dump 卡的位置說明：邏輯備份上傳到離站 repo 的同一個端點，所以與離站 repo 的「同碟與否」同判。 */
export const dumpOffsiteNote = (local: boolean): string => (local ? "與主機同碟：離站備份放在本機 MinIO，主機損毀時也會一併消失" : `離站位置：${EXTERNAL_S3_NOTE}`);

/** 備份清單的固定說明列：失敗的工作不在清單裡（清單只含成功建立的備份）。 */
export const LIST_NOTE = "失敗的工作看狀態卡與工作紀錄";
export const LIST_EMPTY_TEXT = "尚無備份：首次部署後請立刻做第一份全備";

// ── 排程與保留（R-BK-10～13）────────────────────────────────────────────────────────────────────
/** 排程工作名（D-BK-T8）；清理類兩項是維護工作，名稱內帶「（維護工作）」。 */
export const SCHEDULE_JOB_LABELS: Readonly<Record<string, string>> = {
  full: "全備",
  diff: "增備（差異）",
  dump: "離站 pg_dump",
  verify: "驗證",
  expire: "清理過期備份（維護工作）",
  wal_clean: "清理 WAL 複本（維護工作）",
};
export const scheduleJobLabel = (job: string): string => SCHEDULE_JOB_LABELS[job] ?? job;

/** 固定列：WAL 是持續歸檔，不在 crontab 裡。 */
export const WAL_FIXED_ROW_TEXT = "WAL 持續歸檔（有寫入時約每 60 秒一段）";

const WEEKDAY = ["日", "一", "二", "三", "四", "五", "六"] as const;
const pad2 = (n: number): string => String(n).padStart(2, "0");

/**
 * cron 白話化：只認三式 `m h * * d`（d 為 0～6）、`m h * * a-b`（0≤a<b≤6）、`m h * * *`，回「每週<星期> HH:MM」「每週<a>至週<b> HH:MM」「每日 HH:MM」。
 * 其餘一律**原字串**回傳（不 trim、不猜、不丟例外）：星期欄 7、列表式、名稱式、步進式、欄數不是五、數值越界、反向範圍都算不認得。
 * 刻意以「恰好單一空白分隔、無前後空白」的嚴格形狀判斷——寬鬆解析等於替 backend 沒驗過的字串猜意思。
 */
export function humanizeCron(cron: string): string {
  if (typeof cron !== "string") return "";
  const m = /^(\d{1,2}) (\d{1,2}) \* \* (?:(\d)|(\d)-(\d)|(\*))$/.exec(cron);
  if (m === null) return cron;
  const minute = Number(m[1]);
  const hour = Number(m[2]);
  if (minute > 59 || hour > 23) return cron;
  const clock = `${pad2(hour)}:${pad2(minute)}`;
  if (m[6] !== undefined) return `每日 ${clock}`;
  if (m[3] !== undefined) {
    const day = Number(m[3]);
    return day <= 6 ? `每週${WEEKDAY[day]} ${clock}` : cron;
  }
  const from = Number(m[4]);
  const to = Number(m[5]);
  return from < to && to <= 6 ? `每週${WEEKDAY[from]}至週${WEEKDAY[to]} ${clock}` : cron;
}

/** 一條排程列的主文字：「<白話>・<工作名>」（不認得的 cron 顯示原表達式）。 */
export const scheduleRowText = (entry: { job: string; cron: string }): string => `${humanizeCron(entry.cron)}・${scheduleJobLabel(entry.job)}`;

const REPO_KEY = /^repo(\d+)$/;

/** 保留物件裡的 repo 項（鍵為 `repo<N>`，依 N 由小到大）；`logicalDays` 不是 repo 項。 */
function repoRetentions(retention: BackupRetention): Array<[key: string, limits: BackupRepoRetention]> {
  return Object.entries(retention)
    .filter(([key]) => REPO_KEY.test(key))
    .map(([key, limits]): [string, BackupRepoRetention] => [key, limits as BackupRepoRetention])
    .sort(([a], [b]) => Number(REPO_KEY.exec(a)?.[1]) - Number(REPO_KEY.exec(b)?.[1]));
}

/** repo 在保留列的稱呼：repo1 為本地、repo2 為離站。 */
const retentionRole = (repoKey: string): string => (repoKey === "repo1" ? "本地" : repoKey === "repo2" ? "離站" : repoKey);

/**
 * 保留策略一行字：「本地：全備 4、差異 7；離站：全備 4、差異隨全備到期；邏輯備份 28 天」。
 * `retention` 為 null＝量不到，回「—」（不填預設值、不出現任何數字）；欄內 null＝該設定未設：本地的差異顯示「差異 未設」、其他 repo 的差異顯示「差異隨全備到期」
 * （pgBackRest 未設差異保留時，差異備份留到其依附的全備到期）；邏輯備份天數 null 顯示「邏輯備份 —」。
 */
export function retentionText(retention: BackupRetention | null | undefined): string {
  if (retention === null || retention === undefined) return DASH;
  const segments = repoRetentions(retention).map(([key, limits]) => {
    const full = limits.full === null || limits.full === undefined ? "未設" : String(limits.full);
    const diff = limits.diff === null || limits.diff === undefined ? (key === "repo1" ? "差異 未設" : "差異隨全備到期") : `差異 ${limits.diff}`;
    return `${retentionRole(key)}：全備 ${full}、${diff}`;
  });
  const logical = retention.logicalDays === null || retention.logicalDays === undefined ? "邏輯備份 —" : `邏輯備份 ${retention.logicalDays} 天`;
  return [...segments, logical].join("；");
}

// ── 最近狀態卡、WAL 歸檔（R-BK-15～22）──────────────────────────────────────────────────────────
/**
 * WAL 歸檔單行：「WAL 歸檔：最近 <時間>・失敗 N 次」；`failedCount>0` 且最近失敗晚於最近歸檔（或從未歸檔、或失敗時間缺席）＝警示色；讀不到（null）寫「WAL 歸檔：—」，
 * 不寫「失敗 0 次」（那會把「量不到」讀成「沒有失敗」）。真實的零（全新叢集）仍是物件，照常顯示。
 */
export function walLine(wal: BackupWalArchive | null | undefined): { text: string; tone: BackupTone } {
  if (wal === null || wal === undefined) return { text: "WAL 歸檔：—", tone: "muted" };
  const failedAt = wal.failedCount > 0 && wal.lastFailedAt ? `（最近一次失敗 ${formatDateTime(wal.lastFailedAt)}）` : "";
  const text = `WAL 歸檔：最近 ${formatDateTime(wal.lastArchivedAt)}・失敗 ${wal.failedCount} 次${failedAt}`;
  return { text, tone: walNeedsAttention(wal) ? "danger" : "ok" };
}

function walNeedsAttention(wal: BackupWalArchive): boolean {
  if (wal.failedCount <= 0) return false;
  const failed = wal.lastFailedAt ? Date.parse(wal.lastFailedAt) : Number.NaN;
  if (Number.isNaN(failed)) return true; // 有失敗次數卻沒有可比的時間：不能證明已恢復，保守標警示
  const archived = wal.lastArchivedAt ? Date.parse(wal.lastArchivedAt) : Number.NaN;
  return Number.isNaN(archived) || failed > archived;
}

// ── 控制面健康與資料新鮮度（R-BK-23～28）────────────────────────────────────────────────────────
/** 控制面離線（心跳逾 30 秒或缺席）：資料照回，所以不阻擋畫面，只加紅橫幅與「可能已過期」。 */
export const RUNNER_OFFLINE = "runner_offline";

/**
 * 整區原因面板的文字（`control.reason` 為這三者之一時，所有資料區塊都是 null，畫面只顯示原因）：
 * 文字刻意不含「尚無備份」與任何數字——避免「量不到」被讀成「沒有備份」或 0 份。
 */
export const CONTROL_REASON_TEXT: Readonly<Record<string, string>> = {
  not_configured: "備份控制面未設定（不在 Docker 全棧）",
  schema_mismatch: "匯出檔格式版本不符：備份控制面匯出的檔案版本與 Console 不一致，所以不顯示任何備份資料。請把 Console 與備份控制面更新到同一版本。",
  export_unreadable: "匯出檔無法讀取：備份控制面匯出的檔案不存在、損毀或是空的，所以不顯示任何備份資料。請確認備份控制面（sidecar）是否正常運作。",
};

/** `control.reason` 是否讓所有資料區塊缺席（not_configured、schema_mismatch、export_unreadable，以及日後新增的任何不是 runner_offline 的值）。 */
export const reasonBlocksData = (reason: string | null | undefined): boolean => reason !== null && reason !== undefined && reason !== RUNNER_OFFLINE;

/** 原因面板文字；日後新增的 reason 原樣顯示（不吞掉、不當成沒事）。 */
export const controlReasonText = (reason: string): string => CONTROL_REASON_TEXT[reason] ?? `備份控制面回報了無法辨識的狀態：${reason}`;

/** 紅橫幅：「備份控制面無回應（上次心跳 N 秒前）」；心跳檔缺席（null）寫「尚未收到心跳」。 */
export function offlineBannerText(heartbeatAgeSeconds: number | null | undefined): string {
  return typeof heartbeatAgeSeconds === "number" ? `備份控制面無回應（上次心跳 ${heartbeatAgeSeconds} 秒前）` : "備份控制面無回應（尚未收到心跳）";
}

/** 匯出資料過期的門檻（秒）：`exportAgeSeconds` 嚴格大於它才加「已過期」（恰 180 整不加）。 */
export const EXPORT_STALE_SECONDS = 180;
export const isExportStale = (exportAgeSeconds: number | null | undefined): boolean =>
  typeof exportAgeSeconds === "number" && Number.isFinite(exportAgeSeconds) && exportAgeSeconds > EXPORT_STALE_SECONDS;

/** 資料標記：控制面離線＝「可能已過期」；否則匯出舊了＝「已過期」；都不是＝沒有標記（null）。 */
export function staleMarkText(reason: string | null | undefined, exportAgeSeconds: number | null | undefined): string | null {
  if (reason === RUNNER_OFFLINE) return "可能已過期";
  return isExportStale(exportAgeSeconds) ? "已過期" : null;
}

/** `control.warnings` 的中文說明（封閉詞彙；`cron_unparsable:<job>` 帶工作名）；日後新增的值原樣顯示。 */
export function warningText(code: string): string {
  switch (code) {
    case "info_unavailable":
      return "pgBackRest 備份資訊暫時讀不到：備份清單裡的 pgBackRest 備份、各 repo 狀態與保留設定因此缺少。";
    case "logical_unavailable":
      return "離站邏輯備份清單暫時讀不到：備份清單裡的邏輯備份因此缺少。";
    case "retention_unavailable":
      return "保留設定讀不到：不會用預設值代替，保留策略顯示為「—」。";
    case "db_unavailable":
      return "資料庫讀取失敗：進行中的工作與 WAL 歸檔狀態可能缺少。";
    default: {
      const job = /^cron_unparsable:(.+)$/.exec(code)?.[1];
      return job === undefined ? code : `「${scheduleJobLabel(job)}」的排程表達式無法解析：下次執行時間與逾期判斷因此缺少。`;
    }
  }
}

// ── reason 詞表（R-BK-60；與契約〈backup 類 reason 表〉三方雙向鎖）───────────────────────────────
/**
 * 十三個 reason 的中文訊息：前五個是 API 錯誤 reason（對應 backend `ErrorReasons` 的 `BACKUP_` 前綴常數），後八個是 `console.backup_jobs.reason` 的工作理由。
 * 🔴 不放進 `lib/api/reasons.ts`（它與 `API_Contract_P3-6.md` 附錄 B 雙向鎖，本案不動）；鍵集合與訊息須與契約檔 `API_Contract_SysAdminBackup.md` 的
 * 〈backup 類 reason 表〉逐字相同（`sysadminBackup.test.ts` 讀契約檔比對）。
 */
export const BACKUP_REASONS = {
  backup_control_unavailable: "備份控制面目前無法使用",
  backup_confirm_required: "請先確認後再執行",
  backup_job_in_progress: "已有進行中的備份工作",
  backup_too_frequent: "距離上一份同類備份過近，請稍後再試",
  backup_job_not_found: "查無此備份工作",
  script_failed: "備份腳本執行失敗，請看輸出尾段",
  interrupted: "容器重啟或工作被中斷",
  timeout: "工作逾時，控制面無回應",
  lock_timeout: "等待維護鎖逾時，已有其他工作在執行",
  control_write_failed: "請求無法送出（控制面寫入失敗）",
  busy: "排程工作執行中，稍後再試",
  rejected_invalid: "請求內容不合法，已被拒絕",
  expired: "請求逾時未被執行",
} as const;

/** reason → 中文；表外的值原樣顯示，null／缺席顯示「—」。 */
export function backupReasonText(reason: string | null | undefined): string {
  if (reason === null || reason === undefined || reason === "") return DASH;
  return Object.hasOwn(BACKUP_REASONS, reason) ? BACKUP_REASONS[reason as keyof typeof BACKUP_REASONS] : reason;
}

/** 工作紀錄的狀態文字（階段二用；先備齊詞表）。 */
export const JOB_STATUS_TEXT: Readonly<Record<string, string>> = {
  QUEUED: "排隊中",
  RUNNING: "進行中",
  SUCCEEDED: "成功",
  FAILED: "失敗",
  REJECTED: "被拒絕",
  EXPIRED: "逾時未執行",
};

// ── 保留名額（階段二的確認對話框用；純函式先備）──────────────────────────────────────────────────
export type QuotaType = "full" | "diff" | "verify";
export type QuotaItem = { repo: number; kind: "full" | "diff"; current: number; limit: number; willExpire: boolean; oldestLabel: string | null };

/**
 * 手動全備或增備完成後，各 repo 的保留名額：`current`＝現有份數、`limit`＝上限、`willExpire`＝`current ≥ limit`（完成當下最舊一份與依附於它的差異備份會被刪）。
 * 全備只算該 repo 的全備；**差異的份數＝差異加全備合計**（pgBackRest 的差異保留把全備計入），`oldestLabel` 取最舊的差異備份。該 repo 的上限為 null（未設）＝不輸出那一項；
 * 驗證沒有保留名額＝空陣列。「最舊」取標籤的字典序最小者（pgBackRest 標籤內嵌時間戳，字典序即時間序）。
 */
export function retentionQuota(type: QuotaType, backups: ReadonlyArray<Pick<BackupRow, "kind" | "label" | "location">>, retention: BackupRetention | null | undefined): QuotaItem[] {
  if (type === "verify" || retention === null || retention === undefined) return [];
  const items: QuotaItem[] = [];
  for (const [key, limits] of repoRetentions(retention)) {
    const limit = type === "full" ? limits.full : limits.diff;
    if (limit === null || limit === undefined) continue;
    const own = backups.filter((row) => row.location === key);
    const fulls = own.filter((row) => row.kind === "full");
    const diffs = own.filter((row) => row.kind === "diff");
    const counted = type === "full" ? fulls : [...diffs, ...fulls];
    const oldest = (type === "full" ? fulls : diffs).map((row) => row.label).sort()[0] ?? null;
    items.push({ repo: Number(REPO_KEY.exec(key)?.[1]), kind: type, current: counted.length, limit, willExpire: counted.length >= limit, oldestLabel: oldest });
  }
  return items;
}

// ── 說明區：涵蓋範圍與還原指令（R-BK-43～45）────────────────────────────────────────────────────
export type CoverageCategory = "backed_up" | "backup_mechanism" | "rebuildable" | "not_covered";
export type VolumeCoverage = { category: CoverageCategory; note: string };

/** 類別的中文標籤（值域封閉）。 */
export const COVERAGE_CATEGORY_LABEL: Readonly<Record<CoverageCategory, string>> = {
  backed_up: "已備份",
  backup_mechanism: "備份機制本身",
  rebuildable: "可由 primary 重建",
  not_covered: "未涵蓋",
};

/**
 * 涵蓋範圍表：逐卷分類。鍵集合必須與 `docker-compose.yml` 頂層 `volumes:` 的卷集合**雙向相等**（新增卷沒歸類、或表內有不存在的卷都會使 `backup-docs.test.ts` 轉紅）；
 * 現有 14 卷（含備份控制面的 `backup_out`、`backup_req`）。
 */
export const VOLUME_COVERAGE: Readonly<Record<string, VolumeCoverage>> = {
  pg_data: { category: "backed_up", note: "PostgreSQL 整個叢集，含 console schema（Console 的專案、目標、任務等業務資料）" },
  pg_backup: { category: "backup_mechanism", note: "pgBackRest 的本地備份庫（repo1）" },
  minio_data: { category: "backup_mechanism", note: "離站備份物件（本機 MinIO 的資料）" },
  pg_wal_archive: { category: "backup_mechanism", note: "WAL 的本地複本" },
  pg_socket: { category: "backup_mechanism", note: "primary 的 unix socket，供備份控制面以本機模式連線" },
  backup_out: { category: "backup_mechanism", note: "備份控制面的輸出（狀態與匯出檔）" },
  backup_req: { category: "backup_mechanism", note: "備份控制面的請求（手動觸發的請求檔）" },
  pg_replica_data: { category: "rebuildable", note: "replica 的資料，可由 primary 重建（見 docker/README.md 第 5 節）" },
  engine_workspace: { category: "not_covered", note: "Engine Bridge 的執行工作目錄；不在資料庫、也不在備份內，遺失就沒有了" },
  app_logs: { category: "not_covered", note: "後端與 Bridge 的日誌檔" },
  redis_data: { category: "not_covered", note: "Redis 的資料（例如登出名單）" },
  prometheus_data: { category: "not_covered", note: "Prometheus 時序資料" },
  nginx_certs: { category: "not_covered", note: "nginx 的 TLS 憑證" },
  minio_certs: { category: "not_covered", note: "MinIO 的自簽憑證；缺時由 minio-certs job 重產" },
};

/** 涵蓋表下方的提醒：金鑰遺失＝資料救不回來，須另行保管。 */
export const KEY_LOSS_NOTE = "PGBACKREST_CIPHER_PASS 遺失＝備份無法還原、CONSOLE_ENCRYPTION_KEY 遺失＝敏感參數無法解密，請另行保管";

/** 明寫「本頁不提供還原按鈕」與原因（還原要先停 primary、`restore.sh` 在 primary 運作時拒絕、replica 的時間軸會分岔須重建）。 */
export const NO_RESTORE_BUTTON_NOTE = "本頁不提供還原按鈕：還原要先停止 primary，restore.sh 在 primary 仍運作時會拒絕執行，還原後 replica 的時間軸也會分岔、必須重建，這些步驟不適合由網頁一鍵完成。";

export type RestoreStep = { title: string; description: string; bash: readonly string[]; powershell: readonly string[] };

/**
 * 還原三步（停 primary → 容器內 `restore.sh` → 啟動並核對）。🔴 每條指令都必須整行等於 `docker/README.md` 〈4.3〉節 code block 的某一行（去前後空白後比）；
 * `backup-docs.test.ts` 讀真 README 單向比對（README 刪改任一行＝紅，README 另增指令不紅）。改這裡的字串前先改 README，兩邊同 commit。
 */
export const RESTORE_STEPS: readonly RestoreStep[] = [
  {
    title: "第一步：停止 primary",
    description: "還原前一定要先停掉 primary；restore.sh 在 primary 仍接受連線時會拒絕執行。",
    bash: ["(cd AgentConsole && docker compose stop postgres-primary)"],
    powershell: ["Push-Location AgentConsole; docker compose stop postgres-primary; Pop-Location"],
  },
  {
    title: "第二步：在容器內執行 restore.sh",
    description: "還原到最新就拿掉 --target-time；只想還原離站那份就加 --repo 2。目標時間要帶時區。",
    bash: ['(cd AgentConsole && docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes --target-time "2026-10-14 16:39:17+00")'],
    powershell: ['Push-Location AgentConsole; docker compose run --rm --no-deps pgbackrest bash /usr/local/bin/restore.sh --yes --target-time "2026-10-14 16:39:17+00"; Pop-Location'],
  },
  {
    title: "第三步：啟動 primary 並核對",
    description: "啟動後立刻核對資料；只看容器 healthy 不算數，空的資料目錄也會是 healthy。",
    bash: ["(cd AgentConsole && docker compose start postgres-primary)", '(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT NOW(), version();")'],
    powershell: [
      "Push-Location AgentConsole; docker compose start postgres-primary; Pop-Location",
      'Push-Location AgentConsole; docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT NOW(), version();"; Pop-Location',
    ],
  },
];

export type RestoreCheck = { title: string; hint: string; command: string };

/**
 * 還原後的核對三項（只有 bash 形態；README 的 PowerShell 形態只是一句前後綴說明、沒有指令行，所以畫面也只列 bash 並以一句話說明前後綴，不另造 README 沒有的指令行）。
 * 每條 `command` 同樣必須整行等於 README 〈4.3〉的某一行。
 */
export const RESTORE_CHECKS: readonly RestoreCheck[] = [
  {
    title: "各表的精確列數",
    hint: "與災難前記下的數字比對；不要用估計值，還原後的統計是空的。",
    command:
      "(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c \"SELECT table_name, (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text::int AS row_count FROM information_schema.tables WHERE table_schema = 'console' AND table_type = 'BASE TABLE' ORDER BY 1;\")",
  },
  {
    title: "時間軸",
    hint: "成功還原會升格出新的時間軸，編號會是 2 以上；全新的空叢集恆為 1。",
    command: '(cd AgentConsole && docker compose exec postgres-primary psql -U aisdlc -d aisdlc -c "SELECT timeline_id FROM pg_control_checkpoint();")',
  },
  {
    title: "pgbackrest check",
    hint: "確認備份鏈健康。",
    command: "(cd AgentConsole && docker compose exec pgbackrest pgbackrest --stanza=aisdlc check)",
  },
];

/** PowerShell 形態的核對指令：README 沒有指令行，畫面只用一句話說明前後綴。 */
export const CHECKS_POWERSHELL_NOTE = "在 PowerShell 執行時，每一條前面加「Push-Location AgentConsole;」、後面加「; Pop-Location」，並把最外層的括號與「cd AgentConsole &&」拿掉，其餘相同。";
