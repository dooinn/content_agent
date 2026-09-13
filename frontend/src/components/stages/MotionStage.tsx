"use client";

import { Film, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { ModelPicker } from "@/components/ModelPicker";
import { Button, Card, DirectionInput, Stat, inputClass } from "@/components/ui";
import type { MotionPayload, StageProps } from "@/lib/types";

export function MotionStage({ payload, send, pending, options }: StageProps<MotionPayload>) {
  const [shots, setShots] = useState(payload.shots);
  const [feedback, setFeedback] = useState("");
  const [videoModel, setVideoModel] = useState<string | null>(null);

  const currentModel = payload.estimate.model;
  const model = videoModel ?? currentModel;
  const modelLabel = options?.video_models.find((option) => option.id === model)?.label ?? model;
  const candidates = Math.max(1, Math.round(payload.estimate.clips / Math.max(1, payload.shots.length)));
  const totalSeconds = shots.reduce((sum, shot) => sum + shot.clip_seconds, 0) * candidates;
  const edits = shots
    .filter(
      (shot, i) =>
        shot.video_prompt !== payload.shots[i].video_prompt ||
        shot.clip_seconds !== payload.shots[i].clip_seconds,
    )
    .map(({ order, video_prompt, clip_seconds }) => ({ order, video_prompt, clip_seconds }));
  const validSeconds = shots.every(
    (shot) => Number.isInteger(shot.clip_seconds) && shot.clip_seconds >= 3 && shot.clip_seconds <= 15,
  );
  const update = (index: number, patch: Partial<(typeof shots)[number]>) =>
    setShots(shots.map((shot, i) => (i === index ? { ...shot, ...patch } : shot)));

  return (
    <div className="space-y-6">
      <Card className="grid gap-6 lg:grid-cols-[1fr_auto]">
        {options ? (
          <ModelPicker label="Video model" models={options.video_models} value={model} onChange={setVideoModel} />
        ) : (
          <Stat label="Video model" value={model} />
        )}
        <div className="flex gap-8 border-line lg:border-l lg:pl-8">
          <Stat label="Clips" value={payload.estimate.clips} />
          <Stat label="Total clip seconds" value={totalSeconds} />
        </div>
      </Card>

      {shots.map((shot, index) => (
        <Card key={shot.order} className="grid gap-4 lg:grid-cols-[1fr_2fr]">
          <div className="space-y-3">
            <p className="text-sm font-semibold">Scene {shot.order}</p>
            <p className="text-sm italic text-dim">“{shot.narration}”</p>
            <label className="flex items-center gap-3 text-xs font-semibold uppercase tracking-wider text-faint">
              Clip seconds
              <input
                type="number"
                min={3}
                max={15}
                step={1}
                value={shot.clip_seconds}
                onChange={(event) => update(index, { clip_seconds: Number(event.target.value) })}
                className={`w-20 ${inputClass}`}
              />
            </label>
          </div>
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-wider text-faint">Motion prompt</span>
            <textarea
              value={shot.video_prompt}
              onChange={(event) => update(index, { video_prompt: event.target.value })}
              rows={4}
              className={`mt-1.5 ${inputClass} leading-relaxed`}
            />
          </label>
        </Card>
      ))}

      <ActionBar summary="Nothing is generated until you approve">
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="e.g. slower camera moves" />
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() => send({ action: "revise", feedback: feedback || undefined })}
        >
          <RefreshCw className="h-4 w-4" />
          Rewrite motion
        </Button>
        <Button
          disabled={pending || !validSeconds}
          onClick={() =>
            send({
              action: "approve",
              feedback: feedback || undefined,
              edits: {
                ...(edits.length ? { shots: edits } : {}),
                ...(videoModel && videoModel !== currentModel ? { video_model: videoModel } : {}),
              },
            })
          }
        >
          <Film className="h-4 w-4" />
          Generate {payload.estimate.clips} clips with {modelLabel}
        </Button>
      </ActionBar>
    </div>
  );
}
