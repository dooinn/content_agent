"use client";

import { Check, RefreshCw } from "lucide-react";
import { useState } from "react";
import { ActionBar } from "@/components/ActionBar";
import { ModelPicker, QualityPicker } from "@/components/ModelPicker";
import {
  Button,
  Card,
  Detail,
  DirectionInput,
  SectionTitle,
  Toggle,
  fileInputClass,
} from "@/components/ui";
import { assetUrl, errorMessage, uploadImage } from "@/lib/api";
import type { BiblePayload, StageProps } from "@/lib/types";

export function BibleStage({ view, payload, send, pending, options }: StageProps<BiblePayload>) {
  const { bible, character_refs: refs } = payload;
  const looks = bible.character.looks ?? [];
  const styleUrl = assetUrl(view, view.state.style_ref_key);
  const currentModel = view.state.image_model ?? options?.defaults.image_model;
  const currentQuality = view.state.image_quality ?? options?.defaults.image_quality;

  const [feedback, setFeedback] = useState("");
  const [imageOnly, setImageOnly] = useState(false);
  const [styleKey, setStyleKey] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [imageModel, setImageModel] = useState<string | null>(null);
  const [imageQuality, setImageQuality] = useState<string | null>(null);

  const upload = async (file: File | undefined) => {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    try {
      setStyleKey((await uploadImage(file)).key);
    } catch (err) {
      setUploadError(errorMessage(err));
    } finally {
      setUploading(false);
    }
  };

  const reviseEdits = {
    ...(imageOnly ? { image_only: true } : {}),
    ...(styleKey ? { style_ref_key: styleKey } : {}),
    ...(imageModel && imageModel !== currentModel ? { image_model: imageModel } : {}),
    ...(imageQuality && imageQuality !== currentQuality ? { image_quality: imageQuality } : {}),
  };

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card className="space-y-5">
          <Detail label="Visual style">{bible.visual_style}</Detail>
          <div className="grid gap-5 md:grid-cols-2">
            <Detail label="Palette">{bible.color_palette}</Detail>
            <Detail label="Lighting">{bible.lighting}</Detail>
          </div>
          <div className="grid gap-5 border-t border-line pt-5 md:grid-cols-2">
            <Detail label="Period details">
              <ul className="list-disc space-y-1 pl-4">
                {bible.period_details.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Detail>
            <Detail label="Anachronisms to avoid">
              <ul className="list-disc space-y-1 pl-4">
                {bible.anachronisms_to_avoid.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </Detail>
          </div>
        </Card>
        <Card>
          <SectionTitle>Style reference</SectionTitle>
          {styleUrl ? (
            <img src={styleUrl} alt="Style reference" className="w-full rounded-lg" />
          ) : (
            <p className="text-sm text-faint">None uploaded. The bible text defines the look.</p>
          )}
        </Card>
      </div>

      <div>
        <SectionTitle>Character sheets · {bible.character.name}</SectionTitle>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {looks.map((look) => (
            <Card key={look.id} className="p-3">
              <img
                src={assetUrl(view, refs[look.id])}
                alt={look.label}
                className="aspect-[9/16] w-full rounded-lg bg-raised object-cover"
              />
              <div className="px-1 pb-1 pt-3">
                <h3 className="font-semibold">{look.label}</h3>
                <p className="text-xs text-faint">
                  look “{look.id}” · age {look.age}
                </p>
                <p className="mt-2 text-sm leading-relaxed text-dim">{look.costume}</p>
              </div>
            </Card>
          ))}
        </div>
      </div>

      <Card className="space-y-5">
        <SectionTitle>Revise options</SectionTitle>
        <Toggle label="Redraw the character sheets only (keep the bible text)" checked={imageOnly} onChange={setImageOnly} />
        <label className="block text-sm">
          <span className="text-dim">Replace the style reference</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => upload(event.target.files?.[0])}
            className={`mt-2 ${fileInputClass}`}
          />
          {uploading && <span className="mt-1 block text-xs text-faint">Uploading…</span>}
          {styleKey && <span className="mt-1 block text-xs text-ok">Uploaded. Revise to use it.</span>}
          {uploadError && <span className="mt-1 block text-xs text-danger">{uploadError}</span>}
        </label>
        {options && currentModel && currentQuality && (
          <div className="space-y-4 border-t border-line pt-5">
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
          </div>
        )}
      </Card>

      <ActionBar>
        <DirectionInput value={feedback} onChange={setFeedback} placeholder="e.g. make the boy look older" />
        <Button
          variant="secondary"
          disabled={pending || uploading}
          onClick={() => send({ action: "revise", feedback: feedback || undefined, edits: reviseEdits })}
        >
          <RefreshCw className="h-4 w-4" />
          Revise
        </Button>
        <Button
          disabled={pending || uploading}
          onClick={() => send({ action: "approve", feedback: feedback || undefined })}
        >
          <Check className="h-4 w-4" />
          Approve bible
        </Button>
      </ActionBar>
    </div>
  );
}
