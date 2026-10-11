import type { Metadata } from "next";
import { PromoterShop } from "@/components/promoter/shop";

export const metadata: Metadata = { title: "Lojinha" };

export default function Page() {
  return <PromoterShop />;
}
