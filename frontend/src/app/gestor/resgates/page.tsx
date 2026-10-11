import type { Metadata } from "next";
import { RedemptionsPage } from "@/components/manager/redemptions";

export const metadata: Metadata = { title: "Resgates" };

export default function Page() {
  return <RedemptionsPage />;
}
