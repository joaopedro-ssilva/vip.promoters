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
import { initials } from "@/lib/format";
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
  /** Grupo da barra lateral (rótulo estrutural acima do primeiro item). */
  group: string;
}

const NAV: NavItem[] = [
  { href: "/gestor", label: "Visão geral", icon: LayoutDashboard, exact: true, group: "Operação" },
  { href: "/gestor/campanhas", label: "Campanhas", icon: Megaphone, group: "Operação" },
  { href: "/gestor/equipe", label: "Equipe", icon: Users, counter: "pending_members", group: "Operação" },
  { href: "/gestor/ranking", label: "Ranking", icon: Trophy, group: "Operação" },
  { href: "/gestor/lojinha", label: "Lojinha", icon: Gift, group: "Recompensas" },
  { href: "/gestor/resgates", label: "Resgates", icon: Ticket, counter: "pending_redemptions", group: "Recompensas" },
  { href: "/gestor/instagram", label: "Instagram", icon: Camera, group: "Conta" },
  { href: "/gestor/configuracoes", label: "Configurações", icon: Settings, group: "Conta" },
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
    <nav aria-label="Principal" className="flex flex-col gap-0.5">
      {NAV.map((item, index) => {
        const active = item.exact ? pathname === item.href : pathname === item.href || pathname.startsWith(`${item.href}/`);
        const count = item.counter ? counters[item.counter] : 0;
        const Icon = item.icon;
        const countLabel =
          item.counter === "pending_members"
            ? `${count} ${count === 1 ? "pendente" : "pendentes"}`
            : `${count} ${count === 1 ? "pendente" : "pendentes"}`;
        const firstOfGroup = index === 0 || NAV[index - 1].group !== item.group;
        return (
          <div key={item.href}>
          {firstOfGroup && <p className={cn("rotulo px-3 pb-2", index === 0 ? "pt-2" : "pt-5")}>{item.group}</p>}
          <Link
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group relative flex min-h-11 items-center gap-3 rounded-control pl-6 pr-3 py-2 text-label transition-colors duration-[var(--duration-fast)]",
              active
                ? "bg-surface-raised font-semibold text-ink-strong before:absolute before:left-2.5 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-[2px] before:bg-accent"
                : "font-medium text-ink-muted hover:bg-surface-raised/60 hover:text-ink",
            )}
          >
            <Icon
              aria-hidden="true"
              strokeWidth={1.75}
              className={cn("size-5 shrink-0", active ? "text-success" : "text-ink-muted group-hover:text-ink-secondary")}
            />
            <span className="min-w-0 flex-1">
              {item.label}
              {count > 0 && <span className="sr-only">, {countLabel}</span>}
            </span>
            {count > 0 && (
              <span aria-hidden="true" className="num inline-flex h-5 min-w-5 items-center justify-center rounded-pill border border-warning-border bg-warning-soft px-1.5 text-2xs font-semibold text-warning">
                {count}
              </span>
            )}
          </Link>
          </div>
        );
      })}
    </nav>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { user } = useAuth();
  return (
    <div className="flex h-full flex-col gap-4 px-3.5 pb-4 pt-5">
      <Brand href="/gestor" className="px-1.5" />
      {/* A marca do produto não compete com a da conta: logo abaixo, o emblema
          com as iniciais da organização — "que sistema é este" contra "em que
          conta eu estou". */}
      <div className="flex min-w-0 items-center gap-2.5 rounded-control border border-line-subtle bg-surface px-2.5 py-2">
        <span
          aria-hidden="true"
          className="grid size-8 shrink-0 place-items-center rounded-[0.5625rem] border border-accent-border bg-accent-soft text-2xs font-bold tracking-[0.02em] text-success"
        >
          {initials(user?.organization?.name)}
        </span>
        <div className="min-w-0">
          <p className="rotulo">Organização</p>
          {user?.organization ? (
            <p className="truncate text-label text-ink-strong">{user.organization.name}</p>
          ) : (
            <Skeleton className="mt-1 h-4 w-28" />
          )}
        </div>
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
      <ol className="flex flex-wrap items-center gap-2 text-caption text-ink-muted">
        {crumbs.map((c, i) => (
          <li key={c.href} className="flex items-center gap-2">
            {i > 0 && <span aria-hidden="true">/</span>}
            {i === crumbs.length - 1 ? (
              <span aria-current="page" className="font-semibold text-ink">
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
      <aside className="sticky top-0 hidden h-dvh overflow-y-auto border-r border-line-subtle bg-surface-sunken lg:block">
        <SidebarContent />
      </aside>

      <dialog
        ref={drawerRef}
        aria-label="Menu de navegação"
        onClose={() => setDrawer(false)}
        onClick={(e) => {
          if (e.target === e.currentTarget) setDrawer(false);
        }}
        className="m-0 h-dvh max-h-none w-[min(20rem,calc(100%-2rem))] overflow-y-auto border-r border-line-subtle bg-surface-sunken p-0 text-ink shadow-dialog backdrop:bg-[var(--scrim)]"
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

      <div className="palco min-w-0">
        <header
          ref={topRef}
          className="sticky top-0 z-20 flex min-h-16 items-center gap-3 border-b border-line-subtle bg-canvas/80 px-4 backdrop-blur-lg md:px-6 lg:px-10"
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
            <span className="hidden items-center gap-1.5 rounded-pill border border-violet-border bg-violet-soft px-2.5 py-1 text-2xs font-semibold tracking-[0.04em] text-violet sm:inline-flex">
              <FlaskConical aria-hidden="true" strokeWidth={1.75} className="size-4" />
              Modo demonstração
            </span>
          )}
          <NotificationBell />
          <ThemeToggle />
          <AccountMenu />
        </header>
        {mock && (
          <p className="flex items-center justify-center gap-1 border-b border-violet-border bg-violet-soft px-4 py-1 text-caption text-violet sm:hidden">
            <FlaskConical aria-hidden="true" strokeWidth={1.75} className="size-4" />
            Modo demonstração
          </p>
        )}
        <main id="conteudo" tabIndex={-1} className="mx-auto w-full max-w-workspace px-4 pb-10 pt-6 outline-none sm:px-10 sm:pt-8">
          {children}
        </main>
      </div>
    </div>
  );
}
