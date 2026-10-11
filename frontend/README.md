# VIP Promoters: frontend

Site do VIP Promoters em Next.js 16 (App Router), TypeScript, Tailwind CSS 4, TanStack Query e react-hook-form com zod. Os componentes são próprios, sem biblioteca de UI.

Para a visão geral do projeto e como subir tudo com Docker, veja o [README da raiz](../README.md).

## Rodar em desenvolvimento

O backend precisa estar no ar em `http://localhost:8000` (veja o README da raiz).

```bash
npm install
npm run dev
```

Abra <http://localhost:3000>. O navegador só fala com o próprio Next: as chamadas a `/api/*` são repassadas ao backend, definido por `BACKEND_INTERNAL_URL` (padrão `http://localhost:8000`).

## Comandos

| Comando | O que faz |
|---|---|
| `npm run dev` | servidor de desenvolvimento |
| `npm run build` | build de produção (saída `standalone`) |
| `npm run start` | serve o build |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | checagem de tipos |

Não há testes automatizados. Os fluxos de tela foram verificados manualmente em navegador.

## Organização

```
src/app/(public)/     landing, entrar, cadastro, convite
src/app/gestor/       área do gestor
src/app/promoter/     área do promoter
src/components/ui/    componentes base (botão, campo, dialog, toast...)
src/components/       componentes por área (manager, promoter, auth, layout)
src/lib/api/          cliente da API e tipos espelhando o contrato
src/lib/              formatação, validação, URLs seguras, tema
src/proxy.ts          proteção de rotas e política de segurança de conteúdo (CSP)
```

## Pontos importantes

- **Next.js 16**: o antigo `middleware.ts` chama-se `proxy.ts`. Leia [AGENTS.md](AGENTS.md) antes de mexer em convenções do framework.
- **Sessão**: fica em cookies `HttpOnly` definidos pelo backend. O cliente da API envia o cabeçalho `X-Requested-With` em toda chamada e, ao receber 401, tenta renovar a sessão uma vez antes de mandar para `/entrar`.
- **CSP com nonce**: todas as páginas são renderizadas por requisição. Estilos e scripts inline sem nonce são bloqueados em produção.
- **`localStorage`** guarda apenas o tema e a equipe ativa do promoter. Nenhum token ou dado de usuário.
- **Imagens remotas** (posts do Instagram, recompensas) usam `<img>` simples, não `next/image`, porque os endereços expiram.
- **Design**: as cores, a tipografia e os componentes seguem [design/DESIGN.md](../design/DESIGN.md). Use sempre os tokens (`bg-surface`, `text-ink-muted`, `border-line`), nunca cores avulsas do Tailwind.
- **`cn()`** em `src/lib/cn.ts` registra os tamanhos de fonte do design (`text-caption`, `text-label`...). Sem isso o `tailwind-merge` os confunde com cores e descarta.
- **Docker**: o endereço do backend é fixado no build. Passe `BACKEND_INTERNAL_URL` como argumento de build.
- **Datas** são exibidas e digitadas no horário de Brasília.
