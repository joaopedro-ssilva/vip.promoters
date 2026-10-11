import type { Metadata } from "next";
import { PromoterHomePage } from "@/components/promoter/home";

export const metadata: Metadata = { title: "Início" };

export default function Page() {
  return <PromoterHomePage />;
}
