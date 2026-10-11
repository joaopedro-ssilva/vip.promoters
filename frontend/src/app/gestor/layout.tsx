import type { Metadata } from "next";
import { RoleGuard } from "@/components/auth/role-guard";
import { ManagerShell } from "@/components/layout/manager-shell";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function GestorLayout({ children }: { children: React.ReactNode }) {
  return (
    <RoleGuard role="manager">
      <ManagerShell>{children}</ManagerShell>
    </RoleGuard>
  );
}
