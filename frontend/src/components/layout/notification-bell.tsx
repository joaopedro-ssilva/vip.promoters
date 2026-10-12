"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { useRouter } from "next/navigation";
import { notificationsApi } from "@/lib/api/promoter";
import { cn } from "@/lib/cn";
import { formatRelativeDay } from "@/lib/format";
import { isSafeRelativePath } from "@/lib/safe-url";
import { Button } from "@/components/ui/button";
import { Popover, usePopoverClose } from "@/components/ui/popover";
import { Skeleton } from "@/components/ui/feedback";

const KEY = ["notifications"] as const;

export function NotificationBell() {

  const q = useQuery({
    queryKey: KEY,
    queryFn: () => notificationsApi.list(20),
    staleTime: 30_000,
    // polls only while the tab is visible (react-query pauses interval refetch in background tabs)
    refetchInterval: 60_000,
    refetchIntervalInBackground: false,
    refetchOnWindowFocus: true,
  });

  const unread = q.data?.unread_count ?? 0;

  return (
    <Popover
      label={unread > 0 ? `Notificações, ${unread} não ${unread === 1 ? "lida" : "lidas"}` : "Notificações"}
      trigger={
        <>
          <Bell aria-hidden="true" strokeWidth={1.75} className="size-5" />
          {unread > 0 && (
            <span
              aria-hidden="true"
              className="absolute right-0.5 top-0.5 grid min-h-5 min-w-5 place-items-center rounded-pill bg-accent px-1 text-2xs font-bold tabular-nums text-on-accent"
            >
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </>
      }
    >
      <BellPanel />
    </Popover>
  );
}

function BellPanel() {
  const close = usePopoverClose();
  const qc = useQueryClient();
  const router = useRouter();
  const q = useQuery({ queryKey: KEY, queryFn: () => notificationsApi.list(20), staleTime: 30_000 });
  const readOne = useMutation({ mutationFn: notificationsApi.read, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
  const readAll = useMutation({ mutationFn: notificationsApi.readAll, onSuccess: () => qc.invalidateQueries({ queryKey: KEY }) });
  const unread = q.data?.unread_count ?? 0;
  const items = q.data?.items ?? [];
  return (
        <div>
          <div className="flex items-center justify-between gap-2 px-2 py-1">
            <h2 className="font-heading text-section">Notificações</h2>
            {unread > 0 && (
              <Button size="sm" variant="ghost" icon={CheckCheck} loading={readAll.isPending} onClick={() => readAll.mutate()}>
                Marcar todas
              </Button>
            )}
          </div>
          {q.isPending ? (
            <div className="flex flex-col gap-2 p-2" role="status" aria-busy="true">
              <span className="sr-only">Carregando…</span>
              <Skeleton className="h-14" />
              <Skeleton className="h-14" />
            </div>
          ) : q.isError ? (
            <div className="p-3">
              <p className="text-label text-ink-secondary">Não foi possível carregar as notificações.</p>
              <Button size="sm" variant="secondary" className="mt-2" onClick={() => q.refetch()}>
                Tentar novamente
              </Button>
            </div>
          ) : items.length === 0 ? (
            <p className="p-4 text-center text-label text-ink-secondary">Nenhuma notificação por aqui.</p>
          ) : (
            <ul className="max-h-[min(24rem,60dvh)] overflow-y-auto">
              {items.map((n) => {
                const isUnread = !n.read_at;
                const link = n.link && isSafeRelativePath(n.link) ? n.link : null;
                const body = (
                  <>
                    <span className="flex items-start justify-between gap-2">
                      <span className="min-w-0 text-label text-ink">{n.title}</span>
                      {isUnread && <span className="shrink-0 text-caption text-success">Nova</span>}
                    </span>
                    {n.body && <span className="mt-0.5 block text-label font-normal text-ink-secondary">{n.body}</span>}
                    <span className="mt-1 block text-caption text-ink-muted">{formatRelativeDay(n.created_at)}</span>
                  </>
                );
                const cls = cn(
                  "block w-full min-h-11 rounded-control border border-transparent px-3 py-2 text-left hover:bg-surface-hover active:bg-surface-raised",
                  isUnread && "bg-surface-raised",
                );
                return (
                  <li key={n.id}>
                    <button
                      type="button"
                      className={cls}
                      onClick={() => {
                        if (isUnread) readOne.mutate(n.id);
                        if (link) {
                          close();
                          router.push(link);
                        }
                      }}
                    >
                      {body}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
  );
}
