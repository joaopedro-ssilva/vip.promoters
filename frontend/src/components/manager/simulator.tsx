"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FlaskConical } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FormError, SelectField, TextField } from "@/components/ui/fields";
import { Card } from "@/components/ui/misc";
import { useToast } from "@/components/ui/toast";
import { errorMessage } from "@/lib/api/client";
import { devApi, teamApi } from "@/lib/api/manager";
import { keys } from "@/lib/queries";
import { normalizeIgUsername } from "@/lib/validation";

const FREE = "__free__";

/** Dev simulator (only rendered in mock mode on an active campaign). */
export function Simulator({ campaignId }: { campaignId: string }) {
  const qc = useQueryClient();
  const toast = useToast();
  const members = useQuery({
    queryKey: [...keys.members, "approved-all"],
    queryFn: () => teamApi.members({ status: "approved", limit: 100 }),
    staleTime: 60_000,
  });
  const [pick, setPick] = useState<string>("");
  const [free, setFree] = useState("");
  const [text, setText] = useState("Bora! 🔥");
  const [error, setError] = useState<string | null>(null);

  // promoters still proving a disputed @ have none to simulate with
  const items = (members.data?.items ?? []).filter((m) => m.promoter.instagram_username);
  const useFree = pick === FREE || (items.length === 0 && !members.isPending);
  const username = normalizeIgUsername(useFree ? free : pick || items[0]?.promoter.instagram_username || "");

  const refresh = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: keys.campaign(campaignId) }),
      qc.invalidateQueries({ queryKey: keys.dashboard }),
      qc.invalidateQueries({ queryKey: keys.members }),
    ]);
  };

  const comment = useMutation({
    mutationFn: () => devApi.simulateComment({ campaign_id: campaignId, username, text: text.trim() }),
    onSuccess: async ({ interaction }) => {
      await refresh();
      toast.success(
        interaction.status === "awarded" ? `Comentário simulado: +${interaction.points_awarded} pontos.` : `Comentário simulado (${interaction.status}).`,
      );
    },
    onError: (e) => setError(errorMessage(e)),
  });
  const story = useMutation({
    mutationFn: () => devApi.simulateStory({ username }),
    onSuccess: async ({ interaction }) => {
      await refresh();
      toast.success(
        interaction.status === "awarded" ? `Menção simulada: +${interaction.points_awarded} pontos.` : `Menção simulada (${interaction.status}).`,
      );
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const disabled = !username;

  return (
    <Card as="section" aria-labelledby="sim-title">
      <h2 id="sim-title" className="mb-1 flex items-center gap-2 font-heading text-section">
        <FlaskConical aria-hidden="true" strokeWidth={1.75} className="size-5 text-accent-secondary" />
        Simulador
      </h2>
      <p className="mb-4 text-label text-ink-secondary">
        Disponível só no modo demonstração. Gera comentários e menções de teste, como se viessem do Instagram.
      </p>
      <div className="flex flex-col gap-4">
        <FormError message={error} />
        <SelectField
          label="Quem participa"
          value={useFree ? FREE : pick || items[0]?.promoter.instagram_username || ""}
          onChange={(e) => setPick(e.target.value)}
          aria-busy={members.isPending}
        >
          {items.map((m) => (
            <option key={m.id} value={m.promoter.instagram_username ?? ""}>
              {m.promoter.name} (@{m.promoter.instagram_username})
            </option>
          ))}
          <option value={FREE}>Outro @ (digitar)</option>
        </SelectField>
        {useFree && (
          <TextField label="@ do Instagram" value={free} onChange={(e) => setFree(e.target.value)} autoCapitalize="none" spellCheck={false} />
        )}
        <TextField label="Texto do comentário" value={text} onChange={(e) => setText(e.target.value)} maxLength={300} />
        <div className="flex flex-col gap-3 sm:flex-row">
          <Button
            variant="secondary"
            disabled={disabled || !text.trim()}
            loading={comment.isPending}
            onClick={() => {
              setError(null);
              comment.mutate();
            }}
          >
            {comment.isPending ? "Simulando…" : "Simular comentário"}
          </Button>
          <Button
            variant="secondary"
            disabled={disabled}
            loading={story.isPending}
            onClick={() => {
              setError(null);
              story.mutate();
            }}
          >
            {story.isPending ? "Simulando…" : "Simular menção em story"}
          </Button>
        </div>
      </div>
    </Card>
  );
}
