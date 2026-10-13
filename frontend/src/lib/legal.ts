/**
 * Dados do responsável pelo serviço, usados na Política de Privacidade e nos Termos.
 *
 * PREENCHA ANTES DE PUBLICAR (e antes do App Review da Meta): os valores entre colchetes
 * aparecem na página como estão. Peça a revisão de um advogado antes de lançar.
 */
export const LEGAL = {
  /** Razão social de quem opera o serviço (a mesma do Meta Business verificado). */
  company: "[RAZÃO SOCIAL]",
  cnpj: "[CNPJ]",
  /** E-mail que recebe pedidos de privacidade (LGPD) e de suporte. */
  contactEmail: "[privacidade@seudominio.com.br]",
  /** Encarregado de dados (DPO), se houver. Pode ser a mesma pessoa do contato. */
  dpo: "[NOME DO ENCARREGADO]",
  /** Cidade do foro nos Termos. */
  city: "[CIDADE/UF]",
  /** Data em que a versão atual passou a valer. */
  effectiveDate: "[DD/MM/AAAA]",
} as const;

/** Prazos que o backend aplica (RETENTION_DAYS, NOTIFICATION_RETENTION_DAYS). */
export const RETENTION = { interactionsDays: 365, notificationsDays: 90 } as const;
