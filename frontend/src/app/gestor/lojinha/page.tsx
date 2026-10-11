import type { Metadata } from "next";
import { RewardsPage } from "@/components/manager/rewards";

export const metadata: Metadata = { title: "Lojinha" };

export default function Page() {
  return <RewardsPage />;
}
