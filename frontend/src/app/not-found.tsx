import { SearchX } from "lucide-react";
import { ButtonLink } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/feedback";

export default function NotFound() {
  return (
    <main id="conteudo" className="mx-auto flex min-h-dvh max-w-auth items-center px-4">
      <EmptyState
        icon={SearchX}
        title="Página não encontrada"
        description="O endereço que você abriu não existe ou foi movido."
        action={<ButtonLink href="/">Ir para o início</ButtonLink>}
      />
    </main>
  );
}
