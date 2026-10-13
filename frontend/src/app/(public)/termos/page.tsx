import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/layout/legal-page";
import { LEGAL } from "@/lib/legal";

export const metadata: Metadata = { title: "Termos de Uso" };

export default function TermsPage() {
  return (
    <LegalPage title="Termos de Uso" updated={LEGAL.effectiveDate}>
      <section>
        <p>
          Estes termos regem o uso do VIP Promoters, operado por <strong>{LEGAL.company}</strong>, CNPJ {LEGAL.cnpj}. Ao
          criar uma conta, você concorda com eles e com a <Link href="/privacidade">Política de Privacidade</Link>.
        </p>
      </section>

      <section>
        <h2>1. O que o serviço faz</h2>
        <p>
          O VIP Promoters ajuda equipes a organizar a divulgação no Instagram: o gestor cria campanhas a partir dos posts
          dele, o app identifica quem comentou ou marcou a conta em um story e atribui pontos, que os promoters trocam por
          recompensas oferecidas pelo próprio gestor.
        </p>
      </section>

      <section>
        <h2>2. Contas</h2>
        <ul>
          <li>Você precisa ter 18 anos ou mais e informar dados verdadeiros.</li>
          <li>A senha é pessoal. Você responde pelo que for feito com a sua conta.</li>
          <li>
            O promoter deve informar o próprio @. Usar o @ de outra pessoa é proibido; o dono real pode reivindicá-lo
            provando a posse pelo Instagram.
          </li>
        </ul>
      </section>

      <section>
        <h2>3. Instagram</h2>
        <p>
          O gestor precisa de uma conta profissional do Instagram e autoriza o app pelo login oficial da Meta. O uso
          também está sujeito aos termos e às políticas do Instagram. O app depende da API da Meta: se a Meta mudar,
          limitar ou suspender o acesso, funções podem parar sem aviso prévio.
        </p>
      </section>

      <section>
        <h2>4. Pontos e recompensas</h2>
        <ul>
          <li>Pontos não são dinheiro, não têm valor fora da equipe que os concedeu e não podem ser vendidos nem transferidos.</li>
          <li>
            As recompensas são oferecidas e entregues pelo <strong>gestor</strong> de cada equipe. O VIP Promoters não
            fornece, paga nem garante recompensas.
          </li>
          <li>O gestor pode ajustar pontos e cancelar resgates, com estorno dos pontos, dentro do próprio app.</li>
        </ul>
      </section>

      <section>
        <h2>5. O que não é permitido</h2>
        <ul>
          <li>Usar o @ de outra pessoa, contas falsas ou automação para gerar comentários e menções.</li>
          <li>Tentar acessar dados de outra equipe ou contornar limites e medidas de segurança.</li>
          <li>Usar o serviço para spam, assédio ou qualquer conteúdo ilegal.</li>
        </ul>
        <p className="mt-3">Podemos suspender contas que violem estes termos.</p>
      </section>

      <section>
        <h2>6. Disponibilidade e responsabilidade</h2>
        <p>
          Trabalhamos para manter o serviço no ar, mas ele é fornecido como está, sem garantia de funcionamento
          ininterrupto. Não respondemos por decisões do gestor sobre pontos e recompensas, nem por indisponibilidade da
          API da Meta.
        </p>
      </section>

      <section>
        <h2>7. Encerramento</h2>
        <p>
          Você pode excluir sua conta a qualquer momento, no próprio app. Gestor que exclui a conta exclui também a
          organização, as campanhas e a lojinha dela.
        </p>
      </section>

      <section>
        <h2>8. Lei e foro</h2>
        <p>
          Aplica-se a lei brasileira. Fica eleito o foro de {LEGAL.city}, ressalvado o direito do consumidor de usar o foro
          do próprio domicílio. Contato: <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
      </section>
    </LegalPage>
  );
}
