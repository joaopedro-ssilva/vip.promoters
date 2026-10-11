# VIP Promoters — direção de design

Este documento e tokens.css são a especificação para um front em Next.js App Router, TypeScript, Tailwind CSS v4 e lucide-react, com componentes próprios. Nenhum app faz parte desta entrega. Interface, mensagens, rótulos e datas em PT-BR. As dimensões em px abaixo são equivalentes com 1rem = 16px; preservar a preferência de tamanho de fonte do navegador.

> **Notas de implementação.** Este documento é a especificação original de design. Onde ele e o produto divergem, vale o contrato em [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md). Diferenças conhecidas no que foi construído:
>
> - **Rotas**: a tela de login é `/entrar` (não `/login`); o promoter também tem `/promoter/ranking` e `/promoter/extrato`.
> - **Deixado de fora por não haver suporte na API**: "Esqueci minha senha", seletor de período na Visão geral (os indicadores usam janelas fixas de 7 e 30 dias), campo "instruções de retirada" nas recompensas e busca de campanhas no servidor.
> - **Ranking**: os períodos são "Últimos 7 dias", "Últimos 30 dias" (padrão) e "Todo o período", em vez de "Este mês".
> - **Campanha com início futuro** aparece como Ativa com a nota "Começa em DD/MM às HH:mm"; não há estado de agendada.
> - **Token extra `line-subtle`** (escuro `#333D2D`, claro `#D3DAC6`) para bordas de cards estáticos e divisórias; `line` fica para controles interativos.
> - **Título do hero** em desktop usa 4rem a partir de `lg` e 5rem a partir de `xl`, sem o limite de 9ch, que quebrava palavras ao meio.
> - **Ícone do Instagram**: a versão instalada do lucide não traz ícones de marca; usa-se `Camera`.
> - **Ações do detalhe da campanha** são botões visíveis, não um menu. Tema e conta ficam na barra superior do gestor, não no rodapé da sidebar.
> - **Pontos padrão**: 10 por comentário e 25 por menção em story; o gestor pode permitir mais de uma menção pontuada por pessoa (1 a 10).

## 1. Conceito: credencial de acesso

A identidade parte de uma credencial de evento: título condensado, faixa de pontos e linha perfurada.
Grafite esverdeado ocupa o fundo; lima indica ação e saldo; pêssego marca destaques editoriais.
Cards retangulares, números alinhados e bordas de 1px mantêm a leitura operacional do gestor.
O promoter vê participação e benefício com o mesmo vocabulário visual, sem roletas, confetes, brilhos, gradientes ou estética do Instagram.

Marca em texto: “VIP” em Barlow Condensed 700, 1.5rem/1, tracking 0.01em; “Promoters” em Manrope 700, 0.875rem/1.4, tracking 0. Marca horizontal com gap 8px. Ícone Ticket de 24px opcional à esquerda. Sem arquivo de logo. Linha perfurada: border-block-start: 1px dashed var(--line); só em saldo, credencial do hero e comprovante de resgate. Não recortar áreas clicáveis nem sobrepor decoração ao texto.

## 2. Cor e contraste

### Paleta semântica

Os dois papéis usam a mesma paleta. O gestor concentra accent em uma ação principal por seção; o promoter também o usa no saldo. Alternar tema não altera significado. Não usar cores arbitrárias, opacidade em texto nem cores padrão adicionais do Tailwind.

| Token semântico | Escuro (padrão) | Claro | Papel |
|---|---|---|---|
| canvas | #10130F | #F3F4EB | Fundo da página |
| surface | #181D16 | #FFFFFF | Nível 1: cards, campos, navegação e dialog |
| surface-raised | #22291F | #E8ECDD | Nível 2: blocos internos, badges, desabilitados |
| surface-hover | #2B3426 | #DDE5D0 | Nível 3: hover e pressionado de controles neutros |
| line | #728169 | #68765B | Bordas de controles, divisórias e ícones neutros (não texto) |
| ink | #F3F5EB | #192013 | Texto principal |
| ink-secondary | #CBD2C1 | #3F4E34 | Texto de suporte |
| ink-muted | #A5B39A | #536445 | Metadados, placeholder e texto desabilitado |
| accent | #D1F267 | #385900 | Ação principal, pontos e foco |
| accent-hover | #DDF789 | #2C4700 | Preenchimento primary em hover |
| accent-active | #B8DD4B | #213700 | Preenchimento primary pressionado |
| on-accent | #182008 | #FFFFFF | Texto/ícone sobre os três preenchimentos accent |
| accent-secondary | #F5AF82 | #8E4218 | Destaque editorial e segunda série do gráfico |
| success | #9FE0B2 | #23633D | Sucesso e aprovação |
| warning | #F3CE73 | #765400 | Pendência e atenção |
| danger | #FFABA5 | #A12627 | Erro, cancelamento e preenchimento destrutivo |
| danger-hover | #FFC1BC | #8B1D20 | Preenchimento danger em hover |
| danger-active | #F5948C | #721719 | Preenchimento danger pressionado |
| info | #9BCDEB | #255D7B | Informação e identificação pendente |
| on-danger | #32120F | #FFFFFF | Texto/ícone sobre os três preenchimentos danger |

focus é alias de accent nos dois temas, sem novo hex. Utilities correspondentes: bg-canvas, bg-surface, bg-surface-raised, bg-surface-hover, border-line, text-ink, text-ink-secondary, text-ink-muted, bg-accent, text-on-accent, text-accent-secondary, text-success, text-warning, text-danger, text-info e outline-focus.

**Combinações permitidas:** textos ink/ink-secondary/ink-muted e textos semânticos sobre os quatro fundos neutros da matriz; on-accent somente sobre accent/accent-hover/accent-active; on-danger somente sobre danger/danger-hover/danger-active. Badges usam fundo surface-raised e texto semântico. Não colocar texto sobre fotos, overlay translúcido, cor semântica diferente ou cor de série de gráfico. Links de texto usam accent, sublinhado persistente e o mesmo accent em hover; variantes hover/active de accent e danger destinam-se ao preenchimento dos botões. A seleção de texto usa on-accent/accent. Nenhuma foto precisa fornecer contraste: legenda e ações ficam em área neutra opaca.

### Auditoria WCAG calculada

Cálculo aplicado aos valores sRGB de 8 bits: normalizar canal c = valor/255; linearizar com c/12.92 se c ≤ 0.04045, senão ((c + 0.055)/1.055)^2.4. L = 0.2126R + 0.7152G + 0.0722B. Razão = (L maior + 0.05)/(L menor + 0.05). Valores abaixo arredondados a duas casas; validação usa valores completos. Matrizes enumeram todas as combinações permitidas, incluindo fundos de hover e variantes preenchidas.

**Escuro**

| Primeiro plano / fundo | canvas | surface | surface-raised | surface-hover |
|---|---:|---:|---:|---:|
| ink | 17.00:1 | 15.55:1 | 13.57:1 | 11.76:1 |
| ink-secondary | 12.06:1 | 11.03:1 | 9.63:1 | 8.34:1 |
| ink-muted | 8.48:1 | 7.76:1 | 6.77:1 | 5.87:1 |
| accent | 14.80:1 | 13.54:1 | 11.82:1 | 10.24:1 |
| accent-hover | 15.81:1 | 14.47:1 | 12.63:1 | 10.94:1 |
| accent-active | 12.02:1 | 11.00:1 | 9.60:1 | 8.31:1 |
| accent-secondary | 10.10:1 | 9.25:1 | 8.07:1 | 6.99:1 |
| success | 12.28:1 | 11.24:1 | 9.81:1 | 8.50:1 |
| warning | 12.38:1 | 11.33:1 | 9.88:1 | 8.56:1 |
| danger | 10.36:1 | 9.48:1 | 8.27:1 | 7.16:1 |
| danger-hover | 12.13:1 | 11.10:1 | 9.68:1 | 8.39:1 |
| danger-active | 8.46:1 | 7.75:1 | 6.76:1 | 5.86:1 |
| info | 10.98:1 | 10.05:1 | 8.77:1 | 7.60:1 |
| line | 4.51:1 | 4.13:1 | 3.60:1 | 3.12:1 |

**Claro**

| Primeiro plano / fundo | canvas | surface | surface-raised | surface-hover |
|---|---:|---:|---:|---:|
| ink | 15.07:1 | 16.70:1 | 13.90:1 | 12.88:1 |
| ink-secondary | 8.06:1 | 8.93:1 | 7.43:1 | 6.89:1 |
| ink-muted | 5.78:1 | 6.41:1 | 5.33:1 | 4.94:1 |
| accent | 7.30:1 | 8.09:1 | 6.73:1 | 6.24:1 |
| accent-hover | 9.44:1 | 10.46:1 | 8.70:1 | 8.06:1 |
| accent-active | 11.76:1 | 13.03:1 | 10.85:1 | 10.05:1 |
| accent-secondary | 6.44:1 | 7.14:1 | 5.94:1 | 5.50:1 |
| success | 6.48:1 | 7.18:1 | 5.98:1 | 5.54:1 |
| warning | 6.24:1 | 6.91:1 | 5.75:1 | 5.33:1 |
| danger | 6.72:1 | 7.44:1 | 6.19:1 | 5.74:1 |
| danger-hover | 8.26:1 | 9.15:1 | 7.62:1 | 7.06:1 |
| danger-active | 10.23:1 | 11.34:1 | 9.43:1 | 8.74:1 |
| info | 6.47:1 | 7.17:1 | 5.96:1 | 5.53:1 |
| line | 4.38:1 | 4.85:1 | 4.03:1 | 3.74:1 |

**Textos e ícones em superfícies preenchidas**

| Texto / fundo | Escuro | Claro |
|---|---:|---:|
| on-accent / accent | 13.30:1 | 8.09:1 |
| on-accent / accent-hover | 14.20:1 | 10.46:1 |
| on-accent / accent-active | 10.79:1 | 13.03:1 |
| on-danger / danger | 9.45:1 | 7.44:1 |
| on-danger / danger-hover | 11.07:1 | 9.15:1 |
| on-danger / danger-active | 7.73:1 | 11.34:1 |

Cada célula das matrizes, exceto a linha line, supera 4.5:1. line é exclusivamente borda/divisória/ícone não textual e supera 3:1 em todos os fundos: mínimo 3.12:1 no escuro e 3.74:1 no claro. Menor contraste de texto neutro: ink-muted/surface-hover, 5.87:1 escuro e 4.94:1 claro. Texto de ação preenchida também supera 4.5:1 em todos os estados. Mesmo texto grande segue 4.5:1. Ícones informativos herdam a cor do texto. Foco accent usa intervalo de 3px revelando fundo neutro, e seu mínimo é 10.24:1 escuro / 6.24:1 claro contra esse fundo; não usar o anel sobre imagens. Desabilitados mantêm texto opaco ink-muted em surface-raised (6.77:1 / 5.33:1).

Scrim e sombras são as únicas transparências de cor. Scrim: rgb(0 0 0 / 0.64) no escuro e rgb(0 0 0 / 0.40) no claro; nenhum conteúdo legível fica sobre ele. O dialog acima permanece opaco em surface. Durante a curta entrada de um dialog/toast pode haver transição de opacidade; o estado final sempre usa estas cores opacas.

## 3. Tipografia

**Display:** Barlow Condensed, pesos 600 e 700. **Corpo:** Manrope, pesos 400, 500, 600, 700 e 800. Ambas livres sob SIL Open Font License: [Barlow Condensed](https://github.com/google/fonts/blob/main/ofl/barlowcondensed/OFL.txt) e [Manrope](https://github.com/google/fonts/blob/main/ofl/manrope/OFL.txt).

Importar Barlow_Condensed e Manrope de next/font/google; Barlow_Condensed com weight ["600", "700"], subsets ["latin"], display "swap", variable "--font-display"; Manrope variável com subsets ["latin"], display "swap", variable "--font-body". Aplicar **as duas classes .variable no html**, junto de lang="pt-BR" e data-theme. Fontes são servidas pelo próprio Next após build; não adicionar CDN, @import de fontes ou imagens externas. O alias Tailwind font-heading referencia --font-display; font-sans referencia --font-body. Não criar --font-display: var(--font-display), pois isso forma ciclo. A integração segue [next/font](https://nextjs.org/docs/app/api-reference/components/font).

| Utility / uso | Família | rem | Peso | Line-height | Tracking |
|---|---|---:|---:|---:|---:|
| text-caption / legenda e metadados | Manrope | 0.75 | 500 | 1.5 | 0.01em |
| text-label / botão, label, navegação, tabela | Manrope | 0.875 | 600 | 1.428571 | 0em |
| text-body / parágrafo e campo | Manrope | 1 | 400 | 1.5 | 0em |
| text-lead / introdução de página pública | Manrope | 1.125 | 500 | 1.555556 | 0em |
| text-section / título de seção | Barlow Condensed | 1.5 | 600 | 1.166667 | 0.01em |
| text-page / título de página até 1023px | Barlow Condensed | 2 | 600 | 1.125 | 0.01em |
| text-page-wide / título a partir de 1024px | Barlow Condensed | 2.5 | 600 | 1.1 | 0.01em |
| text-balance / saldo em destaque | Manrope | 3 | 800 | 1 | -0.02em |
| text-hero / título do hero até 1023px | Barlow Condensed | 3.5 | 700 | 0.98 | -0.01em |
| text-hero-wide / hero a partir de 1024px | Barlow Condensed | 6 | 700 | 0.98 | -0.01em |

Utilitários de tamanho não escolhem família: sempre combinar font-heading nos títulos e font-sans nos números. KPIs e posição no ranking: Manrope 800, 2rem/1.125, tracking -0.02em, usando text-page font-sans font-extrabold tracking-[-0.02em]. Nomes de cards usam Manrope 700, 1rem/1.5. Corpo em 400, ênfase em 600, nunca peso sintético. Caixa alta só na marca VIP e pequenas etiquetas editoriais (text-caption, tracking 0.08em); títulos e botões em caixa de frase. Largura de parágrafo até 60ch.

Todo saldo, custo, pontuação, KPI, posição, data tabular e código usa **tabular-nums** (font-variant-numeric: tabular-nums). “1.250 pontos”, “+25 pontos”, “−100 pontos”, “6º lugar”; sem abreviação “pts” e sem símbolo de moeda. Valores grandes quebram linha entre número e “pontos”; nunca cortar o número. Códigos alfanuméricos usam Manrope 700 com tracking 0.08em, em vez de introduzir terceira fonte.

## 4. Geometria, elevação e adaptação

- Base de espaçamento: --spacing = 0.25rem (4px). Escala autorizada: 0, 1, 2, 3, 4, 6, 8, 10, 11, 12, 14, 16, 18, 20 e 24 unidades = 0, 4, 8, 12, 16, 24, 32, 40, 44, 48, 56, 64, 72, 80 e 96px. Gap ícone/texto 8px; label/campo 8px; campo/ajuda 4px; campos 24px; cards 16px; seções 32px.
- Página: gutter 16px abaixo de md, 24px de md a lg, 32px a partir de lg. Card: padding 16px mobile, 24px a partir de md; cards densos de listas e recompensa ficam em 16px. Landing: seções com padding-block 48px mobile e 80px a partir de lg.
- Raios: radius-control 0.5rem (8px); radius-card 0.75rem (12px); radius-panel 1rem (16px); radius-pill 9999px. Controles/botões 8px, cards 12px, dialog/credencial 16px, avatar/chip/badge pill.
- Traço default 1px, ênfase 2px. Lucide: 16px auxiliar, 20px padrão, 24px navegação; strokeWidth 1.75. Não usar emoji como ícone.
- Container max-auth 28rem (448px); reading 40rem (640px); form 48rem (768px); promoter 64rem (1024px); site 75rem (1200px); workspace 90rem (1440px). Esses limites incluem padding e usam width: 100%; margin-inline: auto. O limite workspace aplica-se ao conteúdo à direita da sidebar.
- Breakpoints mobile-first: sm 40rem (640px), md 48rem (768px), lg 64rem (1024px), xl 80rem (1280px), 2xl 96rem (1536px). Sem consultas por tipo de dispositivo.
- Gestor em lg+: sidebar 15rem (240px), coluna restante minmax(0, 1fr), top bar 4rem (64px). Em <lg: sidebar vira drawer, página ocupa toda a largura. Promoter em <md: bottom bar 4.5rem (72px) + safe area; em md+: navegação no topo e nenhum espaço reservado inferior.
- Conteúdo com bottom bar: padding-bottom calc(var(--tabbar-height) + env(safe-area-inset-bottom) + 1rem), inicialmente 72px + safe area + 16px. Se texto/zoom fizer barras crescerem, medir com ResizeObserver e atualizar --topbar-height no html para a altura total da top bar e --tabbar-height para a altura da bottom bar menos seu padding inferior de safe area; restaurar 64px/72px ao desmontar o shell. Assim, offsets de foco, toast e conteúdo usam a mesma altura real, sem contar safe area duas vezes. Drawer ocupa min(20rem, calc(100% - 2rem)); dialog width min(30rem, calc(100% - 2rem)), editor largo min(48rem, calc(100% - 2rem)); max-height calc(100dvh - 2rem), overflow-y auto.
- z-index: base 0, sticky 20, nav 30, popover 40, scrim 50, dialog 60, toast 70, skip 80. Dropdown dentro de dialog integra o mesmo dialog para permanecer na camada superior; preferir select nativo.
- Páginas e cards estáticos não precisam de sombra. Card elevado usa shadow-card; popover shadow-popover; dialog/drawer shadow-dialog. Elevação não muda em hover.

| Token | Geometria | Alfa preto escuro | Alfa preto claro |
|---|---|---:|---:|
| shadow-card / elevation-card | 0 2px 8px | 0.16 | 0.06 |
| shadow-popover / elevation-popover | 0 8px 24px | 0.24 | 0.12 |
| shadow-dialog / elevation-dialog | 0 24px 64px | 0.40 | 0.18 |

Sombras usam rgb(0 0 0 / alfa), sem alterar as cores das superfícies. Todos os flex/grid filhos textuais recebem min-width: 0; tracks usam minmax(0, 1fr). Evitar width: 100vw. Sem largura mínima de página e sem overflow-x: hidden para esconder defeitos.

## 5. Componentes e estados

### Contrato comum de estados

Todo controle recebe default, hover só em @media (hover: hover), focus-visible com anel 2px accent e offset 3px, active enquanto pressionado, disabled e loading conforme abaixo. Hover nunca revela a única forma de executar uma ação. Botões e links têm alvo mínimo 44×44px, mesmo com ícone de 16px. Não remover outline, reduzir opacidade do controle, escalar cards ou deslocar botões.

**Disabled comum:** surface-raised + ink-muted + borda line, cursor not-allowed, sem hover/active e sem spinner; usar disabled nativo. Se for necessário que a ação bloqueada seja encontrável por teclado, usar aria-disabled="true", manter foco e impedir handler. Motivo em texto adjacente, nunca só tooltip. **Loading comum:** manter dimensões e label de ação (“Salvando…”, “Sincronizando…”), substituir ícone por LoaderCircle 16px, aria-busy="true"; impedir nova submissão, manter foco no disparador. Não mover foco para o spinner. Usar aria-disabled durante carregamento se disabled nativo retiraria o foco.

Elementos só informativos (badge, avatar, KPI, skeleton, empty state, chip) não recebem hover/focus/active/disabled; não entram na ordem de Tab. Seus botões/links internos seguem o contrato. Não tornar um card inteiro clicável quando contém checklist, menu ou outro botão. Navegação ativa/aba selecionada é estado persistente, diferente de active pressionado.

### Button

Alturas mínimas: sm 44px/padding-inline 12px; md 48px/16px; lg 56px/24px. Todos com text-label 600, gap 8px, borda 1px e radius-control. Icon-only 44×44px, ícone 20px, nome acessível; toolbar pode usar 48×48px. Texto pode quebrar linha em zoom; altura é mínima, nunca teto.

| Variante | Default | Hover | Active pressionado |
|---|---|---|---|
| primary | accent + on-accent; borda accent | accent-hover + on-accent; borda accent-hover | accent-active + on-accent; borda accent-active |
| secondary | surface + ink; borda line | surface-hover + ink; borda line | surface-raised + ink; borda accent |
| ghost | transparente sobre fundo neutro + ink-secondary; borda transparente | surface-hover + ink | surface-raised + ink; borda line |
| danger | danger + on-danger; borda danger | danger-hover + on-danger; borda danger-hover | danger-active + on-danger; borda danger-active |

Focus/disabled/loading seguem o contrato; loading mantém as cores default de cada variante. Primary para única ação de avanço, secondary para alternativa, ghost para ação contextual, danger só para confirmação destrutiva. Link que navega é elemento a; ação é button. “Abrir no Instagram” é secondary com ExternalLink e indicação acessível “abre em nova aba”, target _blank e rel noopener noreferrer.

### Input, Textarea e Select

Label externo text-label, campo surface/ink, placeholder ink-muted, borda line 1px, raio 8px. Input/select min-height 48px e padding 12px; textarea min-height 128px, padding 12px, resize vertical. Fonte do campo 1rem para evitar zoom involuntário mobile. Select nativo com opções em PT-BR; seta no espaço reservado de 24px, sem sobrepor texto.

Hover: borda ink-muted; focus-visible: anel comum e borda accent; active: preserva foco. Disabled: contrato comum; readonly: aparência default, atributo readonly e descrição “Somente leitura”, foco/cópia permitidos. Loading de opções: aria-busy, campo indisponível e “Carregando opções…” em ajuda. Inválido: borda danger, CircleAlert 16px + erro text-label/danger abaixo, aria-invalid e aria-describedby. O foco continua accent, não some por estar inválido. Label “(opcional)” nos opcionais, sem depender de asterisco. Ícones decorativos dentro dos campos não capturam clique.

### Card

Surface, borda line 1px, raio 12px, padding 16/24px, sem sombra por padrão. Subdivisão em surface-raised com raio 8px. Card estático não reage a ponteiro. Card de seleção único: button/radio com default surface, hover surface-hover, active surface-raised, selected borda accent 2px + Check + “Selecionado”, foco comum; reservar a borda de 2px desde o início com faixa interna para não deslocar layout. Disabled e loading comuns; conteúdo carregando mantém skeleton na área. Grupo de escolha de papel/post usa radio sem envolver outros controles.

### Badge de status

Inline-flex, min-height 28px, padding 4px 8px, gap 4px, raio pill, fonte caption, fundo surface-raised, borda line 1px, ícone 16px. Não clicável; texto sempre presente. Não confundir badge com botão de filtro.

| Label visível | Cor de texto/ícone | Lucide |
|---|---|---|
| Pendente | warning | Clock3 |
| Aprovado | success | CircleCheck |
| Ativo | accent | Radio |
| Encerrado | ink-secondary | Flag |
| Rascunho | ink-muted | FilePenLine |
| Pontuou | success | BadgeCheck |
| Duplicado | warning | Copy |
| Não identificado | info | UserRoundSearch |
| Cumprido | success | PackageCheck |
| Cancelado | danger | CircleX |

Usar “Ativa”/“Encerrada” quando o rótulo acompanha explicitamente “Campanha”; mesmos tokens. Sincronização “Aguardando verificação” usa info/Clock3. Badge não tem loading próprio: operação mostra estado ao lado, mantendo o status anterior até confirmação. Nunca exibir cor sem label.

### Tabela

Desktop a partir de md: table semântica, caption acessível, cabeçalho surface-raised text-label ink-secondary com min-height 44px; linhas surface min-height 64px, padding de célula 12px 16px, separação line 1px. Números à direita e tabular-nums; nomes à esquerda. Linha pode crescer. Hover de linha surface-hover apenas quando há ação. Linha selecionada surface-raised + checkbox marcado; foco vai a controles internos, não à linha.

Ordenação em button no th, ícone 16px e aria-sort; direção dita em PT-BR. Não limitar ações ao hover. Disabled/loading de controles seguem contrato; carregamento inicial mostra cinco linhas skeleton e aria-busy na região; atualização preserva linhas anteriores com texto “Atualizando…”. Empty ocupa a região inteira. Paginação de 20 itens com “Anterior”, “Próxima” e “1–20 de 48”; min-height 44px, quebra em duas linhas quando necessário.

Abaixo de md todas as tabelas deste produto viram lista de cards com pares label/valor e ações no rodapé. Não duplicar conteúdo na árvore de acessibilidade. Exceção futura para comparação densa: overflow-x auto só em região identificada e focável; nenhuma tabela desta especificação depende dessa exceção.

### Tabs

Min-height 48px, padding 12px 16px, text-label. Default ink-secondary sobre surface, hover surface-hover, pressed surface-raised; selected ink + borda inferior accent 2px + aria-selected. Focus comum, disabled contrato, loading preserva a aba e exibe skeleton no painel. Em grupos reais de abas: role tablist/tab/tabpanel, setas, Home/End e foco roving; ativação manual por Enter/Espaço para painéis remotos. Filtros de campanha são buttons aria-pressed, não tabs falsas. No mobile tabs quebram em duas linhas; acima de quatro opções, substituir por select com label “Visualização”, sem carrossel horizontal.

### Modal / Dialog

Surface opaca, borda line, raio 16px, padding 24px desktop e 16px mobile, shadow-dialog. Scrim conforme tokens; largura de confirmação até 480px e editor até 768px, limitada à viewport como seção 4. H2 text-section, descrição text-body ink-secondary, gap 16px; footer gap 12px com secundário primeiro e ação confirmadora depois. No mobile ações em coluna, largura total, confirmar por último. Botão X com 44px e label “Fechar”.

Usar dialog modal nativo ou implementação equivalente com nome/descrição, foco contido, fundo inerte, Escape e retorno de foco. Em destruição, foco inicial em “Voltar”; em formulário no primeiro campo. Dialog não tem hover/active/disabled próprios. Loading durante envio mantém aberto, dados e label; confirmação não pode disparar duas vezes. Escape/fechar ainda fecha a visualização e não cancela silenciosamente transação já enviada; resultado aparece na página. Clique no scrim só fecha dialog informativo sem dados; formulário exige “Descartar alterações?” se sujo. Erro permanece inline; não fechar em erro. Validar todas as falhas antes de movimentar foco para o primeiro erro.

### Toast

Surface, borda line, faixa esquerda 3px success/info/warning/danger, texto ink e ícone da mesma cor semântica, raio 12px, shadow-popover, padding 16px, largura min(24rem, calc(100% - 2rem)). Desktop: canto superior direito a 80px do topo e 24px da direita. Mobile: acima da bottom bar a calc(4.5rem + env(safe-area-inset-bottom) + 1rem), margem 16px; em páginas sem bottom bar, 16px + safe area. Máximo três toasts, empilhamento com gap 8px.

Sucesso/info 6s, pausar temporizador em hover/foco; erros e toasts com ação persistem até fechar. role status/polite para confirmação; role alert apenas falha imediata. Não mover foco. Fechar/action têm alvo 44px e estados ghost/secondary. Toast não possui disabled/loading; operação em andamento fica na origem. Em barras que crescerem por zoom, substituir os offsets iniciais de 80px e 4.5rem por calc(var(--topbar-height) + 1rem) e var(--tabbar-height), respectivamente. Ao fechar modal nativo, emitir toast após o fechamento para ficar na região ativa; enquanto aberto, mostrar feedback dentro dele.

### Empty state e Skeleton

Empty: região surface sem borda extra dentro de card, padding 32px 16px, ícone 32px em ink-muted, h3 text-section, descrição text-body até 40ch e uma ação md após 16px. Texto alinhado ao centro em listas vazias; alinhado à esquerda em blocos de onboarding. Sem ilustração externa. Não tem estados interativos próprios; ação herda Button. Diferenciar “Sem dados”, “Nenhum resultado” e “Não foi possível carregar”; erro inclui “Tentar novamente”.

Skeleton: blocos surface-raised, raio 8px, animação animate-skeleton até surface-hover em 1400ms; não usar brilho viajante. Texto: barra 12px de altura, duas larguras de 75%/50%, gap 12px. Thumb usa mesmo aspect-ratio final. aria-hidden em cada bloco, uma única mensagem sr-only “Carregando…” em região aria-busy. Sem foco/hover/active/disabled. Com reduced-motion, superfície estática. Dados desconhecidos são “—”, nunca zero fabricado.

### Avatar e KPI / stat tile

Avatar 32/40/48px, círculo, surface-raised, borda line, iniciais em ink-secondary, Manrope 700, 0.75/0.875/1rem respectivamente. Sem URL externa de placeholder. Imagem real só a fornecida pela conta quando houver integração; alt vazio se nome ao lado, senão nome completo. Estado ausente/erro retorna iniciais; loading usa círculo skeleton. Não interativo; se abrir perfil, fica dentro de link com área 44px e foco comum.

KPI: card com label text-label ink-secondary, valor Manrope 800 2rem tabular-nums, gap 8px, ajuda text-caption ink-muted. Ícone 20px à direita do label, cor ink-secondary. Variação positiva success + ArrowUp, negativa danger + ArrowDown, acompanhadas por “em relação ao período anterior”; mostrar só se há comparação real. Tiles sem destino não têm hover/foco/active/disabled; eventual link “Ver detalhes” usa ghost. Loading skeleton de valor e ajuda, erro “Indisponível” + ação tentar novamente. Sem contadores animados.

### Card de campanha

Surface, line, raio 12px, padding 16px, gap 12px. Gestor em grade: thumb aspect-ratio 4/3, width 100%, raio 8px, object-fit cover; badge e datas fora da imagem, título de até duas linhas, @ da conta, totais e link “Ver campanha”. Promoter: thumb quadrada de 88px ao lado de título/status, coluna textual minmax(0,1fr), checklist e CTA ocupam toda a largura abaixo. Em zoom/texto longo, thumb pode passar acima do título, sem comprimir texto abaixo de 160px.

Checklist é informativo, não input editável: “Comentar no post” e “Mencionar no story”, pontos à direita, Circle antes de verificar, CircleCheck/success quando Pontuou, Clock3/info enquanto aguarda. Ícone 20px; linha min-height 44px; label/pontos podem quebrar. Repetição não soma pontos; status “Duplicado” com ajuda. Abrir Instagram não marca ação como concluída.

Card não muda com hover; só controles internos. Campanha encerrada mantém leitura, badge e datas; CTA “Campanha encerrada” desabilitado com motivo. Loading reserva thumb e três linhas; erro de thumb mostra bloco surface-raised com Image 24px e texto “Publicação”, sem imagem remota substituta. Rascunho só aparece ao gestor.

### Card de recompensa

Surface/line, raio 12px, padding 16px, thumb opcional 4/3; sem foto, bloco surface-raised com Ticket, Gift ou GlassWater 32px e nome textual fora. Nome text-body 700, descrição text-label 400 até três linhas, chip de custo, estoque text-caption. Ações alinhadas no fim por flex-column; min-height automático. Gestor: “Editar” secondary e botão contextual ghost “Mais ações” com excluir. Promoter: “Resgatar” primary de largura total.

Hover/active só nas ações. Estoque zero: badge ink-secondary “Esgotado”, CTA disabled; saldo insuficiente: “Faltam 60 pontos” e CTA disabled. Nunca reduzir opacidade do card. Loading usa skeleton, envio trava apenas CTA selecionado. Confirmar em dialog com custo, saldo atual, saldo após resgate e quantidade 1. Sucesso exibe código e link “Ver meus resgates”; falha preserva saldo visual confirmado anteriormente e informa atualização necessária.

### Item de ranking e chip de pontos

Ranking vertical, linha surface de min-height 72px, padding 12px 16px, borda inferior line, gap 12px: posição com largura 40px e fonte Manrope 800 2rem, avatar 40px, nome/@ flexível, pontos tabulares à direita. Top 1: posição e Trophy accent; top 2: posição e Medal accent-secondary; top 3: posição e Medal info. Todos sobre fundo neutro, com ordinal “1º”, “2º”, “3º”; não usar podium que mude ordem de leitura. Linha do usuário usa surface-raised e label “Você”. No mobile pontos vão abaixo do nome se necessário. Só nome com destino é link; hover/foco/active nele, demais estados sem interação. Loading cinco linhas, vazio sem premiar posições inexistentes.

Chip: surface-raised, texto accent, Ticket 16px, gap 4px, raio pill, padding 4px 8px, min-height 28px, text-label 600 tabular-nums. Exemplo “+25 pontos”. Para débito text-ink-secondary e “−100 pontos”, nunca só vermelho. Chip não é botão e não tem estados interativos; loading fica no bloco pai.

### Sidebar do gestor

Largura 240px, bg-surface, borda direita line 1px, height 100dvh, sticky top 0 e rolagem vertical própria se necessário. Padding 16px; marca no topo, seletor de organização de 48px, navegação com gap 4px, conta/tema no rodapé. Ordem: Visão geral (LayoutDashboard), Campanhas (Megaphone), Equipe (Users), Ranking (Trophy), Lojinha (Gift), Resgates (Ticket), Instagram (Instagram), Configurações (Settings). “Nova campanha” é ação dentro de Campanhas, não item adicional.

Itens min-height 44px, padding 12px, gap 12px, raio 8px, ink-secondary. Hover surface-hover; pressed surface-raised; rota ativa surface-raised + texto ink + marcador esquerdo accent 2px + aria-current="page". Foco comum. Contadores em chip com número e nome acessível (“Resgates, 3 pendentes”). Itens não ficam disabled só por carregar; skeleton apenas no nome da organização. Em <lg, botão Menu 44px abre drawer modal com mesma ordem, scrim e fechamento após navegação; não deixar sidebar compacta ocupando espaço.

### Bottom tab bar do promoter

Somente <md: fixa, surface, borda superior line, z-nav, altura mínima 72px + safe area inferior; grid de **cinco** colunas minmax(0,1fr), sem itens com largura fixa. Início (House), Campanhas (Megaphone), Lojinha (Gift), Resgates (Ticket), Perfil (UserRound). Rótulo visual “Resgates”, título da página “Meus resgates”. Extrato acessível pelo saldo no Início e pelo Perfil.

Ícone 24px + label Manrope 500 0.75rem/1.5, gap 4px; área clicável de toda a célula, min-height 56px. Em 320px, cada célula tem 64px; rótulo pode quebrar e bar crescer em zoom, com reserva inferior ajustada à altura real. Default ink-secondary; ativo accent + traço superior 2px + aria-current; hover surface-hover; pressed surface-raised; foco comum com outline-offset -3px sobre surface. Sem itens disabled/loading por requisição de tela. Badge contador só para resgates pendentes, com label acessível; não sobrepor rótulo. Em md+, estes cinco destinos viram navegação horizontal na top bar, quebrando em nova linha se necessário.

### Top bar

Surface, borda inferior line 1px, altura mínima 64px, sticky top 0, z-sticky, padding-inline igual ao gutter. Gestor: Menu em <lg, breadcrumb visível a partir de md, organização quando mobile, tema icon-only, avatar/menu de conta. Promoter: nome da equipe ativa + seletor, tema e avatar; navegação em segunda linha em md+ se faltar espaço. Público: marca à esquerda, “Entrar” ghost e “Criar conta” primary à direita; em <sm manter só “Entrar” no header e CTA de cadastro no hero.

Título da página fica no conteúdo, não duplicado na barra mobile. Cada ação segue Button, seletor segue Select; carregamento da equipe usa skeleton de 120×16px sem desabilitar sair/navegar. Default surface, sem hover/active na barra inteira. Mudança de tema é botão com nome “Ativar tema claro” ou “Ativar tema escuro”, sem animar todas as cores da página.

## 6. Layout e conteúdo por tela

### Regras de produto que orientam as telas

- Gestor administra uma organização por vez; promoter pode participar de várias equipes. Equipe ativa aparece sempre no topo. Campanhas, ranking, loja, saldo e extrato são isolados por equipe; trocar equipe atualiza todos juntos, sem misturar pontos.
- Cadastro de gestor não equivale a Instagram conectado. Conexão e permissões são etapas próprias; campanhas rascunho podem ser salvas antes de conectar, publicação/disparo exigem conexão pronta.
- Convite solicita entrada, com status Pendente até aprovação. Promoter pendente vê nome da equipe e aviso “Sua entrada está em análise”; campanhas, resgates e pontuação dessa equipe só liberam após aprovação. Pode acessar Perfil e sair da conta.
- Regra fixa solicitada: **no máximo um comentário pontuado por promoter em cada campanha**. Decisão de produto para stories: **no máximo uma menção em story pontuada por promoter em cada campanha**. Repetições aparecem como Duplicado e valem zero. Defaults ao criar: comentário 10 pontos, story 25 pontos; gestor define inteiros positivos antes de ativar e pode desligar uma ação. Deve existir ao menos uma ação habilitada. Limites aparecem no formulário e nos cards, não em tooltip.
- Só participação verificada, da conta identificada, de promoter aprovado e dentro do período pode pontuar. “Abrir no Instagram”, “Já participei” ou sincronizar não dão pontos por si. Não incluir botão de autodeclaração de conclusão. Se API/dado não estiver disponível, mostrar pendência ou indisponibilidade, sem simular sucesso.
- Estados de campanha: Rascunho → Ativa no início do período → Encerrada no fim. Rascunho com envio confirmado para data futura recebe ajuda “Agendada para DD/MM às HH:mm” sem inventar badge de status adicional. “Disparar campanha” a disponibiliza internamente aos promoters aprovados da equipe; não implica envio de DM, WhatsApp ou e-mail. A lista registra “Envio agendado” ou “Disponível para a equipe”.
- Período usa America/Sao_Paulo; rótulo “Horário de Brasília”. Fim estritamente posterior ao início. Após ativar, post, pontos, ações e início ficam bloqueados; título e fim podem ser editados, sem retroagir sobre pontos já concedidos. “Encerrar campanha” pede confirmação e não apaga histórico.
- Saldo é pontos disponíveis. Ranking usa pontos ganhos no período, sem descontar resgates; desempate por momento em que alcançou a pontuação (mais cedo primeiro) e depois nome em ordem alfabética. Padrão “Este mês”; início/fim do filtro ficam visíveis.
- Cada resgate reserva uma unidade e debita pontos após confirmação do servidor. Status Pendente → Cumprido ou Cancelado; cumprir não debita outra vez; cancelar devolve pontos e estoque uma única vez. Apenas gestor cumpre/cancela pendentes. Código de retirada estável no formato VIP-7K2M9Q, ilustrativo, gerado pelo serviço; nunca gerar código de exemplo para transação real.
- Integração pode retornar sem conexão, conectada, sincronizando, permissão insuficiente, expirada ou erro temporário. UI diferencia esses casos e mostra última atualização confirmada. Não prometer leitura de todo story, publicação ou sincronização em tempo real: representar a capacidade entregue pelo serviço. Histórico não desaparece quando conexão falha.
- Protótipo/estado sem dados usa iniciais, blocos CSS e ícones Lucide. Não baixar imagens, usar URLs de mock, banco de imagens, logo do Instagram ou assets pagos. O produto implementado poderá exibir o post/recompensa real fornecido pelo usuário/integração; nenhuma mídia real faz parte desta entrega.

### 6.1 Landing — /

Header público, container site. Hero com grid 7/5 colunas a partir de lg, gap 48px, padding-block 80px; abaixo de lg empilhar, gap 32px, padding-block 48px. Coluna esquerda: etiqueta “Divulgação que vira benefício”; h1 em três linhas de intenção “Sua equipe divulga. / A participação / vira recompensa.”, text-hero/text-hero-wide, largura até 9ch em desktop (permitir redistribuição natural das palavras no mobile); parágrafo “Organize campanhas, acompanhe participações e recompense seus promoters.” até 38ch; CTAs “Sou gestor” primary e “Sou promoter” secondary, lg, lado a lado a partir de sm e empilhados abaixo.

Coluna direita: **uma credencial construída em HTML/CSS**, sem imagem, vídeo, canvas ou WebGL: surface, raio 16px, borda line, largura 100%, max-width 400px, padding 24px, sem rotação. Cabeçalho “VIP Promoters” e etiqueta “Exemplo”; bloco accent com on-accent, raio 8px, padding 16px, “Seu saldo” e “350 pontos” em Manrope 800 3rem; linha perfurada 24px abaixo; duas linhas “Comentário verificado · +10 pontos” e “Menção verificada · +25 pontos”; rodapé “Próximo benefício” e “Entrada VIP · 300 pontos”. Dados explícitos de demonstração, aria-label “Exemplo ilustrativo de saldo”; nenhuma CTA simulada dentro. Sem códigos de barra falsos. A credencial é o único elemento ilustrativo e fica dentro do fluxo.

A seguir, “Como funciona” com três colunas em md+ e lista vertical abaixo: 01 “Conecte e convide” (gestor conecta a conta; promoter entra por código), 02 “Publique e participe” (campanha por post; ações no Instagram), 03 “Confira e recompense” (interações verificadas, pontos e loja). Numerais Manrope 800 2rem, cores accent, accent-secondary, info respectivamente.

Benefícios em duas colunas md+ e uma abaixo: “Para quem organiza” com controle de campanhas, equipe e resgates; “Para quem divulga” com instruções de participação, saldo e benefícios. Máximo três itens por coluna, ícones 20px. CTA final em surface-raised com h2 “Sua próxima campanha começa aqui.” e “Criar conta” primary. Footer com marca e “Entrar”; não inserir preços, depoimentos, logos, métricas inventadas ou links sem destino.

### 6.2 Login — /login

Container auth centralizado com padding vertical 48px, sem altura fixa. Marca → h1 “Entrar” → texto → e-mail → senha com botão Mostrar/Ocultar 44px → primary “Entrar” full-width → “Criar conta”. Campo senha autocomplete current-password; e-mail autocomplete email. Sem login social inventado. Link “Esqueci minha senha” abre dialog interno que pede e-mail e confirma “Se houver uma conta com este e-mail, enviaremos as instruções.”; não inserir href vazio. Este fluxo é especificação de interface, requer serviço na implementação.

Elemento dominante é o formulário. Erro de credencial no topo do form, sem revelar qual campo está correto. Loading “Entrando…”. Preservar destino/código de convite ao autenticar. Mobile: gutter 16px, card sem margem extra, teclado pode rolar a página; ação não fixa sobre os campos.

### 6.3 Cadastro — /cadastro

Container form. Passo 1 “Como você vai usar o VIP Promoters?”: dois radio-cards iguais, lado a lado em md+; empilhados no mobile. “Sou gestor — Organizo campanhas e recompensas” com Users; “Sou promoter — Divulgo e troco pontos por benefícios” com Ticket. Nenhum pré-selecionado em acesso direto; link do hero pode selecionar pelo parâmetro papel=gestor/promoter. “Continuar” desabilitado até selecionar.

Passo 2 em container auth, com voltar: nome, e-mail, senha (ajuda de requisitos fornecidos pelo serviço); gestor adiciona “Nome da organização”; promoter adiciona “Seu @ do Instagram” e “Código da equipe (opcional)”. Código presente no convite permanece preenchido. Labels e senha em 16px, autocomplete new-password. CTA “Criar conta”. Gestor segue Visão geral com onboarding Instagram; promoter com código válido segue equipe pendente; sem código segue Perfil com campo entrar em equipe. Formulário não solicita senha do Instagram nem token manual. Mobile permanece coluna única; indicador textual “Etapa 1 de 2”/“Etapa 2 de 2”, sem stepper horizontal largo.

### 6.4 Convite — /convite/[codigo]

Container auth com marca, avatar/iniciais de equipe 48px, h1 “Entre para a equipe [nome]”, @ da conta e explicação de aprovação. Código em surface-raised com quebra segura e botão copiar 44px. Sem login: primary “Criar conta e solicitar entrada” + secondary “Já tenho conta”, preservando código. Autenticado promoter: “Solicitar entrada”; após envio, painel Clock3/warning “Solicitação enviada. Aguarde a aprovação do gestor.” Autenticado gestor: explicar “Este convite é para uma conta de promoter.” e oferecer “Entrar com outra conta”, sem mudar papel silenciosamente.

Código inválido/expirado: empty “Este convite não está disponível” e instrução “Peça um novo link ao gestor”, com “Ir para o início” apontando para a home adequada. Membro aprovado: “Você já faz parte desta equipe” + “Abrir equipe”. Pendente: reexibir status, impedir solicitação duplicada. Mobile: credencial ocupa largura disponível, sem código estourar a viewport.

### 6.5 Gestor / Visão geral — /gestor

Topo com h1 “Visão geral”, período select padrão “Últimos 7 dias” e primary “Nova campanha”. Se sem conexão, banner surface-raised + info antes dos KPIs, “Conecte o Instagram para começar”, com “Conectar Instagram”. KPI grid 4 colunas em xl+, 2 em sm+, 1 abaixo: Campanhas ativas, Promoters aprovados, Interações pontuadas, Resgates pendentes; período só se aplica às métricas de fluxo, e totais trazem ajuda “Total atual”.

Abaixo em xl+: gráfico dominante com 2fr e pendências 1fr; depois top promoters (cinco linhas). Abaixo de xl, gráfico → pendências → top. Gráfico de linhas diário, altura 240px desktop/200px mobile, comentários em accent linha sólida 2px + marcador Circle, menções em accent-secondary linha tracejada 2px + marcador Square; fundo surface, eixos ink-muted, grade line 1px. Legenda com nome/forma, valores inteiros, eixo Y começa em zero; até sete rótulos X desktop e quatro mobile. Sem fill translúcido. Tooltip surface/ink com focus teclado; botão “Ver dados em lista” expõe os mesmos valores e datas como lista responsiva acessível. Tooltip nunca único acesso.

Pendências contém contagem e links “Aprovar promoters”/“Ver resgates”. Ausência de ações mostra “Tudo em dia”. Falha de uma região não apaga as demais; cada região possui tentar novamente. Sem inventar métricas de alcance, vendas ou conversões que não fazem parte do produto.

### 6.6 Gestor / Campanhas — /gestor/campanhas

H1 + CTA “Nova campanha”; busca por título e filtros “Todas”, “Ativas”, “Rascunhos”, “Encerradas”, além de select de período. Grid de cards 1 coluna base, 2 em md, 3 em xl; gap 16px. Elemento dominante: thumbs dos posts com status fora da imagem. Cada card mostra título, intervalo, duas contagens “Comentários”/“Menções” e “Ver campanha”. Ordem padrão: ativas por encerramento próximo, rascunhos por atualização, encerradas por data decrescente. Paginação 12 por página.

Mobile: busca em largura total, filtros quebram linha, CTA abaixo do título e antes da busca; nenhuma faixa horizontal rolável. Empty inicial “Crie sua primeira campanha” + “Nova campanha”; filtro sem resultados “Nenhuma campanha encontrada” + “Limpar filtros”.

### 6.7 Gestor / Nova campanha — /gestor/campanhas/nova

H1 “Nova campanha”; form até 768px, seções numeradas 01 Publicação, 02 Pontos, 03 Período e envio. Em desktop largo, resumo lateral até 320px em coluna minmax(0,1fr); abaixo de xl, resumo no fim do fluxo. Abas “Post existente” e “Publicar novo”.

Existente: grade de seleção 2 colunas base, 3 em sm+, quadrados, gap 12px, radio-cards com legenda em superfície opaca abaixo, data e primeiras palavras; selecionado recebe borda 2px accent e check fora da foto. Botão “Carregar mais publicações” após 12 itens. Sem conexão: substituir grade por aviso e CTA; sem publicações: orientar aba de novo post.

Publicar novo: seletor local de arquivo, preview CSS antes de haver mídia e preview do arquivo após seleção, legenda textarea com contador do limite retornado pelo serviço; estados enviando, erro e pronto. Para o MVP visual, aceitar uma imagem JPEG/PNG; campo mostra formatos, tamanho e requisitos reais retornados pela integração, sem inventar compatibilidade de vídeo/carrossel. Botão final só habilita quando serviço confirma suporte e validação. Se publicar não estiver disponível: mensagem “A publicação por aqui não está disponível nesta conexão. Publique no Instagram e selecione o post na outra aba.” e ação “Escolher post existente”; conservar legenda digitada.

Pontos: cada ação tem checkbox e input numérico inteiro min 1, defaults 10/25; ajuda explícita “Até 1 comentário e 1 menção em story pontuados por pessoa nesta campanha.” Campos ocultam/disabled conforme ação desmarcada. Nome da campanha obrigatório em campo próprio. Período com início/fim, data e hora, uma coluna mobile e duas sm+; sem inputs que excedam a largura.

Rodapé do form: secondary “Salvar rascunho”; primary “Revisar campanha”. Dialog final mostra post, pontos, período, número de promoters aprovados, e confirmação “Disparar campanha” para post existente ou “Publicar e disparar” para novo. Publicar no Instagram é efeito externo: deixar explícito no dialog, sem fazê-lo ao selecionar arquivo. Se publicação ocorrer e disparo falhar, mostrar post já criado e “Tentar disparo novamente”, sem publicar duplicado. Loading mantém progresso textual. Ao concluir, ir ao detalhe. Mobile: botões full-width em fluxo normal, resumo anterior aos botões, nenhum footer fixo sobre teclado.

### 6.8 Gestor / Detalhe da campanha — /gestor/campanhas/[id]

Breadcrumb, título/status, intervalo e “Sincronizar” primary; menu secondary para editar/encerrar conforme status. Grid lg+ com coluna de post de 320px e feed flexível; mobile post primeiro, estatísticas depois e feed em seguida. Post com thumb 4/3, legenda expandível (“Ler legenda completa”) e link ao Instagram. Estatísticas: comentários que pontuaram, menções que pontuaram, promoters participantes, pontos concedidos; 2 colunas sm+, uma base.

Feed dominante com filtro “Todas”, “Pontuou”, “Duplicado”, “Não identificado”. Itens surface, nome/@, tipo, data/hora, trecho do comentário ou “Menção em story”, badge e chip de pontos; zero se duplicado/não identificado. “Não identificado” traz “Este @ ainda não está vinculado a um promoter aprovado.” e link para Equipe; não fornecer botão “Dar pontos” presumindo identidade. Se mídia não está mais disponível, manter evento e texto do status.

Sincronizar mostra LoaderCircle, “Sincronizando…”, última tentativa e última atualização bem-sucedida separadas em caso de erro. Feed permanece durante atualização. Toast final contém contagens reais; campanha encerrada continua permitindo sincronizar histórico dentro do período definido, se serviço suportar. Erro de permissão direciona Instagram. Mobile filtros wrap, feed cards, ações no topo do conteúdo sem sobrepor post.

### 6.9 Gestor / Equipe — /gestor/equipe

H1, contador de aprovados e painel de convite em surface-raised: código/link com overflow-wrap anywhere, “Copiar link” secondary, “Copiar código” ghost. Não gerar QR externo. Busca por nome/@, filtros Todos/Pendentes/Aprovados e tabela: Promoter (avatar/nome), Instagram, Status, Saldo, Entrada, Ações. Pendentes primeiro. Ações “Aprovar” primary sm e “Recusar” ghost; recusar abre dialog danger, não remove usuário da plataforma. Aprovar altera apenas após confirmação real; loading na linha.

Mobile: cada pessoa vira card, @ e saldo completos, status junto ao nome, ações no rodapé; painel convite precede busca. Entrada pendente não exibe saldo disponível inventado: “Aguardando aprovação”. Mudança de @ indica nova verificação necessária e preserva histórico vinculado à pessoa.

### 6.10 Gestor / Ranking — /gestor/ranking

H1 “Ranking”, select de período “Este mês” e intervalo escrito; resumo “Pontos ganhos no período”. Lista vertical dos três primeiros em cards surface com posições destacadas conforme componente; depois lista contínua do 4º em diante. Não usar degraus de pódio. Mesmo eixo de nomes/pontos nas duas regiões. Busca por promoter e paginação 20 pessoas. Ajuda “Trocar pontos por benefícios não reduz sua posição.” e regra de desempate acessível em texto expansível.

Mobile mantém ordem 1→2→3→4, avatar 40px, pontos podem ir abaixo do nome. Sem participantes: “O ranking começa com a primeira participação verificada.” Não dar medalha/posição a dados vazios.

### 6.11 Gestor / Lojinha — /gestor/lojinha

H1 “Lojinha”, primary “Nova recompensa”, busca e filtros Disponíveis/Esgotadas/Todas. Grid 1 base, 2 md, 3 xl. Cards com custo e estoque numérico; benefício é item mais visível depois do título. Dialog de criar/editar: nome obrigatório, descrição, custo inteiro positivo, estoque inteiro ≥ 0, imagem local opcional, instruções de retirada. Preview compacto no fim; “Salvar recompensa” primary.

Excluir usa dialog danger com nome do item. Decisão: se há resgates/histórico, ação é “Arquivar recompensa”, retirando da vitrine e preservando comprovantes; excluir definitivamente só item sem histórico. Arquivado sai da lista padrão e pode ser visto por filtro adicional no select mobile; não acumular cinco tabs horizontais. Campos de imagem falhando mantêm placeholder e nome. Mobile edição em dialog rolável; controles em uma coluna e preview no final.

### 6.12 Gestor / Resgates — /gestor/resgates

H1 “Resgates”, contagens por estado, busca por código/nome, filtros Pendentes/Cumpridos/Cancelados. Padrão Pendentes, fila mais antigo primeiro. Tabela com código, pessoa/@, recompensa, custo, data, status, ações. Código Manrope 700 tracking 0.08em, tabular-nums, copiável via ícone com nome acessível. “Cumprir” primary e “Cancelar” ghost abrem dialogs; cancelamento confirma devolução de pontos e unidade ao estoque. Cumprir pede conferir pessoa e código e termina com “Confirmar entrega”.

Mobile vira card com código no topo e botões no rodapé; busca full-width. Sucesso remove da fila pendente após confirmação e permite vê-lo no filtro correspondente. Conflito de estoque/status informa “Este resgate já foi atualizado. Atualizamos os dados para você.”, não repetir operação nem duplicar débito.

### 6.13 Gestor / Instagram — /gestor/instagram

Container form, h1 “Instagram”, card de conexão dominante com ícone Instagram 32px em ink (sem gradiente de marca). Desconectado: texto “Conecte sua conta profissional para selecionar publicações e verificar participações.” + primary “Conectar Instagram”; ajuda que a autenticação ocorre na Meta. Conectado: @, tipo de conta retornado, status, última sincronização e lista de capacidades realmente habilitadas.

Expirada/permissão insuficiente: banner warning com motivo e primary “Reconectar”; erro temporário usa danger e “Tentar novamente”. Sincronizando mantém @ e dados prévios. Não exigir senha/token do Instagram em campo próprio. “Desconectar” ghost/danger no final abre confirmação explicando pausa na verificação e manutenção do histórico. Mobile: card único, botões full-width, detalhes em pares label/valor verticais. Não usar indicador verde como único sinal.

### 6.14 Gestor / Configurações — /gestor/configuracoes

Container form, h1 “Configurações”, seções empilhadas: Organização (nome, instrução padrão de retirada); Conta (nome/e-mail e “Alterar senha” em dialog); Aparência (radio “Escuro”/“Claro”); Preferências (fuso fixo “Horário de Brasília”). Instagram aparece como link para sua própria tela. Um “Salvar alterações” por formulário independente, com mensagem de sucesso próxima.

Tema aplica imediatamente e persiste na preferência local, sem botão salvar. Não incluir planos, cobrança ou exclusão total da conta não previstos no escopo. “Sair da conta” no fim, secondary. Mobile uma coluna; ações em fluxo; aviso ao descartar formulário com alterações.

### 6.15 Promoter / Início — /promoter

Top bar com equipe. Card saldo dominante: surface, borda line, faixa superior accent de 4px, padding 24px, “Saldo disponível” em text-label, valor text-balance accent, “pontos” abaixo, linha perfurada e links “Ver extrato” e “Ir para a lojinha”. Nunca colocar ink sobre faixa accent. Saldo de seis ou mais dígitos quebra unidade em nova linha; em zoom adaptar tamanho via clamp(2rem, 10vw, 3rem), sem truncar.

Depois resumo de posição (“6º lugar neste mês” ou “Ainda sem posição”) + cinco primeiros em lista expansível na própria tela, sem nova rota obrigatória; “Ver ranking” expande lista local de até 20 com paginação. Em seguida até três campanhas ativas, por prazo de encerramento, link “Ver todas”. Desktop md+: saldo ocupa 1fr e campanhas 2fr; ranking abaixo do saldo. Mobile: saldo → posição → campanhas, bottom bar.

Sem equipe: “Entre em uma equipe para começar” + input de código e “Solicitar entrada”. Com entrada pendente: aviso de aprovação, sem saldo fictício nem tarefas habilitadas. Com nenhuma campanha ativa: empty com orientação para voltar depois. Saldo carregando usa skeleton; saldo indisponível não libera resgatar baseado em valor antigo.

### 6.16 Promoter / Campanhas — /promoter/campanhas

H1 “Campanhas”, tabs “Ativas”/“Encerradas”; cards com thumb, prazo em data absoluta e checklist com pontos por ação, botão secondary “Abrir no Instagram”. Grade 1 base, 2 md+, gap 16px. Habilitar apenas ações previstas pela campanha; linha desabilitada não aparece como tarefa obrigatória. Ajuda fixa abaixo do checklist: “Até 1 comentário e 1 menção em story pontuados por campanha”, adaptada às ações habilitadas.

“Comentar no post” e “Mencionar no story” são instruções e estados verificados, não checkboxes clicáveis. Abrir post direciona à URL do post; para menção, instrução “Publique um story e mencione @[conta]”, com “Copiar @” ghost. Não alegar que link publica story automaticamente. Após retornar, manter estado atual e “A verificação pode levar alguns minutos”; ação “Atualizar participações” solicita dados ao serviço e não concede pontos. Campanha concluída mostra ambos os estados sem confete. Mobile cards ocupam toda a coluna, CTA full-width; página respeita bottom bar.

### 6.17 Promoter / Lojinha — /promoter/lojinha

H1 “Lojinha”, saldo da equipe em chip não fixo acima da grade. Filtro “Todas”/“Posso resgatar” e ordenação “Menor custo”. Grid 1 coluna base, 2 em sm, 3 em lg, gap 16px. Não forçar duas colunas em 320px. Card de recompensa concentra nome, custo, estoque e CTA.

Resgatar abre dialog com nome, custo, “Seu saldo: 350 pontos”, “Depois do resgate: 50 pontos” (exemplo), quantidade 1 e “Confirmar resgate”. Enquanto enviar, “Resgatando…”; sucesso abre comprovante com código real e “Ver meus resgates”. Backend valida saldo e estoque novamente; se alteraram, mostrar valor atualizado e exigir nova confirmação, sem confirmar automaticamente. Não debitar otimisticamente. Mobile dialog vertical, resumo antes das ações; com teclado fechado, nunca empurrar conteúdo sob bottom bar.

### 6.18 Promoter / Meus resgates — /promoter/resgates

H1 “Meus resgates”, tabs Pendentes/Histórico. Cards tipo credencial: benefício, status, custo, data, linha perfurada e código em Manrope 700 1.5rem/1.166667 tracking 0.08em com botão “Copiar código”. Instruções de retirada em surface-raised; mostrar “Apresente este código ao gestor.” Cópia feedback “Código copiado.”, sem depender apenas de toast para saber o código.

Pendente mostra código disponível; cumprido mantém código/histórico e data de entrega; cancelado mantém referência e informa “Pontos devolvidos”, sem botão de retirada. Não dar CTA de cumprir/cancelar ao promoter. Mobile um card por linha, código quebra só se viewport/zoom exigir, sem gerar QR ou código de barras externo. Desktop duas colunas md+. Empty “Você ainda não resgatou benefícios” + “Ver lojinha”.

### 6.19 Promoter / Extrato de pontos — /promoter/extrato

Link voltar ao Início, h1 “Extrato de pontos”, saldo atual e filtros período/tipo (Todas/Entradas/Saídas). Timeline semântica em lista agrupada por data, com descrição, campanha/recompensa como link quando disponível, hora, variação tabular à direita e saldo resultante. Entrada “Comentário verificado · +10 pontos” em success; débito “Resgate: Entrada VIP · −300 pontos” em ink-secondary; estorno “Resgate cancelado · +300 pontos” em info. Sinal e texto descrevem o sentido, não só cor. Interações duplicadas/não identificadas não entram no extrato financeiro de pontos porque não alteram saldo.

Ordenação mais recente primeiro, paginação 20 lançamentos, sem scroll infinito obrigatório. Mobile valores podem ficar em segunda linha, texto nunca truncado; bottom bar permanece com Início ativo para esta rota filha conceitual. Empty “Seu extrato começa na primeira participação verificada.” Erro de saldo não substitui por zero.

### 6.20 Promoter / Perfil — /promoter/perfil

H1 “Perfil”, avatar 48px/nome, formulário nome e @ Instagram com ajuda “Use o mesmo @ com que você participa das campanhas.” e “Salvar perfil”. Alteração de @ pede confirmação sobre nova identificação; não transfere automaticamente interações antigas de outra conta. E-mail readonly; “Alterar senha” abre dialog do mesmo padrão.

Seção “Suas equipes”: cards com nome/@ da organização, status e ação “Usar esta equipe” secondary; equipe atual tem label “Equipe em uso”, não botão selecionado sem explicação. Campo “Código de convite” + “Entrar em equipe” após lista. Pendências mostram estado e não liberam saldo; código inválido com erro inline. Links “Extrato de pontos”, controles de tema e “Sair da conta” ao fim. Mobile uma coluna e bottom bar; desktop container reading para os forms, evitando linhas muito largas.

## 7. Movimento

| Token | Valor | Uso |
|---|---|---|
| duration-fast | 120ms | Cor de fundo/borda de botões e seleção de item |
| duration-standard | 180ms | Entrada de toast, dialog e painel local |
| duration-slow | 240ms | Entrada/saída de drawer |
| duration-spin | 800ms | Volta do LoaderCircle |
| duration-skeleton | 1400ms | Pulso de superfície do skeleton |
| ease-standard | cubic-bezier(0.2, 0, 0, 1) | Controles e skeleton |
| ease-enter | cubic-bezier(0, 0, 0.2, 1) | Entrada |
| ease-exit | cubic-bezier(0.4, 0, 1, 1) | Saída |

animate-enter executa vp-enter (opacity 0→1, translateY 8px→0, 180ms, ease-enter, both); animate-spinner usa vp-spin (rotate 360deg, 800ms, linear, infinite); animate-skeleton usa vp-skeleton (surface-raised → surface-hover → surface-raised, 1400ms, ease-standard, infinite). Definições estão no @theme. Não aplicar animação de entrada a páginas inteiras nem a cada linha de tabela; usar uma vez em camada recém-aberta. Saída de toast/dialog: opacity 1→0 em 120ms ease-exit, sem atrasar restauração de foco. Drawer: translateX(-100%)→0 e inverso em 240ms, entrada ease-enter e saída ease-exit; backdrop apenas opacity, mesmo tempo.

Não animar saldo, pontuação, posição de ranking, ordem da lista, altura de campo, barras/gráfico após cada sincronização, theme switch, fundo da landing ou indicador de campanha. Não usar parallax, autoplay, glow, partículas, vibração ou animação contínua fora do carregamento. Conteúdo novo pode entrar sem movimento; não deslocar foco ou rolagem espontaneamente.

Com prefers-reduced-motion: reduce, tokens.css reduz animações e transições para 0.01ms/uma iteração e cancela smooth scroll. Mensagens “Carregando…” continuam presentes; não depender de rotação para comunicar progresso. Bibliotecas/JS da futura implementação devem consultar a mesma preferência; não depender apenas do CSS se usarem temporizadores de desmontagem.

## 8. Acessibilidade, estados de dados e armadilhas

- Documento lang pt-BR, landmarks header/nav/main/footer, um h1 por tela, hierarquia sem pular níveis. Skip link “Pular para o conteúdo”, aparece ao foco sobre surface com text-ink e z-skip; altura 44px, padding 12px, foco accent. Ícones decorativos aria-hidden; icon-only sempre tem nome acessível.
- Foco visível 2px + 3px de intervalo, nenhuma regra outline: none. Evitar clipping do anel; reservar 5px entre focáveis e contornos que cortam overflow. Na bottom bar o outline fica inset (-3px) sobre surface. Voltar foco a disparador ao fechar; após navegação, mover foco para título/main de maneira consistente.
- Alvos mínimos 44×44px, inclusive copiar código, mostrar senha, fechar dialog e paginação. Não reduzir texto funcional abaixo de 0.875rem; caption 0.75rem apenas metadados e labels da navegação inferior. Nenhuma ação exige hover, arrastar ou gesto de precisão.
- Sem scroll horizontal da página em **320, 360, 390, 768, 1024 e 1440px**, com textos reais longos, zoom 200% e reflow a 400%. Checar também altura disponível com teclado. Usar min-w-0, max-width:100%, quebra de nomes/@/URLs/códigos, grids minmax(0,1fr). Nenhum card, thumb ou input impõe min-width maior que o pai. Não esconder overflow para mascarar layout.
- Tabelas viram cards <md; navegações/tabs quebram ou viram select. Barra inferior pode aumentar no zoom: reservar sua altura medida/compartilhada no layout, não presumir 72px sob ampliação de fonte. safe-area-inset-bottom no fundo e no padding do conteúdo. Toast e ações não cobrem o item focado.
- Campo tem label visível, erro associado e instrução antes do envio. Não validar destrutivamente a cada tecla; validar no blur e submit, corrigindo feedback quando válido. Autofill mantém texto legível e color-scheme; não tornar placeholder em label.
- Checkbox/radio 20px visuais em label de min-height 44px; default surface + borda line, selecionado accent + ícone on-accent, hover surface-hover quando desmarcado, focus comum, disabled contrato; loading só na região que os contém. Radio nativo mantém setas e checkbox Espaço. Autocomplete correto, type apropriado e inputmode numeric nos códigos estritamente numéricos; convite/código alfanumérico usa text.
- Atualizações assíncronas preservam filtro, scroll, foco e dados confirmados. Skeleton só na carga inicial; refetch não substitui toda a tela. Uma região aria-live por operação, sem anunciar cada linha e sem repetir toast + erro inline com dois alerts.
- Valores demo só no hero marcado “Exemplo”. Demais estados vazios não simulam campanhas, conexão, aprovação, pontuação, saldo ou resgate. “—” significa não carregado; “0” significa zero confirmado. Requisição parcial possui tentar novamente local.
- Botões de operação evitam duplicidade; servidor é autoridade para pontos, estoque, aprovação e retirada. Falha mantém valores confirmados e formulário. Não mostrar saldo atualizado como sucesso antes de concluir a operação.
- Data curta DD/MM/AAAA, hora HH:mm, data textual “6 de outubro”; último sync “Hoje às 14:32” com data completa acessível. Prazo inclui data absoluta, não só “acaba logo”. Moeda não se aplica a pontos. Pontuação usa Intl.NumberFormat("pt-BR").
- Tema escuro padrão independente do sistema; usuário escolhe claro/escuro e preferência persiste. data-theme no html antes da primeira pintura para evitar flash. O CSS não exige classes dark:. Preservar cores de status e papéis em ambos os temas.
- Confirmar fluxo completo só com teclado, zoom e leitor de tela na implementação. Gráfico tem dados equivalentes em lista, imagem tem alternativa adequada, status sempre texto+ícone. Não há confete, competição coercitiva, countdown de urgência artificial, recompensa aleatória ou promessa de benefício não cadastrado.

## 9. Tom de voz e microcopy

Usar “você”, frases diretas, verbos de ação, nomes concretos e períodos curtos. “Promoter” é o nome do papel; “gestor” para quem administra; “equipe” para vínculo; “pontos” para saldo; “resgate” para troca; “story” para publicação efêmera. Não usar “farmar”, “missão”, “loot”, “engajamento garantido”, inglês operacional (“dashboard”, “submit”, “retry”) ou exclamações repetidas. Marca e @ mantêm grafia original.

| Contexto | Texto exato |
|---|---|
| CTA gestor | “Nova campanha” |
| CTA promoter | “Abrir no Instagram” |
| Ação irreversível em externo | “Publicar e disparar” |
| Estado de botão | “Sincronizando…” |
| Campanhas vazias | “Ainda não há campanhas ativas. Volte em breve para participar.” |
| Busca sem resultado | “Nenhum promoter encontrado. Tente outro nome ou @.” |
| Erro de campo | “Informe um @ do Instagram válido.” |
| Erro de período | “O término precisa ser depois do início.” |
| Erro temporário | “Não foi possível atualizar agora. Seus dados foram mantidos.” + “Tentar novamente” |
| Sessão expirada | “Sua sessão expirou. Entre novamente para continuar.” |
| Conexão expirada | “Reconecte o Instagram para retomar a verificação das participações.” |
| Duplicidade | “Este comentário não gerou pontos. Você já pontuou com um comentário nesta campanha.” |
| Story duplicado | “Você já pontuou com uma menção em story nesta campanha.” |
| Sem identificação | “Não encontramos este @ entre os promoters aprovados.” |
| Aprovação | “Promoter aprovado. As campanhas da equipe já estão disponíveis.” |
| Confirmação de troca | “Resgatar Entrada VIP por 300 pontos?” |
| Sucesso de troca | “Resgate confirmado. Apresente seu código ao gestor.” |
| Estoque mudou | “Esta recompensa acabou de esgotar. Nenhum ponto foi descontado.” |
| Saldo insuficiente | “Faltam 60 pontos para este resgate.” |
| Cancelamento | “Cancelar este resgate? Os pontos e a unidade voltarão ao saldo e ao estoque.” |
| Copiar | “Link de convite copiado.” |
| Pendência | “Sua entrada está em análise. Você poderá participar após a aprovação.” |

Interpolar nomes/pontos reais nos exemplos de microcopy; nunca prometer “nenhum ponto descontado” se o resultado do serviço ainda for desconhecido. Nesse caso: “Estamos confirmando o resultado. Consulte Meus resgates antes de tentar novamente.”

## 10. Contrato dos tokens e verificação da entrega

tokens.css começa com @import "tailwindcss"; contém @theme inline para aliases semânticos e @theme para escala, raios, easing e animações. As cores reais ficam em :root e [data-theme="light"]. O uso de aliases inline segue a [documentação de tema do Tailwind CSS v4](https://tailwindcss.com/docs/theme#referencing-other-variables). Assim, bg-surface, text-ink-muted, border-line e bg-accent resolvem o tema ativo sem duplicar classes.

Usar max-w-auth / max-w-reading / max-w-form / max-w-promoter / max-w-site / max-w-workspace; rounded-control/card/panel/pill; shadow-card/popover/dialog; font-heading/font-sans; text-caption/label/body/lead/section/page/page-wide/balance/hero/hero-wide; ease-standard/enter/exit e animate-enter/spinner/skeleton. Complementos CSS de duração usam var(--duration-fast), var(--duration-standard) e var(--duration-slow); variáveis de medida/z-index são consumidas por CSS ou valores arbitrários. Os tokens --icon-sm/md/lg, --icon-stroke, --stroke-default/emphasis, --touch-target, --sidebar-width, --topbar-height, --tabbar-height, --focus-width/offset e --z-* têm os valores descritos nas seções 4 e 5.

Este CSS fornece fundação e tokens; os componentes e fluxos são especificações para o implementador. Não presumir que colar tokens.css cria componentes, aplica famílias a números ou implementa as regras de negócio. As únicas variáveis externas exigidas pelo arquivo são --font-display e --font-body, injetadas por next/font.

Verificação desta entrega: 124 pares de contraste calculados a partir dos hex reais, valores completos validados contra 4.5:1 para texto e 3:1 para UI; igualdade dos 38 hex distintos entre este guia e tokens.css; parsing de CSS com tinycss2 1.4.0 sem erros, incluindo os blocos @theme e keyframes; conferência dos 20 aliases de cor por tema; inventário do workspace comparado ao inicial. As gravações desta tarefa ficaram restritas a DESIGN.md e tokens.css. Nenhum pacote foi instalado e nenhum build de app foi criado/executado por esta tarefa. A compilação Tailwind e a verificação visual/assistiva das telas ficam para a implementação; esta entrega não afirma tê-las executado.
