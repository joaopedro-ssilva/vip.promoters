"use client";

import { CircleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/feedback";

export default function ErrorPage({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="conteudo" className="mx-auto flex min-h-dvh max-w-auth items-center px-4">
      <EmptyState
        icon={CircleAlert}
        title="Algo deu errado"
        description="Não foi possível exibir esta página agora. Seus dados foram mantidos."
        action={<Button onClick={reset}>Tentar novamente</Button>}
      />
    </main>
  );
}
