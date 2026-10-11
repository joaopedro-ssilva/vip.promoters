import type { Metadata } from "next";
import { InviteView } from "@/components/auth/invite-view";

export const metadata: Metadata = { title: "Convite", robots: { index: false, follow: false } };

export default async function InvitePage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = await params;
  return <InviteView code={code.slice(0, 32)} />;
}
