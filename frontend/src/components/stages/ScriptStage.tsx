"use client";

import { Check, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { FactCheckNote } from "@/components/ReviewNotes";
import { Badge, Button, Card, DirectionInput, inputClass } from "@/components/ui";
import type { ScriptPayload, StageProps } from "@/lib/types";

const WORDS_PER_MINUTE = 155;

export function ScriptStage({ payload, send, pending }: StageProps<ScriptPayload>) {
  const original = payload.script.segments.map((segment) => segment.narration);
  const [texts, setTexts] = useState(original);
  const [feedback, setFeedback] = useState("");

  const edited = texts.some((text, i) => text !== original[i]);
  const words = texts.join(" ").split(/\s+/).filter(Boolean).length;
  const seconds = Math.round((words / WORDS_PER_MINUTE) * 60);

  return (
    <div className="space-y-6">
      <FactCheckNote report={payload.fact_check} />

      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">{payload.script.title}</h2>
          <div className="flex gap-2">
            <Badge>{words} words</Badge>
            <Badge tone={seconds > 32 ? "amber" : "green"}>about {seconds}s</Badge>
          </div>
        </div>
        <ol className="mt-5 space-y-3">
          {payload.script.segments.map((segment, i) => (
            <li key={i} className="grid gap-3 md:grid-cols-[6.5rem_1fr]">
              <div className="pt-2">
                <Badge tone="blue">{segment.beat}</Badge>
                <p className="mt-1.5 font-mono text-[11px] text-faint">{segment.fact_ids.join(" · ")}</p>
              </div>
              <textarea
                value={texts[i]}
                onChange={(event) =>
                  setTexts(texts.map((text, j) => (j === i ? event.target.value : text)))
                }
                rows={2}
                aria-label={`Narration line ${i + 1}`}
                className={`${inputClass} resize-none text-base leading-relaxed`}
              />
            </li>
          ))}
        </ol>
      </Card>

      <ActionBar summary={edited ? "You edited the narration" : "Edit any line, then approve"}>
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="e.g. make the hook punchier" />
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() => send({ action: "revise", feedback: feedback || undefined })}
        >
          <RefreshCw className="h-4 w-4" />
          Rewrite
        </Button>
        <Button
          disabled={pending}
          onClick={() =>
            send({
              action: "approve",
              feedback: feedback || undefined,
              edits: edited ? { narration: texts } : {},
            })
          }
        >
          <Check className="h-4 w-4" />
          {edited ? "Approve with my edits" : "Approve script"}
        </Button>
      </ActionBar>
    </div>
  );
}
