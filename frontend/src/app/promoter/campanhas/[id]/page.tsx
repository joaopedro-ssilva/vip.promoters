import type { Metadata } from "next";
import { PromoterCampaignDetailView } from "@/components/promoter/campaign-detail";

export const metadata: Metadata = { title: "Campanha" };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <PromoterCampaignDetailView id={id} />;
}
