"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Gift, ImagePlus, Pencil, Plus, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ConfirmDialog, Dialog, useDialogDirty } from "@/components/ui/dialog";
import { EmptyState, ErrorState, LoadingRegion, Skeleton } from "@/components/ui/feedback";
import { CheckboxField, FormError, SelectField, TextareaField, TextField } from "@/components/ui/fields";
import { Card, DialogActions, PageHeader, PointsChip } from "@/components/ui/misc";
import { RemoteImage } from "@/components/ui/remote-image";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { rewardsApi, uploadsApi, type RewardInput } from "@/lib/api/manager";
import type { Reward } from "@/lib/api/types";
import { formatNumber, formatPoints } from "@/lib/format";
import { applyServerError } from "@/lib/form";
import { keys } from "@/lib/queries";
import { parseIntStrict } from "@/lib/validation";

type View = "available" | "soldout" | "hidden" | "all";

function stockLabel(r: Reward) {
  if (r.stock === null) return "Estoque ilimitado";
  if (r.stock === 0) return "Esgotado";
  return `${formatNumber(r.stock)} em estoque`;
}

export function RewardsPage() {
  const qc = useQueryClient();
  const toast = useToast();
  const [view, setView] = useState<View>("available");
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState<Reward | "new" | null>(null);
  const [deleting, setDeleting] = useState<Reward | null>(null);
  const [delError, setDelError] = useState<string | null>(null);

  const q = useQuery({
    queryKey: keys.rewards,
    queryFn: () => rewardsApi.list({ include_inactive: true, limit: 100 }),
    staleTime: 30_000,
  });

  const remove = useMutation({
    mutationFn: (r: Reward) => rewardsApi.remove(r.id),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: keys.rewards });
      setDeleting(null);
      toast.success("Recompensa removida da vitrine.", "Se já havia resgates, ela foi arquivada e os comprovantes foram preservados.");
    },
    onError: (e) => setDelError(errorMessage(e)),
  });

  const all = q.data?.items ?? [];
  const term = search.trim().toLowerCase();
  const items = all
    .filter((r) => {
      if (view === "available") return r.is_active && r.stock !== 0;
      if (view === "soldout") return r.stock === 0;
      if (view === "hidden") return !r.is_active;
      return true;
    })
    .filter((r) => !term || r.name.toLowerCase().includes(term));

  return (
    <>
      <PageHeader
        title="Lojinha"
        actions={
          <Button icon={Plus} onClick={() => setEditing("new")}>
            Nova recompensa
          </Button>
        }
      />
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TextField label="Buscar recompensa" type="search" value={search} onChange={(e) => setSearch(e.target.value)} />
        <SelectField label="Visualização" value={view} onChange={(e) => setView(e.target.value as View)}>
          <option value="available">Disponíveis</option>
          <option value="soldout">Esgotadas</option>
          <option value="hidden">Ocultas da vitrine</option>
          <option value="all">Todas</option>
        </SelectField>
      </div>

      {q.isPending ? (
        <LoadingRegion className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-72" />
          ))}
        </LoadingRegion>
      ) : q.isError ? (
        <Card>
          <ErrorState onRetry={() => q.refetch()} retrying={q.isFetching} />
        </Card>
      ) : all.length === 0 ? (
        <Card>
          <EmptyState
            icon={Gift}
            title="Crie sua primeira recompensa"
            description="Defina benefícios que os promoters podem trocar pelos pontos."
            action={
              <Button icon={Plus} onClick={() => setEditing("new")}>
                Nova recompensa
              </Button>
            }
          />
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState title="Nenhuma recompensa encontrada" description="Tente outro filtro ou outro nome." />
        </Card>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {items.map((r) => (
            <li key={r.id} className="flex min-w-0 flex-col gap-3 rounded-card border border-line-subtle bg-surface p-4">
              <RemoteImage src={r.image_url} fallbackLabel="Sem imagem" fallbackIcon={Gift} />
              <div className="flex flex-wrap items-center gap-2">
                {r.stock === 0 && <StatusBadge kind="sold_out" />}
                {!r.is_active && <span className="rounded-pill border border-line bg-surface-raised px-2 py-1 text-caption text-ink-secondary">Oculta da vitrine</span>}
              </div>
              <h3 className="font-sans text-body font-bold">{r.name}</h3>
              {r.description && <p className="line-clamp-3 text-label font-normal text-ink-secondary">{r.description}</p>}
              <div>
                <PointsChip>{formatPoints(r.cost_points)}</PointsChip>
              </div>
              <p className="text-caption text-ink-muted tabular-nums">
                {stockLabel(r)} · {formatNumber(r.redeemed_count)} {r.redeemed_count === 1 ? "resgate" : "resgates"}
                {r.max_per_promoter ? ` · máx. ${formatNumber(r.max_per_promoter)} por promoter` : ""}
              </p>
              <div className="mt-auto flex flex-wrap gap-2">
                <Button variant="secondary" size="sm" icon={Pencil} onClick={() => setEditing(r)}>
                  Editar<span className="sr-only">: {r.name}</span>
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={Trash2}
                  onClick={() => {
                    setDelError(null);
                    setDeleting(r);
                  }}
                >
                  {r.redeemed_count > 0 ? "Arquivar" : "Excluir"}
                  <span className="sr-only">: {r.name}</span>
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Dialog
        open={editing !== null}
        onClose={() => setEditing(null)}
        size="lg"
        title={editing === "new" ? "Nova recompensa" : "Editar recompensa"}
      >
        {editing !== null && <RewardForm reward={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
      </Dialog>

      <ConfirmDialog
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        onConfirm={() => deleting && remove.mutate(deleting)}
        title={deleting && deleting.redeemed_count > 0 ? "Arquivar recompensa" : "Excluir recompensa"}
        description={
          deleting
            ? deleting.redeemed_count > 0
              ? `“${deleting.name}” já tem resgates. Ela será arquivada: sai da vitrine e os comprovantes são preservados.`
              : `Excluir definitivamente “${deleting.name}”? Esta ação não pode ser desfeita. Se já houver histórico, ela será arquivada em vez de excluída.`
            : undefined
        }
        confirmLabel={deleting && deleting.redeemed_count > 0 ? "Arquivar recompensa" : "Excluir recompensa"}
        loadingLabel="Removendo…"
        variant="danger"
        loading={remove.isPending}
        error={delError}
      />
    </>
  );
}

/* ---------------- form ---------------- */

const optInt = (min: number, max: number, msg: string) =>
  z.string().refine((v) => {
    if (v.trim() === "") return true;
    const n = parseIntStrict(v);
    return Number.isInteger(n) && n >= min && n <= max;
  }, msg);

const schema = z.object({
  name: z.string().trim().min(2, "O nome precisa ter de 2 a 120 caracteres.").max(120, "O nome precisa ter de 2 a 120 caracteres."),
  description: z.string().max(1000, "Use no máximo 1000 caracteres."),
  cost: z.string().refine((v) => {
    const n = parseIntStrict(v);
    return Number.isInteger(n) && n >= 1 && n <= 1_000_000;
  }, "Informe um número inteiro de 1 a 1.000.000."),
  stock: optInt(0, 100000, "Informe um número inteiro de 0 a 100.000, ou deixe em branco para estoque ilimitado."),
  maxPer: optInt(1, 1000, "Informe um número inteiro de 1 a 1.000, ou deixe em branco."),
  active: z.boolean(),
});
type Values = z.infer<typeof schema>;

function RewardForm({ reward, onClose }: { reward: Reward | null; onClose: () => void }) {
  const qc = useQueryClient();
  const toast = useToast();
  const [formError, setFormError] = useState<string | null>(null);
  const [image, setImage] = useState<string | null>(reward?.image_url ?? null);
  const [imgDirty, setImgDirty] = useState(false);
  const [imgStatus, setImgStatus] = useState<{ state: "idle" | "uploading" | "error"; message?: string }>({ state: "idle" });
  const preview = useRef<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(
    () => () => {
      if (preview.current) URL.revokeObjectURL(preview.current);
    },
    [],
  );

  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: reward?.name ?? "",
      description: reward?.description ?? "",
      cost: reward ? String(reward.cost_points) : "",
      stock: reward?.stock != null ? String(reward.stock) : "",
      maxPer: reward?.max_per_promoter != null ? String(reward.max_per_promoter) : "",
      active: reward?.is_active ?? true,
    },
    mode: "onBlur",
  });
  const w = useWatch({ control: form.control });
  const e = form.formState.errors;
  useDialogDirty(form.formState.isDirty || imgDirty);

  const upload = useMutation({ mutationFn: uploadsApi.image });

  async function onFile(file: File | null) {
    if (!file) return;
    if (!["image/jpeg", "image/png"].includes(file.type)) {
      setImgStatus({ state: "error", message: "Use uma imagem JPEG ou PNG." });
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      setImgStatus({ state: "error", message: "A imagem pode ter no máximo 8 MB." });
      return;
    }
    setImgStatus({ state: "uploading" });
    try {
      const { url } = await upload.mutateAsync(file);
      if (preview.current) URL.revokeObjectURL(preview.current);
      preview.current = URL.createObjectURL(file);
      setPreviewUrl(preview.current);
      setImage(url);
      setImgDirty(true);
      setImgStatus({ state: "idle" });
    } catch (err) {
      setImgStatus({ state: "error", message: errorMessage(err, "Não foi possível enviar a imagem.") });
    }
  }

  const save = useMutation({
    mutationFn: (v: Values) => {
      const body: RewardInput = {
        name: v.name.trim(),
        description: v.description.trim() || null,
        image_url: image,
        cost_points: parseIntStrict(v.cost),
        stock: v.stock.trim() === "" ? null : parseIntStrict(v.stock),
        max_per_promoter: v.maxPer.trim() === "" ? null : parseIntStrict(v.maxPer),
        is_active: v.active,
      };
      return reward ? rewardsApi.update(reward.id, body) : rewardsApi.create(body);
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: keys.rewards });
      onClose();
      toast.success(reward ? "Recompensa atualizada." : "Recompensa criada.");
    },
    onError: (err) =>
      setFormError(
        applyServerError(err, form.setError, ["name", "description", "cost", "stock", "maxPer"], {
          cost_points: "cost",
          max_per_promoter: "maxPer",
        }),
      ),
  });

  const costNum = parseIntStrict(w.cost ?? "");
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
      <TextField label="Nome" data-autofocus="" error={e.name?.message} {...form.register("name")} />
      <TextareaField label="Descrição" optional error={e.description?.message} {...form.register("description")} />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TextField label="Custo em pontos" type="number" inputMode="numeric" min={1} error={e.cost?.message} {...form.register("cost")} />
        <TextField label="Estoque" optional type="number" inputMode="numeric" min={0} hint="Em branco: ilimitado." error={e.stock?.message} {...form.register("stock")} />
        <TextField label="Máx. por promoter" optional type="number" inputMode="numeric" min={1} error={e.maxPer?.message} {...form.register("maxPer")} />
      </div>
      <CheckboxField label="Visível na vitrine" {...form.register("active")} />

      <div>
        <p className="mb-2 text-label">
          Imagem <span className="font-medium text-ink-muted">(opcional)</span>
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="w-full sm:w-40 sm:shrink-0">
            {previewUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={previewUrl} alt="Pré-visualização da imagem selecionada" className="aspect-[4/3] w-full rounded-control object-cover" />
            ) : (
              <RemoteImage src={image} fallbackLabel="Sem imagem" fallbackIcon={Gift} />
            )}
          </div>
          <div className="flex flex-wrap gap-2">
            <label className="inline-flex min-h-11 cursor-pointer items-center gap-2 rounded-control border border-line bg-surface px-3 text-label hover:bg-surface-hover has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-[3px] has-[:focus-visible]:outline-focus">
              <ImagePlus aria-hidden="true" strokeWidth={1.75} className="size-4" />
              {imgStatus.state === "uploading" ? "Enviando…" : image ? "Trocar imagem" : "Escolher imagem"}
              <input
                type="file"
                accept="image/jpeg,image/png"
                className="sr-only"
                disabled={imgStatus.state === "uploading"}
                onChange={(ev) => {
                  void onFile(ev.target.files?.[0] ?? null);
                  ev.target.value = "";
                }}
              />
            </label>
            {image && (
              <Button
                variant="ghost"
                size="sm"
                icon={X}
                onClick={() => {
                  setImage(null);
                  setPreviewUrl(null);
                  setImgDirty(true);
                }}
              >
                Remover imagem
              </Button>
            )}
          </div>
        </div>
        {imgStatus.state === "error" && (
          <p role="alert" className="mt-2 text-label text-danger">
            {imgStatus.message}
          </p>
        )}
      </div>

      <div className="rounded-control bg-surface-raised p-3">
        <p className="text-caption text-ink-muted">Prévia</p>
        <p className="text-body font-bold [overflow-wrap:anywhere]">{w.name?.trim() || "Nome da recompensa"}</p>
        <p className="text-label tabular-nums text-accent">{Number.isInteger(costNum) ? formatPoints(costNum) : "— pontos"}</p>
      </div>

      <DialogActions>
        <Button variant="secondary" onClick={onClose}>
          Cancelar
        </Button>
        <Button type="submit" loading={save.isPending} disabled={imgStatus.state === "uploading"}>
          {save.isPending ? "Salvando…" : "Salvar recompensa"}
        </Button>
      </DialogActions>
    </form>
  );
}
