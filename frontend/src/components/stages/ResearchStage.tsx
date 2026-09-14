"use client";

import { Check, ExternalLink, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { LengthPicker } from "@/components/LengthPicker";
import { Badge, Button, Card, Detail, DirectionInput, SectionTitle, inputClass } from "@/components/ui";
import type { ResearchPayload, StageProps } from "@/lib/types";

const factTone = { verified: "green", disputed: "amber", legend: "zinc" } as const;
const tierTone = { scholarly: "blue", reference: "green", popular: "zinc" } as const;

export function ResearchStage({ view, payload, send, pending, options }: StageProps<ResearchPayload>) {
  const { fact_sheet: sheet, eligibility } = payload;
  const [feedback, setFeedback] = useState("");
  const [topic, setTopic] = useState("");
  const currentLength = view.state.target_seconds ?? options?.defaults.target_seconds ?? 30;
  const [length, setLength] = useState<number | null>(null);
  const lengthEdit = length && length !== currentLength ? { target_seconds: length } : {};
  const sources = new Map(sheet.sources.map((source) => [source.id, source]));
  const counts = { verified: 0, disputed: 0, legend: 0 };
  for (const fact of sheet.facts) counts[fact.status] += 1;

  return (
    <div className="space-y-6">
      {!eligibility.ok && (
        <Card className="border-danger/30 bg-danger/10 text-sm text-danger">{eligibility.reason}</Card>
      )}

      <Card className="grid gap-6 md:grid-cols-2">
        {options && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">Video length</p>
            <LengthPicker options={options} value={length ?? currentLength} onChange={setLength} />
            <p className="mt-2 text-xs text-faint">Last chance to change it: the story is written for this length.</p>
          </div>
        )}
        <label className="block text-sm">
          <span className="text-xs font-semibold uppercase tracking-wider text-faint">
            Research a different figure instead (optional)
          </span>
          <input
            value={topic}
            onChange={(event) => setTopic(event.target.value)}
            placeholder="e.g. Catherine the Great"
            className={`mt-2 max-w-md ${inputClass}`}
          />
        </label>
      </Card>

      <Card>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-2xl font-semibold">{sheet.figure}</h2>
            <p className="mt-1 text-sm text-dim">
              {sheet.born} – {sheet.died}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge>{sheet.era}</Badge>
            <Badge>{sheet.region}</Badge>
          </div>
        </div>
        <p className="mt-4 max-w-3xl leading-relaxed text-dim">{sheet.summary}</p>
        <div className="mt-6 grid gap-6 border-t border-line pt-5 md:grid-cols-3">
          <Detail label="Appearance">{sheet.appearance_notes}</Detail>
          <Detail label="Costume">{sheet.costume_notes}</Detail>
          <Detail label="Setting">{sheet.setting_notes}</Detail>
        </div>
      </Card>

      <Card>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <SectionTitle>Facts · {sheet.facts.length}</SectionTitle>
          <div className="flex gap-2">
            <Badge tone="green">{counts.verified} verified</Badge>
            <Badge tone="amber">{counts.disputed} disputed</Badge>
            <Badge>{counts.legend} legend</Badge>
          </div>
        </div>
        <ul className="divide-y divide-line">
          {sheet.facts.map((fact) => (
            <li key={fact.id} className="flex items-start gap-4 py-3">
              <span className="w-8 shrink-0 pt-0.5 font-mono text-xs text-faint">{fact.id}</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-ink">{fact.claim}</p>
                {fact.note && <p className="mt-1 text-xs text-faint">{fact.note}</p>}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {fact.source_ids.map((id) => {
                    const source = sources.get(id);
                    return source ? (
                      <a
                        key={id}
                        href={source.url}
                        target="_blank"
                        rel="noreferrer"
                        title={source.title}
                        className="inline-flex items-center gap-1 rounded-md border border-line bg-raised px-1.5 py-0.5 text-[11px] text-dim hover:border-line-strong hover:text-ink"
                      >
                        {id}
                        {source.tier && <span className="text-faint">· {source.tier}</span>}
                      </a>
                    ) : (
                      <span key={id} className="text-[11px] text-faint">
                        {id}
                      </span>
                    );
                  })}
                </div>
              </div>
              <Badge tone={factTone[fact.status]}>{fact.status}</Badge>
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <SectionTitle>Sources · {sheet.sources.length}</SectionTitle>
        <ul className="grid gap-x-6 gap-y-2 md:grid-cols-2">
          {sheet.sources.map((source) => (
            <li key={source.id} className="flex min-w-0 items-center gap-2 text-sm">
              <span className="w-8 shrink-0 font-mono text-xs text-faint">{source.id}</span>
              {source.tier && <Badge tone={tierTone[source.tier]}>{source.tier}</Badge>}
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex min-w-0 items-center gap-1 text-dim hover:text-ink"
              >
                <span className="truncate">{source.title}</span>
                <ExternalLink className="h-3 w-3 shrink-0 opacity-50" />
              </a>
            </li>
          ))}
        </ul>
      </Card>

      <ActionBar summary={`${sheet.facts.length} facts from ${sheet.sources.length} sources`}>
        <DirectionInput
          value={feedback}
          onChange={setFeedback}
          placeholder="e.g. focus on his years as a dancer"
        />
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() =>
            send({
              action: "revise",
              feedback: feedback || undefined,
              edits: { ...(topic.trim() ? { topic: topic.trim() } : {}), ...lengthEdit },
            })
          }
        >
          <RefreshCw className="h-4 w-4" />
          Research again
        </Button>
        <Button
          variant={eligibility.ok ? "primary" : "danger"}
          disabled={pending}
          onClick={() => send({ action: "approve", feedback: feedback || undefined, edits: lengthEdit })}
        >
          {eligibility.ok ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
          {eligibility.ok ? "Approve research" : "Close as ineligible"}
        </Button>
      </ActionBar>
    </div>
  );
}
