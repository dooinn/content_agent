import type { Stage } from "./types";

export interface StageInfo {
  key: Stage;
  label: string;
  title: string;
  helper: string;
  paid: boolean;
}

export const STAGE_INFO: Record<Stage, StageInfo> = {
  research: {
    key: "research", label: "Research", paid: false,
    title: "Review the research",
    helper: "Check the facts and sources before the story is written.",
  },
  angle: {
    key: "angle", label: "Angle", paid: false,
    title: "Choose a story angle",
    helper: "Pick the one story this video will tell.",
  },
  script: {
    key: "script", label: "Script", paid: false,
    title: "Edit the narration",
    helper: "Timed at about 155 words per minute. Edit any line directly.",
  },
  audio: {
    key: "audio", label: "Audio", paid: true,
    title: "Listen to the narration and music",
    helper: "Scene timing comes from the narration, so lock the voice before visuals.",
  },
  bible: {
    key: "bible", label: "Visual bible", paid: true,
    title: "Approve the look",
    helper: "The style guide and character sheets that every image follows.",
  },
  scenes: {
    key: "scenes", label: "Scenes", paid: false,
    title: "Review the scenes",
    helper: "One scene per narration line. Fix prompts before any keyframe is made.",
  },
  keyframes: {
    key: "keyframes", label: "Keyframes", paid: true,
    title: "Pick a keyframe for each scene",
    helper: "Click the image you want. Toggle Regenerate to get new options.",
  },
  preview: {
    key: "preview", label: "Animatic", paid: false,
    title: "Watch the animatic",
    helper: "Keyframes cut to the narration. Caption changes here re-render for free.",
  },
  motion: {
    key: "motion", label: "Motion", paid: false,
    title: "Plan the motion",
    helper: "Choose the video model and camera moves. Nothing is generated until you approve.",
  },
  clips: {
    key: "clips", label: "Clips", paid: true,
    title: "Review the clips",
    helper: "Play each clip. Regenerate only the scenes that miss.",
  },
  final: {
    key: "final", label: "Final cut", paid: false,
    title: "Final cut",
    helper: "Adjust captions and re-cut for free, or approve to finish the project.",
  },
};

export const PHASES: { label: string; stages: Stage[] }[] = [
  { label: "Story", stages: ["research", "angle", "script", "audio"] },
  { label: "Look", stages: ["bible", "scenes", "keyframes"] },
  { label: "Video", stages: ["preview", "motion", "clips"] },
  { label: "Final cut", stages: ["final"] },
];

export const STAGE_ORDER: Stage[] = PHASES.flatMap((phase) => phase.stages);

/** Index of the current step; the full length means every step is complete. */
export function stageIndex(stage: string | null, status: string): number {
  if (status === "done" || (status === "final_ready" && !stage)) return STAGE_ORDER.length;
  const index = STAGE_ORDER.indexOf(stage as Stage);
  return index === -1 ? 0 : index;
}
