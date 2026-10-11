"use client";

import { LogOut, Settings, UserRound } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Avatar } from "@/components/ui/misc";
import { Popover, usePopoverClose } from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

export function AccountMenu() {
  const { user } = useAuth();
  if (!user) return null;
  const profileHref = user.role === "manager" ? "/gestor/configuracoes" : "/promoter/perfil";
  const ProfileIcon = user.role === "manager" ? Settings : UserRound;

  return (
    <Popover label={`Menu da conta de ${user.name}`} trigger={<Avatar name={user.name} size="sm" />}>
      <AccountPanel profileHref={profileHref} Icon={ProfileIcon} />
    </Popover>
  );
}

function AccountPanel({ profileHref, Icon: ProfileIcon }: { profileHref: string; Icon: typeof Settings }) {
  const { user, logout } = useAuth();
  const close = usePopoverClose();
  const [busy, setBusy] = useState(false);
  if (!user) return null;
  return (
        <div className="flex flex-col gap-1">
          <div className="min-w-0 px-3 py-2">
            <p className="truncate text-label text-ink">{user.name}</p>
            <p className="truncate text-caption text-ink-muted">{user.email}</p>
          </div>
          <Link
            href={profileHref}
            onClick={close}
            className="flex min-h-11 items-center gap-2 rounded-control px-3 text-label text-ink-secondary hover:bg-surface-hover hover:text-ink"
          >
            <ProfileIcon aria-hidden="true" strokeWidth={1.75} className="size-5" />
            {user.role === "manager" ? "Configurações" : "Perfil"}
          </Link>
          <Button
            variant="ghost"
            icon={LogOut}
            loading={busy}
            className="justify-start"
            onClick={async () => {
              setBusy(true);
              await logout();
            }}
          >
            {busy ? "Saindo…" : "Sair da conta"}
          </Button>
        </div>
  );
}
