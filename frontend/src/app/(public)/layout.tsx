import { Brand } from "@/components/layout/parts";
import { ButtonLink } from "@/components/ui/button";
import { PublicHeader } from "@/components/layout/public-header";

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <PublicHeader />
      <main id="conteudo" tabIndex={-1} className="flex-1 outline-none">
        {children}
      </main>
      <footer className="border-t border-line-subtle bg-surface">
        <div className="mx-auto flex w-full max-w-site flex-wrap items-center justify-between gap-3 px-4 py-6 md:px-6 lg:px-8">
          <Brand />
          <ButtonLink href="/entrar" variant="ghost" size="sm">
            Entrar
          </ButtonLink>
        </div>
      </footer>
    </div>
  );
}
