import { Brand } from "@/components/layout/parts";
import { ButtonLink } from "@/components/ui/button";
import { PublicHeader } from "@/components/layout/public-header";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    // Entrada e landing são sempre escuras (como no Camarim): `data-theme="dark"`
    // no wrapper vale mesmo com o tema claro escolhido dentro do app.
    <div data-theme="dark" className="palco flex min-h-dvh flex-col text-ink">
      <PublicHeader />
      <main id="conteudo" tabIndex={-1} className="flex-1 outline-none">
        {children}
      </main>
      <footer className="border-t border-line-subtle bg-surface-sunken">
        <div className="mx-auto flex w-full max-w-site flex-wrap items-center justify-between gap-3 px-4 py-6 md:px-6 lg:px-8">
          <Brand />
          <nav aria-label="Rodapé" className="flex flex-wrap items-center gap-1">
            <ButtonLink href="/privacidade" variant="ghost" size="sm">
              Privacidade
            </ButtonLink>
            <ButtonLink href="/termos" variant="ghost" size="sm">
              Termos
            </ButtonLink>
            <ButtonLink href="/entrar" variant="ghost" size="sm">
              Entrar
            </ButtonLink>
          </nav>
        </div>
      </footer>
    </div>
  );
}
