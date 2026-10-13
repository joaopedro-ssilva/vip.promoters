import type { ReactNode } from "react";

/** Moldura das páginas legais: leitura longa, sólida, títulos em Syne. */
export function LegalPage({ title, updated, children }: { title: string; updated: string; children: ReactNode }) {
  return (
    <article className="mx-auto w-full max-w-reading px-4 py-10 md:py-16">
      <p className="rotulo">Documento legal</p>
      <h1 className="display mt-2 text-page font-bold text-ink-strong">{title}</h1>
      <p className="mt-2 text-caption text-ink-muted">Em vigor desde {updated}</p>
      <div className="solido mt-8 flex flex-col gap-8 rounded-card p-6 text-body text-ink-secondary md:p-10 [&_a]:text-success [&_a]:underline [&_h2]:mb-3 [&_h2]:text-section [&_h2]:font-semibold [&_h2]:text-ink-strong [&_li]:mt-1 [&_strong]:text-ink [&_ul]:list-disc [&_ul]:pl-5">
        {children}
      </div>
    </article>
  );
}
