"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { formatNumber, formatYmdLong, formatYmdShort } from "@/lib/format";

interface Day {
  date: string;
  comments: number;
  story_mentions: number;
}

function useWidth() {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.floor(entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return { ref, width };
}

/**
 * Responsive hand-written SVG line chart (DESIGN.md 6.5): comments in a solid
 * accent line with circle markers, story mentions in a dashed accent-secondary
 * line with square markers, Y axis from zero, integer ticks, no fills.
 * Every value is also available through the "Ver dados em lista" alternative.
 */
export function InteractionsChart({ data }: { data: Day[] }) {
  const { ref, width } = useWidth();
  const [active, setActive] = useState<number | null>(null);
  const [asList, setAsList] = useState(false);

  const mobile = width > 0 && width < 560;
  const height = mobile ? 200 : 240;
  const m = { top: 12, right: 16, bottom: 28, left: 40 };
  const innerW = Math.max(0, width - m.left - m.right);
  const innerH = height - m.top - m.bottom;
  const n = data.length;
  const rawMax = Math.max(1, ...data.map((d) => Math.max(d.comments, d.story_mentions)));
  const step = Math.max(1, Math.ceil(rawMax / 4));
  const yMax = step * 4;
  const x = (i: number) => m.left + (n <= 1 ? innerW / 2 : (i * innerW) / (n - 1));
  const y = (v: number) => m.top + innerH - (v / yMax) * innerH;
  const maxLabels = mobile ? 4 : 7;
  const every = Math.max(1, Math.ceil(n / maxLabels));

  const path = (key: "comments" | "story_mentions") =>
    data.map((d, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)} ${y(d[key]).toFixed(1)}`).join(" ");

  const colW = n > 1 ? innerW / (n - 1) : innerW;
  const a = active !== null ? data[active] : null;
  const tipW = 148;
  const tipX = a && active !== null ? Math.min(Math.max(x(active) - tipW / 2, 4), width - tipW - 4) : 0;

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <ul className="flex flex-wrap items-center gap-x-5 gap-y-1 text-label text-ink-secondary">
          <li className="flex items-center gap-2">
            <svg aria-hidden="true" width="28" height="10" className="shrink-0">
              <line x1="0" x2="28" y1="5" y2="5" strokeWidth="2" className="stroke-accent" />
              <circle cx="14" cy="5" r="3.5" className="fill-accent" />
            </svg>
            Comentários
          </li>
          <li className="flex items-center gap-2">
            <svg aria-hidden="true" width="28" height="10" className="shrink-0">
              <line x1="0" x2="28" y1="5" y2="5" strokeWidth="2" strokeDasharray="6 4" className="stroke-accent-secondary" />
              <rect x="10.5" y="1.5" width="7" height="7" className="fill-accent-secondary" />
            </svg>
            Menções em story
          </li>
        </ul>
        <Button variant="ghost" size="sm" aria-pressed={asList} onClick={() => setAsList((v) => !v)}>
          {asList ? "Ver gráfico" : "Ver dados em lista"}
        </Button>
      </div>

      {asList ? (
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {data.map((d) => (
            <li key={d.date} className="flex flex-wrap items-baseline justify-between gap-x-3 rounded-control bg-surface-raised px-3 py-2 text-label">
              <span className="tabular-nums text-ink">{formatYmdLong(d.date)}</span>
              <span className="tabular-nums text-ink-secondary">
                {formatNumber(d.comments)} {d.comments === 1 ? "comentário" : "comentários"} · {formatNumber(d.story_mentions)}{" "}
                {d.story_mentions === 1 ? "menção" : "menções"}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <div ref={ref} className="w-full">
          {width > 0 && (
            <svg
              width={width}
              height={height}
              viewBox={`0 0 ${width} ${height}`}
              role="group"
              aria-label="Interações pontuadas por dia nos últimos 14 dias. Use Tab para percorrer os dias ou abra a lista de dados."
              className="block max-w-none rounded-control bg-surface"
              onMouseLeave={() => setActive(null)}
            >
              {Array.from({ length: 5 }, (_, i) => i * step).map((t) => (
                <g key={t}>
                  <line x1={m.left} x2={width - m.right} y1={y(t)} y2={y(t)} strokeWidth="1" className="stroke-line-subtle" />
                  <text x={m.left - 8} y={y(t)} textAnchor="end" dominantBaseline="middle" className="fill-ink-muted text-caption tabular-nums">
                    {formatNumber(t)}
                  </text>
                </g>
              ))}
              {data.map((d, i) =>
                i % every === 0 ? (
                  <text key={d.date} x={x(i)} y={height - 8} textAnchor="middle" className="fill-ink-muted text-caption tabular-nums">
                    {formatYmdShort(d.date)}
                  </text>
                ) : null,
              )}

              <path d={path("story_mentions")} fill="none" strokeWidth="2" strokeDasharray="6 4" strokeLinejoin="round" className="stroke-accent-secondary" />
              <path d={path("comments")} fill="none" strokeWidth="2" strokeLinejoin="round" className="stroke-accent" />

              {data.map((d, i) => (
                <g key={d.date}>
                  <rect x={x(i) - 3.5} y={y(d.story_mentions) - 3.5} width="7" height="7" className="fill-accent-secondary" />
                  <circle cx={x(i)} cy={y(d.comments)} r="3.5" className="fill-accent" />
                </g>
              ))}

              {data.map((d, i) => (
                <rect
                  key={`hit-${d.date}`}
                  x={x(i) - colW / 2}
                  y={m.top}
                  width={Math.max(colW, 1)}
                  height={innerH}
                  fill="transparent"
                  tabIndex={0}
                  role="img"
                  aria-label={`${formatYmdLong(d.date)}: ${d.comments} ${d.comments === 1 ? "comentário" : "comentários"} e ${d.story_mentions} ${d.story_mentions === 1 ? "menção" : "menções"} em story`}
                  onMouseEnter={() => setActive(i)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  className="outline-none focus-visible:stroke-accent"
                  strokeWidth="2"
                />
              ))}

              {a && active !== null && (
                <g pointerEvents="none">
                  <line x1={x(active)} x2={x(active)} y1={m.top} y2={m.top + innerH} strokeWidth="1" className="stroke-line" />
                  <rect x={tipX} y={m.top} width={tipW} height="58" rx="8" className="fill-surface stroke-line" strokeWidth="1" />
                  <text x={tipX + 10} y={m.top + 18} className="fill-ink text-label font-semibold tabular-nums">
                    {formatYmdLong(a.date)}
                  </text>
                  <text x={tipX + 10} y={m.top + 35} className="fill-ink-secondary text-caption tabular-nums">
                    Comentários: {formatNumber(a.comments)}
                  </text>
                  <text x={tipX + 10} y={m.top + 50} className="fill-ink-secondary text-caption tabular-nums">
                    Menções: {formatNumber(a.story_mentions)}
                  </text>
                </g>
              )}
            </svg>
          )}
        </div>
      )}
    </div>
  );
}
