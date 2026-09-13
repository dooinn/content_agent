"use client";

import { CheckCircle2, CircleAlert, RefreshCw, Scissors } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { ModelPicker } from "@/components/ModelPicker";
import { Badge, Button, Card, DirectionInput, SectionTitle, Toggle, toggle } from "@/components/ui";
import { videoUrl } from "@/lib/api";
import type { ClipsPayload, StageProps } from "@/lib/types";

export function ClipsStage({ view, payload, send, pending, options }: StageProps<ClipsPayload>) {
  const [selected, setSelected] = useState(payload.selected);
  const [regenerate, setRegenerate] = useState<number[]>(() => Object.keys(payload.errors).map(Number));
  const [feedback, setFeedback] = useState("");
  const [videoModel, setVideoModel] = useState<string | null>(null);

  const currentModel = payload.video_model ?? view.state.video_model ?? options?.defaults.video_model;
  const ready = payload.shots.filter((shot) => payload.clips[String(shot.order)]?.length).length;
  const missing = payload.shots.length - ready;

  return (
    <div className="space-y-6">
      {Object.keys(payload.errors).length > 0 && (
        <Card className="border-danger/30 bg-danger/5">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-danger">
            <CircleAlert className="h-4 w-4" />
            Some clips failed
          </p>
          <ul className="space-y-1 text-sm text-dim">
            {Object.entries(payload.errors).map(([order, error]) => (
              <li key={order}>
                Scene {order}: {error}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-faint">Clips that succeeded were kept; regenerate only the failed scenes.</p>
        </Card>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {payload.shots.map((shot) => {
          const order = String(shot.order);
          const takes = payload.clips[order] ?? [];
          const failed = order in payload.errors && takes.length === 0;
          return (
            <Card key={order} className="flex flex-col gap-3 p-3">
              <div className="flex items-center justify-between px-1">
                <p className="text-sm font-semibold">Scene {order}</p>
                <div className="flex items-center gap-2">
                  <Badge>{shot.clip_seconds}s</Badge>
                  {failed ? <Badge tone="red">Failed</Badge> : <Badge tone="green">Ready</Badge>}
                </div>
              </div>
              {takes.length === 0 && (
                <div className="flex aspect-[9/16] items-center justify-center rounded-lg bg-raised text-sm text-faint">
                  No clip yet
                </div>
              )}
              {takes.map((key, index) => (
                <div key={key} className="space-y-2">
                  <video
                    controls
                    muted
                    loop
                    playsInline
                    preload="metadata"
                    src={videoUrl(view, key)}
                    className={`aspect-[9/16] w-full rounded-lg border-2 bg-black ${
                      selected[order] === index ? "border-gold" : "border-transparent"
                    }`}
                  />
                  {takes.length > 1 && (
                    <Button
                      variant={selected[order] === index ? "primary" : "secondary"}
                      className="w-full"
                      onClick={() => setSelected({ ...selected, [order]: index })}
                    >
                      {selected[order] === index ? "Selected" : `Use take ${index + 1}`}
                    </Button>
                  )}
                </div>
              ))}
              <p className="line-clamp-3 px-1 text-xs leading-relaxed text-faint">{shot.video_prompt}</p>
              <div className="mt-auto px-1">
                <Toggle
                  label="Regenerate"
                  checked={regenerate.includes(shot.order)}
                  onChange={(on) => setRegenerate(toggle(regenerate, shot.order, on))}
                />
              </div>
            </Card>
          );
        })}
      </div>

      {regenerate.length > 0 && options && currentModel && (
        <Card>
          <SectionTitle>Model for the new clips</SectionTitle>
          <ModelPicker
            label="Video model"
            models={options.video_models}
            value={videoModel ?? currentModel}
            onChange={setVideoModel}
          />
        </Card>
      )}

      <ActionBar
        summary={
          <>
            <CheckCircle2 className={`h-4 w-4 ${missing ? "text-faint" : "text-ok"}`} />
            {ready} of {payload.shots.length} clips ready
          </>
        }
      >
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="Direction for regenerated clips" />
        <Button
          variant="secondary"
          disabled={pending || regenerate.length === 0}
          onClick={() =>
            send({
              action: "regenerate",
              scene_orders: regenerate,
              feedback: feedback || undefined,
              edits: videoModel && videoModel !== currentModel ? { video_model: videoModel } : {},
            })
          }
        >
          <RefreshCw className="h-4 w-4" />
          Regenerate {regenerate.length || ""}
        </Button>
        <Button
          disabled={pending || missing > 0}
          onClick={() => send({ action: "approve", edits: { selections: selected } })}
        >
          <Scissors className="h-4 w-4" />
          Approve clips and cut final
        </Button>
      </ActionBar>
    </div>
  );
}
