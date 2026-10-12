"use client";

import { Circle, CircleCheck } from "lucide-react";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/badge";
import { ButtonLink, Button } from "@/components/ui/button";
import { CopyButton } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import type { PromoterCampaign } from "@/lib/api/types";
import { formatDate, isFuture, formatPoints, formatShortDateTime } from "@/lib/format";
import { useTeam } from "./team-provider";

export function Checklist({ c }: { c: PromoterCampaign }) {
  const rows: { key: string; label: string; points: number; done: boolean; note?: string }[] = [];
  if (c.points_comment > 0) rows.push({ key: "c", label: "Comentar no post", points: c.points_comment, done: c.my.comment_done });
  if (c.points_story_mention > 0) {
    rows.push({
      key: "s",
      label: "Mencionar no story",
      points: c.points_story_mention,
      done: c.my.story_mentions_done > 0,
      note: c.max_story_mentions > 1 ? `${c.my.story_mentions_done} de ${c.max_story_mentions}` : undefined,
    });
  }
  const parts: string[] = [];
  if (c.points_comment > 0) parts.push("1 comentário");
  if (c.points_story_mention > 0) parts.push(`${c.max_story_mentions} ${c.max_story_mentions === 1 ? "menção" : "menções"} em story`);
  return (
    <div>
      <ul className="flex flex-col">
        {rows.map((r) => (
          <li key={r.key} className="flex min-h-11 items-center gap-3 border-t border-line-subtle py-2 first:border-t-0">
            {r.done ? (
              <CircleCheck aria-hidden="true" strokeWidth={1.75} className="size-5 shrink-0 text-success" />
            ) : (
              <Circle aria-hidden="true" strokeWidth={1.75} className="size-5 shrink-0 text-line" />
            )}
            <span className="min-w-0 flex-1 text-label">
              {r.label}
              <span className="block text-caption font-medium text-ink-muted">
                {r.done ? "Pontuou" : "Ainda não verificado"}
                {r.note ? ` · ${r.note}` : ""}
              </span>
            </span>
            <span className="text-label tabular-nums text-success">+{formatPoints(r.points)}</span>
          </li>
        ))}
      </ul>
      {parts.length > 0 && (
        <p className="mt-2 text-caption text-ink-muted">Até {parts.join(" e ")} pontuados por pessoa nesta campanha. Repetições valem zero.</p>
      )}
    </div>
  );
}

export function CampaignCard({ c }: { c: PromoterCampaign }) {
  const team = useTeam();
  const handle = team.memberships.find((m) => m.organization.id === c.organization_id)?.organization.instagram_username;
  const ended = c.status === "ended";
  return (
    <li className="flex min-w-0 flex-col gap-3 rounded-card border border-line-subtle bg-surface p-4">
      <div className="flex gap-3">
        <RemoteImage src={c.thumbnail_url ?? c.media_url} ratio="aspect-square" className="size-[5.5rem] shrink-0" />
        <div className="min-w-0 flex-1">
          <StatusBadge kind={c.status} campaign />
          <h3 className="mt-1 font-sans text-body font-bold [overflow-wrap:anywhere]">
            <Link href={`/promoter/campanhas/${c.id}`} className="hover:underline">
              {c.title}
            </Link>
          </h3>
          <p className="text-caption text-ink-muted tabular-nums">
            {c.ends_at ? `${ended ? "Encerrou" : "Termina"} em ${formatShortDateTime(c.ends_at)}` : "Sem data de término"}
            {isFuture(c.starts_at) ? ` · começa em ${formatDate(c.starts_at)}` : ""}
          </p>
        </div>
      </div>
      <Checklist c={c} />
      {c.points_story_mention > 0 && handle && !ended && (
        <p className="flex flex-wrap items-center gap-2 text-label font-normal text-ink-secondary">
          Publique um story e mencione @{handle}
          <CopyButton text={`@${handle}`} label="Copiar @" successMessage="@ copiado." />
        </p>
      )}
      <div className="mt-auto flex flex-col gap-2">
        {ended ? (
          <>
            <Button variant="secondary" disabled block>
              Campanha encerrada
            </Button>
            <p className="text-caption text-ink-muted">Não é mais possível pontuar nesta campanha.</p>
          </>
        ) : c.permalink ? (
          <ButtonLink href={c.permalink} external variant="secondary" block>
            Abrir no Instagram
          </ButtonLink>
        ) : null}
        <ButtonLink href={`/promoter/campanhas/${c.id}`} variant="ghost" size="sm" block>
          Ver detalhes<span className="sr-only">: {c.title}</span>
        </ButtonLink>
      </div>
    </li>
  );
}
