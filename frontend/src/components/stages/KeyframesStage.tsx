"use client";

import { CheckCircle2, Clapperboard, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { ModelPicker, QualityPicker } from "@/components/ModelPicker";
import { Button, Card, DirectionInput, SectionTitle, Toggle, toggle } from "@/components/ui";
import { assetUrl } from "@/lib/api";
import { timeRange } from "@/lib/format";
import type { KeyframesPayload, StageProps } from "@/lib/types";

export function KeyframesStage({ view, payload, send, pending, options }: StageProps<KeyframesPayload>) {
  const [selected, setSelected] = useState(payload.selected);
  const [regenerate, setRegenerate] = useState<number[]>([]);
  const [feedback, setFeedback] = useState("");
  const [imageModel, setImageModel] = useState<string | null>(null);
  const [imageQuality, setImageQuality] = useState<string | null>(null);

  const currentModel = payload.image_model ?? options?.defaults.image_model;
  const currentQuality = payload.image_quality ?? options?.defaults.image_quality;
  const chosen = payload.scenes.filter((scene) => selected[String(scene.order)] !== undefined).length;

  return (
    <div className="space-y-4">
      <div className="flex gap-2 overflow-x-auto rounded-xl border border-line bg-surface p-2">
        {payload.scenes.map((scene) => {
          const order = String(scene.order);
          const key = payload.keyframes[order]?.[selected[order] ?? 0];
          return (
            <a
              key={order}
              href={`#scene-${order}`}
              className="flex min-w-36 items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-raised"
            >
              <img
                src={assetUrl(view, key)}
                alt=""
                className="h-12 w-7 rounded object-cover ring-1 ring-gold/60"
              />
              <span>
                <span className="block text-xs font-semibold">Scene {order}</span>
                <span className="block font-mono text-[11px] text-faint">{timeRange(scene.start, scene.end)}</span>
              </span>
            </a>
          );
        })}
      </div>

      {payload.scenes.map((scene) => {
        const order = String(scene.order);
        const candidates = payload.keyframes[order] ?? [];
        return (
          <Card
            key={order}
            className="grid scroll-mt-6 gap-4 lg:grid-cols-[15rem_1fr_auto]"
          >
            <div id={`scene-${order}`}>
              <p className="text-sm font-semibold">
                Scene {order}{" "}
                <span className="ml-1 font-mono text-xs font-normal text-faint">
                  {timeRange(scene.start, scene.end)}
                </span>
              </p>
              <p className="mt-2 text-sm italic leading-relaxed text-dim">“{scene.narration}”</p>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-1">
              {candidates.map((key, index) => {
                const isSelected = selected[order] === index;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setSelected({ ...selected, [order]: index })}
                    aria-pressed={isSelected}
                    aria-label={`Scene ${order}, option ${index + 1}`}
                    className={`relative w-32 shrink-0 overflow-hidden rounded-lg border-2 transition ${
                      isSelected ? "border-gold" : "border-transparent opacity-80 hover:opacity-100"
                    }`}
                  >
                    <img
                      src={assetUrl(view, key)}
                      alt=""
                      className="aspect-[9/16] w-full bg-raised object-cover"
                    />
                    {isSelected && (
                      <CheckCircle2 className="absolute right-1.5 top-1.5 h-5 w-5 rounded-full bg-canvas text-gold" />
                    )}
                  </button>
                );
              })}
            </div>
            <Toggle
              label="Regenerate"
              checked={regenerate.includes(scene.order)}
              onChange={(on) => setRegenerate(toggle(regenerate, scene.order, on))}
            />
          </Card>
        );
      })}

      {regenerate.length > 0 && options && currentModel && currentQuality && (
        <Card className="space-y-4">
          <SectionTitle>Settings for the new images</SectionTitle>
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

      <ActionBar
        summary={
          <>
            <CheckCircle2 className="h-4 w-4 text-ok" />
            {chosen} of {payload.scenes.length} scenes selected
          </>
        }
      >
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="Direction for new images" />
        <Button
          variant="secondary"
          disabled={pending || regenerate.length === 0}
          onClick={() =>
            send({
              action: "regenerate",
              scene_orders: regenerate,
              feedback: feedback || undefined,
              edits: {
                ...(imageModel && imageModel !== currentModel ? { image_model: imageModel } : {}),
                ...(imageQuality && imageQuality !== currentQuality ? { image_quality: imageQuality } : {}),
              },
            })
          }
        >
          <RefreshCw className="h-4 w-4" />
          Regenerate {regenerate.length || ""}
        </Button>
        <Button disabled={pending} onClick={() => send({ action: "approve", edits: { selections: selected } })}>
          <Clapperboard className="h-4 w-4" />
          Approve and render animatic
        </Button>
      </ActionBar>
    </div>
  );
}
