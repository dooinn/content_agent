"use client";

import { ArrowRight, RefreshCw, Type } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { CaptionStyleEditor } from "@/components/CaptionStyleEditor";
import { Button, Card, Checkbox, DirectionInput, SectionTitle, toggle } from "@/components/ui";
import { assetUrl, videoUrl } from "@/lib/api";
import { firstKeyframeKey, sameJson } from "@/lib/format";
import type { CaptionStyle, PreviewPayload, StageProps } from "@/lib/types";

export function PreviewStage({ view, payload, send, pending, options }: StageProps<PreviewPayload>) {
  const scenes = view.state.scenes ?? [];
  const savedStyle = payload.caption_style ?? view.state.caption_style ?? options?.defaults.caption_style;
  const [style, setStyle] = useState<CaptionStyle | null>(null);
  const [regenerate, setRegenerate] = useState<number[]>([]);
  const [feedback, setFeedback] = useState("");

  const current = style ?? savedStyle;
  const captionsChanged = style !== null && !sameJson(style, savedStyle);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,20rem)_1fr]">
        <Card className="p-3">
          <video
            controls
            preload="metadata"
            src={videoUrl(view, payload.preview_key)}
            className="aspect-[9/16] w-full rounded-lg bg-black"
          />
          <p className="px-1 pt-3 text-xs text-faint">
            Keyframes with slow push-ins, narration, music, and captions. No video has been generated yet.
          </p>
        </Card>

        <div className="space-y-6">
          {options && current && (
            <Card className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Type className="h-4 w-4 text-gold" />
                  Captions
                </p>
                <span className="text-xs text-faint">Re-rendering is free</span>
              </div>
              <CaptionStyleEditor
                value={current}
                onChange={setStyle}
                options={options}
                previewImage={assetUrl(view, firstKeyframeKey(view.state))}
              />
              <Button
                variant="secondary"
                disabled={pending || !captionsChanged}
                onClick={() => send({ action: "revise", edits: { caption_style: current } })}
              >
                <RefreshCw className="h-4 w-4" />
                Re-render animatic with these captions
              </Button>
            </Card>
          )}

          <Card>
            <SectionTitle>Redo keyframes</SectionTitle>
            <p className="-mt-1 mb-3 text-sm text-faint">Pick scenes whose images should be generated again.</p>
            <div className="flex flex-wrap gap-4">
              {scenes.map((scene) => (
                <Checkbox
                  key={scene.order}
                  label={`Scene ${scene.order}`}
                  checked={regenerate.includes(scene.order)}
                  onChange={(on) => setRegenerate(toggle(regenerate, scene.order, on))}
                />
              ))}
            </div>
          </Card>
        </div>
      </div>

      <ActionBar summary={captionsChanged ? "Caption changes will apply to the final cut" : undefined}>
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="Direction for the motion plan" />
        <Button
          variant="secondary"
          disabled={pending || regenerate.length === 0}
          onClick={() =>
            send({ action: "regenerate", scene_orders: regenerate, feedback: feedback || undefined })
          }
        >
          <RefreshCw className="h-4 w-4" />
          Redo {regenerate.length || ""} keyframes
        </Button>
        <Button
          disabled={pending}
          onClick={() =>
            send({
              action: "approve",
              feedback: feedback || undefined,
              edits: captionsChanged ? { caption_style: current } : {},
            })
          }
        >
          Approve and plan motion
          <ArrowRight className="h-4 w-4" />
        </Button>
      </ActionBar>
    </div>
  );
}
