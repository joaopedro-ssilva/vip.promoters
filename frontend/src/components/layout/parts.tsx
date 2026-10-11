"use client";

import { useQuery } from "@tanstack/react-query";
import { Moon, Sun, Ticket } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type RefObject } from "react";
import { authApi } from "@/lib/api/auth";
import { cn } from "@/lib/cn";
import { useTheme } from "@/lib/theme";
import { Button } from "@/components/ui/button";

export function Brand({ href = "/", className, withIcon = true, compact = false }: { href?: string; className?: string; withIcon?: boolean; compact?: boolean }) {
  return (
    <Link href={href} aria-label="VIP Promoters, página inicial" className={cn("inline-flex min-h-11 items-center gap-2 rounded-control", className)}>
      {withIcon && <Ticket aria-hidden="true" strokeWidth={1.75} className="size-6 text-accent" />}
      <span aria-hidden="true" className="font-heading text-[1.5rem] font-bold leading-none tracking-[0.01em]">
        VIP
      </span>
      <span aria-hidden="true" className={cn("font-sans text-label font-bold leading-[1.4] tracking-normal", compact && "max-md:hidden")}>
        Promoters
      </span>
    </Link>
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
