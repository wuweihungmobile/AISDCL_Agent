import { defaultUrlTransform } from "react-markdown";

/**
 * Markdown 連結與圖片網址的白名單：react-markdown 的預設（http、https、irc、ircs、mailto、xmpp 與相對網址、`#錨點`、`?查詢`），
 * 編輯器預覽（MarkdownEditorImpl）與唯讀的 MarkdownView 共用，所以同一份內容的連結在兩處一模一樣（DEF-AC-013：兩處對同一份內容的呈現必須相同）。
 *
 * 與 react-markdown 預設不同的只有一點：不合格的網址（javascript:、vbscript:、data:、tel:、file:、任何自訂協定與用空白或控制字元混淆的 `java\tscript:`——
 * 判準是白名單，不是黑名單）回傳 `undefined`，不是空字串。`<a href="">` 點下去會「重新載入本頁」，編輯器裡還沒存的內容就丟了；
 * 沒有 href 的 `<a>` 是沒有行為的文字（不可聚焦、點了不導頁）。
 * 套件（@uiw/react-markdown-preview）的預設是「原樣放行」，所以預覽端必須自己帶這一支。
 */
export function safeUrlTransform(url: string): string | undefined {
  const safe = defaultUrlTransform(url);
  return safe === "" && url !== "" ? undefined : safe;
}
