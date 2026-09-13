"use client";

import { ArrowRight, CheckCircle2, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { FactCheckNote } from "@/components/ReviewNotes";
import { Button, Detail, DirectionInput } from "@/components/ui";
import type { AnglePayload, StageProps } from "@/lib/types";

export function AngleStage({ payload, send, pending }: StageProps<AnglePayload>) {
  const [choice, setChoice] = useState<number | null>(null);
  const [feedback, setFeedback] = useState("");

  return (
    <div className="space-y-6">
      <FactCheckNote report={payload.fact_check} />

      <div className="grid gap-4 lg:grid-cols-3" role="radiogroup" aria-label="Story angles">
        {payload.angles.map((angle, index) => {
          const selected = choice === index;
          return (
            <div
              key={index}
              role="radio"
              aria-checked={selected}
              tabIndex={0}
              onClick={() => setChoice(index)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setChoice(index);
                }
              }}
              className={`flex cursor-pointer flex-col gap-3 rounded-xl border p-5 transition focus-visible:outline-2 focus-visible:outline-gold ${
                selected ? "border-gold/60 bg-gold/5 ring-1 ring-gold/40" : "border-line bg-surface hover:border-line-strong"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wider text-faint">
                  Angle {index + 1}
                </span>
                {selected && <CheckCircle2 className="h-5 w-5 text-gold" />}
              </div>
              <h3 className="text-lg font-semibold text-ink">{angle.title}</h3>
              <blockquote className="border-l-2 border-gold pl-3 text-base italic text-ink">
                “{angle.hook_line}”
              </blockquote>
              <p className="text-sm leading-relaxed text-dim">{angle.logline}</p>
              <Detail label="Why it works">{angle.why_it_works}</Detail>
              <Detail label="Accuracy">{angle.accuracy_notes}</Detail>
              <p className="mt-auto pt-2 font-mono text-[11px] text-faint">{angle.fact_ids.join(" · ")}</p>
            </div>
          );
        })}
      </div>

      <ActionBar summary={choice === null ? "Select the angle to write" : `Angle ${choice + 1} selected`}>
        <DirectionInput
          value={feedback}
          onChange={setFeedback}
          placeholder="e.g. keep it light and ironic"
        />
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() => send({ action: "revise", feedback: feedback || undefined })}
        >
          <RefreshCw className="h-4 w-4" />
          Propose new angles
        </Button>
        <Button
          disabled={pending || choice === null}
          onClick={() =>
            choice !== null && send({ action: "select", choice, feedback: feedback || undefined })
          }
        >
          Write the script
          <ArrowRight className="h-4 w-4" />
        </Button>
      </ActionBar>
    </div>
  );
}
