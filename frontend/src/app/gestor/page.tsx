import type { Metadata } from "next";
import { ManagerDashboard } from "@/components/manager/dashboard";

export const metadata: Metadata = { title: "Visão geral" };

export default function Page() {
  return <ManagerDashboard />;
}
