import { Check, Coins, Loader2 } from "lucide-react";
import { PHASES, STAGE_INFO, STAGE_ORDER, stageIndex } from "@/lib/stages";

export function PipelineStepper({
  stage,
  status,
  running,
}: {
  stage: string | null;
  status: string;
  running: boolean;
}) {
  const current = stageIndex(stage, status);

  return (
    <nav aria-label="Pipeline" className="space-y-6">
      {PHASES.map((phase) => (
        <div key={phase.label}>
          <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wider text-faint">
            {phase.label}
          </p>
          <ol className="space-y-1">
            {phase.stages.map((key) => {
              const index = STAGE_ORDER.indexOf(key);
              const info = STAGE_INFO[key];
              const state = index < current ? "done" : index === current ? "current" : "todo";
              return (
                <li
                  key={key}
                  aria-current={state === "current" ? "step" : undefined}
                  className={`flex items-center gap-3 rounded-lg px-2 py-2 text-sm ${
                    state === "current" ? "border border-gold/40 bg-gold/10 text-gold" : "border border-transparent"
                  } ${state === "todo" ? "text-faint" : ""} ${state === "done" ? "text-dim" : ""}`}
                >
                  <span
                    className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold ${
                      state === "done"
                        ? "bg-ok/15 text-ok"
                        : state === "current"
                          ? "bg-gold text-canvas"
                          : "border border-line-strong text-faint"
                    }`}
                  >
                    {state === "done" ? (
                      <Check className="h-3.5 w-3.5" />
                    ) : state === "current" && running ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      index + 1
                    )}
                  </span>
                  <span className="flex-1">{info.label}</span>
                  {info.paid && (
                    <Coins
                      className="h-3.5 w-3.5 opacity-60"
                      aria-label="Uses paid generation"
                    />
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      ))}
    </nav>
  );
}

/** Thin segmented bar of pipeline steps, for project cards. */
export function StageProgress({ stage, status }: { stage: string | null; status: string }) {
  const current = stageIndex(stage, status);
  const complete = current >= STAGE_ORDER.length;
  const color = complete ? "bg-ok" : status === "running" ? "bg-info" : "bg-gold";
  return (
    <div>
      <div className="flex gap-1">
        {STAGE_ORDER.map((key, index) => (
          <span
            key={key}
            className={`h-1.5 flex-1 rounded-full ${index < current || (index === current && !complete) ? color : "bg-line-strong"} ${index === current && !complete ? "opacity-60" : ""}`}
          />
        ))}
      </div>
      <p className="mt-1.5 text-right text-xs text-faint">
        {Math.min(current, STAGE_ORDER.length)} / {STAGE_ORDER.length}
      </p>
    </div>
  );
}
