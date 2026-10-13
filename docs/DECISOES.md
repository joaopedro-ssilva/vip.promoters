# Gargalos e dúvidas de solução

Registro do que ficou em aberto depois da rodada de segurança e LGPD (RLS, exclusão de conta e de
dados, retenção, verificação e disputa de @, rotação de chaves). Cada item diz **o que foi feito
hoje**, **qual é a dúvida** e **quem decide**.

---

## 1. Decisões de produto e negócio (quem decide: você)

### 1.1 Promoter que exclui a conta leva junto os resgates pendentes
**Hoje:** os resgates pendentes dele somem e o estoque da recompensa é devolvido. O gestor deixa de
ver aquele resgate (inclusive o código).
**Dúvida:** o gestor precisa de um registro anônimo ("resgate de promoter excluído") para fechar
contas com o fornecedor da recompensa? Se sim, a troca é anonimizar o resgate em vez de apagar.

### 1.2 Gestor que exclui a conta apaga a organização na hora
**Hoje:** exclusão imediata, sem carência e sem exportação. Os promoters perdem saldo e extrato
daquela equipe.
**Dúvida:** oferecer 30 dias para desfazer e um CSV antes de apagar? Para SaaS pago, a carência
evita suporte ("apaguei sem querer"), mas atrasa o cumprimento da LGPD e precisa de um job de
exclusão agendada.

### 1.3 Prazo de retenção de 365 dias
**Hoje:** `RETENTION_DAYS=365`. Depois disso, comentários e menções de campanhas encerradas ficam
anônimos (somem texto, @, id e link; ficam os pontos).
**Dúvida:** o prazo é razoável para o negócio (comparar campanhas de um ano para o outro) e para
a LGPD? Confirmar com advogado. O valor é configurável sem mexer em código.

### 1.4 Disputa de @: os pontos de quem perdeu o @
**Hoje:** quando o dono real prova a posse, o @ passa para ele e quem estava com o @ fica sem @,
com as equipes de volta para "pendente". **O saldo que ele já ganhou fica com ele.**
**Dúvida:** estornar automaticamente os pontos ganhos com o @ disputado? A favor: se era fraude,
os pontos eram do dono real. Contra: se a pessoa só digitou errado, o estorno pune quem participou
de verdade. Sugestão: deixar o gestor decidir com o "ajustar pontos" que já existe, e mostrar a
ele um aviso da disputa.

### 1.5 @ verificado por outra pessoa
**Hoje:** um @ já verificado não pode ser reivindicado no app; a mensagem manda falar com o
suporte.
**Dúvida:** qual é o processo do suporte? (Ex.: pedir que a pessoa comente um código novo pelo
Instagram e o suporte troca o dono à mão.) Sem processo definido, isto vira um beco sem saída.

### 1.6 Controlador ou operador dos dados dos promoters
**Hoje:** a Política de Privacidade diz que somos controladores da conta e que, nas interações de
uma equipe, quem decide é o gestor.
**Dúvida jurídica:** isso faz do gestor um controlador e do VIP Promoters um operador. Se for
assim, o contrato com o gestor (Termos) precisa de cláusulas de operador (art. 39 da LGPD) ou de
um acordo de tratamento de dados. Decidir com advogado antes de cobrar.

### 1.7 Planos e limites do SaaS
Sem isso não dá para fazer a cobrança: preço, período de teste, limite de campanhas ativas ou de
promoters por plano, e o que acontece quando o pagamento falha (bloquear, só leitura?).

---

## 2. Dúvidas técnicas que só a Meta responde (validar no modo de teste)

| # | Dúvida | Por que importa | Como o código está preparado |
|---|---|---|---|
| 2.1 | Qual chave assina os webhooks: a do app Meta ou a do "app do Instagram"? | Chave errada = todo webhook recusado com 403 | `META_WEBHOOK_SECRET` opcional sobrepõe `META_APP_SECRET` |
| 2.2 | O `from.id` do comentário é o mesmo id do `sender.id` da menção em story? | Casar por id é mais forte que casar por @ | O casamento principal é pelo @; o id é complemento |
| 2.3 | Comentários de quem **não** é testador chegam no modo de teste? | A verificação de @ por comentário depende disso | Provavelmente só depois do App Review (acesso avançado). Antes, só com contas testadoras |
| 2.4 | O webhook de comentários vem para **qualquer** post da conta, não só os de campanha? | A verificação de @ pede para comentar "em qualquer post" | O pipeline aceita o código em qualquer post |
| 2.5 | A menção em story exige "Permitir acesso às mensagens" no Instagram do gestor? | Sem isso, nenhuma menção chega | O onboarding do gestor ainda não avisa disso |
| 2.6 | Comentário apagado gera webhook? | Estorno automático quando o promoter apaga o comentário | Não implementado; sem webhook, exige comparar listas no polling (custo de API) |
| 2.7 | Limite de chamadas da Graph API por conta | O polling a cada 2 minutos por campanha ativa consome a cota | Polling é só reserva do webhook; dá para espaçar com `SYNC_INTERVAL_SECONDS` |

---

## 3. Gargalos técnicos (escala e operação)

### 3.1 O RLS protege as requisições autenticadas, não tudo
Rotas públicas (cadastro, convite), o worker e o pipeline de webhooks rodam em **modo sistema** de
propósito: eles atravessam organizações. Ali a proteção continua sendo só o `where`. É a mesma
escolha do Camarim e cobre a superfície onde o erro é mais provável (as telas logadas), mas não é
"o banco impede tudo".

### 3.2 Polling sequencial
O worker sincroniza até 200 campanhas por minuto, uma depois da outra. Com centenas de clientes e
campanhas ativas, a fila atrasa. Saídas: confiar mais no webhook e espaçar o polling, ou paralelizar
por conta do Instagram respeitando o limite de cada uma.

### 3.3 Uploads no disco do servidor
Imagens de recompensa e de posts publicados ficam no volume `uploads`. Isso impede rodar mais de
um servidor do backend e não entra no backup do banco. Mover para armazenamento de objetos (S3, R2)
antes de escalar.

### 3.4 Sem e-mail transacional
Sem e-mail não há recuperação de senha nem confirmação de e-mail. Todo esquecimento de senha vira
suporte manual, e o cadastro aceita e-mail de outra pessoa. É o maior gargalo operacional do
lançamento.

### 3.5 Custo do contexto de RLS
Cada requisição autenticada faz uma consulta a mais (as organizações do usuário), e cada transação
faz um `set_config`. É pouco, mas não foi medido sob carga.

### 3.6 O frontend não tem testes automatizados
Os fluxos de tela são verificados à mão (e por capturas de tela). Os fluxos novos (excluir conta,
verificação de @, disputa no cadastro) entram nessa mesma situação.

### 3.7 O Docker Compose novo não foi executado de ponta a ponta
O ambiente onde este trabalho foi feito não roda o daemon do Docker. O compose com o serviço
`migrate` foi validado com `docker compose config`, e o fluxo foi reproduzido à mão: preparar o
banco com o dono das tabelas e subir app e worker com o papel de aplicação. Rode
`docker compose up -d --build` na sua máquina antes do primeiro deploy.
