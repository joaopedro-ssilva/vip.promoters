# Guia da Meta: conectar o Instagram e aprovar o app

Este guia explica, em linguagem simples, como sair do modo simulado e usar o Instagram de verdade.

> **Avisos**
> - O caminho real nunca foi testado neste projeto, porque exige um app próprio na Meta. O código segue a documentação oficial, mas espere ajustes na primeira conexão.
> - Os nomes dos menus no painel da Meta mudam de vez em quando. Trate os caminhos como aproximados.
> - Os prazos abaixo são o que costuma acontecer, não um compromisso da Meta.

## Visão geral

| Fase | O que libera | Precisa de empresa (CNPJ)? |
|---|---|---|
| Modo simulado | Testar o produto inteiro com dados de mentira | Não |
| Modo de teste da Meta | Usar o Instagram real, só com contas cadastradas como testadoras | Não |
| App aprovado (App Review) | Qualquer empresa conecta o próprio Instagram | Sim |

## Parte 1: conectar o Instagram real (modo de teste)

### Você precisa de

- Uma conta do Instagram **profissional** (Comercial ou Criador de conteúdo). Se for pessoal, mude no app do Instagram em Configurações → Tipo de conta.
- Uma conta do Facebook, para entrar no painel de desenvolvedor.
- O app em um **endereço público com https**. A Meta não aceita `localhost`.

### Passo 1: endereço público

Para testar sem hospedar, use um túnel como ngrok ou cloudflared. Ele cria um endereço `https://...` que aponta para o seu `localhost:3000`. Chamaremos esse endereço de **SEU-ENDERECO**.

### Passo 2: criar o app na Meta

1. Acesse <https://developers.facebook.com> → **Meus apps** → **Criar app**.
2. Dentro do app, adicione o produto **Instagram**.
3. Escolha **"API setup with Instagram login"** (configuração da API com login do Instagram).
4. Copie o **ID do app do Instagram** e a **Chave secreta do app do Instagram**.

### Passo 3: configurar o `.env`

```
META_MOCK_MODE=false
META_APP_ID=o ID copiado
META_APP_SECRET=a chave secreta copiada
APP_URL=https://SEU-ENDERECO
ALLOWED_ORIGINS=https://SEU-ENDERECO
COOKIE_SECURE=true
```

Reinicie:

```bash
docker compose up -d --build
```

### Passo 4: informar os endereços à Meta

Na tela do produto Instagram, no painel da Meta:

| Campo | Valor |
|---|---|
| URL de redirecionamento (Business login settings) | `https://SEU-ENDERECO/api/v1/instagram/callback` |
| Webhook: URL de callback | `https://SEU-ENDERECO/api/v1/webhooks/instagram` |
| Webhook: token de verificação | o valor de `META_WEBHOOK_VERIFY_TOKEN` do `.env` |
| Política de Privacidade / Termos | `https://SEU-ENDERECO/privacidade` e `https://SEU-ENDERECO/termos` |
| Webhook: campos a assinar | `comments` e `messages` |
| URL de desautorização | `https://SEU-ENDERECO/api/v1/meta/deauthorize` |
| URL de exclusão de dados | `https://SEU-ENDERECO/api/v1/meta/data-deletion` |

O app precisa estar rodando nessa hora: a Meta testa o endereço do webhook ao salvar.

### Passo 5: cadastrar a conta como testadora

1. No painel da Meta, em **Funções do app**, adicione o Instagram do gestor como testador.
2. No Instagram, aceite o convite em Configurações → Sites e apps → Convites de testador.

### Passo 6: conectar dentro do app

1. Abra `https://SEU-ENDERECO` e entre como gestor.
2. Menu **Instagram** → **Conectar Instagram**.
3. Faça login no Instagram e autorize.
4. O status passa a **Conectada**, e os posts reais aparecem ao criar uma campanha.

### Limites do modo de teste

- Só funcionam contas de gestor cadastradas como testadoras. Promoters não precisam de cadastro na Meta: eles não conectam nada.
- A **verificação de @ por comentário** depende do comentário chegar pelo webhook; no modo de teste, provavelmente só chega o de contas com função no app. Para testar, cadastre o Instagram do promoter também como testador.
- Se **todo** webhook for recusado (403 no log), a Meta está assinando com a outra chave do painel (a do app Meta, em vez da do app do Instagram, ou o contrário). Coloque essa outra chave em `META_WEBHOOK_SECRET` e reinicie.
- A Meta costuma entregar apenas as interações de pessoas que também têm função no app. A menção em story de um promoter comum provavelmente não chega.
- A leitura de comentários é feita por busca periódica (a cada 2 minutos) e pode funcionar antes da aprovação, mas isso não foi confirmado com conta real.

O modo de teste serve para validar a ideia, não para operar com promoters de verdade.

## Parte 2: aprovar o app (App Review)

A aprovação tem duas etapas em sequência: a Meta verifica a **empresa** e depois analisa o **app**. Sem a primeira, a segunda não é analisada.

### Antes de pedir

- App no ar em domínio próprio com https (não em túnel temporário).
- Instagram real funcionando para uma conta testadora (Parte 1).
- **Política de Privacidade** e **Termos** públicos: já existem em `/privacidade` e `/termos`, mas como modelo. Preencha `frontend/src/lib/legal.ts` e revise com um advogado.

### Etapa 1: verificação da empresa

1. Crie ou abra a conta no **Meta Business** (<https://business.facebook.com>).
2. Vá em Configurações → **Central de segurança** → **Verificação da empresa**.
3. Envie o cartão CNPJ e um comprovante de endereço ou telefone da empresa.
4. Aguarde a resposta.

Como o app atende outros negócios (cada gestor conecta o próprio Instagram), a Meta o trata como "provedor de tecnologia" e pode pedir uma verificação extra de acesso. Ela aparece no painel se for exigida.

### Etapa 2: dados do app

No painel do app, em **Configurações → Básico**: ícone, categoria, URL da Política de Privacidade, URL de exclusão de dados, e o vínculo com a empresa verificada.

### Etapa 3: pedir as permissões

Em **Análise do app** → **Permissões e recursos**, peça **acesso avançado** para as quatro permissões (os textos sugeridos e o que mostrar em cada vídeo estão no [README](../README.md#fase-4-montar-o-pedido-do-app-review)):

| Permissão | Para que serve no app |
|---|---|
| `instagram_business_basic` | ler o perfil e os posts do gestor |
| `instagram_business_manage_comments` | ver quem comentou no post |
| `instagram_business_manage_messages` | receber as menções em story |
| `instagram_business_content_publish` | publicar post pelo app |

Para cada uma, a Meta pede:

1. **Um texto** explicando o uso. Exemplo: "O gestor cria uma campanha a partir de um post; lemos os comentários para dar pontos aos promoters que comentaram."
2. **Um vídeo da tela** mostrando o caminho completo: login no app → conectar o Instagram → a função usando aquela permissão.
3. **Um login de teste** para o revisor entrar no app, com instruções passo a passo.

Depois, responda o questionário de tratamento de dados e envie para análise.

### Etapa 4: publicar

Com a aprovação, mude o app para o modo **Ao vivo** no topo do painel. A partir daí qualquer empresa cria conta de gestor e conecta o próprio Instagram, sem cadastro de testador.

### Prazos típicos

| Etapa | Prazo |
|---|---|
| Verificação da empresa | 1 a 5 dias úteis |
| Análise do app | de alguns dias a 2 semanas |
| **Total** | **2 a 4 semanas** |

O que costuma atrasar:

- **CNPJ recém-aberto**: pode levar alguns dias para aparecer nas bases públicas que a Meta consulta. Espere uns dias antes de enviar.
- **Dados que não batem**: nome e endereço no Meta Business precisam ser idênticos aos do cartão CNPJ.
- **Reprovação do app**: quase sempre por vídeo pouco claro ou login de teste que não funcionou. Cada reenvio volta para a fila.

Como encurtar:

- Prepare o app, a Política de Privacidade e os vídeos enquanto a empresa é verificada.
- Peça só as quatro permissões que o app usa.
- No vídeo, mostre a tela de autorização do Instagram e o resultado dentro do app.
- Deixe o login de teste com uma campanha ativa já criada.

### Depois da aprovação

- A conta do Instagram de cada cliente precisa ser profissional.
- Cada gestor autoriza o app na tela de login do Instagram. A autorização dura 60 dias, e o app renova sozinho.
- A aprovação não é definitiva: a Meta pede uma revisão periódica do uso de dados e pode suspender o app que descumprir as políticas.

## Parte 3: e se eu não tenho empresa?

Sem CNPJ a Meta não aprova o app. Há três caminhos.

### 1. Usar sem aprovação

Ficar no modo de teste (Parte 1), com as limitações descritas. Serve para validar a ideia.

### 2. Abrir um CNPJ

O mais simples no Brasil é o **MEI**:

- Abertura gratuita e online em `gov.br/mei` ("Quero ser MEI" → "Formalize-se"). O CNPJ sai na hora.
- Exige conta gov.br nível prata ou ouro.
- Custo: uma guia mensal em torno de R$ 80 a R$ 90, que já inclui INSS e impostos (o valor muda todo ano), e uma declaração anual gratuita.
- Use só o site oficial `gov.br`. Existem sites parecidos que cobram por algo que é gratuito.

Pontos de atenção:

- O MEI só aceita atividades de uma lista fechada, e **desenvolvimento de software não está nela**. É preciso escolher uma atividade da lista que combine com o negócio, ou abrir uma ME no Simples Nacional. Converse com um contador antes.
- Há limite de faturamento anual, e o titular não pode ser sócio de outra empresa.
- Abrir MEI pode cortar benefícios como seguro-desemprego, e pode não ser permitido a servidores públicos.
- A Meta costuma aceitar MEI na verificação (é um CNPJ como qualquer outro), mas não há garantia.

### 3. Usar a empresa de um cliente ou sócio

Se o app é feito para uma casa noturna, marca ou agência que já tem CNPJ, o app na Meta pode ficar no nome dela: ela faz a verificação e adiciona você como desenvolvedor. É comum e permitido. O ponto de atenção é que o app passa a pertencer oficialmente a essa empresa.

## Fontes

- [Instagram Platform: App Review (Meta)](https://developers.facebook.com/documentation/instagram-platform/app-review)
- [Instagram Platform: visão geral (Meta)](https://developers.facebook.com/documentation/instagram-platform/overview)
- [Instagram Platform: webhooks (Meta)](https://developers.facebook.com/docs/instagram-platform/webhooks)
- [Menção em story (Meta)](https://developers.facebook.com/docs/messenger-platform/instagram/features/story-mention)
