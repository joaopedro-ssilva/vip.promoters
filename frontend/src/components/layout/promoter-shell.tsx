"use client";

import { Gift, House, Megaphone, Ticket, UserRound, type LucideIcon } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { useTeam } from "@/components/promoter/team-provider";
import { Skeleton } from "@/components/ui/feedback";
import { SelectField } from "@/components/ui/fields";
import { cn } from "@/lib/cn";
import { AccountMenu } from "./account-menu";
import { NotificationBell } from "./notification-bell";
import { Brand, ThemeToggle, useBarHeight, useRouteFocus } from "./parts";

interface Item {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  /** extra path prefixes that keep this item active (e.g. /extrato under Início) */
  alsoActive?: string[];
}

const NAV: Item[] = [
  { href: "/promoter", label: "Início", icon: House, exact: true, alsoActive: ["/promoter/extrato", "/promoter/ranking"] },
  { href: "/promoter/campanhas", label: "Campanhas", icon: Megaphone },
  { href: "/promoter/lojinha", label: "Lojinha", icon: Gift },
  { href: "/promoter/resgates", label: "Resgates", icon: Ticket },
  { href: "/promoter/perfil", label: "Perfil", icon: UserRound },
];

function isActive(item: Item, pathname: string) {
  if (item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`)) return true;
  return (item.alsoActive ?? []).some((p) => pathname === p || pathname.startsWith(`${p}/`));
}

function TeamSwitcher() {
  const team = useTeam();
  if (team.status === "loading") return <Skeleton className="h-4 w-30" />;
  if (team.approved.length === 0) return null;
  if (team.approved.length === 1) {
    return (
      <p className="min-w-0 truncate text-label text-ink">
        <span className="hidden text-ink-muted md:inline">Equipe: </span>
        {team.approved[0].organization.name}
      </p>
    );
  }
  return (
    <SelectField
      label="Equipe ativa"
      hideLabel
      value={team.activeOrgId ?? ""}
      onChange={(e) => team.setActiveOrg(e.target.value)}
      className="w-full md:w-48"
    >
      {team.approved.map((m) => (
        <option key={m.organization.id} value={m.organization.id}>
          {m.organization.name}
        </option>
      ))}
    </SelectField>
  );
}

export function PromoterShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const topRef = useRef<HTMLElement>(null);
  const tabRef = useRef<HTMLDivElement>(null);
  useBarHeight(topRef, "--topbar-height");
  useBarHeight(tabRef, "--tabbar-height");
  useRouteFocus();

  // toasts sit above the tab bar only while it is mounted
  useEffect(() => {
    document.documentElement.setAttribute("data-tabbar", "");
    return () => document.documentElement.removeAttribute("data-tabbar");
  }, []);

  return (
    <div className="palco flex min-h-dvh flex-col">
      <header ref={topRef} className="sticky top-0 z-20 border-b border-line-subtle bg-canvas/80 backdrop-blur-lg">
        <div className="mx-auto flex w-full max-w-promoter flex-wrap items-center gap-x-2 gap-y-1 px-4 py-2 md:gap-x-4 md:px-6 lg:px-8">
          <Brand href="/promoter" compact />
          <div className="order-last min-w-0 basis-full min-[380px]:order-none min-[380px]:flex-1 min-[380px]:basis-0">
            <TeamSwitcher />
          </div>
          <NotificationBell />
          <ThemeToggle />
          <AccountMenu />
          <nav aria-label="Principal" className="hidden w-full md:block">
            <ul className="flex flex-wrap gap-1">
              {NAV.map((item) => {
                const active = isActive(item, pathname);
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "group inline-flex min-h-10 items-center gap-2 rounded-control px-3.5 text-label transition-colors duration-[var(--duration-fast)]",
                        active
                          ? "bg-surface-raised font-semibold text-ink-strong"
                          : "font-medium text-ink-muted hover:bg-surface-raised/60 hover:text-ink",
                      )}
                    >
                      <item.icon aria-hidden="true" strokeWidth={1.75} className={cn("size-5", active ? "text-success" : "text-ink-muted")} />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </div>
      </header>

      <main
        id="conteudo"
        tabIndex={-1}
        className="mx-auto w-full max-w-promoter flex-1 px-4 pt-6 pb-[calc(var(--tabbar-height)+env(safe-area-inset-bottom)+1rem)] outline-none sm:pt-8 md:px-6 md:pb-12 lg:px-8"
      >
        {children}
      </main>

      <nav
        aria-label="Navegação principal"
        className="fixed inset-x-0 bottom-0 z-30 border-t border-line-subtle bg-surface-sunken/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg md:hidden"
      >
        <div ref={tabRef} className="grid grid-cols-5">
          {NAV.map((item) => {
            const active = isActive(item, pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex min-h-[4.5rem] min-w-0 flex-col items-center justify-center gap-1 px-0.5 py-2 text-center text-2xs font-medium -outline-offset-[3px]",
                  active ? "text-ink-strong" : "text-ink-muted hover:text-ink",
                )}
              >
                <item.icon aria-hidden="true" strokeWidth={1.75} className={cn("size-5.5", active ? "text-success" : "text-ink-muted")} />
                <span className="min-w-0 max-w-full">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}
