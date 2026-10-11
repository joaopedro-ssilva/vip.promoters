import { ClipboardList, Gift, Megaphone, Ticket, Trophy, UsersRound, UserRound, Wallet } from "lucide-react";
import { ButtonLink } from "@/components/ui/button";
import { Perforated } from "@/components/ui/misc";

const STEPS = [
  {
    n: "01",
    color: "text-accent",
    title: "Conecte e convide",
    text: "O gestor conecta a conta do Instagram e compartilha o código da equipe. O promoter entra por esse código.",
  },
  {
    n: "02",
    color: "text-accent-secondary",
    title: "Publique e participe",
    text: "A campanha parte de um post. As ações de participação acontecem no próprio Instagram.",
  },
  {
    n: "03",
    color: "text-info",
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

export default function LandingPage() {
  return (
    <>
      <section className="mx-auto grid w-full max-w-site grid-cols-1 gap-8 px-4 py-12 md:px-6 lg:grid-cols-12 lg:gap-12 lg:px-8 lg:py-20">
        <div className="min-w-0 lg:col-span-7">
          <p className="mb-4 text-caption uppercase tracking-[0.08em] text-accent-secondary">Divulgação que vira benefício</p>
          <h1 className="font-heading text-hero font-bold lg:text-[4rem] xl:text-[5rem]">
            <span className="block">Sua equipe divulga.</span> <span className="block">A participação</span> <span className="block">vira recompensa.</span>
          </h1>
          <p className="mt-6 max-w-[38ch] text-lead text-ink-secondary">
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
            className="w-full max-w-[400px] rounded-panel border border-line bg-surface p-6 lg:ml-auto"
          >
            <div className="flex items-center justify-between gap-2">
              <p aria-hidden="true" className="flex items-baseline gap-2">
                <span className="font-heading text-[1.5rem] font-bold leading-none tracking-[0.01em]">VIP</span>
                <span className="text-label font-bold">Promoters</span>
              </p>
              <span className="rounded-pill border border-line bg-surface-raised px-2 py-1 text-caption uppercase tracking-[0.08em] text-ink-secondary">
                Exemplo
              </span>
            </div>
            <div className="mt-4 rounded-control bg-accent p-4 text-on-accent">
              <p className="text-label">Seu saldo</p>
              <p className="font-sans text-balance font-extrabold tabular-nums tracking-[-0.02em]">350 pontos</p>
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
            <div className="mt-6 flex items-start gap-2 rounded-control bg-surface-raised p-3 text-label">
              <Ticket aria-hidden="true" strokeWidth={1.75} className="mt-0.5 size-5 shrink-0 text-accent" />
              <div className="min-w-0">
                <p className="text-caption text-ink-muted">Próximo benefício</p>
                <p className="tabular-nums text-ink">Entrada VIP · 300 pontos</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section aria-labelledby="como-funciona" className="border-t border-line-subtle">
        <div className="mx-auto w-full max-w-site px-4 py-12 md:px-6 lg:px-8 lg:py-20">
          <h2 id="como-funciona" className="font-heading text-page lg:text-page-wide">
            Como funciona
          </h2>
          <ol className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
            {STEPS.map((s) => (
              <li key={s.n} className="min-w-0 rounded-card border border-line-subtle bg-surface p-6">
                <p className={`font-sans text-page font-extrabold tracking-[-0.02em] tabular-nums ${s.color}`}>{s.n}</p>
                <h3 className="mt-3 font-heading text-section">{s.title}</h3>
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
              <div key={col.title} className="min-w-0 rounded-card border border-line-subtle bg-surface p-6">
                <h3 className="font-heading text-section">{col.title}</h3>
                <ul className="mt-4 flex flex-col gap-4">
                  {col.items.map(({ icon: Icon, text }) => (
                    <li key={text} className="flex items-start gap-3 text-body text-ink-secondary">
                      <Icon aria-hidden="true" strokeWidth={1.75} className="mt-1 size-5 shrink-0 text-accent" />
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
        <div className="flex flex-col items-start gap-4 rounded-panel bg-surface-raised p-6 md:flex-row md:items-center md:justify-between md:p-8">
          <h2 className="font-heading text-section lg:text-page">Sua próxima campanha começa aqui.</h2>
          <ButtonLink href="/cadastro" size="lg">
            Criar conta
          </ButtonLink>
        </div>
      </section>

    </>
  );
}
