import type { Metadata } from "next";

import { SiView } from "@/components/domain/si/SiView";

export const metadata: Metadata = { title: "自我進化" };

export default function SelfImprovingPage() {
  return <SiView />;
}
