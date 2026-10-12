# VIP Promoters — design system "Noite / Lima / Violeta"

O visual do VIP Promoters é o design system do **Camarim** (projeto irmão), aplicado aqui.
**A fonte da verdade visual é o código:** os tokens e materiais de
[`frontend/src/app/globals.css`](../frontend/src/app/globals.css) e esta página. A especificação
anterior ("credencial de acesso", Barlow Condensed + Manrope, grafite esverdeado) foi substituída.

> "Escuro de palco, neon de pista e números que não deixam dúvida."

## As regras de cor

1. **Lima é AÇÃO e o que JÁ VALEU.** Botão principal (gel lima, um por tela), item de navegação
   ativo, anel de foco — e os pontos já creditados, o promoter aprovado, o resgate cumprido.
2. **Violeta é o que AINDA VAI ACONTECER.** Campanha ativa (pontos em jogo), interação ainda não
   identificada, "Modo demonstração". "Isto já valeu ponto?" se responde pela cor.
3. **Rosa é perda e recusa** (`danger`). **Âmbar é atenção** (pendente, duplicado). Nada mais usa
   essas duas.
4. **Cifra de apoio fica neutra.** Cor em número é conclusão: se tudo brilhar, nada salta.

| Status | Tom |
|---|---|
| Pontuou, Aprovado, Cumprido | lima |
| Ativa, Não identificado | violeta |
| Pendente, Duplicado | âmbar |
| Recusado, Cancelado | rosa |
| Rascunho, Encerrada, Removido, Fora do período | neutro / apagado |

O mapa vive em `components/ui/badge.tsx`.

## Tokens

Componente usa o **apelido semântico**, nunca a escala crua — é o que deixa o tema claro traduzir
tudo num lugar só.

| Apelido | Escuro | Papel |
|---|---|---|
| `canvas` | noite-950 `#0b0a11` | fundo da página |
| `surface` | noite-850 `#16151f` | card sólido, dialog |
| `surface-raised` | noite-800 `#1d1b28` | item ativo, bloco interno, popover |
| `surface-sunken` | noite-900 `#111019` | barra lateral, campo, cabeçalho de tabela |
| `line` / `line-subtle` | noite-500 / noite-700 | borda de controle / divisória |
| `ink-strong` / `ink` / `ink-secondary` / `ink-muted` | noite-050 / 100 / 200 / 300 | texto |
| `accent` (+ `-soft`, `-border`) | lima-500 `#bcf23f` | ação, marca |
| `success` | lima-400 `#d2fb63` | texto lima (pontos, links) — vira verde-escuro no tema claro |
| `violet` (+ `-soft`, `-border`) | violeta-400 `#a98bff` | o que ainda vai acontecer |
| `warning` (+ `-soft`, `-border`) | âmbar-400 `#ffc24b` | atenção |
| `danger` (+ `-soft`, `-border`) | rosa-400 `#ff7a92` | perda, recusa |

**Texto lima usa `text-success`, não `text-accent`.** O `accent` é lima de preenchimento; como
texto sobre branco (tema claro) ele some. `success` resolve para o verde-escuro do Camarim no claro.

## Materiais

| Classe | Onde |
|---|---|
| `.solido` | lista, tabela, formulário, painel de dado — a maior parte da tela |
| `.vidro-fino` | botão secundário, controle segmentado (filtros) |
| `.vidro` | indicador (KPI), saldo do promoter, destaque da landing |
| `.gel-lima` | a ação principal — **uma por tela** |
| `.palco` | fundo da área de conteúdo: luz lima à esquerda, violeta à direita. Único gradiente de fundo. |

"Vidro resume, sólido comprova": dado para conferir fica em superfície opaca.

## Tipografia

- **Syne** (`.display`, `font-heading`): marca, título de página, título de modal e de seção.
- **Archivo**: todo o resto. Número em lista: `.num` (figuras tabulares). Número de indicador:
  `.cifra`.
- **Instrument Serif**: só na PORTA — landing e telas de entrada (`.titulo-de-entrada`,
  `.site-titulo*`), com o trecho final em itálico lima.
- **`.rotulo`**: caixa alta pequena e espaçada, só em rótulo estrutural (rótulo de campo, de métrica,
  grupo da barra lateral, cabeçalho de tabela). Nunca sobre conteúdo.

Escala (globals.css): `text-2xs` 11 · `text-caption` 12,5 · `text-label` 14 (corpo) · `text-body` 15
· `text-section` 19 · `text-brand` 22 · `text-page` 28 · `text-balance` 52. Campo de formulário
fica em 16px para o iOS não dar zoom. Ao criar um tamanho novo, registre-o também em
`src/lib/cn.ts` — senão o `tailwind-merge` o confunde com cor e descarta a classe.

## Forma, movimento, telas

- Raios: chip 8px, botão e campo 12px (`rounded-control`), card 22px (`rounded-card`).
- Movimento só em `transform` e `opacity`; 80ms hover, 140ms camada, 220ms diálogo.
- Alvo de toque mínimo de 44px (`min-h-11`, `.alvo-de-toque`).
- **Entrada e landing são sempre escuras**: o layout público tem `data-theme="dark"`.
- Casca do gestor: barra lateral de 264px em grupos (Operação, Recompensas, Conta), marcador lima
  no item ativo, emblema com as iniciais da organização abaixo da marca.
- Casca do promoter: barra superior no desktop e barra inferior no celular, ícone ativo em lima.
- A marca: quadrado lima com o ingresso recortado em escuro + "VIP Promoters" em Syne 800
  (`components/layout/parts.tsx`).
