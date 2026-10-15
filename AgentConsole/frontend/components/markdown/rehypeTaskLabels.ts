/**
 * rehype 外掛：給 GFM task list（- [ ] / - [x]）的核取方塊補上無障礙名稱。
 * remark-gfm 產生的 <input type="checkbox"> 旁邊的文字只是兄弟節點、沒有 <label>，螢幕閱讀器只會聽到一個沒有名字的核取方塊
 * （axe：aria-toggle-field-name／label；DEF-AC-005 同類）。名稱＝該項目自己的文字，不含巢狀子清單的文字。
 * MarkdownView（唯讀渲染）與 MarkdownEditorImpl（編輯器預覽）共用。
 */
type HastNode = {
  type: string;
  tagName?: string;
  value?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
};

const NESTED_LIST = new Set(["ul", "ol"]);

/** 項目自己的文字：略過核取方塊本身與巢狀子清單。 */
function ownText(node: HastNode): string {
  if (node.type === "text") return node.value ?? "";
  if (node.type !== "element" && node.type !== "root") return "";
  if (node.tagName && (NESTED_LIST.has(node.tagName) || node.tagName === "input")) return "";
  return (node.children ?? []).map(ownText).join("");
}

/** 項目自己的核取方塊（可能在鬆散清單的 <p> 裡）；不往巢狀子清單裡找。 */
function ownCheckbox(node: HastNode): HastNode | undefined {
  for (const child of node.children ?? []) {
    if (child.type !== "element") continue;
    if (child.tagName === "input" && child.properties?.type === "checkbox") return child;
    if (child.tagName && NESTED_LIST.has(child.tagName)) continue;
    const found = ownCheckbox(child);
    if (found) return found;
  }
  return undefined;
}

function isTaskItem(node: HastNode): boolean {
  if (node.type !== "element" || node.tagName !== "li") return false;
  const cls = node.properties?.className;
  return Array.isArray(cls) && cls.includes("task-list-item");
}

function visit(node: HastNode): void {
  if (isTaskItem(node)) {
    const box = ownCheckbox(node);
    const label = ownText(node).replace(/\s+/g, " ").trim();
    if (box && label) box.properties = { ...box.properties, ariaLabel: label };
  }
  for (const child of node.children ?? []) visit(child);
}

export function rehypeTaskLabels() {
  return (tree: HastNode) => visit(tree);
}
