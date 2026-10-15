import * as React from "react";

import { fieldClass } from "@/components/ui/input";
import { cn } from "@/lib/utils";

/** 多行輸入（設計稿：最小高 80px、垂直可拉伸）。 */
export function Textarea({ className, ...props }: React.ComponentProps<"textarea">) {
  return <textarea data-slot="textarea" className={cn(fieldClass, "min-h-20 resize-y", className)} {...props} />;
}
