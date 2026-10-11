import type { Metadata } from "next";
import { RoleGuard } from "@/components/auth/role-guard";
import { PromoterShell } from "@/components/layout/promoter-shell";
import { TeamProvider } from "@/components/promoter/team-provider";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function PromoterLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="promoter">
      <TeamProvider>
        <PromoterShell>{children}</PromoterShell>
      </TeamProvider>
    </RoleGuard>
  );
}
