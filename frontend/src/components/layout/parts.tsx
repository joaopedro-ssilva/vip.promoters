"use client";

import { useQuery } from "@tanstack/react-query";
import { Moon, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type RefObject } from "react";
import { authApi } from "@/lib/api/auth";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";

/**
 * A marca do produto, no desenho do design system do Camarim: um quadrado lima
 * de cantos generosos com o sinal recortado em escuro, e o logotipo em Syne 800.
 * O sinal é um ingresso com a perfuração no meio — a "entrada VIP".
 */
export function Brand({ href = "/", className, withIcon = true, compact = false }: { href?: string; className?: string; withIcon?: boolean; compact?: boolean }) {
  return (
    <Link href={href} aria-label="VIP Promoters, página inicial" className={cn("inline-flex min-h-11 items-center gap-3 rounded-control", className)}>
      {withIcon && <BrandMark className="size-8 shrink-0" />}
      <span aria-hidden="true" className="display text-brand font-extrabold leading-none tracking-[-0.03em] text-ink-strong">
        VIP
        <span className={cn("ml-1.5 font-bold text-ink-secondary", compact && "max-md:hidden")}>Promoters</span>
      </span>
    </Link>
  );
}

/** Só o sinal da marca, para onde o nome não cabe. */
export function BrandMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 60 60" fill="none" aria-hidden="true" className={className}>
      <rect width="60" height="60" rx="18" fill="#BCF23F" />
      <path
        d="M14 22a4 4 0 0 1 4-4h24a4 4 0 0 1 4 4v3.5a4.5 4.5 0 0 0 0 9V38a4 4 0 0 1-4 4H18a4 4 0 0 1-4-4v-3.5a4.5 4.5 0 0 0 0-9z"
        stroke="#07060B"
        strokeWidth="4.5"
        strokeLinejoin="round"
      />
      <path d="M30 22v16" stroke="#07060B" strokeWidth="4" strokeLinecap="round" strokeDasharray="0.1 6" />
    </svg>
  );
}

export function ThemeToggle() {
  const [theme, setTheme] = useTheme();
  const next = theme === "dark" ? "light" : "dark";
  const Icon = theme === "dark" ? Sun : Moon;
  return (
    <Button
      variant="ghost"
      iconOnly
      aria-label={theme === "dark" ? "Ativar tema claro" : "Ativar tema escuro"}
      onClick={() => setTheme(next)}
    >
      <Icon aria-hidden="true" strokeWidth={1.75} className="size-5" />
    </Button>
  );
}

/** Mock-mode flag from GET /config (cached for the whole session). */
export function useMockMode(): boolean {
  const q = useQuery({
    queryKey: ["config"],
    queryFn: authApi.config,
    staleTime: Infinity,
    gcTime: Infinity,
  });
  return q.data?.mock_mode === true;
}

/**
 * Keeps --topbar-height / --tabbar-height in sync with the real rendered
 * height of the bars (they grow with large text / zoom), and restores the
 * defaults on unmount.
 */
export function useBarHeight(ref: RefObject<HTMLElement | null>, cssVar: "--topbar-height" | "--tabbar-height") {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const root = document.documentElement;
    const apply = () => {
      const h = el.getBoundingClientRect().height;
      root.style.setProperty(cssVar, `${Math.ceil(h)}px`);
    };
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(el);
    return () => {
      ro.disconnect();
      root.style.removeProperty(cssVar);
    };
  }, [ref, cssVar]);
}

/** After a client-side navigation, move focus to <main> so keyboard / SR users land on the new page. */
export function useRouteFocus() {
  const pathname = usePathname();
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    const main = document.getElementById("conteudo");
    main?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }, [pathname]);
}
