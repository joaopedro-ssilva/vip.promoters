# VIP Promoters

Aplicativo web para gestão de divulgação no Instagram.

- O **gestor** conecta a conta profissional do Instagram, cria campanhas a partir de um post, dispara para a equipe, vê quem comentou ou marcou a conta em um story, aprova promoters e mantém uma lojinha de recompensas.
- O **promoter** entra na equipe com um código de convite, comenta no post ou marca a conta no story, ganha pontos e troca por recompensas.

Regra central: **no máximo 1 comentário pontuado por promoter em cada campanha**.

## Situação atual

| Item | Estado |
|---|---|
| Produto (gestor, promoter, pontos, lojinha) | Pronto e testado em modo simulado |
| Instagram de verdade | Código escrito, **nunca testado contra a API real** (exige um app seu na Meta) |
| Aprovação da Meta (App Review) | Não iniciada |
| Cobrança, recuperação de senha, e-mails, painel de administrador | Não existem (ver [O que falta para virar SaaS](#o-que-falta-para-virar-saas)) |
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

## O que falta para virar SaaS

Cada gestor já tem a sua organização isolada (equipe, campanhas, pontos e lojinha próprios; um cliente não enxerga nada do outro, e isso está coberto por testes). O que ainda não existe:

- **Cobrança**: não há planos, assinatura nem pagamento. Qualquer um se cadastra e usa de graça.
- **Recuperação de senha** e **confirmação de e-mail**: o app ainda não envia e-mails.
- **Política de Privacidade e Termos de Uso**: as páginas não existem, e a Meta exige a primeira para aprovar o app.
- **Painel de administrador**: para ver clientes, bloquear contas e acompanhar o uso.
- **Hospedagem** em endereço público com HTTPS.
- **Botão "Ver story"** no feed da campanha, para o gestor conferir o conteúdo da menção.
- **Moderação**: não há estorno automático se o promoter apagar o comentário depois de pontuar.

## Estrutura do projeto

```
compose.yaml / compose.dev.yaml   stack completa e variação de desenvolvimento
.env.example                      modelo das variáveis de ambiente (o .env não é versionado)
backend/                          API em FastAPI, migrações, testes
frontend/                         site em Next.js
design/                           guia visual e tokens de cor e tipografia
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

A suíte tem 108 testes: autenticação, isolamento entre organizações, regras de pontuação, concorrência, resgates, webhooks e uploads. O frontend não tem testes automatizados; os fluxos de tela foram verificados manualmente em navegador. Veja [frontend/README.md](frontend/README.md).

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

Em produção o app **recusa subir** com modo simulado ligado, cookies inseguros, segredos vazios ou dados de demonstração.

Coloque um proxy HTTPS (Caddy, Nginx, Traefik) na frente do frontend, na porta 3000.

> **Não exponha a porta 3000 direto à internet.** O Next.js repassa ao backend o cabeçalho `X-Forwarded-For` que o cliente enviar, sem validar. Quem define o IP real é o proxy da frente: ele precisa sobrescrever esse cabeçalho com o endereço do cliente (padrão do Caddy) ou acrescentar o endereço ao final (`proxy_add_x_forwarded_for` no Nginx). Sem isso, os limites de requisições por IP podem ser burlados. Por esse motivo o `compose.yaml` publica o frontend apenas em `127.0.0.1:3000`.

Outros pontos:

- O limite do tamanho de upload (8 MB) também deve ser configurado no proxy.
- Postgres e Redis não são publicados fora da rede do Docker.
- Publicar posts pelo app exige endereço público: a Meta baixa a imagem pela internet.

## Segurança (resumo)

- Senhas com Argon2id.
- Sessão em cookies `HttpOnly`: token de acesso de 15 minutos e token de renovação com rotação. Logout e troca de senha invalidam a sessão na hora.
- Proteção contra CSRF por cabeçalho próprio e conferência de origem.
- Avisos da Meta validados por assinatura antes de qualquer processamento.
- Tokens do Instagram cifrados no banco, nunca devolvidos pela API nem escritos em log.
- Isolamento por organização: recurso de outra equipe responde "não encontrado".
- Limite de requisições no login, cadastro, resgate e upload.
- Imagens enviadas são decodificadas e regravadas como JPEG.
- Política de segurança de conteúdo (CSP) com nonce no frontend; contêineres sem usuário root.

## Como foi construído

O código foi escrito por agentes de IA e revisado: o backend e o frontend por agentes Claude Sonnet, o design e a revisão de segurança do backend pelo Codex (ChatGPT), com orquestração e verificação final pelo Claude Opus. A revisão do backend apontou 22 problemas, todos corrigidos com teste. O frontend não passou pela revisão do Codex; foi revisado pelo orquestrador.
