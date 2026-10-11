"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Gift,
  Camera,
  LayoutDashboard,
  Megaphone,
  Menu,
  Settings,
  Ticket,
  Trophy,
  Users,
  FlaskConical,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/feedback";
import { cn } from "@/lib/cn";
import { managerDashboardQuery } from "@/lib/queries";
import { AccountMenu } from "./account-menu";
import { NotificationBell } from "./notification-bell";
import { Brand, ThemeToggle, useBarHeight, useMockMode, useRouteFocus } from "./parts";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
  counter?: "pending_members" | "pending_redemptions";
}

const NAV: NavItem[] = [
  { href: "/gestor", label: "Visão geral", icon: LayoutDashboard, exact: true },
  { href: "/gestor/campanhas", label: "Campanhas", icon: Megaphone },
  { href: "/gestor/equipe", label: "Equipe", icon: Users, counter: "pending_members" },
  { href: "/gestor/ranking", label: "Ranking", icon: Trophy },
  { href: "/gestor/lojinha", label: "Lojinha", icon: Gift },
  { href: "/gestor/resgates", label: "Resgates", icon: Ticket, counter: "pending_redemptions" },
  { href: "/gestor/instagram", label: "Instagram", icon: Camera },
  { href: "/gestor/configuracoes", label: "Configurações", icon: Settings },
];

function useCounters() {
  const q = useQuery(managerDashboardQuery());
  return {
    pending_members: q.data?.kpis.promoters_pending ?? 0,
    pending_redemptions: q.data?.kpis.redemptions_pending ?? 0,
  };
}

function SideNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const counters = useCounters();
  return (
    <nav aria-label="Principal" className="flex flex-col gap-1">
      {NAV.map((item) => {
        const active = item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const count = item.counter ? counters[item.counter] : 0;
        const Icon = item.icon;
        const countLabel =
          item.counter === "pending_members"
            ? `${count} ${count === 1 ? "pendente" : "pendentes"}`
            : `${count} ${count === 1 ? "pendente" : "pendentes"}`;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "relative flex min-h-11 items-center gap-3 rounded-control px-3 py-2 text-label",
              active
                ? "bg-surface-raised text-ink before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:bg-accent"
                : "text-ink-secondary hover:bg-surface-hover hover:text-ink active:bg-surface-raised",
            )}
          >
            <Icon aria-hidden="true" strokeWidth={1.75} className="size-6 shrink-0" />
            <span className="min-w-0 flex-1">
              {item.label}
              {count > 0 && <span className="sr-only">, {countLabel}</span>}
            </span>
            {count > 0 && (
              <span aria-hidden="true" className="rounded-pill bg-surface-hover px-2 py-0.5 text-caption tabular-nums text-ink">
                {count}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <Brand href="/gestor" />
      <div className="min-w-0 rounded-control border border-line-subtle bg-surface-raised px-3 py-2">
        <p className="text-caption text-ink-muted">Organização</p>
        {user?.organization ? (
          <p className="truncate text-label text-ink">{user.organization.name}</p>
        ) : (
          <Skeleton className="mt-1 h-4 w-28" />
        )}
      </div>
      <SideNav onNavigate={onNavigate} />
    </div>
  );
}

const CRUMBS: Record<string, string> = {
  campanhas: "Campanhas",
  equipe: "Equipe",
  ranking: "Ranking",
  lojinha: "Lojinha",
  resgates: "Resgates",
  instagram: "Instagram",
  configuracoes: "Configurações",
  nova: "Nova campanha",
};

function Breadcrumb() {
  const pathname = usePathname();
  const segs = pathname.split("/").filter(Boolean).slice(1);
  const crumbs: { href: string; label: string }[] = [{ href: "/gestor", label: "Visão geral" }];
  let acc = "/gestor";
  segs.forEach((s, i) => {
    acc += `/${s}`;
    crumbs.push({ href: acc, label: CRUMBS[s] ?? (i > 0 ? "Detalhe" : s) });
  });
  if (crumbs.length === 1) return <p className="hidden text-label text-ink-secondary md:block">Visão geral</p>;
  return (
    <nav aria-label="Você está em" className="hidden md:block">
      <ol className="flex flex-wrap items-center gap-2 text-label text-ink-secondary">
        {crumbs.map((c, i) => (
          <li key={c.href} className="flex items-center gap-2">
            {i > 0 && <span aria-hidden="true">/</span>}
            {i === crumbs.length - 1 ? (
              <span aria-current="page" className="text-ink">
                {c.label}
              </span>
            ) : (
              <Link href={c.href} className="underline-offset-4 hover:text-ink hover:underline">
                {c.label}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

export function ManagerShell({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const mock = useMockMode();
  const [drawer, setDrawer] = useState(false);
  const drawerRef = useRef<HTMLDialogElement>(null);
  const topRef = useRef<HTMLElement>(null);
  useBarHeight(topRef, "--topbar-height");
  useRouteFocus();

  useEffect(() => {
    const d = drawerRef.current;
    if (!d) return;
    if (drawer && !d.open) d.showModal();
    else if (!drawer && d.open) d.close();
  }, [drawer]);

  return (
    <div className="lg:grid lg:grid-cols-[var(--sidebar-width)_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-dvh overflow-y-auto border-r border-line-subtle bg-surface lg:block">
        <SidebarContent />
      </aside>

      <dialog
        ref={drawerRef}
        aria-label="Menu de navegação"
        onClose={() => setDrawer(false)}
        onClick={(e) => {
          if (e.target === e.currentTarget) setDrawer(false);
        }}
        className="m-0 h-dvh max-h-none w-[min(20rem,calc(100%-2rem))] overflow-y-auto border-r border-line bg-surface p-0 text-ink shadow-dialog backdrop:bg-[var(--scrim)]"
      >
        {drawer && (
          <div className="flex h-full flex-col">
            <div className="flex justify-end px-2 pt-2">
              <Button variant="ghost" onClick={() => setDrawer(false)}>
                Fechar menu
              </Button>
            </div>
            <SidebarContent onNavigate={() => setDrawer(false)} />
          </div>
        )}
      </dialog>

      <div className="min-w-0">
        <header
          ref={topRef}
          className="sticky top-0 z-20 flex min-h-16 items-center gap-3 border-b border-line-subtle bg-surface px-4 md:px-6 lg:px-8"
        >
          <Button variant="ghost" iconOnly aria-label="Abrir menu" className="lg:hidden" onClick={() => setDrawer(true)}>
            <Menu aria-hidden="true" strokeWidth={1.75} className="size-6" />
          </Button>
          <div className="min-w-0 flex-1">
            <div className="md:hidden">
              <p className="truncate text-label text-ink">{user?.organization?.name ?? " "}</p>
            </div>
            <div className="hidden md:block">
              <Breadcrumb />
            </div>
          </div>
          {mock && (
            <span className="hidden items-center gap-1 rounded-pill border border-line bg-surface-raised px-2 py-1 text-caption text-accent-secondary sm:inline-flex">
              <FlaskConical aria-hidden="true" strokeWidth={1.75} className="size-4" />
              Modo demonstração
            </span>
          )}
          <NotificationBell />
          <ThemeToggle />
          <AccountMenu />
        </header>
        {mock && (
          <p className="flex items-center justify-center gap-1 border-b border-line-subtle bg-surface-raised px-4 py-1 text-caption text-accent-secondary sm:hidden">
            <FlaskConical aria-hidden="true" strokeWidth={1.75} className="size-4" />
            Modo demonstração
          </p>
        )}
        <main id="conteudo" tabIndex={-1} className="mx-auto w-full max-w-workspace px-4 py-8 outline-none md:px-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
