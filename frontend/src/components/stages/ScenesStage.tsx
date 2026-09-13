"use client";

import { Check, ImageIcon, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { ModelPicker, QualityPicker } from "@/components/ModelPicker";
import { CriticNote } from "@/components/ReviewNotes";
import { Badge, Button, Card, Detail, DirectionInput, SectionTitle, inputClass } from "@/components/ui";
import { timeRange } from "@/lib/format";
import type { ScenesPayload, StageProps } from "@/lib/types";

interface SceneDraft {
  order: number;
  image_prompt: string;
  character_look: string | null;
}

export function ScenesStage({ view, payload, send, pending, options }: StageProps<ScenesPayload>) {
  const looks = view.state.bible?.character.looks ?? [];
  const initial: SceneDraft[] = payload.scenes.map((scene) => ({
    order: scene.order,
    image_prompt: scene.image_prompt,
    character_look: scene.character_look ?? null,
  }));
  const currentModel = view.state.image_model ?? options?.defaults.image_model;
  const currentQuality = view.state.image_quality ?? options?.defaults.image_quality;

  const [drafts, setDrafts] = useState(initial);
  const [feedback, setFeedback] = useState("");
  const [imageModel, setImageModel] = useState<string | null>(null);
  const [imageQuality, setImageQuality] = useState<string | null>(null);

  const edits = drafts.filter(
    (draft, i) =>
      draft.image_prompt !== initial[i].image_prompt || draft.character_look !== initial[i].character_look,
  );
  const update = (index: number, patch: Partial<SceneDraft>) =>
    setDrafts(drafts.map((draft, i) => (i === index ? { ...draft, ...patch } : draft)));

  return (
    <div className="space-y-6">
      <CriticNote report={payload.critic_report} rounds={payload.critic_rounds} />

      {payload.scenes.map((scene, index) => (
        <Card key={scene.order} className="grid gap-5 lg:grid-cols-[1fr_1.4fr]">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold">Scene {scene.order}</span>
              <span className="font-mono text-xs text-faint">{timeRange(scene.start, scene.end)}</span>
            </div>
            <p className="text-sm italic text-ink">“{scene.narration}”</p>
            <Detail label="Description">{scene.description}</Detail>
            <div className="flex flex-wrap gap-2">
              <Badge>{scene.shot_type}</Badge>
              <Badge>{scene.camera_move}</Badge>
            </div>
          </div>
          <div className="space-y-3">
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wider text-faint">Character look</span>
              <select
                value={drafts[index].character_look ?? ""}
                onChange={(event) => update(index, { character_look: event.target.value || null })}
                className={`mt-1.5 ${inputClass}`}
              >
                <option value="">Character not on screen</option>
                {looks.map((look) => (
                  <option key={look.id} value={look.id}>
                    {look.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wider text-faint">Image prompt</span>
              <textarea
                value={drafts[index].image_prompt}
                onChange={(event) => update(index, { image_prompt: event.target.value })}
                rows={6}
                className={`mt-1.5 ${inputClass} leading-relaxed`}
              />
            </label>
          </div>
        </Card>
      ))}

      {options && currentModel && currentQuality && (
        <Card className="space-y-4">
          <div>
            <SectionTitle>Keyframe settings</SectionTitle>
            <p className="-mt-1 text-sm text-faint">
              Used when the keyframes are generated right after you approve.
            </p>
          </div>
          <ModelPicker
            label="Image model"
            models={options.image_models}
            value={imageModel ?? currentModel}
            onChange={setImageModel}
          />
          <QualityPicker
            qualities={options.image_qualities}
            value={imageQuality ?? currentQuality}
            onChange={setImageQuality}
          />
        </Card>
      )}

      <ActionBar summary={edits.length ? `${edits.length} scene${edits.length > 1 ? "s" : ""} edited` : undefined}>
        <DirectionInput
          value={feedback}
          onChange={setFeedback}
          placeholder="With Approve, added to every keyframe prompt"
        />
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() => send({ action: "revise", feedback: feedback || undefined })}
        >
          <RefreshCw className="h-4 w-4" />
          Rewrite scenes
        </Button>
        <Button
          disabled={pending}
          onClick={() =>
            send({
              action: "approve",
              feedback: feedback || undefined,
              edits: {
                ...(edits.length ? { scenes: edits } : {}),
                ...(imageModel && imageModel !== currentModel ? { image_model: imageModel } : {}),
                ...(imageQuality && imageQuality !== currentQuality ? { image_quality: imageQuality } : {}),
              },
            })
          }
        >
          <ImageIcon className="h-4 w-4" />
          Approve and make keyframes
          <Check className="hidden" />
        </Button>
      </ActionBar>
    </div>
  );
}
