# VIP Promoters

Aplicativo web para gestão de divulgação no Instagram.

- O **gestor** conecta a conta profissional do Instagram, cria campanhas a partir de um post, dispara para a equipe, vê quem comentou ou marcou a conta em um story, aprova promoters e mantém uma lojinha de recompensas.
- O **promoter** entra na equipe com um código de convite, comenta no post ou marca a conta no story, ganha pontos e troca por recompensas.

Regra central: **no máximo 1 comentário pontuado por promoter em cada campanha**.

## Situação atual

| Item | Estado |
|---|---|
| Produto (gestor, promoter, pontos, lojinha) | Pronto e testado em modo simulado |
| Backend | 109 testes passando e lint limpo. Segurança de sessão, CSRF, webhooks e isolamento entre equipes sólidos (ver [Segurança](#segurança)) |
| Visual | Design system "Noite / Lima / Violeta", o mesmo do Camarim ([design/DESIGN.md](design/DESIGN.md)) |
| Instagram de verdade | Código escrito, **nunca testado contra a API real** (exige um app seu na Meta) |
| Aprovação da Meta (App Review) | Não iniciada. Bloqueada por: CNPJ verificado, domínio com HTTPS, Política de Privacidade e Termos (ver [Roteiro](#roteiro-até-o-app-review-e-o-lançamento)) |
| Cobrança, recuperação de senha, e-mails, exclusão de conta, painel de administrador | Não existem |
| Hospedagem | Roda só na máquina local, via Docker |

## O que o Instagram deixa (e não deixa) saber

| O que o promoter fez | O app fica sabendo? |
|---|---|
| Comentou no post do gestor | Sim: quem foi e o texto |
| Publicou um story marcando o @ do gestor | Sim: quem foi e o link do story |
| Repostou o post no story **e** marcou o @ | Sim, pela marcação |
| Repostou no story **sem** marcar o @ | Não |
| Curtiu o post | Não (a Meta só informa o total de curtidas) |
| Compartilhou por direct ou fora do Instagram | Não |

Por isso os pontos vêm só de **comentários** e de **menções em story**. Detalhes:

- **Promoter não conecta o Instagram.** Ele só informa o @ no cadastro; todo comentário já vem com o @ de quem comentou.
- **Gestor precisa conectar.** Mesmo com o post público, a Meta só entrega os comentários ao dono do post, depois que ele autoriza o app.
- **A menção não diz o que tem no story.** Chega só um link para a imagem ou vídeo, válido enquanto o story está no ar (cerca de 24 horas). O app guarda esse link, mas ainda não o mostra na tela do gestor.
- **Menção em story** só chega de contas públicas, ou de contas privadas que seguem a conta do gestor.

Regra prática para os promoters: "reposte no story **e marque o @**". Sem a marcação não há como pontuar.

## Como rodar

Requisito: Docker Desktop. Não é preciso ter Python nem Node instalados.

```bash
cp .env.example .env     # preencha SECRET_KEY, TOKEN_ENCRYPTION_KEY e META_WEBHOOK_VERIFY_TOKEN
docker compose up -d --build
```

Abra **http://localhost:3000**. A API fica em `http://localhost:8000/api/v1`, com documentação interativa em `http://localhost:8000/docs`.

Gerar valores para os segredos:

```bash
openssl rand -hex 32                           # SECRET_KEY
openssl rand -base64 32 | tr '+/' '-_'         # TOKEN_ENCRYPTION_KEY
openssl rand -hex 16                           # META_WEBHOOK_VERIFY_TOKEN
```

### Logins de demonstração

Senha de todos: `Demo@12345`

| Papel | E-mail | Observação |
|---|---|---|
| Gestor | `gestor@demo.com` | Organização "Clube Demo", código de convite `KP7DM42X` |
| Promoter | `bia@demo.com` | aprovada, `@bia.promo` |
| Promoter | `caio@demo.com` | aprovado, `@caio.vip` |
| Promoter | `duda@demo.com` | pendente, `@duda.eventos` |

Os dados de demonstração são criados na primeira subida, quando o banco está vazio. Para voltar ao estado inicial (apaga o banco e os uploads):

```bash
docker compose down -v
docker compose up -d --build
```

## Modo simulado

Com `META_MOCK_MODE=true` (padrão no `.env`), o produto inteiro funciona sem app na Meta:

- **Conectar Instagram** liga uma conta de mentira, passando pelo mesmo código do fluxo real.
- **Posts** são simulados (imagens de exemplo), e publicar um post também funciona.
- **Simulador**: na página de uma campanha ativa, o gestor dispara comentários e menções em story como se viessem do Instagram. Eles passam pela mesma regra de pontuação dos eventos reais.

Para ligar no Instagram de verdade e pedir a aprovação da Meta, siga o **[guia da Meta](docs/META.md)**. Ele cobre o passo a passo de conexão, o App Review, os prazos e o que fazer se você não tem empresa.

## Como funciona a pontuação

1. Comentários e menções chegam por aviso da Meta (webhook), por busca periódica (a cada 2 minutos) ou pelo simulador. Os três caminhos usam a mesma regra, e o mesmo evento nunca pontua duas vezes.
2. **Comentário**: só conta o de primeiro nível (resposta a outro comentário não conta), em post de uma campanha ativa e dentro do período dela.
3. **Menção em story**: vale para a campanha ativa mais recente em que o promoter ainda não atingiu o limite de menções.
4. O promoter é identificado pelo @ entre os membros **aprovados** da equipe. Comentário de @ desconhecido fica como "não identificado".
5. Segundo comentário do mesmo promoter na mesma campanha fica como "duplicado" e vale zero.
6. Cada equipe tem saldo e lojinha próprios. O saldo nunca fica negativo.
7. Pontos de comentário ou de menção com valor 0 desativam aquela ação na campanha.

### Regras contra fraude de identidade

O gestor é quem confirma que um @ pertence a um promoter:

- Pontos de interações antigas só são creditados quando o gestor **aprova manualmente** o promoter.
- Quem **troca o @** volta para "pendente" em todas as equipes até o gestor aprovar de novo. Saldo e histórico são mantidos.
- A **aprovação automática** não pontua retroativamente: vale só para interações feitas depois da entrada.

Sem isso, um promoter poderia assumir o @ de outra pessoa e receber os pontos dela.

## Roteiro até o App Review e o lançamento

Cada gestor já tem a sua organização isolada (equipe, campanhas, pontos e lojinha próprios; um cliente não enxerga nada do outro, e isso está coberto por testes). O caminho até lançar, em ordem:

### Etapa 1: validar o Instagram real (modo de teste da Meta)

Nada disto depende de aprovação; depende de um app criado na Meta e de um endereço com HTTPS. Siga o [guia da Meta](docs/META.md), Parte 1.

1. Criar o app na Meta ("API setup with Instagram login") e preencher `META_APP_ID` / `META_APP_SECRET`.
2. Subir em um endereço público com HTTPS (túnel serve para este teste).
3. Conectar um Instagram profissional cadastrado como testador e conferir, **com conta real**:
   - a lista de posts ao criar campanha;
   - comentários chegando pelo webhook **e** pela busca periódica;
   - menção em story chegando pelo webhook (exige, no app do Instagram do gestor, *Configurações → Mensagens → Ferramentas conectadas → Permitir acesso às mensagens*);
   - publicar um post pelo app (exige endereço público para a Meta baixar a imagem);
   - desconectar e reconectar.
4. **Ponto de atenção a confirmar no primeiro teste:** a assinatura `X-Hub-Signature-256` dos webhooks é conferida com `META_APP_SECRET`. No login do Instagram há duas chaves no painel (a do app Meta e a do "app do Instagram"); se todo webhook vier recusado com 403, a chave usada para assinar é a outra, e o backend precisa de uma variável separada para ela.

### Etapa 2: o que precisa existir antes de pedir o App Review

| Item | Por quê | Situação |
|---|---|---|
| Domínio próprio com HTTPS (não túnel) | a Meta testa as URLs de callback e o revisor usa o app | falta |
| Página de **Política de Privacidade** pública | obrigatória no painel da Meta | falta |
| Página de **Termos de Uso** | exigida na prática para SaaS; o revisor procura | falta |
| **Exclusão de dados de verdade** | o callback `/meta/data-deletion` hoje só apaga a conexão do Instagram; os comentários e @ guardados de quem pediu a exclusão continuam no banco. A Meta e a LGPD esperam que sumam | parcial |
| **Excluir a própria conta** pelo app (gestor e promoter) | LGPD; o revisor costuma procurar | falta |
| Empresa verificada no Meta Business (CNPJ) | sem ela a análise do app não começa | falta (ver [guia](docs/META.md), Parte 3) |
| Conta de teste para o revisor, com campanha ativa e roteiro passo a passo | reprovação mais comum é login de teste que não funciona | falta |
| Vídeo de tela por permissão (4 vídeos) | exigido para cada uma das 4 permissões | falta |
| Revisar o pedido de `instagram_business_manage_messages` | é a permissão mais escrutinada; o uso declarado é **só** receber menções em story. O app nunca lê nem envia DM, e isso precisa estar no texto e no vídeo | texto a escrever |

Dica: peça só as permissões que o app usa. O código também pede `instagram_business_basic` ao **promoter** (verificação opcional do @), mas o login do Instagram só aceita contas profissionais e a maioria dos promoters tem conta pessoal. Para o App Review, o mais seguro é tirar essa verificação da tela ou deixá-la fora do pedido.

### Etapa 3: para operar como SaaS

- **E-mail transacional** (Resend, Postmark, SES): base para recuperação de senha, confirmação de e-mail e convite por e-mail.
- **Recuperação de senha** e **confirmação de e-mail**: não existem. Sem a primeira, todo esquecimento vira suporte manual.
- **Cobrança**: planos e assinatura (Stripe, Asaas, Pagar.me). Hoje qualquer um se cadastra e usa de graça.
- **Painel de administrador**: ver clientes, bloquear contas (o campo `is_active` existe, mas nada o altera) e acompanhar o uso.
- **Hospedagem de produção**: Postgres gerenciado com backup automático, Redis, uploads em armazenamento de objetos (S3, R2) em vez do disco do servidor, e o worker como serviço separado.
- **Monitoramento**: captura de erros (Sentry) e alerta quando o worker parar ou um webhook for descartado após 5 tentativas (hoje só vai para o log).
- **Produto**: botão "Ver story" no feed da campanha; estorno quando o promoter apagar o comentário depois de pontuar (hoje não há); limpeza periódica de sessões expiradas e notificações antigas.

## Segurança

### O que já está bom (e testado)

- Senhas com Argon2id; login em tempo constante para e-mail desconhecido.
- Sessão em cookies `HttpOnly`: token de acesso de 15 minutos e token de renovação com rotação. Reuso de um token já rotacionado revoga a sessão inteira. Logout e troca de senha invalidam a sessão na hora, e a checagem de revogação falha fechada se o Redis cair.
- Proteção contra CSRF por cabeçalho próprio e conferência de origem.
- Avisos da Meta validados por assinatura antes de qualquer processamento; o payload é reduzido ao mínimo antes de entrar na fila (texto de DM nunca é guardado).
- `signed_request` de desautorização e exclusão de dados validado por HMAC.
- Tokens do Instagram cifrados no banco (Fernet), nunca devolvidos pela API nem escritos em log.
- Isolamento por organização: recurso de outra equipe responde "não encontrado".
- Limite de requisições no login, cadastro, renovação, convite, resgate, upload e simulador, com reserva em memória se o Redis cair.
- Corpo de requisição limitado enquanto é recebido; imagens enviadas são decodificadas e regravadas como JPEG, sem metadados.
- Cabeçalhos de segurança em toda resposta (CSP, `nosniff`, `X-Frame-Options`, HSTS com HTTPS); CSP com nonce no frontend; contêineres sem usuário root.
- Em produção o app **recusa subir** com modo simulado, cookies inseguros, segredos padrão ou dados de demonstração. Sem `ENVIRONMENT` definido, o padrão é `production`: esquecer a variável no deploy não pula essa trava.

### O que falta (em ordem de prioridade)

1. **Exclusão de dados e de conta** (LGPD e Meta), descrita na Etapa 2.
2. **Defesa em profundidade no banco**: o isolamento entre equipes depende só do `where` de cada consulta. Uma consulta esquecida vaza dados de outro cliente. Row Level Security no Postgres, como no Camarim, fecha essa porta.
3. **Política de retenção**: comentários, @ e links de story ficam para sempre. Definir prazo (por exemplo, 12 meses após o fim da campanha) e apagar automaticamente.
4. **Disputa de @**: quem se cadastra primeiro com um @ fica com ele. A aprovação manual do gestor impede o roubo de pontos, mas o dono real do @ não consegue se cadastrar e não há caminho para resolver.
5. **Backups e rotação de segredos**: rotacionar `TOKEN_ENCRYPTION_KEY` hoje exige reconectar todas as contas (não há suporte a duas chaves ao mesmo tempo).
6. **Health check de prontidão**: `/health` responde "ok" mesmo com banco ou Redis fora; o orquestrador não percebe a falha.

## Estrutura do projeto

```
compose.yaml / compose.dev.yaml   stack completa e variação de desenvolvimento
.env.example                      modelo das variáveis de ambiente (o .env não é versionado)
backend/                          API em FastAPI, migrações, testes
frontend/                         site em Next.js
design/                           design system (os tokens moram em frontend/src/app/globals.css)
docs/META.md                      guia para conectar e aprovar na Meta
docs/ARCHITECTURE.md              contrato técnico entre backend e frontend (em inglês)
docs/openapi.json                 esquema da API gerado pelo backend
```

Tecnologias: Next.js 16 e Tailwind 4 no frontend; FastAPI, PostgreSQL 17, Redis 7 e um worker de tarefas no backend; tudo em Docker Compose.

## Desenvolvimento

Backend com recarga automática ao editar o código:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d --build db redis backend worker
```

Testes e lint do backend (usam um banco separado, nunca o de desenvolvimento):

```bash
docker compose -f compose.yaml -f compose.dev.yaml run --rm tests
docker compose -f compose.yaml -f compose.dev.yaml run --rm tests ruff check .
```

A suíte tem 109 testes: autenticação, isolamento entre organizações, regras de pontuação, concorrência, resgates, webhooks e uploads. O frontend não tem testes automatizados; os fluxos de tela foram verificados manualmente em navegador. Veja [frontend/README.md](frontend/README.md).

## Colocando em produção

Variáveis do `.env`:

```
ENVIRONMENT=production
APP_URL=https://SEU-DOMINIO
ALLOWED_ORIGINS=https://SEU-DOMINIO
COOKIE_SECURE=true
META_MOCK_MODE=false
META_APP_ID=...
META_APP_SECRET=...
SECRET_KEY=...
TOKEN_ENCRYPTION_KEY=...
META_WEBHOOK_VERIFY_TOKEN=...
SEED_DEMO=false
```

Em produção o app **recusa subir** com modo simulado ligado, cookies inseguros, segredos vazios ou dados de demonstração. Sem `ENVIRONMENT` definido o padrão já é `production`; o `.env.example` declara `development` para o uso local.

Coloque um proxy HTTPS (Caddy, Nginx, Traefik) na frente do frontend, na porta 3000.

> **Não exponha a porta 3000 direto à internet.** O Next.js repassa ao backend o cabeçalho `X-Forwarded-For` que o cliente enviar, sem validar. Quem define o IP real é o proxy da frente: ele precisa sobrescrever esse cabeçalho com o endereço do cliente (padrão do Caddy) ou acrescentar o endereço ao final (`proxy_add_x_forwarded_for` no Nginx). Sem isso, os limites de requisições por IP podem ser burlados. Por esse motivo o `compose.yaml` publica o frontend apenas em `127.0.0.1:3000`.

Outros pontos:

- O limite do tamanho de upload (8 MB) também deve ser configurado no proxy.
- Postgres e Redis não são publicados fora da rede do Docker.
- Publicar posts pelo app exige endereço público: a Meta baixa a imagem pela internet.

## Como foi construído

O código foi escrito por agentes de IA e revisado: o backend e o frontend por agentes Claude Sonnet, o design e a revisão de segurança do backend pelo Codex (ChatGPT), com orquestração e verificação final pelo Claude Opus. A revisão do backend apontou 22 problemas, todos corrigidos com teste. O frontend não passou pela revisão do Codex; foi revisado pelo orquestrador.

O visual foi refeito depois com o design system do Camarim ("Noite / Lima / Violeta"): tokens, materiais, tipografia, cascas e telas de entrada.
