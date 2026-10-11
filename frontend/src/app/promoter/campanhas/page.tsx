import type { Metadata } from "next";
import { PromoterCampaigns } from "@/components/promoter/campaigns";

export const metadata: Metadata = { title: "Campanhas" };

export default function Page() {
  return <PromoterCampaigns />;
}
