# VIP Promoters

Aplicativo web para gestão de divulgação no Instagram.

- O **gestor** conecta a conta profissional do Instagram, cria campanhas a partir de um post, dispara para a equipe, vê quem comentou ou marcou a conta em um story, aprova promoters e mantém uma lojinha de recompensas.
- O **promoter** entra na equipe com um código de convite, comenta no post ou marca a conta no story, ganha pontos e troca por recompensas.

Regra central: **no máximo 1 comentário pontuado por promoter em cada campanha**.

## Situação atual

| Item | Estado |
|---|---|
| Produto (gestor, promoter, pontos, lojinha) | Pronto e testado em modo simulado |
| Backend | 133 testes passando e lint limpo, rodando como em produção (papel de banco sem privilégios, com RLS) |
| Segurança e LGPD | Isolamento entre equipes em duas camadas (aplicação e RLS no Postgres), exclusão de conta e de dados, retenção automática, verificação do @ por comentário com disputa, rotação de chaves (ver [Segurança](#segurança)) |
| Páginas legais | Política de Privacidade (`/privacidade`) e Termos (`/termos`) prontos como **modelo**: falta preencher os dados da empresa e passar por um advogado |
| Visual | Design system "Noite / Lima / Violeta", o mesmo do Camarim ([design/DESIGN.md](design/DESIGN.md)) |
| Instagram de verdade | Código escrito, **nunca testado contra a API real** (exige um app seu na Meta) |
| Aprovação da Meta (App Review) | Não iniciada. Bloqueada por coisas fora do código: CNPJ verificado e domínio com HTTPS (ver [Etapas](#etapas-para-o-app-review-e-o-lançamento-como-saas)) |
| Cobrança, recuperação de senha, e-mails, painel de administrador | Não existem |
| Hospedagem | Roda só na máquina local, via Docker |

O que falta decidir e fazer, em ordem: [Etapas para o App Review e o lançamento](#etapas-para-o-app-review-e-o-lançamento-como-saas), [Decisões em aberto](#decisões-em-aberto) e [Próximos passos](#próximos-passos). Os gargalos técnicos estão em [docs/DECISOES.md](docs/DECISOES.md).

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
cp .env.example .env     # preencha SECRET_KEY, TOKEN_ENCRYPTION_KEY, META_WEBHOOK_VERIFY_TOKEN, POSTGRES_PASSWORD e APP_DB_PASSWORD
docker compose up -d --build
```

Ao subir, o serviço `migrate` aplica as migrações e cria o papel de banco da aplicação (`vip_app`); só depois o backend e o worker sobem, já conectados com esse papel.

Abra **http://localhost:3000**. A API fica em `http://localhost:8000/api/v1`, com documentação interativa em `http://localhost:8000/docs`.

Gerar valores para os segredos:

```bash
openssl rand -hex 32                           # SECRET_KEY
openssl rand -base64 32 | tr '+/' '-_'         # TOKEN_ENCRYPTION_KEY
openssl rand -hex 16                           # META_WEBHOOK_VERIFY_TOKEN
openssl rand -hex 24                           # POSTGRES_PASSWORD e APP_DB_PASSWORD (um valor para cada)
```

O compose não tem senha padrão de banco: sem `POSTGRES_PASSWORD` e `APP_DB_PASSWORD` no `.env`, ele se recusa a subir. Se você já tem o volume do Postgres criado com a senha antiga (`vip`), use essa mesma senha em `POSTGRES_PASSWORD`; o Postgres só define a senha na primeira criação do volume.

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

### Verificação do @ e disputa

O promoter pode **provar** que o @ é dele, mesmo com conta pessoal: o app gera um código (`VIP-XXXXXX`) e ele comenta esse código em qualquer post de uma conta conectada ao app. O comentário chega pelo webhook com o @ autêntico de quem comentou, que vem da Meta e não do usuário. O gestor vê o selo de verificado na lista da equipe. O comentário de verificação nunca pontua.

Se outra pessoa cadastrou o seu @ sem verificar, o cadastro oferece "É meu: criar conta e provar". A conta nasce sem @ e, quando o código chega comentado pelo @ certo, o @ muda de dono: quem estava com ele fica sem @ e as equipes dele voltam para "pendente". Um @ já verificado não pode ser reivindicado.

O login do Instagram não é mais pedido ao promoter: ele só aceita contas profissionais e aumentaria o escopo do App Review.

## Etapas para o App Review e o lançamento como SaaS

O caminho completo, em ordem. Cada fase diz se é código (já feito ou a fazer) ou ação sua.

### Fase 0: o que o código já resolve

| Exigência | Onde está |
|---|---|
| Política de Privacidade e Termos de Uso públicos | `/privacidade` e `/termos` (modelos: preencha `frontend/src/lib/legal.ts`) |
| URL de exclusão de dados da Meta, que apaga de verdade e devolve um código consultável | `POST /api/v1/meta/data-deletion` e `GET /api/v1/meta/data-deletion/{código}` |
| URL de desautorização | `POST /api/v1/meta/deauthorize` |
| Excluir a própria conta (gestor e promoter) | Configurações / Perfil → "Excluir minha conta" |
| Prazo de retenção e minimização de dados | job diário do worker (`RETENTION_DAYS`) |
| Só 4 permissões, todas do gestor | o promoter não conecta o Instagram |
| Isolamento entre clientes (o revisor e os clientes perguntam) | aplicação + Row Level Security, com testes |

### Fase 1: empresa, domínio e textos legais (você)

1. **CNPJ** (MEI ou ME; ver [guia da Meta](docs/META.md), Parte 3) e **Meta Business verificado** com os mesmos dados do cartão CNPJ. Leva de 1 a 5 dias úteis; comece por aqui.
2. **Domínio** próprio e um **e-mail de contato** nele (ex.: `privacidade@seudominio.com.br`).
3. Preencher `frontend/src/lib/legal.ts` (razão social, CNPJ, e-mail, encarregado, foro, data) e **revisar a Política e os Termos com um advogado** (ver [DECISOES.md](docs/DECISOES.md), 1.6).

### Fase 2: hospedagem de produção (você)

1. Servidor com Docker (ou PaaS) e **proxy HTTPS** (Caddy, Nginx, Traefik) na frente do frontend. Veja [Colocando em produção](#colocando-em-produção).
2. **Postgres com backup automático**: gerenciado (Neon, Supabase, RDS…) ou o do compose com `scripts/backup.sh` agendado e cópia fora do servidor.
3. `.env` de produção completo, com segredos novos (lista em [Colocando em produção](#colocando-em-produção)).
4. Monitor de disponibilidade apontado para `/api/v1/health/ready` (UptimeRobot, Better Stack…).

### Fase 3: Instagram real em modo de teste (você)

Siga o [guia da Meta](docs/META.md), Parte 1.

1. Criar o app na Meta ("API setup with Instagram login") e preencher `META_APP_ID` / `META_APP_SECRET`.
2. Cadastrar as URLs no painel: redirecionamento, webhook (campos `comments` e `messages`), desautorização e exclusão de dados.
3. Com uma conta **testadora**, conferir:
   - [ ] os posts aparecem ao criar campanha;
   - [ ] o comentário chega pelo webhook **e** pela busca periódica;
   - [ ] a menção em story chega (exige, no Instagram do gestor, *Configurações → Mensagens → Ferramentas conectadas → Permitir acesso às mensagens*);
   - [ ] a verificação de @ de um promoter testador funciona (comentar o código num post);
   - [ ] publicar um post pelo app;
   - [ ] remover o app no Instagram e pedir exclusão de dados: o código de confirmação abre em `/api/v1/meta/data-deletion/{código}`.
4. Se **todo** webhook voltar com 403, defina `META_WEBHOOK_SECRET` com a outra chave do painel ([DECISOES.md](docs/DECISOES.md), 2.1).

### Fase 4: montar o pedido do App Review

1. **Configurações → Básico** no painel: ícone, categoria, URL da Política (`https://SEU-DOMINIO/privacidade`), URL dos Termos (`/termos`), URL de exclusão de dados e o vínculo com a empresa verificada.
2. **Conta para o revisor**: um gestor com Instagram de teste conectado, uma campanha **ativa**, promoters aprovados e um roteiro passo a passo em inglês. Em produção `SEED_DEMO` fica `false`; crie essa conta à mão.
3. **Acesso avançado** para as 4 permissões, cada uma com texto e vídeo. Textos sugeridos (adapte):

| Permissão | Texto do uso | O vídeo mostra |
|---|---|---|
| `instagram_business_basic` | "The business connects its professional Instagram account to pick one of its own posts as a campaign and to show its profile to its team." | Login no app → Conectar Instagram → tela de autorização → perfil e posts na criação de campanha |
| `instagram_business_manage_comments` | "We read comments on the business's own campaign posts to credit points to the team members who commented. We never reply, hide or delete comments." | Campanha ativa → alguém comenta no Instagram → o comentário aparece no feed da campanha com os pontos |
| `instagram_business_manage_messages` | "Only used to receive story_mention webhooks when a team member mentions the business in a story. We do not read, store or send direct messages." | Promoter publica story marcando o @ → a menção aparece na campanha. Diga, em voz ou legenda, que nenhuma DM é lida |
| `instagram_business_content_publish` | "The business can publish a new post from the app and use it as a campaign." | Nova campanha → Publicar novo → o post aparece no Instagram |

4. Responder o **questionário de tratamento de dados** com o que está na Política: dados mínimos, retenção, exclusão, onde fica hospedado.
5. Enviar. Prazo típico: de alguns dias a 2 semanas depois da empresa verificada. A reprovação costuma vir de vídeo pouco claro ou de login de teste que não funciona; cada reenvio volta para a fila.

### Fase 5: lançar como SaaS

| Item | Por quê | Quem |
|---|---|---|
| Pôr o app em **Ao vivo** no painel da Meta | sem isso, só testadores conectam | você |
| **E-mail transacional** (Resend, Postmark, SES) | base dos itens abaixo | código |
| **Recuperação de senha** e **confirmação de e-mail** | sem isso, cada senha esquecida vira suporte | código |
| **Cobrança** (Stripe, Asaas, Pagar.me): planos, teste grátis, bloqueio por falta de pagamento | hoje qualquer um usa de graça | código + decisão de planos ([DECISOES.md](docs/DECISOES.md), 1.7) |
| **Painel de administrador**: clientes, uso, bloquear conta | operar o SaaS | código |
| **Onboarding do gestor** com o aviso de "Permitir acesso às mensagens" | sem isso, as menções em story não chegam | código |
| **Uploads em S3/R2** | permite mais de um servidor e entra no backup | código |
| **Monitoramento de erros** (Sentry) e alerta de webhook descartado | saber dos problemas antes do cliente | código |
| **Processo de suporte LGPD** (e-mail da Política, `python -m app.cli esquecer @fulano`) | atende pedidos de quem só comentou | você |

## Decisões em aberto

Pontos que o código não resolve sozinho. A recomendação é a sugestão técnica; quem decide está na última coluna. O raciocínio completo de cada item está em [docs/DECISOES.md](docs/DECISOES.md).

### De produto e negócio

| # | Decisão | Como está hoje | Recomendação | Quem decide |
|---|---|---|---|---|
| 1 | Promoter que exclui a conta: o que acontece com os resgates pendentes dele? | Somem, e o estoque da recompensa volta | Manter um registro anônimo, se o gestor precisar fechar contas com o fornecedor | você |
| 2 | Gestor que exclui a conta | Exclusão imediata, sem carência e sem exportação | 30 dias para desfazer e um CSV antes de apagar, quando houver cobrança | você |
| 3 | Prazo de retenção das interações | 365 dias após o fim da campanha (`RETENTION_DAYS`) | Manter, se o advogado concordar | você + advogado |
| 4 | Quem perde um @ na disputa fica com os pontos que já ganhou? | Fica | Não estornar automaticamente; avisar o gestor e deixar o "ajustar pontos" com ele | você |
| 5 | Processo do suporte para @ já verificado por outra pessoa | O app manda "fale com o suporte", mas não há processo | Pedir um comentário com código novo e trocar o dono à mão | você |
| 6 | Papel na LGPD: o gestor é controlador e o VIP Promoters é operador? | A Política sugere isso | Confirmar com advogado e incluir cláusulas de operador nos Termos | advogado |
| 7 | Planos, preço e limites | Não existem | Definir antes de implementar a cobrança | você |

### Técnicas, que só o teste com a Meta responde

| # | Dúvida | Preparado no código |
|---|---|---|
| 8 | Qual chave assina os webhooks (a do app Meta ou a do app do Instagram)? | `META_WEBHOOK_SECRET` opcional |
| 9 | Comentários de quem não é testador chegam no modo de teste? | Sem resposta, a verificação de @ só funciona com testadores até o App Review |
| 10 | Comentário apagado gera webhook? | Sem webhook, o estorno automático exigiria comparar listas no polling |
| 11 | Quanto o polling a cada 2 minutos consome da cota da Graph API? | Ajustável com `SYNC_INTERVAL_SECONDS` |

## Próximos passos

Em ordem. "Você" é ação fora do código; "código" é desenvolvimento.

| # | Passo | Quem | Destrava |
|---|---|---|---|
| 1 | Rodar `docker compose up -d --build` na sua máquina (com `APP_DB_PASSWORD` no `.env`) e conferir os fluxos novos | você | o primeiro deploy |
| 2 | Abrir o CNPJ e pedir a verificação do Meta Business (1 a 5 dias úteis) | você | o App Review |
| 3 | Domínio, e-mail de contato e preencher `frontend/src/lib/legal.ts`; revisão da Política e dos Termos com advogado | você | o App Review |
| 4 | Servidor com HTTPS, Postgres com backup e monitor em `/api/v1/health/ready` ([Fase 2](#fase-2-hospedagem-de-produção-você)) | você | a Fase 3 |
| 5 | Testar o Instagram real em modo de teste ([Fase 3](#fase-3-instagram-real-em-modo-de-teste-você)) e responder as dúvidas 8 a 11 | você | o pedido do App Review |
| 6 | Aviso no onboarding do gestor para ligar "Permitir acesso às mensagens" no Instagram | código | as menções em story |
| 7 | CI no GitHub (testes do backend e build do frontend a cada push) e atualização automática de dependências | código | segurança contínua |
| 8 | E-mail transacional, recuperação de senha e confirmação de e-mail | código | operar sem suporte manual |
| 9 | Montar e enviar o App Review ([Fase 4](#fase-4-montar-o-pedido-do-app-review)) | você | o modo Ao vivo |
| 10 | Cobrança (depois da decisão 7) e painel de administrador | código | o SaaS pago |
| 11 | Uploads em S3/R2 e monitoramento de erros (Sentry) | código | mais de um servidor |
| 12 | Segundo fator de login para o gestor e um pentest externo | código + terceiros | clientes pagantes |

## Segurança

### O que está pronto (e testado)

- **Isolamento entre equipes em duas camadas.** Toda consulta filtra pela organização e, por baixo, o Postgres aplica **Row Level Security**: numa requisição autenticada, o banco só devolve linhas das organizações do usuário, mesmo que uma consulta esqueça o filtro (há um teste que cria uma rota "com bug" e prova isso). O app conecta com um papel sem superusuário, sem `BYPASSRLS` e que não é dono das tabelas, e em produção recusa subir se isso não for verdade. O worker, os webhooks e as rotas públicas rodam em "modo sistema", de propósito ([DECISOES.md](docs/DECISOES.md), 3.1).
- **Senhas** com Argon2id; login em tempo constante para e-mail desconhecido.
- **Sessão** em cookies `HttpOnly`: token de acesso de 15 minutos e token de renovação com rotação. Reuso de um token já rotacionado revoga a sessão inteira. Logout, troca de senha e exclusão de conta invalidam a sessão na hora, e a checagem de revogação falha fechada se o Redis cair.
- **CSRF** por cabeçalho próprio e conferência de origem.
- **Avisos da Meta** validados por assinatura antes de qualquer processamento; o payload é reduzido ao mínimo antes de entrar na fila (texto de DM nunca é guardado). `signed_request` de desautorização e de exclusão validado por HMAC.
- **Tokens do Instagram** cifrados no banco, nunca devolvidos pela API nem escritos em log.
- **Rotação de chaves sem derrubar ninguém**: `SECRET_KEY_PREVIOUS` e `TOKEN_ENCRYPTION_KEY_PREVIOUS` continuam valendo só para leitura, e o worker recifra os tokens com a chave nova.
- **LGPD**: excluir a própria conta pelo app; exclusão de dados pedida pela Meta que apaga de verdade e registra o pedido (só o hash do id); anonimização automática das interações após `RETENTION_DAYS`; limpeza de sessões e notificações antigas; esquecimento de quem só comentou (`python -m app.cli esquecer @fulano`).
- **Identidade do promoter**: verificação do @ por comentário e disputa de @ cadastrado sem verificação.
- **Limite de requisições** no login, cadastro, renovação, convite, verificação, resgate, upload e simulador, com reserva em memória se o Redis cair.
- **Uploads**: corpo limitado enquanto é recebido; imagens decodificadas e regravadas como JPEG, sem metadados.
- **Cabeçalhos de segurança** em toda resposta (CSP, `nosniff`, `X-Frame-Options`, HSTS com HTTPS); CSP com nonce no frontend; contêineres sem usuário root.
- **Configuração de produção**: o app recusa subir com modo simulado, cookies inseguros, segredos padrão (inclusive como chave anterior) ou dados de demonstração. Sem `ENVIRONMENT`, o padrão é `production`.
- **Prontidão**: `/api/v1/health/ready` responde 503 se o banco ou o Redis caírem (o compose usa esse endpoint no healthcheck).
- **Backup**: `scripts/backup.sh` (pg_dump) com restauração.

### O que ainda falta

1. **Recuperação de senha e confirmação de e-mail** (dependem de e-mail transacional). Hoje o cadastro aceita qualquer e-mail sem confirmar.
2. **Segundo fator (2FA) para o gestor**: a conta do gestor controla o Instagram da empresa.
3. **Painel de administrador** para bloquear contas (o campo `is_active` existe, mas nada o altera).
4. **Revisão externa** (pentest) antes de ter clientes pagantes, e atualização automática de dependências (Dependabot) com CI rodando os testes.

## Operação

```bash
docker compose run --rm migrate                         # migrações + papel de aplicação (roda sozinho no up)
docker compose exec backend python -m app.cli retencao  # aplica a retenção agora (o worker roda todo dia)
docker compose exec backend python -m app.cli esquecer @fulano   # pedido LGPD de quem só comentou
scripts/backup.sh                                       # backup do banco em backups/
scripts/backup.sh restaurar backups/vip-AAAAMMDD-HHMMSS.dump
```

**Trocar uma chave**: mova o valor atual para `SECRET_KEY_PREVIOUS` (ou `TOKEN_ENCRYPTION_KEY_PREVIOUS`), gere o novo e reinicie. Depois de 15 minutos (sessões) ou da próxima execução do job de recifra (tokens do Instagram), a chave anterior pode sair.

## Estrutura do projeto

```
compose.yaml / compose.dev.yaml   stack completa e variação de desenvolvimento
.env.example                      modelo das variáveis de ambiente (o .env não é versionado)
backend/                          API em FastAPI, migrações, testes
frontend/                         site em Next.js
design/                           design system (os tokens moram em frontend/src/app/globals.css)
docs/META.md                      guia para conectar e aprovar na Meta
docs/DECISOES.md                  gargalos e dúvidas de solução em aberto
scripts/backup.sh                 backup e restauração do Postgres
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

Fora do Docker, com um Postgres e um Redis locais (o usuário do `DATABASE_URL_ADMIN` precisa poder criar bancos e papéis):

```bash
cd backend
DATABASE_URL_ADMIN=postgresql+asyncpg://USUARIO:SENHA@localhost:5432/vip REDIS_URL=redis://localhost:6379/0 uv run pytest -q
```

Os testes criam o banco `vip_test`, rodam `python -m app.cli preparar-banco` e usam o app com o **papel de aplicação**: o RLS vale de verdade nos testes. A suíte tem 133 testes: autenticação, isolamento entre organizações, regras de pontuação, concorrência, resgates, webhooks e uploads. O frontend não tem testes automatizados; os fluxos de tela foram verificados manualmente em navegador. Veja [frontend/README.md](frontend/README.md).

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
POSTGRES_PASSWORD=...          # dono das tabelas: só o serviço migrate usa
APP_DB_PASSWORD=...            # papel de aplicação (vip_app): é com ele que o app conecta
SEED_DEMO=false
RETENTION_DAYS=365
```

Com Postgres gerenciado (fora do compose), rode `python -m app.cli preparar-banco` com `DATABASE_URL_ADMIN` apontando para o usuário dono e `APP_DB_USER`/`APP_DB_PASSWORD` definidos; depois aponte o `DATABASE_URL` do app para o papel de aplicação. O app **recusa subir em produção** se o `DATABASE_URL` for superusuário, tiver `BYPASSRLS` ou for dono das tabelas: nesses casos o RLS não valeria.

Em produção o app **recusa subir** com modo simulado ligado, cookies inseguros, segredos vazios ou dados de demonstração. Sem `ENVIRONMENT` definido o padrão já é `production`; o `.env.example` declara `development` para o uso local.

Coloque um proxy HTTPS (Caddy, Nginx, Traefik) na frente do frontend, na porta 3000.

> **Não exponha a porta 3000 direto à internet.** O Next.js repassa ao backend o cabeçalho `X-Forwarded-For` que o cliente enviar, sem validar. Quem define o IP real é o proxy da frente: ele precisa sobrescrever esse cabeçalho com o endereço do cliente (padrão do Caddy) ou acrescentar o endereço ao final (`proxy_add_x_forwarded_for` no Nginx). Sem isso, os limites de requisições por IP podem ser burlados. Por esse motivo o `compose.yaml` publica o frontend apenas em `127.0.0.1:3000`.

Outros pontos:

- O limite do tamanho de upload (8 MB) também deve ser configurado no proxy.
- Postgres e Redis não são publicados fora da rede do Docker.
- Publicar posts pelo app exige endereço público: a Meta baixa a imagem pela internet.

## Como foi construído

O código foi escrito por agentes de IA e revisado: o backend e o frontend por agentes Claude Sonnet, o design e a revisão de segurança do backend pelo Codex (ChatGPT), com orquestração e verificação final pelo Claude Opus. A revisão do backend apontou 22 problemas, todos corrigidos com teste. O frontend não passou pela revisão do Codex; foi revisado pelo orquestrador.

O visual foi refeito depois com o design system do Camarim ("Noite / Lima / Violeta"): tokens, materiais, tipografia, cascas e telas de entrada. Na rodada seguinte entraram o RLS no Postgres, a exclusão de conta e de dados, a retenção, a verificação e disputa de @, a rotação de chaves e as páginas legais.
