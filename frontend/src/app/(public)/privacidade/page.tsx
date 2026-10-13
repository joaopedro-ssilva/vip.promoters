import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage } from "@/components/layout/legal-page";
import { LEGAL, RETENTION } from "@/lib/legal";

export const metadata: Metadata = { title: "Política de Privacidade" };

export default function PrivacyPage() {
  return (
    <LegalPage title="Política de Privacidade" updated={LEGAL.effectiveDate}>
      <section>
        <p>
          Esta política explica quais dados o VIP Promoters trata, por que, por quanto tempo e como você exerce seus
          direitos, nos termos da Lei Geral de Proteção de Dados (Lei 13.709/2018, LGPD).
        </p>
      </section>

      <section>
        <h2>1. Quem somos</h2>
        <p>
          O VIP Promoters é operado por <strong>{LEGAL.company}</strong>, CNPJ {LEGAL.cnpj}. Encarregado de dados:{" "}
          {LEGAL.dpo}. Contato para privacidade: <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a>.
        </p>
        <p className="mt-3">
          Somos <strong>controladores</strong> dos dados da sua conta. Quanto às interações dos promoters com o Instagram
          de uma equipe, quem decide a campanha e a recompensa é o gestor dessa equipe; nós tratamos esses dados para
          prestar o serviço a ele.
        </p>
      </section>

      <section>
        <h2>2. Dados que tratamos</h2>
        <ul>
          <li>
            <strong>Conta</strong>: nome, e-mail e senha. A senha é guardada só como hash (Argon2id); ninguém, nem nós,
            consegue lê-la.
          </li>
          <li>
            <strong>Promoter</strong>: o @ do Instagram que você informa e, se você verificar, a confirmação de que ele é
            seu. Saldo de pontos, extrato e resgates em cada equipe.
          </li>
          <li>
            <strong>Gestor</strong>: nome da organização e, ao conectar o Instagram, o perfil profissional (nome, @, foto,
            número de seguidores), os posts e um token de acesso guardado cifrado.
          </li>
          <li>
            <strong>Interações nos posts do gestor</strong>: comentários (@ de quem comentou, identificador do Instagram e
            texto) e menções em story (@, identificador e o link temporário da mídia, que a Meta expira em cerca de 24
            horas).
          </li>
          <li>
            <strong>Registros técnicos</strong>: endereço IP e navegador usados para limitar tentativas de login e
            proteger contra abuso, e registros de erro sem conteúdo das mensagens.
          </li>
        </ul>
        <p className="mt-3">
          <strong>Não lemos suas mensagens diretas.</strong> Da caixa de mensagens do gestor, o app recebe só o aviso de
          menção em story; qualquer outro conteúdo é descartado antes de ser processado ou guardado.
        </p>
      </section>

      <section>
        <h2>3. Para que usamos e com qual base legal</h2>
        <ul>
          <li>Criar e manter sua conta, calcular pontos e registrar resgates: execução de contrato (art. 7º, V).</li>
          <li>
            Conectar o Instagram do gestor e ler comentários e menções dos posts dele: execução de contrato, com a
            autorização que o gestor dá na tela da Meta.
          </li>
          <li>Segurança, prevenção de fraude de identidade (@) e limite de tentativas: legítimo interesse (art. 7º, IX).</li>
          <li>Cumprir obrigações legais e atender autoridades: obrigação legal (art. 7º, II).</li>
        </ul>
        <p className="mt-3">Não vendemos dados, não usamos para publicidade e não traçamos perfil de ninguém.</p>
      </section>

      <section>
        <h2>4. Instagram e Meta</h2>
        <p>
          O gestor conecta a conta profissional pelo login oficial do Instagram e pode desconectar quando quiser, no app ou
          nas configurações do Instagram. Usamos as permissões <em>instagram_business_basic</em> (perfil e posts),{" "}
          <em>instagram_business_manage_comments</em> (ler comentários dos posts das campanhas),{" "}
          <em>instagram_business_manage_messages</em> (receber os avisos de menção em story) e{" "}
          <em>instagram_business_content_publish</em> (publicar um post quando o gestor pede). O uso segue os Termos da
          Plataforma da Meta.
        </p>
      </section>

      <section>
        <h2>5. Com quem compartilhamos</h2>
        <ul>
          <li>Meta Platforms, para as chamadas à API do Instagram que você ou o gestor autorizaram.</li>
          <li>Provedores de infraestrutura (hospedagem, banco de dados, envio de e-mail), sob contrato e só para operar o serviço.</li>
          <li>Autoridades, quando a lei exigir.</li>
        </ul>
        <p className="mt-3">
          Dentro do app, o gestor vê o nome, o @ e os pontos dos promoters da equipe dele. Uma equipe nunca vê dados de
          outra.
        </p>
      </section>

      <section>
        <h2>6. Por quanto tempo guardamos</h2>
        <ul>
          <li>Conta, saldo e extrato: enquanto a conta existir.</li>
          <li>
            Interações (comentários e menções): o texto, o @ e os identificadores são apagados{" "}
            {RETENTION.interactionsDays} dias depois do fim da campanha. Fica só o registro anônimo dos pontos.
          </li>
          <li>Notificações lidas: {RETENTION.notificationsDays} dias. Sessões expiradas são apagadas automaticamente.</li>
          <li>Pedidos de exclusão: guardamos só um código e um resumo cifrado (hash) que provam que o pedido foi atendido.</li>
        </ul>
      </section>

      <section id="exclusao">
        <h2>7. Seus direitos e como excluir seus dados</h2>
        <p>Você pode pedir acesso, correção, portabilidade e exclusão dos seus dados.</p>
        <ul>
          <li>
            <strong>Excluir a conta</strong>: em Configurações (gestor) ou Perfil (promoter), no botão &quot;Excluir minha
            conta&quot;. A exclusão é imediata.
          </li>
          <li>
            <strong>Pelo Instagram</strong>: ao remover o VIP Promoters em Configurações → Apps e sites do Instagram e
            pedir a exclusão, apagamos na hora a conexão e os dados obtidos por ela, e você recebe um código para
            consultar o pedido.
          </li>
          <li>
            <strong>Se você só comentou</strong> num post de uma equipe e não tem conta: escreva para{" "}
            <a href={`mailto:${LEGAL.contactEmail}`}>{LEGAL.contactEmail}</a> informando o seu @. Respondemos em até 15
            dias.
          </li>
        </ul>
      </section>

      <section>
        <h2>8. Segurança</h2>
        <p>
          Conexão sempre por HTTPS, senha com hash Argon2id, tokens do Instagram cifrados, sessão em cookie protegido e
          isolamento entre equipes em duas camadas (aplicação e banco de dados). Nenhum sistema é infalível; se houver um
          incidente que possa causar risco a você, avisaremos você e a ANPD.
        </p>
      </section>

      <section>
        <h2>9. Cookies</h2>
        <p>
          Usamos apenas cookies essenciais de sessão (sem eles não é possível entrar) e guardamos no seu navegador a
          preferência de tema e a equipe ativa. Não usamos cookies de publicidade nem de rastreamento.
        </p>
      </section>

      <section>
        <h2>10. Idade mínima</h2>
        <p>O serviço é destinado a maiores de 18 anos.</p>
      </section>

      <section>
        <h2>11. Mudanças nesta política</h2>
        <p>
          Avisaremos no app antes de mudanças relevantes. Veja também os <Link href="/termos">Termos de Uso</Link>.
        </p>
      </section>
    </LegalPage>
  );
}
