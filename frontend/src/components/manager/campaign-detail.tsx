"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Flag, Pencil, RefreshCw, Rocket, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { StatusBadge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { ConfirmDialog, Dialog, useDialogDirty } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { CheckboxField, FormError, SelectField, TextareaField, TextField } from "@/components/ui/fields";
import { Card, DialogActions, FilterButtons, Kpi, Pagination } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { useToast } from "@/components/ui/toast";
import { useMockMode } from "@/components/layout/parts";
import { ApiError, errorMessage } from "@/lib/api/client";
import { campaignsApi } from "@/lib/api/manager";
import type { Campaign, InteractionStatus, InteractionType } from "@/lib/api/types";
import { formatNumber, formatPoints, formatRelativeDay, fromDateTimeInput, toDateTimeInput } from "@/lib/format";
import { applyServerError } from "@/lib/form";
import { igAccountQuery, keys } from "@/lib/queries";
import { safeUrl } from "@/lib/safe-url";
import { parseIntStrict } from "@/lib/validation";
import { campaignPeriodNote, CampaignPeriod } from "./campaigns-list";
import { InteractionItem } from "./interaction-item";
import { Simulator } from "./simulator";

const PAGE = 20;

type StatusFilter = "all" | "awarded" | "duplicate" | "unmatched";
const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "all", label: "Todas" },
  { value: "awarded", label: "Pontuou" },
  { value: "duplicate", label: "Duplicado" },
  { value: "unmatched", label: "Não identificado" },
];

export function CampaignDetail({ id }: { id: string }) {
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const mock = useMockMode();
  const account = useQuery(igAccountQuery());

  const q = useQuery({ queryKey: keys.campaign(id), queryFn: () => campaignsApi.get(id), staleTime: 15_000 });
  const c = q.data;

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [typeFilter, setTypeFilter] = useState<"" | InteractionType>("");
  const [offset, setOffset] = useState(0);
  const [captionOpen, setCaptionOpen] = useState(false);
  const [dlg, setDlg] = useState<null | "edit" | "dispatch" | "end" | "delete">(null);
  const [dlgError, setDlgError] = useState<string | null>(null);
  const [syncInfo, setSyncInfo] = useState<{ ok: string | null; failedAt: string | null }>({ ok: null, failedAt: null });

  const feed = useQuery({
    queryKey: [...keys.interactions(id), statusFilter, typeFilter, offset],
    queryFn: () =>
      campaignsApi.interactions(id, {
        status: statusFilter === "all" ? undefined : (statusFilter as InteractionStatus),
        type: typeFilter || undefined,
        limit: PAGE,
        offset,
      }),
    placeholderData: (prev) => prev,
    enabled: !!c && c.status !== "draft",
  });

  const refreshAll = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: keys.campaign(id) }),
      qc.invalidateQueries({ queryKey: keys.campaigns }),
      qc.invalidateQueries({ queryKey: keys.dashboard }),
    ]);
  };

  const sync = useMutation({
    mutationFn: () => campaignsApi.sync(id),
    onSuccess: async (r) => {
      await refreshAll();
      setSyncInfo({ ok: new Date().toISOString(), failedAt: null });
      toast.success(
        "Sincronização concluída.",
        `${formatNumber(r.fetched)} comentários consultados, ${formatNumber(r.new_interactions)} novas interações, ${formatNumber(r.awarded)} pontuaram.`,
      );
    },
    onError: (e) => {
      setSyncInfo((s) => ({ ...s, failedAt: new Date().toISOString() }));
      toast.error(
        errorMessage(e, "Não foi possível sincronizar agora."),
        e instanceof ApiError && (e.code === "instagram_not_connected" || e.code === "instagram_error")
          ? "Verifique a conexão na página Instagram."
          : "Seus dados foram mantidos.",
      );
    },
  });

  const closeDlg = () => {
    setDlg(null);
    setDlgError(null);
  };

  const dispatch = useMutation({
    mutationFn: () => campaignsApi.dispatch(id),
    onSuccess: async () => {
      await refreshAll();
      closeDlg();
      toast.success("Campanha disparada para a equipe.");
    },
    onError: (e) => setDlgError(errorMessage(e)),
  });
  const end = useMutation({
    mutationFn: () => campaignsApi.end(id),
    onSuccess: async () => {
      await refreshAll();
      closeDlg();
      toast.success("Campanha encerrada. O histórico foi mantido.");
    },
    onError: (e) => setDlgError(errorMessage(e)),
  });
  const remove = useMutation({
    mutationFn: () => campaignsApi.remove(id),
    onSuccess: async () => {
      qc.removeQueries({ queryKey: keys.campaign(id) });
      await qc.invalidateQueries({ queryKey: keys.campaigns });
      toast.success("Rascunho excluído.");
      router.replace("/gestor/campanhas");
    },
    onError: (e) => setDlgError(errorMessage(e)),
  });

  if (q.isPending) {
    return (
      <LoadingRegion className="flex flex-col gap-6">
        <Skeleton className="h-10 w-72" />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[20rem_minmax(0,1fr)]">
          <Skeleton className="h-96" />
          <Skeleton className="h-96" />
        </div>
      </LoadingRegion>
    );
  }
  if (q.isError || !c) {
    const nf = q.error instanceof ApiError && q.error.status === 404;
    return (
      <Card>
        {nf ? (
          <EmptyState
            title="Campanha não encontrada"
            action={<ButtonLink href="/gestor/campanhas">Voltar às campanhas</ButtonLink>}
          />
        ) : (
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        )}
      </Card>
    );
  }

  const permalink = safeUrl(c.permalink);
  const note = campaignPeriodNote(c);
  const caption = c.caption ?? "";
  const longCaption = caption.length > 160;
  const connected = account.data?.status === "active";
  const canSync = c.status !== "draft";

  return (
    <>
      <div className="mb-8 flex flex-col gap-4">
        <Link href="/gestor/campanhas" className="inline-flex min-h-11 items-center gap-2 self-start text-label text-ink-secondary underline-offset-4 hover:text-ink hover:underline">
          <ArrowLeft aria-hidden="true" strokeWidth={1.75} className="size-4" />
          Campanhas
        </Link>
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div className="min-w-0">
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <StatusBadge kind={c.status} campaign />
              {note && <span className="text-label text-info">{note}</span>}
            </div>
            <h1 tabIndex={-1} className="font-heading text-page lg:text-page-wide outline-none">
              {c.title}
            </h1>
            <p className="mt-2 text-label text-ink-secondary tabular-nums">
              <CampaignPeriod c={c} /> · Horário de Brasília
            </p>
          </div>
          <div className="flex flex-wrap gap-3 lg:shrink-0">
            {canSync && (
              <Button icon={RefreshCw} loading={sync.isPending} onClick={() => sync.mutate()}>
                {sync.isPending ? "Sincronizando…" : "Sincronizar"}
              </Button>
            )}
            {c.status === "draft" && (
              <Button icon={Rocket} onClick={() => setDlg("dispatch")}>
                Disparar campanha
              </Button>
            )}
            {c.status !== "ended" && (
              <Button variant="secondary" icon={Pencil} onClick={() => setDlg("edit")}>
                Editar
              </Button>
            )}
            {c.status === "active" && (
              <Button variant="secondary" icon={Flag} onClick={() => setDlg("end")}>
                Encerrar campanha
              </Button>
            )}
            {c.status === "draft" && (
              <Button variant="ghost" icon={Trash2} onClick={() => setDlg("delete")}>
                Excluir rascunho
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card as="section" aria-label="Publicação" className="flex flex-col gap-3 md:p-4">
            <RemoteImage src={c.media_url ?? c.thumbnail_url ?? c.publish_image_url} />
            {caption ? (
              <div>
                <p className={`whitespace-pre-wrap text-label font-normal text-ink-secondary ${captionOpen ? "" : "line-clamp-4"}`}>{caption}</p>
                {longCaption && (
                  <Button variant="ghost" size="sm" className="-ml-3" onClick={() => setCaptionOpen((o) => !o)} aria-expanded={captionOpen}>
                    {captionOpen ? "Mostrar menos" : "Ler legenda completa"}
                  </Button>
                )}
              </div>
            ) : (
              <p className="text-label text-ink-muted">Post sem legenda.</p>
            )}
            {permalink ? (
              <ButtonLink href={permalink} external variant="secondary" size="sm">
                Abrir no Instagram
              </ButtonLink>
            ) : (
              c.source === "publish" && <p className="text-caption text-ink-muted">O link do post aparece depois da publicação.</p>
            )}
            <dl className="grid grid-cols-1 gap-2 border-t border-line-subtle pt-3 text-label">
              <div>
                <dt className="text-caption text-ink-muted">Comentário</dt>
                <dd className="tabular-nums">{c.points_comment > 0 ? formatPoints(c.points_comment) : "Desligado"}</dd>
              </div>
              <div>
                <dt className="text-caption text-ink-muted">Menção em story</dt>
                <dd className="tabular-nums">
                  {c.points_story_mention > 0 ? `${formatPoints(c.points_story_mention)} (até ${c.max_story_mentions} por pessoa)` : "Desligado"}
                </dd>
              </div>
              {c.instructions && (
                <div>
                  <dt className="text-caption text-ink-muted">Instruções</dt>
                  <dd className="whitespace-pre-wrap font-normal text-ink-secondary">{c.instructions}</dd>
                </div>
              )}
            </dl>
          </Card>

        </div>

        <div className="flex min-w-0 flex-col gap-6">
          <section aria-label="Estatísticas" className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Kpi label="Comentários que pontuaram" value={c.stats.comments_awarded} />
            <Kpi label="Menções que pontuaram" value={c.stats.story_mentions_awarded} />
            <Kpi label="Promoters participantes" value={c.stats.participants} />
            <Kpi label="Pontos concedidos" value={c.stats.points_issued} />
          </section>

          {mock && c.status === "active" && <Simulator campaignId={c.id} />}

          <section aria-labelledby="feed-title">
            <h2 id="feed-title" className="mb-1 font-heading text-section">
              Interações
            </h2>
            <p className="mb-4 text-label text-ink-secondary" aria-live="polite">
              {syncInfo.failedAt && (
                <span className="block text-warning">
                  Última tentativa sem sucesso: {formatRelativeDay(syncInfo.failedAt)}. Seus dados foram mantidos.
                </span>
              )}
              Última atualização confirmada: {c.last_synced_at ? formatRelativeDay(c.last_synced_at) : "ainda não sincronizada"}
            </p>

            {c.status === "draft" ? (
              <Card>
                <EmptyState
                  title="Rascunho ainda não disparado"
                  description="As interações aparecem depois que a campanha for disparada para a equipe."
                />
              </Card>
            ) : (
              <>
                <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                  <FilterButtons
                    label="Filtrar por situação"
                    options={STATUS_FILTERS}
                    value={statusFilter}
                    onChange={(v) => {
                      setStatusFilter(v);
                      setOffset(0);
                    }}
                  />
                  <SelectField
                    label="Tipo"
                    value={typeFilter}
                    onChange={(e) => {
                      setTypeFilter(e.target.value as "" | InteractionType);
                      setOffset(0);
                    }}
                    className="sm:w-56"
                  >
                    <option value="">Todos os tipos</option>
                    <option value="comment">Comentários</option>
                    <option value="story_mention">Menções em story</option>
                  </SelectField>
                </div>

                {feed.isPending ? (
                  <LoadingRegion className="flex flex-col gap-2">
                    {Array.from({ length: 4 }, (_, i) => (
                      <Skeleton key={i} className="h-28" />
                    ))}
                  </LoadingRegion>
                ) : feed.isError && !feed.data ? (
                  <Card>
                    <ErrorState onRetry={() => feed.refetch()} retrying={feed.isFetching} />
                  </Card>
                ) : (feed.data?.items.length ?? 0) === 0 ? (
                  <Card>
                    <EmptyState
                      title={statusFilter === "all" && !typeFilter ? "Nenhuma interação ainda" : "Nenhuma interação encontrada"}
                      description={
                        statusFilter === "all" && !typeFilter
                          ? "Use Sincronizar para buscar comentários agora. A verificação pode levar alguns minutos."
                          : "Tente outro filtro."
                      }
                    />
                  </Card>
                ) : (
                  <ul className="flex flex-col gap-2" aria-busy={feed.isFetching}>
                    {feed.data!.items.map((i) => (
                      <InteractionItem key={i.id} item={i} />
                    ))}
                  </ul>
                )}
                {feed.data && <Pagination total={feed.data.total} limit={PAGE} offset={offset} onChange={setOffset} busy={feed.isFetching && feed.isPlaceholderData} />}
              </>
            )}
          </section>
        </div>
      </div>

      <EditDialog campaign={c} open={dlg === "edit"} onClose={closeDlg} onSaved={refreshAll} />

      <ConfirmDialog
        open={dlg === "dispatch"}
        onClose={closeDlg}
        onConfirm={() => {
          setDlgError(null);
          dispatch.mutate();
        }}
        title="Disparar campanha"
        description={
          c.source === "publish"
            ? "O post será publicado no seu Instagram e a campanha ficará disponível para os promoters aprovados da equipe."
            : "A campanha ficará disponível para os promoters aprovados da equipe. Não há envio de DM, WhatsApp ou e-mail."
        }
        confirmLabel={c.source === "publish" ? "Publicar e disparar" : "Disparar campanha"}
        loadingLabel="Disparando…"
        loading={dispatch.isPending}
        error={dlgError ?? (!connected && c.source === "publish" ? "Conecte o Instagram para publicar." : null)}
      />
      <ConfirmDialog
        open={dlg === "end"}
        onClose={closeDlg}
        onConfirm={() => {
          setDlgError(null);
          end.mutate();
        }}
        title="Encerrar campanha"
        description="Depois de encerrada, novas participações não pontuam. O histórico e os pontos já concedidos são mantidos."
        confirmLabel="Encerrar campanha"
        loadingLabel="Encerrando…"
        variant="danger"
        loading={end.isPending}
        error={dlgError}
      />
      <ConfirmDialog
        open={dlg === "delete"}
        onClose={closeDlg}
        onConfirm={() => {
          setDlgError(null);
          remove.mutate();
        }}
        title="Excluir rascunho"
        description={`Excluir o rascunho “${c.title}”? Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir rascunho"
        loadingLabel="Excluindo…"
        variant="danger"
        loading={remove.isPending}
        error={dlgError}
      />
    </>
  );
}

/* ---------------- edit ---------------- */

const intPts = z.string().refine((v) => {
  const n = parseIntStrict(v);
  return Number.isInteger(n) && n >= 1 && n <= 100000;
}, "Informe um número inteiro de 1 a 100.000.");

const editSchema = z
  .object({
    title: z.string().trim().min(3, "O título precisa ter de 3 a 120 caracteres.").max(120, "O título precisa ter de 3 a 120 caracteres."),
    description: z.string().max(2000, "Use no máximo 2000 caracteres."),
    instructions: z.string().max(2000, "Use no máximo 2000 caracteres."),
    endsAt: z.string(),
    commentOn: z.boolean(),
    commentPoints: z.string(),
    storyOn: z.boolean(),
    storyPoints: z.string(),
  })
  .superRefine((v, ctx) => {
    if (v.commentOn && !intPts.safeParse(v.commentPoints).success)
      ctx.addIssue({ code: "custom", path: ["commentPoints"], message: "Informe um número inteiro de 1 a 100.000." });
    if (v.storyOn && !intPts.safeParse(v.storyPoints).success)
      ctx.addIssue({ code: "custom", path: ["storyPoints"], message: "Informe um número inteiro de 1 a 100.000." });
    if (!v.commentOn && !v.storyOn) ctx.addIssue({ code: "custom", path: ["commentOn"], message: "Habilite pelo menos uma ação." });
  });
type EditValues = z.infer<typeof editSchema>;

function EditDialog({ campaign, open, onClose, onSaved }: { campaign: Campaign; open: boolean; onClose: () => void; onSaved: () => Promise<void> }) {
  return (
    <Dialog open={open} onClose={onClose} size="lg" title="Editar campanha">
      <EditForm campaign={campaign} onClose={onClose} onSaved={onSaved} />
    </Dialog>
  );
}

function EditForm({ campaign: c, onClose, onSaved }: { campaign: Campaign; onClose: () => void; onSaved: () => Promise<void> }) {
  const toast = useToast();
  const draft = c.status === "draft";
  const [formError, setFormError] = useState<string | null>(null);
  const form = useForm<EditValues>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      title: c.title,
      description: c.description ?? "",
      instructions: c.instructions ?? "",
      endsAt: toDateTimeInput(c.ends_at),
      commentOn: c.points_comment > 0,
      commentPoints: String(c.points_comment > 0 ? c.points_comment : 10),
      storyOn: c.points_story_mention > 0,
      storyPoints: String(c.points_story_mention > 0 ? c.points_story_mention : 25),
    },
    mode: "onBlur",
  });
  const w = useWatch({ control: form.control });
  const e = form.formState.errors;
  useDialogDirty(form.formState.isDirty);

  const save = useMutation({
    mutationFn: (v: EditValues) => {
      const ends = fromDateTimeInput(v.endsAt);
      if (c.starts_at && ends && new Date(ends) <= new Date(c.starts_at)) {
        form.setError("endsAt", { type: "validate", message: "O término precisa ser depois do início." });
        throw new Error("validation");
      }
      return campaignsApi.update(c.id, {
        title: v.title.trim(),
        description: v.description.trim(),
        instructions: v.instructions.trim(),
        ends_at: ends,
        ...(draft
          ? {
              points_comment: v.commentOn ? parseIntStrict(v.commentPoints) : 0,
              points_story_mention: v.storyOn ? parseIntStrict(v.storyPoints) : 0,
            }
          : {}),
      });
    },
    onSuccess: async () => {
      await onSaved();
      onClose();
      toast.success("Campanha atualizada.");
    },
    onError: (err) => {
      if (err instanceof ApiError) {
        setFormError(
          applyServerError(err, form.setError, ["title", "description", "instructions", "endsAt", "commentPoints", "storyPoints"], {
            ends_at: "endsAt",
            points_comment: "commentPoints",
            points_story_mention: "storyPoints",
          }),
        );
      }
    },
  });

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((v) => {
        setFormError(null);
        save.mutate(v);
      })}
      className="flex flex-col gap-4"
    >
      <FormError message={formError} />
      {!draft && (
        <p className="rounded-control bg-surface-raised p-3 text-label text-ink-secondary">
          Depois do disparo, o post, os pontos e o início ficam bloqueados. Título, descrição, instruções e término podem mudar sem afetar pontos já concedidos.
        </p>
      )}
      <TextField label="Título" data-autofocus="" error={e.title?.message} {...form.register("title")} />
      <TextareaField label="Descrição" optional error={e.description?.message} {...form.register("description")} />
      <TextareaField label="Instruções" optional error={e.instructions?.message} {...form.register("instructions")} />
      <TextField
        label="Término (horário de Brasília)"
        optional
        type="datetime-local"
        error={e.endsAt?.message}
        {...form.register("endsAt")}
      />
      {draft && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="min-w-0">
            <CheckboxField label="Pontuar comentário" {...form.register("commentOn")} />
            <TextField label="Pontos por comentário" type="number" inputMode="numeric" disabled={!w.commentOn} error={e.commentPoints?.message ?? e.commentOn?.message} {...form.register("commentPoints")} />
          </div>
          <div className="min-w-0">
            <CheckboxField label="Pontuar menção em story" {...form.register("storyOn")} />
            <TextField label="Pontos por menção em story" type="number" inputMode="numeric" disabled={!w.storyOn} error={e.storyPoints?.message} {...form.register("storyPoints")} />
          </div>
        </div>
      )}
      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={save.isPending}>
          {save.isPending ? "Salvando…" : "Salvar alterações"}
        </Button>
      </DialogActions>
    </form>
  );
}
