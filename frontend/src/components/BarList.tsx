"use client";

import { useState } from "react";

export interface BarDatum {
  key: string;
  label: string;
  value: number;
  display: string;
  detail?: string;
}

const LABEL_ROOM = "3.5rem"; // space kept right of the longest bar for its value label

/** Horizontal bars for one series: 16px marks with a 4px rounded end, value at the tip,
 *  and a hover/focus tooltip. The same numbers are available in the table view beside it. */
export function BarList({ data, max, caption }: { data: BarDatum[]; max: number; caption: string }) {
  const [active, setActive] = useState<string | null>(null);

  return (
    <ul className="space-y-1.5" aria-label={caption}>
      {data.map((datum) => {
        const share = max > 0 ? Math.min(1, Math.max(0, datum.value / max)) : 0;
        const width = `calc((100% - ${LABEL_ROOM}) * ${share})`;
        const isActive = active === datum.key;
        return (
          <li key={datum.key} className="grid grid-cols-[7.5rem_1fr] items-center gap-3 text-sm">
            <span className="truncate text-dim" title={datum.label}>
              {datum.label}
            </span>
            <span
              tabIndex={0}
              aria-label={`${datum.label}: ${datum.display}${datum.detail ? `, ${datum.detail}` : ""}`}
              onPointerEnter={() => setActive(datum.key)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(datum.key)}
              onBlur={() => setActive(null)}
              className="relative block h-8 rounded outline-none focus-visible:ring-1 focus-visible:ring-gold/60"
            >
              <span aria-hidden className="absolute inset-y-1 left-0 w-px bg-line-strong" />
              <span
                aria-hidden
                className="absolute left-0 top-1/2 h-4 -translate-y-1/2 rounded-r bg-[var(--viz-bar)] transition-[filter]"
                style={{ width, filter: isActive ? "brightness(1.2)" : undefined }}
              />
              <span
                aria-hidden
                className="absolute top-1/2 -translate-y-1/2 pl-2 text-xs font-medium text-ink"
                style={{ left: width }}
              >
                {datum.display}
              </span>
              {isActive && datum.detail && (
                <span
                  role="tooltip"
                  className="pointer-events-none absolute bottom-full left-0 z-10 mb-1 whitespace-nowrap rounded-md border border-line-strong bg-raised px-2.5 py-1.5 text-xs shadow-lg"
                >
                  <span className="font-semibold text-ink">{datum.display}</span>
                  <span className="ml-2 text-dim">{datum.detail}</span>
                </span>
              )}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
