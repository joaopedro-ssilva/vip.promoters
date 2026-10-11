import type { Metadata } from "next";
import { NewCampaign } from "@/components/manager/campaign-form";

export const metadata: Metadata = { title: "Nova campanha" };

export default function Page() {
  return <NewCampaign />;
}
