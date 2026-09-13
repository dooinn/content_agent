import type { ReactNode } from "react";

/** Sticky bottom bar holding a stage's decision: optional context on the left, buttons right. */
export function ActionBar({ summary, children }: { summary?: ReactNode; children: ReactNode }) {
  return (
    <div className="bottom-0 z-20 -mx-4 mt-8 sm:sticky border-t border-line bg-canvas/90 px-4 py-4 backdrop-blur sm:-mx-8 sm:px-8">
      <div className="flex flex-wrap items-end gap-3">
        {summary && (
          <div className="mr-auto flex min-h-10 items-center gap-2 text-sm text-dim">{summary}</div>
        )}
        {children}
      </div>
    </div>
  );
}
