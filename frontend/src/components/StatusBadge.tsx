import { CheckCircle2, CircleAlert, Clock3, Loader2, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { STAGE_INFO } from "@/lib/stages";
import type { Stage, Status } from "@/lib/types";
import { Badge, type Tone } from "./ui";

const STATUS: Record<Status, { label: string; tone: Tone; icon: ReactNode }> = {
  running: { label: "Working", tone: "blue", icon: <Loader2 className="h-3 w-3 animate-spin" /> },
  awaiting_review: { label: "Needs your review", tone: "amber", icon: <Clock3 className="h-3 w-3" /> },
  failed: { label: "Failed", tone: "red", icon: <CircleAlert className="h-3 w-3" /> },
  rejected: { label: "Rejected", tone: "zinc", icon: <XCircle className="h-3 w-3" /> },
  preview_ready: { label: "Animatic ready", tone: "green", icon: <CheckCircle2 className="h-3 w-3" /> },
  final_ready: { label: "Final ready", tone: "green", icon: <CheckCircle2 className="h-3 w-3" /> },
  done: { label: "Done", tone: "green", icon: <CheckCircle2 className="h-3 w-3" /> },
};

export function StatusBadge({ status }: { status: Status }) {
  const { label, tone, icon } = STATUS[status] ?? { label: status, tone: "zinc", icon: null };
  return (
    <Badge tone={tone}>
      {icon}
      {label}
    </Badge>
  );
}

export function stageLabel(stage: string | null) {
  return stage && stage in STAGE_INFO ? STAGE_INFO[stage as Stage].label : null;
}
