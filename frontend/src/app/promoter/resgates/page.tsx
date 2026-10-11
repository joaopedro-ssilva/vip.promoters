import type { Metadata } from "next";
import { PromoterRedemptions } from "@/components/promoter/redemptions";

export const metadata: Metadata = { title: "Meus resgates" };

export default function Page() {
  return <PromoterRedemptions />;
}
