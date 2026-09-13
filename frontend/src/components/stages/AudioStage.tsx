"use client";

import { Check, Mic, Music, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { Badge, Button, Card, DirectionInput, SectionTitle, Toggle, inputClass } from "@/components/ui";
import { assetUrl } from "@/lib/api";
import { timeRange } from "@/lib/format";
import type { AudioPayload, StageProps } from "@/lib/types";

export function AudioStage({ view, payload, send, pending }: StageProps<AudioPayload>) {
  const { narration, bgm } = payload;
  const segments = view.state.script?.segments ?? [];
  const [feedback, setFeedback] = useState("");
  const [redoNarration, setRedoNarration] = useState(false);
  const [redoMusic, setRedoMusic] = useState(false);
  const [voiceId, setVoiceId] = useState("");

  const targets = [...(redoNarration ? ["narration"] : []), ...(redoMusic ? ["bgm"] : [])];

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <Mic className="h-4 w-4 text-gold" />
              Narration
            </p>
            <Badge>{narration.duration.toFixed(1)}s</Badge>
          </div>
          <audio controls src={assetUrl(view, narration.audio_key)} className="w-full" />
          <ol className="mt-4 space-y-2">
            {narration.segments.map((timing) => (
              <li key={timing.order} className="flex gap-3 text-sm">
                <span className="w-20 shrink-0 font-mono text-xs leading-5 text-faint">
                  {timeRange(timing.start, timing.end)}
                </span>
                <span className="text-dim">{segments[timing.order - 1]?.narration}</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card>
          <div className="mb-3 flex items-center justify-between">
            <p className="flex items-center gap-2 text-sm font-semibold">
              <Music className="h-4 w-4 text-gold" />
              Music bed
            </p>
            <Badge>{bgm.seconds}s</Badge>
          </div>
          <audio controls src={assetUrl(view, bgm.audio_key)} className="w-full" />
          <p className="mt-4 text-sm leading-relaxed text-dim">{bgm.prompt}</p>
          <p className="mt-3 text-xs text-faint">The final mix lowers the music whenever the narrator speaks.</p>
        </Card>
      </div>

      <Card>
        <SectionTitle>Not right? Choose what to regenerate</SectionTitle>
        <div className="flex flex-wrap items-center gap-6">
          <Toggle label="Narration" checked={redoNarration} onChange={setRedoNarration} />
          <Toggle label="Music" checked={redoMusic} onChange={setRedoMusic} />
          {redoNarration && (
            <input
              value={voiceId}
              onChange={(event) => setVoiceId(event.target.value)}
              placeholder="Different ElevenLabs voice id (optional)"
              className={`max-w-xs ${inputClass}`}
            />
          )}
        </div>
      </Card>

      <ActionBar>
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="e.g. warmer, slower music" />
        <Button
          variant="secondary"
          disabled={pending || targets.length === 0}
          onClick={() =>
            send({
              action: "revise",
              feedback: feedback || undefined,
              edits: { regenerate: targets, ...(voiceId.trim() ? { voice_id: voiceId.trim() } : {}) },
            })
          }
        >
          <RefreshCw className="h-4 w-4" />
          Regenerate
        </Button>
        <Button disabled={pending} onClick={() => send({ action: "approve", feedback: feedback || undefined })}>
          <Check className="h-4 w-4" />
          Approve audio
        </Button>
      </ActionBar>
    </div>
  );
}
