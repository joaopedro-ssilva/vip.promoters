import type { Metadata } from "next";
import { ManagerRanking } from "@/components/manager/ranking";

export const metadata: Metadata = { title: "Ranking" };

export default function Page() {
  return <ManagerRanking />;
}
