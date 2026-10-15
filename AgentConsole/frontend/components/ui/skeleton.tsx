import { cn } from "@/lib/utils";

/** 扁平灰佔位（設計系統：僅 opacity 脈動，無 shimmer、無位移）。 */
export function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return <div data-slot="skeleton" aria-hidden className={cn("animate-wg-pulse rounded-md bg-wg-skeleton", className)} {...props} />;
}
