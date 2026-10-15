"use client";

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { EntityEditor, entityTitle, type EntityDone, type EntityTarget } from "./EntityEditor";

/**
 * 建立／編輯 Dialog（設計稿〈全域覆蓋層〉）：560px 白卡；頁面持有 target 狀態（null＝關閉）。
 * 範例：const [target, setTarget] = useState<EntityTarget | null>(null)
 *       <EntityDialog target={target} onClose={() => setTarget(null)} onDone={...} />
 */
export function EntityDialog({ target, onClose, onDone }: { target: EntityTarget | null; onClose: () => void; onDone?: (done: EntityDone) => void }) {
  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      {target ? (
        <DialogContent title={entityTitle(target)} description={`${entityTitle(target)}：填寫名稱、說明與通過標準後儲存`}>
          <EntityEditor
            key={JSON.stringify(target)}
            target={target}
            variant="dialog"
            onCancel={onClose}
            onDone={(done) => {
              onDone?.(done);
              onClose();
            }}
          />
        </DialogContent>
      ) : null}
    </Dialog>
  );
}
