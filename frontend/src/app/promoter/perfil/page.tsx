import type { Metadata } from "next";
import { PromoterProfile } from "@/components/promoter/profile";

export const metadata: Metadata = { title: "Perfil" };

export default function Page() {
  return <PromoterProfile />;
}
