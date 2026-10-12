import { ClipboardList, Gift, Megaphone, Ticket, Trophy, UsersRound, UserRound, Wallet } from "lucide-react";
import { ButtonLink } from "@/components/ui/button";
import { Perforated } from "@/components/ui/misc";

const STEPS = [
  {
    n: "01",
    color: "text-success",
    title: "Conecte e convide",
    text: "O gestor conecta a conta do Instagram e compartilha o código da equipe. O promoter entra por esse código.",
  },
  {
    n: "02",
    color: "text-violet",
    title: "Publique e participe",
    text: "A campanha parte de um post. As ações de participação acontecem no próprio Instagram.",
  },
  {
    n: "03",
    color: "text-warning",
    title: "Confira e recompense",
    text: "Interações verificadas viram pontos, e os pontos podem ser trocados por benefícios na lojinha.",
  },
];

const FOR_MANAGERS = [
  { icon: Megaphone, text: "Controle de campanhas criadas a partir dos seus posts." },
  { icon: UsersRound, text: "Equipe com aprovação de promoters e ranking de participação." },
  { icon: Gift, text: "Lojinha de recompensas e fila de resgates para conferir e entregar." },
];

const FOR_PROMOTERS = [
  { icon: ClipboardList, text: "Instruções claras de como participar de cada campanha." },
  { icon: Wallet, text: "Saldo de pontos e extrato sempre à vista." },
  { icon: Trophy, text: "Benefícios para trocar pelos pontos que você ganhou." },
];

export default async function LandingPage({ searchParams }: { searchParams: Promise<{ conta?: string }> }) {
  const { conta } = await searchParams;
  return (
    <>
      {conta === "excluida" && (
        <p role="status" className="mx-auto mt-6 w-[calc(100%-2rem)] max-w-site rounded-control border border-accent-border bg-accent-soft px-4 py-3 text-label text-success">
          Sua conta foi excluída, junto com os seus dados pessoais.
        </p>
      )}
      <section className="mx-auto grid w-full max-w-site grid-cols-1 gap-8 px-4 py-12 md:px-6 lg:grid-cols-12 lg:gap-12 lg:px-8 lg:py-20">
        <div className="min-w-0 lg:col-span-7">
          <p className="site-sobrancelha mb-5 flex items-center gap-3 text-violet"><span aria-hidden="true" className="h-px w-8 bg-current" />Divulgação que vira benefício</p>
          <h1 className="site-titulo-heroi text-ink-strong">
            <span className="block">Sua equipe divulga.</span> <span className="block">A participação</span>{" "}
            <em className="block italic text-success">vira recompensa.</em>
          </h1>
          <p className="mt-7 max-w-[38ch] text-lead text-ink-secondary">
            Organize campanhas, acompanhe participações e recompense seus promoters.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/cadastro?papel=gestor" size="lg">
              Sou gestor
            </ButtonLink>
            <ButtonLink href="/cadastro?papel=promoter" variant="secondary" size="lg">
              Sou promoter
            </ButtonLink>
          </div>
        </div>

        <div className="min-w-0 lg:col-span-5">
          <div
            role="group"
            aria-label="Exemplo ilustrativo de saldo"
            className="vidro w-full max-w-[25rem] rounded-card p-6 lg:ml-auto"
          >
            <div className="flex items-center justify-between gap-2">
              <p aria-hidden="true" className="display text-brand font-extrabold leading-none tracking-[-0.03em] text-ink-strong">
                VIP<span className="ml-1.5 font-bold text-ink-secondary">Promoters</span>
              </p>
              <span className="rotulo rounded-pill border border-line-subtle bg-surface-raised px-2.5 py-1">
                Exemplo
              </span>
            </div>
            <div className="mt-5">
              <p className="rotulo">Seu saldo</p>
              <p className="cifra mt-2 text-balance text-success">
                350 <span className="text-section font-semibold text-ink-secondary">pontos</span>
              </p>
              <div className="trilho mt-4 h-2 overflow-hidden rounded-pill">
                <div className="preenchimento-lima h-full w-[86%] rounded-pill" />
              </div>
            </div>
            <Perforated className="my-6" />
            <ul className="flex flex-col gap-3 text-label text-ink">
              <li className="flex items-start gap-2">
                <UserRound aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-5 shrink-0 text-success" />
                <span className="min-w-0 tabular-nums">Comentário verificado · +10 pontos</span>
              </li>
              <li className="flex items-start gap-2">
                <UserRound aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-5 shrink-0 text-success" />
                <span className="min-w-0 tabular-nums">Menção verificada · +25 pontos</span>
              </li>
            </ul>
            <div className="mt-6 flex items-start gap-2 rounded-control border border-violet-border bg-violet-soft p-3 text-label">
              <Ticket aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-5 shrink-0 text-violet" />
              <div className="min-w-0">
                <p className="rotulo">Próximo benefício</p>
                <p className="tabular-nums text-ink">Entrada VIP · 300 pontos</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="como-funciona" className="border-t border-line-subtle">
        <div className="mx-auto w-full max-w-site px-4 py-12 md:px-6 lg:px-8 lg:py-20">
          <h2 id="como-funciona" className="site-titulo text-ink-strong">
            Como funciona
          </h2>
          <ol className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
            {STEPS.map((s) => (
              <li key={s.n} className="solido min-w-0 rounded-card p-6">
                <p className={`cifra text-page ${s.color}`}>{s.n}</p>
                <h3 className="display mt-4 text-section font-bold text-ink-strong">{s.title}</h3>
                <p className="mt-2 text-body text-ink-secondary">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section aria-labelledby="beneficios" className="border-t border-line-subtle">
        <div className="mx-auto w-full max-w-site px-4 py-12 md:px-6 lg:px-8 lg:py-20">
          <h2 id="beneficios" className="sr-only">
            Benefícios
          </h2>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {[
              { title: "Para quem organiza", items: FOR_MANAGERS },
              { title: "Para quem divulga", items: FOR_PROMOTERS },
            ].map((col) => (
              <div key={col.title} className="solido min-w-0 rounded-card p-6">
                <h3 className="display text-section font-bold text-ink-strong">{col.title}</h3>
                <ul className="mt-4 flex flex-col gap-4">
                  {col.items.map(({ icon: Icon, text }) => (
                    <li key={text} className="flex items-start gap-3 text-body text-ink-secondary">
                      <Icon aria-hidden="true" strokeWidth={1.75} className="mt-1 size-5 shrink-0 text-success" />
                      <span className="min-w-0">{text}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto w-full max-w-site px-4 pb-12 md:px-6 lg:px-8 lg:pb-20">
        <div className="vidro flex flex-col items-start gap-4 rounded-card p-6 md:flex-row md:items-center md:justify-between md:p-10">
          <h2 className="site-titulo text-ink-strong">Sua próxima campanha <em className="italic text-success">começa aqui.</em></h2>
          <ButtonLink href="/cadastro" size="lg">
            Criar conta
          </ButtonLink>
        </div>
      </section>

    </>
  );
}
