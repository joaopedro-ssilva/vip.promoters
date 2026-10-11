import type { Metadata } from "next";
import { PromoterStatement } from "@/components/promoter/statement";

export const metadata: Metadata = { title: "Extrato" };

export default function Page() {
  return <PromoterStatement />;
}
