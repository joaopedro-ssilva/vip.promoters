const TZ = "America/Sao_Paulo";
const LOCALE = "pt-BR";

const nf = new Intl.NumberFormat(LOCALE);

export function formatNumber(n: number): string {
  return nf.format(n);
}

/** "1.250 pontos" / "1 ponto" */
export function formatPoints(n: number): string {
  return `${nf.format(n)} ${Math.abs(n) === 1 ? "ponto" : "pontos"}`;
}

/** "+25 pontos" / "−100 pontos" (true minus sign) */
export function formatSignedPoints(n: number): string {
  const sign = n > 0 ? "+" : n < 0 ? "\u2212" : "";
  return `${sign}${nf.format(Math.abs(n))} ${Math.abs(n) === 1 ? "ponto" : "pontos"}`;
}

export function formatOrdinal(n: number): string {
  return `${nf.format(n)}º`;
}

function parts(iso: string | Date, opts: Intl.DateTimeFormatOptions) {
  const d = typeof iso === "string" ? new Date(iso) : iso;
  if (Number.isNaN(d.getTime())) return null;
  return new Intl.DateTimeFormat(LOCALE, { timeZone: TZ, ...opts }).format(d);
}

/** DD/MM/AAAA */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return (
    parts(iso, { day: "2-digit", month: "2-digit", year: "numeric" }) ?? "—"
  );
}

/** HH:mm */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return parts(iso, { hour: "2-digit", minute: "2-digit", hourCycle: "h23" }) ?? "—";
}

/** DD/MM/AAAA às HH:mm */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return `${formatDate(iso)} às ${formatTime(iso)}`;
}

/** DD/MM às HH:mm */
export function formatShortDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = parts(iso, { day: "2-digit", month: "2-digit" });
  return d ? `${d} às ${formatTime(iso)}` : "—";
}

/** "6 de outubro" */
export function formatDayMonth(iso: string | null | undefined): string {
  if (!iso) return "—";
  return parts(iso, { day: "numeric", month: "long" }) ?? "—";
}

/** DD/MM from a plain "YYYY-MM-DD" string (no timezone shift). */
export function formatYmdShort(ymd: string): string {
  const [, m, d] = ymd.split("-");
  return `${d}/${m}`;
}

export function formatYmdLong(ymd: string): string {
  const [y, m, d] = ymd.split("-");
  return `${d}/${m}/${y}`;
}

function dayKey(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(d);
}

/** "Hoje às 14:32" / "Ontem às 09:10" / "03/10/2026 às 18:00" */
export function formatRelativeDay(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86_400_000);
  const key = dayKey(d);
  if (key === dayKey(today)) return `Hoje às ${formatTime(iso)}`;
  if (key === dayKey(yesterday)) return `Ontem às ${formatTime(iso)}`;
  return formatDateTime(iso);
}

/** Group key (YYYY-MM-DD in Brasília) for an ISO instant. */
export function brasiliaDayKey(iso: string): string {
  return dayKey(new Date(iso));
}

const INPUT_RE = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/;

/** ISO instant → value for <input type="datetime-local"> in Brasília time. */
export function toDateTimeInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const p = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(d);
  const get = (t: string) => p.find((x) => x.type === t)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}`;
}

/**
 * <input type="datetime-local"> value (Brasília wall time) → ISO UTC string.
 * Brazil has had no daylight saving time since 2019, so the offset is fixed (-03:00).
 */
export function fromDateTimeInput(value: string): string | null {
  if (!value) return null;
  const m = INPUT_RE.exec(value);
  if (!m) return null;
  const d = new Date(`${value}:00-03:00`);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function initials(name: string | null | undefined): string {
  if (!name) return "?";
  const words = name.replace(/^@/, "").trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  const first = words[0][0] ?? "";
  const last = words.length > 1 ? (words[words.length - 1][0] ?? "") : "";
  return (first + last).toUpperCase();
}

export function plural(n: number, one: string, many: string): string {
  return n === 1 ? one : many;
}

/** True when the instant is still in the future. */
export function isFuture(iso: string | null | undefined): boolean {
  return !!iso && new Date(iso).getTime() > Date.now();
}

/** True when the instant is less than `days` days from now (or already past). */
export function expiresWithinDays(iso: string | null | undefined, days: number): boolean {
  return !!iso && new Date(iso).getTime() - Date.now() < days * 86_400_000;
}
