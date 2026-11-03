/**
 * rehype 外掛：預覽端把「內容整個符合指定樣式」的原始 HTML 節點拿掉（例：PRD 的來源節錨點 `<!-- r2p:section=N -->`——那是目錄用的記號，預覽不該把它當文字印出來）。
 *
 * 為什麼要有這支：編輯器預覽不渲染內嵌 HTML（`omitRawHtml` 拿掉 rehype-raw，DEF-AC-013），react-markdown 於是把 HTML 節點（hast 的 `raw`）原文當成文字顯示，
 * 一行獨立的 HTML 註解就變成預覽裡一行看得見的字（INT-14⑤）。這支外掛排在 react-markdown 把 `raw` 轉成文字之前，把符合的 `raw` 節點刪掉。
 *
 * 邊界（刻意很窄）：
 *  - 只刪 `raw` 節點，而且節點的整段內容（含前後空白）要完整符合 `pattern`——其他 HTML 與註解仍照字面以文字顯示（安全立場不變：預覽端沒有任何 HTML 被當成真元素）；
 *  - 程式碼圍欄與行內程式碼的內容不是 `raw` 節點，不受影響（圍欄裡的錨點照原樣顯示）；
 *  - 不改任何元素、不新增節點、不碰 URL 與屬性。
 * 與工作室的「預覽」模式是同一條規則（`StudioPanel` 的 `splitPrdBlocks` 用同一個 `SECTION_ANCHOR` 整行拿掉）；呼叫端把樣式傳進來，本檔不認得任何特定格式。
 */
type HastNode = {
  type: string;
  value?: string;
  children?: HastNode[];
};

/** 刪掉整棵樹裡內容符合 `pattern` 的 `raw` 節點（就地修改）。 */
function prune(node: HastNode, pattern: RegExp): void {
  if (node.children === undefined) return;
  node.children = node.children.filter((child) => !(child.type === "raw" && typeof child.value === "string" && pattern.test(child.value)));
  for (const child of node.children) prune(child, pattern);
}

export function rehypeHideRawLines(options: { pattern: RegExp }) {
  // g／y 旗標的正規式 `test` 會帶狀態（lastIndex）：同一個樣式連續判多個節點會漏判，所以先換成無狀態的副本
  const stateless = new RegExp(options.pattern.source, options.pattern.flags.replace(/[gy]/g, ""));
  return (tree: HastNode) => prune(tree, stateless);
}
