import type { Metadata } from "next";
import { PromoterRanking } from "@/components/promoter/ranking";

export const metadata: Metadata = { title: "Ranking" };

export default function Page() {
  return <PromoterRanking />;
}
