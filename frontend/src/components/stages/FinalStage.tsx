"use client";

import { CheckCircle2, Download, RefreshCw, Type } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { CaptionStyleEditor } from "@/components/CaptionStyleEditor";
import { Button, Card, Stat } from "@/components/ui";
import { assetUrl, videoUrl } from "@/lib/api";
import { firstKeyframeKey, sameJson } from "@/lib/format";
import type { CaptionStyle, FinalPayload, StageProps } from "@/lib/types";

const linkClass =
  "inline-flex items-center justify-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-semibold text-ink hover:bg-raised";

export function FinalStage({ view, payload, send, pending, options }: StageProps<FinalPayload>) {
  const savedStyle = payload.caption_style ?? view.state.caption_style ?? options?.defaults.caption_style;
  const [style, setStyle] = useState<CaptionStyle | null>(null);
  const current = style ?? savedStyle;
  const captionsChanged = style !== null && !sameJson(style, savedStyle);

  const videoModel = view.state.video_model ?? options?.defaults.video_model;
  const modelLabel = options?.video_models.find((model) => model.id === videoModel)?.label ?? videoModel;
  const finalUrl = assetUrl(view, payload.final_key);

  return (
    <div className="space-y-6">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_1fr]">
        <Card className="space-y-3 p-3">
          <video
            controls
            preload="metadata"
            src={videoUrl(view, payload.final_key)}
            className="aspect-[9/16] w-full rounded-lg bg-black"
          />
          {finalUrl && (
            <a href={finalUrl} download className={`${linkClass} w-full`}>
              <Download className="h-4 w-4" />
              Download MP4
            </a>
          )}
        </Card>

        <div className="space-y-6">
          <Card className="flex flex-wrap gap-8">
            <Stat label="Scenes" value={view.state.scenes?.length ?? "–"} />
            <Stat
              label="Runtime"
              value={view.state.narration ? `${view.state.narration.duration.toFixed(1)}s` : "–"}
            />
            <Stat label="Video model" value={modelLabel ?? "–"} />
          </Card>

          {options && current && (
            <Card className="space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="flex items-center gap-2 text-sm font-semibold">
                  <Type className="h-4 w-4 text-gold" />
                  Captions
                </p>
                <span className="text-xs text-faint">Re-cutting reuses the approved clips; nothing is regenerated</span>
              </div>
              <CaptionStyleEditor
                value={current}
                onChange={setStyle}
                options={options}
                previewImage={assetUrl(view, firstKeyframeKey(view.state))}
              />
            </Card>
          )}
        </div>
      </div>

      <ActionBar summary={captionsChanged ? "Re-cut to apply your caption changes" : "Happy with it? Approve to finish."}>
        <Button
          variant="secondary"
          disabled={pending || !captionsChanged}
          onClick={() => send({ action: "revise", edits: { caption_style: current } })}
        >
          <RefreshCw className="h-4 w-4" />
          Re-cut with these captions
        </Button>
        <Button disabled={pending || captionsChanged} onClick={() => send({ action: "approve" })}>
          <CheckCircle2 className="h-4 w-4" />
          Approve and finish
        </Button>
      </ActionBar>
    </div>
  );
}
