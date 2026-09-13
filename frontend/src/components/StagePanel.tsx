"use client";

import { Loader2 } from "lucide-react";
import { Card } from "@/components/ui";
import { AngleStage } from "@/components/stages/AngleStage";
import { AudioStage } from "@/components/stages/AudioStage";
import { BibleStage } from "@/components/stages/BibleStage";
import { ClipsStage } from "@/components/stages/ClipsStage";
import { FinalStage } from "@/components/stages/FinalStage";
import { FinalView } from "@/components/stages/FinalView";
import { KeyframesStage } from "@/components/stages/KeyframesStage";
import { MotionStage } from "@/components/stages/MotionStage";
import { PreviewStage } from "@/components/stages/PreviewStage";
import { ResearchStage } from "@/components/stages/ResearchStage";
import { ScenesStage } from "@/components/stages/ScenesStage";
import { ScriptStage } from "@/components/stages/ScriptStage";
import type {
  AnglePayload,
  AudioPayload,
  BiblePayload,
  ClipsPayload,
  Decision,
  FinalPayload,
  KeyframesPayload,
  MotionPayload,
  Options,
  PreviewPayload,
  ProjectView,
  ResearchPayload,
  ScenesPayload,
  ScriptPayload,
} from "@/lib/types";

interface Props {
  view: ProjectView;
  send: (decision: Decision) => Promise<void>;
  pending: boolean;
  options: Options | null;
}

export function StagePanel({ view, send, pending, options }: Props) {
  const props = { view, send, pending, options };
  const payload = view.payload;

  switch (view.stage) {
    case "research":
      return <ResearchStage {...props} payload={payload as ResearchPayload} />;
    case "angle":
      return <AngleStage {...props} payload={payload as AnglePayload} />;
    case "script":
      return <ScriptStage {...props} payload={payload as ScriptPayload} />;
    case "audio":
      return <AudioStage {...props} payload={payload as AudioPayload} />;
    case "bible":
      return <BibleStage {...props} payload={payload as BiblePayload} />;
    case "scenes":
      return <ScenesStage {...props} payload={payload as ScenesPayload} />;
    case "keyframes":
      return <KeyframesStage {...props} payload={payload as KeyframesPayload} />;
    case "preview":
      return <PreviewStage {...props} payload={payload as PreviewPayload} />;
    case "motion":
      return <MotionStage {...props} payload={payload as MotionPayload} />;
    case "clips":
      return <ClipsStage {...props} payload={payload as ClipsPayload} />;
    case "final":
      return <FinalStage {...props} payload={payload as FinalPayload} />;
  }

  if (view.project.status === "rejected") {
    return (
      <Card className="text-sm text-dim">
        This figure is outside the supported range: only long-deceased historical figures are allowed.
      </Card>
    );
  }
  if (view.state.final_key || view.state.preview_key) {
    return <FinalView view={view} />;
  }
  return <Card className="text-sm text-dim">Nothing is waiting for review.</Card>;
}

export function WorkingNote() {
  return (
    <Card className="flex items-center gap-4">
      <span className="flex h-10 w-10 items-center justify-center rounded-full bg-info/10 text-info">
        <Loader2 className="h-5 w-5 animate-spin" />
      </span>
      <div>
        <p className="font-medium text-ink">Working on the next step…</p>
        <p className="text-sm text-dim">
          Research and generation can take a few minutes. This page refreshes on its own.
        </p>
      </div>
    </Card>
  );
}
