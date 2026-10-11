import type { Metadata } from "next";
import { CampaignsList } from "@/components/manager/campaigns-list";

export const metadata: Metadata = { title: "Campanhas" };

export default function Page() {
  return <CampaignsList />;
}
