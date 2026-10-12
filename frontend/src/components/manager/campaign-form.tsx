"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ImagePlus, Info } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { CheckboxField, FormError, TextareaField, TextField } from "@/components/ui/fields";
import { Card, PageHeader, Tabs } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { useToast } from "@/components/ui/toast";
import { useConnectInstagram } from "@/components/shared/use-connect-instagram";
import { ApiError, errorMessage } from "@/lib/api/client";
import { campaignsApi, instagramApi, teamApi, uploadsApi, type CampaignCreateInput } from "@/lib/api/manager";
import type { InstagramMedia } from "@/lib/api/types";
import { cn } from "@/lib/cn";
import { formatDate, formatDateTime, formatNumber, fromDateTimeInput } from "@/lib/format";
import { applyServerError } from "@/lib/form";
import { igAccountQuery, keys } from "@/lib/queries";
import { parseIntStrict } from "@/lib/validation";

const MAX_UPLOAD = 8 * 1024 * 1024;

const intField = (min: number, max: number, msg: string) =>
  z.string().refine((v) => {
    const n = parseIntStrict(v);
    return Number.isInteger(n) && n >= min && n <= max;
  }, msg);

const schema = z
  .object({
    title: z.string().trim().min(3, "O título precisa ter de 3 a 120 caracteres.").max(120, "O título precisa ter de 3 a 120 caracteres."),
    description: z.string().max(2000, "Use no máximo 2000 caracteres."),
    instructions: z.string().max(2000, "Use no máximo 2000 caracteres."),
    caption: z.string().max(2200, "A legenda pode ter no máximo 2200 caracteres."),
    commentOn: z.boolean(),
    commentPoints: z.string(),
    storyOn: z.boolean(),
    storyPoints: z.string(),
    maxStory: intField(1, 10, "Informe um número de 1 a 10."),
    startsAt: z.string(),
    endsAt: z.string(),
  })
  .superRefine((v, ctx) => {
    const pts = intField(1, 100000, "Informe um número inteiro de 1 a 100.000.");
    if (v.commentOn && !pts.safeParse(v.commentPoints).success)
      ctx.addIssue({ code: "custom", path: ["commentPoints"], message: "Informe um número inteiro de 1 a 100.000." });
    if (v.storyOn && !pts.safeParse(v.storyPoints).success)
      ctx.addIssue({ code: "custom", path: ["storyPoints"], message: "Informe um número inteiro de 1 a 100.000." });
    if (!v.commentOn && !v.storyOn)
      ctx.addIssue({ code: "custom", path: ["commentOn"], message: "Habilite pelo menos uma ação." });
    const s = fromDateTimeInput(v.startsAt);
    const e = fromDateTimeInput(v.endsAt);
    if (s && e && new Date(e) <= new Date(s))
      ctx.addIssue({ code: "custom", path: ["endsAt"], message: "O término precisa ser depois do início." });
  });
type Values = z.infer<typeof schema>;
const FIELD_NAMES = ["title", "description", "instructions", "caption", "commentPoints", "storyPoints", "maxStory", "startsAt", "endsAt"];
const SERVER_MAP: Record<string, string> = {
  points_comment: "commentPoints",
  points_story_mention: "storyPoints",
  max_story_mentions: "maxStory",
  starts_at: "startsAt",
  ends_at: "endsAt",
};

type Source = "existing" | "publish";

interface UploadState {
  status: "idle" | "uploading" | "ready" | "error";
  preview: string | null;
  url: string | null;
  error: string | null;
  name: string | null;
}

export function NewCampaign() {
  const router = useRouter();
  const qc = useQueryClient();
  const toast = useToast();
  const connect = useConnectInstagram();
  const account = useQuery(igAccountQuery());
  const connected = account.data?.status === "active";

  const [source, setSource] = useState<Source>("existing");
  const [media, setMedia] = useState<InstagramMedia | null>(null);
  const [upload, setUpload] = useState<UploadState>({ status: "idle", preview: null, url: null, error: null, name: null });
  const [contentError, setContentError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [review, setReview] = useState(false);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      description: "",
      instructions: "",
      caption: "",
      commentOn: true,
      commentPoints: "10",
      storyOn: true,
      storyPoints: "25",
      maxStory: "1",
      startsAt: "",
      endsAt: "",
    },
    mode: "onBlur",
  });
  const e = form.formState.errors;
  const w = useWatch({ control: form.control });

  const previewRef = useRef<string | null>(null);
  useEffect(() => {
    return () => {
      if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    };
  }, []);

  const approved = useQuery({
    queryKey: [...keys.members, "approved-count"],
    queryFn: () => teamApi.members({ status: "approved", limit: 1 }),
    staleTime: 60_000,
    enabled: review,
  });

  const mediaQuery = useInfiniteQuery({
    queryKey: keys.igMedia,
    queryFn: ({ pageParam }) => instagramApi.media({ after: pageParam, limit: 12 }),
    initialPageParam: null as string | null,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    enabled: connected,
    staleTime: 60_000,
  });
  const mediaItems = mediaQuery.data?.pages.flatMap((p) => p.items) ?? [];

  const uploadMut = useMutation({ mutationFn: uploadsApi.image });

  async function onPickFile(file: File | null) {
    if (!file) return;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = null;
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setUpload({ status: "error", preview: null, url: null, name: file.name, error: "Use uma imagem JPEG ou PNG." });
      return;
    }
    if (file.size > MAX_UPLOAD) {
      setUpload({ status: "error", preview: null, url: null, name: file.name, error: "A imagem pode ter no máximo 8 MB." });
      return;
    }
    const preview = URL.createObjectURL(file);
    previewRef.current = preview;
    setUpload({ status: "uploading", preview, url: null, error: null, name: file.name });
    setContentError(null);
    try {
      const { url } = await uploadMut.mutateAsync(file);
      setUpload({ status: "ready", preview, url, error: null, name: file.name });
    } catch (err) {
      setUpload({ status: "error", preview, url: null, name: file.name, error: errorMessage(err, "Não foi possível enviar a imagem.") });
    }
  }

  function checkContent(): boolean {
    if (source === "existing" && !media) {
      setContentError("Selecione uma publicação.");
      return false;
    }
    if (source === "publish") {
      if (upload.status === "uploading") {
        setContentError("Aguarde o envio da imagem terminar.");
        return false;
      }
      if (upload.status !== "ready" || !upload.url) {
        setContentError("Envie uma imagem para publicar.");
        return false;
      }
    }
    setContentError(null);
    return true;
  }

  function buildPayload(v: Values): CampaignCreateInput {
    const starts = fromDateTimeInput(v.startsAt);
    const ends = fromDateTimeInput(v.endsAt);
    const payload: CampaignCreateInput = {
      title: v.title.trim(),
      source,
      points_comment: v.commentOn ? parseIntStrict(v.commentPoints) : 0,
      points_story_mention: v.storyOn ? parseIntStrict(v.storyPoints) : 0,
      max_story_mentions: parseIntStrict(v.maxStory),
    };
    if (v.description.trim()) payload.description = v.description.trim();
    if (v.instructions.trim()) payload.instructions = v.instructions.trim();
    if (starts) payload.starts_at = starts;
    if (ends) payload.ends_at = ends;
    if (source === "existing" && media) payload.ig_media_id = media.id;
    if (source === "publish") {
      if (upload.url) payload.image_url = upload.url;
      if (v.caption.trim()) payload.caption = v.caption.trim();
    }
    return payload;
  }

  const createMut = useMutation({ mutationFn: campaignsApi.create });
  const dispatchMut = useMutation({ mutationFn: campaignsApi.dispatch });

  async function saveDraft(v: Values) {
    setFormError(null);
    if (!checkContent()) return;
    try {
      const c = await createMut.mutateAsync(buildPayload(v));
      await qc.invalidateQueries({ queryKey: keys.campaigns });
      toast.success("Rascunho salvo.");
      router.push(`/gestor/campanhas/${c.id}`);
    } catch (err) {
      setFormError(applyServerError(err, form.setError, FIELD_NAMES, SERVER_MAP));
    }
  }

  async function confirmDispatch() {
    setReviewError(null);
    const v = form.getValues();
    try {
      let id = createdId;
      if (!id) {
        const c = await createMut.mutateAsync(buildPayload(v));
        id = c.id;
        setCreatedId(id);
      }
      await dispatchMut.mutateAsync(id);
      await qc.invalidateQueries({ queryKey: keys.campaigns });
      await qc.invalidateQueries({ queryKey: keys.dashboard });
      setReview(false);
      toast.success(source === "publish" ? "Post publicado e campanha disparada." : "Campanha disparada para a equipe.");
      router.push(`/gestor/campanhas/${id}`);
    } catch (err) {
      setReviewError(
        err instanceof ApiError && err.code === "instagram_not_connected"
          ? "Conecte o Instagram para disparar a campanha."
          : errorMessage(err),
      );
    }
  }

  const busy = createMut.isPending || dispatchMut.isPending;
  const sourceLabelPublish = source === "publish";
  const caption = w.caption ?? "";

  const summary = (
    <dl className="flex flex-col gap-3 text-label">
      <div>
        <dt className="text-caption text-ink-muted">Publicação</dt>
        <dd>
          {source === "existing"
            ? media
              ? `Post do Instagram de ${formatDate(media.timestamp)}`
              : "Nenhuma selecionada"
            : upload.status === "ready"
              ? "Novo post (imagem enviada)"
              : "Nenhuma imagem"}
        </dd>
      </div>
      <div>
        <dt className="text-caption text-ink-muted">Título</dt>
        <dd className="break-words">{w.title?.trim() || "—"}</dd>
      </div>
      <div>
        <dt className="text-caption text-ink-muted">Pontos</dt>
        <dd className="tabular-nums">
          {w.commentOn ? `Comentário: ${w.commentPoints || "—"}` : "Comentário: desligado"}
          <br />
          {w.storyOn ? `Menção em story: ${w.storyPoints || "—"}` : "Menção em story: desligada"}
        </dd>
      </div>
      <div>
        <dt className="text-caption text-ink-muted">Período (horário de Brasília)</dt>
        <dd className="tabular-nums">
          {w.startsAt ? formatDateTime(fromDateTimeInput(w.startsAt)) : "Ao disparar"} até{" "}
          {w.endsAt ? formatDateTime(fromDateTimeInput(w.endsAt)) : "sem data de término"}
        </dd>
      </div>
    </dl>
  );

  return (
    <>
      <PageHeader title="Nova campanha" description="Escolha o post, defina os pontos e o período, e dispare para a equipe." />

      <div className="grid grid-cols-1 gap-8 xl:grid-cols-[minmax(0,48rem)_minmax(0,20rem)]">
        <form noValidate onSubmit={form.handleSubmit(saveDraft, () => checkContent())} className="flex min-w-0 flex-col gap-8">
          <FormError message={formError} />

          <Card as="section" aria-labelledby="sec-1">
            <h2 id="sec-1" className="mb-4 font-heading text-section">
              <span className="mr-2 text-success tabular-nums">01</span>Publicação
            </h2>
            <Tabs
              label="Origem da publicação"
              tabs={[
                { id: "existing", label: "Post existente" },
                { id: "publish", label: "Publicar novo" },
              ]}
              value={source}
              onChange={(v) => {
                setSource(v);
                setContentError(null);
              }}
            >
              {source === "existing" ? (
                account.isPending ? (
                  <LoadingRegion className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {Array.from({ length: 6 }, (_, i) => (
                      <Skeleton key={i} className="aspect-square" />
                    ))}
                  </LoadingRegion>
                ) : !connected ? (
                  <EmptyState
                    align="start"
                    icon={Info}
                    title={account.data ? "Reconecte o Instagram" : "Conecte o Instagram"}
                    description="Para escolher uma publicação, conecte sua conta profissional. Você pode salvar o rascunho antes."
                    action={
                      <Button loading={connect.isPending} onClick={() => connect.mutate()}>
                        {connect.isPending ? "Conectando…" : account.data ? "Reconectar" : "Conectar Instagram"}
                      </Button>
                    }
                  />
                ) : mediaQuery.isPending ? (
                  <LoadingRegion className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                    {Array.from({ length: 6 }, (_, i) => (
                      <Skeleton key={i} className="aspect-square" />
                    ))}
                  </LoadingRegion>
                ) : mediaQuery.isError ? (
                  <ErrorState onRetry={() => mediaQuery.refetch()} message={errorMessage(mediaQuery.error, "Não foi possível carregar as publicações.")} />
                ) : mediaItems.length === 0 ? (
                  <EmptyState
                    align="start"
                    title="Nenhuma publicação encontrada"
                    description="Publique no Instagram ou use a aba “Publicar novo” para criar o post por aqui."
                    action={
                      <Button variant="secondary" onClick={() => setSource("publish")}>
                        Publicar novo
                      </Button>
                    }
                  />
                ) : (
                  <fieldset>
                    <legend className="sr-only">Publicações do Instagram</legend>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                      {mediaItems.map((m) => {
                        const selected = media?.id === m.id;
                        return (
                          <label
                            key={m.id}
                            className={cn(
                              "flex min-w-0 cursor-pointer flex-col gap-2 rounded-card border-2 bg-surface p-2 hover:bg-surface-hover has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-[3px] has-[:focus-visible]:outline-focus",
                              selected ? "border-accent" : "border-line",
                            )}
                          >
                            <input
                              type="radio"
                              name="media"
                              className="sr-only"
                              checked={selected}
                              onChange={() => {
                                setMedia(m);
                                setContentError(null);
                              }}
                            />
                            <RemoteImage src={m.thumbnail_url ?? m.media_url} ratio="aspect-square" />
                            <span className="min-w-0 text-caption text-ink-muted tabular-nums">{formatDate(m.timestamp)}</span>
                            <span className="line-clamp-2 min-w-0 text-label font-normal text-ink-secondary">{m.caption || "Sem legenda"}</span>
                            {selected && (
                              <span className="inline-flex items-center gap-1 text-caption text-success">
                                <Check aria-hidden="true" strokeWidth={1.75} className="size-4" />
                                Selecionado
                              </span>
                            )}
                          </label>
                        );
                      })}
                    </div>
                    {mediaQuery.hasNextPage && (
                      <div className="mt-4">
                        <Button variant="secondary" loading={mediaQuery.isFetchingNextPage} onClick={() => mediaQuery.fetchNextPage()}>
                          {mediaQuery.isFetchingNextPage ? "Carregando…" : "Carregar mais publicações"}
                        </Button>
                      </div>
                    )}
                  </fieldset>
                )
              ) : (
                <div className="flex flex-col gap-4">
                  <div>
                    <p className="mb-2 text-label">Imagem do post</p>
                    <div className="flex flex-col gap-3 sm:flex-row">
                      <div className="w-full sm:w-48 sm:shrink-0">
                        {upload.preview ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={upload.preview} alt="Pré-visualização da imagem selecionada" className="aspect-square w-full rounded-control object-cover" />
                        ) : (
                          <div className="flex aspect-square w-full flex-col items-center justify-center gap-1 rounded-control bg-surface-raised text-caption text-ink-muted">
                            <ImagePlus aria-hidden="true" strokeWidth={1.75} className="size-6" />
                            Sem imagem
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <label className="inline-flex min-h-12 cursor-pointer items-center gap-2 rounded-control border border-line bg-surface px-4 text-label hover:bg-surface-hover has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-[3px] has-[:focus-visible]:outline-focus">
                          <ImagePlus aria-hidden="true" strokeWidth={1.75} className="size-4" />
                          {upload.preview ? "Trocar imagem" : "Escolher imagem"}
                          <input
                            type="file"
                            accept="image/jpeg,image/png"
                            className="sr-only"
                            onChange={(ev) => {
                              void onPickFile(ev.target.files?.[0] ?? null);
                              ev.target.value = "";
                            }}
                          />
                        </label>
                        <p className="mt-2 text-caption text-ink-muted">JPEG ou PNG, até 8 MB. A imagem precisa ficar publicamente acessível para o Instagram.</p>
                        <p className="mt-2 text-label" role="status">
                          {upload.status === "uploading" && "Enviando…"}
                          {upload.status === "ready" && <span className="text-success">Imagem pronta{upload.name ? `: ${upload.name}` : ""}.</span>}
                          {upload.status === "error" && <span className="text-danger">{upload.error}</span>}
                        </p>
                      </div>
                    </div>
                  </div>
                  <TextareaField
                    label="Legenda"
                    optional
                    hint={`${formatNumber(caption.length)} de 2.200 caracteres`}
                    error={e.caption?.message}
                    {...form.register("caption")}
                  />
                  {!connected && !account.isPending && (
                    <p className="rounded-control bg-surface-raised p-3 text-label text-info">
                      Para publicar e disparar é preciso conectar o Instagram. O rascunho pode ser salvo agora.
                    </p>
                  )}
                </div>
              )}
              {contentError && (
                <p role="alert" className="mt-4 text-label text-danger">
                  {contentError}
                </p>
              )}
            </Tabs>
          </Card>

          <Card as="section" aria-labelledby="sec-2">
            <h2 id="sec-2" className="mb-4 font-heading text-section">
              <span className="mr-2 text-success tabular-nums">02</span>Pontos
            </h2>
            <div className="flex flex-col gap-6">
              <TextField label="Nome da campanha" error={e.title?.message} {...form.register("title")} />
              <TextareaField label="Descrição" optional error={e.description?.message} {...form.register("description")} />
              <TextareaField
                label="Instruções para os promoters"
                optional
                hint="Aparecem para os promoters na página da campanha."
                error={e.instructions?.message}
                {...form.register("instructions")}
              />
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="min-w-0">
                  <CheckboxField label="Pontuar comentário" {...form.register("commentOn")} />
                  <TextField
                    label="Pontos por comentário"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={100000}
                    disabled={!w.commentOn}
                    error={e.commentPoints?.message ?? e.commentOn?.message}
                    {...form.register("commentPoints")}
                  />
                </div>
                <div className="min-w-0">
                  <CheckboxField label="Pontuar menção em story" {...form.register("storyOn")} />
                  <TextField
                    label="Pontos por menção em story"
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={100000}
                    disabled={!w.storyOn}
                    error={e.storyPoints?.message}
                    {...form.register("storyPoints")}
                  />
                </div>
              </div>
              <TextField
                label="Menções em story pontuadas por pessoa"
                type="number"
                inputMode="numeric"
                min={1}
                max={10}
                disabled={!w.storyOn}
                hint="Até 1 comentário pontuado por pessoa nesta campanha. Repetições aparecem como Duplicado e valem zero."
                error={e.maxStory?.message}
                className="max-w-xs"
                {...form.register("maxStory")}
              />
            </div>
          </Card>

          <Card as="section" aria-labelledby="sec-3">
            <h2 id="sec-3" className="mb-1 font-heading text-section">
              <span className="mr-2 text-success tabular-nums">03</span>Período e envio
            </h2>
            <p className="mb-4 text-label text-ink-secondary">Horário de Brasília.</p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <TextField
                label="Início"
                optional
                type="datetime-local"
                hint="Em branco: começa ao disparar."
                error={e.startsAt?.message}
                {...form.register("startsAt")}
              />
              <TextField
                label="Término"
                optional
                type="datetime-local"
                hint="Em branco: sem data de término."
                error={e.endsAt?.message}
                {...form.register("endsAt")}
              />
            </div>
          </Card>

          <div className="xl:hidden">
            <Card as="section" aria-labelledby="sum-m">
              <h2 id="sum-m" className="mb-4 font-heading text-section">
                Resumo
              </h2>
              {summary}
            </Card>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <Button type="submit" variant="secondary" loading={createMut.isPending && !review} className="sm:w-auto">
              {createMut.isPending && !review ? "Salvando…" : "Salvar rascunho"}
            </Button>
            <Button
              onClick={form.handleSubmit(
                () => {
                  setFormError(null);
                  if (checkContent()) {
                    setReviewError(null);
                    setReview(true);
                  }
                },
                () => checkContent(),
              )}
            >
              Revisar campanha
            </Button>
          </div>
        </form>

        <aside className="hidden xl:block">
          <div className="sticky top-24 rounded-card border border-line-subtle bg-surface p-6">
            <h2 className="mb-4 font-heading text-section">Resumo</h2>
            {summary}
          </div>
        </aside>
      </div>

      <Dialog
        open={review}
        onClose={() => !busy && setReview(false)}
        size="sm"
        title="Revisar campanha"
        description={createdId ? "O rascunho foi criado. Falta apenas o disparo." : undefined}
        footer={
          <>
            <Button variant="secondary" onClick={() => setReview(false)} disabled={busy}>
              {createdId ? "Fechar" : "Voltar e editar"}
            </Button>
            <Button loading={busy} disabled={!connected} onClick={confirmDispatch} data-autofocus="">
              {busy
                ? sourceLabelPublish && !createdId
                  ? "Publicando e disparando…"
                  : "Disparando…"
                : createdId
                  ? "Tentar disparo novamente"
                  : sourceLabelPublish
                    ? "Publicar e disparar"
                    : "Disparar campanha"}
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          {source === "existing" && media && <RemoteImage src={media.thumbnail_url ?? media.media_url} ratio="aspect-[4/3]" className="max-w-56" />}
          {source === "publish" && upload.preview && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={upload.preview} alt="Imagem que será publicada" className="aspect-[4/3] max-w-56 rounded-control object-cover" />
          )}
          {summary}
          <p className="text-label tabular-nums text-ink-secondary">
            {approved.isPending
              ? "Contando promoters aprovados…"
              : approved.isError
                ? "Não foi possível contar os promoters aprovados."
                : `Será disponibilizada para ${formatNumber(approved.data?.total ?? 0)} ${(approved.data?.total ?? 0) === 1 ? "promoter aprovado" : "promoters aprovados"}. Não há envio de DM, WhatsApp ou e-mail.`}
          </p>
          {sourceLabelPublish && (
            <p className="rounded-control border border-warning bg-surface-raised p-3 text-label text-warning">
              Esta ação publica a imagem no seu Instagram. Publicar é um efeito externo e não pode ser desfeito por aqui.
            </p>
          )}
          {!connected && <p className="text-label text-info">Conecte o Instagram para disparar. O rascunho pode ser salvo sem conexão.</p>}
          <FormError message={reviewError} />
          {busy && (
            <p role="status" className="text-label text-ink-secondary">
              {createMut.isPending ? "Criando a campanha…" : "Disparando para a equipe…"}
            </p>
          )}
        </div>
      </Dialog>
    </>
  );
}
